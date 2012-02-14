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
from distutils.version import LooseVersion

_mercurial_missing = False
try:
    import mercurial
    import mercurial.util
    from mercurial import ui, hg, commands
except:
    _mercurial_missing = True
    
from .vcs_base import VcsClientBase, VcsError

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

class HackedHgUI():
    """This class modifies a given mercurial.ui object by substituing
    the write method, so that the output is stored in a variable."""
    def __init__(self, ui):
        self.output = ''
        ui.write = self.write

    def write(self, output, label = None):
        # label param required for later mercurial versions
        self.output += output

        
class HgClient(VcsClientBase):
        
    def __init__(self, path):
        """
        :raises: VcsError if hg not detected
        """
        VcsClientBase.__init__(self, 'hg', path)
        if _mercurial_missing:
            raise VcsError("Mercurial libs could not be imported. Please install mercurial. On debian systems sudo apt-get install mercurial")

    @staticmethod
    def get_environment_metadata():
        metadict = {}
        try:
            import mercurial.util
            metadict["version"] = '%s'%str(mercurial.util.version())
        except:
            metadict["version"] = "no mercurial installed"
        return metadict
   
    def get_url(self):
        """
        :returns: HG URL of the directory path (output of hg paths command), or None if it cannot be determined
        """
        r =  self._get_hg_repo(self._path)
        if r is None:
            return None
        r = hg.repository(ui = ui.ui(), path = self._path)
        for name, path in r.ui.configitems("paths"):
            if name == 'default':
                return path
        return None

    def detect_presence(self):
        try:
            hg.repository(ui = ui.ui(), path = self._path)
            return True
        except mercurial.error.RepoError:
            return False

    def checkout(self, url, version=None):
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
        try:
            if version == None or version.strip() == '':
                version = True # means default
            if LooseVersion(mercurial.util.version()) >= LooseVersion("1.9"):
                hg.clone(ui = ui.ui(),
                         peeropts = {}, # new in 1.9
                         source = url,
                         dest = self._path,
                         update = version)
            else:
                hg.clone(ui = ui.ui(),
                         source = url,
                         dest = self._path,
                         update = version)
            return True
        except mercurial.error.RepoError as e:
            sys.stderr.write("RepoError during checkout version %s from %s : %s\n"%(str(version), url, str(e)))
            return False
        except Exception as e:
            sys.stderr.write("Failed to checkout version %s from url %s : %s\n"%(str(version), url, str(e)))
            return False

    def update(self, version=None):
        try:
            r =  self._get_hg_repo(self._path)
            if r is None:
                return None
            commands.pull(ui = r.ui, repo = r)
            hg.update(repo = r, node = version)
            return True
        except mercurial.error.RepoError as e:
            sys.stderr.write("RepoError during pull/update : %s\n"%str(e))
            return False
        except Exception as e:
            sys.stderr.write("Failed to pull/update : %s\n"%str(e))
            return False
        
    def get_version(self, spec=None):
        """
        :param spec: (optional) token for identifying version. spec can be
        a whatever is allowed by 'hg log -r', e.g. a tagname, sha-ID,
        revision-number

        :returns: the current SHA-ID of the repository. Or if spec is
        provided, the SHA-ID of a revision specified by some
        token.
        """
        r =  self._get_hg_repo(self._path)
        if r is None:
            return None
        fakeui = HackedHgUI(r.ui)
        commands.identify(ui = r.ui, repo = r, rev=spec)
        result = fakeui.output
        shaid = result.splitlines()[0].split()[0].rstrip('+')
        return shaid
        
    def get_diff(self, basepath=None):
        if basepath == None:
            basepath = self._path

        rel_path = self._normalized_rel_path(self._path, basepath)
        # command returns None, prints result to ui object
        r =  self._get_hg_repo(self._path)
        if r is None:
            return None
        fakeui = HackedHgUI(r.ui)
        commands.diff(ui = r.ui, repo = r, git = True)
        response = fakeui.output
        if response is not None and response.strip() == '':
            response = None
        if response is None:
            return None
        response = _hg_diff_path_change(response, rel_path)
        return response
        

    def get_status(self, basepath=None, untracked=False):
        response=None
        if basepath == None:
            basepath = self._path
        if self.path_exists():
            r =  self._get_hg_repo(self._path)
            if r is None:
                return None
            fakeui = HackedHgUI(r.ui)
            commands.status(ui = r.ui,
                            repo = r,
                            git = True,
                            modified = not untracked,
                            added=not untracked,
                            removed=not untracked,
                            deleted=not untracked)
            response = fakeui.output
            response_processed = ""
            rel_path = self._normalized_rel_path(self._path, basepath)
            if rel_path == '.':
                rel_path = ''
            else:
                rel_path +='/'
            for line in response.split('\n'):
                if len(line.strip()) > 0:
                    response_processed+=line[0:2]+rel_path+line[2:]+'\n'
            response = response_processed
        return response

    def _get_hg_repo(self, path):
        try:
            return hg.repository(ui = ui.ui(), path = path)
        except mercurial.error.RepoError:            
            sys.stderr.write("No hg repo at : %s\n"%self._path)
            return None

# backwards compat
HGClient = HgClient
