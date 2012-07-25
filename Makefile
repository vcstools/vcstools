.PHONY: all setup clean_dist distro clean install deb_dist upload-packages upload-building upload testsetup test

NAME=vcstools
VERSION=$(shell grep version= ./src/vcstools/__version__.py | sed 's,version=,,')

all:
	echo "noop for debbuild"

setup:
	@echo "Confirming version numbers are all consistently taged with ${VERSION}"
	@grep ${VERSION} setup.py 1> /dev/null
	@echo "Confirmed: all files reference version ${VERSION}"

clean_dist:
	-rm -f MANIFEST
	-rm -rf dist
	-rm -rf deb_dist

distro: setup clean_dist
	python setup.py sdist

push: distro
	python setup.py sdist register upload
	scp dist/${NAME}-${VERSION}.tar.gz ipr:/var/www/pr.willowgarage.com/html/downloads/${NAME}

clean: clean_dist
	echo "clean"

install: distro
	sudo checkinstall python setup.py install

deb_dist:
	# need to convert unstable to each distro and repeat
	python setup.py --command-packages=stdeb.command bdist_deb 

upload-packages: deb_dist
	dput -u -c dput.cf all-shadow ${OUTPUT_DIR}/${NAME}_${VERSION}-1_amd64.changes 
	dput -u -c dput.cf all-shadow-fixed ${OUTPUT_DIR}/${NAME}_${VERSION}-1_amd64.changes 
	#dput -u -c dput.cf all-ros ${OUTPUT_DIR}/${NAME}_${VERSION}-1_amd64.changes 

upload-building: deb_dist
	dput -u -c dput.cf all-building ${OUTPUT_DIR}/${NAME}_${VERSION}-1_amd64.changes 

upload: upload-building upload-packages

testsetup:
	echo "running tests"

test: testsetup
	nosetests --with-coverage --cover-package=vcstools --with-xunit
