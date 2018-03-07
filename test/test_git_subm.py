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
import unittest
import subprocess
import tempfile
import shutil
import tarfile
import filecmp
from contextlib import closing

from vcstools.git import GitClient


class GitClientTestSetups(unittest.TestCase):

    @classmethod
    def setUpClass(self):

        self.root_directory = tempfile.mkdtemp()
        # helpful when setting tearDown to pass
        self.directories = dict(setUp=self.root_directory)
        self.remote_dir = os.path.join(self.root_directory, "remote")
        self.repo_path = os.path.join(self.remote_dir, "repo")
        self.submodule_path = os.path.join(self.remote_dir, "submodule")
        self.subsubmodule_path = os.path.join(self.remote_dir, "subsubmodule")
        self.local_path = os.path.join(self.root_directory, "local")
        self.sublocal_path = os.path.join(self.local_path, "submodule")
        self.sublocal2_path = os.path.join(self.local_path, "submodule2")
        self.subsublocal_path = os.path.join(self.sublocal_path, "subsubmodule")
        self.subsublocal2_path = os.path.join(self.sublocal2_path, "subsubmodule")
        self.export_path = os.path.join(self.root_directory, "export")
        self.subexport_path = os.path.join(self.export_path, "submodule")
        self.subexport2_path = os.path.join(self.export_path, "submodule2")
        self.subsubexport_path = os.path.join(self.subexport_path, "subsubmodule")
        self.subsubexport2_path = os.path.join(self.subexport2_path, "subsubmodule")
        os.makedirs(self.repo_path)
        os.makedirs(self.submodule_path)
        os.makedirs(self.subsubmodule_path)

        # create a "remote" repo
        subprocess.check_call("git init", shell=True, cwd=self.repo_path)
        subprocess.check_call("touch fixed.txt", shell=True, cwd=self.repo_path)
        subprocess.check_call("git add fixed.txt", shell=True, cwd=self.repo_path)
        subprocess.check_call("git commit -m initial", shell=True, cwd=self.repo_path)
        subprocess.check_call("git tag test_tag", shell=True, cwd=self.repo_path)
        subprocess.check_call("git branch initial_branch", shell=True, cwd=self.repo_path)
        po = subprocess.Popen("git log -n 1 --pretty=format:\"%H\"", shell=True,
                              cwd=self.repo_path, stdout=subprocess.PIPE)
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
        subprocess.check_call("git submodule add %s %s" % (self.subsubmodule_path, "subsubmodule"),
                              shell=True, cwd=self.submodule_path)
        subprocess.check_call("git submodule init", shell=True, cwd=self.submodule_path)
        subprocess.check_call("git submodule update", shell=True, cwd=self.submodule_path)
        subprocess.check_call("git commit -m subsubmodule", shell=True, cwd=self.submodule_path)

        po = subprocess.Popen("git log -n 1 --pretty=format:\"%H\"", shell=True,
                              cwd=self.subsubmodule_path, stdout=subprocess.PIPE)
        self.subsubversion_final = po.stdout.read().decode('UTF-8').rstrip('"').lstrip('"')

        po = subprocess.Popen("git log -n 1 --pretty=format:\"%H\"", shell=True,
                              cwd=self.submodule_path, stdout=subprocess.PIPE)
        self.subversion_final = po.stdout.read().decode('UTF-8').rstrip('"').lstrip('"')

        # attach submodule somewhere, only in test_branch first
        subprocess.check_call("git checkout master -b test_branch", shell=True, cwd=self.repo_path)
        subprocess.check_call("git submodule add %s %s" % (self.submodule_path,
                                                           "submodule2"), shell=True, cwd=self.repo_path)

        # this is needed only if git <= 1.7, during the time when submodules were being introduced (from 1.5.3)
        subprocess.check_call("git submodule init", shell=True, cwd=self.repo_path)
        subprocess.check_call("git submodule update", shell=True, cwd=self.repo_path)

        subprocess.check_call("git commit -m submodule", shell=True, cwd=self.repo_path)

        po = subprocess.Popen("git log -n 1 --pretty=format:\"%H\"", shell=True,
                              cwd=self.repo_path, stdout=subprocess.PIPE)
        self.version_test = po.stdout.read().decode('UTF-8').rstrip('"').lstrip('"')

        # attach submodule using relative url, only in test_sub_relative
        subprocess.check_call("git checkout master -b test_sub_relative", shell=True, cwd=self.repo_path)
        subprocess.check_call("git submodule add %s %s" % (os.path.join('..', os.path.basename(self.submodule_path)),
                                                           "submodule"), shell=True, cwd=self.repo_path)

        # this is needed only if git <= 1.7, during the time when submodules were being introduced (from 1.5.3)
        subprocess.check_call("git submodule init", shell=True, cwd=self.repo_path)
        subprocess.check_call("git submodule update", shell=True, cwd=self.repo_path)

        subprocess.check_call("git commit -m submodule", shell=True, cwd=self.repo_path)

        po = subprocess.Popen("git log -n 1 --pretty=format:\"%H\"", shell=True,
                              cwd=self.repo_path, stdout=subprocess.PIPE)
        self.version_relative = po.stdout.read().decode('UTF-8').rstrip('"').lstrip('"')

        # attach submodule to remote on master. CAREFUL : submodule2 is still in working tree (git does not clean it)
        subprocess.check_call("git checkout master", shell=True, cwd=self.repo_path)
        subprocess.check_call("git submodule add %s %s" % (self.submodule_path, "submodule"),
                              shell=True, cwd=self.repo_path)

        # this is needed only if git <= 1.7, during the time when submodules were being introduced (from 1.5.3)
        subprocess.check_call("git submodule init", shell=True, cwd=self.repo_path)
        subprocess.check_call("git submodule update", shell=True, cwd=self.repo_path)

        subprocess.check_call("git commit -m submodule", shell=True, cwd=self.repo_path)

        po = subprocess.Popen("git log -n 1 --pretty=format:\"%H\"", shell=True,
                              cwd=self.repo_path, stdout=subprocess.PIPE)
        self.version_final = po.stdout.read().decode('UTF-8').rstrip('"').lstrip('"')
        subprocess.check_call("git tag last_tag", shell=True, cwd=self.repo_path)

        print("setup done\n\n")

    @classmethod
    def tearDownClass(self):
        for d in self.directories:
            shutil.rmtree(self.directories[d])

    def tearDown(self):
        if os.path.exists(self.local_path):
            shutil.rmtree(self.local_path)
        if os.path.exists(self.export_path):
            shutil.rmtree(self.export_path)


