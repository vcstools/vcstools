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

import platform
import os
import io
import fnmatch
import shutil
import subprocess
import tempfile
import unittest
from vcstools.bzr import BzrClient, _get_bzr_version


os.environ['EMAIL'] = 'Your Name <name@example.com>'


class BzrClientTestSetups(unittest.TestCase):

    @classmethod
    def setUpClass(self):
        self.root_directory = tempfile.mkdtemp()
        self.directories = dict(setUp=self.root_directory)
        self.remote_path = os.path.join(self.root_directory, "remote")
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

        self.local_path = os.path.join(self.root_directory, "local")

    @classmethod
    def tearDownClass(self):
        for d in self.directories:
            shutil.rmtree(self.directories[d])

    def tearDown(self):
        if os.path.exists(self.local_path):
            shutil.rmtree(self.local_path)


class BzrClientTest(BzrClientTestSetups):

    def test_url_matches_with_shortcut_strings(self):
        client = BzrClient(self.local_path)
        self.assertTrue(client.url_matches('test1234', 'test1234'))

    def test_url_matches_with_shortcut_strings_slashes(self):
        client = BzrClient(self.local_path)
        self.assertTrue(client.url_matches('test1234/', 'test1234'))
        self.assertTrue(client.url_matches('test1234', 'test1234/'))
        self.assertTrue(client.url_matches('test1234/', 'test1234/'))

    def get_launchpad_info(self, url):
        po = subprocess.Popen(["bzr", "info", url], stdout=subprocess.PIPE)
        output = po.stdout.read()
        # it is not great to use the same code for testing as in
        # production, but relying on fixed bzr info output is just as
        # bad.
        for line in output.splitlines():
            sline = line.decode('UTF-8').strip()
            for prefix in ['shared repository: ',
                           'repository branch: ',
                           'branch root: ']:
                if sline.startswith(prefix):
                    return sline[len(prefix):]
        return None

    # this test fails on travis with bzr 2.1.4 and python2.6, but
    # probably due to the messed up source install of bzr using python2.7
    if not (platform.python_version().startswith('2.6') and
            '2.1' in _get_bzr_version()):
        def test_url_matches_with_shortcut(self):
            # bzr on launchpad should have shared repository
            client = BzrClient(self.local_path)
            url = 'lp:bzr'
            url2 = self.get_launchpad_info(url)
            self.assertFalse(url2 is None)
            self.assertTrue(client.url_matches(url2, url), "%s~=%s" % (url, url2))

            # launchpad on launchpad should be a branch root
            url = 'lp:launchpad'
            url2 = self.get_launchpad_info(url)
            self.assertFalse(url2 is None)
            self.assertTrue(client.url_matches(url2, url), "%s~=%s" % (url, url2))

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

    def test_checkout_dir_exists(self):
        url = self.remote_path
        client = BzrClient(self.local_path)
        self.assertFalse(client.path_exists())
        os.makedirs(self.local_path)
        self.assertTrue(client.checkout(url))
        # non-empty
        self.assertFalse(client.checkout(url))

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

    def testDiffClean(self):
        client = BzrClient(self.remote_path)
        self.assertEquals('', client.get_diff())

    def testStatusClean(self):
        client = BzrClient(self.remote_path)
        self.assertEquals('', client.get_status())

    def test_get_environment_metadata(self):
        # Verify that metadata is generated
        directory = tempfile.mkdtemp()
        self.directories['local'] = directory
        local_path = os.path.join(directory, "local")
        client = BzrClient(local_path)
        self.assertTrue('version' in client.get_environment_metadata())


class BzrClientLogTest(BzrClientTestSetups):

    @classmethod
    def setUpClass(self):
        BzrClientTestSetups.setUpClass()
        client = BzrClient(self.local_path)
        client.checkout(self.remote_path)

    def test_get_log_defaults(self):
        client = BzrClient(self.local_path)
        client.checkout(self.remote_path)
        log = client.get_log()
        self.assertEquals(3, len(log))
        self.assertEquals('modified', log[0]['message'])
        for key in ['id', 'author', 'email', 'date', 'message']:
            self.assertTrue(log[0][key] is not None, key)

    def test_get_log_limit(self):
        client = BzrClient(self.local_path)
        client.checkout(self.remote_path)
        log = client.get_log(limit=1)
        self.assertEquals(1, len(log))
        self.assertEquals('modified', log[0]['message'])

    def test_get_log_path(self):
        client = BzrClient(self.local_path)
        client.checkout(self.remote_path)
        log = client.get_log(relpath='fixed.txt')
        self.assertEquals('initial', log[0]['message'])


class BzrClientAffectedFilesTest(BzrClientTestSetups):

    @classmethod
    def setUpClass(self):
        BzrClientTestSetups.setUpClass()
        client = BzrClient(self.local_path)
        client.checkout(self.remote_path)

    def test_get_log_defaults(self):
        client = BzrClient(self.local_path)
        client.checkout(self.remote_path)
        log = client.get_log(limit=1)[0]
        affected = client.get_affected_files(log['id'])
        self.assertEqual(sorted(['deleted-fs.txt', 'deleted.txt']),
                         sorted(affected))


