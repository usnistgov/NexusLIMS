#!/usr/bin/env bash

XSLT=***REMOVED***NexusMicroscopyLIMS/xsl/xslStylesheet.xsl

for f in *.xml; do
  filename=$(basename -- "${f}")
  extension="${filename##*.}"
  filename="${filename%.*}"
  output_filename=${filename}.html
  echo "Processing ${f}"
  /usr/bin/saxon ${f} ${XSLT} > ${filename}.html
done