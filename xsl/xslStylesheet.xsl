<?xml version="1.0" encoding="UTF-8"?>
<xsl:stylesheet xmlns:xsl="http://www.w3.org/1999/XSL/Transform"
    xmlns:xs="http://www.w3.org/2001/XMLSchema"
    xmlns:nx="https://data.nist.gov/od/dm/nexus/experiment/v1.0"
    exclude-result-prefixes="xs"
    version="2.0">    

    <xsl:variable name="datasetBaseUrl">http://***REMOVED***/mmfnexus/</xsl:variable>
    <xsl:variable name="previewBaseUrl">http://***REMOVED***/nexusLIMS/mmfnexus/</xsl:variable>

    <xsl:template match="/nx:Experiment">
        
        <!-- ============ CSS Styling ============ --> 
        <style>
            body { /* Set the font style for the page */
            font-family: "Lato", sans-serif;
            }
                        
            button { 
            cursor: pointer; /* Changes cursor type when hovering over a button */
            }
            
            img {
            max-width: 100%;
            max-height: auto;
            margin-left: auto; /* Center justify images */
            margin-right: auto;
            display: block;
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
            
            /* Set up 2 divided columns to separate setup parameters and the corresponding image gallery */
            .column { 
            float: left;
            width: 50%;
            }
            
            .row:after {
            content: "";
            display: table;
            clear: both;
            }
            
            .slide {
            display: none;
            }
            
            .slideshow-container {
            max-width: 800px;
            position: relative;
            margin: auto;
            }
            
            .prev, .next { /* Parameters for the 'next' and 'prev' buttons on the slideshow gallery */
            cursor: pointer;
            position: absolute;
            top: 50%;
            width: auto;
            padding: 16px;
            margin-top: -22px;
            color: white;
            font-weight: bold;
            font-size: 18px;
            transition: 0.6s ease;
            border-radius: 0 3px 3px 0;
            user-select: none;
            background-color: rgba(0,0,0,0.4);
            }
            
            .next { /*Have the 'next' button appear on the right of the slideshow gallery */
            right: 0;
            border-radius: 3px 0 0 3px;
            }
            
            .prev:hover, .next:hover { /* Have a background appear when the prev/next buttons are hovered over */
            background-color: rgba(0,0,0,0.8);
            }
            
            .text { /* Parameters for the caption text displayed in the image gallery */
            color: black;
            font-size: 15px;
            padding: 8px 12px;
            position: absolute;
            bottom: -1.1em;
            width: 100%;
            text-align: center;
            }
            
            #to_top_button { /* Parameters for the button which jumps to the top of the page when clicked */
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
            
            .accordion { /* Parameters for accordions used to hide parameter / metadata tables */
            background-color: #eee;
            color: #444;
            cursor: pointer;
            padding: 18px;
            width: 95%;
            border: none;
            text-align: left;
            outline: none;
            font-size: 15px;
            transition: 0.4s;
            }
            
            .active, .accordion:hover { /* Change color of the accordion when it is active or hovered over */
            background-color: #ccc;
            }
            
            .accordion:after { /* Parameters for the accordion header while it is open */
            content: '\002B';
            color: #777;
            font-weight: bold;
            float: right;
            margin-left: 5px;
            }
            
            .active:after {
            content: '\2212';
            }
            
            .panel { /* Parameters for the contents of the accordion */
            padding: 0 18px;
            background-color: white;
            max-height: 0;
            overflow: hidden;
            transition: max-height 0.2s ease-out;
            }
            
            .modal { /* Parameters for modal boxes */
            display: none;
            position: fixed;
            z-index: 1;
            padding-top: 100px;
            left: 0;
            top: 0;
            width: 100%;
            height: 100%;
            overflow: auto;
            background-color: rgba(209,203,203,0.7);
            }
            
            .modal-content { /* Parameters for content within modal boxes */
            background-color: #fefefe;
            margin: auto;
            padding: 20px;
            border: 1px solid #888;
            width: 80%;
            }
            
            .close { /* Parameters for 'X' used to close the modal box */
            color: #aaaaaa;
            float: right;
            font-size: 28px;
            font-weight: bold;
            }
            
            .close:hover, /* Changes color of close button and cursor type when hovering over it */
            .close:focus {
            color: #000;
            text-decoration: none;
            cursor: pointer;
            }
            
            .link a:hover { /* Change the links when the mouse is hovered over them */
            cursor: pointer;
            }
            
            .main { /* Set parameters for the rest of the page in order to adjust for the sidebar being there */
            margin-left: 160px; /* Same width as the sidebar + left position in px */
            padding: 0px 10px;
            }
        </style>
        
        <!-- ============= Main Generation of the Page ============= -->
        <html id="html_wrapper">
            
        <!-- Execute showButtonOnScroll() whenever page is scrolled to have the button which jumps back to the top appear -->
        <body onscroll="showButtonOnScroll()">
                    
            <!-- Add sidebar to the page -->
            <div class="sidenav">
                <!-- Include sidebar heading -->
                <h1 style="font-size:24px;padding-left:10px;">
                    Navigation
                </h1>
                
                <a href="#{generate-id(experiment/event)}">Summary</a>
                <hr/>
                
                <!-- Procedurally generate unique id numbers which relate each acquisition event to its position on
                    the webpage such that it will jump there when the link is clicked -->
                <xsl:for-each select="acquisitionActivity">
                    <a class="link" href="#{generate-id(current())}">
                        Activity <xsl:value-of select="@seqno+1"/>
                    </a>
                    <div>Mode: <xsl:value-of select="setup/param[@name='Mode']"/></div>
                    
                    <!-- Add a horizontal line to separate sections in the sidebar -->
                    <hr/>
                </xsl:for-each>
            </div>
        
            <div class="main">
                <!-- Define site title for the page -->
                <title>NIST Microscopy, <xsl:value-of select="event/title"/></title>
                
                <!-- Create floating button in bottom right which jumps to the top of the page when clicked -->
                <button id="to_top_button" type="button" value="Top" onclick="toTop()">
                    Top
                </button>
                
                <!-- Display the experiment title and experimenter at the top of the page -->
                <h1>
                    <xsl:value-of select="event/title"/>
                </h1>
                <h3>
                    <xsl:value-of select="event/user/name"/>
                    <br/>
                    <div style="font-size:16px;"><xsl:value-of select="event/user/email"/></div>
                </h3>
                
                <!-- Add a horizontal line separating the title and experimenter -->
                <hr></hr>
                
                <!-- Display the motivation for the experiment -->
                <div style="font-size:16pt;" name="#{generate-id(event)}"><b>Motivation</b></div>
                <div style="font-size:13pt"><xsl:value-of select="event/purpose"/></div>
                
                <!-- Add blank space between sections -->
                <br/>
                <div class="row">
                    <div class="column">
                        <!-- Display summary information (date, time, instrument, and id) -->
                        <div align="left" style="border-style:none;border-width:2px;padding:6px;">
                            <div><b>Instrument: </b>
                                <xsl:value-of select="event/instrument"/>
                            </div>
                            <div><b>Date: </b>
                                <!-- Tokenize()[1] splits the date/time using 'T' as the delimiter and takes the 1st index
                                    which corresponds to the date value -->
                                <xsl:value-of select="tokenize(event/startTime,'T')[1]"/>
                            </div>
                            <div><b>Start Time: </b>
                                <!-- Tokenize()[2] splits the date/time using 'T' as the delimiter and takes the 2nd index
                                    which corresponds to the time value -->
                                <xsl:value-of select="tokenize(event/startTime,'T')[2]"/> 
                            </div>
                            <div><b>End Time: </b>
                                <xsl:value-of select="tokenize(event/endTime,'T')[2]"/>
                            </div>
                            <!-- Display id associated with the time on the machine -->
                            <div><b>Session ID: </b>
                                <xsl:value-of select="event/eventId"/>
                            </div>
                        </div>
                        
                        <!-- Display information about the sample -->  
                        <h3>Sample Information</h3> 
                        <table border="3" style="border-collapse:collapse;">
                            <tr>
                                <th align="left">Sample Name</th>
                                <th align="left"><xsl:value-of select="event/sampleDetails"/></th>
                            </tr>
                            <tr>
                                <th align="left">Sample ID</th>
                                <th align="left"><xsl:value-of select="acquisitionActivity[@seqno=1]/sampleID"/></th>
                            </tr>
                            <tr>
                                <th align="left">Description</th>
                                <th align="left"><xsl:value-of select="event/description"/></th>
                            </tr>
                        </table>
                    </div>
                    
                    <!-- Image gallery showing images from every dataset of the session -->
                    <div class="column">
                        <div class="slideshow-container" id="img_gallery">
                            <xsl:for-each select="//dataset">
                                <div class="slide">
                                    <img><xsl:attribute name="src"><xsl:value-of select="$previewBaseUrl"/><xsl:value-of select="preview"/></xsl:attribute></img>
                                    <div class="text"><xsl:value-of select="position()"/> / <xsl:value-of select="count(//dataset)" /></div>
                                </div>
                            </xsl:for-each>
                            <a class="prev" onclick="plusSlide(-1)">&lt;</a>
                            <a class="next" onclick="plusSlide(1)">&gt;</a>
                        </div>
                    </div>
                </div>
                
                <br/> <!-- Add a break for readability -->
                
                <!-- Loop through each acquisition activity -->
                <xsl:for-each select="acquisitionActivity">
                    <div></div>
                    <h2>
                        <!-- Generate name id which corresponds to the link associated with the acquisition activity --> 
                        <a name="{generate-id(current())}">
                            <b>Acquisition Activity <xsl:value-of select="@seqno+1"/></b>
                        </a>
                        <div style="font-size:19px"><i><xsl:value-of select="setup/param[@name='Mode']"/></i></div>
                        <a class="link" href="https:\\nist.gov" target="_blank" style="font-size:14px">(Original Data - placeholder)</a>
                    </h2>
                    
                    <!-- Create accordion which contains acquisition activity setup parameters -->
                    <button class="accordion" style="font-weight:bold;font-size:21px">Activity Parameters</button>
                    <div class="panel">
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
                    </div>                    
                    
                    <hr></hr>
                    
                    <div class="row">
                        <!-- Generate metadata table for each image dataset taken for respective acquisition activities -->
                        <xsl:for-each select="dataset">
                            <!-- Generate unique modal box for each dataset which contains the corresponding image, accessed via a button -->
                            <div id="#{generate-id(current())}" class="modal">
                                <div class="modal-content">
                                    <span class="close" onclick="closeModal('#{generate-id(current())}')">X</span>
                                    <img><xsl:attribute name="src"><xsl:value-of select="$previewBaseUrl"/><xsl:value-of select="preview"/></xsl:attribute></img>
                                </div>
                            </div>
                            
                            <!-- Create accordion which contains metadata for each image dataset -->
                            <button class="accordion"><b><xsl:value-of select="@type"/>: <xsl:value-of select="name"/></b></button>
                            <div class="panel">
                                <br/>
                                <!-- TODO: Button which opens a modal box displaying the image for each dataset, respectively -->
                                <button onclick="openModal('#{generate-id(current())}')">View Thumbnail</button>
                                <xsl:if test="meta"> <!-- Checks whether there are parameters and only creates a table if there is -->
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
                                </xsl:if>
                            </div>
                        </xsl:for-each>

                        <br/>
                    </div>
                </xsl:for-each>
            </div>
            
            <!-- Javascript which supports some capabilities on the generated page -->
            <script language="javascript">                
                
                <xsl:comment><![CDATA[
                //Function which scrolls to the top of the page
                function toTop(){
                    document.body.scrollTop = document.documentElement.scrollTop = 0;
                }               

                //Function checks where the page is scrolled to and either shows or hides the button which jumps to the top.
                //If the page is scrolled within 30px of the top, the button is hidden (it is hidden when the page loads).
                function showButtonOnScroll() {
                    if (document.body.scrollTop > 30 || document.documentElement.scrollTop > 30) {
                        document.getElementById("to_top_button").style.display = "block";
                    } 
                    else {
                        document.getElementById("to_top_button").style.display = "none";
                    }
                }

                //Function to open a modal box with id 'name' and prevent scrolling while the box is open
                function openModal(name){
                    document.getElementById(name).style.display = "block";
                    document.getElementById("html_wrapper").style.overflow = "hidden"
                }

                //Function to close a modal box with id 'name' and re-allow page scrolling
                function closeModal(name){
                    document.getElementById(name).style.display = "none";
                    document.getElementById("html_wrapper").style.overflow = "scroll"
                }
                
                //Handler for accordions used to hide parameter and metadata tables
                var acc = document.getElementsByClassName("accordion");
                var i;

                for (i = 0; i < acc.length; i++) {
                    acc[i].addEventListener("click", function() {
                        this.classList.toggle("active");
                        var panel = this.nextElementSibling;
                        if (panel.style.maxHeight){
                            panel.style.maxHeight = null;
                        } else {
                            panel.style.maxHeight = panel.scrollHeight + "px";
                        } 
                    });
                }
                
                //Function to close all open accordions [DEVELOP]
                function closeAccor() {
                    
                }
                
                //Handler for moving through an image gallery
                var slideIndex = 1;
                showSlides(slideIndex);
                
                function plusSlide(n) {
                    showSlides(slideIndex += n);
                }
                
                function currentSlide(n) {
                    showSlides(slideIndex = n);
                }
                
                function showSlides(n) {
                    var i;
                    var slides = document.getElementsByClassName("slide");
                    if (n > slides.length) {slideIndex = 1}    
                    if (n < 1) {slideIndex = slides.length}
                    for (i = 0; i < slides.length; i++) {
                        slides[i].style.display = "none";  
                    }
                    slides[slideIndex-1].style.display = "block";
                }

                //Function which adds a new slide to the overall image gallery for each dataset [WAITING ON THUMBNAILS TO BE ABLE TO TEST]
                function addSlide(source) {
                    var slide = document.createElement("div");
                    slide.class = "slide";                    
                    var image = document.createElement("img");
                    image.src = source;
                    var text = document.createElement("div");
                    text.class = "text"
                    text.innerHTML = source;
                    
                    slide.innerHTML = image + source;
                    
                    document.getElementById("img_gallery").appendChild(slide);
                }
                
                // Key handlers
                document.onkeydown = function(evt) {
                    evt = evt || window.event;
                    var isLeft = false;
                    var isRight = false;
                    var isEscape = false;
                    isLeft = (evt.keyCode === 37);
                    isRight = (evt.keyCode === 39);
                    isEscape = (evt.keyCode === 27);
                    if (isLeft) {
                        plusSlide(-1);
                    }
                    if (isRight) {
                        plusSlide(1);
                    }
                    if (isEscape) {
                        var i;
                        for (i = 0; i < document.getElementsByClassName("modal").length; i++) {
                          closeModal(document.getElementsByClassName("modal")[i].id);
                        }
                    }
                }
                ]]></xsl:comment>
                
            </script>
        </body>
        </html>
    </xsl:template>    
</xsl:stylesheet>