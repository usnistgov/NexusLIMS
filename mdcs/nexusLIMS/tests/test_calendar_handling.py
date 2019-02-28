import os
import pytest
from lxml import etree
from .. import writeCalEvents as wce


class TestCalendarHandling:
    XML_TEST_FILE = os.path.join(os.path.dirname(__file__),
                                 "2019-02-28_titan_cal.xml")

    @pytest.mark.parametrize('instrument', ['titan', 'quanta', 'jeol_sem',
                                            'hitachi_sem', 'jeol_tem',
                                            'cm30', 'em400'])
    def test_downloading_valid_calendars(self, instrument):
        wce.fetch_xml(instrument)

    def test_downloading_bad_calendar(self):
        with pytest.raises(KeyError):
            wce.fetch_xml('bogus_instr')

    def test_calendar_parsing(self):

        with open(self.XML_TEST_FILE, 'rb') as f:
            xml_string = wce.wrap_events(str(wce.parse_xml(f.read())))

        doc = etree.fromstring(xml_string)
        doc.getchildren()

        return
