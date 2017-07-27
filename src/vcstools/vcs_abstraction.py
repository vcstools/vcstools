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
import os
import warnings


_VCS_TYPES = {}


def register_vcs(vcs_type, clazz):
    """
    :param vcs_type: id, ``str``
    :param clazz: class extending VcsClientBase
    """
    _VCS_TYPES[vcs_type] = clazz


def get_registered_vcs_types():
    """
    :returns: list of valid key to use as vcs_type
    """
    return list(_VCS_TYPES.keys())


def get_vcs(vcs_type):
    """
    Returns the class interfacing with vcs of given type

    :param vcs_type: id of the tpye, e.g. git, svn, hg, bzr
    :returns: class extending VcsClientBase
    :raises: ValueError for unknown vcs_type
    """
    vcs_class = _VCS_TYPES.get(vcs_type, None)
    if not vcs_class:
        raise ValueError('No Client type registered for vcs type "%s"' % vcs_type)
    return vcs_class


def get_vcs_client(vcs_type, path):
    """
    Returns a client with which to interact with the vcs at given path

    :param vcs_type: id of the tpye, e.g. git, svn, hg, bzr
    :returns: instance of VcsClientBase
    :raises: ValueError for unknown vcs_type
    """
    clientclass = get_vcs(vcs_type)
    return clientclass(path)


class VcsClient(object):
    """
    *DEPRECATED* API for interacting with source-controlled paths
    independent of actual version-control implementation.
    """

    def __init__(self, vcs_type, path):
        self._path = path
        warnings.warn("Class VcsClient is deprecated, use from vcstools" +
                      " import get_vcs_client; get_vcs_client() instead")
        self.vcs = get_vcs_client(vcs_type, path)

    def path_exists(self):
        return os.path.exists(self._path)

    def get_path(self):
        return self._path

    # pass through VCSClientBase API
    def get_version(self, spec=None):
        return self.vcs.get_version(spec)

    def get_current_version_label(self):
        return self.vcs.get_current_version_label()

    def get_remote_version(self, fetch=False):
        return self.vcs.get_remote_version(fetch)

    def get_default_remote_version_label(self):
        return self.vcs.get_default_remote_version_label()

    def checkout(self, url, version='', verbose=False, shallow=False):
        return self.vcs.checkout(url,
                                 version,
                                 verbose=verbose,
                                 shallow=shallow)

    def url_matches(self, url, url_or_shortcut):
        return self.vcs.url_matches(url=url, url_or_shortcut=url_or_shortcut)

    def update(self, version='', verbose=False):
        return self.vcs.update(version, verbose=verbose)

    def detect_presence(self):
        return self.vcs.detect_presence()

    def get_vcs_type_name(self):
        return self.vcs.get_vcs_type_name()

    def get_url(self):
        return self.vcs.get_url()

    def get_diff(self, basepath=None):
        return self.vcs.get_diff(basepath)

    def get_status(self, basepath=None, untracked=False, **kwargs):
        return self.vcs.get_status(basepath, untracked, **kwargs)

    def get_log(self, relpath=None, limit=None):
        return self.vcs.get_log(relpath, limit)

    def export_repository(self, version, basepath):
        return self.vcs.export_repository(version, basepath)

    def get_branches(self, local_only=False):
        return self.vcs.get_branches(local_only)


# backwards compat
VCSClient = VcsClient
