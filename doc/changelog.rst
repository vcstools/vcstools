Changelog
=========

0.1
===

0.1.27
------

- fix #47 several performance improvements by removing unecessary update actions after checkout
- fix #45 sometimes commands run forever
- fix #44 minor bug when checking out from repo with default branch not master

0.1.26
------

- fix #38 git commands fail in local repositories with many (>2000) references
- fix #31 get_log() svn xml not available on Ubuntu Lucid (hg 1.4.2)
- fix #37 update() returns True even when fetch failed

0.1.25
------

- minor bugfixes
- travis-ci config file
- fix unit tests for svn diff&status ordering changes
- deprecated VcsClient Class
- added get_log function

0.1.24
------

- fix git update return value to False when fast-forward not possible due to diverge
- fix. svn certificate prompt invisible, svn checkout and update become verbose due to this

0.1.22
------

- Changed the way that git implements detect_presence to fix a bug with submodules in newer versions of git
- fix for git single quotes on Windows
- minor internal api bug where a git function always returned True
- fix gub in svn export_repository

0.1.21
------

- bugfix #66: hg http username prompt hidden
- add export_repository method to vcs_base and all implementations with tests
- bugfix #64: unicode decoding problems

0.1.20
------

- rosws update --verbose for git prints small message when rebasing
- improved python3 compatibility

0.1.19
------
- more python3 compatibility
- code style improved
- match_url to compare bzr shortcuts to real urls
- more unit tests
- get_status required to end with newline, to fix #55

0.1.18
------
- added shallow flag to API, implemented for git

0.1.17
------

- svn stdout output on get_version removed

0.1.16
------

- All SCMs show some output when update caused changes
- All SCMs have verbose option to show all changes done on update
- bugfix for bazaar getUrl() being a joined abspath
- bugfix for not all output being shown when requested


0.1.15
------

- Added pyyaml as a proper dependency, removed detection code.
- remove use of tar entirely, switch to tarfile module
- fix #36 allowing for tar being bsdtar on OSX

0.1.14
------

- Added tarball uncompression.

0.1.13
------

- added this changelog
- git get-version fetches only when local lookup fails
- hg get-version pulls if label not found
- Popen error message incudes cwd path

0.1.12
------

- py_checker clean after all refactorings since 0.1.0

0.1.11
------

- svn and hg update without user interaction
- bugfix #30
- minor bugfixes

0.1.10
------

- minor bugs

0.1.9
-----

- safer sanitization of shell params
- git diff and stat recurse for submodules
- base class manages all calls to Popen

0.1.8
-----

- several bugfixes
- reverted using shell commands instead of bazaar API


0.1.7
-----

- reverted using shell commands instaed of pysvn and mercurial APIs
- protection against shell incection attempts

0.1.6
-----

- bugfixes to svn and bzr
- unified all calls through Popen

0.1.5
-----

- missing dependency to dateutil added

0.1.4
-----

switched shell calls to calls to python API of mercurial, bazaar, py-svn

0.1.3
-----

- fix #6

0.1.2
-----

- fix #15

0.1.1
-----

- more unit tests
- diverse bugfixes
- major change to git client behavior, based around git https://kforge.ros.org/vcstools/trac/ticket/1

0.1.0
-----

- documentation fixes

0.0.3
-----

- import from svn
