<?xml version="1.0" encoding="UTF-8"?>
<xsl:stylesheet xmlns:xsl="http://www.w3.org/1999/XSL/Transform"
    xmlns:xs="http://www.w3.org/2001/XMLSchema"
    xmlns:nx="https://data.nist.gov/od/dm/nexus/experiment/v1.0"
    exclude-result-prefixes="xs"
    version="2.0">    
    
    <xsl:template match="/nx:Experiment">
        <!-- CSS styling which is applied to various elements of the html output --> 
        <style>
            div { /* Set the font for the page */
            font-family: "Lato", sans-serif;
            }
            
            .sidenav { /* Parameters for the sidebar */
            height: 100%;
            width: 160px;
            position: fixed; /* Sets the sidebar to always be visible even when the page is scrolled */
            z-index: 1;
            top: 0;
            left: 0;
            overflow-x: hidden;
            padding-top: 20px;
            background-color: #111;
            }
            
            .sidenav a { /* Parameters for the acquisition activity links within the sidebar */
            padding: 6px 12px 6px 16px;
            text-decoration: none;
            font-size: 18px;
            color: #9b9da0;
            display: block;
            }
            
            .sidenav div { /* Parameters for other text found in the sidebar (e.g. start time( */
            font-size: 13px;
            padding: 1px 6px 5px 20px;
            color: #818181;
            }
            
            .sidenav a:hover { /* Change the color of the links when the mouse is hovered over them */
            color: #f1f1f1;
            }
            
            .main { /* Set parameters for the rest of the page in order to adjust for the sidebar being there */
            margin-left: 160px; /* Same width as the sidebar + left position in px */
            padding: 0px 10px;
            }
            
            @media screen and (max-height: 450px) {
            .sidenav {padding-top: 15px;}
            .sidenav a {font-size: 18px;}
            }
        </style>
        
        <!-- Add sidebar to the page -->
        <div class="sidenav">
            <!-- Include sidebar heading -->
            <h1 style="color:#999a9e;font-size:24px;padding-left:10px;">
                Acquisition Events
            </h1>
            
            <!-- Procedurally generate unique id numbers which relate each acquisition event to its position on
                the webpage such that it will jump there when the link is clicked -->
            <xsl:for-each select="acquisitionActivity">
                <a href="#{generate-id(current())}">
                    Acquisition <xsl:value-of select="@seqno"/>
                </a>
                <!-- Tokenize()[2] splits the date/time using 'T' as the delimiter and takes the 2nd index
                        which corresponds to the time value -->
                <div>Start Time: <xsl:value-of select="tokenize(startTime,'T')[2]"/></div>
                
                <!-- Add a horizontal line to separate sections in the sidebar -->
                <hr></hr>
            </xsl:for-each>
        </div>
        
        <div class="main">
            <!-- Define site title for the page -->
            <title>NIST Microscopy, <xsl:value-of select="title"/></title>
            
            <!-- Create floating button in bottom right which jumps to the top of the page when clicked -->
            <script type="text/javascript" src="../stylesheet-JS.js">//</script>
            <button type="button" value="Top" onclick="toTop()" 
                style="position:fixed;bottom:20px;right:30px;background-color:#e87474;border:none;
                outline:none;color:white;cursor:pointer;padding:15px;border-radius:4px;font-size:15px">
                Top
            </button>
            
            <!-- Display the experiment title and experimenter at the top of the page -->
            <h1>
                <xsl:apply-templates select="title"/>
            </h1>
            <h3>
                <xsl:value-of select="summary/experimenter"/>
            </h3>
            
            <!-- Add a horizontal line separating the title and experimenter -->
            <hr></hr>
            
            <!-- Display the motivation for the experiment -->
            <div style="font-size:16pt;"><b>Motivation</b></div>
            <div style="font-size:14pt"><xsl:value-of select="summary/motivation"/></div>
            
            <!-- Add blank space between sections -->
            <br/><br/>
            
            <!-- Display summary information (date, time, instrument, and id) -->
            <div align="center" style="border-style:none;border-width:2px;padding:6px;">
                <div><b>Instrument: </b>
                    <xsl:value-of select="summary/instrument"/>
                </div>
                <div><b>Date: </b>
                    <!-- Tokenize()[1] splits the date/time using 'T' as the delimiter and takes the 1st index
                        which corresponds to the date value -->
                    <xsl:value-of select="tokenize(summary/reservationStart,'T')[1]"/>
                </div>
                <div><b>Start Time: </b>
                    <!-- Tokenize()[2] splits the date/time using 'T' as the delimiter and takes the 2nd index
                        which corresponds to the time value -->
                    <xsl:value-of select="tokenize(summary/reservationStart,'T')[2]"/> 
                </div>
                <div><b>End Time: </b>
                    <xsl:value-of select="tokenize(summary/reservationEnd,'T')[2]"/>
                </div>
                <!-- Display id associated with the time on the machine -->
                <div><b>id: </b>
                    <xsl:value-of select="id"/>
                </div>
            </div>
            
            <!-- Display information about the sample -->  
            <h3>Sample Information</h3> 
            <table border="2" align="center">
                <tr bgcolor="#0ab226">
                    <th>Sample Name</th>
                    <th>Notes</th>
                    <th>Description</th>
                    <th>Thumbnail</th>
                </tr>
                <!-- Populates the sample information table with informatoin corresponding to the headings -->
                <xsl:apply-templates select="sample"/>
            </table>
            
            <br/> <!-- Add a break for readability -->
            
            <h3>Acquisition Activities</h3>
            <table border="2" align="center" style="width:90%;">
                <tr bgcolor="#f4aa42">
                    <!-- Generate links from the top acquisition activity
                        table to the corresponding activity -->
                    <xsl:for-each select="acquisitionActivity">
                        <th align="center">
                            <!-- Automatically generates a reference id corresponding to each acquisition activity
                                which allows for a link to the specific page location of the activity parameters -->
                            <a href="#{generate-id(current())}">
                                <h3><b>Acquisition <xsl:value-of select="@seqno"/></b></h3>
                            </a> 
                            <h4><b>Start Time:</b></h4>
                            <h4><b><xsl:value-of select="tokenize(startTime,'T')[2]"/></b></h4>
                        </th>
                    </xsl:for-each>
                </tr>
            </table>
            
            <br/>
            <hr></hr> 
            
            <!-- Loop through each acquisition activity -->
            <xsl:for-each select="acquisitionActivity">
                <h2>
                    <!-- Generate name id which corresponds to the link associated with the acquisition activity --> 
                    <a name="{generate-id(current())}">
                        <b>Acquisition Activity <xsl:value-of select="@seqno"/></b>
                    </a>
                </h2>
                <div><b>Start time:</b> <xsl:value-of select="tokenize(startTime,'T')[2]"/></div>
                
                <!-- Generate the table with setup conditions for each acquisition activity -->
                <table border="1" style="border-collapse:collapse;">
                    <tr bgcolor="#84b1f9">
                        <th>Setup</th>
                    </tr>
                    <!-- Loop through each setup value under the 'param' heading -->
                    <xsl:for-each select="setup/param">
                        <xsl:sort select="@name"/>
                        <tr>
                            <!-- Populate setup table with parameter name and value -->
                            <td><b><xsl:value-of select="@name"/></b></td>
                            <td><xsl:value-of select="current()"/></td>
                        </tr>
                    </xsl:for-each>
                </table>            
                
                <!-- Generate metadata table for each image taken for respective acquisition activities -->
                <xsl:for-each select="dataset">
                    <h4><b>
                        <xsl:value-of select="@type"/>: <xsl:value-of select="name"/> 
                    </b></h4>
                    <p>Thumbnail Location: <xsl:value-of select="preview"/></p>
                    <table border="1" style="border-collapse:collapse;">
                        <tr bgcolor="#84b1f9">
                            <th>Parameter</th>
                        </tr>
                        <!-- Loop through each metadata parameter -->
                        <xsl:for-each select="meta">
                            <xsl:sort select="@name"/>
                            <tr>
                                <!-- Populate table values with the metadata name and value -->
                                <td><b><xsl:value-of select="@name"/></b></td>
                                <td><xsl:value-of select="current()"/></td>
                            </tr>
                        </xsl:for-each>                        
                    </table>                
                </xsl:for-each>
                <!-- Add a horizontal line to separate each acquisition activity -->
                <hr></hr>
                <br/>
            </xsl:for-each>
        </div>
    </xsl:template>
    
    <!-- ====== Templates ====== -->
    
    <!-- Template for displaying sample information -->
    <xsl:template match="sample">
        <tr align="center">
            <!-- Fetch values to match the table headings and assign them to corresponding table cells -->
            <td><xsl:value-of select="name"/></td>
            <td><xsl:value-of select="notes"/></td>
            <td><xsl:value-of select="description"/></td>
            <td><xsl:value-of select="notes/entry/imageURL"/></td>
        </tr>
    </xsl:template>  
    
</xsl:stylesheet>