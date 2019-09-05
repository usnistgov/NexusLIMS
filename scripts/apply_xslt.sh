#!/usr/bin/env bash

XSLT=***REMOVED***NexusMicroscopyLIMS/xsl/xslStylesheet.xsl

for f in *.xml; do
  filename=$(basename -- "${f}")
  filename="${filename%.*}"
  echo "Processing ${f}"
  /usr/bin/saxon "${f}" "${XSLT}" > "${filename}.html"
done