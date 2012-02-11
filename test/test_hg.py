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
import struct
import sys
import unittest
import subprocess
import tempfile
import shutil

from vcstools.hg import HgClient

class HGClientTestSetups(unittest.TestCase):

    @classmethod
    def setUpClass(self):

        directory = tempfile.mkdtemp()
        self.directories = dict(setUp=directory)
        remote_path = os.path.join(directory, "remote")
        os.makedirs(remote_path)

        # create a "remote" repo
        subprocess.check_call(["hg", "init"], cwd=remote_path)
        subprocess.check_call(["touch", "fixed.txt"], cwd=remote_path)
        subprocess.check_call(["hg", "add", "fixed.txt"], cwd=remote_path)
        subprocess.check_call(["hg", "commit", "-m", "initial"], cwd=remote_path)
        
        po = subprocess.Popen(["hg", "log", "--template", "'{node|short}'", "-l1"], cwd=remote_path, stdout=subprocess.PIPE)
        self.local_version_init = po.stdout.read().rstrip("'").lstrip("'")
        # in hg, tagging creates an own changeset, so we need to fetch version before tagging
        subprocess.check_call(["hg", "tag", "test_tag"], cwd=remote_path)

        
        # files to be modified in "local" repo
        subprocess.check_call(["touch", "modified.txt"], cwd=remote_path)
        subprocess.check_call(["touch", "modified-fs.txt"], cwd=remote_path)
        subprocess.check_call(["hg", "add", "modified.txt", "modified-fs.txt"], cwd=remote_path)
        subprocess.check_call(["hg", "commit", "-m", "initial"], cwd=remote_path)
        po = subprocess.Popen(["hg", "log", "--template", "'{node|short}'", "-l1"], cwd=remote_path, stdout=subprocess.PIPE)
        self.local_version_second = po.stdout.read().rstrip("'").lstrip("'")
        
        subprocess.check_call(["touch", "deleted.txt"], cwd=remote_path)
        subprocess.check_call(["touch", "deleted-fs.txt"], cwd=remote_path)
        subprocess.check_call(["hg", "add", "deleted.txt", "deleted-fs.txt"], cwd=remote_path)
        subprocess.check_call(["hg", "commit", "-m", "modified"], cwd=remote_path)
        po = subprocess.Popen(["hg", "log", "--template", "'{node|short}'", "-l1"], cwd=remote_path, stdout=subprocess.PIPE)
        self.local_version = po.stdout.read().rstrip("'").lstrip("'")

        self.local_path = os.path.join(directory, "local")
        self.local_url = remote_path
        

    @classmethod
    def tearDownClass(self):
        for d in self.directories:
            shutil.rmtree(self.directories[d])

    def tearDown(self):
        if os.path.exists(self.local_path):
            shutil.rmtree(self.local_path)

class HGClientTest(HGClientTestSetups):

    def test_get_url_by_reading(self):
        url = self.local_url
        client = HgClient(self.local_path)
        client.checkout(url, self.local_version)
        self.assertTrue(client.path_exists())
        self.assertTrue(client.detect_presence())
        self.assertEqual(client.get_url(), self.local_url)
        self.assertEqual(client.get_version(), self.local_version)
        self.assertEqual(client.get_version(self.local_version_init[0:6]), self.local_version_init)
        self.assertEqual(client.get_version("test_tag"), self.local_version_init)

    def test_get_url_nonexistant(self):
        local_path = "/tmp/dummy"
        client = HgClient(local_path)
        self.assertEqual(client.get_url(), None)

    def test_get_type_name(self):
        local_path = "/tmp/dummy"
        client = HgClient(local_path)
        self.assertEqual(client.get_vcs_type_name(), 'hg')

    def test_checkout(self):
        url = self.local_url
        client = HgClient(self.local_path)
        self.assertFalse(client.path_exists())
        self.assertFalse(client.detect_presence())
        self.assertTrue(client.checkout(url))
        self.assertTrue(client.path_exists())
        self.assertTrue(client.detect_presence())
        self.assertEqual(client.get_path(), self.local_path)
        self.assertEqual(client.get_url(), url)
        self.assertEqual(client.get_version(), self.local_version)

    def test_checkout_emptystringversion(self):
        # special test to check that version '' means the same as None
        url = self.local_url
        client = HgClient(self.local_path)
        self.assertTrue(client.checkout(url, ''))
        self.assertEqual(client.get_version(), self.local_version)
        
    def test_checkout_into_subdir_without_existing_parent(self): # test for #3497
        local_path = os.path.join(self.local_path, "nonexistant_subdir")
        url = self.local_url
        client = HgClient(local_path)
        self.assertFalse(client.path_exists())
        self.assertFalse(client.detect_presence())
        self.assertTrue(client.checkout(url))
        self.assertTrue(client.path_exists())
        self.assertTrue(client.detect_presence())
        self.assertEqual(client.get_path(), local_path)
        self.assertEqual(client.get_url(), url)

    def test_checkout_specific_version_and_update(self):
        url = self.local_url
        version = self.local_version
        client = HgClient(self.local_path)
        self.assertFalse(client.path_exists())
        self.assertFalse(client.detect_presence())
        self.assertFalse(client.detect_presence())
        self.assertTrue(client.checkout(url, version))
        self.assertTrue(client.path_exists())
        self.assertTrue(client.detect_presence())
        self.assertEqual(client.get_path(), self.local_path)
        self.assertEqual(client.get_url(), url)
        self.assertEqual(client.get_version(), version)
        
        new_version = self.local_version_second
        self.assertTrue(client.update(new_version))
        self.assertEqual(client.get_version(), new_version)
       

