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
vcs support library base class.
"""
import os
import logging

__pychecker__ = 'unusednames=spec,url,version,basepath,untracked'


class VcsError(Exception):
    """To be thrown when an SCM Client faces a situation because of a
    violated assumption"""

    def __init__(self, value):
        super(VcsError, self).__init__(self)
        self.value = value

    def __str__(self):
        return repr(self.value)


class VcsClientBase(object):

    def __init__(self, vcs_type_name, path):
        """
        subclasses may raise VcsError when a dependency is missing
        """
        self._path = path
        if path is None:
            raise VcsError("Cannot initialize VCSclient without path")
        self._vcs_type_name = vcs_type_name
        self.logger = logging.getLogger('vcstools')

    @staticmethod
    def get_environment_metadata():
        """
        For debugging purposes, returns a dict containing information
        about the environment, like the version of the SCM client, or
        version of libraries involved.
        Suggest considering keywords "version", "dependency", "features" first.
        :returns: a dict containing relevant information
        :rtype: dict
        """
        raise NotImplementedError("Base class get_environment_metadata method must be overridden")

    def path_exists(self):
        return os.path.exists(self._path)

    def get_path(self):
        return self._path

    def url_matches(self, url, url_or_shortcut):
        """
        client can decide whether the url and the other url are equivalent.
        Checks string equality by default
        :param url_or_shortcut: url or shortcut (e.g. bzr launchpad url)
        :returns: bool if params are equivalent
        """
        if url is None or url_or_shortcut is None:
            return False
        return url.rstrip('/') == url_or_shortcut.rstrip('/')

    def get_url(self):
        """
        :returns: The source control url for the path
        :rtype: str
        """
        raise NotImplementedError("Base class get_url method must be overridden")

    def get_version(self, spec=None):
        """
        Find an identifier for a the current or a specified
        revision. Token spec might be a tagname, branchname,
        version-id, SHA-ID, ... depending on the VCS implementation.

        :param spec: token for identifying repository revision
        :type spec: str
        :returns: current revision number of the repository.  Or if
          spec is provided, the respective revision number.
        :rtype: str
        """
        raise NotImplementedError("Base class get_version method must be overridden")

    def checkout(self, url, spec, verbose=False, shallow=False):
        """
        Attempts to create a local repository given a remote
        url. Fails if a directory exists already in target
        location. If a spec is provided, the local repository
        will be updated to that revision. It is possible that
        after a failed call to checkout, a repository still exists,
        e.g. if an invalid revision spec was given.
        If shallow is provided, the scm client may checkout less
        than the full repository history to save time / disk space.

        :param url: where to checkout from
        :type url: str
        :param spec: token for identifying repository revision
        :type spec: str
        :param shallow: hint to checkout less than a full repository
        :type shallow: bool
        :returns: True if successful
        """
        raise NotImplementedError("Base class checkout method must be overridden")

    def update(self, spec, verbose=False):
        """
        Sets the local copy of the repository to a version matching
        the spec. Fails when there are uncommited changes.
        On failures (also e.g. network failure) grants the
        checked out files are in the same state as before the call.

        :param spec: token for identifying repository revision
           desired.  Token might be a tagname, branchname, version-id,
           SHA-ID, ... depending on the VCS implementation.
        :returns: True on success, False else
        """
        raise NotImplementedError("Base class update method must be overridden")

    def detect_presence(self):
        """For auto detection"""
        raise NotImplementedError("Base class detect_presence method must be overridden")

    def get_vcs_type_name(self):
        """ used when auto detected """
        return self._vcs_type_name

    def get_diff(self, basepath=None):
        """
        :param basepath: diff paths will be relative to this, if any
        :returns: A string showing local differences
        :rtype: str
        """
        raise NotImplementedError("Base class get_diff method must be overridden")

    def get_status(self, basepath=None, untracked=False):
        """
        Calls scm status command. Output must be terminated by newline unless empty.

        Semantics of untracked are difficult to generalize.
        In SVN, this would be new files only. In git,
        hg, bzr, this would be changes that have not been added for
        commit.

        :param basepath: status path will be relative to this, if any
        :param untracked: whether to also show changes that would not commit
        :returns: A string summarizing locally modified files
        :rtype: str
        """
        raise NotImplementedError("Base class get_status method must be overridden")

    def export_repository(self, version, basepath):
        """
        Calls scm equivalent to `svn export`, removing scm meta information and tar gzip'ing the repository at a given version to the given basepath.

        :param version: version of the repository to export.  This can be a branch, tag, or path (svn).  When specifying the version as a path for svn, the path should be relative to the root of the svn repository, i.e. 'trunk', or 'tags/1.2.3', or './' for the root.
        :param basepath: this is the path to the tar gzip, excluding the extension which will be .tar.gz
        :returns: True on success, False otherwise.
        """
        raise NotImplementedError("Base class export_repository method must be overridden")
