Contributing guide
==================

Thanks for your interest in contributing to vcstools.

Any kinds of contributions are welcome: Bug reports, Documentation, Patches.

Developer Environment
---------------------

For many tasks, it is okay to just develop using a single installed python version. But if you need to test/debug the project in multiple python versions, you need to install those version::

1. (Optional) Install multiple python versions

   1. (Optional) Install [pyenv](https://github.com/pyenv/pyenv-installer) to manage python versions
   2. (Optional) Using pyenv, install the python versions used in testing::

       pyenv install 2.7.16
       pyenv install 3.6.8

It may be okay to run and test python against locally installed libraries, but if you need to have a consistent build, it is recommended to manage your environment using `virtualenv <https://virtualenv.readthedocs.org/en/latest/>`_::

  $ virtualenv ~/vcstools_venv
  $ source ~/vcstools_venv/bin/activate

Editable library install
-------------------

It is common to work on rosinstall or wstool while also needing to make changes to the vcstools library. For that purpose, use::

  $ pip install --editable /path/to/vcstools_source

For convenience also consider [virtualenvwrapper](https://pypi.org/project/virtualenvwrapper/ ).

At this point in any shell where you run ``source ~/vcstools_venv/bin/activate``, you can use vcstools and evny edits to files in the vcstools source will take effect immediately.
This is the effect of ``pip install --editable``, see ``pip install --help``.

To setup a virtualenv for Python3 simply do this (from a clean terminal)::

  $ virtualenv --python=python3 ~/vcstools_venv_py3
  $ source ~/vcstools_venv_py3

When you're done developing, you can exit any shells where you did ``source .../bin/activate`` and delete the virtualenv folder, e.g. ``~/vcstools_venv``.

Testing
-------

Prerequisites:

* The tests require git, mercurial, bazaar and subversion to be installed.

Using the python library nose to test::

  # run all tests using nose
  $ nosetests
  # run one test using nose
  $ nosetests {testname}
  # run all tests with coverage check
  $ python setup.py test
  # run all tests using python3
  $ python3 setup.py test
  # run all tests against multiple python versions (same as in travis)
  $ tox

Releasing
---------

* Update `src/vcstools/__version__.py`
* Check `doc/changelog` is up to date
* Check `stdeb.cfg` is up to date
* prepare release dependencies::

      pip install --upgrade setuptools wheel twine

* Upload to testpypi::

      python3 setup.py sdist bdist_wheel
      twine upload --repository testpypi dist/*

* Check testpypi download files and documentation look ok
* Actually release::

      twine upload dist/*

* Create and push tag::

      git tag x.y.z
      git push
      git push --tags
