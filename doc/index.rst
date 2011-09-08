vcstools documentation
======================

.. module:: vcstools
.. moduleauthor:: Tully Foote <tfoote@willowgarage.com>, Thibault Kruse <kruset@in.tum.de>, Ken Conley <kwc@willowgarage.com>

The :mod:`vcstools` module provides a Python API for interacting with
different version control systems (VCS/SCMs).  The :class:`VcsClient`
class provides an API for seamless interacting with Git, Mercurial
(Hg), Bzr and SVN.  The focus of the API is manipulating on-disk
checkouts of source-controlled trees.  Its main use is to support the
`rosinstall` tool.

.. toctree::
   :maxdepth: 2

   vcsclient

Example::

    import vcstools

    # interrogate an existing tree
    client = vcstools.VcsClient('svn', '/path/to/checkout')
    
    print client.get_url()
    print client.get_version()
    print client.get_diff()
    
    # create a new tree
    client = vcstools.VcsClient('hg', '/path/to/new/checkout')
    client.checkout('https://bitbucket.org/foo/bar')
    

Installation
============

vcstools is available on pypi and can be installed via ``pip``
::

    pip install vcstools

or ``easy_install``:

::

    easy_install vcstools

Using vcstools
==============

The :mod:`vcstools` module is meant to be used as a normal Python
module.  After it has been installed, you can ``import`` it normally
and do not need to declare as a ROS package dependency.


Advanced: vcstools developers/contributors
========================================

.. toctree::
   :maxdepth: 2

   developers_guide


Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`

