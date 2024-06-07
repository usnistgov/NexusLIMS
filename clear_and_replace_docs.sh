#!/bin/env bash

# This script will remove the existing documentation files and move the contents of 
# the _build/ directory into their place. It is useful when releasing a new version
# of the documentation to the public docs site

set -x 
rm -r *.html objects.inv searchindex.js docHtml.css .buildinfo .doctrees/ api/ img/ _images/ _modules/ _sources/ _static/
mv _build/* .