class BzrDiffStatClientTest(BzrClientTestSetups):

    @classmethod
    def setUpClass(self):
        # setup a local repo once for all diff and status test
        BzrClientTestSetups.setUpClass()
        url = self.remote_path
        client = BzrClient(self.local_path)
        client.checkout(url)
        # after setting up "local" repo, change files and make some changes
        subprocess.check_call(["rm", "deleted-fs.txt"], cwd=self.local_path)
        subprocess.check_call(["bzr", "rm", "deleted.txt"], cwd=self.local_path)
        f = io.open(os.path.join(self.local_path, "modified.txt"), 'a')
        f.write('0123456789abcdef')
        f.close()
        f = io.open(os.path.join(self.local_path, "modified-fs.txt"), 'a')
        f.write('0123456789abcdef')
        f.close()
        f = io.open(os.path.join(self.local_path, "added-fs.txt"), 'w')
        f.write('0123456789abcdef')
        f.close()
        f = io.open(os.path.join(self.local_path, "added.txt"), 'w')
        f.write('0123456789abcdef')
        f.close()
        subprocess.check_call(["bzr", "add", "added.txt"], cwd=self.local_path)

    def tearDown(self):
        pass

    @classmethod
    def tearDownClass(self):
        BzrClientTestSetups.tearDownClass()

    def test_diff(self):
        client = BzrClient(self.local_path)
        self.assertTrue(client.path_exists())
        self.assertTrue(client.detect_presence())
        # using fnmatch because date and time change (remove when bzr reaches diff --format)
        diff = client.get_diff()
        self.assertTrue(diff is not None)
        self.assertTrue(fnmatch.fnmatch(diff, "=== added file 'added.txt'\n--- ./added.txt\t????-??-?? ??:??:?? +0000\n+++ ./added.txt\t????-??-?? ??:??:?? +0000\n@@ -0,0 +1,1 @@\n+0123456789abcdef\n\\ No newline at end of file\n\n=== removed file 'deleted-fs.txt'\n=== removed file 'deleted.txt'\n=== modified file 'modified-fs.txt'\n--- ./modified-fs.txt\t????-??-?? ??:??:?? +0000\n+++ ./modified-fs.txt\t????-??-?? ??:??:?? +0000\n@@ -0,0 +1,1 @@\n+0123456789abcdef\n\\ No newline at end of file\n\n=== modified file 'modified.txt'\n--- ./modified.txt\t????-??-?? ??:??:?? +0000\n+++ ./modified.txt\t????-??-?? ??:??:?? +0000\n@@ -0,0 +1,1 @@\n+0123456789abcdef\n\\ No newline at end of file"))

    def test_diff_relpath(self):
        client = BzrClient(self.local_path)
        self.assertTrue(client.path_exists())
        self.assertTrue(client.detect_presence())
        # using fnmatch because date and time change (remove when bzr introduces diff --format)
        diff = client.get_diff(basepath=os.path.dirname(self.local_path))
        self.assertTrue(diff is not None)
        self.assertTrue(fnmatch.fnmatch(diff, "=== added file 'added.txt'\n--- local/added.txt\t????-??-?? ??:??:?? +0000\n+++ local/added.txt\t????-??-?? ??:??:?? +0000\n@@ -0,0 +1,1 @@\n+0123456789abcdef\n\\ No newline at end of file\n\n=== removed file 'deleted-fs.txt'\n=== removed file 'deleted.txt'\n=== modified file 'modified-fs.txt'\n--- local/modified-fs.txt\t????-??-?? ??:??:?? +0000\n+++ local/modified-fs.txt\t????-??-?? ??:??:?? +0000\n@@ -0,0 +1,1 @@\n+0123456789abcdef\n\\ No newline at end of file\n\n=== modified file 'modified.txt'\n--- local/modified.txt\t????-??-?? ??:??:?? +0000\n+++ local/modified.txt\t????-??-?? ??:??:?? +0000\n@@ -0,0 +1,1 @@\n+0123456789abcdef\n\\ No newline at end of file"))

    def test_status(self):
        client = BzrClient(self.local_path)
        self.assertTrue(client.path_exists())
        self.assertTrue(client.detect_presence())
        self.assertEquals('+N  ./added.txt\n D  ./deleted-fs.txt\n-D  ./deleted.txt\n M  ./modified-fs.txt\n M  ./modified.txt\n', client.get_status())

    def test_status_relpath(self):
        client = BzrClient(self.local_path)
        self.assertTrue(client.path_exists())
        self.assertTrue(client.detect_presence())
        self.assertEquals('+N  local/added.txt\n D  local/deleted-fs.txt\n-D  local/deleted.txt\n M  local/modified-fs.txt\n M  local/modified.txt\n', client.get_status(basepath=os.path.dirname(self.local_path)))

    def test_status_untracked(self):
        client = BzrClient(self.local_path)
        self.assertTrue(client.path_exists())
        self.assertTrue(client.detect_presence())
        self.assertEquals('?   ./added-fs.txt\n+N  ./added.txt\n D  ./deleted-fs.txt\n-D  ./deleted.txt\n M  ./modified-fs.txt\n M  ./modified.txt\n', client.get_status(untracked=True))


class BzrDiffStatClientTest(BzrClientTestSetups):

    @classmethod
    def setUpClass(self):
        # setup a local repo once for all diff and status test
        BzrClientTestSetups.setUpClass()
        url = self.remote_path
        client = BzrClient(self.local_path)
        client.checkout(url)

        self.basepath_export = os.path.join(self.root_directory, 'export')

    def tearDown(self):
        pass

    @classmethod
    def tearDownClass(self):
        BzrClientTestSetups.tearDownClass()

    def test_export_repository(self):
        client = BzrClient(self.local_path)
        self.assertTrue(
          client.export_repository(self.local_version, self.basepath_export)
        )

        self.assertTrue(os.path.exists(self.basepath_export + '.tar.gz'))
        self.assertFalse(os.path.exists(self.basepath_export + '.tar'))
        self.assertFalse(os.path.exists(self.basepath_export))
