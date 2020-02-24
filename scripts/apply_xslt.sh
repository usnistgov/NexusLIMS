#!/usr/bin/env bash

XSLT=***REMOVED***NexusMicroscopyLIMS/xsl/xslStylesheet.xsl
CDCS_XSLT=***REMOVED***NexusMicroscopyLIMS/xsl/cdcs_stylesheet.xsl

for f in *.xml; do
  filename=$(basename -- "${f}")
  filename="${filename%.*}"
  echo "Processing ${f}"
#  /usr/bin/saxon "${f}" "${XSLT}" > "${filename}.html"
  /usr/bin/saxon "${f}" "${CDCS_XSLT}" > "${filename}_cdcs_stylesheet.html"
done