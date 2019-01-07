#!/usr/bin/env python
# Software License Agreement (BSD License)
#
# Copyright (c) 2011, Willow Garage, Inc.
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
import tarfile
import tempfile
import shutil
import subprocess
import mock

from vcstools.tar import TarClient
from test.mock_server import start_mock_server

def tarfile_contents():
    '''
    :returns: binary string of ROS package-release-like tarfile to serve
    '''
    tar_directory = tempfile.mkdtemp()
    filename = os.path.join(tar_directory, 'sample.tar.gz')
    pkgname = "sample-1.0"
    pkg_directory = os.path.join(tar_directory, pkgname)
    os.mkdir(pkg_directory)
    packagexml = os.path.join(pkg_directory, "package.xml")
    with open(packagexml, 'w+') as f:
        f.write('<?xml version="1.0"?><package>' + ('<name>sample</name>' * 1000) + '</package>')

    with tarfile.open(filename, "w:gz") as tar_handle:
        tar_handle.addfile(tarfile.TarInfo(os.path.join(pkgname, "package.xml")), packagexml)
    tar_handle.close()

    with open(filename, mode='rb') as file: # b is important -> binary
        result = file.read()
    shutil.rmtree(tar_directory)
    return result



class TarClientTest(unittest.TestCase):
    '''Test against mock http server'''

    @classmethod
    def setUpClass(self):
        baseURL = start_mock_server(tarfile_contents())
        self.remote_url = baseURL + '/downloads/1.0.tar.gz'
        self.package_version = "sample-1.0"

    def setUp(self):
        self.directories = {}

    def tearDown(self):
        for d in self.directories:
            self.assertTrue(os.path.exists(self.directories[d]))
            shutil.rmtree(self.directories[d])
            self.assertFalse(os.path.exists(self.directories[d]))

    def test_get_url_by_reading(self):
        directory = tempfile.mkdtemp()
        self.directories['local'] = directory

        local_path = os.path.join(directory, "local")

        client = TarClient(local_path)
        self.assertTrue(client.checkout(self.remote_url, self.package_version))

        self.assertTrue(client.path_exists())
        self.assertTrue(client.detect_presence())
        self.assertEqual(client.get_url(), self.remote_url)
        #self.assertEqual(client.get_version(), self.package_version)

    def test_get_url_nonexistant(self):
        local_path = "/tmp/dummy"
        client = TarClient(local_path)
        self.assertEqual(client.get_url(), None)

    def test_get_type_name(self):
        local_path = "/tmp/dummy"
        client = TarClient(local_path)
        self.assertEqual(client.get_vcs_type_name(), 'tar')


    @mock.patch('netrc.netrc') # cannot rely on local ~/.netrc file
    def test_checkout_parametrized(self, patched_netrc):
        netrc_mock = mock.Mock()
        netrc_mock.authenticators.return_value = ('user', '' , 'password')
        patched_netrc.return_value = netrc_mock
        for query_params in ['', '?chunked=true', '?auth=true', '?chunked=true&auth=true']:
            self.check_checkout(query_params)

    # parametrized
    def check_checkout(self, query_params):
        # checks out all subdirs
        directory = tempfile.mkdtemp()
        self.directories["checkout_test"] = directory
        local_path = os.path.join(directory, "exploration")
        client = TarClient(local_path)
        self.assertFalse(client.path_exists())
        self.assertFalse(client.detect_presence())
        self.assertFalse(client.detect_presence())
        self.assertTrue(client.checkout(self.remote_url + query_params))
        self.assertTrue(client.path_exists())
        self.assertTrue(client.detect_presence())
        self.assertEqual(client.get_path(), local_path)
        self.assertEqual(client.get_url(), self.remote_url + query_params)
        # make sure the tarball subdirectory was promoted correctly.
        self.assertTrue(os.path.exists(os.path.join(local_path,
                                                    self.package_version,
                                                    'package.xml')))

    def test_checkout_dir_exists(self):
        directory = tempfile.mkdtemp()
        self.directories["checkout_test"] = directory
        local_path = os.path.join(directory, "exploration")
        client = TarClient(local_path)
        self.assertFalse(client.path_exists())
        os.makedirs(local_path)
        self.assertTrue(client.checkout(self.remote_url))
        # non-empty
        self.assertFalse(client.checkout(self.remote_url))

    def test_checkout_version(self):
        directory = tempfile.mkdtemp()
        self.directories["checkout_test"] = directory
        local_path = os.path.join(directory, "exploration")
        client = TarClient(local_path)
        self.assertFalse(client.path_exists())
        self.assertFalse(client.detect_presence())
        self.assertFalse(client.detect_presence())
        self.assertTrue(client.checkout(self.remote_url,
                                        version=self.package_version))
        self.assertTrue(client.path_exists())
        self.assertTrue(client.detect_presence())
        self.assertEqual(client.get_path(), local_path)
        self.assertEqual(client.get_url(), self.remote_url)
        # make sure the tarball subdirectory was promoted correctly.
        self.assertTrue(os.path.exists(os.path.join(local_path, 'package.xml')))

    def test_get_environment_metadata(self):
        # Verify that metadata is generated
        directory = tempfile.mkdtemp()
        self.directories['local'] = directory
        local_path = os.path.join(directory, "local")
        client = TarClient(local_path)
        self.assertTrue('version' in client.get_environment_metadata())


