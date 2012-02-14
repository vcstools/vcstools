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

import os
import io
import stat
import struct
import sys
import unittest
import subprocess
import tempfile
import urllib
import shutil

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
        subprocess.check_call(["git", "init"], cwd=self.remote_path)
        subprocess.check_call(["touch", "fixed.txt"], cwd=self.remote_path)
        subprocess.check_call(["git", "add", "*"], cwd=self.remote_path)
        subprocess.check_call(["git", "commit", "-m", "initial"], cwd=self.remote_path)
        subprocess.check_call(["git", "tag", "test_tag"], cwd=self.remote_path)
        # other branch
        subprocess.check_call(["git", "branch", "test_branch"], cwd=self.remote_path)
        
        po = subprocess.Popen(["git", "log", "-n", "1", "--pretty=format:\"%H\""], cwd=self.remote_path, stdout=subprocess.PIPE)
        self.readonly_version_init = po.stdout.read().rstrip('"').lstrip('"')

        # files to be modified in "local" repo
        subprocess.check_call(["touch", "modified.txt"], cwd=self.remote_path)
        subprocess.check_call(["touch", "modified-fs.txt"], cwd=self.remote_path)
        subprocess.check_call(["git", "add", "*"], cwd=self.remote_path)
        subprocess.check_call(["git", "commit", "-m", "initial"], cwd=self.remote_path)
        po = subprocess.Popen(["git", "log", "-n", "1", "--pretty=format:\"%H\""], cwd=self.remote_path, stdout=subprocess.PIPE)
        self.readonly_version_second = po.stdout.read().rstrip('"').lstrip('"')
        
        subprocess.check_call(["touch", "deleted.txt"], cwd=self.remote_path)
        subprocess.check_call(["touch", "deleted-fs.txt"], cwd=self.remote_path)
        subprocess.check_call(["git", "add", "*"], cwd=self.remote_path)
        subprocess.check_call(["git", "commit", "-m", "modified"], cwd=self.remote_path)
        po = subprocess.Popen(["git", "log", "-n", "1", "--pretty=format:\"%H\""], cwd=self.remote_path, stdout=subprocess.PIPE)
        self.readonly_version = po.stdout.read().rstrip('"').lstrip('"')
        subprocess.check_call(["git", "tag", "last_tag"], cwd=self.remote_path)


    @classmethod
    def tearDownClass(self):
        for d in self.directories:
            shutil.rmtree(self.directories[d])

    def tearDown(self):
        if os.path.exists(self.local_path):
            shutil.rmtree(self.local_path)
            
    
class GitClientTest(GitClientTestSetups):
    
    def test_get_url_by_reading(self):
        from vcstools.git import GitClient
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
        from vcstools.git import GitClient
        local_path = "/tmp/dummy"
        client = GitClient(self.local_path)
        self.assertEqual(client.get_url(), None)

    def test_get_type_name(self):
        from vcstools.git import GitClient
        local_path = "/tmp/dummy"
        client = GitClient(self.local_path)
        self.assertEqual(client.get_vcs_type_name(), 'git')

    def test_checkout(self):
        from vcstools.git import GitClient
        
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


    def test_checkout_specific_version_and_update(self):
        from vcstools.git import GitClient
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
        from vcstools.git import GitClient
        subdir = "checkout_specific_version_test"
        
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
        from vcstools.git import GitClient
        subdir = "checkout_specific_version_test"
        
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

        self.assertTrue(client.update())# no arg
        self.assertEqual(client.get_branch(), branch)
        self.assertEqual(client.get_version(), self.readonly_version_init)
        self.assertEqual(client.get_branch_parent(), branch)

        self.assertTrue(client.update(branch))# same branch arg
        self.assertEqual(client.get_branch(), branch)
        self.assertEqual(client.get_version(), self.readonly_version_init)
        self.assertEqual(client.get_branch_parent(), branch)
        
        new_branch = 'master'
        self.assertTrue(client.update(new_branch))
        self.assertEqual(client.get_branch(), new_branch)
        self.assertEqual(client.get_branch_parent(), new_branch)


    def test_checkout_specific_tag_and_update(self):
        from vcstools.git import GitClient
        
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
        from vcstools.git import GitClient
        
        url = self.remote_path
        client = GitClient(self.local_path)
        self.assertTrue(client.checkout(url, "master"))
        subprocess.check_call(["git", "reset", "--hard", "test_tag"], cwd=self.local_path)
        self.assertTrue(client.update())

    def test_fast_forward_simple_ref(self):
        from vcstools.git import GitClient
        
        url = self.remote_path
        client = GitClient(self.local_path)
        self.assertTrue(client.checkout(url, "master"))
        subprocess.check_call(["git", "reset", "--hard", "test_tag"], cwd=self.local_path)
        # replace "refs/head/master" with just "master"
        subprocess.check_call(["git", "config", "--replace-all", "branch.master.merge", "master"], cwd=self.local_path)
        
        self.assertTrue(client.get_branch_parent() is not None)
        
