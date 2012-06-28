#!/bin/sh

rm -rf build/html
mkdir build
mkdir build/html

echo '\n PyLint report \n****************************************\n'

pylint -d I0011 -i y -f html api tests >> build/html/lint.html

echo '\n Unittest coverage \n****************************************\n'

nosetests --with-coverage --cover-html --cover-html-dir=build/html/ --cover-erase --cover-package=api

echo '\n Code style \n****************************************\n'

pep8 --repeat --statistics --count api

echo '\n Issues report \n****************************************\n'
pyflakes api

echo '\n Pychecker report \n****************************************\n'

pychecker -# 99 api/*.py api/compute/*.py api/network/*.py api/storage/*.py api/extensions/*.py

# TODO: create project!
#epydoc epydoc.prj
