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


import os
import sys

import tarfile


from vcstools.vcs_base import VcsClientBase, VcsError
from vcstools.common import sanitized, normalized_rel_path, run_shell_command


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
            raise VcsError("svn --version returned "
                         + "%s maybe svn is not installed" % value)
    except VcsError as exc:
        raise VcsError("Could not determine whether svn is installed: "
                     + str(exc))
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
            #3305: parsing not robust to non-US locales
            cmd = 'svn info %s' % self._path
            _, output, _ = run_shell_command(cmd, shell=True)
            matches = [l for l in output.splitlines() if l.startswith('URL: ')]
            if matches:
                return matches[0][5:]

    def detect_presence(self):
        return self.path_exists() and \
               os.path.isdir(os.path.join(self._path, '.svn'))

    def checkout(self, url, version='', verbose=False, shallow=False):
        # Need to check as SVN does not care
        if self.path_exists():
            sys.stderr.write("Error: cannot checkout into existing "
                           + "directory\n")
            return False
        if version is not None and version != '':
            if not version.startswith("-r"):
                version = "-r%s" % version
        elif version is None:
            version = ''
        cmd = 'svn co %s %s %s' % (sanitized(version),
                                   sanitized(url),
                                   self._path)
        value, _, _ = run_shell_command(cmd,
                                        shell=True,
                                        no_filter=True)
        if value == 0:
            return True
        return False

    def update(self, version=None, verbose=False):
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
        :returns: current revision number of the repository. Or if spec
          provided, the number of a revision specified by some
          token.
        """
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
        command += " %s" % self._path
        # #3305: parsing not robust to non-US locales
        _, output, _ = run_shell_command(command, shell=True, us_env=True)
        if output is not None:
            matches = \
              [l for l in output.splitlines() if l.startswith('Revision: ')]
            if len(matches) == 1:
                split_str = matches[0].split()
                if len(split_str) == 2:
                    return '-r' + split_str[1]
        return None

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
        # tar gzip the exported repo
        targzip_file = tarfile.open(basepath + '.tar.gz', 'w:gz')
        try:
            targzip_file.add(basepath, '')
        finally:
            targzip_file.close()
        # clean up
        from shutil import rmtree
        rmtree(basepath)
        return True


SVNClient = SvnClient