class HGDiffStatClientTest(HGClientTestSetups):

    @classmethod
    def setUpClass(self):
        HGClientTestSetups.setUpClass()
        url = self.local_url
        client = HgClient(self.local_path)
        client.checkout(url)
        # after setting up "local" repo, change files and make some changes
        subprocess.check_call(["rm", "deleted-fs.txt"], cwd=self.local_path)
        subprocess.check_call(["hg", "rm", "deleted.txt"], cwd=self.local_path)
        f = io.open(os.path.join(self.local_path, "modified.txt"), 'a')
        f.write(u'0123456789abcdef')
        f.close()
        f = io.open(os.path.join(self.local_path, "modified-fs.txt"), 'a')
        f.write(u'0123456789abcdef')
        f.close()
        f = io.open(os.path.join(self.local_path, "added-fs.txt"), 'w')
        f.write(u'0123456789abcdef')
        f.close()
        f = io.open(os.path.join(self.local_path, "added.txt"), 'w')
        f.write(u'0123456789abcdef')
        f.close()
        subprocess.check_call(["hg", "add", "added.txt"], cwd=self.local_path)

    def tearDown(self):
        pass
        
    def test_diff(self):

        client = HgClient(self.local_path)
        self.assertTrue(client.path_exists())
        self.assertTrue(client.detect_presence())
        self.assertEquals('diff --git ./added.txt ./added.txt\nnew file mode 100644\n--- /dev/null\n+++ ./added.txt\n@@ -0,0 +1,1 @@\n+0123456789abcdef\n\\ No newline at end of file\ndiff --git ./deleted.txt ./deleted.txt\ndeleted file mode 100644\ndiff --git ./modified-fs.txt ./modified-fs.txt\n--- ./modified-fs.txt\n+++ ./modified-fs.txt\n@@ -0,0 +1,1 @@\n+0123456789abcdef\n\\ No newline at end of file\ndiff --git ./modified.txt ./modified.txt\n--- ./modified.txt\n+++ ./modified.txt\n@@ -0,0 +1,1 @@\n+0123456789abcdef\n\\ No newline at end of file\n\n', client.get_diff())

    def test_diff_relpath(self):

        client = HgClient(self.local_path)
        self.assertTrue(client.path_exists())
        self.assertTrue(client.detect_presence())

        self.assertEquals('diff --git local/added.txt local/added.txt\nnew file mode 100644\n--- /dev/null\n+++ local/added.txt\n@@ -0,0 +1,1 @@\n+0123456789abcdef\n\\ No newline at end of file\ndiff --git local/deleted.txt local/deleted.txt\ndeleted file mode 100644\ndiff --git local/modified-fs.txt local/modified-fs.txt\n--- local/modified-fs.txt\n+++ local/modified-fs.txt\n@@ -0,0 +1,1 @@\n+0123456789abcdef\n\\ No newline at end of file\ndiff --git local/modified.txt local/modified.txt\n--- local/modified.txt\n+++ local/modified.txt\n@@ -0,0 +1,1 @@\n+0123456789abcdef\n\\ No newline at end of file\n\n', client.get_diff(basepath=os.path.dirname(self.local_path)))

    def test_get_version_modified(self):
        client = HgClient(self.local_path)
        self.assertFalse(client.get_version().endswith('+'))
    
    def test_status(self):
        client = HgClient(self.local_path)
        self.assertTrue(client.path_exists())
        self.assertTrue(client.detect_presence())
        self.assertEquals('M modified-fs.txt\nM modified.txt\nA added.txt\nR deleted.txt\n! deleted-fs.txt\n', client.get_status())

    def test_status_relpath(self):
        client = HgClient(self.local_path)
        self.assertTrue(client.path_exists())
        self.assertTrue(client.detect_presence())
        self.assertEquals('M local/modified-fs.txt\nM local/modified.txt\nA local/added.txt\nR local/deleted.txt\n! local/deleted-fs.txt\n', client.get_status(basepath=os.path.dirname(self.local_path)))

    def testStatusUntracked(self):
        client = HgClient(self.local_path)
        self.assertTrue(client.path_exists())
        self.assertTrue(client.detect_presence())
        self.assertEquals('M modified-fs.txt\nM modified.txt\nA added.txt\nR deleted.txt\n! deleted-fs.txt\n? added-fs.txt\n', client.get_status(untracked=True))


    def test_hg_diff_path_change_None(self):
        from vcstools.hg import _hg_diff_path_change
        self.assertEqual(_hg_diff_path_change(None, '/tmp/dummy'), None)

