vcstools
========

The vcstools module provides a Python API for interacting with different version control systems (VCS/SCMs).

See http://www.ros.org/doc/independent/api/vcstools/html/

Installing
----------

Install the latest release on Ubuntu using apt-get::

  $ sudo apt-get install vcstools

On other Systems, use the pypi package::

  $ pip install vcstools

Developer Environment
---------------------

When testing or doing development on vcstools, use a `virtualenv <https://virtualenv.readthedocs.org/en/latest/>`_::

  $ virtualenv ~/vcstools_venv
  $ source ~/vcstools_venv/bin/activate
  $ pip install --editable /path/to/vcstools_source

At this point in any shell where you run ``source ~/vcstools_venv/bin/activate``, you can use vcstools and evny edits to files in the vcstools source will take effect immediately.
This is the effect of ``pip install --editable``, see ``pip install --help``.

To setup a virtualenv for Python3 simply do this (from a clean terminal)::

  $ virtualenv --python=python3 ~/vcstools_venv_py3
  $ source ~/vcstools_venv_py3

When you're done developing, you can exit any shells where you did ``source .../bin/activate`` and delete the virtualenv folder, e.g. ``~/vcstools_venv``.

Testing
-------

Use the python library nose to test::

  $ python setup.py test

To test with coverage, make sure to have python-coverage installed and run::

  $ python setup.py test -n  # this installs test dependencies only
  $ nosetests --with-coverage --cover-package vcstools

To run python3 compatibility tests, run::

  $ python3 setup.py test

Test Status
-----------

.. image:: https://travis-ci.org/vcstools/vcstools.svg?branch=master
    :target: https://travis-ci.org/vcstools/vcstools

