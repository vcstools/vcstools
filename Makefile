.PHONY: all setup clean_dist distro clean install testsetup test

NAME=vcstools
VERSION=$(shell grep version ./src/vcstools/__version__.py | sed 's,version = ,,')


all:
	echo "noop for debbuild"

setup:
	echo "building version ${VERSION}"

clean_dist:
	-rm -f MANIFEST
	-rm -rf dist
	-rm -rf deb_dist
	-rm -fr src/vcstools.egg-info/

distro: clean_dist setup
	python setup.py sdist

clean: clean_dist
	echo "clean"

install: distro
	sudo checkinstall python setup.py install

testsetup:
	echo "running tests"

test: testsetup
	nosetests --with-coverage --cover-package=vcstools --with-xunit
