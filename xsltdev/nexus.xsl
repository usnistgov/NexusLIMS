<xsl:stylesheet 
        xmlns:xsl="http://www.w3.org/1999/XSL/Transform" version="1.0"

        xmlns:nx="https://data.nist.gov/od/dm/nexus/experiment/v1.0">
        
        <xsl:template match="/nx:Experiment">
            <html>
                <body>		
                    <h2>A Prototype Nexus Experiment</h2>
                    <h3>id</h3> 
                    
                    
                    <table border="1">
                        <tr bgcolor ="#9acd32">
                            <th>experimenter</th>
                            <th>collaborator</th>
                            <th>instrument</th>
                        </tr>
                        <xsl:apply-templates select="summary"/>
                       <!--<xsl:for-each select="summary">
                                   
                            </xsl:for-each> -->
                                <tr>
                                    <td>
                                        <xsl:value-of select="reservationStart"/>
                                            <xsl:value-of select="reservationEnd"/>
                                </td>        
                                </tr>
                              
                                <tr>
                                    <td>
                                        <xsl:value-of select="motivation"/>
                                  </td>
                                </tr>
                               
                          
                        
                    </table>
                </body>
            </html>
            
        </xsl:template>
        <xsl:template match ="summary">
            <xsl:comment>INSIDE SUMMARY TEMPLATE</xsl:comment>
            <xsl:element name="tr">
                <xsl:element name="td">
                    <xsl:value-of select="experimenter"/>
                </xsl:element>
                
                <td>
                    <xsl:value-of select="collaborator"/>
                </td>
                <td>
                    <xsl:value-of select="instrument"/>
                </td>
            </xsl:element>
        </xsl:template>
    
</xsl:stylesheet>