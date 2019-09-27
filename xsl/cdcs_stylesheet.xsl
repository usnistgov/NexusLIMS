<xsl:stylesheet xmlns:xsl="http://www.w3.org/1999/XSL/Transform"
    xmlns:xsi="http://www.w3.org/2001/XMLSchema"
    xmlns:nx="https://data.nist.gov/od/dm/nexus/experiment/v1.0"
    version="1.0">
    <xsl:output method="html" indent="yes" encoding="UTF-8"/>

    <xsl:variable name="datasetBaseUrl">http://***REMOVED***/mmfnexus/</xsl:variable>
    <xsl:variable name="previewBaseUrl">http://***REMOVED***/nexusLIMS/mmfnexus/</xsl:variable>

    <xsl:template match="/">
        <xsl:apply-templates select="/nx:Experiment"/>
    </xsl:template>
    <xsl:template match="nx:Experiment">
      <div>        
        <!-- ============ CSS Styling ============ --> 
        <style>
            .main_body, .sidenav { /* Set the font style for the page */
                font-family: "Lato", sans-serif;
                overflow-x: hidden;
            }

            /* Link colors */
            a:link {
                color: #3865a3;
            }
            a:visited {
                color: #3865a3;
            }
            a:hover {
                color: #5e7ca3;
            }

            button { 
                cursor: pointer; /* Changes cursor type when hovering over a button */
                font-size: 12px;
            }

            /* Override bootstrap button outline styling */
            .btn:focus,.btn:active {
                outline: none !important;
                box-shadow: none;
                background-color: #ccc;
            }
            
            img.nx-img {
                max-width: 100%;
                margin-left: auto; /* Center justify images */
                margin-right: auto;
                display: block;
            }
            
            th,td {
                font-size: 14px;
            }
            
            .aa_header {
                font-size: 19px;
                text-decoration: none;
                color: black;
            }
            
            .aa_header:hover {
                cursor: default;
                color: black;
            }

            /* makes it so link does not get hidden behind the header */
            .aa_header::before { 
                display: block; 
                content: " "; 
                margin-top: -5.5em; 
                height: 4.5em; 
                visibility: hidden; 
                pointer-events: none;
            }
            
            .sidenav { /* Parameters for the sidebar */
                width: 170px;
                position: fixed;
                max-height: 100%;
                z-index: auto;
                overflow-x: hidden;
                overflow-y: scroll;

                /* Hide scrollbars (see https://stackoverflow.com/a/49278385/1435788) */
                overflow-y: scroll;
                scrollbar-width: none; /* Firefox */
                -ms-overflow-style: none;  /* IE 10+ */
            }

            .sidenav {
                visibility: hidden; /* Make hidden, to be revealed when jQuery is done paginating results */    
            }

            .sidenav::-webkit-scrollbar { /* WebKit */
                width: 0px;
            }
            
            /* Parameters for the acquisition activity links and headers within the sidebar */
            .sidenav a, .sidenav th { 
                text-decoration: none;
                font-size: 16px;
                font-weight: bold;
            }

            /* for sidenav table paginator */
            .sidenav .cdatatableDetails {
                float: left;
                margin: 0 1em;
            }

            .sidenav div.dataTables_paginate {
                text-align: center !important;
            }
            
            .sidenav div { /* Parameters for other text found in the sidebar (e.g. start time) */
                font-size: 11px;
            }

            #close-accords-btn, #open-accords-btn {
                margin: 1em auto;
                display: block;
                width: 100%;
            }

            #to-top-btn { /* Parameters for the button which jumps to the top of the page when clicked */
                display: block;
                visibility: hidden; /* Set button to hidden on default so that it will appear when the page is scrolled */
                opacity: 0;
                cursor: pointer;
                margin: 0px auto;
                width: 100%;
                transition: visibility 0.25s linear, opacity 0.25s linear;

                /* Use bootstrap formatting instead */
                <!-- background-color: #3865a3;
                border: none;
                outline: none;
                color: white; 
                padding: 15px 20px;
                border-radius: 3px;
                font-size: 14px; -->
            }
            
            <!-- #to-top-btn:hover { /* Changes the color of the button when hovered over */
                background-color: #5e7ca3;
            } -->
            
            /* Set up 2 divided columns to separate setup parameters and the corresponding image gallery */
            .row {
                display: flex;
            }

            .column {
                flex: 50%;
            }
            
            .slide {
                display: none;
            }
            
            .slideshow-container {
                position: relative;
                margin: auto;
                margin-bottom: 2em;
            }
            
            .gal-prev, .gal-next { /* Parameters for the 'next' and 'prev' buttons on the slideshow gallery */
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
                border-radius: 3px 0px 0px 3px;
                user-select: none;
                background-color: rgba(0,0,0,0.4);
            }
            
            .gal-next { /*Have the 'next' button appear on the right of the slideshow gallery */
                right: 0;
                border-radius: 0px 3px 3px 0px;
            }
            
            .gal-prev:hover, .gal-next:hover { /* Have a background appear when the prev/next buttons are hovered over */
                background-color: rgba(145,145,145,0.8);
                color: white;
            }

            .text { /* Parameters for the caption text displayed in the image gallery */
                color: black;
                font-size: 1em;
                padding: 8px 12px;
                position: absolute;
                bottom: -2em;
                width: 100%;
                text-align: center;
            }

            .aa_header_row {
                /* width: 95%; */
                margin-bottom: .5em;
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
            
            .active-accordian, .accordion:hover { /* Change color of the accordion when it is active or hovered over */
                background-color: #ccc;
            }
            
            .accordion:after { /* Parameters for the accordion header while it is open */
                content: '\002B';
                color: #777;
                font-weight: bold;
                float: right;
                margin-left: 5px;
            }
            
            .active-accordion:after {
                content: '\2212';
            }
            
            .panel { /* Parameters for the contents of the accordion */
                background-color: white;
                max-height: 0;
                overflow: hidden;
                transition: max-height 0.2s ease-out;
                width: 95%;
            }

            img.dataset-preview-img {
                display: block;
                width: 100%;
                height: auto;
                max-height: 400px;
                max-width: 400px;
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
                color: #000;
                float: right;
                font-size: 28px;
                font-weight: bold;
            }
            
            .close:hover, /* Changes color of close button and cursor type when hovering over it */
                .close:focus {
                color: #525252;
                text-decoration: none;
                cursor: pointer;
            }
            
            .main_body { /* Set parameters for the rest of the page in order to adjust for the sidebar being there */
                margin-left: 10em; /* Same width as the sidebar + left position in px */
                padding: 0px 10px;
            }

            .main_body h1 {
                font-size: 1.5em;
            }

            .main_body h3 {
                font-size: 1.1em;
            }

            table.preview-and-table {
                margin: 2em auto;
            }

            table.preview-and-table td {
                vertical-align: middle;
                font-size: 0.9em;
            }

            table.meta-table {
                border-collapse: collapse;
            }

            table.meta-table td, table.meta-table th {
                padding: 0.3em;
            }

            table.meta-table th {
                background-color: #3a65a2;
                border-color: black;
                color: white;
            }

            th.parameter-name {
                font-weight: bold;
            }

            /* Fix for margins getting messed up inside the AA panels */
            .main_body .dataTables_wrapper .row {
                margin: 0;
                display: flex;
                align-items: center;
                margin-top: 0.5em;
            }
            .main_body .dataTables_wrapper .row > * {
                padding: 0;
            }
            .main_body .dataTables_wrapper ul.pagination > li > a {
                padding: 0px 8px;
            }

            .main_body .dataTables_wrapper label {
                font-size: smaller;
            }

            /* For loading screen */
            #loading {
                visibility: visible;
                opacity: 1;
                position: fixed;
                top: 0;
                left: 0;
                z-index: 100;
                width: 100vw;
                height: 100vh;
                background: #f7f7f7 url(static/img/bg01.png);
            }

            #loading img {
                position: absolute;
                top: 50%;
                left: 50%;
                width: 400px;
                margin-top: -200px;
                margin-left: -200px;
                animation: spinner 1.5s ease infinite;
            }

            @keyframes spinner {
            to {transform: rotate(360deg);}
            }
 
            .xslt_render {
                visibility: hidden;
                opacity: 0;
            }

        </style>

        <div id="loading">
            <img src="static/img/logo_bare.png"/>
        </div>

        <!-- ============= Main Generation of the Page ============= -->
        <!-- Add sidebar to the page -->
        <div class="xslt_render">
        <div class="sidenav">
            <table id="nav-table" class="table table-condensed table-hover">
            <!-- Procedurally generate unique id numbers which relate each acquisition event to its position on
                the webpage such that it will jump there when the link is clicked -->
            <thead>
                <tr><th>Record contents:</th></tr>
            </thead>
            <tbody>
            <xsl:for-each select="acquisitionActivity">
                <tr><td>
                <a class="link" href="#{generate-id(current())}">
                    Activity <xsl:value-of select="@seqno+1"/>
                </a>
                <div><xsl:value-of select="setup/param[@name='Mode']"/></div>
                </td></tr>
            </xsl:for-each>
            </tbody>
            </table>

            <button id="open-accords-btn" class="btn btn-default" onclick="openAccords()">
                <i class="fa fa-plus-square-o"></i> Expand All Panels
            </button>
            
            <button id="close-accords-btn" class="btn btn-default" onclick="closeAccords()">
                <i class="fa fa-minus-square-o"></i> Collapse All Panels
            </button>

                    <!-- Create floating button in bottom right which jumps to the top of the page when clicked -->
            <button id="to-top-btn" type="button" class="btn btn-primary" value="Top" onclick="toTop()">
                <i class="fa fa-arrow-up"></i> Scroll to Top
            </button>
        </div>
    
        <div class="main_body">                        
            <!-- Display the experiment title and experimenter at the top of the page -->
            <h1 id="record-title">
                <xsl:value-of select="title"/>
            </h1>
            <h3 id="record-experimenter">
                <xsl:value-of select="summary/experimenter"/>
            </h3>
            
            <div class="row">
                <div class="column" id="session_info_column">
                    <h3 id="res-info-header">Reservation Information:</h3>
                    <!-- Display summary information (date, time, instrument, and id) -->

                    <table class="table table-striped table-hover table-bordered" 
                           style="border-collapse:collapse;width:80%;">
                        <tr>
                            <th align="left" class="parameter-name">Motivation: </th>
                            <td align="left"><xsl:value-of select="summary/motivation"/></td>
                        </tr>
                        <tr>
                            <th align="left" class="parameter-name">Instrument: </th>
                            <td align="left"><xsl:value-of select="summary/instrument"/></td>
                        </tr>
                        <tr>
                            <th align="left" class="parameter-name">Date: </th>
                            <td align="left">
                                <xsl:call-template name="tokenize-select">
                                    <xsl:with-param name="text" select="summary/reservationStart"/>
                                    <xsl:with-param name="delim">T</xsl:with-param>
                                    <xsl:with-param name="i" select="1"/>
                                </xsl:call-template>
                            </td>
                        </tr>
                        <tr>
                            <th align="left" class="parameter-name">Start Time: </th>
                            <td align="left">
                                <xsl:call-template name="tokenize-select">
                                    <xsl:with-param name="text" select="summary/reservationStart"/>
                                    <xsl:with-param name="delim">T</xsl:with-param>
                                    <xsl:with-param name="i" select="2"/>
                                </xsl:call-template>
                            </td>
                        </tr>
                        <tr>
                            <th align="left" class="parameter-name">End Time: </th>
                            <td align="left">
                                <xsl:call-template name="tokenize-select">
                                    <xsl:with-param name="text" select="summary/reservationEnd"/>
                                    <xsl:with-param name="delim">T</xsl:with-param>
                                    <xsl:with-param name="i" select="2"/>
                                </xsl:call-template>
                            </td>
                        </tr>
                        <tr>
                            <th align="left" class="parameter-name">Session ID: </th>
                            <td align="left"><xsl:value-of select="id"/></td>
                        </tr>
                    </table>

                    <!-- Display information about the sample -->  
                    <h3>Sample Information:</h3>

                    <table class="table table-striped table-hover table-bordered" 
                           style="border-collapse:collapse;width:80%;">
                        <tr>
                            <th align="left" class="parameter-name">Sample name: </th>
                            <td align="left"> <xsl:value-of select="sample/name"/></td>
                        </tr>
                        <tr>
                            <th align="left" class="parameter-name">Sample ID: </th>
                            <td align="left"><xsl:value-of select="acquisitionActivity[@seqno=1]/sampleID"/></td>
                        </tr>
                        <tr>
                            <th align="left" class="parameter-name">Description: </th>
                            <td align="left"><xsl:value-of select="sample/description"/></td>
                        </tr>
                    </table>
                </div>
                
                <!-- Image gallery showing images from every dataset of the session -->
                <div class="column">
                    <div class="slideshow-container" id="img_gallery">
                        <xsl:for-each select="//dataset">
                            <div class="slide">
                                <img class="nx-img"><xsl:attribute name="src"><xsl:value-of select="$previewBaseUrl"/><xsl:value-of select="preview"/></xsl:attribute></img>
                                <div class="text"><xsl:value-of select="position()"/> / <xsl:value-of select="count(//dataset)" /></div>
                            </div>
                        </xsl:for-each>
                        <a class="gal-prev" onclick="plusSlide(-1)">&lt;</a>
                        <a class="gal-next" onclick="plusSlide(1)">&gt;</a>
                    </div>
                </div>
            </div>
            <hr/>
            <!-- Loop through each acquisition activity -->
            <xsl:for-each select="acquisitionActivity">
                <div class="container-fluid">
                    <div class="row aa_header_row">
                        <div class="col-md-6">
                            <!-- Generate name id which corresponds to the link associated with the acquisition activity --> 
                            <a name="{generate-id(current())}" class="aa_header">
                                <b>Acquisition Activity <xsl:value-of select="@seqno+1"/></b>
                            </a>
                            <div style="font-size:15px">Activity mode: <i><xsl:value-of select="setup/param[@name='Mode']"/></i></div>
                        </div>
                        <div class="col-md-2 col-md-offset-4" style="margin-right: 4%;">
                            <button id="{generate-id(current())}-btn" class="btn btn-success pull-right"
                                    onclick="toggleAA('{generate-id(current())}-btn')">
                            <i class="fa fa-plus-square-o"></i> Expand Activity</button>
                        </div>
                    </div>
                </div>

                <!-- Create accordion which contains acquisition activity setup parameters -->
                <button class="accordion" style="font-weight:bold;font-size:19px;">Activity Parameters</button>
                <div class="panel">
                    <!-- Generate the table with setup conditions for each acquisition activity -->
                    <table class="table table-condensed table-hover meta-table compact" border="1" style="">
                        <thead>
                        <tr>
                            <th>Setup Parameter</th>
                            <th>Value</th>
                        </tr>
                        </thead>
                        <tbody>
                            <tr>
                            <td><b>Start time</b></td>
                                <td>
                                    <xsl:call-template name="tokenize-select">
                                        <xsl:with-param name="text" select="startTime"/>
                                        <xsl:with-param name="delim">T</xsl:with-param>
                                        <xsl:with-param name="i" select="2"/>
                                    </xsl:call-template>
                                </td>
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
                        </tbody>
                    </table>                        
                </div>
                
                <!-- Generate metadata table for each image dataset taken for respective acquisition activities -->
                <xsl:for-each select="dataset">
                    <!-- Generate unique modal box for each dataset which contains the corresponding image, accessed via a button -->
                    <div id="#{generate-id(current())}" class="modal">
                        <div class="modal-content">
                            <span class="close" onclick="closeModal('#{generate-id(current())}')">X</span>
                            <img class="nx-img"><xsl:attribute name="src"><xsl:value-of select="$previewBaseUrl"/><xsl:value-of select="preview"/></xsl:attribute></img>
                        </div>
                    </div>
                    
                    <!-- Create accordion which contains metadata for each image dataset -->
                    <button class="accordion"><b><xsl:value-of select="@type"/>: <xsl:value-of select="name"/></b></button>
                    <div class="panel">
                        <form><xsl:attribute name="action"><xsl:value-of select="$datasetBaseUrl"/><xsl:value-of select="location"/></xsl:attribute>
                            <button class="btn btn-default" style="display:block; margin: 2em auto;" type="submit">Download original data</button>
                        </form>
                        <table class="preview-and-table">
                        <tr>
                            <td>
                                <a><xsl:attribute name="href"><xsl:value-of select="$previewBaseUrl"/><xsl:value-of select="preview"/></xsl:attribute>
                                    <img width="400" height="400" class="dataset-preview-img"><xsl:attribute name="src"><xsl:value-of select="$previewBaseUrl"/><xsl:value-of select="preview"/></xsl:attribute></img>
                                </a>
                            </td>
                            <xsl:choose>
                                <xsl:when test="meta"> <!-- Checks whether there are parameters and only creates a table if there is -->
                                    <td>
                                        <table class="table table-condensed table-hover meta-table compact" border="1" style="width:100%; border-collapse:collapse;">
                                            <thead>
                                            <tr bgcolor="#3a65a2" color='white'>
                                                <th>Parameter</th>
                                                <th>Value</th>
                                            </tr>
                                            </thead>
                                           <!-- Loop through each metadata parameter -->
                                           <tbody>
                                           <xsl:for-each select="meta">
                                               <xsl:sort select="@name"/>
                                               <tr>
                                                   <!-- Populate table values with the metadata name and value -->
                                                   <td><b><xsl:value-of select="@name"/></b></td>
                                                   <td><xsl:value-of select="current()"/></td>
                                               </tr>
                                           </xsl:for-each>
                                           </tbody>
                                       </table>
                                   </td>
                                </xsl:when>
                                <xsl:otherwise/>
                            </xsl:choose>
                        </tr>
                        </table>
                    </div>
                </xsl:for-each>
                <br/>
            </xsl:for-each>
        </div>
        </div>

        <!-- Javascript which supports some capabilities on the generated page -->
        <script language="javascript">
            <![CDATA[
            //Function which scrolls to the top of the page
            function toTop(){
                document.body.scrollTop = document.documentElement.scrollTop = 0;
            }               

            //Function checks where the page is scrolled to and either shows or hides the button which jumps to the top.
            //If the page is scrolled within 30px of the top, the button is hidden (it is hidden when the page loads).
            window.onscroll = function() {showButtonOnScroll()};
            
            function showButtonOnScroll() {
                var header_pos = $('#record-experimenter').first().position()['top'];
                if (document.body.scrollTop > header_pos || document.documentElement.scrollTop > header_pos) {
                    document.getElementById("to-top-btn").style.visibility = "visible";
                    document.getElementById("to-top-btn").style.opacity = 1;
                } 
                else {
                    document.getElementById("to-top-btn").style.visibility = "hidden";
                    document.getElementById("to-top-btn").style.opacity = 0;
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
                    togglePanel($(this));
                });
            }

            // Function to close an accordion panel
            function closePanel(acc) {
                // acc is a jquery object
                var panel = acc.next();
                acc.removeClass("active-accordion");
                panel.css('maxHeight', 0);
            }

            // Function to open an accordion panel
            function openPanel(acc) {
                // acc is a jquery object
                var panel = acc.next();
                acc.addClass("active-accordion");
                panel.css('maxHeight', panel.prop('scrollHeight') + "px");
            }

            // Function to toggle an accordion panel
            function togglePanel(acc) {
                // acc is a jquery object
                if (acc.hasClass("active-accordion")) {
                    closePanel(acc);
                } else {
                    openPanel(acc);
                }
            }

            //Function to close all open accordions
            function closeAccords() {
                $('button[id*=idm]').each(function(){
                    toggleAA($(this).prop('id'), force_open=false, force_close=true);
                });
            }

            //Function to open all accordions 
            function openAccords() {
               $('button[id*=idm]').each(function(){
                    toggleAA($(this).prop('id'), force_open=true, force_close=false);
                });
            }

            // Function to toggle an aquisition activity section
            function toggleAA(btn_id, force_open=false, force_close=false) {
                // btn_id is like "idm45757030174584-btn"
                
                // strings
                var collapse_str = "<i class='fa fa-minus-square-o'> Collapse Activity</i>"
                var expand_str = "<i class='fa fa-plus-square-o'> Expand Activity</i>"

                // get jquery object
                var btn = $('#' + btn_id);
                
                // determine what to do
                var action_is_expand = btn.text().includes('Expand');

                // get list of accordions to toggle
                var acc = btn.parents().eq(2).nextUntil('.container-fluid').filter('.accordion');
                
                // loop through all accordions, and toggle
                acc.each(function( index ) {
                    var panel = $(this).next();
                    if (action_is_expand || force_open) {   
                        // expand panel
                        openPanel($(this));

                        // change button to collapse
                        btn.html(collapse_str)
                        btn.addClass('btn-danger')
                        btn.removeClass('btn-success')
                    } else if (!(action_is_expand) || force_close) { // collapse
                        closePanel($(this));

                        // change button to expand
                        btn.html(expand_str)
                        btn.addClass('btn-success')
                        btn.removeClass('btn-danger')
                    }
                });
            };
            
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

            /* Prevent buttons from getting focus property when clicking */
            /* https://stackoverflow.com/a/30949767/1435788 */
            $('button').on('mousedown', 
                /** @param {!jQuery.Event} event */ 
                function(event) {
                    event.preventDefault();
                }
            );

            /* Add navigation to sidenav using DataTables */
            $(document).ready(function(){
                var navTable = $('#nav-table').DataTable({
                                destroy: true,
                                pagingType: "simple",
                                info: false,
                                ordering: false,
                                processing: false,
                                searching: false,
                                lengthChange: false,
                                pageLength: 5,
                                language: {
                                            paginate: {
                                                previous: "<i class='fa fa-angle-double-left'></i>",
                                                next: "<i class='fa fa-angle-double-right'></i>"
                                            }
                                        },
                                    "bInfo" : false,
                                    select: 'single',
                                    responsive: true,
                                    altEditor: false,    
                                    drawCallback: function(){
                                        $('.paginate_button.next', this.api().table().container())          
                                            .on('click', function(){
                                            var info = navTable.page.info();
                                                $('.cdatatableDetails').remove();
                                                $('.sidenav .paginate_button.next').before($('<span>',{
                                                'text':' Page '+ (info.page+1) +' of '+info.pages + ' ',
                                                class:'cdatatableDetails'
                                                }));

                                            });    
                                            $('.paginate_button.previous', this.api().table().container())          
                                            .on('click', function(){
                                            var info = navTable.page.info();
                                                $('.cdatatableDetails').remove();
                                                $('.sidenav .paginate_button.next').before($('<span>',{
                                                'text':'Page '+ (info.page+1) +' of '+info.pages,
                                                class:'cdatatableDetails'
                                                }));

                                            }); 
                                    },
                                    ordering: false,
                                    "dom": 'pt'
                                });
                
                var info = navTable.page.info();
                $('.sidenav .paginate_button.next').before($('<span>',{
                    'text':' Page '+ (info.page+1) +' of '+info.pages + ' ' ,
                    class:'cdatatableDetails'
                }));

                // Make acquisition activity metadata tables DataTables
                $('.meta-table').each(function() {
                    $(this).DataTable({
                        destroy: true,
                        pagingType: "simple_numbers",
                        info: false,
                        ordering: false,
                        processing: true,
                        searching: true,
                        lengthChange: false,
                        pageLength: 10,
                        language: {
                            paginate: {
                                previous: "<i class='fa fa-angle-double-left'></i>",
                                next: "<i class='fa fa-angle-double-right'></i>"
                            }
                        },
                        select: 'single',
                        responsive: true,
                        ordering: false,
                        dom: "<'row'<'col-sm-4'f><'col-sm-8'p>>t"
                    });
                });

                // Make visible:
                $('.sidenav').first().css('visibility', 'visible');

                $('#loading').fadeOut('slow');
                
                document.getElementsByClassName('xslt_render')[0].style.visibility = "visible";
                document.getElementsByClassName('xslt_render')[0].style.opacity = 1;
                
            });

            ]]>
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