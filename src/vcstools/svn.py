# Software License Agreement (BSD License)
#
# Copyright (c) 2010, Willow Garage, Inc.
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions
# are met:
#
#  * Redistributions of source code must retain the above copyright
#    notice, this list of conditions and the following disclaimer.
#  * Redistributions in binary form must reproduce the above
#    copyright notice, this list of conditions and the following
#    disclaimer in the documentation and/or other materials provided
#    with the distribution.
#  * Neither the name of Willow Garage, Inc. nor the names of its
#    contributors may be used to endorse or promote products derived
#    from this software without specific prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
# "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
# LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS
# FOR A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE
# COPYRIGHT OWNER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT,
# INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING,
# BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
# LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER
# CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT
# LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN
# ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
# POSSIBILITY OF SUCH DAMAGE.
#
"""
svn vcs support.
"""

import os
import sys
import subprocess
from .vcs_base import VcsClientBase

class SvnClient(VcsClientBase):

    def __init__(self, path):
        """
        Raise LookupError if svn not detected
        """
        VcsClientBase.__init__(self, 'svn', path)
        with open(os.devnull, 'w') as fnull:
            try:
                subprocess.call("svn help".split(), stdout=fnull, stderr=fnull)
            except:
                raise LookupError("svn not installed, cannnot create an svn vcs client")
 
    def get_url(self):
        """
        @return: SVN URL of the directory path (output of svn info command), or None if it cannot be determined
        """
        if self.detect_presence():
            #3305: parsing not robust to non-US locales
            output = subprocess.Popen(['svn', 'info', self._path], stdout=subprocess.PIPE, env={"LANG":"en_US.UTF-8"}).communicate()[0]
            matches = [l for l in output.splitlines() if l.startswith('URL: ')]
            if matches:
                return matches[0][5:]
        return None

    def detect_presence(self):
        return self.path_exists() and os.path.isdir(os.path.join(self._path, '.svn'))

    def exists(self, url):
        """
        @return: True if url exists in repo
        """
        cmd = ['svn', 'info', url]
        output = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE).communicate()
        return bool(output[0])

    def checkout(self, url, version=''):
        if self.path_exists():
            sys.stderr.write("Error: cannot checkout into existing directory\n")
            return False
        if version != None and version != '':
            if not version.startswith("-r"):
                version = "-r" + version
        cmd = "svn co %s %s %s"%(version, url, self._path)
        if subprocess.call(cmd, shell=True) == 0:
            return True
        return False

    def update(self, version=''):
        if not self.detect_presence():
            return False
        if version != None and version != '':
            if not version.startswith("-r"):
                version = "-r" + version
        cmd = "svn up %s %s"%(version, self._path)
        if subprocess.call(cmd, shell=True) == 0:
            return True
        return False

    def get_version(self, spec=None):
        """
        @param spec: (optional) spec can be what 'svn info --help'
        allows, meaning a revnumber, {date}, HEAD, BASE, PREV, or
        COMMITTED.

        @return: current revision number of the repository. Or if spec
        provided, the number of a revision specified by some
        token.
        """
        command = ['svn', 'info']
        if spec != None:
            if spec.isdigit():
                # looking up svn with "-r" takes long, and if spec is
                # a number, all we get from svn is the same number,
                # unless we try to look at higher rev numbers (in
                # which case either get the same number, or an error
                # if the rev does not exist). So we first do a very
                # quick svn info, and check revision numbers.
                currentversion = self.get_version(spec = None)
                # currentversion is like '-r12345'
                if currentversion != None and int(currentversion[2:]) > int(spec):
                    # so if we know revision exist, just return the
                    # number, avoid the long call to svn server
                    return '-r'+spec
            if spec.startswith("-r"):
                command.append(spec)
            else:
                command.append('-r' + spec)
        command.append(self._path)
        # #3305: parsing not robust to non-US locales
        output = subprocess.Popen(command, env={"LANG":"en_US.UTF-8"}, stdout=subprocess.PIPE).communicate()[0]
        if output != None:
            matches = [l for l in output.splitlines() if l.startswith('Revision: ')]
            if len(matches) == 1:
                split_str = matches[0].split()
                if len(split_str) == 2:
                    return '-r'+split_str[1]
        return None

    def get_diff(self, basepath=None):
        response = None
        if basepath == None:
            basepath = self._path
        if self.path_exists():
            rel_path = self._normalized_rel_path(self._path, basepath)
            command = "cd %s; svn diff %s"%(basepath, rel_path)
            stdout_handle = os.popen(command, "r")
            response = stdout_handle.read()
        if response != None and response.strip() == '':
            response = None
        return response
 
 
    def get_status(self, basepath=None, untracked=False):
        response=None
        if basepath == None:
            basepath = self._path
        if self.path_exists():
            rel_path = self._normalized_rel_path(self._path, basepath)
            command = "cd %s; svn status %s"%(basepath, rel_path)
            if not untracked:
                command += " -q"
            stdout_handle = os.popen(command, "r")
            response = stdout_handle.read()
        return response

SVNClient = SvnClient
