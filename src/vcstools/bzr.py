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
#

"""
bzr vcs support.
"""


from __future__ import absolute_import, print_function, unicode_literals
import os

import re
import email.utils  # For email parsing
import dateutil.parser  # Date string parsing

# first try python3, then python2
try:
    from urllib.request import url2pathname
except ImportError:
    from urllib2 import url2pathname

from vcstools.vcs_base import VcsClientBase, VcsError
from vcstools.common import sanitized, normalized_rel_path, \
    run_shell_command, ensure_dir_notexists


def _get_bzr_version():
    """Looks up bzr version by calling bzr --version.
    :raises: VcsError if bzr is not installed"""
    try:
        value, output, _ = run_shell_command('bzr --version',
                                             shell=True,
                                             us_env=True)
        if value == 0 and output is not None and len(output.splitlines()) > 0:
            version = output.splitlines()[0]
        else:
            raise VcsError("bzr --version returned %s," +
                           " maybe bzr is not installed" %
                           value)
    except VcsError as e:
        raise VcsError("Coud not determine whether bzr is installed: %s" % e)
    return version


class BzrClient(VcsClientBase):
    def __init__(self, path):
        """
        :raises: VcsError if bzr not detected
        """
        VcsClientBase.__init__(self, 'bzr', path)
        _get_bzr_version()

    @staticmethod
    def get_environment_metadata():
        metadict = {}
        try:
            metadict["version"] = _get_bzr_version()
        except:
            metadict["version"] = "no bzr installed"
        return metadict

    def get_url(self):
        """
        :returns: BZR URL of the branch (output of bzr info command),
        or None if it cannot be determined
        """
        result = None
        if self.detect_presence():
            cmd = 'bzr info %s' % self._path
            _, output, _ = run_shell_command(cmd, shell=True, us_env=True)
            matches = [l for l in output.splitlines() if l.startswith('  parent branch: ')]
            if matches:
                ppath = url2pathname(matches[0][len('  parent branch: '):])
                # when it can, bzr substitues absolute path for relative paths
                if (ppath is not None and os.path.isdir(ppath) and not os.path.isabs(ppath)):
                    result = os.path.abspath(os.path.join(os.getcwd(), ppath))
                else:
                    result = ppath
        return result

    def url_matches(self, url, url_or_shortcut):
        if super(BzrClient, self).url_matches(url, url_or_shortcut):
            return True
        # if we got a shortcut (e.g. launchpad url), we compare using
        # bzr info and return that one if result matches.
        result = False
        if url_or_shortcut is not None:
            cmd = 'bzr info %s' % url_or_shortcut
            value, output, _ = run_shell_command(cmd, shell=True, us_env=True)
            if value == 0:
                for line in output.splitlines():
                    sline = line.strip()
                    for prefix in ['shared repository: ',
                                   'repository branch: ',
                                   'branch root: ']:
                        if sline.startswith(prefix):
                            if super(BzrClient, self).url_matches(url, sline[len(prefix):]):
                                result = True
                                break
        return result

    @staticmethod
    def static_detect_presence(path):
        return os.path.isdir(os.path.join(path, '.bzr'))

    def checkout(self, url, version=None, verbose=False,
                 shallow=False, timeout=None):
        if url is None or url.strip() == '':
            raise ValueError('Invalid empty url : "%s"' % url)
        # bzr 2.5.1 fails if empty directory exists
        if not ensure_dir_notexists(self.get_path()):
            self.logger.error("Can't remove %s" % self.get_path())
            return False
        cmd = 'bzr branch'
        if version:
            cmd += ' -r %s' % version
        cmd += ' %s %s' % (url, self._path)
        value, _, msg = run_shell_command(cmd,
                                          shell=True,
                                          show_stdout=verbose,
                                          verbose=verbose)
        if value != 0:
            if msg:
                self.logger.error('%s' % msg)
            return False
        return True

    def update(self, version='', verbose=False, timeout=None):
        if not self.detect_presence():
            return False
        value, _, _ = run_shell_command("bzr pull",
                                        cwd=self._path,
                                        shell=True,
                                        show_stdout=True,
                                        verbose=verbose)
        if value != 0:
            return False
        # Ignore verbose param, bzr is pretty verbose on update anyway
        if version is not None and version != '':
            cmd = "bzr update -r %s" % (version)
        else:
            cmd = "bzr update"
        value, _, _ = run_shell_command(cmd,
                                        cwd=self._path,
                                        shell=True,
                                        show_stdout=True,
                                        verbose=verbose)
        if value == 0:
            return True
        return False

    def get_version(self, spec=None):
        """
        :param spec: (optional) revisionspec of desired version.  May
          be any revisionspec as returned by 'bzr help revisionspec',
          e.g. a tagname or 'revno:<number>'
        :returns: the current revision number of the repository. Or if
          spec is provided, the number of a revision specified by some
          token.
        """
        if self.detect_presence():
            if spec is not None:
                command = ['bzr log -r %s .' % sanitized(spec)]
                _, output, _ = run_shell_command(command,
                                                 shell=True,
                                                 cwd=self._path,
                                                 us_env=True)
                if output is None or output.strip() == '' or output.startswith("bzr:"):
                    return None
                else:
                    matches = [l for l in output.split('\n') if l.startswith('revno: ')]
                    if len(matches) == 1:
                        return matches[0].split()[1]
            else:
                _, output, _ = run_shell_command('bzr revno --tree',
                                                 shell=True,
                                                 cwd=self._path,
                                                 us_env=True)
                return output.strip()

    def get_current_version_label(self):
        # url contains branch information
        return None

    def get_remote_version(self, fetch=False):
        # Not sure how to get any useful information from bzr about this,
        # since bzr has no globally unique IDs
        return None

    def get_diff(self, basepath=None):
        response = None
        if basepath is None:
            basepath = self._path
        if self.path_exists():
            rel_path = sanitized(normalized_rel_path(self._path, basepath))
            command = "bzr diff %s" % rel_path
            command += " -p1 --prefix %s/:%s/" % (rel_path, rel_path)
            _, response, _ = run_shell_command(command, shell=True, cwd=basepath)
        return response

    def get_affected_files(self, revision):
        cmd = "bzr status -c {0} -S -V".format(
            revision)

        code, output, _ = run_shell_command(cmd, shell=True, cwd=self._path)

        affected = []
        if code == 0:
            for filename in output.splitlines():
                affected.append(filename.split(" ")[2])
        return affected

    def get_log(self, relpath=None, limit=None):
        response = []

        if relpath is None:
            relpath = ''

        # Compile regexes
        id_regex = re.compile('^revno: ([0-9]+)$', flags=re.MULTILINE)
        committer_regex = re.compile('^committer: (.+)$', flags=re.MULTILINE)
        timestamp_regex = re.compile('^timestamp: (.+)$', flags=re.MULTILINE)
        message_regex = re.compile('^  (.+)$', flags=re.MULTILINE)

        if self.path_exists() and os.path.exists(os.path.join(self._path, relpath)):
            # Get the log
            limit_cmd = (("--limit=%d" % (int(limit))) if limit else "")
            command = "bzr log %s %s" % (sanitized(relpath), limit_cmd)
            return_code, text_response, stderr = run_shell_command(command, shell=True, cwd=self._path)
            if return_code == 0:
                revno_match = id_regex.findall(text_response)
                committer_match = committer_regex.findall(text_response)
                timestamp_match = timestamp_regex.findall(text_response)
                message_match = message_regex.findall(text_response)

                # Extract the entries
                for revno, committer, timestamp, message in zip(revno_match,
                                                                committer_match,
                                                                timestamp_match,
                                                                message_match):
                    author, email_address = email.utils.parseaddr(committer)
                    date = dateutil.parser.parse(timestamp)
                    log_data = {'id': revno,
                                'author': author,
                                'email': email_address,
                                'message': message,
                                'date': date}

                    response.append(log_data)

        return response

    def get_status(self, basepath=None, untracked=False):
        response = None
        if basepath is None:
            basepath = self._path
        if self.path_exists():
            rel_path = normalized_rel_path(self._path, basepath)
            command = "bzr status %s -S" % sanitized(rel_path)
            if not untracked:
                command += " -V"
            _, response, _ = run_shell_command(command, shell=True, cwd=basepath)
            response_processed = ""
            for line in response.split('\n'):
                if len(line.strip()) > 0:
                    response_processed += line[0:4] + rel_path + '/'
                    response_processed += line[4:] + '\n'
            response = response_processed
        return response

    def get_branches(self, local_only=False):
        # see http://doc.bazaar.canonical.com/beta/en/user-guide/shared_repository_layouts.html
        # the 'bzr branches' command exists, but is not useful here (too many assumptions)
        # Else bazaar branches are equivalent to forks in git and hg
        # such branches (forks) on launchpad could be retrieved using
        # the launchpadlib, but the API is probably not stable.
        raise NotImplementedError("get_branches is not implemented for bzr")

    def export_repository(self, version, basepath):
        # execute the bzr export cmd
        cmd = 'bzr export --format=tgz {0} '.format(basepath + '.tar.gz')
        cmd += '{0}'.format(version)
        result, _, _ = run_shell_command(cmd, shell=True, cwd=self._path)
        if result:
            return False
        return True

BZRClient = BzrClient
