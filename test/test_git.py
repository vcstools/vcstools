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

    def setUp(self):
        from vcstools.git import GitClient
        
        directory = tempfile.mkdtemp()
        self.directories = dict(setUp=directory)
        remote_path = os.path.join(directory, "remote")
        os.makedirs(remote_path)
        
        # create a "remote" repo
        subprocess.check_call(["git", "init"], cwd=remote_path)
        subprocess.check_call(["touch", "fixed.txt"], cwd=remote_path)
        subprocess.check_call(["git", "add", "*"], cwd=remote_path)
        subprocess.check_call(["git", "commit", "-m", "initial"], cwd=remote_path)
        subprocess.check_call(["git", "tag", "test_tag"], cwd=remote_path)
        
        po = subprocess.Popen(["git", "log", "-n", "1", "--pretty=format:\"%H\""], cwd=remote_path, stdout=subprocess.PIPE)
        self.readonly_version_init = po.stdout.read().rstrip('"').lstrip('"')
        
        # files to be modified in "local" repo
        subprocess.check_call(["touch", "modified.txt"], cwd=remote_path)
        subprocess.check_call(["touch", "modified-fs.txt"], cwd=remote_path)
        subprocess.check_call(["git", "add", "*"], cwd=remote_path)
        subprocess.check_call(["git", "commit", "-m", "initial"], cwd=remote_path)
        po = subprocess.Popen(["git", "log", "-n", "1", "--pretty=format:\"%H\""], cwd=remote_path, stdout=subprocess.PIPE)
        self.readonly_version_second = po.stdout.read().rstrip('"').lstrip('"')
        
        subprocess.check_call(["touch", "deleted.txt"], cwd=remote_path)
        subprocess.check_call(["touch", "deleted-fs.txt"], cwd=remote_path)
        subprocess.check_call(["git", "add", "*"], cwd=remote_path)
        subprocess.check_call(["git", "commit", "-m", "modified"], cwd=remote_path)
        po = subprocess.Popen(["git", "log", "-n", "1", "--pretty=format:\"%H\""], cwd=remote_path, stdout=subprocess.PIPE)

        self.readonly_version = po.stdout.read().rstrip('"').lstrip('"')
        self.readonly_path = os.path.join(directory, "readonly")
        self.readonly_url = remote_path
        gitc = GitClient(self.readonly_path)
        self.assertTrue(gitc.checkout(remote_path, self.readonly_version))

    def tearDown(self):
        for d in self.directories:
            shutil.rmtree(self.directories[d])

    
class GitClientTest(GitClientTestSetups):


    def test_get_url_by_reading(self):
        from vcstools.git import GitClient

        gitc = GitClient(self.readonly_path)
        self.assertTrue(gitc.path_exists())
        self.assertTrue(gitc.detect_presence())
        self.assertEqual(gitc.get_url(), self.readonly_url)
        self.assertEqual(gitc.get_version(), self.readonly_version)
        self.assertEqual(gitc.get_version(self.readonly_version_init[0:6]), self.readonly_version_init)
        self.assertEqual(gitc.get_version("test_tag"), self.readonly_version_init)

    def test_get_url_nonexistant(self):
        from vcstools.git import GitClient
        local_path = "/tmp/dummy"
        client = GitClient(local_path)
        self.assertEqual(client.get_url(), None)

    def test_get_type_name(self):
        from vcstools.git import GitClient
        local_path = "/tmp/dummy"
        gitc = GitClient(local_path)
        self.assertEqual(gitc.get_vcs_type_name(), 'git')

    def test_checkout(self):
        from vcstools.git import GitClient
        directory = tempfile.mkdtemp()
        self.directories["checkout_test"] = directory
        local_path = os.path.join(directory, "ros")
        url = self.readonly_url
        gitc = GitClient(local_path)
        self.assertFalse(gitc.path_exists())
        self.assertFalse(gitc.detect_presence())
        self.assertFalse(gitc.detect_presence())
        self.assertTrue(gitc.checkout(url))
        self.assertTrue(gitc.path_exists())
        self.assertTrue(gitc.detect_presence())
        self.assertEqual(gitc.get_path(), local_path)
        self.assertEqual(gitc.get_url(), url)
        self.assertEqual(gitc.get_branch(), "master")
        self.assertEqual(gitc.get_branch_parent(), "master")
        #self.assertEqual(gitc.get_version(), '-r*')

        shutil.rmtree(directory)
        self.directories.pop("checkout_test")

    def test_checkout_specific_version_and_update(self):
        from vcstools.git import GitClient
        directory = tempfile.mkdtemp()
        subdir = "checkout_specific_version_test"
        self.directories[subdir] = directory
        local_path = os.path.join(directory, "ros")
        url = self.readonly_url
        version = self.readonly_version
        gitc = GitClient(local_path)
        self.assertFalse(gitc.path_exists())
        self.assertFalse(gitc.detect_presence())
        self.assertTrue(gitc.checkout(url, version))
        self.assertTrue(gitc.path_exists())
        self.assertTrue(gitc.detect_presence())
        self.assertEqual(gitc.get_path(), local_path)
        self.assertEqual(gitc.get_url(), url)
        self.assertEqual(gitc.get_version(), version)
        
        new_version = self.readonly_version_second
        self.assertTrue(gitc.update(new_version))
        self.assertEqual(gitc.get_version(), new_version)
        
        shutil.rmtree(directory)
        self.directories.pop(subdir)

    def test_checkout_specific_branch_and_update(self):
        from vcstools.git import GitClient
        directory = tempfile.mkdtemp()
        subdir = "checkout_specific_version_test"
        self.directories[subdir] = directory
        local_path = os.path.join(directory, "ros")
        url = self.readonly_url
        branch = "master"
        gitc = GitClient(local_path)
        self.assertFalse(gitc.path_exists())
        self.assertFalse(gitc.detect_presence())
        self.assertTrue(gitc.checkout(url, branch))
        self.assertTrue(gitc.path_exists())
        self.assertTrue(gitc.detect_presence())
        self.assertEqual(gitc.get_path(), local_path)
        self.assertEqual(gitc.get_url(), url)
        self.assertEqual(gitc.get_branch_parent(), branch)
        
        new_branch = 'master'
        self.assertTrue(gitc.update(new_branch))
        self.assertEqual(gitc.get_branch_parent(), new_branch)
        
        shutil.rmtree(directory)
        self.directories.pop(subdir)

        
