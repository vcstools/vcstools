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

refnames in git can be branchnames, hashes, partial hashes, tags. On
checkout, git will disambiguate by checking them in that order, taking the first that applies

This class aims to provide git for linear centralized workflows.
This means we assume that the only relevant remote is the one named "origin",
and we assume that commits once on origin remain on origin.

A challenge with git is that it has strong reasonable
conventions, but is very allowing for breaking them. E.g. it is
possible to name remotes and branches with names like
"refs/heads/master", give branches and tags the same name, or a valid
SHA-ID as name, etc.  Similarly git allows plenty of ways to reference
any object, in cae of ambiguities, git attempts to take the most
reasonable disambiguation, and in some cases warns.
"""

import subprocess
import os
import base64 
import sys
from distutils.version import LooseVersion

from .vcs_base import VcsClientBase


class GitClient(VcsClientBase):
    def __init__(self, path):
        """
        Raise LookupError if git not detected
        """
        VcsClientBase.__init__(self, 'git', path)
        with open(os.devnull, 'w') as fnull:
            try:
                version = subprocess.Popen(['git --version'], shell=True, stdout=subprocess.PIPE).communicate()[0]
            except:
                raise LookupError("git not installed, cannot create a git vcs client")
            if version.startswith('git version '):
                version = version[len('git version '):].strip()
            else:
                raise LookupError("git --version command returned invalid string: '%s'"%version)
            self.gitversion = version
        self.submodule_exists = self._check_git_submodules()

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

    def checkout(self, url, refname=None):
        """calls git clone and then, if refname was given, update(refname)"""
        if self.path_exists():
            sys.stderr.write("Error: cannot checkout into existing directory\n")
            return False
        
        #since we cannot know whether refname names a branch, clone master initially
        cmd = "git clone --recursive %s %s"%(url, self._path)
        if not subprocess.call(cmd, shell=True) == 0:
            return False

        if refname != None and refname != "master":
            return self.update(refname)
        else:
            return True
        
    def update_submodules(self):
    
        # update and or init submodules too
        if self.submodule_exists:
            cmd = "git submodule update --init --recursive"
            if not subprocess.call(cmd, cwd=self._path, shell=True) == 0:
                return False
        return True

    def update(self, refname=None):
        """interprets refname as a local branch, remote branch, tagname, hash, etc.
        If it is a branch, attempts to move to it unless already on it, and to fast-forward, unless not a tracking branch.
        Else go untracked on tag or whatever refname is. Does not leave if current commit would become dangling."""
        # try calling git fetch just once per call to update()
        need_to_fetch = True
        if not self.detect_presence():
            return False

        # are we on any branch?
        current_branch = self.get_branch()
        if current_branch:
            branch_parent = self.get_branch_parent(need_to_fetch)
            need_to_fetch = False
        else:
            branch_parent = None

        if refname == None or refname.strip() == '':
            refname = branch_parent
        if refname == None:
            # we are neither tracking, nor did we get any refname to update to
            return self.update_submodules()

        # local branch might be named differently from remote by user, we respect that
        same_branch = (refname == branch_parent) or (refname == current_branch)

        # if same_branch and branch_parent == None:
        #   already on branch, nothing to pull as non-tracking branch
        if same_branch and branch_parent != None:
            if not self._do_fast_forward(need_to_fetch):
                return False
            need_to_fetch = False
        elif not same_branch:
            # refname can be a different branch or something else than a branch
            
            refname_is_local_branch = self.is_local_branch(refname)
            if refname_is_local_branch == True:
                # might also be remote branch, but we treat it as local
                refname_is_remote_branch = False
            else:
                refname_is_remote_branch = self.is_remote_branch(refname, fetch = need_to_fetch)
                need_to_fetch = False
            refname_is_branch = refname_is_remote_branch or refname_is_local_branch

            # shortcut if version is the same as requested
            if not refname_is_branch and self.get_version() == refname:
                return self.update_submodules()
            
            if current_branch == None:
                current_version = self.get_version()
                # prevent commit from becoming dangling
                if self.is_commit_in_orphaned_subtree(current_version, fetch = need_to_fetch):
                    # commit becomes dangling unless we move to one of its descendants
                    if not self.rev_list_contains(refname, [current_version], fetch = False):
                        # TODO: should raise error instead of printing message
                        print "vcstools refusing to move away from dangling commit, to protect your work."
                        return False
                need_to_fetch = False

            # git checkout makes all the decisions for us
            self._do_checkout(refname, fetch = need_to_fetch)
            need_to_fetch = False
            
            if refname_is_local_branch:
                # if we just switched to a local tracking branch (not created one), we should also fast forward
                new_branch_parent = self.get_branch_parent(fetch = need_to_fetch)
                if new_branch_parent != None:
                    if not self._do_fast_forward(fetch = need_to_fetch):
                        return False
            
        return self.update_submodules()
    
    def get_version(self, spec=None, fetch = True):
        """
        @param spec: (optional) token to identify desired version. For
        git, this may be anything accepted by git log, e.g. a tagname,
        branchname, or sha-id.
        @param fetch: When spec is given, can be used to suppress git fetch call
        
        @return: current SHA-ID of the repository. Or if spec is
        provided, the SHA-ID of a commit specified by some token.
        """
        if self.detect_presence():
            command = ['git', 'log', "-1", "--format='%H'"]
            if spec is not None:
                if fetch:
                    self._do_fetch()
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


    def is_remote_branch(self, branch_name, fetch = True):
        """
        checks list of remote branches for match. Set fetch to False if you just fetched already.
        """
        if self.path_exists():
            if fetch and not self._do_fetch():
                return False
            output = subprocess.Popen(['git branch -r'], shell=True, cwd= self._path, stdout=subprocess.PIPE).communicate()[0]
            for l in output.splitlines():
                elem = l.split()[0]
                rem_name = elem[:elem.find('/')]
                br_name = elem[elem.find('/') + 1:]
                if rem_name == "origin" and br_name == branch_name:
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


    def get_branch_parent(self, fetch=False):
        """return the name of the branch this branch tracks, if any"""
        if self.path_exists():
            # get name of configured merge ref.
            output = subprocess.Popen(['git config --get-all branch.%s.merge'%self.get_branch()], shell=True, cwd= self._path, stdout=subprocess.PIPE).communicate()[0].strip()
            if not output:
                return None
            lines = output.splitlines()
            if len(lines) > 1:
                print "vcstools unable to handle multiple merge references for branch %s:\n%s"%(self.get_branch(), output)
                return None
            # get name of configured remote
            output2 = subprocess.Popen(['git config --get-all branch.%s.remote'%self.get_branch()], shell=True, cwd= self._path, stdout=subprocess.PIPE).communicate()[0].strip()
            if output2 != "origin":
                print "vcstools only handles branches tracking remote 'origin', branch '%s' tracks remote '%s'"%(self.get_branch(), output2)
                return None
            output = lines[0]
            # output is either refname, or /refs/heads/refname, or heads/refname
            # we would like to return refname
            # however, user could also have named any branch "/refs/heads/refname", for some unholy reason
            # check all known branches on remote for refname, then for the odd cases, as git seems to do
            candidate = output
            if candidate.startswith('refs/'):
                candidate = candidate[len('refs/'):]
            if candidate.startswith('heads/'):
                candidate = candidate[len('heads/'):]
            elif candidate.startswith('tags/'):
                candidate = candidate[len('tags/'):]
            elif candidate.startswith('remotes/'):
                candidate = candidate[len('remotes/'):]
            if self.is_remote_branch(candidate, fetch=fetch):
                return candidate
            if output != candidate and self.is_remote_branch(output, fetch=False):
                return output
        return None


    def is_tag(self, tag_name, fetch = True):
        """
        checks list of tags for match. Set fetch to False if you just fetched already.
        """
        if fetch:
            self._do_fetch()
        if self.path_exists():
            output = subprocess.Popen(['git tag -l %s'%tag_name], shell=True, cwd= self._path, stdout=subprocess.PIPE).communicate()[0]
            lines =  output.splitlines()
            if len(lines) == 1:
                return True
        return False


    def rev_list_contains(self, refname, version, fetch = True):
        """
        calls git rev-list with refname and returns True if version can be found in rev-list result
        @param refname a git refname
        @param version an SHA IDs (if partial, caller is responsible for mismatch)
        @returns
        """
        # to avoid listing unnecessarily many rev-ids, we cut off all
        # those we are definitely not interested in
        # $ git rev-list foo bar ^baz ^bez
        # means "list all the commits which are reachable from foo or
        # bar, but not from baz or bez". We use --parents because
        # ^baz also excludes baz itself. We could also use git
        # show --format=%P to get all parents first and use that,
        # not sure what's more performant
        if fetch == True:
            self._do_fetch()
        if refname != None and refname != '' and version!=None and version!='':
            output = subprocess.Popen(['git rev-list %s ^%s --parents'%(refname, version)], shell=True, cwd= self._path, stdout=subprocess.PIPE).communicate()[0]
            #print "revlist", refname, versionlist, output
            for line in output.splitlines():
                # can have 1, 2 or 3 elements (commit, parent1, parent2)
                for hash in line.split(" "):
                    if hash.startswith(version):
                        return True
        return False


    def is_commit_in_orphaned_subtree(self, version, mask_self = False, fetch = True):
        """
        checks git log --all (the list of all commits reached by
        references, meaning branches or tags) for version. If it shows
        up, that means git garbage collection will not remove the
        commit. Else it would eventually be deleted.
        @param version SHA IDs (if partial, caller is responsible for mismatch)
        @param mask_self whether to consider direct references to this commit (rather than only references on descendants) as well
        @param fetch whether fetch should be done first for remote refs
        @return true if version is not recursively referenced by a branch or tag
        """
        if version != None and version != '':
            cmd = 'git show-ref -s'
            output = subprocess.Popen([cmd], shell=True, cwd= self._path, stdout=subprocess.PIPE).communicate()[0]
            refs = output.splitlines()
            # git log over all refs except HEAD
            cmd = 'git log '+ " ".join(refs)
            if mask_self == True:
                # %P: parent hashes
                cmd += " --pretty=format:%P"
            else:
                # %H: commit hash
                cmd += " --pretty=format:%H"
            output = subprocess.Popen([cmd], shell=True, cwd= self._path, stdout=subprocess.PIPE).communicate()[0]
            count = 0
            for l in output.splitlines():
                if l.startswith(version):
                    return False
            return True
        return False

    def _check_git_submodules(self):
        """
        @return: True if git version supports submodules, False otherwise,
        including if version cannot be detected
        """
        # 'git version 1.7.0.4\n'
        return LooseVersion(self.gitversion) > LooseVersion('1.7')


    def _do_fetch(self):
        if not subprocess.call("git fetch", cwd=self._path, shell=True) == 0:
            return False
        return True


    def _do_fast_forward(self, fetch = True):
        """Execute git fetch if necessary, and if we can fast-foward,
        do so to the last fetched version using git rebase. Returns
        False on command line failures"""
        parent = self.get_branch_parent(fetch = fetch)
        if parent != None and self.rev_list_contains("remotes/origin/%s"%parent, self.get_version(), fetch = False):
            # Rebase, do not pull, because somebody could have
            # commited in the meantime.
            if LooseVersion(self.gitversion) >= LooseVersion('1.7.1'):
                # --keep allows o rebase even with local changes, as long as
                # local changes are not in files that change between versions
                cmd = "git reset --keep remotes/origin/%s"%parent
                if subprocess.call(cmd, cwd=self._path, shell=True) == 0:
                    return True
            else:
                # prior to version 1.7.1, git does not know --keep
                # Do not merge, rebase does nothing when there are local changes
                cmd = "git rebase remotes/origin/%s"%parent
                if subprocess.call(cmd, cwd=self._path, shell=True) == 0:
                    return True
            return False
        return True


    def _do_checkout(self, refname, fetch = True):
        """meaning git checkout, not vcstools checkout. This works
        for local branches, remote branches, tagnames, hashes, etc.
        git will create local branch of same name when no such local
        branch exists, and also setup tracking. Git decides with own
        rules whether local changes would cause conflicts, and refuses
        to checkout else."""
        # since refname may relate to remote branch / tag we do not know about yet, do fetch if not already done
        if fetch == True:
            self._do_fetch()
        cmd = "git checkout %s"%(refname)
        if not subprocess.call(cmd, cwd=self._path, shell=True) == 0:
            return False
        return True

GITClient=GitClient
