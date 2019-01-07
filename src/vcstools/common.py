# Software License Agreement (BSD License)
#
# Copyright (c) 2010, Willow Garage, Inc.
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
import errno
import os
import sys
import copy
import shlex
import subprocess
import logging
import netrc
import tempfile
import shutil
import threading
import signal

try:
    # py3k
    from urllib.request import urlopen, HTTPPasswordMgrWithDefaultRealm, \
        HTTPBasicAuthHandler, build_opener
    from urllib.parse import urlparse
    from queue import Queue
except ImportError:
    # py2.7
    from urlparse import urlparse
    from urllib2 import urlopen, HTTPPasswordMgrWithDefaultRealm, \
        HTTPBasicAuthHandler, build_opener
    from Queue import Queue

from vcstools.vcs_base import VcsError


def ensure_dir_notexists(path):
    """
    helper function, removes dir if it exists

    :returns: True if dir does not exist after this function
    :raises: OSError if dir exists and removal failed for non-trivial reasons
    """
    try:
        if os.path.exists(path):
            os.rmdir(path)
        return True
    except OSError as ose:
        # ignore if directory
        if ose.errno not in [errno.ENOENT, errno.ENOTEMPTY, errno.ENOTDIR]:
            return False


def urlopen_netrc(uri, *args, **kwargs):
    '''
    wrapper to urlopen, using netrc on 401 as fallback
    Since this wraps both python2 and python3 urlopen, accepted arguments vary

    :returns: file-like object as urllib.urlopen
    :raises: IOError and urlopen errors
    '''
    try:
        return urlopen(uri, *args, **kwargs)
    except IOError as ioe:
        if hasattr(ioe, 'code') and ioe.code == 401:
            # 401 means authentication required, we try netrc credentials
            result = _netrc_open(uri)
            if result is not None:
                return result
        raise


def urlretrieve_netrc(url, filename=None):
    '''
    writes a temporary file with the contents of url. This works
    similar to urllib2.urlretrieve, but uses netrc as fallback on 401,
    and has no reporthook or data option. Also urllib2.urlretrieve
    malfunctions behind proxy, so we avoid it.

    :param url: What to retrieve
    :param filename: target file (default is basename of url)
    :returns: (filename, response_headers)
    :raises: IOError and urlopen errors
    '''
    fname = None
    fhand = None
    try:
        resp = urlopen_netrc(url)
        if filename:
            fhand = open(filename, 'wb')
            fname = filename
        else:
            # Make a temporary file
            fdesc, fname = tempfile.mkstemp()
            fhand = os.fdopen(fdesc, "wb")
            # Copy the http response to the temporary file.
        shutil.copyfileobj(resp, fhand)
    finally:
        if fhand:
            fhand.close()
    return (fname, resp.headers)


def _netrc_open(uri, filename=None):
    '''
    open uri using netrc credentials.

    :param uri: uri to open
    :param filename: optional, path to non-default netrc config file
    :returns: file-like object from opening a socket to uri, or None
    :raises IOError: if opening .netrc file fails (unless file not found)
    '''
    if not uri:
        return None
    parsed_uri = urlparse(uri)
    machine = parsed_uri.netloc
    if not machine:
        return None
    opener = None
    try:
        info = netrc.netrc(filename).authenticators(machine)
        if info is not None:
            (username, _, password) = info
            if username and password:
                pass_man = HTTPPasswordMgrWithDefaultRealm()
                pass_man.add_password(None, machine, username, password)
                authhandler = HTTPBasicAuthHandler(pass_man)
                opener = build_opener(authhandler)
                return opener.open(uri)
        else:
            # caught below, like other netrc parse errors
            raise netrc.NetrcParseError('No authenticators for "%s"' % machine)
    except IOError as ioe:
        if ioe.errno != 2:
            # if = 2, User probably has no .netrc, this is not an error
            raise
    except netrc.NetrcParseError as neterr:
        logger = logging.getLogger('vcstools')
        logger.warn('WARNING: parsing .netrc: %s' % str(neterr))
    # we could install_opener() here, but prefer to keep
    # default opening clean. Client can do that, though.
    return None


def normalized_rel_path(path, basepath):
    """
    If path is absolute, return relative path to it from
    basepath. If relative, return it normalized.

    :param path: an absolute or relative path
    :param basepath: if path is absolute, shall be made relative to this
    :returns: a normalized relative path
    """
    # gracefully ignore invalid input absolute path + no basepath
    if path is None:
        return basepath
    if os.path.isabs(path) and basepath is not None:
        return os.path.normpath(os.path.relpath(os.path.realpath(path), os.path.realpath(basepath)))
    return os.path.normpath(path)


def sanitized(arg):
    """
    makes sure a composed command to be executed via shell was not injected.

    A composed command would be like "ls %s"%foo.
    In this example, foo could be "; rm -rf *"
    sanitized raises an Error when it detects such an attempt

    :raises VcsError: on injection attempts
    """
    if arg is None or arg.strip() == '':
        return ''
    arg = str(arg.strip('"').strip())
    safe_arg = '"%s"' % arg
    # this also detects some false positives, like bar"";foo
    if '"' in arg:
        if (len(shlex.split(safe_arg, False, False)) != 1):
            raise VcsError("Shell injection attempt detected: >%s< = %s" %
                           (arg, shlex.split(safe_arg, False, False)))
    return safe_arg


