<xsl:stylesheet xmlns:xsl="http://www.w3.org/1999/XSL/Transform"
    xmlns:xsi="http://www.w3.org/2001/XMLSchema"
    xmlns:nx="https://data.nist.gov/od/dm/nexus/experiment/v1.0"
    version="1.0">
    <xsl:output method="html" indent="yes" encoding="UTF-8"/>

    <xsl:variable name="datasetBaseUrl">http://***REMOVED***/mmfnexus/</xsl:variable>
    <xsl:variable name="previewBaseUrl">http://***REMOVED***/nexusLIMS/mmfnexus/</xsl:variable>
    <xsl:variable name="sharepointBaseUrl">https://***REMOVED***/***REMOVED***/Lists/</xsl:variable>

    <xsl:variable name="month-num-dictionary">
        <month month-number="01">January</month>
        <month month-number="02">February</month>
        <month month-number="03">March</month>
        <month month-number="04">April</month>
        <month month-number="05">May</month>
        <month month-number="06">June</month>
        <month month-number="07">July</month>
        <month month-number="08">August</month>
        <month month-number="09">September</month>
        <month month-number="10">October</month>
        <month month-number="11">November</month>
        <month month-number="12">December</month>
    </xsl:variable>
    <xsl:key name="lookup.date.month" match="month" use="@month-number"/>
    
    
    <xsl:variable name="sharepoint-instrument-dictionary">
        <instr display-name="FEI Helios">FEI%20HeliosDB/</instr>
        <instr display-name="FEI Quanta200">FEI%20Quanta200%20Events/</instr>
        <instr display-name="FEI Titan STEM">MMSD%20Titan/</instr>
        <instr display-name="FEI Titan TEM">FEI%20Titan%20Events/</instr>
        <instr display-name="Hitachi S4700">Hitachi%20S4700%20Events/</instr>
        <instr display-name="Hitachi S5500">HitachiS5500/</instr>
        <instr display-name="JEOL JEM3010">JEOL%20JEM3010%20Events/</instr>
        <instr display-name="JEOL JSM7100">JEOL%20JSM7100%20Events/</instr>
        <instr display-name="Philips CM30">Philips%20CM30%20Events/</instr>
        <instr display-name="Philips EM400">Philips%20EM400%20Events/</instr>
    </xsl:variable>
    <xsl:key name="lookup.instrument.url" match="instr" use="@display-name"/>

    <xsl:template match="/">
        <xsl:apply-templates select="/nx:Experiment"/>
    </xsl:template>
    <xsl:template match="nx:Experiment">
        <xsl:variable name="reservation-date-part">
            <xsl:call-template name="tokenize-select">
                <xsl:with-param name="text" select="summary/reservationStart"/>
                <xsl:with-param name="delim">T</xsl:with-param>
                <xsl:with-param name="i" select="1"/>
            </xsl:call-template>
        </xsl:variable>
        <xsl:variable name="firstfile-date-part">
            <xsl:call-template name="tokenize-select">
                <xsl:with-param name="text" select="acquisitionActivity[1]/startTime"/>
                <xsl:with-param name="delim">T</xsl:with-param>
                <xsl:with-param name="i" select="1"/>
            </xsl:call-template>
        </xsl:variable>
        <xsl:variable name="title">
            <xsl:value-of select="title"/>
        </xsl:variable>
        <xsl:variable name="extension-strings">
            <xsl:for-each select="//dataset/location">
                <xsl:call-template name="get-file-extension">
                    <xsl:with-param name="path">
                        <xsl:value-of select="."/>
                    </xsl:with-param>
                </xsl:call-template>
            </xsl:for-each>
        </xsl:variable>
        <xsl:variable name="unique-extensions">
            <xsl:call-template name="dedup-list">
                <xsl:with-param name="input">
                    <xsl:value-of select="$extension-strings"/>
                </xsl:with-param>
            </xsl:call-template>
        </xsl:variable>
      <div style="width:95%;">        
        <!-- ============ CSS Styling ============ --> 
        <style>
            .scrollDisabled { /* class to prevent scrolling when modal is shown */
                position: fixed; 
                overflow-y:scroll;
            }
            
            .main, .sidebar { /* Set the font style for the page */
                /*font-family: "Lato", sans-serif;*/
            }
            
            #nav { /* Make sure top nav does not get overlayed */
                z-index: 100000 !important;
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
            a.aa_anchor { 
                display: block;
                position: relative;
                top: -3.5em;
                visibility: hidden; 
            }
            
            /* Hide for mobile, show later */
            .sidebar {
              display: block;
              position: fixed;
              left: -400px;
              width: 180px;
              font-size: 14px;
              -webkit-transition: all 0.5s ease-in-out 0s;
              -moz-transition: all 0.5s ease-in-out 0s;
              -o-transition: all 0.5s ease-in-out 0s;
              transition: all 0.5s ease-in-out 0s;
              height: 90vh;
            }
            @media (min-width: 768px) {
                .sidebar {
                     position: fixed;
                     top: 5em;
                     bottom: 0;
                     left: 0;
                     z-index: 1000;
                     display: block;
                     padding: 20px;
                     overflow-x: visible;
                     overflow-y: auto; /* Scrollable contents if viewport is shorter than content. */
                     /* border-right: 1px solid #eee; */
                }
            }
            
            .sidebar.side-expanded {
                left: 0;
                padding: 20px;
                background-color: white;
                z-index: 100;
                border: 1px solid #eee;
            }

            .sidebar {
                visibility: hidden; /* Make hidden, to be revealed when jQuery is done paginating results */    
            }

            .sidebar::-webkit-scrollbar { /* WebKit */
                width: 0px;
            }
            
            /* Parameters for the acquisition activity links and headers within the sidebar */
            .sidebar a, .sidebar h1 { 
                text-decoration: none;
                font-weight: bold;
            }

            .sidebar .pagination > li > a, .pagination > li > span {
                padding: 6px 10px;
            }

            /* for sidenav table paginator */
            .sidebar .cdatatableDetails {
                float: left;
                margin: 0 0.5em;
            }

            .sidebar div.dataTables_paginate {
                text-align: center !important;
            }
            
            .sidebar div { /* Parameters for other text found in the sidebar (e.g. start time) */
                font-size: 12px;
            }

            #close-accords-btn, #open-accords-btn, #to-top-btn {
                margin: 0.5em auto;
                display: block;
                width: 100%;
                font-size: 12px;
                z-index: 101;
            }

            #to-top-btn { /* Parameters for the button which jumps to the top of the page when clicked */
                visibility: hidden; /* Set button to hidden on default so that it will appear when the page is scrolled */
                opacity: 0;
                -webkit-transition: visibility 0.25s linear, opacity 0.25s linear;
                -moz-transition: visibility 0.25s linear, opacity 0.25s linear;
                -o-transition: visibility 0.25s linear, opacity 0.25s linear;
                transition: visibility 0.25s linear, opacity 0.25s linear;
            }
     
            .slide {
                display: none;
            }
            
            .slideshow-container {
                position: relative;
                margin: auto;
                margin-bottom: 2em;
            }
          
            img.nx-img {
               max-width: 100%;
               margin-left: auto; /* Center justify images */
               margin-right: auto;
               display: block;
            }
            
            img.nx-img.aa-img {
                
            }
            
            .gal-nav { /* Parameters for the 'next' and 'prev' buttons on the slideshow gallery */

            }
            
            div#img_gallery { /* make entire gallery unselectable to prevent highlighting when clicking nav buttons */
              -webkit-touch-callout: none;
              -webkit-user-select: none;
              -khtml-user-select: none;
              -moz-user-select: none;
              -ms-user-select: none;
              user-select: none;
            }
            
            div#img_gallery .fa-stack-2x{
                color: #aaa;
                -webkit-transition: color 0.25s linear;
                -moz-transition: color 0.25s linear;
                -o-transition: color 0.25s linear;
                transition: color 0.25s linear;
            }
            
            div#img_gallery:hover .fa-stack-2x {
                color: #337ab7;
            }
            
            div#img_gallery .fa-stack:hover .fa-stack-2x {
                color: #23527c;
            }
            
            .gal-prev:hover, .gal-next:hover { /* Have a background appear when the prev/next buttons are hovered over */
            }
            
            .nx-caption .row {
                margin: 0;
            }
            .nx-caption .row > * {
                padding: 0;
            }

            .nx-caption { /* Parameters for the caption text displayed in the image gallery */
                color: black;
                font-size: 14px;
                padding: 8px 12px;
                width: 100%;
                text-align: center;
                margin-top: -1em;
                line-height: 150%;
            }

            .aa_header_row {
                /* width: 95%; */
                margin-bottom: .5em;
                margin-top: -35px;
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
                -webkit-transition: 0.4s;
                -moz-transition: 0.4s;
                -o-transition: 0.4s;
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
                -webkit-transition: max-height 0.2s ease-out; 
                -moz-transition: max-height 0.2s ease-out; 
                -o-transition: max-height 0.2s ease-out;
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
                display: block;
                position: fixed;
                z-index: 1001;
                padding-top: 100px;
                left: 0;
                top: 0;
                width: 100%;
                height: 100%;
                overflow: auto;
                background-color: rgba(209,203,203,0.7);
                -webkit-transition: all 0.25s linear;
                -moz-transition: all 0.25s linear;
                -o-transition: all 0.25s linear;
                transition: all 0.25s linear;
                visibility: hidden;
                opacity: 0;
            }
            
            .modal-content { /* Parameters for content within modal boxes */
                background-color: #fefefe;
                margin: auto;
                padding: 20px;
                border: 1px solid #888;
                width: 80%;
            }
            
            .close-modal { /* Parameters for 'X' used to close the modal box */
                color: #000;
                float: right;
                font-size: 28px;
                font-weight: bold;
            }
            
            .close-modal:hover, /* Changes color of close button and cursor type when hovering over it */
                .close-modal:focus {
                color: #525252;
                text-decoration: none;
                cursor: pointer;
            }
            
            /*
            * Main content
            */
            
            .main {
                padding: 20px;
                -webkit-transition: padding 0.5s ease-in-out 0s;
                -moz-transition: padding 0.5s ease-in-out 0s;
                -o-transition: padding 0.5s ease-in-out 0s;
                transition: padding 0.5s ease-in-out 0s;
                padding-top: 5px;
            }
            @media (min-width: 768px) {
            .main {
                padding-right: 40px;
                padding-left: 220px; /* 180 + 40 */
            }
            }
            .main .page-header {
                margin-top: 0;
                border-bottom: none;`
            }
            

            .main h1 {
                font-size: 1.5em;
            }

            .main h3 {
                font-size: 1.1em;
                margin-bottom: 0.1em;
            }
            
            table#summary-table > tbody > tr > * {
                border: 0;
                padding: 1px;
                line-height: 1.25;
            }

            table.preview-and-table {
                margin: 2em auto;
            }

            table.preview-and-table td {
                vertical-align: middle;
                font-size: 0.9em;
            }

            table.meta-table, 
            table.aa-table {
                border-collapse: collapse;

            }

            table.meta-table td, table.meta-table th, 
            table.aa-table td, table.aa-table th {
                padding: 0.3em;
            }

            table.meta-table th, 
            table.aa-table th {
                background-color: #3a65a2;
                border-color: black;
                color: white;
            }

            th.parameter-name {
                font-weight: bold;
            }

/* Fix for margins getting messed up inside the AA panels */ 
            .main .dataTables_wrapper .row {
                margin: 0;
                /*display: flex;*/
                align-items: center;
                margin-top: 0.5em;
                }
            .main .dataTables_wrapper .row > * {
                padding: 0;
            }
            .main .dataTables_wrapper ul.pagination > li > a {
                padding: 0px 8px;
                }

            .main .dataTables_wrapper label {
                font-size: smaller;
            }
            
            .modal div.dataTables_wrapper div.dataTables_paginate ul.pagination {
                margin-left: 1em;
                white-space: nowrap;
            }
            
            .modal table{
              margin: 0 auto;
              width: 100% !important;
              clear: both;
              border-collapse: collapse;
              table-layout: fixed;
              word-wrap: break-word;
            }

            /* For loading screen */
            #loading {
                visibility: visible;
                opacity: 1;
                position: fixed;
                top: 0;
                left: 0;
                z-index: 500;
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
            
            @media screen and (max-width: 680px) {
            #loading img {
                width: 200px;
                margin-top: -100px;
                margin-left:-100px;
            }
            }

            @keyframes spinner {
            to {transform: rotate(360deg);}
            }
 
            .xslt_render {
                visibility: hidden;
                opacity: 0;
            }
            
            /* Fix spacing between components */
            .main .row {
            }

            .motivation-text, #session_info_column {
                margin-top: -40px;
            }
            @media screen and (max-width: 1680px) {
            .motivation-text, #session_info_column {
                margin-top: -35px;
            }
            }
            @media screen and (max-width: 1280px) {
            .motivation-text, #session_info_column {
            margin-top: -25px;
            }
            }
            @media screen and (max-width: 980px) {
            .motivation-text, #session_info_column {
            margin-top: -20px;
            }
            }
            @media screen and (max-width: 736px) {
            .motivation-text, #session_info_column {
            margin-top: -15px;
            }
            }
            @media screen and (max-width: 480px) {
            .motivation-text, #session_info_column {
            margin-top: -10px;
            margin-right: 50px;
            }
            .experimenter-and-date {
            margin-right: 50px;
            }
            #top-button-div {
            margin-right: 50px;
            }
            }
            .tooltip {
                z-index: 100001;
                position: fixed; 
                -webkit-touch-callout: none;
                -webkit-user-select: none;
                -khtml-user-select: none;
                -moz-user-select: none;
                -ms-user-select: none;
                user-select: none;
                -webkit-transition: opacity 0.25s linear;
                -moz-transition: opacity 0.25s linear;
                -o-transition: opacity 0.25s linear;
                transition: opacity 0.25s linear;
                white-space: pre-wrap;
            }
            .tooltip-inner {
                white-space: pre-wrap;
            }
            .sidebar-btn-tooltip {
                top: 69px !important;
            }
            .sidebar-btn-tooltip .tooltip-arrow{
                top: 50% !important;
            }
            @media screen and (max-width: 768px) {
            #edit-record-btn, #previous-page-btn {
                font-size: 10px;
            }
            }
            #sidebar-btn {
                visibility: hidden;
                opacity: 0;
                position: fixed;
                top: 69px;
                left: 20px;
                font-size: 20px;
                -webkit-transition: opacity 0.5s ease-in-out 0s;
                -moz-transition: opacity 0.5s ease-in-out 0s;
                -o-transition: opacity 0.5s ease-in-out 0s;
                transition: opacity 0.5s ease-in-out 0s;
                z-index: 50;
                }
            @media screen and (max-width: 768px) {
            #sidebar-btn {
                visibility: visible;
                opacity: 1;
            }
            }
            
            .slideshow-col {
                padding: 0;
            }
            
            .badge a {
                color: #fff;
            }
            
            .help-tip {
                color: #eee;
            }
            .help-tip:hover {
                color: #aaa;
            }
            .no-cal-warning {
                color: #a94442;
                font-style: italic;
            }
            .sup-link {
                font-size: 0.5em; 
                top: -1em;
            }
            
            i.param-button {
                margin-left: 0.5em; 
                font-size: medium;
                color: #aaa;
                border: solid 0.1em #eee;
                -webkit-transition: color 0.25s linear, border 0.25s linear, background 0.25s linear;
                -moz-transition: color 0.25s linear, border 0.25s linear, background 0.25s linear;
                -o-transition: color 0.25s linear, border 0.25s linear, background 0.25s linear;
                transition: color 0.25s linear, border 0.25s linear, background 0.25s linear;
            }
            i.param-button:hover {
               margin-left: 0.5em; 
               font-size: medium;
               color: #5e7ca3;
               border: solid 0.1em #999;
               background: #eee;
            }
            
        </style>

        <div id="loading">
            <img src="static/img/logo_bare.png"/>
        </div>

        <!-- ============= Main Generation of the Page ============= -->
        <!-- Add sidebar to the page -->
        <div class="sidebar">
            <table id="nav-table" class="table table-condensed table-hover">
                <!-- Procedurally generate unique id numbers which relate each acquisition event to its position on
                    the webpage such that it will jump there when the link is clicked -->
                <thead>
                    <tr><th>Explore record:</th></tr>
                </thead>
                <tbody>
                <xsl:for-each select="acquisitionActivity">
                    <tr><td>
                    <a class="link" href="#{generate-id(current())}">
                        Activity <xsl:value-of select="@seqno+1"/>
                    </a>
                        <div><xsl:call-template name="parse-instrument-mode"></xsl:call-template></div>
                    </td></tr>
                </xsl:for-each>
                </tbody>
                </table>
    
                <!--
                <button id="open-accords-btn" class="btn btn-default" onclick="openAccords()">
                    <i class="fa fa-plus-square-o"></i> Expand All Panels
                </button>
                
                <button id="close-accords-btn" class="btn btn-default" onclick="closeAccords()">
                    <i class="fa fa-minus-square-o"></i> Collapse All Panels
                </button>-->
    
                <!-- Create button which jumps to the top of the page when clicked -->
                <button id="to-top-btn" type="button" class="btn btn-primary" value="Top" onclick="toTop()">
                    <i class="fa fa-arrow-up"></i> Scroll to Top
                </button>
        </div>
          <div id="sidebar-btn" data-toggle="tooltip" data-placement="right" 
              title="Click to explore record contents">
             <a><i class="fa fa-toggle-right"></i></a>
         </div>
    
          <div class="main col-md-push-2" style="padding: 0;" id="top-button-div">
              <button id="edit-record-btn" type="button" class="btn btn-default pull-right"
                  data-toggle="tooltip" data-placement="top" 
                  title="Manually edit the contents of this record">
                  <i class="fa fa-file-text"></i> Edit this record
              </button>
              <button id="previous-page-btn" type="button" class="btn btn-default pull-right"
                  data-toggle="tooltip" data-placement="top" 
                  title="Go back to the previous page">
                  <i class="fa fa-arrow-left"></i> Back to previous
              </button>
          </div>
    
            <div class="main col-sm-pull-10" id="main-column">                        
                
                <div id='summary-info'>
                    <span class="list-record-title page-header">
                        <i class="fa fa-file-text results-icon"/>
                        <xsl:choose>
                            <xsl:when test="$title = 'No matching calendar event found'">
                                <xsl:text>Untitled experiment</xsl:text>
                                <span class='no-cal-warning'> (No matching calendar event found)</span>
                            </xsl:when>
                            <xsl:otherwise>
                                <xsl:value-of select="$title"/>
                            </xsl:otherwise>
                        </xsl:choose>
                    </span>
                    <br/>
                    <span class="badge list-record-badge yellow-badge">
                        <xsl:choose>
                            <xsl:when test="summary/instrument/text()">
                                <xsl:element name="a">
                                    <xsl:attribute name="href">
                                        <xsl:call-template name="get-calendar-link">
                                            <xsl:with-param name="instrument" select="summary/instrument"></xsl:with-param>
                                        </xsl:call-template></xsl:attribute>
                                    <xsl:attribute name="data-toggle">tooltip</xsl:attribute>
                                    <xsl:attribute name="data-placement">bottom</xsl:attribute> 
                                    <xsl:attribute name="title">Click to view this instrument on the Sharepoint calendar</xsl:attribute>
                                    <xsl:value-of select="summary/instrument"/>
                                </xsl:element>
                            </xsl:when>
                            <xsl:otherwise>
                                Unknown instrument
                            </xsl:otherwise>
                        </xsl:choose>
                        
                    </span>
                    <span class="badge list-record-badge">
                        <xsl:element name="a">
                            <xsl:attribute name="href">
                                <xsl:value-of select="$datasetBaseUrl"/>
                                <xsl:call-template name="get-path-of-file">
                                    <xsl:with-param name="absolute_filename">
                                        <xsl:value-of select="//dataset[1]/location"/>
                                    </xsl:with-param>
                                </xsl:call-template>
                            </xsl:attribute>
                            <xsl:attribute name="data-toggle">tooltip</xsl:attribute>
                            <xsl:attribute name="data-placement">bottom</xsl:attribute> 
                            <xsl:attribute name="title">Click to view file listing of this record in the browser</xsl:attribute>
                            <xsl:value-of select="count(//dataset)"/> data files in <xsl:value-of select="count(//acquisitionActivity)"/> activites 
                        </xsl:element>
                    </span>
                    <i class="fa fa-cubes" style="margin-left:0.75em; font-size: small;"
                       data-toggle="tooltip" data-placement="bottom" title="Filetypes present in record"/><span style="font-size: small;"><xsl:text>: </xsl:text></span>
                    <xsl:call-template name="extensions-to-badges">
                        <xsl:with-param name="input"><xsl:value-of select="$unique-extensions"/></xsl:with-param>
                        <xsl:with-param name="global-count">true</xsl:with-param>
                    </xsl:call-template>
                </div>
                <div class="row">
                        <div class="experimenter-and-date">
                            <span class="list-record-experimenter">
                                <xsl:choose>
                                    <xsl:when test="summary/experimenter">
                                        <xsl:value-of select="summary/experimenter"/>
                                    </xsl:when>
                                    <xsl:otherwise>Unknown experimenter</xsl:otherwise>
                                </xsl:choose>
                            </span>
                            <xsl:text> - </xsl:text>
                            <span class="list-record-date">
                                <i>
                                    <xsl:choose>
                                        <xsl:when test="$reservation-date-part != ''">
                                            <xsl:call-template name="localize-date">
                                                <xsl:with-param name="date">
                                                    <xsl:value-of select="$reservation-date-part"/>
                                                </xsl:with-param>
                                            </xsl:call-template>
                                            <xsl:text> </xsl:text>
                                            <sup class="sup-link"
                                                data-toggle='tooltip' data-placement='right'
                                                title='Click to view associated record on the Sharepoint calendar'>
                                                <xsl:element name="a">
                                                <xsl:attribute name="href">
                                                    <xsl:call-template name="get-calendar-event-link">
                                                        <xsl:with-param name="instrument" select="summary/instrument"></xsl:with-param>
                                                        <xsl:with-param name="event-id" select="id"></xsl:with-param>
                                                    </xsl:call-template>
                                                </xsl:attribute><xsl:text> </xsl:text>
                                                <i class='fa fa-calendar'/>
                                                </xsl:element></sup>
                                        </xsl:when>
                                        <xsl:when test="$firstfile-date-part != ''">
                                            <xsl:call-template name="localize-date">
                                                <xsl:with-param name="date">
                                                    <xsl:value-of select="$firstfile-date-part"/>
                                                </xsl:with-param>
                                            </xsl:call-template>
                                            <span style="font-size:small; font-style:italic;"> (taken from file timestamps)</span>
                                        </xsl:when>
                                        <xsl:otherwise>Unknown date</xsl:otherwise>
                                    </xsl:choose>
                                </i>
                            </span>
                        </div>
                </div>
                <div class="row">
                        <div class="motivation-text">
                            <span style="font-style:italic;">Motivation: </span><xsl:value-of select="summary/motivation"/>
                        </div>
                </div>            
                <div class="row">    
                    <div class="col-md-6" id="session_info_column">
                        <h3 id="res-info-header">Session Summary 
                        <xsl:call-template name="help-tip">
                            <xsl:with-param name="tip-text">Summary information is extracted from the Sharepoint calendar reservation associated with this record</xsl:with-param>
                        </xsl:call-template></h3>
                        <!-- Display summary information (date, time, instrument, and id) -->
    
                        <table class="table table-condensed" id="summary-table" 
                               style="border-collapse:collapse;width:80%;">
                            <tr>
                                <th align="left" class="col-sm-4 parameter-name">Date: </th>
                                <td align="left" class="col-sm-8">
                                    <xsl:call-template name="tokenize-select">
                                        <xsl:with-param name="text" select="summary/reservationStart"/>
                                        <xsl:with-param name="delim">T</xsl:with-param>
                                        <xsl:with-param name="i" select="1"/>
                                    </xsl:call-template>
                                </td>
                            </tr>
                            <tr>
                                <th align="left" class="col-sm-4 parameter-name">Start Time: </th>
                                <td align="left" class="col-sm-8">
                                    <xsl:call-template name="tokenize-select">
                                        <xsl:with-param name="text" select="summary/reservationStart"/>
                                        <xsl:with-param name="delim">T</xsl:with-param>
                                        <xsl:with-param name="i" select="2"/>
                                    </xsl:call-template>
                                </td>
                            </tr>
                            <tr>
                                <th align="left" class="col-sm-4 parameter-name">End Time: </th>
                                <td align="justify" class="col-sm-8">
                                    <xsl:call-template name="tokenize-select">
                                        <xsl:with-param name="text" select="summary/reservationEnd"/>
                                        <xsl:with-param name="delim">T</xsl:with-param>
                                        <xsl:with-param name="i" select="2"/>
                                    </xsl:call-template>
                                </td>
                            </tr>
                            <tr>
                                <th align="left" class="col-sm-4 parameter-name">Session ID:<xsl:text> </xsl:text>
                                    <xsl:call-template name="help-tip">
                                        <xsl:with-param name="tip-placement">right</xsl:with-param>
                                        <xsl:with-param name="tip-text">ID from this instrument's Sharepoint calendar listing</xsl:with-param>
                                    </xsl:call-template></th>
                                <td align="justify" class="col-sm-8"><xsl:value-of select="id"/></td>
                            </tr>
                            <tr>
                                <th align="left" class="col-sm-4 parameter-name">Sample name: </th>
                                <td align="left" class="col-sm-8"> <xsl:value-of select="sample/name"/></td>
                            </tr>
                            <tr>
                                <th align="left" class="col-sm-4 parameter-name">Sample ID:<xsl:text> </xsl:text>
                                    <xsl:call-template name="help-tip">
                                        <xsl:with-param name="tip-placement">right</xsl:with-param>
                                        <xsl:with-param name="tip-text">Automatically generated random ID (for now)</xsl:with-param>
                                    </xsl:call-template></th>
                                <td align="justify" class="col-sm-8"><xsl:value-of select="acquisitionActivity[@seqno=1]/sampleID"/></td>
                            </tr>
                            <xsl:choose>
                                <xsl:when test="sample/description/text()">
                                    <tr>
                                        <th align="left" class="col-sm-6 parameter-name">Description: </th>
                                        <td align="justify"><xsl:value-of select="sample/description"/></td>
                                    </tr>
                                </xsl:when>
                                <xsl:otherwise></xsl:otherwise>
                            </xsl:choose>
                        </table>
                    </div>
                    
                    <!-- Image gallery showing images from every dataset of the session -->
                    <div class="col-md-6 slideshow-col">
                        <div id="img_gallery">
                            <xsl:for-each select="//dataset">
                                <xsl:variable name="aa_num" select="count(../preceding-sibling::acquisitionActivity) + 1"/>
                                <figure class="slide">
                                    <img class="nx-img"><xsl:attribute name="src"><xsl:value-of select="$previewBaseUrl"/><xsl:value-of select="preview"/></xsl:attribute></img>
                                    <figcaption class="nx-caption">
                                        <div class="row">
                                            <div class="col-xs-offset-1 col-xs-1" style="margin-top:0.2em;">
                                            <a  class="gal-nav" onclick="plusSlide(-1); disable_gallery_tooltips();"
                                                data-toggle="tooltip" data-placement="left" 
                                                title="The left/right arrow keys can also be used to navigate the image gallery">
                                                <span class="fa-stack fa-lg">
                                                    <i class="fa fa-circle fa-stack-2x"></i>
                                                    <i class="fa fa-long-arrow-left fa-stack-1x fa-inverse"></i>
                                                </span>
                                            </a></div>
                                            <div class="col-xs-8">
                                            <span>Dataset <xsl:value-of select="position()"/> of <xsl:value-of select="count(//dataset)" /></span>
                                            <br/>
                                            <span style="margin-left:0.9em;">Activity <xsl:value-of select="$aa_num"/> of <xsl:value-of select="count(//acquisitionActivity)"/></span>
                                            <xsl:text> </xsl:text>
                                            <sup>
                                                <a  href="#{generate-id(..)}" 
                                                    data-toggle='tooltip' data-placement='bottom'
                                                    title='Jump to activity {$aa_num} in record'><i class='fa fa-link'/></a>
                                            </sup></div>
                                            <div class='col-xs-1' style="margin-top:0.2em;">
                                                <a  class="gal-nav" onclick="plusSlide(1); disable_gallery_tooltips();"
                                                data-toggle="tooltip" data-placement="right" 
                                                title="The left/right arrow keys can also be used to navigate the image gallery">
                                                <span class="fa-stack fa-lg">
                                                    <i class="fa fa-circle fa-stack-2x"></i>
                                                    <i class="fa fa-long-arrow-right fa-stack-1x fa-inverse"></i>
                                                </span>
                                            </a></div>
                                        </div>
                                    </figcaption>
                                </figure>
                            </xsl:for-each>
                        </div>
                    </div>
                </div>
                <hr/>
                
                <!-- Loop through each acquisition activity -->
                <xsl:for-each select="acquisitionActivity">
                    <div class="row aa_header_row">
                        <div class="col-md-12">
                            <div class="row">
                                <div class="col-md-6">
                                    <!-- Generate name id which corresponds to the link associated with the acquisition activity --> 
                                    <a class="aa_anchor" name="{generate-id(current())}"/>
                                    <span class="aa_header"><b>Experiment activity <xsl:value-of select="@seqno+1"/></b><xsl:text> </xsl:text></span>
                                    
                                    <a href='javascript:void(0)' onclick="$(this).blur(); openModal('{generate-id(current())}-modal')"
                                       data-toggle='tooltip' data-placement='right'
                                       title="Click to view this activity's setup parameters">
                                       <i class='fa fa-tasks fa-border param-button'/>
                                    </a>
                                    <div style="font-size:15px">Instrument mode: 
                                        <i>
                                            <xsl:call-template name="parse-instrument-mode"></xsl:call-template>
                                        </i>
                                    </div>
                                    <span class="badge list-record-badge">
                                        <xsl:value-of select="count(dataset)"/> data files
                                    </span>
                                    <xsl:variable name="this-aa-extension-strings">
                                        <xsl:for-each select="./dataset/location">
                                            <xsl:call-template name="get-file-extension">
                                                <xsl:with-param name="path">
                                                    <xsl:value-of select="."/>
                                                </xsl:with-param>
                                            </xsl:call-template>
                                        </xsl:for-each>
                                    </xsl:variable>
                                    <xsl:variable name="this-aa-unique-extensions">
                                        <xsl:call-template name="dedup-list">
                                            <xsl:with-param name="input">
                                                <xsl:value-of select="$this-aa-extension-strings"/>
                                            </xsl:with-param>
                                        </xsl:call-template>
                                    </xsl:variable>
                                    <i class="fa fa-cubes" style="margin-left:0.75em; font-size: small;"
                                        data-toggle="tooltip" data-placement="bottom" title="Filetypes present in this activity"/><span style="font-size: small;"><xsl:text>: </xsl:text></span>
                                    <xsl:call-template name="extensions-to-badges">
                                        <xsl:with-param name="input"><xsl:value-of select="$this-aa-unique-extensions"/></xsl:with-param>
                                    </xsl:call-template>
                                </div>
                            </div>
                            <div class="row">
                                <!-- preview image column -->
                                <div class="col-xs-4">
                                    <img class="nx-img aa-img"><xsl:attribute name="src"><xsl:value-of select="$previewBaseUrl"/><xsl:value-of select="dataset[1]/preview"/></xsl:attribute></img>
                                </div>
                                
                                <!-- dataset listing column -->
                                <div class="col-xs-8">
                                    <table class="table table-condensed table-hover aa-table compact" border="1" style="width:100%; border-collapse:collapse;">
                                        <thead>
                                            <tr>
                                                <th>
                                                    Dataset Name
                                                    <xsl:call-template name="help-tip">
                                                        <xsl:with-param name="tip-placement">top</xsl:with-param>
                                                        <xsl:with-param name="tip-text">The name given to the dataset (typically the filename)</xsl:with-param>
                                                    </xsl:call-template>
                                                </th>
                                                <th>
                                                    Type
                                                    <xsl:call-template name="help-tip">
                                                        <xsl:with-param name="tip-placement">top</xsl:with-param>
                                                        <xsl:with-param name="tip-text">A label indicating the data type of this dataset (taken from a controlled list)</xsl:with-param>
                                                    </xsl:call-template>
                                                </th>
                                                <th>
                                                    Role
                                                    <xsl:call-template name="help-tip">
                                                        <xsl:with-param name="tip-placement">top</xsl:with-param>
                                                        <xsl:with-param name="tip-text">A label indicating the experimental role of this dataset (taken from a controlled list)</xsl:with-param>
                                                    </xsl:call-template>
                                                </th>
                                                <xsl:choose>
                                                    <xsl:when test="dataset/format">
                                                        <th>
                                                            Format
                                                            <xsl:call-template name="help-tip">
                                                                <xsl:with-param name="tip-placement">top</xsl:with-param>
                                                                <xsl:with-param name="tip-text">A string (can be a MIME type) indicating the format of the dataset (e.g. TIFF, DICOM, Excel)</xsl:with-param>
                                                            </xsl:call-template>
                                                        </th>
                                                    </xsl:when>
                                                </xsl:choose>
                                                <th><!-- metadata link --></th>
                                                <th><!-- download link --></th>
                                            </tr>
                                        </thead>
                                        <!-- Loop through each dataset -->
                                        <tbody>
                                            <xsl:for-each select="dataset">
                                                <tr>
                                                    <!-- Populate table values with the metadata name and value -->
                                                    <td><xsl:value-of select="name"/></td>
                                                    <td><xsl:value-of select="@type"/></td>
                                                    <td><xsl:value-of select="@role"/></td>
                                                    <xsl:choose>
                                                        <xsl:when test="../dataset/format">
                                                            <td><xsl:value-of select="format"/></td>
                                                        </xsl:when>
                                                    </xsl:choose>
                                                    <td>
                                                        <a href='javascript:void(0)' onclick="$(this).blur(); openModal('{generate-id(current())}-modal')"
                                                        data-toggle='tooltip' data-placement='right'
                                                        title="Click to view this dataset's unique metadata">
                                                            <i class='fa fa-tasks fa-border param-button'/>
                                                        </a>
                                                        <div id="{generate-id(current())}-modal" class="modal">
                                                            <div class="modal-content">
                                                                <div class="container-fluid">
                                                                    <div class="row">
                                                                        <div class="col-xs-11">
                                                                            <b><xsl:value-of select="name"/></b><br/>
                                                                            <xsl:choose>
                                                                                <xsl:when test="description/text()">
                                                                                    <div style="font-size:15px">Dataset description: 
                                                                                        <i>
                                                                                            <xsl:value-of select="description"/>
                                                                                        </i>
                                                                                    </div>
                                                                                </xsl:when>
                                                                            </xsl:choose>
                                                                        </div>
                                                                        
                                                                        <div class="col-xs-1">
                                                                            <i class="close-modal fa fa-close" onclick="closeModal('{generate-id(current())}-modal')"/>
                                                                        </div> 
                                                                    </div>
                                                                    <div class="row">
                                                                        <div class='col-xs-12' style="padding-top: 10px;">
                                                                            <!-- Generate the table with setup conditions for each acquisition activity -->
                                                                            <table class="table table-condensed table-hover meta-table compact" border="1" style="">
                                                                                <thead>
                                                                                    <tr>
                                                                                        <th>Metadata Parameter
                                                                                            <xsl:call-template name="help-tip">
                                                                                                <xsl:with-param name="tip-placement">right</xsl:with-param>
                                                                                                <xsl:with-param name="tip-text">The following metadata values are those (within an activity) that are unique to each dataset</xsl:with-param>
                                                                                            </xsl:call-template></th>
                                                                                        <th>Value</th>
                                                                                    </tr>
                                                                                </thead>
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
                                                                        </div>
                                                                    </div>
                                                                </div>
                                                            </div>
                                                        </div>
                                                    </td>
                                                    <td>
                                                        <xsl:element name='a'>
                                                            <xsl:attribute name="href"><xsl:value-of select="$datasetBaseUrl"/><xsl:value-of select="location"/></xsl:attribute>
                                                            <xsl:attribute name="onclick">
                                                                $(this).blur()
                                                            </xsl:attribute>
                                                            <xsl:attribute name="data-toggle">tooltip</xsl:attribute>
                                                            <xsl:attribute name="data-placement">right</xsl:attribute>
                                                            <xsl:attribute name="data-html">true</xsl:attribute>
                                                            <xsl:attribute name="title">Click to download &#013;<xsl:value-of select='name'/></xsl:attribute>
                                                            <i class='fa fa-download fa-border param-button'/>
                                                        </xsl:element>
                                                    </td>
                                                </tr>
                                            </xsl:for-each>
                                        </tbody>
                                    </table>
                                </div>
                            </div>
                        </div>
                        <!-- Generate unique modal box for each AA which contains the setup params, accessed via a button -->
                        <div id="{generate-id(current())}-modal" class="modal">
                            <div class="modal-content">
                                <div class="container-fluid">
                                    <div class="row">
                                        <div class="col-xs-11">
                                            <b>Experiment activity <xsl:value-of select="@seqno+1"/></b><br/>
                                            <div style="font-size:15px">Instrument mode: 
                                                <i>
                                                    <xsl:call-template name="parse-instrument-mode"></xsl:call-template>
                                                </i>
                                            </div>
                                        </div>
                                        
                                        <div class="col-xs-1">
                                            <i class="close-modal fa fa-close" onclick="closeModal('{generate-id(current())}-modal')"/>
                                        </div> 
                                    </div>
                                    <div class="row">
                                        <div class='col-xs-12' style="padding-top: 10px;">
                                            <!-- Generate the table with setup conditions for each acquisition activity -->
                                            <table class="table table-condensed table-hover meta-table compact" border="1" style="">
                                                <thead>
                                                    <tr>
                                                        <th>Setup Parameter
                                                        <xsl:call-template name="help-tip">
                                                            <xsl:with-param name="tip-placement">right</xsl:with-param>
                                                            <xsl:with-param name="tip-text">Setup parameters are defined as those metadata values that are common between all datasets within a given activity</xsl:with-param>
                                                        </xsl:call-template></th>
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
                                    </div>
                                </div>
                            </div>
                        </div>
                    </div>
                    
                    <br/>
                </xsl:for-each>
            </div>

        <!-- Javascript which supports some capabilities on the generated page -->
        <script language="javascript">
            <![CDATA[
            
            // Functions to enable/disable scrolling and add appropriate classes
            var $body = $('body'),
                scrollDisabled = false,
                scrollTop;
                
            function scrollDisable() {
                if (scrollDisabled) {
                    return;
                }
           
                scrollTop = $(window).scrollTop();
           
                $body.addClass('scrollDisabled').css({
                   top: -1 * scrollTop
                });
           
                scrollDisabled = true;
            }

            function scrollEnable() {
                if (!scrollDisabled) {
                    return;
                }
            
                $body.removeClass('scrollDisabled');
                $(window).scrollTop(scrollTop);
            
                scrollDisabled = false;
            }
            
            //Function which scrolls to the top of the page
            function toTop(){
                document.body.scrollTop = document.documentElement.scrollTop = 0;
            }               

            //Function checks where the page is scrolled to and either shows or hides the button which jumps to the top.
            //If the page is scrolled within 30px of the top, the button is hidden (it is hidden when the page loads).
            window.onscroll = function() {showButtonOnScroll()};
            
            function showButtonOnScroll() {
                var header_pos = $('.list-record-experimenter').first().position()['top'];
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
                var modal = document.getElementById(name); 
                modal.style.opacity = 1;
                modal.style.visibility = "visible";
                
                scrollDisable();
                
                window.onclick = function(event) {
                    // console.log(event.target);
                    if (event.target == modal) {
                        closeModal(name);
                    }
                };
            }

            //Function to close a modal box with id 'name' and re-allow page scrolling
            function closeModal(name){
                var modal = document.getElementById(name); 
                modal.style.opacity = 0;
                modal.style.visibility = "hidden";
                
                scrollEnable();                
            }
            
            // Function to get width of scrollbar for padding offset above 
            // (from https://stackoverflow.com/a/13382873/1435788)
            function getScrollbarWidth() {
              // Creating invisible container
              const outer = document.createElement('div');
              outer.style.visibility = 'hidden';
              outer.style.overflow = 'scroll'; // forcing scrollbar to appear
              outer.style.msOverflowStyle = 'scrollbar'; // needed for WinJS apps
              document.body.appendChild(outer);
            
              // Creating inner element and placing it in the container
              const inner = document.createElement('div');
              outer.appendChild(inner);
            
              // Calculating difference between container's full width and the child width
              const scrollbarWidth = (outer.offsetWidth - inner.offsetWidth);
            
              // Removing temporary elements from the DOM
              outer.parentNode.removeChild(outer);
            
              return scrollbarWidth;
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
                var collapse_str = "<i class='fa fa-minus-square-o'></i> Collapse Activity"
                var expand_str = "<i class='fa fa-plus-square-o'></i> Expand Activity"

                // get jquery object
                var btn = $('#' + btn_id);
                
                // determine what to do
                var action_is_expand = btn.text().includes('Expand');
                if ( force_close ) {
                    action_is_expand = false;
                }

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
                if (slides.length === 0) {
                    document.getElementById('img_gallery').remove()
                } else {
                    if (n > slides.length) {slideIndex = 1}    
                    if (n < 1) {slideIndex = slides.length}
                    for (i = 0; i < slides.length; i++) {
                        slides[i].style.display = "none";  
                    }
                    slides[slideIndex-1].style.display = "block";
                }
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
            
            // Function to disable gallery tooltips
            function disable_gallery_tooltips() {
                $('#img_gallery a.gal-nav[data-toggle=tooltip]').tooltip('disable');
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
                                                $('.sidebar .paginate_button.next').before($('<span>',{
                                                'text':' Page '+ (info.page+1) +' of '+info.pages + ' ',
                                                class:'cdatatableDetails'
                                                }));
                                            $('.sidebar .pagination').first().addClass('vertical-align');
                                            });    
                                            $('.paginate_button.previous', this.api().table().container())          
                                            .on('click', function(){
                                            var info = navTable.page.info();
                                                $('.cdatatableDetails').remove();
                                                $('.sidebar .paginate_button.next').before($('<span>',{
                                                'text':'Page '+ (info.page+1) +' of '+info.pages,
                                                class:'cdatatableDetails'
                                                }));
                                                $('.sidebar .pagination').first().addClass('vertical-align');
                                            }); 
                                    },
                                    ordering: false,
                                    "dom": 'pt'
                                });
                
                var info = navTable.page.info();
                $('.sidebar .paginate_button.next').before($('<span>',{
                    'text':' Page '+ (info.page+1) +' of '+info.pages + ' ' ,
                    class:'cdatatableDetails'
                }));
                $('.sidebar .pagination').first().addClass('vertical-align');


                // Make dataset metadata tables DataTables
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
                        dom: "<'row'<'col-sm-4'f><'col-sm-8'p>><'row't>"
                    });
                });
                
//                $('.aa-table').each(function() {
//                    padRows($(this), 5);
//                });
                
                // Make AA filelist tables DataTables
                $('.aa-table').each(function() {
                    $(this).DataTable({
                        destroy: true,
                        pagingType: "simple_numbers",
                        info: false,
                        ordering: false,
                        processing: true,
                        searching: true,
                        lengthChange: false,
                        pageLength: 5,
                        language: {
                            paginate: {
                                previous: "<i class='fa fa-angle-double-left'></i>",
                                next: "<i class='fa fa-angle-double-right'></i>"
                            }
                        },
                        select: 'single',
                        responsive: true,
                        ordering: false,
                        dom: "<'row'<'col-xs-6 pull-right'p>><'row't>",
                    });
                });
                
                // adapted from http://live.datatables.net/patejija/14/edit
                function padRows(obj, targetRows) {
                    var tableRows = obj.find('> tbody > tr'); // grab the existing data rows immediately under this table (so ignoring nested modal tables)
                    var numberNeeded = targetRows - tableRows.length % targetRows; // how many blank rows are needed to fill up to targetRows
                    var lastRow = tableRows.last(); // cache the last data row
                    var lastRowCells = lastRow.children('td'); // how many visible columns are there?
                    var cellString;
                    
                    /* Iterate through the number of blank rows needed, building a string that will
                     * be used for the HTML of each row. Another iterator inside creates the desired
                     * number of columns, adding the sorting class to the appropriate TD.
                     */
                    for (i=0; i < numberNeeded; i++) {
                        cellString = "";
                        for (j=0; j < lastRowCells.length; j++) {
                            cellString += '<td>&nbsp;</td>';
                        }
 
                        // Add the TR and its contents to the DOM
                        lastRow.after('<tr>'+cellString+'</tr>');
                    }
                }

                // Make visible:
                $('.sidebar').first().css('visibility', 'visible');

                $('#loading').fadeOut('slow');
                
                //document.getElementById('xslt_render').style.visibility = "visible";
                //document.getElementById('xslt_render').style.opacity = 1;
                
            });

            ]]>
        </script>
      </div>
    </xsl:template>

    <!--
      - Format a date given in yyyy-mm-dd format to a text-based format
      - e.g. "2019-10-04" becomes "October 4, 2019"
      - @param date   the date to parse
      -->
    <xsl:template name="localize-date">
        <xsl:param name="date"/>
        <xsl:variable name="month-num">
            <xsl:call-template name="tokenize-select">
                <xsl:with-param name="text">
                    <xsl:value-of select="$date"/>
                </xsl:with-param>
                <xsl:with-param name="delim" select="'-'"/>
                <xsl:with-param name="i" select="2"/>
            </xsl:call-template>
        </xsl:variable>
        
        <!-- The 'for-each document' bit is required because keys only work in the context of the current
                 document in XSLT 1.0 (see https://stackoverflow.com/a/35327827/1435788) -->
        <xsl:for-each select="document('')">
            <xsl:value-of select="key('lookup.date.month', $month-num)"/>
        </xsl:for-each>
        <xsl:text> </xsl:text>
        <xsl:call-template name="tokenize-select">
            <xsl:with-param name="text">
                <xsl:value-of select="$date"/>
            </xsl:with-param>
            <xsl:with-param name="delim" select="'-'"/>
            <xsl:with-param name="i" select="3"/>
        </xsl:call-template>
        <xsl:text>, </xsl:text>
        <xsl:call-template name="tokenize-select">
            <xsl:with-param name="text">
                <xsl:value-of select="$date"/>
            </xsl:with-param>
            <xsl:with-param name="delim" select="'-'"/>
            <xsl:with-param name="i" select="1"/>
        </xsl:call-template>
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
    
    <xsl:template name="get-file-extension">
        <xsl:param name="path"/>
        <xsl:choose>
            <xsl:when test="contains($path, '/')">
                <xsl:call-template name="get-file-extension">
                    <xsl:with-param name="path" select="substring-after($path, '/')"/>
                </xsl:call-template>
            </xsl:when>
            <xsl:when test="contains($path, '.')">
                <xsl:call-template name="TEMP">
                    <xsl:with-param name="x" select="substring-after($path, '.')"/>
                </xsl:call-template>
            </xsl:when>
            <xsl:otherwise>
                <xsl:text>No extension</xsl:text>
            </xsl:otherwise>
        </xsl:choose>
    </xsl:template>
    
    <xsl:template name="TEMP">
        <xsl:param name="x"/>
        
        <xsl:choose>
            <xsl:when test="contains($x, '.')">
                <xsl:call-template name="TEMP">
                    <xsl:with-param name="x" select="substring-after($x, '.')"/>
                </xsl:call-template>
            </xsl:when>
            <xsl:otherwise>
                <xsl:element name="ext">
                    <xsl:value-of select="$x"/><xsl:text> </xsl:text>
                </xsl:element>
            </xsl:otherwise>
        </xsl:choose>
    </xsl:template>
    
    <xsl:template name="dedup-list">
        <!-- Cribbed from https://www.oxygenxml.com/archives/xsl-list/200412/msg00888.html -->
        <xsl:param name="input"/>
        <xsl:param name="to-keep"/>
        <xsl:choose>
            <!-- Our string contains a space, so there are more values to process -->
            <xsl:when test="contains($input, ' ')">
                <!-- Value to test is substring-before -->
                <xsl:variable name="firstWord" select="substring-before($input, ' ')"/>
                
                <xsl:choose>
                    <xsl:when test="not(contains($to-keep, $firstWord))">
                        <xsl:variable name="newString">
                            <xsl:choose>
                                <xsl:when test="string-length($to-keep) = 0">
                                    <xsl:value-of select="$firstWord"/>
                                </xsl:when>
                                <xsl:otherwise>
                                    <xsl:value-of select="$to-keep"/>
                                    <xsl:text> </xsl:text>
                                    <xsl:value-of select="$firstWord"/>
                                </xsl:otherwise>
                            </xsl:choose>
                        </xsl:variable>
                        <xsl:call-template name="dedup-list">
                            <xsl:with-param name="input" select="substring-after($input, ' ')"/>
                            <xsl:with-param name="to-keep" select="$newString"/>
                        </xsl:call-template>
                    </xsl:when>
                    <xsl:otherwise>
                        <xsl:call-template name="dedup-list">
                            <xsl:with-param name="input" select="substring-after($input, ' ')"/>
                            <xsl:with-param name="to-keep" select="$to-keep"/>
                        </xsl:call-template>
                    </xsl:otherwise>
                </xsl:choose>
            </xsl:when>
            <xsl:otherwise>
                <xsl:choose>
                    <xsl:when test="string-length($to-keep) = 0">
                        <xsl:value-of select="$input"/>
                    </xsl:when>
                    <xsl:otherwise>
                        <xsl:choose>
                            <xsl:when test="contains($to-keep, $input)">
                                <xsl:value-of select="$to-keep"/>
                            </xsl:when>
                            <xsl:otherwise>
                                <xsl:value-of select="$to-keep"/>
                                <xsl:text> </xsl:text>
                                <xsl:value-of select="$input"/>
                            </xsl:otherwise>
                        </xsl:choose>
                    </xsl:otherwise>
                </xsl:choose>
            </xsl:otherwise>
        </xsl:choose>
    </xsl:template>
    
    <xsl:template name="extensions-to-badges">
        <xsl:param name="input"/>
        <xsl:param name="global-count" select="'false'"/>
        <xsl:choose>
            <!-- Our string contains a space, so there are more values to process -->
            <xsl:when test="contains($input, ' ')">
                <xsl:call-template name="extensions-to-badges">
                    <xsl:with-param name="input" select="substring-before($input, ' ')"></xsl:with-param>
                    <xsl:with-param name="global-count" select="$global-count"/>
                </xsl:call-template>
                <xsl:call-template name="extensions-to-badges">
                    <xsl:with-param name="input" select="substring-after($input, ' ')"></xsl:with-param>
                    <xsl:with-param name="global-count" select="$global-count"/>
                </xsl:call-template>
            </xsl:when>
            <xsl:otherwise>
                <span style="white-space:nowrap;">
                    <xsl:attribute name="data-toggle">tooltip</xsl:attribute>
                    <xsl:attribute name="data-placement">bottom</xsl:attribute>
                    <xsl:choose>
                        <xsl:when test="$input = 'dm3'">
                            <xsl:attribute name="title">Gatan DigitalMicrograph file</xsl:attribute>
                        </xsl:when>
                        <xsl:when test="$input = 'tif'">
                            <xsl:attribute name="title">Tiff-format image</xsl:attribute>
                        </xsl:when>
                        <xsl:when test="$input = 'ser'">
                            <xsl:attribute name="title">FEI .ser file</xsl:attribute>
                        </xsl:when>
                        <xsl:when test="$input = 'emi'">
                            <xsl:attribute name="title">FEI .emi file</xsl:attribute>
                        </xsl:when>
                        <xsl:otherwise>
                            <xsl:attribute name="title">File extension</xsl:attribute>
                        </xsl:otherwise>
                    </xsl:choose>
                    <span class="badge-left badge list-record-badge">
                        <!-- count the number of dataset locations that end with this extension -->
                        <xsl:choose>
                            <xsl:when test="$global-count = 'true'">
                                <xsl:value-of select="count(//dataset/location[$input = substring(., string-length() - string-length($input) + 1)])"/>                                
                            </xsl:when>
                            <xsl:otherwise>
                                <xsl:value-of select="count(dataset/location[$input = substring(., string-length() - string-length($input) + 1)])"/>
                            </xsl:otherwise>
                        </xsl:choose>
                    </span>
                    <span class="badge-right badge list-record-badge">
                        <xsl:value-of select="$input"/>
                    </span>
                </span>
            </xsl:otherwise>
        </xsl:choose>
    </xsl:template>
    
    <xsl:template name="substring-after-last">
        <xsl:param name="string"/>
        <xsl:param name="char"/>
        
        <xsl:choose>
            <xsl:when test="contains($string, $char)">
                <xsl:call-template name="substring-after-last">
                    <xsl:with-param name="string" select="substring-after($string, $char)"/>
                    <xsl:with-param name="char" select="$char"/>
                </xsl:call-template>
            </xsl:when>
            <xsl:otherwise>
                <xsl:value-of select="$string"/>
            </xsl:otherwise>
        </xsl:choose>
    </xsl:template>
    
    <xsl:template name="get-path-of-file">
        <xsl:param name="absolute_filename"/>
        <xsl:variable name="just-filename">
            <xsl:call-template name="substring-after-last">
                <xsl:with-param name="char">/</xsl:with-param>
                <xsl:with-param name="string"><xsl:value-of select="$absolute_filename"/></xsl:with-param>
            </xsl:call-template>
        </xsl:variable>
        
        <xsl:value-of select="substring($absolute_filename, 0, string-length($absolute_filename) - string-length($just-filename))"/>
    </xsl:template>
    
    <xsl:template name="help-tip">
        <xsl:param name="tip-text"/>
        <xsl:param name="tip-placement" select='"right"'></xsl:param>
        <xsl:element name="sup">
            <xsl:attribute name="class">help-tip</xsl:attribute>
            <xsl:attribute name="data-toggle">tooltip</xsl:attribute>
            <xsl:attribute name="data-placement"><xsl:value-of select="$tip-placement"/></xsl:attribute>
            <xsl:attribute name="title"><xsl:value-of select="$tip-text"/></xsl:attribute>
            <i class='fa fa-question-circle'/>
        </xsl:element>
    </xsl:template>
    
    <xsl:template name="get-calendar-link">
        <xsl:param name="instrument"/>
        <xsl:for-each select="document('')">
            <xsl:value-of select="$sharepointBaseUrl"/>
            <xsl:value-of select="key('lookup.instrument.url', $instrument)"/>calendar.aspx</xsl:for-each>
    </xsl:template>
    
    <xsl:template name="get-calendar-event-link">
        <xsl:param name="instrument"/>
        <xsl:param name="event-id"></xsl:param>
        <xsl:for-each select="document('')">
            <xsl:value-of select="$sharepointBaseUrl"/>
            <xsl:value-of select="key('lookup.instrument.url', $instrument)"/>DispForm.aspx?ID=<xsl:value-of select="$event-id"/></xsl:for-each>
    </xsl:template>
    
    <xsl:template name="parse-instrument-mode">
        <xsl:choose>
            <xsl:when test="contains(setup/param[@name='Mode'], 'TEM')">TEM<xsl:text> </xsl:text></xsl:when>
            <xsl:when test="contains(setup/param[@name='Mode'], 'SEM')">SEM<xsl:text> </xsl:text></xsl:when>
            <xsl:otherwise></xsl:otherwise>
        </xsl:choose>
        <xsl:choose>
            <xsl:when test="contains(setup/param[@name='Mode'], 'Diffraction')">Diffraction</xsl:when>
            <xsl:when test="contains(setup/param[@name='Mode'], 'Image')">Imaging</xsl:when>
            <xsl:otherwise><xsl:value-of select="setup/param[@name='Mode']"/></xsl:otherwise>
        </xsl:choose>
    </xsl:template>
    
</xsl:stylesheet>