#!/usr/bin/env python
# Software License Agreement (BSD License)
#
# Copyright (c) 2009, Willow Garage, Inc.
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

from __future__ import absolute_import, print_function, unicode_literals

import os
import io
import unittest
import subprocess
import tempfile
import shutil
import types

from vcstools import GitClient
from vcstools.vcs_base import VcsError


class GitClientTestSetups(unittest.TestCase):

    @classmethod
    def setUpClass(self):
        self.root_directory = tempfile.mkdtemp()
        # helpful when setting tearDown to pass
        self.directories = dict(setUp=self.root_directory)
        self.remote_path = os.path.join(self.root_directory, "remote")
        self.local_path = os.path.join(self.root_directory, "ros")
        os.makedirs(self.remote_path)

        # create a "remote" repo
        subprocess.check_call("git init", shell=True, cwd=self.remote_path)
        subprocess.check_call("touch fixed.txt", shell=True, cwd=self.remote_path)
        subprocess.check_call("git add *", shell=True, cwd=self.remote_path)
        subprocess.check_call("git commit -m initial", shell=True, cwd=self.remote_path)
        subprocess.check_call("git tag test_tag", shell=True, cwd=self.remote_path)
        # other branch
        subprocess.check_call("git branch test_branch", shell=True, cwd=self.remote_path)

        po = subprocess.Popen("git log -n 1 --pretty=format:\"%H\"", shell=True, cwd=self.remote_path, stdout=subprocess.PIPE)
        self.readonly_version_init = po.stdout.read().decode('UTF-8').rstrip('"').lstrip('"')

        # files to be modified in "local" repo
        subprocess.check_call("touch modified.txt", shell=True, cwd=self.remote_path)
        subprocess.check_call("touch modified-fs.txt", shell=True, cwd=self.remote_path)
        subprocess.check_call("git add *", shell=True, cwd=self.remote_path)
        subprocess.check_call("git commit -m initial", shell=True, cwd=self.remote_path)
        po = subprocess.Popen("git log -n 1 --pretty=format:\"%H\"", shell=True, cwd=self.remote_path, stdout=subprocess.PIPE)
        self.readonly_version_second = po.stdout.read().decode('UTF-8').rstrip('"').lstrip('"')

        subprocess.check_call("touch deleted.txt", shell=True, cwd=self.remote_path)
        subprocess.check_call("touch deleted-fs.txt", shell=True, cwd=self.remote_path)
        subprocess.check_call("git add *", shell=True, cwd=self.remote_path)
        subprocess.check_call("git commit -m modified", shell=True, cwd=self.remote_path)
        po = subprocess.Popen("git log -n 1 --pretty=format:\"%H\"", shell=True, cwd=self.remote_path, stdout=subprocess.PIPE)
        self.readonly_version = po.stdout.read().decode('UTF-8').rstrip('"').lstrip('"')
        subprocess.check_call("git tag last_tag", shell=True, cwd=self.remote_path)

    @classmethod
    def tearDownClass(self):
        for d in self.directories:
            shutil.rmtree(self.directories[d])

    def tearDown(self):
        if os.path.exists(self.local_path):
            shutil.rmtree(self.local_path)


