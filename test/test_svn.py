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
import sys
import unittest
import subprocess
import tempfile
import shutil
import re

class SvnClientTestSetups(unittest.TestCase):

    @classmethod
    def setUpClass(self):
        from vcstools.svn import SvnClient
        directory = tempfile.mkdtemp()
        self.directories = dict(setUp=directory)
        remote_path = os.path.join(directory, "remote")
        init_path = os.path.join(directory, "remote")
        
        # create a "remote" repo
        subprocess.check_call(["svnadmin", "create", remote_path], cwd=directory)
        self.readonly_url = "file://localhost"+remote_path
        
        # create an "init" repo to feed remote repo
        subprocess.check_call(["svn", "checkout", self.readonly_url, init_path], cwd=directory)
        
        subprocess.check_call(["touch", "fixed.txt"], cwd=init_path)
        subprocess.check_call(["svn", "add", "fixed.txt"], cwd=init_path)
        subprocess.check_call(["svn", "commit", "-m", "initial"], cwd=init_path)
                
        self.readonly_version_init = "-r1"
        
        # files to be modified in "local" repo
        subprocess.check_call(["touch", "modified.txt"], cwd=init_path)
        subprocess.check_call(["touch", "modified-fs.txt"], cwd=init_path)
        subprocess.check_call(["svn", "add", "modified.txt", "modified-fs.txt"], cwd=init_path)
        subprocess.check_call(["svn", "commit", "-m", "initial"], cwd=init_path)
        
        self.readonly_version_second = "-r2"
        
        subprocess.check_call(["touch", "deleted.txt"], cwd=init_path)
        subprocess.check_call(["touch", "deleted-fs.txt"], cwd=init_path)
        subprocess.check_call(["svn", "add", "deleted.txt", "deleted-fs.txt"], cwd=init_path)
        subprocess.check_call(["svn", "commit", "-m", "modified"], cwd=init_path)
        
        self.readonly_version = "-r3"

        self.readonly_path = os.path.join(directory, "readonly")
        client = SvnClient(self.readonly_path)
        client.checkout(self.readonly_url, self.readonly_version)

    @classmethod
    def tearDownClass(self):
        for d in self.directories:
            shutil.rmtree(self.directories[d])


class SvnClientTest(SvnClientTestSetups):

    def test_get_url_by_reading(self):
        from vcstools.svn import SvnClient
        client = SvnClient(self.readonly_path)
        self.assertTrue(client.path_exists())
        self.assertTrue(client.detect_presence())
        self.assertEqual(client.get_url(), self.readonly_url)
        #self.assertEqual(client.get_version(), self.readonly_version)
        self.assertEqual(client.get_version("PREV"), "-r2")
        self.assertEqual(client.get_version("2"), "-r2")
        self.assertEqual(client.get_version("-r2"), "-r2")

    def test_get_type_name(self):
        from vcstools.svn import SvnClient
        local_path = "/tmp/dummy"
        client = SvnClient(local_path)
        self.assertEqual(client.get_vcs_type_name(), 'svn')

    def test_get_url_nonexistant(self):
        from vcstools.svn import SvnClient
        local_path = "/tmp/dummy"
        client = SvnClient(local_path)
        self.assertEqual(client.get_url(), None)

    def test_checkout(self):
        from vcstools.svn import SvnClient
        directory = tempfile.mkdtemp()
        self.directories["checkout_test"] = directory
        local_path = os.path.join(directory, "ros")
        url = self.readonly_url
        client = SvnClient(local_path)
        self.assertFalse(client.path_exists())
        self.assertFalse(client.detect_presence())
        self.assertFalse(client.detect_presence())
        self.assertTrue(client.checkout(url))
        self.assertTrue(client.path_exists())
        self.assertTrue(client.detect_presence())
        self.assertEqual(client.get_path(), local_path)
        self.assertEqual(client.get_url(), url)

        #self.assertEqual(client.get_version(), '-r*')

    def test_checkout_specific_version_and_update_short(self):
        "using just a number as version"
        from vcstools.svn import SvnClient
        directory = tempfile.mkdtemp()
        subdir = "checkout_specific_version_test"
        self.directories[subdir] = directory
        local_path = os.path.join(directory, "ros")
        url = self.readonly_url
        version = "3"
        client = SvnClient(local_path)
        self.assertFalse(client.path_exists())
        self.assertFalse(client.detect_presence())
        self.assertTrue(client.checkout(url, version))
        self.assertTrue(client.path_exists())
        self.assertTrue(client.detect_presence())
        self.assertEqual(client.get_version(), "-r3")
        
        new_version = '2'
        self.assertTrue(client.update(new_version))
        self.assertEqual(client.get_version(), "-r2")

