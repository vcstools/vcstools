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

source setup.sh to include the src folder in your PYTHONPATH.

Testing
-------

Use the python library nose to test::

  $ nosetests

To test with coverage, make sure to have python-coverage installed and run::

  $ nosetests --with-coverage --cover-package vcstools

To run python3 compatibility tests, run either::

  $ nosetests3
  $ python3 -m unittest discover --pattern*.py

Test Status
-----------

.. image:: https://travis-ci.org/vcstools/vcstools.svg?branch=master
    :target: https://travis-ci.org/vcstools/vcstools

