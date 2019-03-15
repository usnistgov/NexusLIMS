import os
import pytest
from lxml import etree
from .. import writeCalEvents as wce


class TestCalendarHandling:
    # This file is the raw response manually copied from
    # https://***REMOVED***/***REMOVED***/_vti_bin/ListData.svc/FEITitanTEM?$expand=CreatedBy
    # into a file on the disk to have something to test against. The only
    # modification made was the manual removal of
    # 'xmlns="http://www.w3.org/2005/Atom"' from the top level element, since
    # this is done by fetch_xml() in the actual processing
    XML_TEST_FILE = os.path.join(os.path.dirname(__file__),
                                 "2019-03-14_titan_tem_cal.xml")

    @pytest.mark.parametrize('instrument', ['msed_titan', 'quanta', 'jeol_sem',
                                            'hitachi_sem', 'jeol_tem',
                                            'cm30', 'em400', 'hitachi_s5500',
                                            'mmsd_titan', 'fei_helios_db'])
    def test_downloading_valid_calendars(self, instrument):
        wce.fetch_xml(instrument)

    def test_downloading_bad_calendar(self):
        with pytest.raises(KeyError):
            wce.fetch_xml('bogus_instr')

    def test_calendar_parsing(self):
        # TODO: do tests here on parsed xml (number of events, extract
        #  certain users, etc.) using parse_xml()

        # return the xml parsed from the file
        with open(self.XML_TEST_FILE, 'rb') as f:
            file_content = f.read()

        # parsed_xml will be an _XSLTResultTree object with many
        # <event>...</event> tags on the same level
        parsed_xml = wce.parse_xml(file_content)
        raw_xml = etree.fromstring(file_content)

        # convert parsing result to string and wrap so we have well-formed xml:
        xml_string = wce.wrap_events(str(parsed_xml))

        doc = etree.fromstring(xml_string)
        # there should be
        doc.findall('event')

        return
