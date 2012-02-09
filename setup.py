from setuptools import setup

setup(name='vcstools',
      version= '0.1.3',
      packages=['vcstools'],
      package_dir = {'':'src'},
      scripts = [],
      author = "Tully Foote, Thibault Kruse, Ken Conley", 
      author_email = "tfoote@willowgarage.com",
      url = "http://www.ros.org/wiki/vcstools",
      download_url = "http://pr.willowgarage.com/downloads/vcstools/", 
      keywords = ["scm","vcs","git", "svn","hg","bzr"],
      classifiers = [
        "Programming Language :: Python", 
        "License :: OSI Approved :: BSD License" ],
      description = "VCS/SCM source control library for svn, git, hg, and bzr", 
      long_description = """\
Library for managing source code trees from multiple version control systems. 
Current supports svn, git, hg, and bzr.
""",
      license = "BSD"
      )
