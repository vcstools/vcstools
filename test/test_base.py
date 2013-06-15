from __future__ import absolute_import, print_function, unicode_literals
import os
import unittest
import tempfile
import shutil
from mock import Mock

import vcstools
from vcstools.vcs_base import VcsClientBase, VcsError
from vcstools.common import sanitized, normalized_rel_path, \
    run_shell_command, urlretrieve_netrc, _netrc_open, urlopen_netrc


class BaseTest(unittest.TestCase):

    def test_normalized_rel_path(self):
        self.assertEqual(None, normalized_rel_path(None, None))
        self.assertEqual('foo', normalized_rel_path(None, 'foo'))
        self.assertEqual('/foo', normalized_rel_path(None, '/foo'))
        self.assertEqual('../bar', normalized_rel_path('/bar', '/foo'))
        self.assertEqual('../bar', normalized_rel_path('/bar', '/foo/baz/..'))
        self.assertEqual('../bar', normalized_rel_path('/bar/bam/foo/../..', '/foo/baz/..'))
        self.assertEqual('bar', normalized_rel_path('bar/bam/foo/../..', '/foo/baz/..'))

    def test_sanitized(self):
        self.assertEqual('', sanitized(None))
        self.assertEqual('', sanitized(''))
        self.assertEqual('"foo"', sanitized('foo'))
        self.assertEqual('"foo"', sanitized('\"foo\"'))
        self.assertEqual('"foo"', sanitized('"foo"'))
        self.assertEqual('"foo"', sanitized('" foo"'))

        try:
            sanitized('bla"; foo"')
            self.fail("Expected Exception")
        except VcsError:
            pass
        try:
            sanitized('bla";foo"')
            self.fail("Expected Exception")
        except VcsError:
            pass
        try:
            sanitized('bla";foo \"bum')
            self.fail("Expected Exception")
        except VcsError:
            pass
        try:
            sanitized('bla";foo;"bam')
            self.fail("Expected Exception")
        except VcsError:
            pass
        try:
            sanitized('bla"#;foo;"bam')
            self.fail("Expected Exception")
        except VcsError:
            pass

    def test_shell_command(self):
        self.assertEqual((0, "", None), run_shell_command("true"))
        self.assertEqual((1, "", None), run_shell_command("false"))
        self.assertEqual((0, "foo", None), run_shell_command("echo foo", shell=True))
        (v, r, e) = run_shell_command("[", shell=True)
        self.assertFalse(v == 0)
        self.assertFalse(e is None)
        self.assertEqual(r, '')
        (v, r, e) = run_shell_command("echo foo && [", shell=True)
        self.assertFalse(v == 0)
        self.assertFalse(e is None)
        self.assertEqual(r, 'foo')
        # not a great test on a system where this is default
        _, env_langs, _ = run_shell_command("/usr/bin/env |grep LANG=", shell=True, us_env=True)
        self.assertTrue("LANG=en_US.UTF-8" in env_langs.splitlines())
        try:
            run_shell_command("two words")
            self.fail("expected exception")
        except:
            pass

    def test_shell_command_verbose(self):
        # just check no Exception happens due to decoding
        run_shell_command("echo %s" % (b'\xc3\xa4'.decode('UTF-8')), shell=True, verbose=True)
        run_shell_command(["echo", b'\xc3\xa4'.decode('UTF-8')], verbose=True)

    def test_netrc_open(self):
        root_directory = tempfile.mkdtemp()
        machine = 'foo.org'
        uri = 'https://%s/bim/bam' % machine
        netrcname = os.path.join(root_directory, "netrc")
        mock_build_opener = Mock()
        mock_build_opener_fun = Mock()
        mock_build_opener_fun.return_value = mock_build_opener
        back_build_opener = vcstools.common.build_opener
        try:
            vcstools.common.build_opener = mock_build_opener_fun
            filelike = _netrc_open(uri, netrcname)
            self.assertFalse(filelike)

            with open(netrcname, 'w') as fhand:
                fhand.write(
                    'machine %s login fooname password foopass' % machine)
            filelike = _netrc_open(uri, netrcname)
            self.assertTrue(filelike)
            filelike = _netrc_open('other', netrcname)
            self.assertFalse(filelike)
            filelike = _netrc_open(None, netrcname)
            self.assertFalse(filelike)
        finally:
            shutil.rmtree(root_directory)
            vcstools.common.build_opener = back_build_opener

    def test_urlopen_netrc(self):
        mockopen = Mock()
        mock_result = Mock()
        backopen = vcstools.common.urlopen
        backget = vcstools.common._netrc_open
        try:
            #monkey-patch with mocks
            vcstools.common.urlopen = mockopen
            vcstools.common._netrc_open = Mock()
            vcstools.common._netrc_open.return_value = mock_result
            ioe = IOError('MockError')
            mockopen.side_effect = ioe
            self.assertRaises(IOError, urlopen_netrc, 'foo')
            ioe.code = 401
            result = urlopen_netrc('foo')
            self.assertEqual(mock_result, result)
        finally:
            vcstools.common.urlopen = backopen
            vcstools.common._netrc_open = backget

    def test_urlretrieve_netrc(self):
        root_directory = tempfile.mkdtemp()
        examplename = os.path.join(root_directory, "foo")
        outname = os.path.join(root_directory, "fooout")
        with open(examplename, "w") as fhand:
            fhand.write('content')
        mockget = Mock()
        mockopen = Mock()
        mock_fhand = Mock()
        backopen = vcstools.common.urlopen
        backget = vcstools.common._netrc_open
        try:
            # vcstools.common.urlopen = mockopen
            # vcstools.common.urlopen.return_value = mock_fhand
            # mock_fhand.read.return_value = 'content'
            mockopen.open.return_value
            vcstools.common._netrc_open = Mock()
            vcstools.common._netrc_open.return_value = mockget
            (fname, headers) = urlretrieve_netrc('file://' + examplename)
            self.assertTrue(fname)
            self.assertFalse(os.path.exists(outname))
            (fname, headers) = urlretrieve_netrc('file://' + examplename,
                                                 outname)
            self.assertEqual(outname, fname)
            self.assertTrue(os.path.isfile(outname))
        finally:
            vcstools.common.urlopen = backopen
            vcstools.common._netrc_open = backget
            shutil.rmtree(root_directory)
