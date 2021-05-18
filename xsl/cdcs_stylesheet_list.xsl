<xsl:stylesheet xmlns:xsl="http://www.w3.org/1999/XSL/Transform"
  xmlns:xsi="http://www.w3.org/2001/XMLSchema"
  xmlns:nx="https://data.nist.gov/od/dm/nexus/experiment/v1.0" version="1.0">
  <xsl:output method="html" indent="yes" encoding="UTF-8"/>

  <xsl:param name="detail_url" select="'#'"/>
  <xsl:variable name="datasetBaseUrl">https://***REMOVED***/mmfnexus/</xsl:variable>
  <xsl:variable name="previewBaseUrl">https://***REMOVED***/nexusLIMS/mmfnexus/</xsl:variable>

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
    
    <style>
      .tooltip {
      z-index: 20000;
      position: fixed; 
      }
    </style>
    <div class='a-result'>
     <div>
       <xsl:element name="a">
         <xsl:attribute name="href">
           <xsl:value-of select="$detail_url"/>
         </xsl:attribute>
         <span class="list-record-title">
             <i class="fas fa-file-alt results-icon"/>
           <xsl:choose>
             <xsl:when test="$title = 'No matching calendar event found'">
               <xsl:text>Untitled experiment</xsl:text>
             </xsl:when>
             <xsl:otherwise>
               <xsl:value-of select="$title"/>
             </xsl:otherwise>
           </xsl:choose>
         </span>
       </xsl:element>
       <xsl:text> </xsl:text>
       <xsl:variable name="instr-pid">
         <xsl:value-of select="string(summary/instrument/@pid)"/>
       </xsl:variable>
       <span class="badge list-record-badge">
         <xsl:attribute name="style">background-color:<xsl:for-each select="document('')">
             <xsl:value-of select="key('lookup.instr.color', $instr-pid)"/>
           </xsl:for-each> !important;</xsl:attribute>
         <xsl:value-of select="summary/instrument"/>
       </span>
       <span class="badge list-record-badge">
         <xsl:value-of select="count(//dataset)"/> data files in <xsl:value-of select="count(//acquisitionActivity)"/> activit<xsl:choose>
           <xsl:when test="count(//acquisitionActivity) = 1">y</xsl:when>
           <xsl:otherwise>ies</xsl:otherwise>
         </xsl:choose> </span>
        <i class="fa fa-cubes filetypes-icon" style="margin-left:0.75em; font-size: small;"
            data-toggle="tooltip" data-placement="top" title="Filetypes present in record"/><span style="font-size: small;"><xsl:text>: </xsl:text></span>
       <xsl:call-template name="extensions-to-badges">
         <xsl:with-param name="input"><xsl:value-of select="$unique-extensions"/></xsl:with-param>
       </xsl:call-template>
     </div>
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
      <xsl:choose>
        <xsl:when test="summary/motivation/text()">
          <div class="motivation-text">
            <span style="font-style:italic;">Motivation: </span><xsl:value-of select="summary/motivation"/>
          </div>
        </xsl:when>
      </xsl:choose>
     
        <!-- Javascript which supports some capabilities on the generated page -->
        <script language="javascript">
            <![CDATA[
            $('.a-result').click(function() {
                window.location = $(this).find('a').attr('href');
                return false;
            });
            
            // Shepherd tutorial code
            function create_tour() {
                var topScrollHandler = function(element){
                    if (element) {
                        var $element = $(element);
                        var topOfElement = $element.offset().top;
                        var heightOfElement = $element.height() + 75;
                        $('html, body').animate({
                            scrollTop: topOfElement - heightOfElement
                        },{
                            duration: 500
                        });
                    }
                };

                var list_tour = new Shepherd.Tour({
                    useModalOverlay: true,
                    defaultStepOptions: {
                        when: { show() { showStepNumber() } },
                        scrollTo: true,
                        scrollToHandler: topScrollHandler
                    }
                });
            
                showStepNumber = () => {
                    $("<span style='font-size: small'></span>")
                        .insertAfter('.shepherd-footer .btn-default')
                        .html(`${list_tour.steps.indexOf(list_tour.currentStep) + 1}/${list_tour.steps.length}`);
                }
                
                end_button = {
                    text: 'End',
                    classes: 'btn btn-danger',
                    action: list_tour.next,
                    label: 'End'
                }
                
                next_button = {
                    text: 'Next <i class="fa fa-arrow-right menu-fa"></i>',
                    classes: 'btn btn-primary',
                    action: list_tour.next,
                    label: 'Next'
                }
                
                var back_button = (enabled) => {
                    return {
                        text: '<i class="fa fa-arrow-left menu-fa"></i> Back',
                        classes: 'btn btn-default',
                        disabled: (! enabled),
                        action: list_tour.back,
                        label: 'Back'}
                }
            
                list_tour.addStep({
                    id: 'tut-welcome',
                    title: 'This is the record explorer page',
                    text: 'The <em>explore</em> page allows you to browse and search through the records contained in the NexusLIMS repository. Click <em>Next</em> for a brief tour of the features of this page. You can also use the keyboard arrow keys to navigate through the tutorial.',
                    buttons: [
                        back_button(false),
                        next_button
                    ],
                });
            
                list_tour.addStep({
                    id: 'tut-search-field',
                    title: 'The search bar',
                    text: 'Use the search box to do a full-text search on all the records (can search by username, date, instrument, etc.). Leave the box empty to return all results from the database.',
                    attachTo: {
                        element: '#search-field',
                        on: 'bottom'
                    },
                    buttons: [
                        back_button(true),
                        next_button
                    ],
                });
            
                list_tour.addStep({
                    id: 'tut-example-record',
                    title: 'An example record listing',
                    text: 'Each listing in the results area represents one record in the database and provides some basic summary information about the record\'s contents. Click anywhere on the listing to view the record details.',
                    attachTo: {
                        element: '#example-record',
                        on: 'bottom'
                    },
                    scrollTo: false,
                    buttons: [
                        back_button(true),
                        next_button
                    ],
                });
            
                
            
                list_tour.addStep({
                    id: 'tut-result-button-filter',
                    title: 'Record sorting',
                    text: 'By default, the records are sorted with the most recently added records first. Use this sort button to change the sorting order.',
                    attachTo: {
                        element: '#result-button-filter0',
                        on: 'left'
                    },
                    scrollTo: false,
                    buttons: [
                        back_button(true),
                        $('.pagination-container').length > 0 ? next_button : end_button
                    ],
                    modalOverlayOpeningPadding: 15,
                    popperOptions: {
                        modifiers: [{
                            name: 'offset',
                            options: {
                                offset: [0, 15]
                            }
                        }]
                    }
                });
            
                if ( $('.pagination-container').length > 0 ) {
                    list_tour.addStep({
                        id: 'tut-pagination-container',
                        title: 'Browsing many records',
                        text: 'If your search returns more items than fit on one page, use the paging controls at the bottom to browse through the records',
                        attachTo: {
                            element: '#pagination-container',
                            on: 'bottom'
                        },
                        when: { show() { showStepNumber() } },
                        buttons: [
                            back_button(true),
                            end_button
                        ]
                    });
                }
            
                var scroll_to_start = function() {
                    $('html, body').animate(
                        {scrollTop: cur_pos}, 
                        {duration: 500}
                    );
                }
            
                let cur_pos = $(document).scrollTop();
                list_tour.on('complete', scroll_to_start)
                list_tour.on('cancel', scroll_to_start)
                list_tour.on('hide', scroll_to_start)
                $('.shepherd-modal-overlay-container').on('click', () => list_tour.cancel());
                list_tour.start()
            }              

            $( document ).ready(function() {
                $('[data-toggle="tooltip"]').tooltip(
                    {container:'body'}); // toggle all tooltips with default
              
                // add IDs for use with intro.js
                $('.a-result').first().attr('id', 'example-record');
                $('input#id_keywords ~ ul').attr('id', 'search-field');
                $('.pagination-container').attr('id', 'pagination-container');
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
      <xsl:when test="$i = 1">
        <xsl:choose>
          <xsl:when test="contains($text, $delim)">
            <xsl:value-of select="substring-before($text, $delim)"/>
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
            <xsl:value-of select="substring-after($text, $delim)"/>
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
    <xsl:choose>
      <!-- Our string contains a space, so there are more values to process -->
      <xsl:when test="contains($input, ' ')">
        <xsl:call-template name="extensions-to-badges">
          <xsl:with-param name="input" select="substring-before($input, ' ')"></xsl:with-param>
        </xsl:call-template>
        <xsl:call-template name="extensions-to-badges">
          <xsl:with-param name="input" select="substring-after($input, ' ')"></xsl:with-param>
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
            <xsl:value-of select="count(//dataset/location[$input = substring(., string-length() - string-length($input) + 1)])"/>
          </span>
          <span class="badge-right badge list-record-badge">
            <xsl:value-of select="$input"/>
          </span>
        </span>
      </xsl:otherwise>
    </xsl:choose>
  </xsl:template>
  
</xsl:stylesheet>
