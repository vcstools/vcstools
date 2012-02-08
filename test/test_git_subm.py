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
        subprocess.check_call(["git", "init"], cwd=self.remote_path)
        subprocess.check_call(["touch", "fixed.txt"], cwd=self.remote_path)
        subprocess.check_call(["git", "add", "*"], cwd=self.remote_path)
        subprocess.check_call(["git", "commit", "-m", "initial"], cwd=self.remote_path)
        subprocess.check_call(["git", "tag", "test_tag"], cwd=self.remote_path)
        subprocess.check_call(["git", "branch", "test_branch"], cwd=self.remote_path)
        po = subprocess.Popen(["git", "log", "-n", "1", "--pretty=format:\"%H\""], cwd=self.remote_path, stdout=subprocess.PIPE)
        self.version_init = po.stdout.read().rstrip('"').lstrip('"')

        # create a submodule repo
        subprocess.check_call(["git", "init"], cwd=self.submodule_path)
        subprocess.check_call(["touch", "subfixed.txt"], cwd=self.submodule_path)
        subprocess.check_call(["git", "add", "*"], cwd=self.submodule_path)
        subprocess.check_call(["git", "commit", "-m", "initial"], cwd=self.submodule_path)
        subprocess.check_call(["git", "tag", "sub_test_tag"], cwd=self.submodule_path)

        # create a subsubmodule repo
        subprocess.check_call(["git", "init"], cwd=self.subsubmodule_path)
        subprocess.check_call(["touch", "subsubfixed.txt"], cwd=self.subsubmodule_path)
        subprocess.check_call(["git", "add", "*"], cwd=self.subsubmodule_path)
        subprocess.check_call(["git", "commit", "-m", "initial"], cwd=self.subsubmodule_path)
        subprocess.check_call(["git", "tag", "subsub_test_tag"], cwd=self.subsubmodule_path)

        # attach subsubmodule to submodule
        subprocess.check_call(["git", "submodule", "add", self.subsubmodule_path, "subsubmodule"], cwd=self.submodule_path)
        subprocess.check_call(["git", "submodule", "init"], cwd=self.submodule_path)
        subprocess.check_call(["git", "submodule", "update"], cwd=self.submodule_path)
        subprocess.check_call(["git", "commit", "-m", "subsubmodule"], cwd=self.submodule_path)

        po = subprocess.Popen(["git", "log", "-n", "1", "--pretty=format:\"%H\""], cwd=self.subsubmodule_path, stdout=subprocess.PIPE)
        self.subsubversion_final = po.stdout.read().rstrip('"').lstrip('"')

        po = subprocess.Popen(["git", "log", "-n", "1", "--pretty=format:\"%H\""], cwd=self.submodule_path, stdout=subprocess.PIPE)
        self.subversion_final = po.stdout.read().rstrip('"').lstrip('"')

        # attach submodule to remote
        subprocess.check_call(["git", "submodule", "add", self.submodule_path, "submodule"], cwd=self.remote_path)
        subprocess.check_call(["git", "submodule", "init"], cwd=self.remote_path)
        subprocess.check_call(["git", "submodule", "update"], cwd=self.remote_path)
        subprocess.check_call(["git", "commit", "-m", "submodule"], cwd=self.remote_path)

        po = subprocess.Popen(["git", "log", "-n", "1", "--pretty=format:\"%H\""], cwd=self.remote_path, stdout=subprocess.PIPE)
        self.version_final = po.stdout.read().rstrip('"').lstrip('"')
        subprocess.check_call(["git", "tag", "last_tag"], cwd=self.remote_path)

        # attach submodule somewhere else in test_branch
        subprocess.check_call(["git", "checkout", "test_branch"], cwd=self.remote_path)
        subprocess.check_call(["git", "submodule", "add", self.submodule_path, "submodule2"], cwd=self.remote_path)
        subprocess.check_call(["git", "submodule", "init"], cwd=self.remote_path)
        subprocess.check_call(["git", "submodule", "update"], cwd=self.remote_path)
        subprocess.check_call(["git", "commit", "-m", "submodule"], cwd=self.remote_path)

        # go back to master else clients will checkout test_branch
        subprocess.check_call(["git", "checkout", "master"], cwd=self.remote_path)
        
    @classmethod
    def tearDownClass(self):
        for d in self.directories:
            shutil.rmtree(self.directories[d])

    def tearDown(self):
        if os.path.exists(self.local_path):
            shutil.rmtree(self.local_path)
            
    
class GitClientTest(GitClientTestSetups):
    
    def test_checkout_master_with_subs(self):
        from vcstools.git import GitClient
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
        from vcstools.git import GitClient
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
        