class GitClientTest(GitClientTestSetups):

    def test_get_url_by_reading(self):
        url = self.remote_path
        client = GitClient(self.local_path)
        self.assertFalse(client.path_exists())
        self.assertFalse(client.detect_presence())
        self.assertTrue(client.checkout(url))
        self.assertTrue(client.path_exists())
        self.assertTrue(client.detect_presence())
        self.assertEqual(client.get_url(), self.remote_path)
        self.assertEqual(client.get_version(), self.readonly_version)
        self.assertEqual(client.get_version(self.readonly_version_init[0:6]), self.readonly_version_init)
        self.assertEqual(client.get_version("test_tag"), self.readonly_version_init)
        # private functions
        self.assertFalse(client.is_local_branch("test_branch"))
        self.assertTrue(client.is_remote_branch("test_branch"))
        self.assertTrue(client.is_tag("test_tag"))
        self.assertFalse(client.is_remote_branch("test_tag"))
        self.assertFalse(client.is_tag("test_branch"))

    def test_get_url_nonexistant(self):
        # local_path = "/tmp/dummy"
        client = GitClient(self.local_path)
        self.assertEqual(client.get_url(), None)

    def test_get_type_name(self):
        # local_path = "/tmp/dummy"
        client = GitClient(self.local_path)
        self.assertEqual(client.get_vcs_type_name(), 'git')

    def test_checkout(self):
        url = self.remote_path
        client = GitClient(self.local_path)
        self.assertFalse(client.path_exists())
        self.assertFalse(client.detect_presence())
        self.assertTrue(client.checkout(url))
        self.assertTrue(client.path_exists())
        self.assertTrue(client.detect_presence())
        self.assertEqual(client.get_path(), self.local_path)
        self.assertEqual(client.get_url(), url)
        self.assertEqual(client.get_branch(), "master")
        self.assertEqual(client.get_branch_parent(), "master")
        #self.assertEqual(client.get_version(), '-r*')

    def test_checkout_dir_exists(self):
        url = self.remote_path
        client = GitClient(self.local_path)
        self.assertFalse(client.path_exists())
        os.makedirs(self.local_path)
        self.assertTrue(client.checkout(url))
        # non-empty
        self.assertFalse(client.checkout(url))

    def test_checkout_no_unnecessary_updates(self):
        client = GitClient(self.local_path)
        client.fetches = 0
        client.submodules = 0
        client.fast_forwards = 0
        def ifetch(self):
            self.fetches +=1
            return True
        def iff(self, fetch=True, branch_parent=None, verbose=False):
            self.fast_forwards +=1
            return True
        def isubm(self, verbose=False):
            self.submodules +=1
            return True
        client._do_fetch = types.MethodType(ifetch, client)
        client._do_fast_forward = types.MethodType(iff, client)
        client.update_submodules = types.MethodType(isubm, client)
        url = self.remote_path
        self.assertFalse(client.path_exists())
        self.assertFalse(client.detect_presence())
        self.assertTrue(client.checkout(url))
        self.assertEqual(0, client.submodules)
        self.assertEqual(0, client.fetches)
        self.assertEqual(0, client.fast_forwards)
        self.assertTrue(client.update())
        self.assertEqual(1, client.submodules)
        self.assertEqual(1, client.fetches)
        self.assertEqual(1, client.fast_forwards)
        self.assertTrue(client.update('test_branch'))
        self.assertEqual(2, client.submodules)
        self.assertEqual(2, client.fetches)
        self.assertEqual(1, client.fast_forwards)
        self.assertTrue(client.update('test_branch'))
        self.assertEqual(3, client.submodules)
        self.assertEqual(3, client.fetches)
        self.assertEqual(2, client.fast_forwards)

    def test_checkout_no_unnecessary_updates_other_branch(self):
        client = GitClient(self.local_path)
        client.fetches = 0
        client.submodules = 0
        client.fast_forwards = 0
        def ifetch(self):
            self.fetches +=1
            return True
        def iff(self, fetch=True, branch_parent=None, verbose=False):
            self.fast_forwards +=1
            return True
        def isubm(self, verbose=False):
            self.submodules +=1
            return True
        client._do_fetch = types.MethodType(ifetch, client)
        client._do_fast_forward = types.MethodType(iff, client)
        client.update_submodules = types.MethodType(isubm, client)
        url = self.remote_path
        self.assertFalse(client.path_exists())
        self.assertFalse(client.detect_presence())
        self.assertTrue(client.checkout(url, 'test_branch'))
        self.assertEqual(1, client.submodules)
        self.assertEqual(0, client.fetches)
        self.assertEqual(0, client.fast_forwards)

    def test_checkout_shallow(self):
        url = 'file://' + self.remote_path
        client = GitClient(self.local_path)
        self.assertFalse(client.path_exists())
        self.assertFalse(client.detect_presence())
        self.assertTrue(client.checkout(url, shallow=True))
        self.assertTrue(client.path_exists())
        self.assertTrue(client.detect_presence())
        self.assertEqual(client.get_path(), self.local_path)
        self.assertEqual(client.get_url(), url)
        self.assertEqual(client.get_branch(), "master")
        self.assertEqual(client.get_branch_parent(), "master")
        po = subprocess.Popen("git log --pretty=format:%H", shell=True, cwd=self.local_path, stdout=subprocess.PIPE)
        log = po.stdout.read().decode('UTF-8').splitlines()
        # shallow only contains last 2 commits
        self.assertEqual(2, len(log), log)

    def test_checkout_specific_version_and_update(self):
        url = self.remote_path
        version = self.readonly_version
        client = GitClient(self.local_path)
        self.assertFalse(client.path_exists())
        self.assertFalse(client.detect_presence())
        self.assertTrue(client.checkout(url, version))
        self.assertTrue(client.path_exists())
        self.assertTrue(client.detect_presence())
        self.assertEqual(client.get_path(), self.local_path)
        self.assertEqual(client.get_url(), url)
        self.assertEqual(client.get_version(), version)

        new_version = self.readonly_version_second
        self.assertTrue(client.update(new_version))
        self.assertEqual(client.get_version(), new_version)

    def test_checkout_master_branch_and_update(self):
        # subdir = "checkout_specific_version_test"
        url = self.remote_path
        branch = "master"
        client = GitClient(self.local_path)
        self.assertFalse(client.path_exists())
        self.assertFalse(client.detect_presence())
        self.assertTrue(client.checkout(url, branch))
        self.assertTrue(client.path_exists())
        self.assertTrue(client.detect_presence())
        self.assertEqual(client.get_path(), self.local_path)
        self.assertEqual(client.get_url(), url)
        self.assertEqual(client.get_branch_parent(), branch)

        self.assertTrue(client.update(branch))
        self.assertEqual(client.get_branch_parent(), branch)

    def test_checkout_specific_branch_and_update(self):
        # subdir = "checkout_specific_version_test"
        url = self.remote_path
        branch = "test_branch"
        client = GitClient(self.local_path)
        self.assertFalse(client.path_exists())
        self.assertFalse(client.detect_presence())
        self.assertTrue(client.checkout(url, branch))
        self.assertTrue(client.path_exists())
        self.assertTrue(client.detect_presence())
        self.assertTrue(client.is_local_branch(branch))
        self.assertEqual(client.get_path(), self.local_path)
        self.assertEqual(client.get_url(), url)
        self.assertEqual(client.get_version(), self.readonly_version_init)
        self.assertEqual(client.get_branch(), branch)
        self.assertEqual(client.get_branch_parent(), branch)

        self.assertTrue(client.update())  # no arg
        self.assertEqual(client.get_branch(), branch)
        self.assertEqual(client.get_version(), self.readonly_version_init)
        self.assertEqual(client.get_branch_parent(), branch)

        self.assertTrue(client.update(branch))  # same branch arg
        self.assertEqual(client.get_branch(), branch)
        self.assertEqual(client.get_version(), self.readonly_version_init)
        self.assertEqual(client.get_branch_parent(), branch)

        new_branch = 'master'
        self.assertTrue(client.update(new_branch))
        self.assertEqual(client.get_branch(), new_branch)
        self.assertEqual(client.get_branch_parent(), new_branch)

    def test_checkout_specific_tag_and_update(self):
        url = self.remote_path
        tag = "last_tag"
        client = GitClient(self.local_path)
        self.assertFalse(client.path_exists())
        self.assertFalse(client.detect_presence())
        self.assertTrue(client.checkout(url, tag))
        self.assertTrue(client.path_exists())
        self.assertTrue(client.detect_presence())
        self.assertEqual(client.get_path(), self.local_path)
        self.assertEqual(client.get_url(), url)
        self.assertEqual(client.get_branch_parent(), None)
        tag = "test_tag"
        self.assertTrue(client.update(tag))
        self.assertEqual(client.get_branch_parent(), None)

        new_branch = 'master'
        self.assertTrue(client.update(new_branch))
        self.assertEqual(client.get_branch_parent(), new_branch)
        tag = "test_tag"
        self.assertTrue(client.update(tag))

    def test_fast_forward(self):
        url = self.remote_path
        client = GitClient(self.local_path)
        self.assertTrue(client.checkout(url, "master"))
        subprocess.check_call("git reset --hard test_tag", shell=True, cwd=self.local_path)
        self.assertTrue(client.update())

    def test_fast_forward_diverged(self):
        url = self.remote_path
        client = GitClient(self.local_path)
        self.assertTrue(client.checkout(url, "master"))
        subprocess.check_call("git reset --hard test_tag", shell=True, cwd=self.local_path)
        subprocess.check_call("touch diverged.txt", shell=True, cwd=self.local_path)
        subprocess.check_call("git add *", shell=True, cwd=self.local_path)
        subprocess.check_call("git commit -m diverge", shell=True, cwd=self.local_path)
        # fail because we have diverged
        self.assertFalse(client.update('master'))

    def test_fast_forward_simple_ref(self):
        url = self.remote_path
        client = GitClient(self.local_path)
        self.assertTrue(client.checkout(url, "master"))
        subprocess.check_call("git reset --hard test_tag", shell=True, cwd=self.local_path)
        # replace "refs/head/master" with just "master"
        subprocess.check_call("git config --replace-all branch.master.merge master", shell=True, cwd=self.local_path)

        self.assertTrue(client.get_branch_parent() is not None)

    def testDiffClean(self):
        client = GitClient(self.remote_path)
        self.assertEquals('', client.get_diff())

    def testStatusClean(self):
        client = GitClient(self.remote_path)
        self.assertEquals('', client.get_status())


