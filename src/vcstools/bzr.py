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

Important bzrlib types:

Revision - a snapshot of the files you're working with.
revision_id are globally unique. Revision numbers are local to a branch
Working tree - the directory containing your version-controlled files and sub-directories.
Branch - an ordered set of revisions that describe the history of a set of files (that which lies in .bzr)
Repository - a store of revisions.
A bzrdir is a filesystem directory.
A bzr RevisionSpec is something that may identify a revision.

workingtree and branch do not necessarily lie in the same directory (in contrast to e.g. git).
"""

import sys
_bzr_missing = False
try:
    import bzrlib
    import bzrlib.errors
    import bzrlib.branch
    import bzrlib.status
    import bzrlib.revisionspec
    import bzrlib.workingtree
except:
    _bzr_missing = True
from distutils.version import LooseVersion

from  .vcs_base import VcsClientBase, VcsError

class BzrClient(VcsClientBase):
    def __init__(self, path):
        """
        :raises: VcsError if bzr not detected
        """
        VcsClientBase.__init__(self, 'bzr', path)
        if _bzr_missing:
            raise VcsError("Bazaar libs could not be imported. Please install bazaar. On debian systems sudo apt-get install bzr")
        # required for any run_bzr command!
        bzrlib.commands.install_bzr_command_hooks()
        # required with e.g bzr 2.3.4 as workaround for some quirk
        # https://bugs.launchpad.net/bzr/+bug/930511
        bzrlib.commands.all_command_names()
        if LooseVersion(bzrlib.version_string) >= LooseVersion('2.2.0'):
            # not necessary in e.g 2.3.4 tests, but recommended by bzr docstrings
            bzrlib.initialize()
        
    @staticmethod
    def get_environment_metadata():
        metadict = {}
        try:
            import bzrlib
            metadict["version"] = '%s'%str(bzrlib.version_string)
        except:
            metadict["version"] = "no bzr installed"
        return metadict
        
    def get_url(self):
        """
        :returns: BZR URL of the branch (output of bzr info command), or None if it cannot be determined
        """
        try:
            branch = bzrlib.workingtree.WorkingTree.open(self._path).branch
            parent = str(branch.get_parent())
            if parent is not None and parent.strip() != '':
                prefix = 'file://'
                if parent.startswith(prefix):
                    parent = parent[len(prefix):]
                return str(parent.rstrip('/'))
        except bzrlib.errors.NotBranchError as e:
            sys.stderr.write("No bzr branch at %s : %s\n"%(self._path, str(e)))
        return None

    def detect_presence(self):
        try:
            bzrlib.workingtree.WorkingTree.open(self._path)
            return True
        except bzrlib.errors.NotBranchError as e:
            return False

    def checkout(self, url, version=None):
        if self.path_exists():
            sys.stderr.write("Error: cannot checkout into existing directory\n")
            return False
        argv=['branch', url, self._path]
        if version is not None:
            argv.extend(['-r', version])
        try:
            status = bzrlib.commands.run_bzr(argv)
            # not sure what status number could be else
            if status == 0:
                return True
        except bzrlib.errors.InvalidRevisionSpec:
            sys.stderr.write("Invalid revision: %s"%version)
        except bzrlib.errors.NotBranchError:
            sys.stderr.write("No bzr repo at: %s"%self._path)
        except bzrlib.errors.BzrCommandError as e:
            sys.stderr.write(str(e))
        return False

    def update(self, version=None):
        argv=['pull', '-d', self._path]
        if version is not None:
            argv.extend(['-r', version])
        try:
            status = bzrlib.commands.run_bzr(argv)
            # not sure what status number could be else
            if status == 0:
                return True
        except bzrlib.errors.InvalidRevisionSpec:
            sys.stderr.write("Invalid revision: %s"%version)
        except bzrlib.errors.NotBranchError:
            sys.stderr.write("No bzr repo at: %s"%self._path)
        except bzrlib.errors.BzrCommandError as e:
            sys.stderr.write(str(e))
        return False

    def get_version(self, spec=None):
        """
        @param spec: (optional) revisionspec of desired version.  May
        be any revisionspec as returned by 'bzr help revisionspec',
        e.g. a tagname or 'revno:<number>'
        
        :returns: the current revision number of the repository. Or if
        spec is provided, the number of a revision specified by some
        token. 
        """
        try:
            tree = bzrlib.workingtree.WorkingTree.open(self._path)
            branch = tree.branch
            if spec is None:
                spec = tree.last_revision() # not always same as branch.last_revision()
            rspec = bzrlib.revisionspec.RevisionSpec.from_string(spec)
            rev_id = rspec.as_revision_id(branch)
            # revision = branch.get_revision(rev_id) 
            rid_rno_map = branch.get_revision_id_to_revno_map()
            result = rid_rno_map.get(rev_id)
            if result is not None and len(result)>0:
                return str(result[0])
            else:
                return str(branch.revno())
        except bzrlib.errors.NotBranchError:
            sys.stderr.write("No bzr repo at:%s"%self._path)
        except bzrlib.errors.InvalidRevisionSpec:
            sys.stderr.write("Not a valid Revision:%s"%spec)
        return None

    def get_diff(self, basepath=None):
        if basepath == None:
            basepath = self._path
        if self.path_exists():
            rel_path = self._normalized_rel_path(self._path, basepath)

        argv=['diff', self._path, '-p1', '--prefix', "%s/:%s/"%(rel_path,rel_path)]
        try:
            from cStringIO import StringIO
            import sys
            old_stdout = sys.stdout
            # redirect stdout as the only means to get the diff
            sys.stdout = mystdout = StringIO()
            status = bzrlib.commands.run_bzr(argv)
            sys.stdout = old_stdout
            # for some reason, this returns always 1
            if status == 1:
                return mystdout.getvalue()
        except bzrlib.errors.InvalidRevisionSpec:
            sys.stdout = old_stdout
            sys.stderr.write("Invalid revision: %s"%version)
        except bzrlib.errors.NotBranchError:
            sys.stdout = old_stdout
            sys.stderr.write("No bzr repo at: %s"%self._path)
        except bzrlib.errors.BzrCommandError as e:
            sys.stdout = old_stdout
            sys.stderr.write(str(e))
        return None


    def get_status(self, basepath=None, untracked=False):
        if basepath == None:
            basepath = self._path
        if self.path_exists():
            rel_path = self._normalized_rel_path(self._path, basepath)
        versioned = not untracked
        try:

            from cStringIO import StringIO
            import sys
            old_stdout = sys.stdout
            # redirect stdout as the only means to get the diff
            sys.stdout = mystdout = StringIO()
            tree = bzrlib.workingtree.WorkingTree.open(self._path)
            bzrlib.status.show_tree_status(tree, short=True, versioned=versioned)
            sys.stdout = old_stdout
            response = mystdout.getvalue()
            response_processed = ""
            for line in response.split('\n'):
                if len(line.strip()) > 0:
                    response_processed+=line[0:4]+rel_path+'/'+line[4:]+'\n'
            response = response_processed
            return response
        except bzrlib.errors.InvalidRevisionSpec:
            sys.stdout = old_stdout
            sys.stderr.write("Invalid revision: %s"%version)
        except bzrlib.errors.NotBranchError:
            sys.stdout = old_stdout
            sys.stderr.write("No bzr repo at: %s"%self._path)
        except bzrlib.errors.BzrCommandError as e:
            sys.stdout = old_stdout
            sys.stderr.write(str(e))
        return None
    
BZRClient=BzrClient
