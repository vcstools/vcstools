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
hg vcs support.

using ui object to redirect output into a string
"""


from __future__ import absolute_import, print_function, unicode_literals
import os
import sys

import gzip

import dateutil.parser  # For parsing date strings

from vcstools.vcs_base import VcsClientBase, VcsError
from vcstools.common import sanitized, normalized_rel_path, run_shell_command


def _get_hg_version():
    """Looks up hg version by calling hg --version.
    :raises: VcsError if hg is not installed"""
    try:
        value, output, _ = run_shell_command('hg --version',
                                             shell=True,
                                             us_env=True)
        if value == 0 and output is not None and len(output.splitlines()) > 0:
            version = output.splitlines()[0]
        else:
            raise VcsError("hg --version returned %s, output '%s', maybe hg is not installed" % (value, output))
    except VcsError as e:
        raise VcsError("Could not determine whether hg is installed %s" % e)
    return version


# hg diff cannot seem to be persuaded to accept a different prefix for filenames
def _hg_diff_path_change(diff, path):
    """
    Parses hg diff result and changes the filename prefixes.
    """
    if diff is None:
        return None
    INIT = 0
    INDIFF = 1
    # small state machine makes sure we never touch anything inside
    # the actual diff
    state = INIT

    s_list = [line for line in diff.split(os.linesep)]
    lines = []
    for line in s_list:
        if line.startswith("diff"):
            state = INIT
        if state == INIT:
            if line.startswith("@@"):
                state = INDIFF
                newline = line
            else:
                if line.startswith("---") and not line.startswith("--- /dev/null"):
                    newline = "--- %s%s" % (path, line[5:])
                elif line.startswith("+++") and not line.startswith("+++ /dev/null"):
                    newline = "+++ %s%s" % (path, line[5:])
                elif line.startswith("diff --git"):
                    # first replacing b in case path starts with a/
                    newline = line.replace(" b/", " " + path + "/", 1)
                    newline = newline.replace(" a/", " " + path + "/", 1)
                else:
                    newline = line
        else:
            newline = line
        if newline != '':
            lines.append(newline)
    result = "\n".join(lines)
    return result


class HgClient(VcsClientBase):

    def __init__(self, path):
        """
        :raises: VcsError if hg not detected
        """
        VcsClientBase.__init__(self, 'hg', path)
        _get_hg_version()

    @staticmethod
    def get_environment_metadata():
        metadict = {}
        try:
            metadict["version"] = '%s' % _get_hg_version()
        except:
            metadict["version"] = "no mercurial installed"
        return metadict

    def get_url(self):
        """
        :returns: HG URL of the directory path. (output of hg paths
        command), or None if it cannot be determined
        """
        if self.detect_presence():
            cmd = "hg paths default"
            _, output, _ = run_shell_command(cmd,
                                             shell=True,
                                             cwd=self._path,
                                             us_env=True)
            return output.rstrip()
        return None

    @staticmethod
    def static_detect_presence(path):
        return os.path.isdir(os.path.join(path, '.hg'))

    def checkout(self, url, version='', verbose=False,
                 shallow=False, timeout=None):
        if url is None or url.strip() == '':
            raise ValueError('Invalid empty url : "%s"' % url)
        # make sure that the parent directory exists for #3497
        base_path = os.path.split(self.get_path())[0]
        try:
            os.makedirs(base_path)
        except OSError:
            # OSError thrown if directory already exists this is ok
            pass
        cmd = "hg clone %s %s" % (sanitized(url), self._path)
        value, _, msg = run_shell_command(cmd,
                                          shell=True,
                                          no_filter=True)
        if value != 0:
            if msg:
                sys.logger.error('%s' % msg)
            return False
        if version is not None and version.strip() != '':
            cmd = "hg checkout %s" % sanitized(version)
            value, _, msg = run_shell_command(cmd,
                                              cwd=self._path,
                                              shell=True,
                                              no_filter=True)
            if value != 0:
                if msg:
                    sys.stderr.write('%s\n' % msg)
                return False
        return True

    def update(self, version='', verbose=False, timeout=None):
        verboseflag = ''
        if verbose:
            verboseflag = '--verbose'
        if not self.detect_presence():
            sys.stderr.write("Error: cannot update non-existing directory\n")
            return True
        if not self._do_pull():
            return False
        if version is not None and version.strip() != '':
            cmd = "hg checkout %s %s" % (verboseflag, sanitized(version))
        else:
            cmd = "hg update %s --config ui.merge=internal:fail" % verboseflag
        value, _, _ = run_shell_command(cmd,
                                        cwd=self._path,
                                        shell=True,
                                        no_filter=True)
        if value != 0:
            return False
        return True

    def get_version(self, spec=None):
        """
        :param spec: (optional) token for identifying version. spec can be
          a whatever is allowed by 'hg log -r', e.g. a tagname, sha-ID,
          revision-number
        :returns: the current SHA-ID of the repository. Or if spec is
          provided, the SHA-ID of a revision specified by some
          token.
        """
        # detect presence only if we need path for cwd in popen
        if spec is not None:
            if self.detect_presence():
                command = 'hg log -r %s' % sanitized(spec)
                repeated = False
                output = ''
                # we repeat the call once after pullin if necessary
                while output == '':
                    _, output, _ = run_shell_command(command,
                                                     shell=True,
                                                     cwd=self._path,
                                                     us_env=True)
                    if (output.strip() != '' and
                            not output.startswith("abort") or
                            repeated is True):

                        matches = [l for l in output.splitlines() if l.startswith('changeset: ')]
                        if len(matches) == 1:
                            return matches[0].split(':')[2]
                        else:
                            sys.stderr.write("Warning: found several candidates for hg spec %s" % spec)
                        break
                    self._do_pull()
                    repeated = True
            return None
        else:
            command = 'hg identify -i %s' % self._path
            _, output, _ = run_shell_command(command, shell=True, us_env=True)
            if output is None or output.strip() == '' or output.startswith("abort"):
                return None
            # hg adds a '+' to the end if there are uncommited
            # changes, inconsistent to hg log
            return output.strip().rstrip('+')

    def get_current_version_label(self):
        """
        :param spec: (optional) spec can be what 'svn info --help'
          allows, meaning a revnumber, {date}, HEAD, BASE, PREV, or
          COMMITTED.
        :returns: current revision number of the repository. Or if spec
          provided, the number of a revision specified by some
          token.
        """
        return self.get_branch()

    def get_branch(self):
        if self.path_exists():
            command = "hg branch --repository %s" % self.get_path()
            _, output, _ = run_shell_command(command, shell=True)
            if output is not None:
                return output.strip()
        return None

    def get_remote_version(self, fetch=False):
        if fetch:
            self._do_pull(filter=True)
        # use local information only
        result = self.get_log(limit=1)
        if (len(result) == 1 and 'id' in result[0]):
            return result[0]['id']
        return None

    def get_diff(self, basepath=None):
        response = None
        if basepath is None:
            basepath = self._path
        if self.path_exists():
            rel_path = normalized_rel_path(self._path, basepath)
            command = "hg diff -g %(path)s --repository %(path)s" % {'path': sanitized(rel_path)}
            _, response, _ = run_shell_command(command, shell=True, cwd=basepath)
            response = _hg_diff_path_change(response, rel_path)
        return response

    def get_affected_files(self, revision):
        cmd = "hg log -r %s --template '{files}'" % revision
        code, output, _ = run_shell_command(cmd, shell=True, cwd=self._path)
        affected = []
        if code == 0:
            affected = output.split(" ")
        return affected

    def get_log(self, relpath=None, limit=None):
        response = []

        if relpath is None:
            relpath = ''

        if self.path_exists() and os.path.exists(os.path.join(self._path, relpath)):
            # Get the log
            limit_cmd = (("--limit %d" % (int(limit))) if limit else "")
            HG_COMMIT_FIELDS = ['id', 'author', 'email', 'date', 'message']
            HG_LOG_FORMAT = '\x1f'.join(['{node|short}', '{author|person}',
                                         '{autor|email}', '{date|isodate}',
                                         '{desc}']) + '\x1e'

            command = "hg log %s -b %s --template '%s' %s" % (sanitized(relpath),
                                                              self.get_branch(),
                                                              HG_LOG_FORMAT,
                                                              limit_cmd)
            return_code, response_str, stderr = run_shell_command(command, shell=True, cwd=self._path)

            if return_code == 0:
                # Parse response
                response = response_str.strip('\n\x1e').split("\x1e")
                response = [row.strip().split("\x1f") for row in response]
                response = [dict(zip(HG_COMMIT_FIELDS, row)) for row in response]
                # Parse dates
                for entry in response:
                    entry['date'] = dateutil.parser.parse(entry['date'])

        return response

    def get_status(self, basepath=None, untracked=False):
        response = None
        if basepath is None:
            basepath = self._path
        if self.path_exists():
            rel_path = normalized_rel_path(self._path, basepath)
            # protect against shell injection
            command = "hg status %(path)s --repository %(path)s" % {'path': sanitized(rel_path)}
            if not untracked:
                command += " -mard"
            _, response, _ = run_shell_command(command,
                                               shell=True,
                                               cwd=basepath)
            if response is not None:
                if response.startswith("abort"):
                    raise VcsError("Probable Bug; Could not call %s, cwd=%s" % (command, basepath))
                if len(response) > 0 and response[-1] != '\n':
                    response += '\n'
        return response

    def export_repository(self, version, basepath):
        # execute the hg archive cmd
        cmd = 'hg archive -t tar -r {0} {1}.tar'.format(version, basepath)
        result, _, _ = run_shell_command(cmd, shell=True, cwd=self._path)
        if result:
            return False
        try:
            # gzip the tar file
            with open(basepath + '.tar', 'rb') as tar_file:
                gzip_file = gzip.open(basepath + '.tar.gz', 'wb')
                try:
                    gzip_file.writelines(tar_file)
                finally:
                    gzip_file.close()
        finally:
            # clean up
            os.remove(basepath + '.tar')
        return True

    def get_branches(self, local_only=False):
        if not local_only:
            self._do_pull()
        cmd = 'hg branches'
        result, out, _ = run_shell_command(cmd, shell=True, cwd=self._path,
                                           show_stdout=False)
        if result:
            return []
        branches = []
        for line in out.splitlines():
            line = line.strip()
            line = line.split()
            branches.append(line[0])
        return branches

    def _do_pull(self, filter=False):
        value, _, _ = run_shell_command("hg pull",
                                        cwd=self._path,
                                        shell=True,
                                        no_filter=not filter)
        return value == 0

# backwards compat
HGClient = HgClient
