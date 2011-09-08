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

_vcs_types = {}

def register_vcs(vcs_type, clazz):
    _vcs_types[vcs_type] = clazz
  
def get_vcs(vcs_type):
    return _vcs_types[vcs_type]

class VcsClient(object):
    """
    API for interacting with source-controlled paths independent of
    actual version-control implementation.
    """

    def __init__(self, vcs_type, path):
        self._path = path
        self.vcs = get_vcs(vcs_type)(path)
    
    def path_exists(self):
        return os.path.exists(self._path)

    def get_path(self):
        return self._path

    # pass through VCSClientBase API
    def get_version(self, spec=None):
        return self.vcs.get_version(spec)

    def checkout(self, url, version=''):
        return self.vcs.checkout(url, version)

    def update(self, version):
        return self.vcs.update(version)

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

# backwards compat
VCSClient=VcsClient