class GitClientUpdateTest(GitClientTestSetups):

    def test_update_fetch_all_tags(self):
        url = self.remote_path
        client = GitClient(self.local_path)
        self.assertTrue(client.checkout(url, "master"))
        self.assertEqual(client.get_branch(), "master")
        self.assertTrue(client.update())
        p = subprocess.Popen("git tag", shell=True, cwd=self.local_path, stdout=subprocess.PIPE)
        output = p.communicate()[0].decode('utf-8')
        self.assertEqual('last_tag\ntest_tag\n', output)
        subprocess.check_call("git checkout test_tag", shell=True, cwd=self.remote_path)
        subprocess.check_call("git branch alt_branch", shell=True, cwd=self.remote_path)
        subprocess.check_call("touch alt_file.txt", shell=True, cwd=self.remote_path)
        subprocess.check_call("git add *", shell=True, cwd=self.remote_path)
        subprocess.check_call("git commit -m altfile", shell=True, cwd=self.remote_path)
        # switch to untracked
        subprocess.check_call("git checkout test_tag", shell=True, cwd=self.remote_path)
        subprocess.check_call("touch new_file.txt", shell=True, cwd=self.remote_path)
        subprocess.check_call("git add *", shell=True, cwd=self.remote_path)
        subprocess.check_call("git commit -m newfile", shell=True, cwd=self.remote_path)
        subprocess.check_call("git tag new_tag", shell=True, cwd=self.remote_path)
        self.assertTrue(client.update())
        # test whether client gets the tag
        p = subprocess.Popen("git tag", shell=True, cwd=self.local_path, stdout=subprocess.PIPE)
        output = p.communicate()[0].decode('utf-8')
        self.assertEqual('''\
last_tag
new_tag
test_tag
''', output)
        p = subprocess.Popen("git branch -a", shell=True, cwd=self.local_path, stdout=subprocess.PIPE)
        output = p.communicate()[0].decode('utf-8')
        self.assertEqual('''\
* master
  remotes/origin/HEAD -> origin/master
  remotes/origin/alt_branch
  remotes/origin/master
  remotes/origin/test_branch
''', output)

