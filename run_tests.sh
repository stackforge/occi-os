#!/bin/sh

rm -rf build/html
mkdir build
mkdir build/html

echo '\n PyLint report \n****************************************\n'

#pylint -d I0011 -i y -f html api tests >> build/html/lint.html
pylint -d W0511,I0011,E1101,E0611,F0401 -i y --report no *

echo '\n Unittest coverage \n****************************************\n'

nosetests --with-coverage --cover-html --cover-html-dir=build/html/ --cover-erase --cover-package=api,nova_glue

echo '\n Code style \n****************************************\n'

pep8 --repeat --statistics --count api nova_glue

echo '\n Issues report \n****************************************\n'
pyflakes api nova_glue

echo '\n Pychecker report \n****************************************\n'

pychecker -# 99 api/*.py api/compute/*.py api/network/*.py api/storage/*.py api/extensions/*.py nova_glue/*.py

# TODO: create project!
#epydoc epydoc.prj
