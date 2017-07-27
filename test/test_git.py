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
import threading
import time

from distutils.version import LooseVersion
from vcstools import GitClient
from vcstools.vcs_base import VcsError

try:
    from socketserver import TCPServer, BaseRequestHandler
except ImportError:
    from SocketServer import TCPServer, BaseRequestHandler

os.environ['GIT_AUTHOR_NAME'] = 'Your Name'
os.environ['GIT_COMMITTER_NAME'] = 'Your Name'
os.environ['GIT_AUTHOR_EMAIL'] = 'name@example.com'
os.environ['EMAIL'] = 'Your Name <name@example.com>'


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

class GitSwitchDefaultBranchTest(GitClientTestSetups):
    def test_get_default_remote_version_label(self):
        url = self.remote_path
        client = GitClient(self.local_path)
        self.assertTrue(client.checkout(url))
        self.assertEqual(client.get_default_remote_version_label(), 'master')
        subprocess.check_call("git symbolic-ref HEAD refs/heads/test_branch", shell=True, cwd=self.remote_path)
        self.assertEqual(client.get_default_remote_version_label(), 'test_branch')



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
        self.assertFalse(client._is_local_branch("test_branch"))
        self.assertTrue(client._is_remote_branch("test_branch"))
        self.assertTrue(client.is_tag("test_tag"))
        self.assertFalse(client._is_remote_branch("test_tag"))
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
        self.assertEqual(client._get_branch(), "master")
        self.assertEqual(client._get_branch_parent(), ("master", "origin"))
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
            self.fetches += 1
            return True

        def iff(self, branch_parent, fetch=True, verbose=False):
            self.fast_forwards += 1
            return True

        def isubm(self, verbose=False, timeout=None):
            self.submodules += 1
            return True
        client._do_fetch = types.MethodType(ifetch, client)
        client._do_fast_forward = types.MethodType(iff, client)
        client._update_submodules = types.MethodType(isubm, client)
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
            self.fetches += 1
            return True

        def iff(self, branch_parent, fetch=True, verbose=False):
            self.fast_forwards += 1
            return True

        def isubm(self, verbose=False, timeout=None):
            self.submodules += 1
            return True
        client._do_fetch = types.MethodType(ifetch, client)
        client._do_fast_forward = types.MethodType(iff, client)
        client._update_submodules = types.MethodType(isubm, client)
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
        self.assertEqual(client._get_branch(), "master")
        self.assertEqual(client._get_branch_parent(), ("master", "origin"))
        po = subprocess.Popen("git log --pretty=format:%H", shell=True, cwd=self.local_path, stdout=subprocess.PIPE)
        log = po.stdout.read().decode('UTF-8').strip().splitlines()
        if LooseVersion(client.gitversion) >= LooseVersion('1.8.2'):
            # shallow only contains last commit
            self.assertEqual(1, len(log), log)
        else:
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
        self.assertEqual(client._get_branch_parent(), (branch, "origin"))

        self.assertTrue(client.update(branch))
        self.assertEqual(client._get_branch_parent(), (branch, "origin"))

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
        self.assertTrue(client._is_local_branch(branch))
        self.assertEqual(client.get_path(), self.local_path)
        self.assertEqual(client.get_url(), url)
        self.assertEqual(client.get_version(), self.readonly_version_init)
        self.assertEqual(client._get_branch(), branch)
        self.assertEqual(client._get_branch_parent(), (branch, "origin"))

        self.assertTrue(client.update())  # no arg
        self.assertEqual(client._get_branch(), branch)
        self.assertEqual(client.get_version(), self.readonly_version_init)
        self.assertEqual(client._get_branch_parent(), (branch, "origin"))

        self.assertTrue(client.update(branch))  # same branch arg
        self.assertEqual(client._get_branch(), branch)
        self.assertEqual(client.get_version(), self.readonly_version_init)
        self.assertEqual(client._get_branch_parent(), (branch, "origin"))

        new_branch = 'master'
        self.assertTrue(client.update(new_branch))
        self.assertEqual(client._get_branch(), new_branch)
        self.assertEqual(client._get_branch_parent(), (new_branch, "origin"))

    def test_checkout_local_only_branch_and_update(self):
        # prevent regression on wstool#25: no rebase after switching branch
        url = self.remote_path
        branch = "master"
        client = GitClient(self.local_path)
        self.assertFalse(client.path_exists())
        self.assertFalse(client.detect_presence())
        self.assertTrue(client.checkout(url, branch))
        self.assertTrue(client.path_exists())
        self.assertTrue(client.detect_presence())
        self.assertTrue(client._is_local_branch(branch))

        subprocess.check_call("git reset --hard HEAD~1", shell=True, cwd=self.local_path)
        subprocess.check_call("git checkout -b new_local_branch", shell=True, cwd=self.local_path)

        self.assertTrue(client.update(branch))  # same branch arg
        self.assertEqual(client._get_branch(), branch)
        self.assertEqual(client.get_version(), self.readonly_version)
        self.assertEqual(client._get_branch_parent(), (branch, "origin"))


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
        self.assertEqual(client._get_branch_parent(), (None, None))
        tag = "test_tag"
        self.assertTrue(client.update(tag))
        self.assertEqual(client._get_branch_parent(), (None, None))

        new_branch = 'master'
        self.assertTrue(client.update(new_branch))
        self.assertEqual(client._get_branch_parent(), (new_branch, "origin"))
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

        self.assertTrue(client._get_branch_parent() is not (None, None))

    def test_get_version_not_exist(self):
        client = GitClient(path=self.local_path)
        client.checkout(url=self.remote_path, version='master')
        self.assertEqual(client.get_version(spec='not_exist_version'), None)

    def test_get_branch_parent(self):
        client = GitClient(path=self.local_path)
        client.checkout(url=self.remote_path, version='master')
        self.assertEqual(client._get_branch_parent(), ("master", "origin"))

        # with other remote than origin
        for cmd in ['git remote add remote2 %s' % self.remote_path,
                    'git config --replace-all branch.master.remote remote2']:
            subprocess.check_call(cmd, shell=True, cwd=self.local_path)
        self.assertEqual(client._get_branch_parent(), (None, None))
        self.assertEqual(client._get_branch_parent(fetch=True), ('master', "remote2"))
        # with not actual remote branch
        cmd = 'git config --replace-all branch.master.merge dummy_branch'
        subprocess.check_call(cmd, shell=True, cwd=self.local_path)
        self.assertEqual(client._get_branch_parent(), (None, None))
        # return remote back to original config
        for cmd in [
             'git config --replace-all branch.master.remote origin',
             'git config --replace-all branch.master.merge refs/heads/master']:
            subprocess.check_call(cmd, shell=True, cwd=self.local_path)

        # with detached local status
        client.update(version='test_tag')
        self.assertEqual(client._get_branch_parent(), (None, None))
        # back to master branch
        client.update(version='master')

    def test_get_current_version_label(self):
        client = GitClient(path=self.local_path)
        # with detached local status
        client.checkout(url=self.remote_path, version='test_tag')
        self.assertEqual(client.get_current_version_label(), '<detached>')
        # when difference between local and tracking branch
        client.update(version='master')
        self.assertEqual(client.get_current_version_label(), 'master')
        # with other tracking branch
        cmd = 'git config --replace-all branch.master.merge test_branch'
        subprocess.check_call(cmd, shell=True, cwd=self.local_path)
        self.assertEqual(client.get_current_version_label(),
                         'master < test_branch')
        # with other remote
        for cmd in [
                'git remote add remote2 %s' % self.remote_path,
                'git config --replace-all branch.master.remote remote2',
                'git fetch remote2']:
            subprocess.check_call(cmd, shell=True, cwd=self.local_path)
        self.assertEqual(client.get_current_version_label(),
                         'master < remote2/test_branch')
        # return remote back to original config
        for cmd in [
             'git config --replace-all branch.master.remote origin',
             'git config --replace-all branch.master.merge refs/heads/master']:
            subprocess.check_call(cmd, shell=True, cwd=self.local_path)

    def test_get_remote_version(self):
        url = self.remote_path
        client = GitClient(path=self.local_path)
        client.checkout(url, version='master')
        self.assertEqual(client.get_remote_version(fetch=True), self.readonly_version)
        self.assertEqual(client.get_remote_version(fetch=False), self.readonly_version)
        subprocess.check_call("git reset --hard test_tag", shell=True, cwd=self.local_path)
        self.assertEqual(client.get_remote_version(fetch=True), self.readonly_version)
        client.update(version='test_branch')
        self.assertEqual(client.get_remote_version(fetch=True), self.readonly_version_init)
        client.update(version='test_branch')
        self.assertEqual(client.get_remote_version(fetch=False), self.readonly_version_init)
        # switch tracked branch
        subprocess.check_call('git config --replace-all branch.master.merge test_branch', shell=True, cwd=self.local_path)
        client.update(version='master')
        self.assertEqual(client.get_remote_version(fetch=False), self.readonly_version_init)
        # with other remote
        for cmd in [
                'git remote add remote2 %s' % self.remote_path,
                'git config --replace-all branch.master.remote remote2',
                'git fetch remote2']:
            subprocess.check_call(cmd, shell=True, cwd=self.local_path)
        self.assertEqual(client.get_remote_version(fetch=False), self.readonly_version_init)

    def testDiffClean(self):
        client = GitClient(self.remote_path)
        self.assertEquals('', client.get_diff())

    def testStatusClean(self):
        client = GitClient(self.remote_path)
        self.assertEquals('', client.get_status(porcelain=True))

    def test_get_environment_metadata(self):
        # Verify that metadata is generated
        directory = tempfile.mkdtemp()
        self.directories['local'] = directory
        local_path = os.path.join(directory, "local")
        client = GitClient(local_path)
        self.assertTrue('version' in client.get_environment_metadata())


