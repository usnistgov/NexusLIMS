<?xml version="1.0" encoding="UTF-8"?>
<!--
  ~ NIST Public License - 2019
  ~
  ~ This software was developed by employees of the National Institute of
  ~ Standards and Technology (NIST), an agency of the Federal Government
  ~ and is being made available as a public service. Pursuant to title 17
  ~ United States Code Section 105, works of NIST employees are not subject
  ~ to copyright protection in the United States.  This software may be
  ~ subject to foreign copyright.  Permission in the United States and in
  ~ foreign countries, to the extent that NIST may hold copyright, to use,
  ~ copy, modify, create derivative works, and distribute this software and
  ~ its documentation without fee is hereby granted on a non-exclusive basis,
  ~ provided that this notice and disclaimer of warranty appears in all copies.
  ~
  ~ THE SOFTWARE IS PROVIDED 'AS IS' WITHOUT ANY WARRANTY OF ANY KIND,
  ~ EITHER EXPRESSED, IMPLIED, OR STATUTORY, INCLUDING, BUT NOT LIMITED
  ~ TO, ANY WARRANTY THAT THE SOFTWARE WILL CONFORM TO SPECIFICATIONS, ANY
  ~ IMPLIED WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE,
  ~ AND FREEDOM FROM INFRINGEMENT, AND ANY WARRANTY THAT THE DOCUMENTATION
  ~ WILL CONFORM TO THE SOFTWARE, OR ANY WARRANTY THAT THE SOFTWARE WILL BE
  ~ ERROR FREE.  IN NO EVENT SHALL NIST BE LIABLE FOR ANY DAMAGES, INCLUDING,
  ~ BUT NOT LIMITED TO, DIRECT, INDIRECT, SPECIAL OR CONSEQUENTIAL DAMAGES,
  ~ ARISING OUT OF, RESULTING FROM, OR IN ANY WAY CONNECTED WITH THIS SOFTWARE,
  ~ WHETHER OR NOT BASED UPON WARRANTY, CONTRACT, TORT, OR OTHERWISE, WHETHER
  ~ OR NOT INJURY WAS SUSTAINED BY PERSONS OR PROPERTY OR OTHERWISE, AND
  ~ WHETHER OR NOT LOSS WAS SUSTAINED FROM, OR AROSE OUT OF THE RESULTS OF,
  ~ OR USE OF, THE SOFTWARE OR SERVICES PROVIDED HEREUNDER.
  ~
  -->

<!-- This stylesheet exists to convert the response of the NexusLIMS sharepoint
harvester to a format that conforms with title, id, summary, sample, and project
nodes in the NexusLIMS schema for loading into CDCS (see the .xsl files in the
/xsl folder at the root of the repository and the .xsd schema definition in the
../schemas folder)

If multiple "events" are inputted, this stylesheet will build a record from
the first one only
-->



<xsl:stylesheet xmlns:xsl="http://www.w3.org/1999/XSL/Transform" version="1.0"
                xmlns:d="http://schemas.microsoft.com/ado/2007/08/dataservices"
                xmlns:m="http://schemas.microsoft.com/ado/2007/08/dataservices/metadata">
  <xsl:output method="xml"
              indent="yes"
              encoding="UTF-8"
              omit-xml-declaration="yes"/>
  <xsl:variable name="newline">
<xsl:text>
</xsl:text>
  </xsl:variable>

  <xsl:param name="instrument_PID"/>
  <xsl:param name="instrument_name"/>
  <xsl:param name="collaborator"/>
  <xsl:param name="sample_id"/>

  <xsl:template match="/">
      <xsl:apply-templates select="events/event[1]" />
  </xsl:template>

<xsl:template match="event">
  <xsl:element name="title">
    <xsl:value-of select="title"/>
  </xsl:element><xsl:value-of select="$newline"/>
  <xsl:element name="id">
    <xsl:value-of select="eventId"/>
  </xsl:element><xsl:value-of select="$newline"/>
  <xsl:element name="summary">
    <xsl:element name="experimenter">
      <xsl:value-of select="user/name"/>
    </xsl:element>
    <xsl:choose>
      <xsl:when test="$collaborator">
        <xsl:element name="collaborator">
          <xsl:value-of select="$collaborator"/>
        </xsl:element>
      </xsl:when>
    </xsl:choose>
    <xsl:element name="instrument">
      <xsl:attribute name="pid">
        <xsl:value-of select="$instrument_PID"/>
      </xsl:attribute>
      <xsl:value-of select="$instrument_name"/>
    </xsl:element>
      <xsl:element name="reservationStart">
    <xsl:value-of select="startTime"/>
    </xsl:element>
    <xsl:element name="reservationEnd">
      <xsl:value-of select="endTime"/>
    </xsl:element>
    <xsl:element name="motivation">
      <xsl:value-of select="purpose"/>
    </xsl:element>
  </xsl:element><xsl:value-of select="$newline"/>
  <xsl:element name="sample">
    <xsl:choose>
      <xsl:when test="$sample_id">
        <xsl:attribute name="id">
          <xsl:value-of select="$sample_id"/>
        </xsl:attribute>
      </xsl:when>
    </xsl:choose>
    <xsl:element name="name">
      <xsl:value-of select="sampleDetails"/>
    </xsl:element>
    <xsl:element name="description">
      <xsl:value-of select="description"/>
    </xsl:element>
  </xsl:element><xsl:value-of select="$newline"/>
  <xsl:element name="project">
    <xsl:copy-of select="project/node()"/>
  </xsl:element>
</xsl:template>

</xsl:stylesheet>