class GitClientTest(GitClientTestSetups):

    def test_checkout_master_with_subs(self):
        url = self.repo_path
        client = GitClient(self.local_path)
        subclient = GitClient(self.sublocal_path)
        subsubclient = GitClient(self.subsublocal_path)
        self.assertFalse(client.path_exists())
        self.assertFalse(client.detect_presence())
        self.assertTrue(client.checkout(url))
        self.assertTrue(client.path_exists())
        self.assertTrue(client.detect_presence())
        self.assertEqual(self.version_final, client.get_version())
        self.assertTrue(subclient.path_exists())
        self.assertTrue(subclient.detect_presence())
        self.assertEqual(self.subversion_final, subclient.get_version())
        self.assertTrue(subsubclient.path_exists())
        self.assertTrue(subsubclient.detect_presence())
        self.assertEqual(self.subsubversion_final, subsubclient.get_version())

    def test_export_master(self):
        url = self.repo_path
        client = GitClient(self.local_path)
        subclient = GitClient(self.sublocal_path)
        subsubclient = GitClient(self.subsublocal_path)
        self.assertFalse(client.path_exists())
        self.assertFalse(client.detect_presence())
        self.assertFalse(os.path.exists(self.export_path))
        self.assertTrue(client.checkout(url))
        self.assertTrue(client.path_exists())
        self.assertTrue(subclient.path_exists())
        self.assertTrue(subsubclient.path_exists())
        tarpath = client.export_repository("master", self.export_path)
        self.assertEqual(tarpath, self.export_path + '.tar.gz')
        os.mkdir(self.export_path)
        with closing(tarfile.open(tarpath, "r:gz")) as tarf:
            tarf.extractall(self.export_path)
        subsubdirdiff = filecmp.dircmp(self.subsubexport_path, self.subsublocal_path, ignore=['.git', '.gitmodules'])
        self.assertEqual(subsubdirdiff.left_only, [])
        self.assertEqual(subsubdirdiff.right_only, [])
        self.assertEqual(subsubdirdiff.diff_files, [])
        subdirdiff = filecmp.dircmp(self.subexport_path, self.sublocal_path, ignore=['.git', '.gitmodules'])
        self.assertEqual(subdirdiff.left_only, [])
        self.assertEqual(subdirdiff.right_only, [])
        self.assertEqual(subdirdiff.diff_files, [])
        dirdiff = filecmp.dircmp(self.export_path, self.local_path, ignore=['.git', '.gitmodules'])
        self.assertEqual(dirdiff.left_only, [])
        self.assertEqual(dirdiff.right_only, [])
        self.assertEqual(dirdiff.diff_files, [])

    def test_export_relative(self):
        url = self.repo_path
        client = GitClient(self.local_path)
        subclient = GitClient(self.sublocal_path)
        subsubclient = GitClient(self.subsublocal_path)
        self.assertFalse(client.path_exists())
        self.assertFalse(client.detect_presence())
        self.assertFalse(os.path.exists(self.export_path))
        self.assertTrue(client.checkout(url, "test_sub_relative"))
        self.assertTrue(client.path_exists())
        self.assertTrue(subclient.path_exists())
        self.assertTrue(subsubclient.path_exists())
        #subprocess.call(["tree", self.root_directory])
        tarpath = client.export_repository("test_sub_relative", self.export_path)
        self.assertEqual(tarpath, self.export_path + '.tar.gz')
        os.mkdir(self.export_path)
        with closing(tarfile.open(tarpath, "r:gz")) as tarf:
            tarf.extractall(self.export_path)
        subsubdirdiff = filecmp.dircmp(self.subsubexport_path, self.subsublocal_path, ignore=['.git', '.gitmodules'])
        self.assertEqual(subsubdirdiff.left_only, [])
        self.assertEqual(subsubdirdiff.right_only, [])
        self.assertEqual(subsubdirdiff.diff_files, [])
        subdirdiff = filecmp.dircmp(self.subexport_path, self.sublocal_path, ignore=['.git', '.gitmodules'])
        self.assertEqual(subdirdiff.left_only, [])
        self.assertEqual(subdirdiff.right_only, [])
        self.assertEqual(subdirdiff.diff_files, [])
        dirdiff = filecmp.dircmp(self.export_path, self.local_path, ignore=['.git', '.gitmodules'])
        self.assertEqual(dirdiff.left_only, [])
        self.assertEqual(dirdiff.right_only, [])
        self.assertEqual(dirdiff.diff_files, [])

    def test_export_branch(self):
        url = self.repo_path
        client = GitClient(self.local_path)
        subclient = GitClient(self.sublocal_path)
        subclient2 = GitClient(self.sublocal2_path)
        subsubclient = GitClient(self.subsublocal_path)
        subsubclient2 = GitClient(self.subsublocal2_path)
        self.assertFalse(client.path_exists())
        self.assertFalse(client.detect_presence())
        self.assertFalse(os.path.exists(self.export_path))
        self.assertTrue(client.checkout(url, version='master'))
        self.assertTrue(client.path_exists())
        self.assertTrue(subclient.path_exists())
        self.assertTrue(subsubclient.path_exists())
        self.assertFalse(subclient2.path_exists())
        self.assertFalse(subsubclient2.path_exists())
        # we need first to retrieve locally the branch we want to export
        self.assertTrue(client.update(version='test_branch'))
        self.assertTrue(client.path_exists())
        # git leaves old submodule around by default
        self.assertTrue(subclient.path_exists())
        self.assertTrue(subsubclient.path_exists())
        # new submodule should be there
        self.assertTrue(subclient2.path_exists())
        self.assertTrue(subsubclient2.path_exists())

        tarpath = client.export_repository("test_branch", self.export_path)
        self.assertEqual(tarpath, self.export_path + '.tar.gz')
        os.mkdir(self.export_path)
        with closing(tarfile.open(tarpath, "r:gz")) as tarf:
            tarf.extractall(self.export_path)

        # Checking that we have only submodule2 in our export
        self.assertFalse(os.path.exists(self.subexport_path))
        self.assertFalse(os.path.exists(self.subsubexport_path))
        self.assertTrue(os.path.exists(self.subexport2_path))
        self.assertTrue(os.path.exists(self.subsubexport2_path))

        # comparing with test_branch version ( currently checked-out )
        subsubdirdiff = filecmp.dircmp(self.subsubexport2_path, self.subsublocal_path, ignore=['.git', '.gitmodules'])
        self.assertEqual(subsubdirdiff.left_only, [])  # same subsubfixed.txt in both subsubmodule/
        self.assertEqual(subsubdirdiff.right_only, [])
        self.assertEqual(subsubdirdiff.diff_files, [])
        subdirdiff = filecmp.dircmp(self.subexport2_path, self.sublocal_path, ignore=['.git', '.gitmodules'])
        self.assertEqual(subdirdiff.left_only, [])
        self.assertEqual(subdirdiff.right_only, [])
        self.assertEqual(subdirdiff.diff_files, [])
        dirdiff = filecmp.dircmp(self.export_path, self.local_path, ignore=['.git', '.gitmodules'])
        self.assertEqual(dirdiff.left_only, [])
        # submodule is still there on local_path (git default behavior)
        self.assertEqual(dirdiff.right_only, ['submodule'])
        self.assertEqual(dirdiff.diff_files, [])

    def test_export_hash(self):
        url = self.repo_path
        client = GitClient(self.local_path)
        subclient = GitClient(self.sublocal_path)
        subclient2 = GitClient(self.sublocal2_path)
        subsubclient = GitClient(self.subsublocal_path)
        subsubclient2 = GitClient(self.subsublocal2_path)
        self.assertFalse(client.path_exists())
        self.assertFalse(client.detect_presence())
        self.assertFalse(os.path.exists(self.export_path))
        self.assertTrue(client.checkout(url, version='master'))
        self.assertTrue(client.path_exists())
        self.assertTrue(subclient.path_exists())
        self.assertTrue(subsubclient.path_exists())
        self.assertFalse(subclient2.path_exists())
        self.assertFalse(subsubclient2.path_exists())
        # we need first to retrieve locally the hash we want to export
        self.assertTrue(client.update(version=self.version_test))
        self.assertTrue(client.path_exists())
        # git leaves old submodule around by default
        self.assertTrue(subclient.path_exists())
        self.assertTrue(subsubclient.path_exists())
        # new submodule should be there
        self.assertTrue(subclient2.path_exists())
        self.assertTrue(subsubclient2.path_exists())

        tarpath = client.export_repository(self.version_test, self.export_path)
        self.assertEqual(tarpath, self.export_path + '.tar.gz')
        os.mkdir(self.export_path)
        with closing(tarfile.open(tarpath, "r:gz")) as tarf:
            tarf.extractall(self.export_path)

        # Checking that we have only submodule2 in our export
        self.assertFalse(os.path.exists(self.subexport_path))
        self.assertFalse(os.path.exists(self.subsubexport_path))
        self.assertTrue(os.path.exists(self.subexport2_path))
        self.assertTrue(os.path.exists(self.subsubexport2_path))

        # comparing with version_test ( currently checked-out )
        subsubdirdiff = filecmp.dircmp(self.subsubexport2_path, self.subsublocal_path, ignore=['.git', '.gitmodules'])
        self.assertEqual(subsubdirdiff.left_only, [])  # same subsubfixed.txt in both subsubmodule/
        self.assertEqual(subsubdirdiff.right_only, [])
        self.assertEqual(subsubdirdiff.diff_files, [])
        subdirdiff = filecmp.dircmp(self.subexport2_path, self.sublocal_path, ignore=['.git', '.gitmodules'])
        self.assertEqual(subdirdiff.left_only, [])
        self.assertEqual(subdirdiff.right_only, [])
        self.assertEqual(subdirdiff.diff_files, [])
        dirdiff = filecmp.dircmp(self.export_path, self.local_path, ignore=['.git', '.gitmodules'])
        self.assertEqual(dirdiff.left_only, [])
        # submodule is still there on local_path (git default behavior)
        self.assertEqual(dirdiff.right_only, ['submodule'])
        self.assertEqual(dirdiff.diff_files, [])

    def test_checkout_branch_without_subs(self):
        url = self.repo_path
        client = GitClient(self.local_path)
        subclient = GitClient(self.sublocal_path)
        subsubclient = GitClient(self.subsublocal_path)
        self.assertFalse(client.path_exists())
        self.assertFalse(client.detect_presence())
        self.assertTrue(client.checkout(url, version='initial_branch'))
        self.assertTrue(client.path_exists())
        self.assertTrue(client.detect_presence())
        self.assertEqual(self.version_init, client.get_version())
        self.assertFalse(subclient.path_exists())
        self.assertFalse(subsubclient.path_exists())

    def test_checkout_test_branch_with_subs(self):
        url = self.repo_path
        client = GitClient(self.local_path)
        subclient = GitClient(self.sublocal_path)
        subsubclient = GitClient(self.subsublocal_path)
        subclient2 = GitClient(self.sublocal2_path)
        subsubclient2 = GitClient(self.subsublocal2_path)
        self.assertFalse(client.path_exists())
        self.assertFalse(client.detect_presence())
        self.assertTrue(client.checkout(url, version='test_branch'))
        self.assertTrue(client.path_exists())
        self.assertTrue(client.detect_presence())
        self.assertEqual(self.version_test, client.get_version())
        self.assertFalse(subclient.path_exists())
        self.assertFalse(subsubclient.path_exists())
        self.assertTrue(subclient2.path_exists())
        self.assertTrue(subsubclient2.path_exists())

    def test_checkout_master_with_subs2(self):
        url = self.repo_path
        client = GitClient(self.local_path)
        subclient = GitClient(self.sublocal_path)
        subsubclient = GitClient(self.subsublocal_path)
        subclient2 = GitClient(self.sublocal2_path)
        subsubclient2 = GitClient(self.subsublocal2_path)
        self.assertFalse(client.path_exists())
        self.assertFalse(client.detect_presence())
        self.assertTrue(client.checkout(url, version='master'))
        self.assertTrue(client.path_exists())
        self.assertTrue(client.detect_presence())
        self.assertEqual(self.version_final, client.get_version())
        self.assertTrue(subclient.path_exists())
        self.assertTrue(subsubclient.path_exists())
        self.assertFalse(subclient2.path_exists())
        self.assertFalse(subsubclient2.path_exists())

    def test_switch_branches(self):
        url = self.repo_path
        client = GitClient(self.local_path)
        subclient = GitClient(self.sublocal_path)
        subclient2 = GitClient(self.sublocal2_path)
        subsubclient = GitClient(self.subsublocal_path)
        subsubclient2 = GitClient(self.subsublocal2_path)
        self.assertFalse(client.path_exists())
        self.assertFalse(client.detect_presence())
        self.assertTrue(client.checkout(url))
        self.assertTrue(client.path_exists())
        self.assertTrue(subclient.path_exists())
        self.assertTrue(subsubclient.path_exists())
        self.assertFalse(subclient2.path_exists())
        new_version = "test_branch"
        self.assertTrue(client.update(new_version))
        # checking that update doesnt make submodule disappear (git default behavior)
        self.assertTrue(subclient2.path_exists())
        self.assertTrue(subsubclient2.path_exists())
        self.assertTrue(subclient.path_exists())
        self.assertTrue(subsubclient.path_exists())
        oldnew_version = "master"
        self.assertTrue(client.update(oldnew_version))
        # checking that update doesnt make submodule2 disappear (git default behavior)
        self.assertTrue(subclient2.path_exists())
        self.assertTrue(subsubclient2.path_exists())
        self.assertTrue(subclient.path_exists())
        self.assertTrue(subsubclient.path_exists())

    def test_switch_branches_retrieve_local_subcommit(self):
        url = self.repo_path
        client = GitClient(self.local_path)
        subclient = GitClient(self.sublocal_path)
        subclient2 = GitClient(self.sublocal2_path)
        subsubclient = GitClient(self.subsublocal_path)
        subsubclient2 = GitClient(self.subsublocal2_path)
        self.assertFalse(client.path_exists())
        self.assertFalse(client.detect_presence())
        self.assertTrue(client.checkout(url))
        self.assertTrue(client.path_exists())
        self.assertTrue(subclient.path_exists())
        self.assertTrue(subsubclient.path_exists())
        self.assertFalse(subclient2.path_exists())
        new_version = "test_branch"
        self.assertTrue(client.update(new_version))
        # checking that update doesnt make submodule disappear (git default behavior)
        self.assertTrue(subclient2.path_exists())
        self.assertTrue(subsubclient2.path_exists())
        self.assertTrue(subclient.path_exists())
        self.assertTrue(subsubclient.path_exists())
        subprocess.check_call("touch submodif.txt", shell=True, cwd=self.sublocal2_path)
        subprocess.check_call("git add submodif.txt", shell=True, cwd=self.sublocal2_path)
        subprocess.check_call("git commit -m submodif", shell=True, cwd=self.sublocal2_path)
        subprocess.check_call("git add submodule2", shell=True, cwd=self.local_path)
        subprocess.check_call("git commit -m submodule2_modif", shell=True, cwd=self.local_path)
        oldnew_version = "master"
        self.assertTrue(client.update(oldnew_version))
        # checking that update doesnt make submodule2 disappear (git default behavior)
        self.assertTrue(subclient2.path_exists())
        self.assertTrue(subsubclient2.path_exists())
        self.assertTrue(subclient.path_exists())
        self.assertTrue(subsubclient.path_exists())
        self.assertTrue(client.update(new_version))
        # checking that update still has submodule with submodif
        self.assertTrue(subclient2.path_exists())
        self.assertTrue(subsubclient2.path_exists())
        self.assertTrue(subclient.path_exists())
        self.assertTrue(subsubclient.path_exists())
        self.assertTrue(os.path.exists(os.path.join(self.sublocal2_path, "submodif.txt")))

    def test_status(self):
        url = self.repo_path
        client = GitClient(self.local_path)
        self.assertTrue(client.checkout(url))
        output = client.get_status(porcelain=True)  # porcelain=True ensures stable format
        self.assertEqual('', output, "Expected empty string, got `{0}`".format(output))

        with open(os.path.join(self.local_path, 'fixed.txt'), 'a') as f:
            f.write('0123456789abcdef')
        subprocess.check_call("touch new.txt", shell=True, cwd=self.local_path)
        with open(os.path.join(self.sublocal_path, 'subfixed.txt'), 'a') as f:
            f.write('abcdef0123456789')
        subprocess.check_call("touch subnew.txt", shell=True, cwd=self.sublocal_path)
        with open(os.path.join(self.subsublocal_path, 'subsubfixed.txt'), 'a') as f:
            f.write('012345cdef')
        subprocess.check_call("touch subsubnew.txt", shell=True, cwd=self.subsublocal_path)

        output = client.get_status(porcelain=True)  # porcelain=True ensures stable format
        self.assertEqual('''\
 M ./fixed.txt
 M ./submodule
 M ./subfixed.txt
 M ./subsubmodule
 M ./subsubfixed.txt''', output.rstrip())

        output = client.get_status(untracked=True, porcelain=True)
        self.assertEqual('''\
 M ./fixed.txt
 M ./submodule
?? ./new.txt
 M ./subfixed.txt
 M ./subsubmodule
?? ./subnew.txt
 M ./subsubfixed.txt
?? ./subsubnew.txt''', output.rstrip())

        output = client.get_status(
            basepath=os.path.dirname(self.local_path),
            untracked=True,
            porcelain=True)
        self.assertEqual('''\
 M local/fixed.txt
 M local/submodule
?? local/new.txt
 M local/subfixed.txt
 M local/subsubmodule
?? local/subnew.txt
 M local/subsubfixed.txt
?? local/subsubnew.txt''', output.rstrip())

    def test_diff(self):
        url = self.repo_path
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
        self.assertTrue('''\
diff --git ./fixed.txt ./fixed.txt
index e69de29..454f6b3 100644
--- ./fixed.txt
+++ ./fixed.txt
@@ -0,0 +1 @@
+0123456789abcdef
\\ No newline at end of file''' in output)
        self.assertTrue('''\
diff --git ./submodule/subsubmodule/subsubfixed.txt ./submodule/subsubmodule/subsubfixed.txt
index e69de29..1a332dc 100644
--- ./submodule/subsubmodule/subsubfixed.txt
+++ ./submodule/subsubmodule/subsubfixed.txt
@@ -0,0 +1 @@
+012345cdef
\\ No newline at end of file''' in output)

        output = client.get_diff(basepath=os.path.dirname(self.local_path))
        self.assertEqual(1174, len(output))
        self.assertTrue('''\
diff --git local/fixed.txt local/fixed.txt
index e69de29..454f6b3 100644
--- local/fixed.txt
+++ local/fixed.txt
@@ -0,0 +1 @@
+0123456789abcdef
\ No newline at end of file''' in output, output)
        self.assertTrue('''
diff --git local/submodule/subsubmodule/subsubfixed.txt local/submodule/subsubmodule/subsubfixed.txt
index e69de29..1a332dc 100644
--- local/submodule/subsubmodule/subsubfixed.txt
+++ local/submodule/subsubmodule/subsubfixed.txt
@@ -0,0 +1 @@
+012345cdef
\ No newline at end of file''' in output, output)
