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
git vcs support.

New in ROS C-Turtle.
"""

import subprocess
import os
import base64 
import sys
from distutils.version import LooseVersion

from .vcs_base import VcsClientBase

branch_name = "rosinstall_tagged_branch"

def check_git_submodules():
    """
    @return: True if git version supports submodules, False otherwise,
    including if version cannot be detected
    """
    try:
        version = subprocess.Popen(['git --version'], shell=True, stdout=subprocess.PIPE).communicate()[0]
    except:
        return False
   # 'git version 1.7.0.4\n'
    if version.startswith('git version '):
        version = version[len('git version '):].strip()
    else:
        return False
    return LooseVersion(version) > LooseVersion('1.7')

class GitClient(VcsClientBase):
    def __init__(self, path):
        """
        Raise LookupError if git not detected
        """
        VcsClientBase.__init__(self, 'git', path)
        with open(os.devnull, 'w') as fnull:
            try:
                subprocess.call("git help".split(), stdout=fnull, stderr=fnull)
            except:
                raise LookupError("git not installed, cannot create a git vcs client")

        self.submodule_exists = check_git_submodules()

    def get_url(self):
        """
        @return: GIT URL of the directory path (output of git info command), or None if it cannot be determined
        """
        if self.detect_presence():
            output = subprocess.Popen(["git config --get remote.origin.url"], shell=True, cwd=self._path, stdout=subprocess.PIPE).communicate()[0]
            return output.rstrip()
        return None

    def detect_presence(self):
        return self.path_exists() and os.path.isdir(os.path.join(self._path, '.git'))

    def checkout(self, url, version='master'):
        if self.path_exists():
            sys.stderr.write("Error: cannot checkout into existing directory\n")
            return False
            
        cmd = "git clone %s %s"%(url, self._path)
        if not subprocess.call(cmd, shell=True) == 0:
            return False

        # update submodules early to work around what appears to be a git bug noted in #3251
        if not self.update_submodules():
            return False

        if self.get_branch_parent() == version:
            # If already at the right version update submodules and return
            return self.update_submodules()
        elif self.is_remote_branch(version):  # remote branch
            cmd = "git checkout remotes/origin/%s -b %s"%(version, version)
        else:  # tag or hash
            cmd = "git checkout %s -b %s"%(version, branch_name)
        if not self.is_hash(version) and not self.is_tag(version):
            cmd = cmd + " --track"
        #print "Git Installing: %s"%cmd
        if not subprocess.call(cmd, cwd=self._path, shell=True) == 0:
            return False
        
        # update submodules if present and available
        return self.update_submodules()
        
    def update_submodules(self):
    
        # update and or init submodules too
        if self.submodule_exists:
            cmd = "git submodule update --init --recursive"
            if not subprocess.call(cmd, cwd=self._path, shell=True) == 0:
                return False
        return True

    def update(self, version='master'):
        if not self.detect_presence():
            return False
        
        # shortcut if version is the same as requested
        if self.is_hash(version) :
            if self.get_version() == version:
                return self.update_submodules()

            cmd = "git checkout -f -b rosinstall_temp" 
            if not subprocess.call(cmd, cwd=self._path, shell=True) == 0:
                return False
            cmd = "git fetch"
            if not subprocess.call(cmd, cwd=self._path, shell=True) == 0:
                return False
            cmd = "git branch -D %s"%branch_name
            if not subprocess.call(cmd, cwd=self._path, shell=True) == 0:
                pass # OK to fail return False
            cmd = "git checkout %s -f -b %s"%(version, branch_name)
            if not subprocess.call(cmd, cwd=self._path, shell=True) == 0:
                return False
            cmd = "git branch -D rosinstall_temp"
            if not subprocess.call(cmd, cwd=self._path, shell=True) == 0:
                return False
        else:     # must be a branch name
            if self.get_branch_parent() != version:
                #cannot update if branch has changed
                return False
            cmd = "git pull"
            if not subprocess.call(cmd, cwd=self._path, shell=True) == 0:
                return False
            # update submodules too
            if self.submodule_exists:
                cmd = "git submodule update --init --recursive"
                if not subprocess.call(cmd, cwd=self._path, shell=True) == 0:
                    return False
        return self.update_submodules()

    def get_version(self, spec=None):
        """
        @param spec: (optional) token to identify desired version. For
        git, this may be anything accepted by git log, e.g. a tagname,
        branchname, or sha-id.
        
        @return: current SHA-ID of the repository. Or if spec is
        provided, the SHA-ID of a commit specified by some token.
        """
        if self.detect_presence():
            command = ['git', 'log', "-1", "--format='%H'"]
            if spec is not None:
                command.insert(3, spec)
            output = subprocess.Popen(' '.join(command), shell=True, cwd= self._path, stdout=subprocess.PIPE).communicate()[0]
            output = output.strip().strip("'")
            return output

    def get_diff(self, basepath=None):
        response = None
        if basepath == None:
            basepath = self._path
        if self.path_exists():
            rel_path = self._normalized_rel_path(self._path, basepath)
            # git needs special treatment as it only works from inside
            # use HEAD to also show staged changes. Maybe should be option?
            command = "cd %s; git diff HEAD"%(self._path)
            # change path using prefix
            command += " --src-prefix=%s/ --dst-prefix=%s/ ."%(rel_path,rel_path)
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
            # git command only works inside repo
            command = "cd %s; git status -s "%(self._path)
            if not untracked:
                command += " -uno"
            stdout_handle = os.popen(command, "r")
            response = stdout_handle.read()
            response_processed = ""
            for line in response.split('\n'):
                if len(line.strip()) > 0:
                    # prepend relative path
                    response_processed+=line[0:3]+rel_path+'/'+line[3:]+'\n'
            response = response_processed
        return response
        
    def is_remote_branch(self, branch_name):
        if self.path_exists():
            output = subprocess.Popen(['git branch -r'], shell=True, cwd= self._path, stdout=subprocess.PIPE).communicate()[0]
            for l in output.splitlines():
                elems = l.split()
                if len(elems) == 1:
                    br_names = elems[0].split('/')
                    if len(br_names) == 2 and br_names[0] == 'origin' and br_names[1] == branch_name:
                        return True
            return False

    def is_local_branch(self, branch_name):
        if self.path_exists():
            output = subprocess.Popen(['git branch'], shell=True, cwd= self._path, stdout=subprocess.PIPE).communicate()[0]
            for l in output.splitlines():
                elems = l.split()
                if len(elems) == 1:
                    if elems[0] == branch_name:
                        return True
                elif len(elems) == 2:
                    if elems[0] == '*' and elems[1] == branch_name:
                        return True
            return False

    def get_branch(self):
        if self.path_exists():
            output = subprocess.Popen(['git branch'], shell=True, cwd= self._path, stdout=subprocess.PIPE).communicate()[0]
            for l in output.splitlines():
                elems = l.split()
                if len(elems) == 2 and elems[0] == '*':
                    return elems[1]
            return None

    def get_branch_parent(self):
        if self.path_exists():
            output = subprocess.Popen(['git config --get branch.%s.merge'%self.get_branch()], shell=True, cwd= self._path, stdout=subprocess.PIPE).communicate()[0].strip()
            if not output:
                print "No output of get branch.%s.merge"%self.get_branch()
                return None
            elems = output.split('/')
            if len(elems) != 3 or elems[0] != 'refs' or (elems[1] != 'heads' and elems[1] != 'tags'):
                print "elems improperly formatted", elems
                return None
            else:
                return elems[2]

    def is_hash(self, hashstr):
        """
        Determine if the hashstr is a valid sha1 hash
        """
        if len(hashstr) == 40:
            try:
                base64.b64decode(hashstr)
                return True
            except Exception as ex:
                pass
        return False

    def is_tag(self, tag_name):
        if self.path_exists():
            output = subprocess.Popen(['git tag -l %s'%tag_name], shell=True, cwd= self._path, stdout=subprocess.PIPE).communicate()[0]
            lines =  output.splitlines()
            if len(lines) == 1:
                return True
            return False
        
GITClient=GitClient