class GitClientLogTest(GitClientTestSetups):

    def setUp(self):
        client = GitClient(self.local_path)
        client.checkout(self.remote_path)
        # Create some local untracking branch
        subprocess.check_call("git checkout test_tag -b localbranch", shell=True, cwd=self.local_path)

        self.n_commits = 10

        for i in range(self.n_commits):
            subprocess.check_call("touch local_%d.txt" % i, shell=True, cwd=self.local_path)
            subprocess.check_call("git add local_%d.txt" % i, shell=True, cwd=self.local_path)
            subprocess.check_call("git commit -m \"local_%d\"" % i, shell=True, cwd=self.local_path)

    def test_get_log_defaults(self):
        client = GitClient(self.local_path)
        log = client.get_log()
        self.assertEquals(self.n_commits + 1, len(log))
        self.assertEquals('local_%d' % (self.n_commits - 1), log[0]['message'])
        for key in ['id', 'author', 'email', 'date', 'message']:
            self.assertTrue(log[0][key] is not None, key)

    def test_get_log_limit(self):
        client = GitClient(self.local_path)
        log = client.get_log(limit=1)
        self.assertEquals(1, len(log))
        self.assertEquals('local_%d' % (self.n_commits - 1), log[0]['message'])

    def test_get_log_path(self):
        client = GitClient(self.local_path)
        for count in range(self.n_commits):
            log = client.get_log(relpath='local_%d.txt' % count)
            self.assertEquals(1, len(log))


