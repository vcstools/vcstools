from __future__ import absolute_import, print_function, unicode_literals
import unittest
from mock import Mock

import vcstools.vcs_abstraction
from vcstools.vcs_abstraction import register_vcs, get_registered_vcs_types, \
    get_vcs

from vcstools import get_vcs_client


class TestVcsAbstraction(unittest.TestCase):

    def test_register_vcs(self):
        try:
            backup = vcstools.vcs_abstraction._VCS_TYPES
            vcstools.vcs_abstraction._VCS_TYPES = {}
            self.assertEqual([], get_registered_vcs_types())
            mock_class = Mock()
            register_vcs('foo', mock_class)
            self.assertEqual(['foo'], get_registered_vcs_types())
        finally:
            vcstools.vcs_abstraction._VCS_TYPES = backup

    def test_get_vcs(self):
        try:
            backup = vcstools.vcs_abstraction._VCS_TYPES
            vcstools.vcs_abstraction._VCS_TYPES = {}
            self.assertEqual([], get_registered_vcs_types())
            mock_class = Mock()
            register_vcs('foo', mock_class)
            self.assertEqual(mock_class, get_vcs('foo'))
            self.assertRaises(ValueError, get_vcs, 'bar')
        finally:
            vcstools.vcs_abstraction._VCS_TYPES = backup

    def test_get_vcs_client(self):
        try:
            backup = vcstools.vcs_abstraction._VCS_TYPES
            vcstools.vcs_abstraction._VCS_TYPES = {}
            self.assertEqual([], get_registered_vcs_types())
            mock_class = Mock()
            mock_instance = Mock()
            # mock __init__ constructor
            mock_class.return_value = mock_instance
            register_vcs('foo', mock_class)
            self.assertEqual(mock_instance, get_vcs_client('foo', 'foopath'))
            self.assertRaises(ValueError, get_vcs_client, 'bar', 'barpath')
        finally:
            vcstools.vcs_abstraction._VCS_TYPES = backup
