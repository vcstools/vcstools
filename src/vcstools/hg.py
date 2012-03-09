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

using ui object to redirect output into a string
"""

import os
import sys
import string
   
from vcs_base import VcsClientBase, VcsError, sanitized, normalized_rel_path, run_shell_command


def _get_hg_version():
    """Looks up hg version by calling hg --version.
    :raises: VcsError if hg is not installed"""
    try:
        _, output, _ = run_shell_command('hg --version', shell=True, us_env = True)
        if output is not None and len(output.splitlines()) > 0:
            version = output.splitlines()[0]
        else:
            raise VcsError("hg not installed")
    except:
        raise VcsError("hg not installed")
    return version

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

    s_list = [line for line in diff.split(os.linesep)]
    lines = []
    for line in s_list:
        if line.startswith("diff"):
            state = INIT
        if state == INIT:
            if line.startswith("@@"):
                state = INDIFF
                newline = line
            else:
                if line.startswith("---") and not line.startswith("--- /dev/null"):
                    newline = "--- %s%s"%(path, line[5:])
                elif line.startswith("+++") and not line.startswith("+++ /dev/null"):
                    newline = "+++ %s%s"%(path, line[5:])
                elif line.startswith("diff --git"):
                    # first replacing b in case path starts with a/
                    newline = string.replace(line, " b/", " " + path + "/", 1)
                    newline = string.replace(newline, " a/", " " + path + "/", 1)
                else:
                    newline = line
        else:
            newline = line
        if newline != '':
            lines.append(newline)
    result = "\n".join(lines)
    return result

        
class HgClient(VcsClientBase):
        
    def __init__(self, path):
        """
        :raises: VcsError if hg not detected
        """
        VcsClientBase.__init__(self, 'hg', path)
        _get_hg_version()

    @staticmethod
    def get_environment_metadata():
        metadict = {}
        try:
            import mercurial.util
            metadict["version"] = '%s'%_get_hg_version()
        except:
            metadict["version"] = "no mercurial installed"
        return metadict
   
    def get_url(self):
        """
        :returns: HG URL of the directory path (output of hg paths command), or None if it cannot be determined
        """
        if self.detect_presence():
            cmd = "hg paths default"
            _, output, _ = run_shell_command(cmd, shell=True, cwd=self._path, us_env = True)
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
        cmd = "hg clone %s %s"%(sanitized(url), self._path)
        value, _, _ = run_shell_command(cmd, shell=True)
        if value != 0:
            return False
        if version != None and version.strip() != '':
            cmd = "hg checkout %s"%sanitized(version)
            value, _, _ = run_shell_command(cmd, cwd=self._path, shell=True)
            if value != 0:
                return False
        return True

    def update(self, version = ''):
        if not self.detect_presence():
            sys.stderr.write("Error: cannot update non-existing directory\n")
            return True
        value, _, _ = run_shell_command("hg pull", cwd=self._path, shell=True)
        if value != 0:
            return False
        if version != None and version.strip() != '':
            cmd = "hg checkout %s"%sanitized(version)
        else:
            cmd = "hg update"
        value, _, _ = run_shell_command(cmd, cwd=self._path, shell=True)
        if value != 0:
            return False
        return True
        
    def get_version(self, spec=None):
        """
        :param spec: (optional) token for identifying version. spec can be
        a whatever is allowed by 'hg log -r', e.g. a tagname, sha-ID,
        revision-number

        :returns: the current SHA-ID of the repository. Or if spec is
        provided, the SHA-ID of a revision specified by some
        token.
        """
        # detect presence only if we need path for cwd in popen
        if spec != None and self.detect_presence():
            command = 'hg log -r %s'%sanitized(spec)
            _, output, _ = run_shell_command(command, shell=True, cwd=self._path, us_env = True)
            if output == None or output.strip() == '' or output.startswith("abort"):
                return None
            else:
                 matches = [l for l in output.split('\n') if l.startswith('changeset: ')]
                 if len(matches) == 1:
                     return matches[0].split(':')[2]
        else:
            command = 'hg identify -i %s'%self._path
            _, output, _ = run_shell_command(command, shell=True, us_env = True)
            if output == None or output.strip() == '' or output.startswith("abort"):
                return None
            # hg adds a '+' to the end if there are uncommited changes, inconsistent to hg log
            return output.strip().rstrip('+')
        
    def get_diff(self, basepath=None):
        response = None
        if basepath == None:
            basepath = self._path
        if self.path_exists():
            rel_path = normalized_rel_path(self._path, basepath)
            command = "hg diff -g %s"%(sanitized(rel_path))
            _, response, _ = run_shell_command(command, shell=True, cwd=basepath)
            response = _hg_diff_path_change(response, rel_path)
        return response

    def get_status(self, basepath=None, untracked=False):
        response=None
        if basepath == None:
            basepath = self._path
        if self.path_exists():
            rel_path = normalized_rel_path(self._path, basepath)
            # protect against shell injection
            command = "hg status %s"%(sanitized(rel_path))
            if not untracked:
                command += " -mard"
            _, response, _ = run_shell_command(command, shell=True, cwd=basepath)
            if response != None and response.startswith("abort"):
                raise VcsError("Probable Bug; Could not call %s, cwd=%s"%(command, basepath))
        return response

# backwards compat
HGClient = HgClient
