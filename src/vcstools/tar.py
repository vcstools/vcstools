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
tar vcs support.

The implementation uses the "version" argument to indicate a subfolder
within a tarfile.  Hence one can organize sources by creating one
tarfile with a folder inside for each version.
"""


from __future__ import absolute_import, print_function, unicode_literals
import os
import tempfile
import shutil
import tarfile
import sys
import yaml
from vcstools.vcs_base import VcsClientBase, VcsError
from vcstools.common import urlretrieve_netrc, ensure_dir_notexists


__pychecker__ = 'unusednames=spec'

_METADATA_FILENAME = ".tar"


class TarClient(VcsClientBase):

    def __init__(self, path):
        """
        @raise VcsError if tar not detected
        """
        VcsClientBase.__init__(self, 'tar', path)
        self.metadata_path = os.path.join(self._path, _METADATA_FILENAME)

    @staticmethod
    def get_environment_metadata():
        metadict = {}
        metadict["version"] = 'tarfile version: %s' % tarfile.version
        return metadict

    def get_url(self):
        """
        :returns: TAR URL of the directory path (output of tar info
        command), or None if it cannot be determined
        """
        if self.detect_presence():
            with open(self.metadata_path, 'r') as metadata_file:
                metadata = yaml.load(metadata_file.read())
                if 'url' in metadata:
                    return metadata['url']
        return None

    @staticmethod
    def static_detect_presence(path):
        return os.path.isfile(os.path.join(path, _METADATA_FILENAME))

    def checkout(self, url, version='', verbose=False,
                 shallow=False, timeout=None):
        """
        untars tar at url to self.path.
        If version was given, only the subdirectory 'version' of the
        tar will end up in self.path.  Also creates a file next to the
        checkout named *.tar which is a yaml file listing origin url
        and version arguments.
        """
        if not ensure_dir_notexists(self.get_path()):
            self.logger.error("Can't remove %s" % self.get_path())
            return False
        tempdir = None
        result = False
        try:
            tempdir = tempfile.mkdtemp()
            if os.path.isfile(url):
                filename = url
            else:
                (filename, _) = urlretrieve_netrc(url)
                # print "filename", filename
            temp_tarfile = tarfile.open(filename, 'r:*')
            members = None  # means all members in extractall
            if version == '' or version is None:
                subdir = tempdir
                self.logger.warn("No tar subdirectory chosen via the 'version' argument for url: %s" % url)
            else:
                # getmembers lists all files contained in tar with
                # relative path
                subdirs = []
                members = []
                for m in temp_tarfile.getmembers():
                    if m.name.startswith(version + '/'):
                        members.append(m)
                    if m.name.split('/')[0] not in subdirs:
                        subdirs.append(m.name.split('/')[0])
                if not members:
                    raise VcsError("%s is not a subdirectory with contents in members %s" % (version, subdirs))
                subdir = os.path.join(tempdir, version)
            temp_tarfile.extractall(path=tempdir, members=members)

            if not os.path.isdir(subdir):
                raise VcsError("%s is not a subdirectory\n" % subdir)

            try:
                # os.makedirs(os.path.dirname(self._path))
                shutil.move(subdir, self._path)
            except Exception as ex:
                raise VcsError("%s failed to move %s to %s" % (ex, subdir, self._path))
            metadata = yaml.dump({'url': url, 'version': version})
            with open(self.metadata_path, 'w') as mdat:
                mdat.write(metadata)
            result = True

        except Exception as exc:
            self.logger.error("Tarball download unpack failed: %s" % str(exc))
        finally:
            if tempdir is not None and os.path.exists(tempdir):
                shutil.rmtree(tempdir)
        return result

    def update(self, version='', verbose=False, timeout=None):
        """
        Does nothing except returning true if tar exists in same
        "version" as checked out with vcstools.
        """
        if not self.detect_presence():
            return False
        if version != self.get_version():
            sys.stderr.write("Tarball Client does not support updating with different version '%s' != '%s'\n"
                             % (version, self.get_version()))
            return False

        return True

    def get_version(self, spec=None):

        if self.detect_presence():
            with open(self.metadata_path, 'r') as metadata_file:
                metadata = yaml.load(metadata_file.read())
                if 'version' in metadata:
                    return metadata['version']
        return None

    def get_current_version_label(self):
        # exploded tar has no local version
        return None

    def get_remote_version(self, fetch=False):
        # exploded tar has no remote version (not a required feature)
        return None

    def get_diff(self, basepath=None):
        return ''

    def get_status(self, basepath=None, untracked=False):
        return ''

    def export_repository(self, version, basepath):
        raise VcsError('export repository not implemented for extracted tars')


# backwards compatibility
TARClient = TarClient