class TarClientTestLocal(unittest.TestCase):
    '''Tests with URL being a local filepath'''

    def setUp(self):
        self.root_directory = tempfile.mkdtemp()
        # helpful when setting tearDown to pass
        self.directories = dict(setUp=self.root_directory)
        self.version_path0 = os.path.join(self.root_directory, "version")
        self.version_path1 = os.path.join(self.root_directory, "version1")
        self.version_path2 = os.path.join(self.root_directory, "version1.0")

        os.makedirs(self.version_path0)
        os.makedirs(self.version_path1)
        os.makedirs(self.version_path2)

        subprocess.check_call("touch stack0.xml", shell=True, cwd=self.version_path0)
        subprocess.check_call("touch stack.xml", shell=True, cwd=self.version_path1)
        subprocess.check_call("touch stack1.xml", shell=True, cwd=self.version_path2)
        subprocess.check_call("touch version1.txt", shell=True, cwd=self.root_directory)

        self.tar_url = os.path.join(self.root_directory, "origin.tar")
        self.tar_url_compressed = os.path.join(self.root_directory,
                                               "origin_compressed.tar.bz2")

        subprocess.check_call("tar -cf %s %s" % (self.tar_url, " ".join(["version",
                                                                        "version1",
                                                                        "version1.txt",
                                                                        "version1.0"])),
                              shell=True,
                              cwd=self.root_directory)
        subprocess.check_call("tar -cjf %s %s" % (self.tar_url_compressed, " ".join(["version",
                                                                                    "version1",
                                                                                    "version1.txt",
                                                                                    "version1.0"])),
                              shell=True,
                              cwd=self.root_directory)

    def tearDown(self):
        for d in self.directories:
            self.assertTrue(os.path.exists(self.directories[d]))
            shutil.rmtree(self.directories[d])
            self.assertFalse(os.path.exists(self.directories[d]))

    def test_checkout_version_local(self):
        directory = tempfile.mkdtemp()
        self.directories["checkout_test"] = directory
        local_path = os.path.join(directory, "version1")
        url = self.tar_url
        client = TarClient(local_path)
        self.assertFalse(client.path_exists())
        self.assertFalse(client.detect_presence())
        self.assertFalse(client.detect_presence())
        self.assertTrue(client.checkout(url, version='version1'))
        self.assertTrue(client.path_exists())
        self.assertTrue(client.detect_presence())
        self.assertEqual(client.get_path(), local_path)
        self.assertEqual(client.get_url(), url)
        # make sure the tarball subdirectory was promoted correctly.
        self.assertTrue(os.path.exists(os.path.join(local_path, 'stack.xml')))

    def test_checkout_version_compressed_local(self):
        directory = tempfile.mkdtemp()
        self.directories["checkout_test"] = directory
        local_path = os.path.join(directory, "version1")
        url = self.tar_url_compressed
        client = TarClient(local_path)
        self.assertFalse(client.path_exists())
        self.assertFalse(client.detect_presence())
        self.assertFalse(client.detect_presence())
        self.assertTrue(client.checkout(url, version='version1'))
        self.assertTrue(client.path_exists())
        self.assertTrue(client.detect_presence())
        self.assertEqual(client.get_path(), local_path)
        self.assertEqual(client.get_url(), url)
        # make sure the tarball subdirectory was promoted correctly.
        self.assertTrue(os.path.exists(os.path.join(local_path, 'stack.xml')))