class SvnDiffStatClientTest(SvnClientTestSetups):

    @classmethod
    def setUpClass(self):
        SvnClientTestSetups.setUpClass()
        # after setting up "readonly" repo, change files and make some changes
        subprocess.check_call(["rm", "deleted-fs.txt"], cwd=self.readonly_path)
        subprocess.check_call(["svn", "rm", "deleted.txt"], cwd=self.readonly_path)
        f = io.open(os.path.join(self.readonly_path, "modified.txt"), 'a')
        f.write(u'0123456789abcdef')
        f.close()
        f = io.open(os.path.join(self.readonly_path, "modified-fs.txt"), 'a')
        f.write(u'0123456789abcdef')
        f.close()
        f = io.open(os.path.join(self.readonly_path, "added-fs.txt"), 'w')
        f.write(u'0123456789abcdef')
        f.close()
        f = io.open(os.path.join(self.readonly_path, "added.txt"), 'w')
        f.write(u'0123456789abcdef')
        f.close()
        subprocess.check_call(["svn", "add", "added.txt"], cwd=self.readonly_path)
        
    def assertEqualDiffs(self, expected, actual):
        "True if actual is similar enough to expected, minus svn properties"
        filtered = ''
        # A block starts with \nIndex, and the actual diff goes up to the first line starting with [a-zA-Z], e.g. "Properties changed:"
        for block in actual.split("\nIndex: "):
            if filtered != '':
                # restore "Index: " removed by split()
                block = "Index: " + block
            newblock = ''
            for line in block.splitlines():
                if re.search("[=+-\\@ ].*", line) == None:
                    break
                else:
                    newblock += line + '\n'
            filtered += newblock
        self.assertEquals(expected, filtered, "Assert failed, expected something like '"+ expected+"'\n but got:\n'" + filtered +"'\n, original:\n''" + actual)
            
        
    def test_diff(self):
        from vcstools.svn import SvnClient
        client = SvnClient(self.readonly_path)
        self.assertTrue(client.path_exists())
        self.assertTrue(client.detect_presence())

        self.assertEqualDiffs('Index: added.txt\n===================================================================\n--- added.txt\t(revision 0)\n+++ added.txt\t(revision 0)\n@@ -0,0 +1 @@\n+0123456789abcdef\n\\ No newline at end of file\nIndex: modified-fs.txt\n===================================================================\n--- modified-fs.txt\t(revision 3)\n+++ modified-fs.txt\t(working copy)\n@@ -0,0 +1 @@\n+0123456789abcdef\n\\ No newline at end of file\nIndex: modified.txt\n===================================================================\n--- modified.txt\t(revision 3)\n+++ modified.txt\t(working copy)\n@@ -0,0 +1 @@\n+0123456789abcdef\n\\ No newline at end of file\n',
                          client.get_diff())


    def test_diff_relpath(self):
        from vcstools.svn import SvnClient
        client = SvnClient(self.readonly_path)
        self.assertTrue(client.path_exists())
        self.assertTrue(client.detect_presence())

        print 'Index: readonly/added.txt\n===================================================================\n--- readonly/added.txt\t(revision 0)\n+++ readonly/added.txt\t(revision 0)\n@@ -0,0 +1 @@\n+0123456789abcdef\n\\ No newline at end of file\nIndex: readonly/modified-fs.txt\n===================================================================\n--- readonly/modified-fs.txt\t(revision 3)\n+++ readonly/modified-fs.txt\t(working copy)\n@@ -0,0 +1 @@\n+0123456789abcdef\n\\ No newline at end of file\nIndex: readonly/modified.txt\n===================================================================\n--- readonly/modified.txt\t(revision 3)\n+++ readonly/modified.txt\t(working copy)\n@@ -0,0 +1 @@\n+0123456789abcdef\n\\ No newline at end of file\n'
        print client.get_diff(basepath=os.path.dirname(self.readonly_path))
        
        self.assertEqualDiffs('Index: readonly/added.txt\n===================================================================\n--- readonly/added.txt\t(revision 0)\n+++ readonly/added.txt\t(revision 0)\n@@ -0,0 +1 @@\n+0123456789abcdef\n\\ No newline at end of file\nIndex: readonly/modified-fs.txt\n===================================================================\n--- readonly/modified-fs.txt\t(revision 3)\n+++ readonly/modified-fs.txt\t(working copy)\n@@ -0,0 +1 @@\n+0123456789abcdef\n\\ No newline at end of file\nIndex: readonly/modified.txt\n===================================================================\n--- readonly/modified.txt\t(revision 3)\n+++ readonly/modified.txt\t(working copy)\n@@ -0,0 +1 @@\n+0123456789abcdef\n\\ No newline at end of file\n', client.get_diff(basepath=os.path.dirname(self.readonly_path)))

    def test_status(self):
        from vcstools.svn import SvnClient
        client = SvnClient(self.readonly_path)
        self.assertTrue(client.path_exists())
        self.assertTrue(client.detect_presence())
        self.assertEquals('A       added.txt\nD       deleted.txt\nM       modified-fs.txt\n!       deleted-fs.txt\nM       modified.txt\n', client.get_status())

    def test_status_relpath(self):
        from vcstools.svn import SvnClient
        client = SvnClient(self.readonly_path)
        self.assertTrue(client.path_exists())
        self.assertTrue(client.detect_presence())
        self.assertEquals('A       readonly/added.txt\nD       readonly/deleted.txt\nM       readonly/modified-fs.txt\n!       readonly/deleted-fs.txt\nM       readonly/modified.txt\n', client.get_status(basepath=os.path.dirname(self.readonly_path)))

    def test_status_untracked(self):
        from vcstools.svn import SvnClient
        client = SvnClient(self.readonly_path)
        self.assertTrue(client.path_exists())
        self.assertTrue(client.detect_presence())
        self.assertEquals('?       added-fs.txt\nA       added.txt\nD       deleted.txt\nM       modified-fs.txt\n!       deleted-fs.txt\nM       modified.txt\n', client.get_status(untracked=True))

