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
bzr vcs support.

New in ROS C-Turtle.
"""

import subprocess
import os
import sys
import urllib

from  .vcs_base import VcsClientBase

class BzrClient(VcsClientBase):
    def __init__(self, path):
        """
        Raise LookupError if bzr not detected
        """
        VcsClientBase.__init__(self, 'bzr', path)
        with open(os.devnull, 'w') as fnull:
            try:
                subprocess.call("bzr help".split(), stdout=fnull, stderr=fnull)
            except:
                raise LookupError("bzr not installed, cannot create a bzr vcs client")

    def get_url(self):
        """
        @return: BZR URL of the directory path (output of bzr info command), or None if it cannot be determined
        """
        if self.detect_presence():
            output = subprocess.Popen(['bzr', 'info', self._path], stdout=subprocess.PIPE).communicate()[0]
            matches = [l for l in output.split('\n') if l.startswith('  parent branch:')]
            if matches:
                return urllib.url2pathname(matches[0][17:])
        return None

    def detect_presence(self):
        return self.path_exists() and os.path.isdir(os.path.join(self._path, '.bzr'))

    def checkout(self, url, version=''):
        if self.path_exists():
            sys.stderr.write("Error: cannot checkout into existing directory\n")
            return False
            
        if version:
            cmd = "bzr branch -r %s %s %s"%(version, url, self._path)
        else:
            cmd = "bzr branch %s %s"%(url, self._path)
        if subprocess.call(cmd, shell=True) == 0:
            return True
        return False

    def update(self, version=''):
        if not self.detect_presence():
            return False
        if not subprocess.call("bzr pull", cwd=self._path, shell=True) == 0:
            return False
        if version != '':
            cmd = "bzr update -r %s"%(version)
            if subprocess.call(cmd, cwd=self._path, shell=True) == 0:
                return True
        return False

    def get_version(self, spec=None):
        """
        @param spec: (optional) revisionspec of desired version.  May
        be any revisionspec as returned by 'bzr help revisionspec',
        e.g. a tagname or 'revno:<number>'
        
        @return: the current revision number of the repository. Or if
        spec is provided, the number of a revision specified by some
        token. 
        """
        if self.detect_presence():
            if spec is not None:
                command = ['bzr', 'log', '-r', spec, '.']
                output = subprocess.Popen(command, cwd=self._path, stdout=subprocess.PIPE).communicate()[0]
                if output is None or output.strip() == '' or output.startswith("bzr:"):
                    return None
                else:
                    matches = [l for l in output.split('\n') if l.startswith('revno: ')]
                    if len(matches) == 1:
                        return matches[0].split()[1]
            else:
                output = subprocess.Popen(['bzr', 'revno', '--tree'], cwd= self._path, stdout=subprocess.PIPE).communicate()[0]
                return output.strip()

    def get_diff(self, basepath=None):
        response = None
        if basepath == None:
            basepath = self._path
        if self.path_exists():
            rel_path = self._normalized_rel_path(self._path, basepath)
            command = "cd %s; bzr diff %s"%(basepath, rel_path)
            command += " -p1 --prefix %s/:%s/"%(rel_path,rel_path)
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
            command = "cd %s; bzr status %s -S"%(basepath, rel_path)
            if not untracked:
                command += " -V"
            stdout_handle = os.popen(command, "r")
            response = stdout_handle.read()
            response_processed = ""
            for line in response.split('\n'):
                if len(line.strip()) > 0:
                    response_processed+=line[0:4]+rel_path+'/'+line[4:]+'\n'
            response = response_processed
        return response

BZRClient=BzrClient
