Developer's Guide
=================

Bug reports and feature requests
--------------------------------

- `Submit a bug report <https://code.ros.org/trac/ros/newticket?component=vcstools&type=defect&&vcstools>`_
- `Submit a feature request <https://code.ros.org/trac/ros/newticket?component=vcstools&type=enhancement&vcstools>`_

Developer Setup
---------------

vcstools uses `setuptools <http://pypi.python.org/pypi/setuptools>`_,
which you will need to download and install in order to run the
packaging.  We use setuptools instead of distutils in order to be able
use ``setup()`` keys like ``install_requires``.

Configure your :envvar:`PYTHONPATH`::

    cd vcstools
    . setup.sh

OR::

    cd vcstools
    python setup.py install

The first will prepend ``vcstools/src`` to your :envvar:`PYTHONPATH`. The second will install vcstools into your dist/site-packages.

Testing
-------

Install test dependencies

::

    pip install nose
    pip install mock


rospkg uses `Python nose
<http://readthedocs.org/docs/nose/en/latest/>`_ for testing, which is
a fairly simple and straightfoward test framework.  The vcstools
mainly use :mod:`unittest` to construct test fixtures, but with nose
you can also just write a function that starts with the name ``test``
and use normal ``assert`` statements.

vcstools also uses `mock <http://www.voidspace.org.uk/python/mock/>`_
to create mocks for testing.

You can run the tests, including coverage, as follows:

::

    cd vcstools
    make test


Documentation
-------------

Sphinx is used to provide API documentation for vcstools.  The documents
are stored in the ``doc`` subdirectory.

