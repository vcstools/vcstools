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

"""

import subprocess
import os
import urllib
import tempfile
import sys
import shutil

_yaml_missing = False
try:
    import yaml
except:
    _yaml_missing = True

from .vcs_base import VcsClientBase, VcsError

def _get_tar_version():
    """Looks up tar version by calling tar --version.

    :raises: VcsError if git is not installed or returns
    something unexpected"""
    try:
        version = subprocess.Popen(['tar --version'],
                                   shell = True,
                                   stdout = subprocess.PIPE).communicate()[0]
    except:
        raise VcsError("git not installed")
    if version.startswith('tar '):
        version = version.splitlines()[0][len('tar '):].strip()
    else:
        raise VcsError("tar --version returned invalid string: '%s'"%version)
    return version

class TarClient(VcsClientBase):

    def __init__(self, path):
        """
        @raise VcsError if tar not detected
        """
        VcsClientBase.__init__(self, 'tar', path)
        self.metadata_path = os.path.join(self._path, ".tar")
        _get_tar_version()
        if _yaml_missing:
            raise VcsError("Python yaml libs could not be imported. Please install python-yaml. On debian systems sudo apt-get install python-yaml")

    @staticmethod
    def get_environment_metadata():
        metadict = {}
        try:
            version = _get_tar_version()
        except VcsError as e:
            version = "No tar installed"
        metadict["version"] = version
        return metadict

    def get_url(self):
        """
        :returns: TAR URL of the directory path (output of tar info command), or None if it cannot be determined
        """
        if self.detect_presence():
            with open(self.metadata_path, 'r') as metadata_file:
                metadata = yaml.load(metadata_file.read())
                if 'url' in metadata:
                    return metadata['url']                
        return None

    def detect_presence(self):
        return self.path_exists() and os.path.exists(self.metadata_path)

    def checkout(self, url, version=''):
        if self.path_exists():
            sys.stderr.write("Error: cannot checkout into existing directory\n")
            return False
        try:
            (filename, headers) = urllib.urlretrieve(url)
            #print "filename", filename
            tempdir = tempfile.mkdtemp()
            cmd = "tar -xf %s -C %s"%(filename, tempdir)
            #print "extract command", cmd
            if subprocess.call(cmd, shell=True) == 0:
                subdir = os.path.join(tempdir, version)
                if not os.path.isdir(subdir):
                    sys.stderr.write("%s is not a subdirectory\n"%subdir)
                    return False
                try:
                    #os.makedirs(os.path.dirname(self._path))
                    shutil.move(subdir, self._path)
                except Exception as ex:
                    print "%s failed to move %s to %s"%(ex, subdir, self._path)
                metadata = yaml.dump({'url': url, 'version':version})
                with open(self.metadata_path, 'w') as md:
                    md.write(metadata)
                if os.path.exists(tempdir):
                    shutil.rmtree(tempdir)
                return True
            else:
                sys.stderr.write("failed to extract")
            
            shutil.rmtree(tempdir)
        except Exception as e:
            sys.stderr.write("Tarball download unpack failed%s\n"%str(e))
            return False
        return False

    def update(self, version=''):
        if not self.detect_presence():
            return False

        if version != self.get_version():
            sys.stderr.write("Tarball Client does not support updating with different version.\n")
            return False

        return True

    def get_version(self):
        if self.detect_presence():
            with open(self.metadata_path, 'r') as metadata_file:
                metadata = yaml.load(metadata_file.read())
                if 'version' in metadata:
                    return metadata['version']
        return None

# backwards compatibility
TARClient = TarClient