class GitClientUpdateTest(GitClientTestSetups):

    def test_update_fetch_all_tags(self):
        url = self.remote_path
        client = GitClient(self.local_path)
        self.assertTrue(client.checkout(url, "master"))
        self.assertEqual(client._get_branch(), "master")
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


class GitClientRemoteVersionFetchTest(GitClientTestSetups):

    def test_update_fetch_all_tags(self):
        url = self.remote_path
        client = GitClient(self.local_path)
        self.assertTrue(client.checkout(url, "master"))
        self.assertEqual(client._get_branch(), "master")
        self.assertEqual(client.get_remote_version(fetch=False), self.readonly_version)
        self.assertEqual(client.get_remote_version(fetch=True), self.readonly_version)

        subprocess.check_call("touch new_file.txt", shell=True, cwd=self.remote_path)
        subprocess.check_call("git add *", shell=True, cwd=self.remote_path)
        subprocess.check_call("git commit -m newfile", shell=True, cwd=self.remote_path)

        po = subprocess.Popen("git log -n 1 --pretty=format:\"%H\"", shell=True, cwd=self.remote_path, stdout=subprocess.PIPE)
        remote_new_version = po.stdout.read().decode('UTF-8').rstrip('"').lstrip('"')

        self.assertNotEqual(self.readonly_version, remote_new_version)

        # remote version stays same until we fetch
        self.assertEqual(client.get_remote_version(fetch=False), self.readonly_version)
        self.assertEqual(client.get_remote_version(fetch=True), remote_new_version)
        self.assertEqual(client.get_remote_version(fetch=False), remote_new_version)


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