class GitClientDanglingCommitsTest(GitClientTestSetups):

    def setUp(self):
        client = GitClient(self.local_path)
        client.checkout(self.remote_path)
        # Create some local untracking branch
        subprocess.check_call("git checkout test_tag -b localbranch", shell=True, cwd=self.local_path)
        subprocess.check_call("touch local.txt", shell=True, cwd=self.local_path)
        subprocess.check_call("git add *", shell=True, cwd=self.local_path)
        subprocess.check_call("git commit -m my_branch", shell=True, cwd=self.local_path)
        subprocess.check_call("git tag my_branch_tag", shell=True, cwd=self.local_path)
        po = subprocess.Popen("git log -n 1 --pretty=format:\"%H\"", shell=True, cwd=self.local_path, stdout=subprocess.PIPE)
        self.untracked_version = po.stdout.read().decode('UTF-8').rstrip('"').lstrip('"')

        # diverged branch
        subprocess.check_call("git checkout test_tag -b diverged_branch", shell=True, cwd=self.local_path)
        subprocess.check_call("touch diverged.txt", shell=True, cwd=self.local_path)
        subprocess.check_call("git add *", shell=True, cwd=self.local_path)
        subprocess.check_call("git commit -m diverged_branch", shell=True, cwd=self.local_path)
        po = subprocess.Popen("git log -n 1 --pretty=format:\"%H\"", shell=True, cwd=self.local_path, stdout=subprocess.PIPE)
        self.diverged_branch_version = po.stdout.read().decode('UTF-8').rstrip('"').lstrip('"')

        # Go detached to create some dangling commits
        subprocess.check_call("git checkout test_tag", shell=True, cwd=self.local_path)
        # create a commit only referenced by tag
        subprocess.check_call("touch tagged.txt", shell=True, cwd=self.local_path)
        subprocess.check_call("git add *", shell=True, cwd=self.local_path)
        subprocess.check_call("git commit -m no_branch", shell=True, cwd=self.local_path)
        subprocess.check_call("git tag no_br_tag", shell=True, cwd=self.local_path)
        po = subprocess.Popen("git log -n 1 --pretty=format:\"%H\"", shell=True, cwd=self.local_path, stdout=subprocess.PIPE)
        self.no_br_tag_version = po.stdout.read().decode('UTF-8').rstrip('"').lstrip('"')

        # create a dangling commit
        subprocess.check_call("touch dangling.txt", shell=True, cwd=self.local_path)
        subprocess.check_call("git add *", shell=True, cwd=self.local_path)
        subprocess.check_call("git commit -m dangling", shell=True, cwd=self.local_path)

        po = subprocess.Popen("git log -n 1 --pretty=format:\"%H\"", shell=True, cwd=self.local_path, stdout=subprocess.PIPE)
        self.dangling_version = po.stdout.read().decode('UTF-8').rstrip('"').lstrip('"')

        # create a dangling tip on top of dangling commit (to catch related bugs)
        subprocess.check_call("touch dangling-tip.txt", shell=True, cwd=self.local_path)
        subprocess.check_call("git add *", shell=True, cwd=self.local_path)
        subprocess.check_call("git commit -m dangling_tip", shell=True, cwd=self.local_path)

        # create and delete branch to cause reflog entry
        subprocess.check_call("git branch oldbranch", shell=True, cwd=self.local_path)
        subprocess.check_call("git branch -D oldbranch", shell=True, cwd=self.local_path)

        # go back to master to make head point somewhere else
        subprocess.check_call("git checkout master", shell=True, cwd=self.local_path)

    def test_is_commit_in_orphaned_subtree(self):
        client = GitClient(self.local_path)
        self.assertTrue(client.is_commit_in_orphaned_subtree(self.dangling_version))
        self.assertFalse(client.is_commit_in_orphaned_subtree(self.no_br_tag_version))
        self.assertFalse(client.is_commit_in_orphaned_subtree(self.diverged_branch_version))

    def test_protect_dangling(self):
        client = GitClient(self.local_path)
        # url = self.remote_path
        self.assertEqual(client.get_branch(), "master")
        tag = "no_br_tag"
        self.assertTrue(client.update(tag))
        self.assertEqual(client.get_branch(), None)
        self.assertEqual(client.get_branch_parent(), None)

        tag = "test_tag"
        self.assertTrue(client.update(tag))
        self.assertEqual(client.get_branch(), None)
        self.assertEqual(client.get_branch_parent(), None)

        # to dangling commit
        sha = self.dangling_version
        self.assertTrue(client.update(sha))
        self.assertEqual(client.get_branch(), None)
        self.assertEqual(client.get_version(), self.dangling_version)
        self.assertEqual(client.get_branch_parent(), None)

        # now HEAD protects the dangling commit, should not be allowed to move off.
        new_branch = 'master'
        self.assertFalse(client.update(new_branch))

    def test_detached_to_branch(self):
        client = GitClient(self.local_path)
        # url = self.remote_path
        self.assertEqual(client.get_branch(), "master")
        tag = "no_br_tag"
        self.assertTrue(client.update(tag))
        self.assertEqual(client.get_branch(), None)
        self.assertEqual(client.get_branch_parent(), None)

        tag = "test_tag"
        self.assertTrue(client.update(tag))
        self.assertEqual(client.get_branch(), None)
        self.assertEqual(client.get_version(), self.readonly_version_init)
        self.assertEqual(client.get_branch_parent(), None)

        #update should not change anything
        self.assertTrue(client.update())  # no arg
        self.assertEqual(client.get_branch(), None)
        self.assertEqual(client.get_version(), self.readonly_version_init)
        self.assertEqual(client.get_branch_parent(), None)

        new_branch = 'master'
        self.assertTrue(client.update(new_branch))
        self.assertEqual(client.get_branch(), new_branch)
        self.assertEqual(client.get_version(), self.readonly_version)
        self.assertEqual(client.get_branch_parent(), new_branch)

    def test_checkout_untracked_branch_and_update(self):
        # difference to tracked branches is that branch parent is None, and we may hop outside lineage
        client = GitClient(self.local_path)
        url = self.remote_path
        branch = "localbranch"
        self.assertEqual(client.get_branch(), "master")
        self.assertTrue(client.path_exists())
        self.assertTrue(client.detect_presence())
        self.assertTrue(client.is_local_branch(branch))
        self.assertEqual(client.get_path(), self.local_path)
        self.assertEqual(client.get_url(), url)
        self.assertTrue(client.update(branch))
        self.assertEqual(client.get_version(), self.untracked_version)
        self.assertEqual(client.get_branch(), branch)
        self.assertEqual(client.get_branch_parent(), None)

        self.assertTrue(client.update())  # no arg
        self.assertEqual(client.get_branch(), branch)
        self.assertEqual(client.get_version(), self.untracked_version)
        self.assertEqual(client.get_branch_parent(), None)

        self.assertTrue(client.update(branch))  # same branch arg
        self.assertEqual(client.get_branch(), branch)
        self.assertEqual(client.get_version(), self.untracked_version)
        self.assertEqual(client.get_branch_parent(), None)

        # to master
        new_branch = 'master'
        self.assertTrue(client.update(new_branch))
        self.assertEqual(client.get_branch(), new_branch)
        self.assertEqual(client.get_version(), self.readonly_version)
        self.assertEqual(client.get_branch_parent(), new_branch)

        # and back
        self.assertTrue(client.update(branch))  # same branch arg
        self.assertEqual(client.get_branch(), branch)
        self.assertEqual(client.get_version(), self.untracked_version)
        self.assertEqual(client.get_branch_parent(), None)

        # to dangling commit
        sha = self.dangling_version
        self.assertTrue(client.update(sha))
        self.assertEqual(client.get_branch(), None)
        self.assertEqual(client.get_version(), self.dangling_version)
        self.assertEqual(client.get_branch_parent(), None)

        #should not work to protect commits from becoming dangled
        # to commit outside lineage
        tag = "test_tag"
        self.assertFalse(client.update(tag))

    def test_inject_protection(self):
        client = GitClient(self.local_path)
        try:
            client.is_tag('foo"; bar"', fetch=False)
            self.fail("expected Exception")
        except VcsError:
            pass
        try:
            client.rev_list_contains('foo"; echo bar"', "foo", fetch=False)
            self.fail("expected Exception")
        except VcsError:
            pass
        try:
            client.rev_list_contains('foo', 'foo"; echo bar"', fetch=False)
            self.fail("expected Exception")
        except VcsError:
            pass
        try:
            client.get_version('foo"; echo bar"')
            self.fail("expected Exception")
        except VcsError:
            pass

