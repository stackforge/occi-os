#!/bin/sh

rm -rf build/html
mkdir build/html

pylint -d I0011 -i y -f html api tests >> build/html/lint.html

nosetests --with-coverage --cover-html --cover-html-dir=build/html/ --cover-erase --cover-package=api

pep8 --repeat --statistics --count api

pyflakes api

pychecker -# 99 api/*.py api/compute/*.py api/network/*.py api/storage/*.py api/extensions/*.py

# TODO: create project!
#epydoc epydoc.prj
