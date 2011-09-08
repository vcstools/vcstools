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

import os
import struct
import sys
import unittest
import tempfile
import shutil

class TarClientTest(unittest.TestCase):

    def setUp(self):
        self.directories = {}

    def tearDown(self):
        for d in self.directories:
            shutil.rmtree(self.directories[d])

    def test_get_url_by_reading(self):
        from vcstools.tar import TarClient

        directory = tempfile.mkdtemp()
        self.directories['readonly'] = directory

        readonly_url = "https://code.ros.org/svn/release/download/stacks/exploration/exploration-0.3.0/exploration-0.3.0.tar.bz2"
        readonly_version = "exploration-0.3.0"
        readonly_path = os.path.join(directory, "readonly")

        client = TarClient(readonly_path)
        self.assertTrue(client.checkout(readonly_url, readonly_version))
        
        self.assertTrue(client.path_exists())
        self.assertTrue(client.detect_presence())
        self.assertEqual(client.get_url(), readonly_url)
        #self.assertEqual(client.get_version(), readonly_version)

    def test_get_url_nonexistant(self):
        from vcstools.tar import TarClient
        local_path = "/tmp/dummy"
        client = TarClient(local_path)
        self.assertEqual(client.get_url(), None)

    def test_get_type_name(self):
        from vcstools.tar import TarClient
        local_path = "/tmp/dummy"
        client = TarClient(local_path)
        self.assertEqual(client.get_vcs_type_name(), 'tar')

    def test_checkout(self):
        from vcstools.tar import TarClient
        directory = tempfile.mkdtemp()
        self.directories["checkout_test"] = directory
        local_path = os.path.join(directory, "exploration")
        url = "https://code.ros.org/svn/release/download/stacks/exploration/exploration-0.3.0/exploration-0.3.0.tar.bz2"
        client = TarClient(local_path)
        self.assertFalse(client.path_exists())
        self.assertFalse(client.detect_presence())
        self.assertFalse(client.detect_presence())
        self.assertTrue(client.checkout(url))
        self.assertTrue(client.path_exists())
        self.assertTrue(client.detect_presence())
        self.assertEqual(client.get_path(), local_path)
        self.assertEqual(client.get_url(), url)

        #self.assertEqual(client.get_version(), '-r*')
        shutil.rmtree(directory)
        self.directories.pop("checkout_test")
