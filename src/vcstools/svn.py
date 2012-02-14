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
import subprocess

_pysvn_missing = False
try:
    import pysvn
except:
    _pysvn_missing = True

import time
_dateutil_missing = False
try:
    import dateutil.parser
except:
    _dateutil_missing = True
    
import tempfile
from .vcs_base import VcsClientBase, VcsError


class SvnClient(VcsClientBase):

    def __init__(self, path):
        """
        :raises: VcsError if python-svn not detected
        """
        VcsClientBase.__init__(self, 'svn', path)
        if _pysvn_missing:
            raise VcsError("python-svn could not be imported. Please install python-svn. On debian systems sudo apt-get install python-svn")
        # test for svn here, we need it for status
        try:
            # SVN commands produce differently formatted output for french locale
            subprocess.Popen(['svn', '--version'],
                             stdout=subprocess.PIPE,
                             env={"LANG":"en_US.UTF-8"}).communicate()[0]
        except:
            raise VcsError("svn not installed")
        self._pysvnclient = pysvn.Client()

    @staticmethod
    def get_environment_metadata():
        metadict = {}
        try:
            import pysvn
            metadict["version"] = '.'.join([str(x) for x in pysvn.svn_api_version])
        except VcsError:
            metadict["version"] = "no svn installed"
        try:
            import pysvn
            metadict["dependency"] = 'pysvn: %s'%('.'.join([str(x) for x in pysvn.version]))
        except:
            metadict["dependency"] = "no pysvn installed"
        metadict["features"] = "dateutil: %s"%(_dateutil_missing)
        return metadict

    def get_url(self):
        """
        :returns: SVN URL of the directory path (output of svn info command), or None if it cannot be determined
        """
        info = self._get_info_dict(self._path)
        if info is not None:
            return info.data['url']
        return None

    def detect_presence(self):
        return self._get_info_dict(self._path, show_error=False) is not None

    def checkout(self, url, version=''):
        if self.path_exists():
            sys.stderr.write("Error: cannot checkout into existing directory\n")
            return False
        try:
            self._pysvnclient.checkout(url, self._path, self._parse_revision(version))
        except pysvn.ClientError as e:
            sys.stderr.write("Failed to checkout from url %s : %s\n"%(url, str(e)))
            return False
        return True

    def update(self, version=''):
        try:
            result = self._pysvnclient.update(self._path, revision = self._parse_revision(version))[0]
        except pysvn.ClientError as e:
            sys.stderr.write("Failed to update : %s\n"%str(e))
            return False
        if result.number == -1:
            # pysvn's way of telling us something is odd, e.g. there is no svn repo
            sys.stderr.write("Failed to update, maybe no repo at %s : %s\n"%(self._path, str(e)))
            return False
        return True

    def get_version(self, spec=None):
        """
        :param spec: (optional) spec can be what 'svn info --help'
        allows, meaning a revnumber, {date}, HEAD, BASE, PREV, or
        COMMITTED.

        :returns: current revision number of the repository. Or if spec
        provided, the number of a revision specified by some
        token.
        """
        # info2 returns a list of (path, dict) tupels. Need the dict of first tuple
        try:
            datadict = self._pysvnclient.info2(self._path, revision= self._parse_revision(spec), recurse = False)[0][1]
            if datadict is not None:
                return '-r%s'%datadict.data["rev"].number
        except pysvn.ClientError as e:
            sys.stderr.write("Failed to get svn info : %s\n"%str(e))
            return None

    def get_diff(self, basepath=None):
        response = None
        if basepath == None:
            basepath = self._path
        if self.path_exists():
            try:
                # first argument to diff is a writable path for temp files
                response = self._pysvnclient.diff(tempfile.gettempdir(),
                                              self._path,
                                              relative_to_dir = basepath)
            except pysvn.ClientError as e:
                sys.stderr.write("Failed to svn diff : %s\n"%str(e))
        return response
 
 
    def get_status(self, basepath=None, untracked=False):
        # status not implemented yet using pysvn as we would have to
        # format data ourselves and amend the relative paths
        response=None
        if basepath == None:
            basepath = self._path
        if self.path_exists():
            rel_path = self._normalized_rel_path(self._path, basepath)
            command = "cd %s; svn status %s"%(basepath, rel_path)
            if not untracked:
                command += " -q"
            stdout_handle = os.popen(command, "r")
            response = stdout_handle.read()
        return response

    def _get_info_dict(self, path, show_error=True):
        """returns the result of svn info path as a dict, if path is
        an svn controlled resource. Returns None else."""
        try:
            info = self._pysvnclient.info(path)
            return info
        except pysvn.ClientError as e:
            if show_error:
                sys.stderr.write("Failed to get svn info for path %s : %s\n"%(path, str(e)))
            return None

    def _parse_revision(self, version):
        """takes a string and returns a pysvn revision object, or throws an error if format is mysterious"""
        if version == None or version == '':
            revision=pysvn.Revision(pysvn.opt_revision_kind.unspecified)
        elif version.startswith("-r"):
            revision=pysvn.Revision(pysvn.opt_revision_kind.number, int(version[2:]))
        else:
            if version.upper() == "BASE":
                revision=pysvn.Revision(pysvn.opt_revision_kind.base)
            elif version.upper() == "HEAD":
                revision=pysvn.Revision(pysvn.opt_revision_kind.head)
            elif version.upper() == "COMMITTED":
                revision=pysvn.Revision(pysvn.opt_revision_kind.committed)
            elif version.upper() == "PREV":
                revision=pysvn.Revision(pysvn.opt_revision_kind.previous)
            elif '{' in version and '}' in version:
                try:
                    if _dateutil_missing:
                        raise VcsError("vcstools without dateutils library unable to handle revisions by date")
                    else:
                        # dateutil parser can cope with "{}"
                        date=dateutil.parser.parse(version)
                        revision=pysvn.Revision(pysvn.opt_revision_kind.date, date)
                except ValueError:
                    raise ValueError("%s is not a valid ISO time:"%version)
            else:
                revision=pysvn.Revision(pysvn.opt_revision_kind.number, int(version))
        return revision
        
SVNClient = SvnClient