class GitClientOverflowTest(GitClientTestSetups):
    '''Test reproducing an overflow of arguments to git log'''

    def setUp(self):
        client = GitClient(self.local_path)
        client.checkout(self.remote_path)
        subprocess.check_call("git checkout test_tag", shell=True, cwd=self.local_path)
        subprocess.check_call("echo 0 >> count.txt", shell=True, cwd=self.local_path)
        subprocess.check_call("git add count.txt", shell=True, cwd=self.local_path)
        subprocess.check_call("git commit -m modified-0", shell=True, cwd=self.local_path)
        # produce many tags to make git log command fail if all are added
        for count in range(4000):
            subprocess.check_call("git tag modified-%s" % count, shell=True, cwd=self.local_path)
        po = subprocess.Popen("git log -n 1 --pretty=format:\"%H\"", shell=True, cwd=self.local_path, stdout=subprocess.PIPE)
        self.last_version = po.stdout.read().decode('UTF-8').rstrip('"').lstrip('"')

    def test_orphaned_overflow(self):
        client = GitClient(self.local_path)
        # this failed when passing all ref ids to git log
        self.assertFalse(client.is_commit_in_orphaned_subtree(self.last_version))

class GitDiffStatClientTest(GitClientTestSetups):

    @classmethod
    def setUpClass(self):
        GitClientTestSetups.setUpClass()

        client = GitClient(self.local_path)
        client.checkout(self.remote_path, self.readonly_version)
        # after setting up "readonly" repo, change files and make some changes
        subprocess.check_call("rm deleted-fs.txt", shell=True, cwd=self.local_path)
        subprocess.check_call("git rm deleted.txt", shell=True, cwd=self.local_path)
        f = io.open(os.path.join(self.local_path, "modified.txt"), 'a')
        f.write('0123456789abcdef')
        f.close()
        f = io.open(os.path.join(self.local_path, "modified-fs.txt"), 'a')
        f.write('0123456789abcdef')
        f.close()
        subprocess.check_call("git add modified.txt", shell=True, cwd=self.local_path)
        f = io.open(os.path.join(self.local_path, "added-fs.txt"), 'w')
        f.write('0123456789abcdef')
        f.close()
        f = io.open(os.path.join(self.local_path, "added.txt"), 'w')
        f.write('0123456789abcdef')
        f.close()
        subprocess.check_call("git add added.txt", shell=True, cwd=self.local_path)

    def tearDown(self):
        pass

    def testDiff(self):
        client = GitClient(self.local_path)
        self.assertTrue(client.path_exists())
        self.assertTrue(client.detect_presence())
        self.assertEquals('diff --git ./added.txt ./added.txt\nnew file mode 100644\nindex 0000000..454f6b3\n--- /dev/null\n+++ ./added.txt\n@@ -0,0 +1 @@\n+0123456789abcdef\n\\ No newline at end of file\ndiff --git ./deleted-fs.txt ./deleted-fs.txt\ndeleted file mode 100644\nindex e69de29..0000000\ndiff --git ./deleted.txt ./deleted.txt\ndeleted file mode 100644\nindex e69de29..0000000\ndiff --git ./modified-fs.txt ./modified-fs.txt\nindex e69de29..454f6b3 100644\n--- ./modified-fs.txt\n+++ ./modified-fs.txt\n@@ -0,0 +1 @@\n+0123456789abcdef\n\\ No newline at end of file\ndiff --git ./modified.txt ./modified.txt\nindex e69de29..454f6b3 100644\n--- ./modified.txt\n+++ ./modified.txt\n@@ -0,0 +1 @@\n+0123456789abcdef\n\\ No newline at end of file', client.get_diff().rstrip())

    def testDiffRelpath(self):
        client = GitClient(self.local_path)
        self.assertTrue(client.path_exists())
        self.assertTrue(client.detect_presence())
        self.assertEquals('diff --git ros/added.txt ros/added.txt\nnew file mode 100644\nindex 0000000..454f6b3\n--- /dev/null\n+++ ros/added.txt\n@@ -0,0 +1 @@\n+0123456789abcdef\n\\ No newline at end of file\ndiff --git ros/deleted-fs.txt ros/deleted-fs.txt\ndeleted file mode 100644\nindex e69de29..0000000\ndiff --git ros/deleted.txt ros/deleted.txt\ndeleted file mode 100644\nindex e69de29..0000000\ndiff --git ros/modified-fs.txt ros/modified-fs.txt\nindex e69de29..454f6b3 100644\n--- ros/modified-fs.txt\n+++ ros/modified-fs.txt\n@@ -0,0 +1 @@\n+0123456789abcdef\n\\ No newline at end of file\ndiff --git ros/modified.txt ros/modified.txt\nindex e69de29..454f6b3 100644\n--- ros/modified.txt\n+++ ros/modified.txt\n@@ -0,0 +1 @@\n+0123456789abcdef\n\\ No newline at end of file', client.get_diff(basepath=os.path.dirname(self.local_path)).rstrip())

    def testStatus(self):
        client = GitClient(self.local_path)
        self.assertTrue(client.path_exists())
        self.assertTrue(client.detect_presence())
        self.assertEquals('A  ./added.txt\n D ./deleted-fs.txt\nD  ./deleted.txt\n M ./modified-fs.txt\nM  ./modified.txt\n', client.get_status())

    def testStatusRelPath(self):
        client = GitClient(self.local_path)
        self.assertTrue(client.path_exists())
        self.assertTrue(client.detect_presence())
        self.assertEquals('A  ros/added.txt\n D ros/deleted-fs.txt\nD  ros/deleted.txt\n M ros/modified-fs.txt\nM  ros/modified.txt\n', client.get_status(basepath=os.path.dirname(self.local_path)))

    def testStatusUntracked(self):
        client = GitClient(self.local_path)
        self.assertTrue(client.path_exists())
        self.assertTrue(client.detect_presence())
        self.assertEquals('A  ./added.txt\n D ./deleted-fs.txt\nD  ./deleted.txt\n M ./modified-fs.txt\nM  ./modified.txt\n?? ./added-fs.txt\n', client.get_status(untracked=True))


class GitExportClientTest(GitClientTestSetups):

    @classmethod
    def setUpClass(self):
        GitClientTestSetups.setUpClass()

        client = GitClient(self.local_path)
        client.checkout(self.remote_path, self.readonly_version)

        self.basepath_export = os.path.join(self.root_directory, 'export')

    def tearDown(self):
        pass

    def testExportRepository(self):
        client = GitClient(self.local_path)
        self.assertTrue(
          client.export_repository(self.readonly_version, self.basepath_export)
        )

        self.assertTrue(os.path.exists(self.basepath_export + '.tar.gz'))
        self.assertFalse(os.path.exists(self.basepath_export + '.tar'))
        self.assertFalse(os.path.exists(self.basepath_export))