class GitDiffStatClientTest(GitClientTestSetups):

    def setUp(self):
        GitClientTestSetups.setUp(self)
        # after setting up "readonly" repo, change files and make some changes
        subprocess.check_call(["rm", "deleted-fs.txt"], cwd=self.readonly_path)
        subprocess.check_call(["git", "rm", "deleted.txt"], cwd=self.readonly_path)
        f = io.open(os.path.join(self.readonly_path, "modified.txt"), 'a')
        f.write(u'0123456789abcdef')
        f.close()
        f = io.open(os.path.join(self.readonly_path, "modified-fs.txt"), 'a')
        f.write(u'0123456789abcdef')
        f.close()
        subprocess.check_call(["git", "add", "modified.txt"], cwd=self.readonly_path)
        f = io.open(os.path.join(self.readonly_path, "added-fs.txt"), 'w')
        f.write(u'0123456789abcdef')
        f.close()
        f = io.open(os.path.join(self.readonly_path, "added.txt"), 'w')
        f.write(u'0123456789abcdef')
        f.close()
        subprocess.check_call(["git", "add", "added.txt"], cwd=self.readonly_path)

    def testDiff(self):
        from vcstools.git import GitClient
        client = GitClient(self.readonly_path)
        self.assertTrue(client.path_exists())
        self.assertTrue(client.detect_presence())
        self.assertEquals('diff --git ./added.txt ./added.txt\nnew file mode 100644\nindex 0000000..454f6b3\n--- /dev/null\n+++ ./added.txt\n@@ -0,0 +1 @@\n+0123456789abcdef\n\\ No newline at end of file\ndiff --git ./deleted-fs.txt ./deleted-fs.txt\ndeleted file mode 100644\nindex e69de29..0000000\ndiff --git ./deleted.txt ./deleted.txt\ndeleted file mode 100644\nindex e69de29..0000000\ndiff --git ./modified-fs.txt ./modified-fs.txt\nindex e69de29..454f6b3 100644\n--- ./modified-fs.txt\n+++ ./modified-fs.txt\n@@ -0,0 +1 @@\n+0123456789abcdef\n\\ No newline at end of file\ndiff --git ./modified.txt ./modified.txt\nindex e69de29..454f6b3 100644\n--- ./modified.txt\n+++ ./modified.txt\n@@ -0,0 +1 @@\n+0123456789abcdef\n\\ No newline at end of file\n', client.get_diff())

    def testDiffRelpath(self):
        from vcstools.git import GitClient
        client = GitClient(self.readonly_path)
        self.assertTrue(client.path_exists())
        self.assertTrue(client.detect_presence())
        self.assertEquals('diff --git readonly/added.txt readonly/added.txt\nnew file mode 100644\nindex 0000000..454f6b3\n--- /dev/null\n+++ readonly/added.txt\n@@ -0,0 +1 @@\n+0123456789abcdef\n\\ No newline at end of file\ndiff --git readonly/deleted-fs.txt readonly/deleted-fs.txt\ndeleted file mode 100644\nindex e69de29..0000000\ndiff --git readonly/deleted.txt readonly/deleted.txt\ndeleted file mode 100644\nindex e69de29..0000000\ndiff --git readonly/modified-fs.txt readonly/modified-fs.txt\nindex e69de29..454f6b3 100644\n--- readonly/modified-fs.txt\n+++ readonly/modified-fs.txt\n@@ -0,0 +1 @@\n+0123456789abcdef\n\\ No newline at end of file\ndiff --git readonly/modified.txt readonly/modified.txt\nindex e69de29..454f6b3 100644\n--- readonly/modified.txt\n+++ readonly/modified.txt\n@@ -0,0 +1 @@\n+0123456789abcdef\n\\ No newline at end of file\n', client.get_diff(basepath=os.path.dirname(self.readonly_path)))

    def testStatus(self):
        from vcstools.git import GitClient
        client = GitClient(self.readonly_path)
        self.assertTrue(client.path_exists())
        self.assertTrue(client.detect_presence())
        self.assertEquals('A  ./added.txt\n D ./deleted-fs.txt\nD  ./deleted.txt\n M ./modified-fs.txt\nM  ./modified.txt\n', client.get_status())

    def testStatusRelPath(self):
        from vcstools.git import GitClient
        client = GitClient(self.readonly_path)
        self.assertTrue(client.path_exists())
        self.assertTrue(client.detect_presence())
        self.assertEquals('A  readonly/added.txt\n D readonly/deleted-fs.txt\nD  readonly/deleted.txt\n M readonly/modified-fs.txt\nM  readonly/modified.txt\n', client.get_status(basepath=os.path.dirname(self.readonly_path)))

    def testStatusUntracked(self):
        from vcstools.git import GitClient
        client = GitClient(self.readonly_path)
        self.assertTrue(client.path_exists())
        self.assertTrue(client.detect_presence())
        self.assertEquals('A  ./added.txt\n D ./deleted-fs.txt\nD  ./deleted.txt\n M ./modified-fs.txt\nM  ./modified.txt\n?? ./added-fs.txt\n', client.get_status(untracked=True))
