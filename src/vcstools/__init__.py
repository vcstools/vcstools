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
Library for tools that need to interact with ROS-support
version control systems.
"""

from __future__ import absolute_import, print_function, unicode_literals
import logging

from vcstools.vcs_abstraction import VcsClient, VCSClient, register_vcs, \
    get_vcs_client

from vcstools.svn import SvnClient
from vcstools.bzr import BzrClient
from vcstools.hg import HgClient
from vcstools.git import GitClient
from vcstools.tar import TarClient

# configure the VCSClient
register_vcs("svn", SvnClient)
register_vcs("bzr", BzrClient)
register_vcs("git", GitClient)
register_vcs("hg", HgClient)
register_vcs("tar", TarClient)


def setup_logger():
    """
    creates a logger 'vcstools'
    """
    logger = logging.getLogger('vcstools')
    logger.setLevel(logging.WARN)
    handler = logging.StreamHandler()
    handler.setLevel(logging.WARN)

    # create formatter
    template = '%(levelname)s [%(name)s] %(message)s[/%(name)s]'
    formatter = logging.Formatter(template)
    # add formatter to handler
    handler.setFormatter(formatter)

    # add handler to logger
    logger.addHandler(handler)

setup_logger()