class GitClientAffectedFiles(GitClientTestSetups):

    def setUp(self):
        client = GitClient(self.local_path)
        client.checkout(self.remote_path)
        # Create some local untracking branch

        subprocess.check_call("git checkout test_tag -b localbranch", shell=True, cwd=self.local_path)
        subprocess.check_call("touch local_file", shell=True, cwd=self.local_path)
        subprocess.check_call("git add local_file", shell=True, cwd=self.local_path)
        subprocess.check_call("git commit -m \"local_file\"", shell=True, cwd=self.local_path)

    def test_get_affected_files(self):
        client = GitClient(self.local_path)
        affected = client.get_affected_files(client.get_log()[0]['id'])

        self.assertEqual(sorted(['local_file']),
                         sorted(affected))

        self.assertEquals(['local_file'], affected)


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
        self.assertTrue(client._is_commit_in_orphaned_subtree(self.dangling_version))
        self.assertFalse(client._is_commit_in_orphaned_subtree(self.no_br_tag_version))
        self.assertFalse(client._is_commit_in_orphaned_subtree(self.diverged_branch_version))

    def test_protect_dangling(self):
        client = GitClient(self.local_path)
        # url = self.remote_path
        self.assertEqual(client._get_branch(), "master")
        tag = "no_br_tag"
        self.assertTrue(client.update(tag))
        self.assertEqual(client._get_branch(), None)
        self.assertEqual(client._get_branch_parent(), (None, None))

        tag = "test_tag"
        self.assertTrue(client.update(tag))
        self.assertEqual(client._get_branch(), None)
        self.assertEqual(client._get_branch_parent(), (None, None))

        # to dangling commit
        sha = self.dangling_version
        self.assertTrue(client.update(sha))
        self.assertEqual(client._get_branch(), None)
        self.assertEqual(client.get_version(), self.dangling_version)
        self.assertEqual(client._get_branch_parent(), (None, None))

        # now HEAD protects the dangling commit, should not be allowed to move off.
        new_branch = 'master'
        self.assertFalse(client.update(new_branch))

    def test_detached_to_branch(self):
        client = GitClient(self.local_path)
        # url = self.remote_path
        self.assertEqual(client._get_branch(), "master")
        tag = "no_br_tag"
        self.assertTrue(client.update(tag))
        self.assertEqual(client._get_branch(), None)
        self.assertEqual(client._get_branch_parent(), (None, None))

        tag = "test_tag"
        self.assertTrue(client.update(tag))
        self.assertEqual(client._get_branch(), None)
        self.assertEqual(client.get_version(), self.readonly_version_init)
        self.assertEqual(client._get_branch_parent(), (None, None))

        #update should not change anything
        self.assertTrue(client.update())  # no arg
        self.assertEqual(client._get_branch(), None)
        self.assertEqual(client.get_version(), self.readonly_version_init)
        self.assertEqual(client._get_branch_parent(), (None, None))

        new_branch = 'master'
        self.assertTrue(client.update(new_branch))
        self.assertEqual(client._get_branch(), new_branch)
        self.assertEqual(client.get_version(), self.readonly_version)
        self.assertEqual(client._get_branch_parent(), (new_branch, "origin"))

    def test_checkout_untracked_branch_and_update(self):
        # difference to tracked branches is that branch parent is None, and we may hop outside lineage
        client = GitClient(self.local_path)
        url = self.remote_path
        branch = "localbranch"
        self.assertEqual(client._get_branch(), "master")
        self.assertTrue(client.path_exists())
        self.assertTrue(client.detect_presence())
        self.assertTrue(client._is_local_branch(branch))
        self.assertEqual(client.get_path(), self.local_path)
        self.assertEqual(client.get_url(), url)
        self.assertTrue(client.update(branch))
        self.assertEqual(client.get_version(), self.untracked_version)
        self.assertEqual(client._get_branch(), branch)
        self.assertEqual(client._get_branch_parent(), (None, None))

        self.assertTrue(client.update())  # no arg
        self.assertEqual(client._get_branch(), branch)
        self.assertEqual(client.get_version(), self.untracked_version)
        self.assertEqual(client._get_branch_parent(), (None, None))

        self.assertTrue(client.update(branch))  # same branch arg
        self.assertEqual(client._get_branch(), branch)
        self.assertEqual(client.get_version(), self.untracked_version)
        self.assertEqual(client._get_branch_parent(), (None, None))

        # to master
        new_branch = 'master'
        self.assertTrue(client.update(new_branch))
        self.assertEqual(client._get_branch(), new_branch)
        self.assertEqual(client.get_version(), self.readonly_version)
        self.assertEqual(client._get_branch_parent(), (new_branch, "origin"))

        # and back
        self.assertTrue(client.update(branch))  # same branch arg
        self.assertEqual(client._get_branch(), branch)
        self.assertEqual(client.get_version(), self.untracked_version)
        self.assertEqual(client._get_branch_parent(), (None, None))

        # to dangling commit
        sha = self.dangling_version
        self.assertTrue(client.update(sha))
        self.assertEqual(client._get_branch(), None)
        self.assertEqual(client.get_version(), self.dangling_version)
        self.assertEqual(client._get_branch_parent(), (None, None))

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
            client._rev_list_contains('foo"; echo bar"', "foo", fetch=False)
            self.fail("expected Exception")
        except VcsError:
            pass
        try:
            client._rev_list_contains('foo', 'foo"; echo bar"', fetch=False)
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
        po = subprocess.Popen(
            "git log -n 1 --pretty=format:\"%H\"",
            shell=True, cwd=self.local_path, stdout=subprocess.PIPE)
        self.last_version = po.stdout.read().decode('UTF-8').rstrip('"').lstrip('"')

    def test_orphaned_overflow(self):
        client = GitClient(self.local_path)
        # this failed when passing all ref ids to git log
        self.assertFalse(client._is_commit_in_orphaned_subtree(self.last_version))


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
        self.assertEquals(
            '''\
diff --git ./added.txt ./added.txt
new file mode 100644
index 0000000..454f6b3
--- /dev/null
+++ ./added.txt
@@ -0,0 +1 @@
+0123456789abcdef
\\ No newline at end of file
diff --git ./deleted-fs.txt ./deleted-fs.txt
deleted file mode 100644
index e69de29..0000000
diff --git ./deleted.txt ./deleted.txt
deleted file mode 100644
index e69de29..0000000
diff --git ./modified-fs.txt ./modified-fs.txt
index e69de29..454f6b3 100644
--- ./modified-fs.txt
+++ ./modified-fs.txt
@@ -0,0 +1 @@
+0123456789abcdef
\\ No newline at end of file
diff --git ./modified.txt ./modified.txt
index e69de29..454f6b3 100644
--- ./modified.txt
+++ ./modified.txt
@@ -0,0 +1 @@
+0123456789abcdef
\\ No newline at end of file''',
        client.get_diff().rstrip())

    def testDiffRelpath(self):
        client = GitClient(self.local_path)
        self.assertTrue(client.path_exists())
        self.assertTrue(client.detect_presence())
        self.assertEquals(
            '''\
diff --git ros/added.txt ros/added.txt
new file mode 100644
index 0000000..454f6b3
--- /dev/null
+++ ros/added.txt
@@ -0,0 +1 @@
+0123456789abcdef
\\ No newline at end of file
diff --git ros/deleted-fs.txt ros/deleted-fs.txt
deleted file mode 100644
index e69de29..0000000
diff --git ros/deleted.txt ros/deleted.txt
deleted file mode 100644
index e69de29..0000000
diff --git ros/modified-fs.txt ros/modified-fs.txt
index e69de29..454f6b3 100644
--- ros/modified-fs.txt
+++ ros/modified-fs.txt
@@ -0,0 +1 @@
+0123456789abcdef
\\ No newline at end of file
diff --git ros/modified.txt ros/modified.txt
index e69de29..454f6b3 100644
--- ros/modified.txt
+++ ros/modified.txt
@@ -0,0 +1 @@
+0123456789abcdef
\\ No newline at end of file''',
            client.get_diff(basepath=os.path.dirname(self.local_path)).rstrip())

    def testStatus(self):
        client = GitClient(self.local_path)
        self.assertTrue(client.path_exists())
        self.assertTrue(client.detect_presence())
        self.assertEquals(
            '''\
A  ./added.txt
 D ./deleted-fs.txt
D  ./deleted.txt
 M ./modified-fs.txt
M  ./modified.txt
''',
            client.get_status(porcelain=True))

    def testStatusRelPath(self):
        client = GitClient(self.local_path)
        self.assertTrue(client.path_exists())
        self.assertTrue(client.detect_presence())
        self.assertEquals(
            '''\
A  ros/added.txt
 D ros/deleted-fs.txt
D  ros/deleted.txt
 M ros/modified-fs.txt
M  ros/modified.txt
''',
            client.get_status(basepath=os.path.dirname(self.local_path), porcelain=True))

    def testStatusUntracked(self):
        client = GitClient(self.local_path)
        self.assertTrue(client.path_exists())
        self.assertTrue(client.detect_presence())
        self.assertEquals(
            '''\
A  ./added.txt
 D ./deleted-fs.txt
D  ./deleted.txt
 M ./modified-fs.txt
M  ./modified.txt
?? ./added-fs.txt
''',
            client.get_status(untracked=True, porcelain=True))


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
            client.export_repository(self.readonly_version,
                                     self.basepath_export)
        )

        self.assertTrue(os.path.exists(self.basepath_export + '.tar.gz'))
        self.assertFalse(os.path.exists(self.basepath_export + '.tar'))
        self.assertFalse(os.path.exists(self.basepath_export))


