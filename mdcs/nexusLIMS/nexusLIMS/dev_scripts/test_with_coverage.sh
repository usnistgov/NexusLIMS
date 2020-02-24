#!/usr/bin/env bash

# This script was written to work on Josh's local machine, but can be tweaked as necessary to get it to work on another machine

cd ***REMOVED***NexusMicroscopyLIMS

echo $(pwd)

pipenv run pytest --cov=nexusLIMS \
                  --cov-report html:***REMOVED***NexusMicroscopyLIMS/mdcs/nexusLIMS/nexusLIMS/tests/_coverage_output \
                  mdcs/nexusLIMS/nexusLIMS/tests/"$1"

echo ""
echo "see file://***REMOVED***NexusMicroscopyLIMS/mdcs/nexusLIMS/nexusLIMS/tests/_coverage_output/index.html for coverage summary"