def _discard_line(line):
    if line is None:
        return True
    # the most common feedback lines of scms. We don't care about those. We let through anything unusual only.
    discard_prefixes = ["adding ", "added ", "updating ", "requesting ", "pulling from ",
                        "searching for ", "(", "no changes found",
                        "0 files",
                        "A  ", "D  ", "U  ",
                        "At revision", "Path: ", "First,",
                        "Installing", "Using ",
                        "No ", "Tree ",
                        "All ",
                        "+N  ", "-D  ", " M  ", " M* ", "RM"  # bzr
                        ]
    for pre in discard_prefixes:
        if line.startswith(pre):
            return True
    return False


def _read_shell_output(proc, no_filter, verbose, show_stdout, output_queue):
    # when we read output in while loop, it would not be returned
    # in communicate()
    stdout_buf = []
    stderr_buf = []
    if not no_filter:
        if (verbose or show_stdout):
            # this loop runs until proc is done it listen to the pipe, print
            # and stores result in buffer for returning this allows proc to run
            # while we still can filter out output avoiding readline() because
            # it may block forever
            for line in iter(proc.stdout.readline, b''):
                line = line.decode('UTF-8')
                if line is not None and line != '':
                    if verbose or not _discard_line(line):
                        sys.stdout.write(line),
                        stdout_buf.append(line)
                if (not line or proc.returncode is not None):
                    break
        # stderr was swallowed in pipe, in verbose mode print lines
        if verbose:
            for line in iter(proc.stderr.readline, b''):
                line = line.decode('UTF-8')
                if line != '':
                    sys.stdout.write(line),
                    stderr_buf.append(line)
                if not line:
                    break
    output_queue.put(proc.communicate())
    output_queue.put(stdout_buf)
    output_queue.put(stderr_buf)


def run_shell_command(cmd, cwd=None, shell=False, us_env=True,
                      show_stdout=False, verbose=False, timeout=None,
                      no_warn=False, no_filter=False):
    """
    executes a command and hides the stdout output, loggs stderr
    output when command result is not zero. Make sure to sanitize
    arguments in the command.

    :param cmd: A string to execute.
    :param shell: Whether to use os shell.
    :param us_env: changes env var LANG before running command, can influence program output
    :param show_stdout: show some of the output (except for discarded lines in _discard_line()), ignored if no_filter
    :param no_warn: hides warnings
    :param verbose: show all output, overrides no_warn, ignored if no_filter
    :param timeout: time allocated to the subprocess
    :param no_filter: does not wrap stdout, so invoked command prints everything outside our knowledge
    this is DANGEROUS, as vulnerable to shell injection.
    :returns: ( returncode, stdout, stderr); stdout is None if no_filter==True
    :raises: VcsError on OSError
    """
    try:
        env = copy.copy(os.environ)
        if us_env:
            env["LANG"] = "en_US.UTF-8"
        if no_filter:
            # in no_filter mode, we cannot pipe stdin, as this
            # causes some prompts to be hidden (e.g. mercurial over
            # http)
            stdout_target = None
            stderr_target = None
        else:
            stdout_target = subprocess.PIPE
            stderr_target = subprocess.PIPE

        # additional parameters to Popen when using a timeout
        crflags = {}
        if timeout is not None:
            if hasattr(os.sys, 'winver'):
                crflags['creationflags'] = subprocess.CREATE_NEW_PROCESS_GROUP
            else:
                crflags['preexec_fn'] = os.setsid

        proc = subprocess.Popen(cmd,
                                shell=shell,
                                cwd=cwd,
                                stdout=stdout_target,
                                stderr=stderr_target,
                                env=env,
                                **crflags)

        # using a queue to enable usage in a separate thread
        q = Queue()
        if timeout is None:
            _read_shell_output(proc, no_filter, verbose, show_stdout, q)
        else:
            t = threading.Thread(target=_read_shell_output,
                                 args=[proc, no_filter, verbose, show_stdout, q])
            t.start()
            t.join(timeout)
            if t.isAlive():
                if hasattr(os.sys, 'winver'):
                    os.kill(proc.pid, signal.CTRL_BREAK_EVENT)
                else:
                    os.killpg(proc.pid, signal.SIGTERM)
                t.join()
        (stdout, stderr) = q.get()
        stdout_buf = q.get()
        stderr_buf = q.get()

        if stdout is not None:
            stdout_buf.append(stdout.decode('utf-8'))
        stdout = "\n".join(stdout_buf)
        if stderr is not None:
            stderr_buf.append(stderr.decode('utf-8'))
        stderr = "\n".join(stderr_buf)
        message = None
        if proc.returncode != 0 and stderr is not None and stderr != '':
            logger = logging.getLogger('vcstools')
            message = "Command failed: '%s'" % (cmd)
            if cwd is not None:
                message += "\n run at: '%s'" % (cwd)
            message += "\n errcode: %s:\n%s" % (proc.returncode, stderr)
            if not no_warn:
                logger.warn(message)
        result = stdout
        if result is not None:
            result = result.rstrip()
        return (proc.returncode, result, message)
    except OSError as ose:
        logger = logging.getLogger('vcstools')
        message = "Command failed with OSError. '%s' <%s, %s>:\n%s" % (cmd, shell, cwd, ose)
        logger.error(message)
        raise VcsError(message)