class GitGetBranchesClientTest(GitClientTestSetups):

    @classmethod
    def setUpClass(self):
        GitClientTestSetups.setUpClass()

    def tearDown(self):
        pass

    def testGetBranches(self):
        client = GitClient(self.local_path)
        client.checkout(self.remote_path)
        self.assertEqual(client.get_branches(True), ['master'])
        self.assertEqual(client.get_branches(),
                         ['master', 'remotes/origin/master',
                          'remotes/origin/test_branch'])
        subprocess.check_call('git checkout test_branch', shell=True,
                              cwd=self.local_path, stdout=subprocess.PIPE,
                              stderr=subprocess.PIPE)
        self.assertEqual(client.get_branches(True), ['master', 'test_branch'])
        self.assertEqual(client.get_branches(),
                         ['master', 'test_branch', 'remotes/origin/master',
                          'remotes/origin/test_branch'])


class GitTimeoutTest(unittest.TestCase):

    class MuteHandler(BaseRequestHandler):
        def handle(self):
            data = True
            while data:
                data = self.request.recv(1024)

    @classmethod
    def setUpClass(self):
        self.mute_server = TCPServer(('localhost', 0), GitTimeoutTest.MuteHandler)
        _, self.mute_port = self.mute_server.server_address
        serv_thread = threading.Thread(target=self.mute_server.serve_forever)
        serv_thread.daemon = True
        serv_thread.start()

        self.root_directory = tempfile.mkdtemp()
        self.local_path = os.path.join(self.root_directory, "ros")

    def test_checkout_timeout(self):
        # SSH'ing to a mute server will hang for a very long time
        url = 'ssh://test@127.0.0.1:{0}/test'.format(self.mute_port)
        client = GitClient(self.local_path)
        start = time.time()

        self.assertFalse(client.checkout(url, timeout=2.0))
        stop = time.time()
        self.assertTrue(stop - start > 1.9)
        self.assertTrue(stop - start < 3.0)
        # the git processes will clean up the checkout dir, we have to wait
        # for them to finish in order to avoid a race condition with rmtree()
        while os.path.exists(self.local_path):
            time.sleep(0.2)

    @classmethod
    def tearDownClass(self):
        self.mute_server.shutdown()
        if os.path.exists(self.root_directory):
            shutil.rmtree(self.root_directory)

    def tearDown(self):
        if os.path.exists(self.local_path):
            shutil.rmtree(self.local_path)
