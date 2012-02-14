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
import sys
import io
import fnmatch
import shutil
import subprocess
import tempfile
import unittest
from vcstools.bzr import BzrClient

class BzrClientTestSetups(unittest.TestCase):

    @classmethod
    def setUpClass(self):
        try:
            subprocess.check_call(["bzr", "whoami"])
        except subprocess.CalledProcessError as e:
            subprocess.check_call(["bzr", "whoami", '"ros ros@ros.org"'])
        
        directory = tempfile.mkdtemp()
        self.directories = dict(setUp=directory)
        self.remote_path = os.path.join(directory, "remote")
        os.makedirs(self.remote_path)

        # create a "remote" repo
        subprocess.check_call(["bzr", "init"], cwd=self.remote_path)
        subprocess.check_call(["touch", "fixed.txt"], cwd=self.remote_path)
        subprocess.check_call(["bzr", "add", "fixed.txt"], cwd=self.remote_path)
        subprocess.check_call(["bzr", "commit", "-m", "initial"], cwd=self.remote_path)
        subprocess.check_call(["bzr", "tag", "test_tag"], cwd=self.remote_path)
        self.local_version_init = "1"
        
        # files to be modified in "local" repo
        subprocess.check_call(["touch", "modified.txt"], cwd=self.remote_path)
        subprocess.check_call(["touch", "modified-fs.txt"], cwd=self.remote_path)
        subprocess.check_call(["bzr", "add", "modified.txt", "modified-fs.txt"], cwd=self.remote_path)
        subprocess.check_call(["bzr", "commit", "-m", "initial"], cwd=self.remote_path)
        self.local_version_second = "2"
        
        subprocess.check_call(["touch", "deleted.txt"], cwd=self.remote_path)
        subprocess.check_call(["touch", "deleted-fs.txt"], cwd=self.remote_path)
        subprocess.check_call(["bzr", "add", "deleted.txt", "deleted-fs.txt"], cwd=self.remote_path)
        subprocess.check_call(["bzr", "commit", "-m", "modified"], cwd=self.remote_path)
        self.local_version = "3"

        self.local_path = os.path.join(directory, "local")

    @classmethod
    def tearDownClass(self):
        for d in self.directories:
            shutil.rmtree(self.directories[d])

    def tearDown(self):
        if os.path.exists(self.local_path):
            shutil.rmtree(self.local_path)
            
class BzrClientTest(BzrClientTestSetups):

    def test_get_url_by_reading(self):
        client = BzrClient(self.local_path)
        url = self.remote_path
        self.assertFalse(client.path_exists())
        self.assertFalse(client.detect_presence())
        self.assertTrue(client.checkout(url))
        self.assertTrue(client.path_exists())
        self.assertTrue(client.detect_presence())
        self.assertEqual(client.get_url(), self.remote_path)
        self.assertEqual(client.get_version(), self.local_version)
        self.assertEqual(client.get_version(self.local_version_init[0:6]), self.local_version_init)
        self.assertEqual(client.get_version("test_tag"), self.local_version_init)
        
    def test_get_url_nonexistant(self):
        local_path = "/tmp/dummy"
        client = BzrClient(local_path)
        self.assertEqual(client.get_url(), None)

    def test_get_type_name(self):
        local_path = "/tmp/dummy"
        client = BzrClient(local_path)
        self.assertEqual(client.get_vcs_type_name(), 'bzr')

    def test_checkout_invalid(self):
        "makes sure failed checkout results in False, not Exception"
        url = self.remote_path + "foobar"
        client = BzrClient(self.local_path)
        self.assertFalse(client.path_exists())
        self.assertFalse(client.detect_presence())
        self.assertFalse(client.checkout(url))

    def test_checkout_invalid_update(self):
        "makes sure no exception happens on invalid update"
        url = self.remote_path
        client = BzrClient(self.local_path)
        self.assertTrue(client.checkout(url))
        new_version = 'foobar'
        self.assertFalse(client.update(new_version))

    def test_checkout(self):
        url = self.remote_path
        client = BzrClient(self.local_path)
        self.assertFalse(client.path_exists())
        self.assertFalse(client.detect_presence())
        self.assertTrue(client.checkout(url))
        self.assertTrue(client.path_exists())
        self.assertTrue(client.detect_presence())
        self.assertEqual(client.get_path(), self.local_path)
        self.assertEqual(client.get_url(), url)


    def test_checkout_specific_version_and_update(self):
        url = self.remote_path
        version = "1"
        client = BzrClient(self.local_path)
        self.assertFalse(client.path_exists())
        self.assertFalse(client.detect_presence())
        self.assertTrue(client.checkout(url, version))
        self.assertTrue(client.path_exists())
        self.assertTrue(client.detect_presence())
        self.assertEqual(client.get_path(), self.local_path)
        self.assertEqual(client.get_url(), url)
        self.assertEqual(client.get_version(), version)
        
        new_version = '2'
        self.assertTrue(client.update(new_version))
        self.assertEqual(client.get_version(), new_version)
        

# class BzrDiffStatClientTest(BzrClientTestSetups):

