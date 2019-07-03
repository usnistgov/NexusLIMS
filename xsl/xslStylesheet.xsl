<?xml version="1.0" encoding="UTF-8"?>
<xsl:stylesheet xmlns:xsl="http://www.w3.org/1999/XSL/Transform"
    xmlns:xs="http://www.w3.org/2001/XMLSchema"
    xmlns:nx="https://data.nist.gov/od/dm/nexus/experiment/v1.0"
    exclude-result-prefixes="xs"
    version="2.0">    
    
    <xsl:template match="/nx:Experiment">
        
        <!-- ============ CSS Styling ============ --> 
        <style>
            body { /* Set the font for the page */
            font-family: "Lato", sans-serif;
            }
            
            #to_top_button { /* Parameters for the button which jumps to the top of the page */
            display: none; /* Set button to hidden on default so that it will appear when the page is scrolled */
            position: fixed;
            bottom: 20px;
            right: 30px;
            background-color: #e87474;
            border: none;
            outline: none;
            color: white;
            cursor: pointer;
            padding: 15px;
            border-radius: 4px;
            font-size: 15px;
            }
            
            #to_top_button:hover { /* Changes the color of the button when hovered over */
            background-color: #555;
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
            border-style: solid;
            border-width: 2px;
            }
            
            .sidenav a { /* Parameters for the acquisition activity links within the sidebar */
            padding: 6px 12px 6px 16px;
            text-decoration: none;
            font-size: 18px;
            display: block;
            }
            
            .sidenav div { /* Parameters for other text found in the sidebar (e.g. start time( */
            font-size: 13px;
            padding: 1px 6px 5px 20px;
            }
            
            .column {
            float: left;
            width: 50%;
            }
            
            .row:after {
            content: "";
            display: table;
            clear: both;
            }
            
            a:hover { /* Change the links when the mouse is hovered over them */
            cursor: pointer;
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
        
        
        <!-- ============= Main Generation of the Page ============= -->
        <html>
        <!-- Execute showButtonOnScroll() whenever page is scrolled to have the button which jumps back to the top appear -->
        <body onscroll="showButtonOnScroll()">
            
            <!-- Add sidebar to the page -->
            <div class="sidenav">
                <!-- Include sidebar heading -->
                <h1 style="font-size:24px;padding-left:10px;">
                    Navigation
                </h1>
                
                <a href="#{generate-id(experiment/summary)}">Summary</a>
                <hr/>
                
                <!-- Procedurally generate unique id numbers which relate each acquisition event to its position on
                    the webpage such that it will jump there when the link is clicked -->
                <xsl:for-each select="acquisitionActivity">
                    <a href="#{generate-id(current())}">
                        Activity <xsl:value-of select="@seqno+1"/>
                    </a>
                    <div>Mode: <xsl:value-of select="setup/param[@name='Mode']"/></div>
                    
                    <!-- Add a horizontal line to separate sections in the sidebar -->
                    <hr/>
                </xsl:for-each>
            </div>
        
            <div class="main">
                <!-- Define site title for the page -->
                <title>NIST Microscopy, <xsl:value-of select="title"/></title>
                
                <!-- Create floating button in bottom right which jumps to the top of the page when clicked -->
                <script type="text/javascript" src="../stylesheet-JS.js">//</script>
                <button id="to_top_button" type="button" value="Top" onclick="toTop()">
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
                <div style="font-size:16pt;" name="#{generate-id(experiment/summary)}"><b>Motivation</b></div>
                <div style="font-size:14pt"><xsl:value-of select="summary/motivation"/></div>
                
                <!-- Add blank space between sections -->
                <br/><br/>
                
                <!-- Display summary information (date, time, instrument, and id) -->
                <div align="left" style="border-style:none;border-width:2px;padding:6px;">
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
                    <div><b>Session ID: </b>
                        <xsl:value-of select="id"/>
                    </div>
                </div>
                
                <!-- Display information about the sample -->  
                <h3>Sample Information</h3> 
                <table border="3" style="border-collapse:collapse;">
                    <tr>
                        <th>Sample Name</th>
                        <th><xsl:value-of select="sample/name"/></th>
                    </tr>
                    <tr>
                        <th>Notes</th>
                        <th><xsl:value-of select="sample/notes/entry"/></th>
                    </tr>
                    <tr>
                        <th>Description</th>
                        <th><xsl:value-of select="sample/description"/></th>
                    </tr>
                </table>
                
                <br/> <!-- Add a break for readability -->
                <hr></hr> 
                
                <!-- Loop through each acquisition activity -->
                <xsl:for-each select="acquisitionActivity">
                    <div class="row">
                        <h2>
                            <!-- Generate name id which corresponds to the link associated with the acquisition activity --> 
                            <a name="{generate-id(current())}">
                                <b>Acquisition Activity <xsl:value-of select="@seqno+1"/></b>
                            </a>
                            <div style="font-size:19px"><i><xsl:value-of select="setup/param[@name='Mode']"/></i></div>
                            <a href="https:\\nist.gov" target="_blank" style="font-size:14px">(Original Data)</a>
                        </h2>
                        <div><b>Start time:</b> <xsl:value-of select="tokenize(startTime,'T')[2]"/></div>
                        
                        <div class="column">  
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
                        </div>
                        
                        <div class="column">
                            <img src="https://yak-ridge.com/wp-content/uploads/2019/04/image-placeholder-350x350.png"/>
                        </div>
                    </div>
                    
                    <div class="row">
                        <!-- Generate metadata table for each image taken for respective acquisition activities -->
                        <xsl:for-each select="dataset">
                            <h4><b>
                                <xsl:value-of select="@type"/>: <xsl:value-of select="name"/> 
                            </b></h4>
                            
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
                        
                    </div>
                </xsl:for-each>
            </div>
        </body>
        </html>
    </xsl:template>    
</xsl:stylesheet>