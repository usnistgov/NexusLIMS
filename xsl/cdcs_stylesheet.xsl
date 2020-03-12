<xsl:stylesheet xmlns:xsl="http://www.w3.org/1999/XSL/Transform"
    xmlns:xsi="http://www.w3.org/2001/XMLSchema"
    xmlns:nx="https://data.nist.gov/od/dm/nexus/experiment/v1.0"
    version="1.0">
    <xsl:output method="html" indent="yes" encoding="UTF-8"/>

    <xsl:variable name="datasetBaseUrl">https://***REMOVED***/mmfnexus/</xsl:variable>
    <xsl:variable name="previewBaseUrl">https://***REMOVED***/nexusLIMS/mmfnexus/</xsl:variable>
    <xsl:variable name="sharepointBaseUrl">https://***REMOVED***/Div/msed/MSED-MMF/Lists/</xsl:variable>

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
    
    <!-- This lookup table assigns a color to each instrument's badge so they can be visually distinguished 
       on the list page -->
    <xsl:variable name="instr-color-dictionary">
        <instr instr-PID="FEI-Titan-TEM-635816">#ff7f0e</instr>
        <instr instr-PID="FEI-Titan-STEM-630901">#2ca02c</instr>
        <instr instr-PID="FEI-Quanta200-ESEM-633137">#d62728</instr>
        <instr instr-PID="JEOL-JEM3010-TEM-565989">#9467bd</instr>
        <instr instr-PID="FEI-Helios-DB-636663">#8c564b</instr>
        <instr instr-PID="Hitachi-S4700-SEM-606559">#e377c2</instr>
        <instr instr-PID="Hitachi-S5500-SEM-635262">#17becf</instr>
        <instr instr-PID="JEOL-JSM7100-SEM-N102656">#bcbd22</instr>
        <instr instr-PID="Philips-EM400-TEM-599910">#bebada</instr>
        <instr instr-PID="Philips-CM30-TEM-540388">#b3de69</instr>
    </xsl:variable>
    <xsl:key name="lookup.instr.color" match="instr" use="@instr-PID"/>
    
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
                    width: 100%;
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
                   max-height: 500px;
                   max-width: 100%;
                   margin-left: auto; /* Center justify images */
                   margin-right: auto;
                   display: block;
                }
                
                img.nx-img.aa-img {
                    display: block;
                    width: 400px;
                }
                
                img.nx-img.aa-img.hidden {
                    display: none;
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
                
                .no-top-padding { /* class to remove padding and margin from bootstrap columns */
                    padding-top: 0 !important;
                    margin-top: 0 !important;
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
                    width: max-content;
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
                
                .modal-expTitle {
                    font-size: smaller;
                    font-weight: normal;
                }
                
                .modal-expDate {
                    font-size: smaller;
                    font-style: oblique;
                }
                
                code {
                    font-family: "Menlo", "DejaVu Sans Mono", "Liberation Mono", "Consolas", "Ubuntu Mono", "Courier New", "andale mono", "lucida console", monospace;
                    font-size: small;
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
                table.aa-table,
                table.filelist-table {
                    border-collapse: collapse;
                
                }
                
                table.meta-table td, table.meta-table th, 
                table.aa-table td, table.aa-table th,
                table.filelist-table td, table.filelist-table th{
                    padding: 0.3em;
                }
                
                table.meta-table th, 
                table.aa-table th,
                table.filelist-table th{
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
                  width: auto;
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
                #edit-record-btn, #btn-previous-page {
                margin: 0.25em;
                }
                @media screen and (max-width: 768px) {
                #edit-record-btn, #btn-previous-page {
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
                
                .warning-tip {
                    color: #f5c636;
                }
                .warning-tip:hover {
                
                }
                
                td.has-warning {
                    color:  #a3a3a3;
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
                
                .row.vertical-align {
                    display: flex;
                    align-items: center;
                    width: 100%;
                }
                
                .dataTables_paginate {
                    font-size: 14px;
                }
                .pager-col {
                    padding-top: 20px;
                }
                .aa-img-col {
                    padding-top: 10px;
                }
                .aa_header_row > .col-md-12 {
                    padding-top: 10px;
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
                            <div><xsl:call-template name="parse-activity-contents"></xsl:call-template></div>
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
                  title="Manually edit the contents of this record (login required)">
                  <i class="fa fa-file-text"></i> Edit this record
              </button>
              <button id="btn-previous-page" type="button" class="btn btn-default pull-right"
                  data-toggle="tooltip" data-placement="top" 
                  title="Go back to the previous page">
                  <i class="fa fa-arrow-left"></i> Back to previous
              </button>
            </div>
            
            <div class="main col-sm-pull-10" id="main-column">                        
                <xsl:variable name="expTitle">
                    <xsl:choose>
                        <xsl:when test="$title = 'No matching calendar event found'">
                            <xsl:text>Untitled experiment</xsl:text>
                            <span class='no-cal-warning'> (No matching calendar event found)</span>
                        </xsl:when>
                        <xsl:otherwise>
                            <xsl:value-of select="$title"/>
                        </xsl:otherwise>
                    </xsl:choose>
                </xsl:variable>
                <div id='summary-info'>
                    <span class="list-record-title page-header">
                        <i class="fa fa-file-text results-icon"/>
                        <xsl:value-of select="$expTitle"/>
                    </span>
                    <br/>
                    <xsl:variable name="instr-pid">
                        <xsl:value-of select="string(summary/instrument/@pid)"/>
                    </xsl:variable>
                    <span class="badge list-record-badge">
                        <xsl:choose>
                            <xsl:when test="summary/instrument/text()">
                                <xsl:attribute name="style">background-color:<xsl:for-each select="document('')">
                                    <xsl:value-of select="key('lookup.instr.color', $instr-pid)"/>
                                </xsl:for-each> !important;</xsl:attribute>
                                <xsl:element name="a">
                                    <xsl:attribute name="target">_blank</xsl:attribute>
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
                                javascript:void(0);
                            </xsl:attribute>
                            <xsl:attribute name="onclick">
                                openModal('filelist-modal');
                            </xsl:attribute>
                            <xsl:attribute name="data-toggle">tooltip</xsl:attribute>
                            <xsl:attribute name="data-placement">bottom</xsl:attribute> 
                            <xsl:attribute name="title">Click to view a file listing of this record</xsl:attribute>
                            <xsl:value-of select="count(//dataset)"/> data file<xsl:if test="count(//dataset)>1">s</xsl:if> in <xsl:value-of select="count(//acquisitionActivity)"/> activit<xsl:choose>
                                <xsl:when test="count(//acquisitionActivity) = 1">y</xsl:when>
                                <xsl:otherwise>ies</xsl:otherwise>
                            </xsl:choose>
                        </xsl:element>
                    </span>
                    <i class="fa fa-cubes" style="margin-left:0.75em; font-size: small;"
                       data-toggle="tooltip" data-placement="bottom" title="Filetypes present in record"/><span style="font-size: small;"><xsl:text>: </xsl:text></span>
                    <xsl:call-template name="extensions-to-badges">
                        <xsl:with-param name="input"><xsl:value-of select="$unique-extensions"/></xsl:with-param>
                        <xsl:with-param name="global-count">true</xsl:with-param>
                    </xsl:call-template>
                </div>
                <xsl:variable name="date">
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
                                    <xsl:attribute name="target">_blank</xsl:attribute>
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
                </xsl:variable>
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
                            <span class="list-record-date"><i><xsl:value-of select="$date"/></i></span>
                        </div>
                </div>
                <div class="row">
                        <div class="motivation-text">
                           
                                <xsl:choose>
                                    <xsl:when test="summary/motivation/text()">
                                        <span style="font-style:italic;">Motivation: </span><xsl:value-of select="summary/motivation"/>
                                    </xsl:when>
                                    <xsl:otherwise>
                                        No motivation provided
                                        <xsl:call-template name="help-tip">
                                            <xsl:with-param name="tip-placement">right</xsl:with-param>
                                            <xsl:with-param name="tip-text">This value is pulled from the "Experiment Purpose" field of a Sharepoint calendar reservation</xsl:with-param>
                                        </xsl:call-template>
                                    </xsl:otherwise>
                                </xsl:choose>
                            
                        </div>
                </div>            
                <div class="row">    
                    <div class="col-md-6 no-top-padding" id="session_info_column">
                        <span style='line-height: 0.5em;'><br/></span>
                        <h3 id="res-info-header">Session Summary 
                        <xsl:call-template name="help-tip">
                            <xsl:with-param name="tip-text">Summary information is extracted from the Sharepoint calendar reservation associated with this record</xsl:with-param>
                        </xsl:call-template></h3>
                        <!-- Display summary information (date, time, instrument, and id) -->
    
                        <table class="table table-condensed" id="summary-table" 
                               style="border-collapse:collapse;width:80%;">
                            <xsl:if test="summary/reservationStart/text()">
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
                            </xsl:if>
                            <xsl:if test="summary/reservationEnd/text()">
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
                            </xsl:if>
                            <xsl:if test="summary/collaborator">
                                <tr>
                                    <th align="left" class="col-sm-4 parameter-name">Collaborator<xsl:if test="count(summary/collaborator) > 1">s</xsl:if>: </th>
                                    <td align="left" class="col-sm-8">
                                        <xsl:for-each select="summary/collaborator">
                                            <xsl:if test="position() > 1"><br/></xsl:if>
                                            <xsl:value-of select="."/>
                                        </xsl:for-each>
                                    </td>
                                </tr>
                            </xsl:if>
                            <xsl:if test="id/text()">
                                <tr>
                                    <th align="left" class="col-sm-4 parameter-name">Session ID:<xsl:text> </xsl:text>
                                        <xsl:call-template name="help-tip">
                                            <xsl:with-param name="tip-placement">right</xsl:with-param>
                                            <xsl:with-param name="tip-text">ID from this instrument's Sharepoint calendar listing</xsl:with-param>
                                        </xsl:call-template></th>
                                    <td align="justify" class="col-sm-8"><xsl:value-of select="id"/></td>
                                </tr>
                            </xsl:if>
                            <xsl:if test="sample/name/text()">
                                <tr>
                                    <th align="left" class="col-sm-4 parameter-name">Sample name: </th>
                                    <td align="left" class="col-sm-8"> <xsl:value-of select="sample/name"/></td>
                                </tr>    
                            </xsl:if>
                            <xsl:if test="acquisitionActivity[@seqno=0]/sampleID/text()">
                                <tr>
                                    <th align="left" class="col-sm-4 parameter-name">Sample ID:<xsl:text> </xsl:text>
                                        <xsl:call-template name="help-tip">
                                            <xsl:with-param name="tip-placement">right</xsl:with-param>
                                            <xsl:with-param name="tip-text">Automatically generated random ID (for now)</xsl:with-param>
                                        </xsl:call-template></th>
                                    <td align="justify" class="col-sm-8"><xsl:value-of select="acquisitionActivity[@seqno=0]/sampleID"/></td>
                                </tr>
                            </xsl:if>
                            <xsl:variable name="description-stripped">
                                <xsl:call-template name='strip-tags'>
                                    <xsl:with-param name="text" select="sample/description"/>
                                </xsl:call-template>
                            </xsl:variable>
                            <xsl:if test="string-length($description-stripped) > 0">
                                <tr>
                                    <th align="left" class="col-sm-6 parameter-name">Description: </th>
                                    <td align="justify"><xsl:value-of select="$description-stripped"/></td>
                                </tr>
                            </xsl:if>
                        </table>
                        
                        <xsl:if test="project/*/text()">
                          <h3 id="res-info-header">Project Information 
                              <xsl:call-template name="help-tip">
                                  <xsl:with-param name="tip-text">Project information is extracted from the user's division and group, as well as the Sharepoint calendar reservation associated with this record</xsl:with-param>
                              </xsl:call-template>
                              <xsl:if test="project/ref/text()">
                                  <xsl:text> </xsl:text>
                                  <sup>
                                      <xsl:element name="a">
                                          <xsl:attribute name="href"><xsl:value-of select="project/ref"/></xsl:attribute>    
                                          <xsl:attribute name="data-toggle">tooltip</xsl:attribute>
                                          <xsl:attribute name="data-placement">top</xsl:attribute>
                                          <xsl:attribute name="title">Link to this project's reference</xsl:attribute>
                                          <i class='fa fa-link'/>
                                      </xsl:element>
                                  </sup>
                              </xsl:if>
                          </h3>
                          
                          <table class="table table-condensed" id="summary-table" 
                              style="border-collapse:collapse;width:80%;">
                              <xsl:if test="project/name/text()">
                                  <tr>
                                      <th align="left" class="col-sm-4 parameter-name">Name: </th>
                                      <td align="left" class="col-sm-8">
                                          <xsl:value-of select="project/name/text()"/>
                                      </td>
                                  </tr>
                              </xsl:if>
                              <xsl:if test="project/project_id/text()">
                                  <tr>
                                      <th align="left" class="col-sm-4 parameter-name">ID: </th>
                                      <td align="left" class="col-sm-8">
                                          <xsl:value-of select="project/project_id/text()"/>
                                      </td>
                                  </tr>
                              </xsl:if>
                              <xsl:if test="project/division/text()">
                                  <tr>
                                      <th align="left" class="col-sm-4 parameter-name">Division: </th>
                                      <td align="left" class="col-sm-8">
                                          <xsl:value-of select="project/division/text()"/>
                                      </td>
                                  </tr>
                              </xsl:if>
                              <xsl:if test="project/group/text()">
                                  <tr>
                                      <th align="left" class="col-sm-4 parameter-name">Group: </th>
                                      <td align="left" class="col-sm-8">
                                          <xsl:value-of select="project/group/text()"/>
                                      </td>
                                  </tr>
                              </xsl:if>
                          </table>
                        </xsl:if>
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
                                <xsl:if test="@seqno = 0">
                                    <xsl:attribute name="style">margin-top: -20px;</xsl:attribute>
                                </xsl:if>
                                <div class="col-md-6">
                                    <!-- Generate name id which corresponds to the link associated with the acquisition activity --> 
                                    <a class="aa_anchor" name="{generate-id(current())}"/>
                                    <span class="aa_header"><b>Experiment activity <xsl:value-of select="@seqno+1"/></b><xsl:text> </xsl:text></span>
                                    
                                    <a href='javascript:void(0)' onclick="$(this).blur(); openModal('{generate-id(current())}-modal');"
                                       data-toggle='tooltip' data-placement='right'
                                       title="Click to view this activity's setup parameters">
                                       <i class='fa fa-tasks fa-border param-button'/>
                                    </a>
                                    <div style="font-size:15px">Activity contents: 
                                        <i>
                                            <xsl:call-template name="parse-activity-contents"></xsl:call-template>
                                        </i>
                                    </div>
                                    <span class="badge list-record-badge">
                                        <xsl:value-of select="count(dataset)"/> data file<xsl:if test="count(dataset) > 1">s</xsl:if>
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
                            <div class="row aa-content-row">
                                <!-- preview image column -->
                                <div class="col-lg-5 aa-img-col">
                                    <!-- likely better to load and hide each image first rather than change img src dynamically -->
                                    <xsl:for-each select="dataset[1]">
                                        <img class="nx-img aa-img visible" id="{generate-id()}-aa-img"><xsl:attribute name="src"><xsl:value-of select="$previewBaseUrl"/><xsl:value-of select="preview"/></xsl:attribute></img>        
                                    </xsl:for-each>
                                    <xsl:for-each select="dataset[position() > 1]">
                                        <img class="nx-img aa-img hidden" id="{generate-id()}-aa-img"><xsl:attribute name="src"><xsl:value-of select="$previewBaseUrl"/><xsl:value-of select="preview"/></xsl:attribute></img>
                                    </xsl:for-each>                                    
                                </div>
                                
                                <!-- dataset listing column -->
                                <div class="col-lg-7 aa-table-col">
                                    <table class="table table-condensed table-hover aa-table compact wrap" border="1" style="width:100%; border-collapse:collapse;">
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
                                                    Creation Time
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
                                                    <xsl:when test="dataset/format/text()">
                                                        <th>
                                                            Format
                                                            <xsl:call-template name="help-tip">
                                                                <xsl:with-param name="tip-placement">top</xsl:with-param>
                                                                <xsl:with-param name="tip-text">A string (can be a MIME type) indicating the format of the dataset (e.g. TIFF, DICOM, Excel)</xsl:with-param>
                                                            </xsl:call-template>
                                                        </th>
                                                    </xsl:when>
                                                </xsl:choose>
                                                <th class='text-center' style='padding-right: 1%'>Meta</th>
                                                <th class='text-center' style='padding-right: 1%'>D/L</th>
                                            </tr>
                                        </thead>
                                        <!-- Loop through each dataset -->
                                        <tbody>
                                            <xsl:for-each select="dataset">
                                                <tr img-id="{generate-id()}-aa-img">
                                                    <!-- Populate table values with the metadata name and value -->
                                                    <!-- generate a dataset id that matches preview image as an attribute on the first column for accessing later via JS -->
                                                    <xsl:element name="td">
                                                        <xsl:value-of select="name"/>
                                                    </xsl:element>
                                                    <xsl:element name="td">
                                                        <xsl:choose>
                                                            <xsl:when test="meta[@name = 'Creation Time']">
                                                                <xsl:value-of select="string(meta[@name = 'Creation Time'])"/>
                                                            </xsl:when>
                                                            <xsl:when test="../setup/param[@name = 'Creation Time']">
                                                                <xsl:value-of select="string(../setup/param[@name = 'Creation Time'])"/>
                                                            </xsl:when>
                                                            <xsl:otherwise>---</xsl:otherwise>
                                                        </xsl:choose>
                                                    </xsl:element>
                                                    <xsl:variable name="dataset-type">
                                                        <xsl:choose>
                                                            <xsl:when test="string(@type) = 'SpectrumImage'">Spectrum Image</xsl:when>
                                                            <xsl:otherwise><xsl:value-of select="@type"/></xsl:otherwise>
                                                        </xsl:choose>
                                                    </xsl:variable>
                                                    <td><xsl:value-of select="$dataset-type"/></td>
                                                    <td><xsl:value-of select="@role"/></td>
                                                    <xsl:choose>
                                                        <xsl:when test="../dataset/format/text()">
                                                            <td><xsl:value-of select="format/text()"/></td>
                                                        </xsl:when>
                                                    </xsl:choose>
                                                    <td class='text-center'>
                                                        <!-- Modal content inside of table, since it needs to be in the context of this dataset -->
                                                        <a href='javascript:void(0)' onclick="$(this).blur(); openModal('{generate-id(current())}-modal');"
                                                        data-toggle='tooltip' data-placement='left'
                                                        title="Click to view this dataset's unique metadata">
                                                            <i class='fa fa-tasks fa-border param-button' style='margin-left:0;'/>
                                                        </a>
                                                        <xsl:variable name="json-tmp"><xsl:value-of select="$previewBaseUrl"/><xsl:value-of select="preview"/></xsl:variable>
                                                        <xsl:variable name="json-location"><xsl:value-of select="substring-before($json-tmp, '.thumb.png')"/>.json</xsl:variable>
                                                        <xsl:element name='a'>
                                                            <xsl:attribute name="href"><xsl:value-of select="$json-location"/></xsl:attribute>
                                                            <xsl:attribute name="onclick">
                                                                $(this).blur()
                                                            </xsl:attribute>
                                                            <xsl:attribute name="target">_blank</xsl:attribute>
                                                            <xsl:attribute name="data-toggle">tooltip</xsl:attribute>
                                                            <xsl:attribute name="data-placement">right</xsl:attribute>
                                                            <xsl:attribute name="data-html">true</xsl:attribute>
                                                            <xsl:attribute name="title">Click to download this dataset's metadata in JSON format</xsl:attribute>
                                                            <i class='fa fa-download fa-border param-button' style='margin-left:0;'/>
                                                        </xsl:element>
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
                                                                            <table class="table table-condensed table-hover meta-table compact text-left" border="1" style="">
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
                                                                                            <td><b><xsl:value-of select="@name"/></b>
                                                                                            <!-- If this parameter has a warning attribute, then add warning tooltip -->
                                                                                            <xsl:if test="@warning = 'true'"><xsl:text> </xsl:text>
                                                                                                <xsl:call-template name="warning-tip">
                                                                                                    <xsl:with-param name="tip-placement">right</xsl:with-param>
                                                                                                    <xsl:with-param name="tip-text">This parameter is known to be unreliable, so use its value with caution</xsl:with-param>
                                                                                                </xsl:call-template>
                                                                                            </xsl:if>
                                                                                            </td>
                                                                                            <td>
                                                                                                <xsl:attribute name="class">
                                                                                                    <xsl:if test="@warning = 'true'">has-warning</xsl:if>
                                                                                                </xsl:attribute>
                                                                                                <!-- If metadata tag is "Data Type", then replace '_' with ' ' -->
                                                                                                <xsl:choose>
                                                                                                    <xsl:when test="@name = 'Data Type'">
                                                                                                        <xsl:call-template name="string-replace-all">
                                                                                                            <xsl:with-param name="text"><xsl:value-of select="current()"/></xsl:with-param>
                                                                                                            <xsl:with-param name="replace" select="'_'" />
                                                                                                            <xsl:with-param name="by" select="' '" />
                                                                                                        </xsl:call-template>
                                                                                                    </xsl:when>
                                                                                                    <xsl:otherwise>
                                                                                                        <xsl:value-of select="current()"/>
                                                                                                    </xsl:otherwise>
                                                                                                </xsl:choose>
                                                                                            </td>
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
                                                    <td class='text-center'>
                                                        <xsl:element name='a'>
                                                            <xsl:attribute name="href"><xsl:value-of select="$datasetBaseUrl"/><xsl:value-of select="location"/></xsl:attribute>
                                                            <xsl:attribute name="onclick">
                                                                $(this).blur()
                                                            </xsl:attribute>
                                                            <xsl:attribute name="data-toggle">tooltip</xsl:attribute>
                                                            <xsl:attribute name="data-placement">right</xsl:attribute>
                                                            <xsl:attribute name="data-html">true</xsl:attribute>
                                                            <xsl:attribute name="title">Click to download &#013;<xsl:value-of select='name'/></xsl:attribute>
                                                            <i class='fa fa-download fa-border param-button' style='margin-left:0;'/>
                                                        </xsl:element>
                                                    </td>
                                                </tr>
                                            </xsl:for-each>
                                        </tbody>
                                    </table>
                                </div>
                            </div>
                            <div class='row dt_paginate_container vertical-align'>
                                <!-- this row exists just to hold the pagination controls for the table above, moved here via JS -->
                            </div>
                        </div>
                        <!-- Generate unique modal box for each AA which contains the setup params, accessed via a button -->
                        <div id="{generate-id(current())}-modal" class="modal">
                            <div class="modal-content">
                                <div class="container-fluid">
                                    <div class="row">
                                        <div class="col-med-11">
                                            <b>Experiment activity <xsl:value-of select="@seqno+1"/></b><br/>
                                        </div>
                                        
                                        <div class="col-med-1 pull-right">
                                            <i class="close-modal fa fa-close" onclick="closeModal('{generate-id(current())}-modal')"/>
                                        </div> 
                                    </div>
                                    <div class="row">
                                        <div class='col-xs-12' style='padding-top: 0.25em;'>
                                            <div style="font-size:15px">Activity contents: 
                                                <i>
                                                    <xsl:call-template name="parse-activity-contents"></xsl:call-template>
                                                </i>
                                            </div>
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
                                                            <td><b><xsl:value-of select="@name"/></b>
                                                            <xsl:if test="@warning = 'true'"><xsl:text> </xsl:text>
                                                                <xsl:call-template name="warning-tip">
                                                                    <xsl:with-param name="tip-placement">right</xsl:with-param>
                                                                    <xsl:with-param name="tip-text">This parameter is known to be unreliable, so use its value with caution</xsl:with-param>
                                                                </xsl:call-template>
                                                            </xsl:if>
                                                            </td>
                                                            <td>
                                                                <xsl:attribute name="class">
                                                                    <xsl:if test="@warning = 'true'">has-warning</xsl:if>
                                                                </xsl:attribute>
                                                                <!-- If metadata tag is "Data Type", then replace '_' with ' ' -->
                                                                <xsl:choose>
                                                                    <xsl:when test="@name = 'Data Type'">
                                                                        <xsl:call-template name="string-replace-all">
                                                                            <xsl:with-param name="text"><xsl:value-of select="current()"/></xsl:with-param>
                                                                            <xsl:with-param name="replace" select="'_'" />
                                                                            <xsl:with-param name="by" select="' '" />
                                                                        </xsl:call-template>
                                                                    </xsl:when>
                                                                    <xsl:otherwise>
                                                                        <xsl:value-of select="current()"/>
                                                                    </xsl:otherwise>
                                                                </xsl:choose></td>
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
                </xsl:for-each>
                <div id="filelist-modal" class="modal">
                    <div class="modal-content">
                        <div class="container-fluid">
                            <div class="row">
                                <div class="col-med-11 pull-left">
                                    <b>Complete filelisting for:</b><br/>
                                    <span class='modal-expTitle'>
                                        <i class="fa fa-file-text-o results-icon"/>
                                        <xsl:value-of select="$expTitle"/>
                                    </span> - <span class='modal-expDate'><xsl:value-of select="$date"/></span><br/>
                                    <span class='modal-expTitle'>Root path: </span><code id='filelist-rootpath'><a>
                                        <xsl:attribute name="href">
                                            <xsl:value-of select="$datasetBaseUrl"/>
                                        </xsl:attribute>
                                        <xsl:attribute name="target">_blank</xsl:attribute>
                                        <xsl:attribute name="class">help-tip</xsl:attribute>
                                        <xsl:attribute name="data-toggle">tooltip</xsl:attribute>
                                        <xsl:attribute name="data-placement">top</xsl:attribute>
                                        <xsl:attribute name="title">Click to view directory struture directly in the browser</xsl:attribute>
                                    </a></code>
                                </div>
                                <div class="col-xs-1 pull-right">
                                    <i class="close-modal fa fa-close" onclick="closeModal('filelist-modal')"/>
                                </div>
                            </div>
                            <div class="row">
                                <div class='col-xs-12' style="padding-top: 10px;">
                                    <!-- Generate the table with setup conditions for each acquisition activity -->
                                    <table class="table table-condensed table-hover filelist-table compact" border="1" style="">
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
                                                    Path
                                                    <xsl:call-template name="help-tip">
                                                        <xsl:with-param name="tip-placement">top</xsl:with-param>
                                                        <xsl:with-param name="tip-text">The path (relative to root path, above) containing this dataset</xsl:with-param>
                                                    </xsl:call-template>
                                                </th>
                                                <th>
                                                    Type
                                                    <xsl:call-template name="help-tip">
                                                        <xsl:with-param name="tip-placement">top</xsl:with-param>
                                                        <xsl:with-param name="tip-text">A label indicating the data type of this dataset (taken from a controlled list)</xsl:with-param>
                                                    </xsl:call-template>
                                                </th>
                                                <xsl:choose>
                                                    <xsl:when test="//dataset/format/text()">
                                                        <th>
                                                            Format
                                                            <xsl:call-template name="help-tip">
                                                                <xsl:with-param name="tip-placement">top</xsl:with-param>
                                                                <xsl:with-param name="tip-text">A string (can be a MIME type) indicating the format of the dataset (e.g. TIFF, DICOM, Excel)</xsl:with-param>
                                                            </xsl:call-template>
                                                        </th>
                                                    </xsl:when>
                                                </xsl:choose>
                                                <th class='text-center' style='padding-right: 1%'>Meta</th>
                                                <th class='text-center' style='padding-right: 1%'>D/L</th>
                                            </tr>
                                        </thead>
                                        <tbody>
                                            <xsl:for-each select="//dataset">
                                                <tr>
                                                    <xsl:element name="td">
                                                        <xsl:value-of select="name"/>
                                                    </xsl:element>
                                                    <td class='filepath'>
                                                        <xsl:call-template name="get-path-of-file">
                                                            <xsl:with-param name="absolute_filename">
                                                                <xsl:value-of select="location"/>
                                                            </xsl:with-param>
                                                        </xsl:call-template>
                                                    </td>
                                                    <xsl:variable name="dataset-type">
                                                        <xsl:choose>
                                                            <xsl:when test="string(@type) = 'SpectrumImage'">Spectrum Image</xsl:when>
                                                            <xsl:otherwise><xsl:value-of select="@type"/></xsl:otherwise>
                                                        </xsl:choose>
                                                    </xsl:variable>
                                                    <td><xsl:value-of select="$dataset-type"/></td>
                                                    <xsl:choose>
                                                        <xsl:when test="../dataset/format/text()">
                                                            <td><xsl:value-of select="format/text()"/></td>
                                                        </xsl:when>
                                                    </xsl:choose>
                                                    <td class='text-center'>
                                                        <xsl:variable name="json-tmp"><xsl:value-of select="$previewBaseUrl"/><xsl:value-of select="preview"/></xsl:variable>
                                                        <xsl:variable name="json-location"><xsl:value-of select="substring-before($json-tmp, '.thumb.png')"/>.json</xsl:variable>
                                                        <xsl:element name='a'>
                                                            <xsl:attribute name="href"><xsl:value-of select="$json-location"/></xsl:attribute>
                                                            <xsl:attribute name="onclick">
                                                                $(this).blur()
                                                            </xsl:attribute>
                                                            <xsl:attribute name="target">_blank</xsl:attribute>
                                                            <xsl:attribute name="data-toggle">tooltip</xsl:attribute>
                                                            <xsl:attribute name="data-placement">right</xsl:attribute>
                                                            <xsl:attribute name="data-html">true</xsl:attribute>
                                                            <xsl:attribute name="title">Click to download this dataset's metadata in JSON format</xsl:attribute>
                                                            <i class='fa fa-download fa-border param-button' style='margin-left:0;'/>
                                                        </xsl:element>
                                                    </td>
                                                    <td class='text-center'>
                                                        <xsl:element name='a'>
                                                            <xsl:attribute name="href"><xsl:value-of select="$datasetBaseUrl"/><xsl:value-of select="location"/></xsl:attribute>
                                                            <xsl:attribute name="onclick">
                                                                $(this).blur()
                                                            </xsl:attribute>
                                                            <xsl:attribute name="data-toggle">tooltip</xsl:attribute>
                                                            <xsl:attribute name="data-placement">right</xsl:attribute>
                                                            <xsl:attribute name="data-html">true</xsl:attribute>
                                                            <xsl:attribute name="title">Click to download &#013;<xsl:value-of select='name'/></xsl:attribute>
                                                            <i class='fa fa-download fa-border param-button' style='margin-left:0;'/>
                                                        </xsl:element>
                                                    </td>
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

            <!-- Javascript which supports some capabilities on the generated page -->
            <script language="javascript">
                <![CDATA[
                
                // Function to find common path from list of paths (https://www.rosettacode.org/wiki/Find_common_directory_path#JavaScript)
                /**
                 * Given an array of strings, return an array of arrays, containing the
                 * strings split at the given separator
                 * @param {!Array<!string>} a
                 * @param {string} sep
                 * @returns {!Array<!Array<string>>}
                 */
                const splitStrings = (a, sep = '/') => a.map(i => i.split(sep));
                 
                /**
                 * Given an index number, return a function that takes an array and returns the
                 * element at the given index
                 * @param {number} i
                 * @return {function(!Array<*>): *}
                 */
                const elAt = i => a => a[i];
                 
                /**
                 * Transpose an array of arrays:
                 * Example:
                 * [['a', 'b', 'c'], ['A', 'B', 'C'], [1, 2, 3]] ->
                 * [['a', 'A', 1], ['b', 'B', 2], ['c', 'C', 3]]
                 * @param {!Array<!Array<*>>} a
                 * @return {!Array<!Array<*>>}
                 */
                const rotate = a => a[0].map((e, i) => a.map(elAt(i)));
                 
                /**
                 * Checks of all the elements in the array are the same.
                 * @param {!Array<*>} arr
                 * @return {boolean}
                 */
                const allElementsEqual = arr => arr.every(e => e === arr[0]);
                function commonPath(input, sep = '/') {
                    return rotate(splitStrings(input, sep)).filter(allElementsEqual).map(elAt(0)).join(sep);
                 }
                
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
                
                function activate_metadata_tooltips(){
                    // activate tooltips (on demand)
                    $('table.meta-table [data-toggle="tooltip"]').tooltip({trigger: 'hover'}); 
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
            
                // Things to do when document is ready
                $(document).ready(function(){
                    /* Add navigation to sidenav using DataTables */
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
                            dom: "<'row'<'col-sm-4'f><'col-sm-8'p>><'row'<'col-sm-12't>>",
                            drawCallback: function(){
                                            $('.paginate_button.next', this.api().table().container())          
                                                .on('click', activate_metadata_tooltips());    
                                                $('.paginate_button.previous', this.api().table().container())          
                                                .on('click', activate_metadata_tooltips()); 
                                        },
                        });
                    });
                    
                    // Make AA filelist tables DataTables
                    $('.aa-table').each(function() {
                        var this_table = $(this).DataTable({
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
                            dom: "<'row table-row't><'row pager-row'<'col-xs-12 pager-col text-right'p>>",
                        });
                        
                        // controls to reveal appropriate image on row hover
                        $(this).on('mouseenter', '> tbody > tr', function() {
                            // get the id of the correct image by looking at the row's img-id attribute
                            var this_rows_img = $(this).first().attr('img-id');
                            // the image we want to show is the one with that id
                            var img_to_show = $('#' + this_rows_img);
                            // get any img that have the visible class (so we can hide them)
                            var img_to_hide = img_to_show.siblings('.aa-img.visible');
                            // show/hide by adding and removing appropriate classes
                            img_to_hide.addClass('hidden');
                            img_to_hide.removeClass('visible');
                            img_to_show.addClass('visible');
                            img_to_show.removeClass('hidden');
                        });
                        
                        var new_container = $(this).closest('.aa-content-row').next('.dt_paginate_container');
                        var to_move = $(this).closest('.table-row').next('.pager-row').find('.pager-col');
                        //debugger;
                        new_container.append(to_move);
                        //debugger;
                        
                    });
                    
                    // Get array of filepaths from filelist-modal using jQuery:
                    $('div#filelist-modal').each(function() {
                      var paths = $('td.filepath').map(function() {
                              return $(this).text();
                          }).get();
                      var rootPath = commonPath(paths, '/');
                      $('td.filepath').each(function() {
                        curText = $(this).text();
                        // replace common path with blank in each file's path
                        $(this).text(curText.replace(rootPath, ''));
                      });
                      // put root path text into modal header link
                      $('code#filelist-rootpath > a').each(function() {
                        $(this).text(rootPath);
                        $(this).attr("href", $(this).attr("href") + rootPath);
                      });
                    });
                    
                    // Make sidebar visible after everything is done loading:
                    $('.sidebar').first().css('visibility', 'visible');
                    
                    // Fade out the loading screen
                    $('#loading').fadeOut('slow');                
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
                            <xsl:attribute name="title">Gatan DigitalMicrograph file (v3)</xsl:attribute>
                        </xsl:when>
                        <xsl:when test="$input = 'dm4'">
                            <xsl:attribute name="title">Gatan DigitalMicrograph file (v4)</xsl:attribute>
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
    
    <xsl:template name="warning-tip">
        <xsl:param name="tip-text"/>
        <xsl:param name="tip-placement" select='"right"'></xsl:param>
        <xsl:element name="sup">
            <xsl:attribute name="class">warning-tip</xsl:attribute>
            <xsl:attribute name="data-toggle">tooltip</xsl:attribute>
            <xsl:attribute name="data-placement"><xsl:value-of select="$tip-placement"/></xsl:attribute>
            <xsl:attribute name="title"><xsl:value-of select="$tip-text"/></xsl:attribute>
            <i class='fa fa-exclamation-triangle'/>
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
    
    <xsl:template name="parse-activity-contents">
        <xsl:choose>
            <xsl:when test="setup/param[@name='Data Type']">
                <xsl:call-template name="string-replace-all">
                    <xsl:with-param name="text" select="setup/param[@name='Data Type']/text()"/>
                    <xsl:with-param name="replace" select="'_'" />
                    <xsl:with-param name="by" select="' '" />
                </xsl:call-template>
            </xsl:when>
            <xsl:otherwise>
                <xsl:variable name="this-aa-data-types">
                    <xsl:for-each select="./dataset/meta[@name='Data Type']"><xsl:value-of select="."/><xsl:text> </xsl:text></xsl:for-each>
                </xsl:variable>
                <xsl:variable name="deduped-data-types">
                    <xsl:call-template name="dedup-list">
                        <xsl:with-param name="input">
                            <xsl:value-of select="$this-aa-data-types"/>
                        </xsl:with-param>
                    </xsl:call-template>
                </xsl:variable>
                <xsl:variable name="comma-separated-list">
                    <xsl:call-template name="string-replace-all">
                        <xsl:with-param name="text" select="$deduped-data-types"/>
                        <xsl:with-param name="replace" select="' '" />
                        <xsl:with-param name="by" select="', '" />
                    </xsl:call-template>
                </xsl:variable>
                <xsl:call-template name="string-replace-all">
                    <xsl:with-param name="text" select="$comma-separated-list"/>
                    <xsl:with-param name="replace" select="'_'" />
                    <xsl:with-param name="by" select="' '" />
                </xsl:call-template>
            </xsl:otherwise>
        </xsl:choose>
    </xsl:template>
    
    <!-- Taken from http://geekswithblogs.net/Erik/archive/2008/04/01/120915.aspx -->
    <xsl:template name="string-replace-all">
        <xsl:param name="text" />
        <xsl:param name="replace" />
        <xsl:param name="by" />
        <xsl:choose>
            <xsl:when test="contains($text, $replace)">
                <xsl:value-of select="substring-before($text,$replace)" />
                <xsl:value-of select="$by" />
                <xsl:call-template name="string-replace-all">
                    <xsl:with-param name="text"
                        select="substring-after($text,$replace)" />
                    <xsl:with-param name="replace" select="$replace" />
                    <xsl:with-param name="by" select="$by" />
                </xsl:call-template>
            </xsl:when>
            <xsl:otherwise>
                <xsl:value-of select="$text" />
            </xsl:otherwise>
        </xsl:choose>
    </xsl:template>
    
    <xsl:template name="strip-tags">
        <xsl:param name="text"/>
        <xsl:comment>From https://ehikioya.com/remove-html-tags-xsl-value/</xsl:comment>
        <xsl:choose>
            <xsl:when test="contains($text, '&lt;')">
                <xsl:value-of select="substring-before($text, '&lt;')"/>
                <xsl:call-template name="strip-tags">
                    <xsl:with-param name="text" select="substring-after($text, '&gt;')"/>
                </xsl:call-template>
            </xsl:when>
            <xsl:otherwise>
                <xsl:value-of select="$text"/>
            </xsl:otherwise>
        </xsl:choose>
    </xsl:template>
    
</xsl:stylesheet>