#     @classmethod
#     def setUpClass(self):
#         # setup a local repo once for all diff and status test
#         BzrClientTestSetups.setUpClass()
#         url = self.remote_path
#         client = BzrClient(self.local_path)
#         client.checkout(url)
#         # after setting up "local" repo, change files and make some changes
#         subprocess.check_call(["rm", "deleted-fs.txt"], cwd=self.local_path)
#         subprocess.check_call(["bzr", "rm", "deleted.txt"], cwd=self.local_path)
#         f = io.open(os.path.join(self.local_path, "modified.txt"), 'a')
#         f.write(u'0123456789abcdef')
#         f.close()
#         f = io.open(os.path.join(self.local_path, "modified-fs.txt"), 'a')
#         f.write(u'0123456789abcdef')
#         f.close()
#         f = io.open(os.path.join(self.local_path, "added-fs.txt"), 'w')
#         f.write(u'0123456789abcdef')
#         f.close()
#         f = io.open(os.path.join(self.local_path, "added.txt"), 'w')
#         f.write(u'0123456789abcdef')
#         f.close()
#         subprocess.check_call(["bzr", "add", "added.txt"], cwd=self.local_path)

#     def tearDown(self):
#         pass

#     @classmethod
#     def tearDownClass(self):
#         BzrClientTestSetups.tearDownClass()
        
#     def test_diff(self):
#         client = BzrClient(self.local_path)
#         self.assertTrue(client.path_exists())
#         self.assertTrue(client.detect_presence())
#         # using fnmatch because date and time change (remove when bzr reaches diff --format)
#         diff=client.get_diff()
#         self.assertTrue(diff is not None)
#         self.assertTrue(fnmatch.fnmatch(diff,"=== added file 'added.txt'\n--- ./added.txt\t????-??-?? ??:??:?? +0000\n+++ ./added.txt\t????-??-?? ??:??:?? +0000\n@@ -0,0 +1,1 @@\n+0123456789abcdef\n\\ No newline at end of file\n\n=== removed file 'deleted-fs.txt'\n=== removed file 'deleted.txt'\n=== modified file 'modified-fs.txt'\n--- ./modified-fs.txt\t????-??-?? ??:??:?? +0000\n+++ ./modified-fs.txt\t????-??-?? ??:??:?? +0000\n@@ -0,0 +1,1 @@\n+0123456789abcdef\n\\ No newline at end of file\n\n=== modified file 'modified.txt'\n--- ./modified.txt\t????-??-?? ??:??:?? +0000\n+++ ./modified.txt\t????-??-?? ??:??:?? +0000\n@@ -0,0 +1,1 @@\n+0123456789abcdef\n\\ No newline at end of file\n\n"))

#     def test_diff_relpath(self):
#         client = BzrClient(self.local_path)
#         self.assertTrue(client.path_exists())
#         self.assertTrue(client.detect_presence())
#         # using fnmatch because date and time change (remove when bzr introduces diff --format)
#         diff = client.get_diff(basepath=os.path.dirname(self.local_path))
#         self.assertTrue(diff is not None)
#         self.assertTrue(fnmatch.fnmatch(diff, "=== added file 'added.txt'\n--- local/added.txt\t????-??-?? ??:??:?? +0000\n+++ local/added.txt\t????-??-?? ??:??:?? +0000\n@@ -0,0 +1,1 @@\n+0123456789abcdef\n\\ No newline at end of file\n\n=== removed file 'deleted-fs.txt'\n=== removed file 'deleted.txt'\n=== modified file 'modified-fs.txt'\n--- local/modified-fs.txt\t????-??-?? ??:??:?? +0000\n+++ local/modified-fs.txt\t????-??-?? ??:??:?? +0000\n@@ -0,0 +1,1 @@\n+0123456789abcdef\n\\ No newline at end of file\n\n=== modified file 'modified.txt'\n--- local/modified.txt\t????-??-?? ??:??:?? +0000\n+++ local/modified.txt\t????-??-?? ??:??:?? +0000\n@@ -0,0 +1,1 @@\n+0123456789abcdef\n\\ No newline at end of file\n\n"))

#     def test_status(self):
#         client = BzrClient(self.local_path)
#         self.assertTrue(client.path_exists())
#         self.assertTrue(client.detect_presence())
#         self.assertEquals('+N  ./added.txt\n D  ./deleted-fs.txt\n-D  ./deleted.txt\n M  ./modified-fs.txt\n M  ./modified.txt\n', client.get_status())

#     def test_status_relpath(self):
#         client = BzrClient(self.local_path)
#         self.assertTrue(client.path_exists())
#         self.assertTrue(client.detect_presence())
#         self.assertEquals('+N  local/added.txt\n D  local/deleted-fs.txt\n-D  local/deleted.txt\n M  local/modified-fs.txt\n M  local/modified.txt\n', client.get_status(basepath=os.path.dirname(self.local_path)))

#     def test_status_untracked(self):
#         client = BzrClient(self.local_path)
#         self.assertTrue(client.path_exists())
#         self.assertTrue(client.detect_presence())
#         self.assertEquals('?   ./added-fs.txt\n+N  ./added.txt\n D  ./deleted-fs.txt\n-D  ./deleted.txt\n M  ./modified-fs.txt\n M  ./modified.txt\n', client.get_status(untracked=True))
