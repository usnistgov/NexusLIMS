#  NIST Public License - 2020
#
#  This software was developed by employees of the National Institute of
#  Standards and Technology (NIST), an agency of the Federal Government
#  and is being made available as a public service. Pursuant to title 17
#  United States Code Section 105, works of NIST employees are not subject
#  to copyright protection in the United States.  This software may be
#  subject to foreign copyright.  Permission in the United States and in
#  foreign countries, to the extent that NIST may hold copyright, to use,
#  copy, modify, create derivative works, and distribute this software and
#  its documentation without fee is hereby granted on a non-exclusive basis,
#  provided that this notice and disclaimer of warranty appears in all copies.
#
#  THE SOFTWARE IS PROVIDED 'AS IS' WITHOUT ANY WARRANTY OF ANY KIND,
#  EITHER EXPRESSED, IMPLIED, OR STATUTORY, INCLUDING, BUT NOT LIMITED
#  TO, ANY WARRANTY THAT THE SOFTWARE WILL CONFORM TO SPECIFICATIONS, ANY
#  IMPLIED WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE,
#  AND FREEDOM FROM INFRINGEMENT, AND ANY WARRANTY THAT THE DOCUMENTATION
#  WILL CONFORM TO THE SOFTWARE, OR ANY WARRANTY THAT THE SOFTWARE WILL BE
#  ERROR FREE.  IN NO EVENT SHALL NIST BE LIABLE FOR ANY DAMAGES, INCLUDING,
#  BUT NOT LIMITED TO, DIRECT, INDIRECT, SPECIAL OR CONSEQUENTIAL DAMAGES,
#  ARISING OUT OF, RESULTING FROM, OR IN ANY WAY CONNECTED WITH THIS SOFTWARE,
#  WHETHER OR NOT BASED UPON WARRANTY, CONTRACT, TORT, OR OTHERWISE, WHETHER
#  OR NOT INJURY WAS SUSTAINED BY PERSONS OR PROPERTY OR OTHERWISE, AND
#  WHETHER OR NOT LOSS WAS SUSTAINED FROM, OR AROSE OUT OF THE RESULTS OF,
#  OR USE OF, THE SOFTWARE OR SERVICES PROVIDED HEREUNDER.
#

from nexusLIMS.utils import parse_xml
from nexusLIMS.utils import try_getting_dict_value
from nexusLIMS.utils import get_nested_dict_value
from io import StringIO, BytesIO
from lxml import etree
import pytest


class TestUtils:
    def test_parse_xml_bad_xslt(self):
        xml_string = '<xml><level1>test</level1></xml>'
        xsl_string = \
            b"""
            <xsl:stylesheet xmlns:xsl="http://www.w3.org/1999/XSL/Transform"
            xmlns:xsi="http://www.w3.org/2001/XMLSchema"                                                             
            xmlns:nx="https://data.nist.gov/od/dm/nexus/experiment/v1.0"                                             
            version="1.0">                                                                                           
            <xsl:output method="html" indent="yes" encoding="UTF-8"/>                                                
            <xsl:template match="/">                                                                                 
                <xsl:comment>--</xsl:comment>                                                                        
            </xsl:template> 
            </xsl:stylesheet>
            """
        with pytest.raises(etree.XSLTApplyError):
            parse_xml(xml_string, BytesIO(xsl_string))

    def test_get_nested_dict_value(self):
        nest = {'level1': {'level2.1': {'level3.1': 'value'}}}
        assert get_nested_dict_value(nest, 'value') == ('level1', 'level2.1',
                                                        'level3.1')
        assert get_nested_dict_value(nest, 'bogus') is None

    def test_try_getting_dict_val(self):
        non_nest = {'level1': 'value_1'}
        nest = {'level1': {'level2.1': {'level3.1': 'value'}}}

        assert try_getting_dict_value(non_nest, 'level1') == 'value_1'
        assert try_getting_dict_value(non_nest, 'level3') == 'not found'
        assert try_getting_dict_value(nest, ['level1', 'level2.1']) == {
            'level3.1': 'value'}
