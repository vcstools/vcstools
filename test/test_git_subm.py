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

from __future__ import unicode_literals

import os
import io
import stat
import struct
import sys
import unittest
import subprocess
import tempfile
import shutil

from vcstools.git import GitClient

class GitClientTestSetups(unittest.TestCase):

    @classmethod
    def setUpClass(self):
       
        self.root_directory = tempfile.mkdtemp()
        # helpful when setting tearDown to pass
        self.directories = dict(setUp=self.root_directory)
        self.remote_path = os.path.join(self.root_directory, "remote")
        self.submodule_path = os.path.join(self.root_directory, "submodule")
        self.subsubmodule_path = os.path.join(self.root_directory, "subsubmodule")
        self.local_path = os.path.join(self.root_directory, "local")
        self.sublocal_path = os.path.join(self.local_path, "submodule")
        self.sublocal2_path = os.path.join(self.local_path, "submodule2")
        self.subsublocal_path = os.path.join(self.sublocal_path, "subsubmodule")
        os.makedirs(self.remote_path)
        os.makedirs(self.submodule_path)
        os.makedirs(self.subsubmodule_path)
        
        # create a "remote" repo
        subprocess.check_call("git init", shell=True, cwd=self.remote_path)
        subprocess.check_call("touch fixed.txt", shell=True, cwd=self.remote_path)
        subprocess.check_call("git add *", shell=True, cwd=self.remote_path)
        subprocess.check_call("git commit -m initial", shell=True, cwd=self.remote_path)
        subprocess.check_call("git tag test_tag", shell=True, cwd=self.remote_path)
        subprocess.check_call("git branch test_branch", shell=True, cwd=self.remote_path)
        po = subprocess.Popen("git log -n 1 --pretty=format:\"%H\"", shell=True, cwd=self.remote_path, stdout=subprocess.PIPE)
        self.version_init = po.stdout.read().decode('UTF-8').rstrip('"').lstrip('"')

        # create a submodule repo
        subprocess.check_call("git init", shell=True, cwd=self.submodule_path)
        subprocess.check_call("touch subfixed.txt", shell=True, cwd=self.submodule_path)
        subprocess.check_call("git add *", shell=True, cwd=self.submodule_path)
        subprocess.check_call("git commit -m initial", shell=True, cwd=self.submodule_path)
        subprocess.check_call("git tag sub_test_tag", shell=True, cwd=self.submodule_path)

        # create a subsubmodule repo
        subprocess.check_call("git init", shell=True, cwd=self.subsubmodule_path)
        subprocess.check_call("touch subsubfixed.txt", shell=True, cwd=self.subsubmodule_path)
        subprocess.check_call("git add *", shell=True, cwd=self.subsubmodule_path)
        subprocess.check_call("git commit -m initial", shell=True, cwd=self.subsubmodule_path)
        subprocess.check_call("git tag subsub_test_tag", shell=True, cwd=self.subsubmodule_path)

        # attach subsubmodule to submodule
        subprocess.check_call("git submodule add %s %s"%(self.subsubmodule_path, "subsubmodule"), shell=True, cwd=self.submodule_path)
        subprocess.check_call("git submodule init", shell=True, cwd=self.submodule_path)
        subprocess.check_call("git submodule update", shell=True, cwd=self.submodule_path)
        subprocess.check_call("git commit -m subsubmodule", shell=True, cwd=self.submodule_path)

        po = subprocess.Popen("git log -n 1 --pretty=format:\"%H\"", shell=True, cwd=self.subsubmodule_path, stdout=subprocess.PIPE)
        self.subsubversion_final = po.stdout.read().decode('UTF-8').rstrip('"').lstrip('"')

        po = subprocess.Popen("git log -n 1 --pretty=format:\"%H\"", shell=True, cwd=self.submodule_path, stdout=subprocess.PIPE)
        self.subversion_final = po.stdout.read().decode('UTF-8').rstrip('"').lstrip('"')

        # attach submodule to remote
        subprocess.check_call("git submodule add %s %s"%(self.submodule_path, "submodule"), shell=True, cwd=self.remote_path)
        subprocess.check_call("git submodule init", shell=True, cwd=self.remote_path)
        subprocess.check_call("git submodule update", shell=True, cwd=self.remote_path)
        subprocess.check_call("git commit -m submodule", shell=True, cwd=self.remote_path)

        po = subprocess.Popen("git log -n 1 --pretty=format:\"%H\"", shell=True, cwd=self.remote_path, stdout=subprocess.PIPE)
        self.version_final = po.stdout.read().decode('UTF-8').rstrip('"').lstrip('"')
        subprocess.check_call("git tag last_tag", shell=True, cwd=self.remote_path)

        # attach submodule somewhere else in test_branch
        subprocess.check_call("git checkout test_branch", shell=True, cwd=self.remote_path)
        subprocess.check_call("git submodule add %s %s"%(self.submodule_path, "submodule2"), shell=True, cwd=self.remote_path)
        subprocess.check_call("git submodule init", shell=True, cwd=self.remote_path)
        subprocess.check_call("git submodule update", shell=True, cwd=self.remote_path)
        subprocess.check_call("git commit -m submodule", shell=True, cwd=self.remote_path)

        # go back to master else clients will checkout test_branch
        subprocess.check_call("git checkout master", shell=True, cwd=self.remote_path)
        
    @classmethod
    def tearDownClass(self):
        for d in self.directories:
            shutil.rmtree(self.directories[d])

    def tearDown(self):
        if os.path.exists(self.local_path):
            shutil.rmtree(self.local_path)
            
    