class GitClientDanglingCommitsTest(GitClientTestSetups):

    def setUp(self):
        from vcstools.git import GitClient
        client = GitClient(self.local_path)
        client.checkout(self.remote_path)
        # Create some local untracking branch
        subprocess.check_call(["git", "checkout", "test_tag", "-b", "localbranch"], cwd=self.local_path)
        subprocess.check_call(["touch", "local.txt"], cwd=self.local_path)
        subprocess.check_call(["git", "add", "*"], cwd=self.local_path)
        subprocess.check_call(["git", "commit", "-m", "my_branch"], cwd=self.local_path)
        subprocess.check_call(["git", "tag", "my_branch_tag"], cwd=self.local_path)
        po = subprocess.Popen(["git", "log", "-n", "1", "--pretty=format:\"%H\""], cwd=self.local_path, stdout=subprocess.PIPE)
        self.untracked_version = po.stdout.read().rstrip('"').lstrip('"')
        
        # Go detached to create some dangling commits
        subprocess.check_call(["git", "checkout", "test_tag"], cwd=self.local_path)
        # create a commit only referenced by tag
        subprocess.check_call(["touch", "tagged.txt"], cwd=self.local_path)
        subprocess.check_call(["git", "add", "*"], cwd=self.local_path)
        subprocess.check_call(["git", "commit", "-m", "no_branch"], cwd=self.local_path)
        subprocess.check_call(["git", "tag", "no_br_tag"], cwd=self.local_path)
        # create a dangling commit
        subprocess.check_call(["touch", "dangling.txt"], cwd=self.local_path)
        subprocess.check_call(["git", "add", "*"], cwd=self.local_path)
        subprocess.check_call(["git", "commit", "-m", "dangling"], cwd=self.local_path)

        po = subprocess.Popen(["git", "log", "-n", "1", "--pretty=format:\"%H\""], cwd=self.local_path, stdout=subprocess.PIPE)
        self.dangling_version = po.stdout.read().rstrip('"').lstrip('"')

        # go back to master to make head point somewhere else
        subprocess.check_call(["git", "checkout", "master"], cwd=self.local_path)

        
    def test_protect_dangling(self):
        from vcstools.git import GitClient
        client = GitClient(self.local_path)
        url = self.remote_path
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
        from vcstools.git import GitClient
        client = GitClient(self.local_path)
        url = self.remote_path
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
        self.assertTrue(client.update()) #no arg
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
        from vcstools.git import GitClient
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

        self.assertTrue(client.update())# no arg
        self.assertEqual(client.get_branch(), branch)
        self.assertEqual(client.get_version(), self.untracked_version)
        self.assertEqual(client.get_branch_parent(), None)

        self.assertTrue(client.update(branch))# same branch arg
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
        self.assertTrue(client.update(branch))# same branch arg
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



