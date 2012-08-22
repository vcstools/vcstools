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


import os

_VCS_TYPES = {}


def register_vcs(vcs_type, clazz):
    _VCS_TYPES[vcs_type] = clazz


def get_vcs(vcs_type):
    return _VCS_TYPES[vcs_type]


class VcsClient(object):
    """
    API for interacting with source-controlled paths independent of
    actual version-control implementation.
    """

    def __init__(self, vcs_type, path):
        self._path = path
        clientclass = get_vcs(vcs_type)
        if clientclass is None:
            raise LookupError("No Vcs client registered for type %s" % vcs_type)
        self.vcs = clientclass(path)

    def path_exists(self):
        return os.path.exists(self._path)

    def get_path(self):
        return self._path

    # pass through VCSClientBase API
    def get_version(self, spec=None):
        return self.vcs.get_version(spec)

    def checkout(self, url, version='', verbose=False, shallow=False):
        return self.vcs.checkout(url, version, verbose=verbose, shallow=shallow)

    def url_matches(self, url, url_or_shortcut):
        return self.vcs.url_matches(url=url, url_or_shortcut=url_or_shortcut)

    def update(self, version, verbose=False):
        return self.vcs.update(version, verbose=verbose)

    def detect_presence(self):
        return self.vcs.detect_presence()

    def get_vcs_type_name(self):
        return self.vcs.get_vcs_type_name()

    def get_url(self):
        return self.vcs.get_url()

    def get_branch_parent(self):
        return self.vcs.get_branch_parent()

    def get_diff(self, basepath=None):
        return self.vcs.get_diff(basepath)

    def get_status(self, basepath=None, untracked=False):
        return self.vcs.get_status(basepath, untracked)

    def export_repository(self, version, basepath):
        return self.vcs.export_repository(version, basepath)

# backwards compat
VCSClient = VcsClient
