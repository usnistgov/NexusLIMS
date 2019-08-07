<xsl:stylesheet xmlns:xsl="http://www.w3.org/1999/XSL/Transform"
    xmlns:xsi="http://www.w3.org/2001/XMLSchema"
    xmlns:nx="https://data.nist.gov/od/dm/nexus/experiment/v1.0"
    version="1.0">
    <xsl:output method="html" indent="yes" encoding="UTF-8"/>
    <xsl:template match="/">
        <xsl:apply-templates select="/nx:Experiment"/>
    </xsl:template>
    <xsl:template match="nx:Experiment">
      <div>        
        <!-- ============ CSS Styling ============ --> 
        <style>
            body { /* Set the font style for the page */
            font-family: "Lato", sans-serif;
            overflow-x: hidden;
            }
                        
            button { 
            cursor: pointer; /* Changes cursor type when hovering over a button */
            }
            
            img {
            max-height: 350px;
            max-width: auto;
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
            border-style: none solid none none;
            border-width: 2px;
            }
            
            .sidenav a { /* Parameters for the acquisition activity links within the sidebar */
            padding: 6px 12px 6px 16px;
            text-decoration: none;
            font-size: 18px;
            display: block;
            }
            
            .sidenav div { /* Parameters for other text found in the sidebar (e.g. start time) */
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
            max-height: 300px;
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
            background-color: rgba(0,0,0,0.8);
            user-select: none;
            }
            
            .next { /*Have the 'next' button appear on the right of the slideshow gallery */
            right: 0;
            border-radius: 3px 0 0 3px;
            }
            
            .prev:hover, .next:hover { /* Have a background appear when the prev/next buttons are hovered over */
            background-color: rgba(145,145,145,0.8);
            }
            
            .text { /* Parameters for the caption text displayed in the image gallery */
            color: #f2f2f2;
            font-size: 15px;
            padding: 8px 12px;
            position: absolute;
            bottom: 8px;
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
                <a class="link" href="#{generate-id(current())}">
                    Activity <xsl:value-of select="@seqno+1"/>
                </a>
                <div>Mode: <xsl:value-of select="setup/param[@name='Mode']"/></div>
                
                <!-- Add a horizontal line to separate sections in the sidebar -->
                <hr/>
            </xsl:for-each>
        </div>
    
        <div class="main">                        
            <!-- Display the experiment title and experimenter at the top of the page -->
            <h1>
                <xsl:value-of select="title"/>
            </h1>
            <h3>
                <xsl:value-of select="summary/experimenter"/>
            </h3>
            
            <!-- Add a horizontal line separating the title and experimenter -->
            <hr></hr>
            
            <!-- Display the motivation for the experiment -->
            <div style="font-size:16pt;" name="#{generate-id(summary)}"><b>Motivation</b></div>
            <div style="font-size:13pt"><xsl:value-of select="summary/motivation"/></div>
            
            <!-- Add blank space between sections -->
            <br/>
            <div class="row">
                <div class="column">
                    <!-- Display summary information (date, time, instrument, and id) -->
                    <div align="left" style="border-style:none;border-width:2px;padding:6px;">
                        <div><b>Instrument: </b>
                            <xsl:value-of select="summary/instrument"/>
                        </div>
                        <div><b>Date: </b>
                            <xsl:call-template name="tokenize-select">
                              <xsl:with-param name="text" select="summary/reservationStart"/>
                              <xsl:with-param name="delim">T</xsl:with-param>
                              <xsl:with-param name="i" select="1"/>
                            </xsl:call-template>
                        </div>
                        <div><b>Start Time: </b>
                            <xsl:call-template name="tokenize-select">
                              <xsl:with-param name="text" select="summary/reservationStart"/>
                              <xsl:with-param name="delim">T</xsl:with-param>
                              <xsl:with-param name="i" select="2"/>
                            </xsl:call-template>
                        </div>
                        <div><b>End Time: </b>
                            <xsl:call-template name="tokenize-select">
                              <xsl:with-param name="text" select="summary/reservationStart"/>
                              <xsl:with-param name="delim">T</xsl:with-param>
                              <xsl:with-param name="i" select="2"/>
                            </xsl:call-template>
                        </div>
                        <!-- Display id associated with the time on the machine -->
                        <div><b>Session ID: </b>
                            <xsl:value-of select="id"/>
                        </div>
                        <a class="link" href="https:\\nist.gov" target="_blank" style="font-size:14px">(Original Data)</a>
                    </div>
                    
                    <!-- Display information about the sample -->  
                    <h3>Sample Information</h3> 
                    <table border="3" style="border-collapse:collapse;width:80%">
                        <tr>
                            <th align="left">Sample Name</th>
                            <th align="left"><xsl:value-of select="sample/name"/></th>
                        </tr>
                        <tr>
                            <th align="left">Sample ID</th>
                            <th align="left"><xsl:value-of select="acquisitionActivity[@seqno=1]/sampleID"/></th>
                        </tr>
                        <tr>
                            <th align="left">Description</th>
                            <th align="left"><xsl:value-of select="sample/description"/></th>
                        </tr>
                    </table>
                </div>
                
                <!-- Image gallery showing images from every dataset of the session -->
                <div class="column">
                    <div class="slideshow-container" id="img_gallery">
                        <div class="slide">
                            <img src="https://www.nanoimages.com/wp-content/uploads/Tin.jpg"/>
                        </div>
                        <div class="slide">
                            <img src="http://www.aerogel.org/wp-content/uploads/2009/03/fenanofoamsem-lanl.jpg"/>
                        </div>
                        
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
                </h2>
                
                <!-- Create accordion which contains acquisition activity setup parameters -->
                <button class="accordion" style="font-weight:bold;font-size:21px">Activity Parameters</button>
                <div class="panel">
                    <div><b>Start time:</b>
                    <xsl:call-template name="tokenize-select">
                      <xsl:with-param name="text" select="summary/reservationStart"/>
                      <xsl:with-param name="delim">T</xsl:with-param>
                      <xsl:with-param name="i" select="2"/>
                    </xsl:call-template></div>

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
                                <img src="https://www.nanoimages.com/wp-content/uploads/Metal_BSE.jpg"/>
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
        
        <!-- Create floating button in bottom right which jumps to the top of the page when clicked -->
        <button id="to_top_button" type="button" value="Top" onclick="toTop()">
            Top
        </button>
        
        <!-- Javascript which supports some capabilities on the generated page -->
        <script language="javascript">                
            
            <xsl:comment><![CDATA[
            //Function which scrolls to the top of the page
            function toTop(){
                document.body.scrollTop = document.documentElement.scrollTop = 0;
            }               

            //Function checks where the page is scrolled to and either shows or hides the button which jumps to the top.
            //If the page is scrolled within 30px of the top, the button is hidden (it is hidden when the page loads).
            window.onscroll = function() {showButtonOnScroll()};
            
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
                document.body.style.overflow = "hidden"
            }

            //Function to close a modal box with id 'name' and re-allow page scrolling
            function closeModal(name){
                document.getElementById(name).style.display = "none";
                document.body.style.overflow = "scroll"
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
            
            //Function to close all open accordions [TODO]
            function closeAccor() {
                
            }
            ]]></xsl:comment>
            
        </script>
      </div>
    </xsl:template>

    <!--
      - split a string by a given delimiter and then select out a given
      - element
      - @param text   the text to split
      - @param delim  the delimiter to split by (default: a single space)
      - @param i      the number of the element in the split array desired,
      -               where 1 is the first element (default: 1)
      -->
    <xsl:template name="tokenize-select">
      <xsl:param name="text"/>
      <xsl:param name="delim" select="' '"/>
      <xsl:param name="i" select="1"/>

      <xsl:choose>
      
        <!-- we want the first element; we can deliver it  -->
        <xsl:when test="$i=1">
          <xsl:choose>
            <xsl:when test="contains($text,$delim)">
              <xsl:value-of select="substring-before($text,$delim)"/>
            </xsl:when>
            <xsl:otherwise>
              <xsl:value-of select="$text"/>
            </xsl:otherwise>
          </xsl:choose>
        </xsl:when>

        <!-- should not happen -->
        <xsl:when test="$i &lt;= 1"/>

        <!-- need an element that's not first one; strip off the first element
             and recurse into this function -->
        <xsl:otherwise>
          <xsl:call-template name="tokenize-select">
            <xsl:with-param name="text">
              <xsl:value-of select="substring-after($text,$delim)"/>
            </xsl:with-param>
            <xsl:with-param name="delim" select="$delim"/>
            <xsl:with-param name="i" select="$i - 1"/>
          </xsl:call-template>
        </xsl:otherwise>
        
      </xsl:choose>
    </xsl:template>
</xsl:stylesheet>