class GitDiffStatClientTest(GitClientTestSetups):

    @classmethod
    def setUpClass(self):
        GitClientTestSetups.setUpClass()
        
        from vcstools.git import GitClient
        client = GitClient(self.local_path)
        client.checkout(self.remote_path, self.readonly_version)
        # after setting up "readonly" repo, change files and make some changes
        subprocess.check_call(["rm", "deleted-fs.txt"], cwd=self.local_path)
        subprocess.check_call(["git", "rm", "deleted.txt"], cwd=self.local_path)
        f = io.open(os.path.join(self.local_path, "modified.txt"), 'a')
        f.write(u'0123456789abcdef')
        f.close()
        f = io.open(os.path.join(self.local_path, "modified-fs.txt"), 'a')
        f.write(u'0123456789abcdef')
        f.close()
        subprocess.check_call(["git", "add", "modified.txt"], cwd=self.local_path)
        f = io.open(os.path.join(self.local_path, "added-fs.txt"), 'w')
        f.write(u'0123456789abcdef')
        f.close()
        f = io.open(os.path.join(self.local_path, "added.txt"), 'w')
        f.write(u'0123456789abcdef')
        f.close()
        subprocess.check_call(["git", "add", "added.txt"], cwd=self.local_path)

    def tearDown(self):
        pass
        
    def testDiff(self):
        from vcstools.git import GitClient
        client = GitClient(self.local_path)
        self.assertTrue(client.path_exists())
        self.assertTrue(client.detect_presence())
        self.assertEquals('diff --git ./added.txt ./added.txt\nnew file mode 100644\nindex 0000000..454f6b3\n--- /dev/null\n+++ ./added.txt\n@@ -0,0 +1 @@\n+0123456789abcdef\n\\ No newline at end of file\ndiff --git ./deleted-fs.txt ./deleted-fs.txt\ndeleted file mode 100644\nindex e69de29..0000000\ndiff --git ./deleted.txt ./deleted.txt\ndeleted file mode 100644\nindex e69de29..0000000\ndiff --git ./modified-fs.txt ./modified-fs.txt\nindex e69de29..454f6b3 100644\n--- ./modified-fs.txt\n+++ ./modified-fs.txt\n@@ -0,0 +1 @@\n+0123456789abcdef\n\\ No newline at end of file\ndiff --git ./modified.txt ./modified.txt\nindex e69de29..454f6b3 100644\n--- ./modified.txt\n+++ ./modified.txt\n@@ -0,0 +1 @@\n+0123456789abcdef\n\\ No newline at end of file\n', client.get_diff())

    def testDiffRelpath(self):
        from vcstools.git import GitClient
        client = GitClient(self.local_path)
        self.assertTrue(client.path_exists())
        self.assertTrue(client.detect_presence())
        self.assertEquals('diff --git ros/added.txt ros/added.txt\nnew file mode 100644\nindex 0000000..454f6b3\n--- /dev/null\n+++ ros/added.txt\n@@ -0,0 +1 @@\n+0123456789abcdef\n\\ No newline at end of file\ndiff --git ros/deleted-fs.txt ros/deleted-fs.txt\ndeleted file mode 100644\nindex e69de29..0000000\ndiff --git ros/deleted.txt ros/deleted.txt\ndeleted file mode 100644\nindex e69de29..0000000\ndiff --git ros/modified-fs.txt ros/modified-fs.txt\nindex e69de29..454f6b3 100644\n--- ros/modified-fs.txt\n+++ ros/modified-fs.txt\n@@ -0,0 +1 @@\n+0123456789abcdef\n\\ No newline at end of file\ndiff --git ros/modified.txt ros/modified.txt\nindex e69de29..454f6b3 100644\n--- ros/modified.txt\n+++ ros/modified.txt\n@@ -0,0 +1 @@\n+0123456789abcdef\n\\ No newline at end of file\n', client.get_diff(basepath=os.path.dirname(self.local_path)))

    def testStatus(self):
        from vcstools.git import GitClient
        client = GitClient(self.local_path)
        self.assertTrue(client.path_exists())
        self.assertTrue(client.detect_presence())
        self.assertEquals('A  ./added.txt\n D ./deleted-fs.txt\nD  ./deleted.txt\n M ./modified-fs.txt\nM  ./modified.txt\n', client.get_status())

    def testStatusRelPath(self):
        from vcstools.git import GitClient
        client = GitClient(self.local_path)
        self.assertTrue(client.path_exists())
        self.assertTrue(client.detect_presence())
        self.assertEquals('A  ros/added.txt\n D ros/deleted-fs.txt\nD  ros/deleted.txt\n M ros/modified-fs.txt\nM  ros/modified.txt\n', client.get_status(basepath=os.path.dirname(self.local_path)))

    def testStatusUntracked(self):
        from vcstools.git import GitClient
        client = GitClient(self.local_path)
        self.assertTrue(client.path_exists())
        self.assertTrue(client.detect_presence())
        self.assertEquals('A  ./added.txt\n D ./deleted-fs.txt\nD  ./deleted.txt\n M ./modified-fs.txt\nM  ./modified.txt\n?? ./added-fs.txt\n', client.get_status(untracked=True))



