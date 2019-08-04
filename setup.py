from setuptools import setup

import imp

with open('README.rst') as readme_file:
    README = readme_file.read()

def get_version():
    ver_file = None
    try:
        ver_file, pathname, description = imp.find_module('__version__', ['src/vcstools'])
        vermod = imp.load_module('__version__', ver_file, pathname, description)
        version = vermod.version
        return version
    finally:
        if ver_file is not None:
            ver_file.close()

test_required = [
    "nose",
    "coverage",
    "coveralls",
    "mock",
    "pep8",
    # run checks in multiple environments
    "tox",
    "tox-pyenv",
    # code metrics
    "radon~=1.4.0; python_version > '3'",
    # coala lint checks only in newest python
    "coala; python_version > '3'",
    "coala-bears; python_version > '3'",
    # mypy typing checks only in newest python
    "mypy; python_version > '3'"
]

setup(name='vcstools',
      version=get_version(),
      packages=['vcstools'],
      package_dir={'': 'src'},
      scripts=[],
      install_requires=['pyyaml', 'python-dateutil'],
      # tests_require automatically installed when running python setup.py test
      tests_require=test_required,
      # extras_require allow pip install .[test]
      extras_require={
        'test': test_required
      },
      author="Tully Foote, Thibault Kruse, Ken Conley",
      author_email="tfoote@osrfoundation.org",
      url="http://wiki.ros.org/vcstools",
      keywords=["scm", "vcs", "git", "svn", "hg", "bzr"],
      classifiers=[
          "Programming Language :: Python",
          "Programming Language :: Python :: 2",
          "Programming Language :: Python :: 3",
          "License :: OSI Approved :: BSD License",
          "Development Status :: 7 - Inactive",
          "Topic :: Software Development :: Version Control"
      ],
      description="VCS/SCM source control library for svn, git, hg, and bzr",
      long_description=README,
      license="BSD")
