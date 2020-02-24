#!/usr/bin/env bash

if [ $# -eq 0 ]; then
 $0 -h
 exit
fi

while test $# -ge 1; do
  case "$1" in
    -h|--help)
      echo "$0 - run tests for the NexusLIMS library, with optional flag to generate test images"
      echo " "
      echo "$0 [options]"
      echo " "
      echo "options:"
      echo "-h, --help                     show brief help"
      echo "-r, --run-tests                run test suite"
      echo "-rh, --run-tests-htmlcov       run test suite with HTML coverage report"
      echo "-rb                            run record builder tests"
      echo "-g, --generate-test-figs       generate figures for mpl tests instead of running tests"
      exit 0
      ;;
    -g|--generate-test-figs)
      echo "Generating test images for mpl tests..."
      pipenv run pytest mdcs/nexusLIMS/nexusLIMS/tests/test_extractors.py \
             -k TestThumbnailGenerator \
             --mpl-generate-path=mdcs/nexusLIMS/nexusLIMS/tests/files/figs
      echo ""
      break
      ;;
    -r|--run-tests)
      rm .coverage
      echo "Running test suite with coverage..."
      pipenv run pytest mdcs/nexusLIMS/nexusLIMS/tests \
        --cov=mdcs/nexusLIMS/nexusLIMS \
        --mpl --mpl-baseline-path=mdcs/nexusLIMS/nexusLIMS/tests/files/figs
      break
      ;;
    -rh|--run-tests-htmlcov)
      echo "Removing previous coverage reports..."
      rm -rf htmlcov/*
      rm .coverage
      rm .coverage.*
      echo "Running test suite with coverage (HTML output)..."
      pipenv run pytest mdcs/nexusLIMS/nexusLIMS/tests \
        --cov=mdcs/nexusLIMS/nexusLIMS \
        --cov-report html:$(pwd)/htmlcov \
        --mpl --mpl-baseline-path=mdcs/nexusLIMS/nexusLIMS/tests/files/figs
      break
      ;;
    -rb)
      echo "Removing previous coverage reports..."
      rm -rf htmlcov/*
      rm .coverage
      rm .coverage.*
      echo "Running record builder test suite with coverage..."
      pipenv run pytest mdcs/nexusLIMS/nexusLIMS/tests \
        -k "test_records" \
        --cov=mdcs/nexusLIMS/nexusLIMS \
        --cov-report html:$(pwd)/htmlcov \
        --mpl --mpl-baseline-path=mdcs/nexusLIMS/nexusLIMS/tests/files/figs
      break
      ;;
  esac
done