class GitClientTest(GitClientTestSetups):
    
    def test_checkout_master_with_subs(self):
        url = self.remote_path
        client = GitClient(self.local_path)
        subclient = GitClient(self.sublocal_path)
        subsubclient = GitClient(self.subsublocal_path)
        self.assertFalse(client.path_exists())
        self.assertFalse(client.detect_presence())
        self.assertTrue(client.checkout(url))
        self.assertTrue(client.path_exists())
        self.assertTrue(client.detect_presence())
        self.assertEqual(client.get_version(), self.version_final)
        self.assertTrue(subclient.path_exists())
        self.assertTrue(subclient.detect_presence())
        self.assertEqual(subclient.get_version(), self.subversion_final)
        self.assertTrue(subsubclient.path_exists())
        self.assertTrue(subsubclient.detect_presence())
        self.assertEqual(subsubclient.get_version(), self.subsubversion_final)
        
    def test_switch_branches(self):
        url = self.remote_path
        client = GitClient(self.local_path)
        subclient = GitClient(self.sublocal_path)
        subclient2 = GitClient(self.sublocal2_path)
        subsubclient = GitClient(self.subsublocal_path)
        self.assertFalse(client.path_exists())
        self.assertFalse(client.detect_presence())
        self.assertTrue(client.checkout(url))
        self.assertTrue(client.path_exists())
        self.assertTrue(subclient.path_exists())
        self.assertTrue(subsubclient.path_exists())
        self.assertFalse(subclient2.path_exists())
        new_version = "test_branch"
        self.assertTrue(client.update(new_version))
        self.assertTrue(subclient2.path_exists())

    def test_status(self):
        url = self.remote_path
        client = GitClient(self.local_path)
        self.assertTrue(client.checkout(url))
        output = client.get_status()
        self.assertEqual('', output, output)
        
        with open(os.path.join(self.local_path, 'fixed.txt'), 'a') as f:
            f.write('0123456789abcdef')
        subprocess.check_call("touch new.txt", shell=True, cwd=self.local_path)
        with open(os.path.join(self.sublocal_path, 'subfixed.txt'), 'a') as f:
            f.write('abcdef0123456789')
        subprocess.check_call("touch subnew.txt", shell=True, cwd=self.sublocal_path)
        with open(os.path.join(self.subsublocal_path, 'subsubfixed.txt'), 'a') as f:
            f.write('012345cdef')
        subprocess.check_call("touch subsubnew.txt", shell=True, cwd=self.subsublocal_path)

        output = client.get_status()
        self.assertEqual(' M ./fixed.txt\n M ./submodule\n M ./subfixed.txt\n M ./subsubmodule\n M ./subsubfixed.txt', output.rstrip())

        output = client.get_status(untracked = True)
        self.assertEqual(' M ./fixed.txt\n M ./submodule\n?? ./new.txt\n M ./subfixed.txt\n M ./subsubmodule\n?? ./subnew.txt\n M ./subsubfixed.txt\n?? ./subsubnew.txt', output.rstrip())

        output = client.get_status(basepath=os.path.dirname(self.local_path), untracked = True)
        self.assertEqual(' M local/fixed.txt\n M local/submodule\n?? local/new.txt\n M local/subfixed.txt\n M local/subsubmodule\n?? local/subnew.txt\n M local/subsubfixed.txt\n?? local/subsubnew.txt', output.rstrip())

        
    def test_diff(self):
        url = self.remote_path
        client = GitClient(self.local_path)
        self.assertTrue(client.checkout(url))
        output = client.get_diff()
        self.assertEqual('', output, output)
        
        with open(os.path.join(self.local_path, 'fixed.txt'), 'a') as f:
            f.write('0123456789abcdef')
        subprocess.check_call("touch new.txt", shell=True, cwd=self.local_path)
        with open(os.path.join(self.sublocal_path, 'subfixed.txt'), 'a') as f:
            f.write('abcdef0123456789')
        subprocess.check_call("touch subnew.txt", shell=True, cwd=self.sublocal_path)
        with open(os.path.join(self.subsublocal_path, 'subsubfixed.txt'), 'a') as f:
            f.write('012345cdef')
        subprocess.check_call("touch subsubnew.txt", shell=True, cwd=self.subsublocal_path)

        output = client.get_diff()
        self.assertEqual(1094, len(output))
        self.assertTrue('diff --git ./fixed.txt ./fixed.txt\nindex e69de29..454f6b3 100644\n--- ./fixed.txt\n+++ ./fixed.txt\n@@ -0,0 +1 @@\n+0123456789abcdef\n\\ No newline at end of file' in output)
        self.assertTrue('diff --git ./submodule/subsubmodule/subsubfixed.txt ./submodule/subsubmodule/subsubfixed.txt\nindex e69de29..1a332dc 100644\n--- ./submodule/subsubmodule/subsubfixed.txt\n+++ ./submodule/subsubmodule/subsubfixed.txt\n@@ -0,0 +1 @@\n+012345cdef\n\\ No newline at end of file' in output)
        
        output = client.get_diff(basepath=os.path.dirname(self.local_path))
        self.assertEqual(1174, len(output))
        self.assertTrue('diff --git local/fixed.txt local/fixed.txt\nindex e69de29..454f6b3 100644\n--- local/fixed.txt\n+++ local/fixed.txt\n@@ -0,0 +1 @@\n+0123456789abcdef\n\ No newline at end of file' in output, output)
        self.assertTrue('diff --git local/submodule/subsubmodule/subsubfixed.txt local/submodule/subsubmodule/subsubfixed.txt\nindex e69de29..1a332dc 100644\n--- local/submodule/subsubmodule/subsubfixed.txt\n+++ local/submodule/subsubmodule/subsubfixed.txt\n@@ -0,0 +1 @@\n+012345cdef\n\ No newline at end of file' in output, output)
