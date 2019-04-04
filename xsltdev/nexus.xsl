<xsl:stylesheet 
        xmlns:xsl="http://www.w3.org/1999/XSL/Transform" version="1.0"

        xmlns:nx="https://data.nist.gov/od/dm/nexus/experiment/v1.0">
        
        <xsl:template match="/nx:Experiment">
            <html>
                <body>		
                    <h2>A Prototype Nexus Experiment</h2>
                    <h3>id</h3> 
                    <xsl:value-of select="id"/>
                    
                    
                    <table border="1">
                        <tr bgcolor ="#9acd32">
                            <th>experimenter</th>
                            <th>collaborator</th>
                            <th>instrument</th>
                        </tr>
                        
                        <xsl:apply-templates select="summary"/>
                       <!--<xsl:for-each select="summary">            
                                   
                            </xsl:for-each> -->   
                  </table>
                </body>
            </html>
            
        </xsl:template>
        <xsl:template match ="summary">
            <xsl:comment>INSIDE SUMMARY TEMPLATE</xsl:comment>
            <tr>
                <td>
                    <xsl:value-of select="experimenter"/>
                </td>
                <td>
                    <xsl:value-of select="collaborator"/>
                </td>
                <td>
                    <xsl:value-of select="instrument"/>
                </td>
                
                
            </tr>
            
            <table border="1">
                <tr bgcolor ="#9acd32">
            <tr>
                <th>reservationStart</th>
                <th>reservationEnd</th>
                
            </tr>
            
            <tr>
                <td>
                    <xsl:value-of select="reservationStart"/>
                </td>
                <td>
                    <xsl:value-of select="reservationEnd"/>
                </td>        
            </tr>
                </tr>
                <tr>
                    <th>motivation</th>
                </tr>
            
            <tr>
                <td>
                    <xsl:value-of select="motivation"/>
                </td>
            </tr>
            
            </table>  
        </xsl:template>
    
</xsl:stylesheet>