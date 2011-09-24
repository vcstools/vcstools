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
hg vcs support.

New in ROS C-Turtle.
"""

import os
import subprocess
import sys
import string

from .vcs_base import VcsClientBase

#hg diff cannot seem to be persuaded to accept a different prefix for filenames
def _hg_diff_path_change(diff, path):
    """
    Parses hg diff result and changes the filename prefixes.
    """
    if diff == None:
        return None
    INIT = 0
    INDIFF = 1
    # small state machine makes sure we never touch anything inside the actual diff
    state = INIT
    result = ""
    s_list = [line for line in diff.split(os.linesep)]
    for line in s_list:
        newline = line
        if line.startswith("diff"):
            state = INIT
        if state == INIT:
            if line.startswith("@@"):
                state = INDIFF
            else:
                if line.startswith("---") and not line.startswith("--- /dev/null"):
                    newline = "--- " + path + line[5:]
                if line.startswith("+++") and not line.startswith("+++ /dev/null"):
                    newline = "+++ " + path + line[5:]
                if line.startswith("diff --git"):
                    # first replacing b in case path starts with a/
                    newline = string.replace(line, " b/", " " + path + "/", 1)
                    newline = string.replace(newline, " a/", " " + path + "/", 1)
        result += newline + '\n'
    return result

class HgClient(VcsClientBase):
        
    def __init__(self, path):
        """
        Raise LookupError if hg not detected
        """
        VcsClientBase.__init__(self, 'hg', path)
        with open(os.devnull, 'w') as fnull:
            try:
                subprocess.call("hg help".split(), stdout=fnull, stderr=fnull)
            except:
                raise LookupError("hg not installed, cannot create a hg vcs client")

    def get_url(self):
        """
        @return: HG URL of the directory path (output of hg paths command), or None if it cannot be determined
        """
        if self.detect_presence():
            output = subprocess.Popen(["hg", "paths", "default"], cwd=self._path, stdout=subprocess.PIPE).communicate()[0]
            return output.rstrip()
        return None

    def detect_presence(self):
        return self.path_exists() and os.path.isdir(os.path.join(self._path, '.hg'))

    def checkout(self, url, version=''):
        if self.path_exists():
            sys.stderr.write("Error: cannot checkout into existing directory\n")
            return False

        # make sure that the parent directory exists for #3497
        base_path = os.path.split(self.get_path())[0]
        try:
            os.makedirs(base_path) 
        except OSError, ex:
            # OSError thrown if directory already exists this is ok
            pass
        
        cmd = "hg clone %s %s"%(url, self._path)
        if not subprocess.call(cmd, shell=True) == 0:
            return False
        cmd = "hg checkout %s"%(version)
        if not subprocess.call(cmd, cwd=self._path, shell=True) == 0:
            return False
        return True

    def update(self, version=''):
        if not self.detect_presence():
            return False
        cmd = "hg pull"
        if not subprocess.call(cmd, cwd=self._path, shell=True) == 0:
            return False
        cmd = "hg checkout %s"%version
        if not subprocess.call(cmd, cwd=self._path, shell=True) == 0:
            return False
        return True

    def get_version(self, spec=None):
        """
        @param spec: (optional) token for identifying version. spec can be
        a whatever is allowed by 'hg log -r', e.g. a tagname, sha-ID,
        revision-number

        @return the current SHA-ID of the repository. Or if spec is
        provided, the SHA-ID of a revision specified by some
        token.
        """
        # detect presence only if we need path for cwd in popen
        if self.detect_presence() and spec != None:
            command = ['hg', 'log', '-r', spec, '.']
            output = subprocess.Popen(command, cwd= self._path, stdout=subprocess.PIPE).communicate()[0]
            if output == None or output.strip() == '' or output.startswith("abort"):
                return None
            else:
                 matches = [l for l in output.split('\n') if l.startswith('changeset: ')]
                 if len(matches) == 1:
                     return matches[0].split(':')[2]
        else:
            command = ['hg', 'identify', "-i", self._path]            
            output = subprocess.Popen(command, stdout=subprocess.PIPE).communicate()[0]
            # hg adds a '+' to the end if there are uncommited changes, inconsistent to hg log
            return output.strip().rstrip('+')
        
    def get_diff(self, basepath=None):
        response = None
        if basepath == None:
            basepath = self._path
        if self.path_exists():
            rel_path = self._normalized_rel_path(self._path, basepath)
            command = "cd %s; hg diff -g %s"%(basepath, rel_path)
            stdout_handle = os.popen(command, "r")
            response = stdout_handle.read()
            response = _hg_diff_path_change(response, rel_path)
        if response != None and response.strip() == '':
            response = None
        return response


    def get_status(self, basepath=None, untracked=False):
        response=None
        if basepath == None:
            basepath = self._path
        if self.path_exists():
            rel_path = self._normalized_rel_path(self._path, basepath)
            command = "cd %s; hg status %s"%(basepath, rel_path)
            if not untracked:
                command += " -mard"
            stdout_handle = os.popen(command, "r")
            response = stdout_handle.read()
            response_processed = ""
            for line in response.split('\n'):
                if len(line.strip()) > 0:
                    response_processed+=line[0:2]+line[2:]+'\n'
            response = response_processed
        return response

# backwards compat
HGClient = HgClient
