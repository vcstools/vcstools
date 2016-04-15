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
svn vcs support.
"""

from __future__ import absolute_import, print_function, unicode_literals
import os
import sys
try:
    # PY3K
    from urlparse import urlsplit
except ImportError:
    from urllib.parse import urlsplit
import re
import tarfile

import dateutil.parser  # For parsing date strings
import xml.dom.minidom  # For parsing logfiles

from vcstools.vcs_base import VcsClientBase, VcsError
from vcstools.common import sanitized, normalized_rel_path, \
    run_shell_command, ensure_dir_notexists


def canonical_svn_url_split(url):
    """
    checks url for traces of canonical svn structure,
    and return root, type, name (of tag or branch), subfolder, query and fragment (see urllib urlparse)
    This should allow creating a different url for switching to a different tag or branch

    :param url: location of central repo, ``str``
    :returns: dict {root, type, name, subfolder, query, fragment}
    with type one of "trunk", "tags", "branches"
    """
    result = {'root': url, 'type': None, 'name': None, 'subfolder': None, 'query': None, 'fragment': None}
    if not url:
        return result
    splitresult = urlsplit(url)
    if not splitresult.scheme:
        # svn does not accept mere paths
        return result
    canonical_pattern = re.compile('(.*/)?(trunk|branches|tags)(/.*)?')
    matches = canonical_pattern.findall(splitresult.path)
    if len(matches) > 0:
        if len(matches) > 1:
            raise ValueError('Invalid path in url %s' % splitresult.path)
        prefix, branchtype, rest = matches[0]
        prefix = prefix.rstrip('/')
        rest = rest.lstrip('/')
        if branchtype == 'trunk':
            result['root'] = '%s://%s%s' % (splitresult.scheme,
                                            splitresult.netloc,
                                            prefix)
            result['type'] = branchtype
            result['query'] = splitresult.query or None
            result['fragment'] = splitresult.fragment or None
            if rest:
                result['subfolder'] = rest
        elif branchtype in ['tags', 'branches']:
            result['type'] = branchtype
            result['root'] = '%s://%s%s' % (splitresult.scheme,
                                            splitresult.netloc,
                                            prefix)
            result['query'] = splitresult.query or None
            result['fragment'] = splitresult.fragment or None
            if rest:
                splitrest = rest.split('/', 1)
                print(splitrest)
                result['name'] = splitrest[0]
                if len(splitrest) == 2 and splitrest[1]:
                    result['subfolder'] = splitrest[1]
    return result


def get_remote_contents(url):
    contents = []
    if url:
        cmd = 'svn ls %s' % (url)
        result_code, output, _ = run_shell_command(cmd, shell=True)
        if result_code:
            return []
        contents = [line.strip('/') for line in output.splitlines()]
    return contents


def _get_svn_version():
    """Looks up svn version by calling svn --version.
    :raises: VcsError if svn is not installed"""
    try:
        # SVN commands produce differently formatted output for french locale
        value, output, _ = run_shell_command('svn --version',
                                             shell=True,
                                             us_env=True)
        if value == 0 and output is not None and len(output.splitlines()) > 0:
            version = output.splitlines()[0]
        else:
            raise VcsError("svn --version returned " +
                           "%s maybe svn is not installed" % value)
    except VcsError as exc:
        raise VcsError("Could not determine whether svn is installed: " +
                       str(exc))
    return version


class SvnClient(VcsClientBase):

    def __init__(self, path):
        """
        :raises: VcsError if python-svn not detected
        """
        VcsClientBase.__init__(self, 'svn', path)
        # test for svn here, we need it for status
        _get_svn_version()

    @staticmethod
    def get_environment_metadata():
        metadict = {}
        try:
            metadict["version"] = _get_svn_version()
        except:
            metadict["version"] = "no svn installed"
        return metadict

    def get_url(self):
        """
        :returns: SVN URL of the directory path (output of svn info command),
         or None if it cannot be determined
        """
        if self.detect_presence():
            # 3305: parsing not robust to non-US locales
            cmd = 'svn info %s' % self._path
            _, output, _ = run_shell_command(cmd, shell=True)
            matches = [l for l in output.splitlines() if l.startswith('URL: ')]
            if matches:
                return matches[0][5:]

    @staticmethod
    def static_detect_presence(path):
        return os.path.isdir(os.path.join(path, '.svn'))

    def checkout(self, url, version='', verbose=False,
                 shallow=False, timeout=None):
        if url is None or url.strip() == '':
            raise ValueError('Invalid empty url : "%s"' % url)
        # Need to check as SVN 1.6.17 writes into directory even if not empty
        if not ensure_dir_notexists(self.get_path()):
            self.logger.error("Can't remove %s" % self.get_path())
            return False
        if version is not None and version != '':
            if not version.startswith("-r"):
                version = "-r%s" % version
        elif version is None:
            version = ''
        cmd = 'svn co %s %s %s' % (sanitized(version),
                                   sanitized(url),
                                   self._path)
        value, _, msg = run_shell_command(cmd,
                                          shell=True,
                                          no_filter=True)
        if value != 0:
            if msg:
                self.logger.error('%s' % msg)
            return False
        return True

    def update(self, version=None, verbose=False, timeout=None):
        if not self.detect_presence():
            sys.stderr.write("Error: cannot update non-existing directory\n")
            return False
        # protect against shell injection

        if version is not None and version != '':
            if not version.startswith("-r"):
                version = "-r" + version
        elif version is None:
            version = ''
        cmd = 'svn up %s %s --non-interactive' % (sanitized(version),
                                                  self._path)
        value, _, _ = run_shell_command(cmd,
                                        shell=True,
                                        no_filter=True)
        if value == 0:
            return True
        return False

    def get_version(self, spec=None):
        """
        :param spec: (optional) spec can be what 'svn info --help'
          allows, meaning a revnumber, {date}, HEAD, BASE, PREV, or
          COMMITTED.
        :param path: the url to use, default is for this repo
        :returns: current revision number of the repository. Or if spec
          provided, the number of a revision specified by some
          token.
        """
        return self._get_version_from_path(spec=spec, path=self._path)

    def _get_version_from_path(self, spec=None, path=None):
        """
        :param spec: (optional) spec can be what 'svn info --help'
          allows, meaning a revnumber, {date}, HEAD, BASE, PREV, or
          COMMITTED.
        :param path: the url to use, default is for this repo
        :returns: current revision number of the repository. Or if spec
          provided, the number of a revision specified by some
          token.
        """
        if not self.path_exists():
            return None
        command = 'svn info '
        if spec is not None:
            if spec.isdigit():
                # looking up svn with "-r" takes long, and if spec is
                # a number, all we get from svn is the same number,
                # unless we try to look at higher rev numbers (in
                # which case either get the same number, or an error
                # if the rev does not exist). So we first do a very
                # quick svn info, and check revision numbers.
                currentversion = self.get_version(spec=None)
                # currentversion is like '-r12345'
                if currentversion is not None and \
                   int(currentversion[2:]) > int(spec):
                    # so if we know revision exist, just return the
                    # number, avoid the long call to svn server
                    return '-r' + spec
            if spec.startswith("-r"):
                command += sanitized(spec)
            else:
                command += sanitized('-r%s' % spec)
        command += " %s" % path
        # #3305: parsing not robust to non-US locales
        _, output, _ = run_shell_command(command, shell=True, us_env=True)
        if output is not None:
            matches = \
                [l for l in output.splitlines() if l.startswith('Last Changed Rev: ')]
            if len(matches) == 1:
                split_str = matches[0].split()
                if len(split_str) == 4:
                    return '-r' + split_str[3]
        return None

    def get_current_version_label(self):
        # SVN branches are part or URL
        return None

    def get_remote_version(self, fetch=False):
        if fetch is False:
            return None
        return self._get_version_from_path(path=self.get_url())

    def get_diff(self, basepath=None):
        response = None
        if basepath is None:
            basepath = self._path
        if self.path_exists():
            rel_path = normalized_rel_path(self._path, basepath)
            command = 'svn diff %s' % sanitized(rel_path)
            _, response, _ = run_shell_command(command,
                                               shell=True,
                                               cwd=basepath)
        return response

    def get_affected_files(self, revision):
        cmd = "svn diff --summarize -c {0}".format(
            revision)

        code, output, _ = run_shell_command(cmd, shell=True, cwd=self._path)
        affected = []
        if code == 0:
            for filename in output.splitlines():
                affected.append(filename.split(" ")[7])
        return affected

    def get_log(self, relpath=None, limit=None):
        response = []

        if relpath is None:
            relpath = ''

        if self.path_exists() and os.path.exists(os.path.join(self._path, relpath)):
            # Get the log
            limit_cmd = (("--limit %d" % (int(limit))) if limit else "")
            command = "svn log %s --xml %s" % (limit_cmd, sanitized(relpath) if len(relpath) > 0 else '')
            return_code, xml_response, stderr = run_shell_command(command, shell=True, cwd=self._path)

            # Parse response
            dom = xml.dom.minidom.parseString(xml_response)
            log_entries = dom.getElementsByTagName("logentry")

            # Extract the entries
            for log_entry in log_entries:
                author_tag = log_entry.getElementsByTagName("author")[0]
                date_tag = log_entry.getElementsByTagName("date")[0]
                msg_tags = log_entry.getElementsByTagName("msg")

                log_data = dict()
                log_data['id'] = log_entry.getAttribute("revision")
                log_data['author'] = author_tag.firstChild.nodeValue
                log_data['email'] = None
                log_data['date'] = dateutil.parser.parse(str(date_tag.firstChild.nodeValue))
                if len(msg_tags) > 0 and msg_tags[0].firstChild:
                    log_data['message'] = msg_tags[0].firstChild.nodeValue
                else:
                    log_data['message'] = ''

                response.append(log_data)

        return response

    def get_status(self, basepath=None, untracked=False):
        response = None
        if basepath is None:
            basepath = self._path
        if self.path_exists():
            rel_path = normalized_rel_path(self._path, basepath)
            # protect against shell injection
            command = 'svn status %s' % sanitized(rel_path)
            if not untracked:
                command += " -q"
            _, response, _ = run_shell_command(command,
                                               shell=True,
                                               cwd=basepath)
            if response is not None and \
               len(response) > 0 and \
               response[-1] != '\n':
                response += '\n'
        return response

    def export_repository(self, version, basepath):
        # Run the svn export cmd
        cmd = 'svn export {0} {1}'.format(os.path.join(self._path, version),
                                          basepath)
        result, _, _ = run_shell_command(cmd, shell=True)
        if result:
            return False
        try:
            # tar gzip the exported repo
            targzip_file = tarfile.open(basepath + '.tar.gz', 'w:gz')
            try:
                targzip_file.add(basepath, '')
            finally:
                targzip_file.close()
        finally:
            # clean up
            from shutil import rmtree
            rmtree(basepath)
        return True

    def get_branches(self, local_only=False):
        url = self.get_url()
        canonical_dict = canonical_svn_url_split(url)
        if local_only:
            if canonical_dict['type'] == 'branches':
                return [canonical_dict['name']]
            return []

        branches = []
        if canonical_dict['type']:
            branches = get_remote_contents('%s/%s' % (canonical_dict['root'], 'branches'))

        return branches


SVNClient = SvnClient
