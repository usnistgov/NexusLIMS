<?xml version="1.0" encoding="UTF-8"?>
<!-- Add the date namespace to allow use of the EXSLT date function -->
<xsl:stylesheet xmlns:xsl="http://www.w3.org/1999/XSL/Transform" version="1.0"
                xmlns:d="http://schemas.microsoft.com/ado/2007/08/dataservices"
                xmlns:m="http://schemas.microsoft.com/ado/2007/08/dataservices/metadata"
                xmlns:date="http://exslt.org/dates-and-times"
                extension-element-prefixes="date">
  <xsl:output method="xml"
              indent="yes"
              encoding="UTF-8"
              omit-xml-declaration="yes"/>
  <!--TODO: output should be structured like the Summary element of the schema
            (or maybe schema will be modified) -->
  <xsl:variable name="newline">
<xsl:text>
</xsl:text>
  </xsl:variable>
  <!--Allow searching by date and by username with parameters-->
  <!--TODO: search for date inclusive, rather than just looking at d:StartTime
            (i.e. if a multi-day reservation straddles the given date, return it
             as well) -->
  <xsl:param name="date"/>
  <xsl:param name="user"/>
  <xsl:param name="division"/>
  <xsl:param name="group"/>

  <xsl:template match="/feed">
    <!--The following choose block decides which entry nodes to process. If
        both date and user parameters are given, select the entries that match
        those values (using the EXSLT date:date() function as necessary. If only
        one is given, use that to filter the list of entries. Otherwise, just
        return all the entries. -->
    <xsl:choose>
      <xsl:when test="$date and $user">
        <xsl:apply-templates select="entry[date:date(./content/m:properties/d:StartTime) = $date and ./link/m:inline/entry/content/m:properties/d:UserName/text() = $user]" />
      </xsl:when>
      <xsl:when test="$date">
        <xsl:apply-templates select="entry[date:date(./content/m:properties/d:StartTime) = $date]" />
      </xsl:when>
      <xsl:when test="$user">
        <xsl:apply-templates select="entry[./link/m:inline/entry/content/m:properties/d:UserName/text() = $user]"/>
      </xsl:when>
      <xsl:otherwise>
        <xsl:apply-templates select="entry" />
      </xsl:otherwise>
    </xsl:choose>
  </xsl:template>

<xsl:template match="entry">
  <xsl:element name="event">
    <xsl:element name="dateSearched">
      <xsl:value-of select="$date"/>
    </xsl:element>
    <xsl:element name="userSearched">
      <xsl:value-of select="$user"/>
    </xsl:element>
    <xsl:element name="title">
      <xsl:value-of select="content/m:properties/d:TitleOfExperiment"/>
    </xsl:element>
    <xsl:element name="instrument">
      <!-- Get name of the instrument (in SharePoint) by going up from entry and -->
      <!-- getting the title attribute of the link node with rel="self" -->
      <xsl:value-of select="../link[@rel='self']/@title"/>
      <!--<xsl:value-of select="substring-before(link[@rel='edit']/@title,'EventsItem')"/>-->
    </xsl:element>
    <xsl:element name="user">
      <xsl:element name="userName">
        <xsl:value-of select="link/m:inline/entry/content/m:properties/d:UserName"/>
      </xsl:element>
      <xsl:element name="name">
        <xsl:value-of select="link/m:inline/entry/content/m:properties/d:Name"/>
      </xsl:element>
      <xsl:element name="email">
        <xsl:value-of select="link/m:inline/entry/content/m:properties/d:WorkEmail"/>
      </xsl:element>
      <xsl:element name="phone">
        <xsl:value-of select="link/m:inline/entry/content/m:properties/d:WorkPhone"/>
      </xsl:element>
      <xsl:element name="office">
        <xsl:value-of select="link/m:inline/entry/content/m:properties/d:Office"/>
      </xsl:element>
      <xsl:element name="link">
        <xsl:value-of select="link/m:inline/entry/id"/>
      </xsl:element>
      <xsl:element name="userId">
        <xsl:value-of select="link/m:inline/entry/content/m:properties/d:Id"/>
      </xsl:element>
    </xsl:element>
    <xsl:element name="purpose">
      <xsl:value-of select="content/m:properties/d:ExperimentPurpose"/>
    </xsl:element>
    <xsl:choose>
      <xsl:when test="$division or $group">
        <xsl:element name="project">
          <xsl:choose>
            <xsl:when test="$division">
              <xsl:element name="division">
                <xsl:value-of select="$division"/>
              </xsl:element>
            </xsl:when>
          </xsl:choose>
          <xsl:choose>
            <xsl:when test="$group">
              <xsl:element name="group">
                <xsl:value-of select="$group"/>
              </xsl:element>
            </xsl:when>
          </xsl:choose>
        </xsl:element>
      </xsl:when>
    </xsl:choose>
    <xsl:element name="sampleDetails">
      <xsl:value-of select="content/m:properties/d:SampleDetails"/>
    </xsl:element>
    <xsl:element name="description">
      <xsl:value-of select="content/m:properties/d:Description"/>
    </xsl:element>
    <xsl:element name="startTime">
      <xsl:value-of select="content/m:properties/d:StartTime"/>
    </xsl:element>
    <xsl:element name="endTime">
      <xsl:value-of select="content/m:properties/d:EndTime"/>
    </xsl:element>
    <xsl:element name="link">
      <xsl:value-of select="id"/>
    </xsl:element>
    <xsl:element name="eventId">
      <xsl:value-of select="content/m:properties/d:Id"/>
    </xsl:element>
  </xsl:element>
<xsl:value-of select="$newline"/>
</xsl:template>

</xsl:stylesheet>
