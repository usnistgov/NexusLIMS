import os
import pytest
import requests
from lxml import etree
from nexusLIMS.harvester import sharepoint_calendar as sc
from nexusLIMS.utils import parse_xml as _parse_xml
from nexusLIMS.utils import nexus_req as _nexus_req
from nexusLIMS.harvester.sharepoint_calendar import AuthenticationError
from nexusLIMS.instruments import instrument_db
from collections import OrderedDict

import warnings
warnings.filterwarnings(
    action='ignore',
    message=r"DeprecationWarning: Using Ntlm()*",
    category=DeprecationWarning)
warnings.filterwarnings(
    'ignore',
    r"Manually creating the cbt stuct from the cert hash will be removed",
    DeprecationWarning)


class TestCalendarHandling:
    SC_XSL_FILE = os.path.abspath(
        os.path.join(os.path.dirname(sc.__file__), 'cal_parser.xsl'))
    CREDENTIAL_FILE_ABS = os.path.abspath(
        os.path.join(os.path.dirname(__file__),
                     '..',
                     'credentials.ini.example'))
    CREDENTIAL_FILE_REL = os.path.join('..', 'credentials.ini.example')

    # get xml content from the FEI Titan for use with parse_xml (we do it at
    # class level so we don't have to hit the server more than once)
    #  The only modification made is the manual removal of
    #  'xmlns="http://www.w3.org/2005/Atom"' from the top level element,
    #  since this is done by fetch_xml() in the actual processing
    instr_url = instrument_db['FEI-Titan-TEM-635816'].api_url + \
                '?$expand=CreatedBy'
    xml_content = _nexus_req(instr_url, requests.get).text.replace(
        'xmlns="http://www.w3.org/2005/Atom"', '')

    @pytest.fixture
    def parse_xml(self):
        """
        Use the parse_xml method to actually parse the xml through the XSLT
        stylesheet, which we can then compare to parsing the raw calendar
        events directly.
        """
        # return the xml parsed from the file
        file_content = bytes(TestCalendarHandling.xml_content, encoding='utf-8')

        # parsed_xml items will be an _XSLTResultTree object with many
        # <event>...</event> tags on the same level
        parsed_xml = dict()
        # should be 403 items
        parsed_xml['all'] = _parse_xml(xml=file_content,
                                       xslt_file=self.SC_XSL_FILE)
        # should be 10 items
        parsed_xml['user'] = _parse_xml(xml=file_content,
                                        xslt_file=self.SC_XSL_FILE,
                                        user="***REMOVED***")
        # should be 2 items
        parsed_xml['date'] = _parse_xml(xml=file_content,
                                        xslt_file=self.SC_XSL_FILE,
                                        date='2019-03-06')
        # should be 1 item
        parsed_xml['date_and_user'] = _parse_xml(xml=file_content,
                                                 xslt_file=self.SC_XSL_FILE,
                                                 date='2019-03-06',
                                                 user='***REMOVED***')

        # convert parsing result to string and wrap so we have well-formed xml:
        xml_strings = dict()
        for k, v in parsed_xml.items():
            xml_strings[k] = sc._wrap_events(str(v))

        # get document tree from the raw file and the ones we parsed:
        parsed_docs = dict()
        raw_doc = etree.fromstring(file_content)
        for k, v in xml_strings.items():
            parsed_docs[k] = etree.fromstring(v)

        return raw_doc, parsed_docs

    @pytest.mark.parametrize('instrument', list(instrument_db.values()),
                             ids=list(instrument_db.keys()))
    def test_downloading_valid_calendars(self, instrument):
        # Handle the two test instruments that we put into the database,
        # which will raise an error because their url values are bogus
        if instrument.name in ['testsurface-CPU_P1111111',
                               'testVDI-VM-JAT-111222']:
            with pytest.raises(requests.exceptions.ConnectionError):
                sc.fetch_xml(instrument)
        else:
            sc.fetch_xml(instrument)

    def test_download_with_date(self):
        doc = etree.fromstring(
            sc.fetch_xml(instrument=instrument_db['FEI-Titan-TEM-635816'],
                         date='2018-11-13'))
        # This day should have one entry:
        assert len(doc.findall('entry')) == 1

    def test_downloading_bad_calendar(self):
        with pytest.raises(KeyError):
            sc.fetch_xml('bogus_instr')

    def test_bad_username(self, monkeypatch):
        with monkeypatch.context() as m:
            m.setenv('nexusLIMS_user', 'bad_user')
            with pytest.raises(AuthenticationError):
                sc.fetch_xml(instrument_db['FEI-Titan-TEM-635816'])

    def test_absolute_path_to_credentials(self, monkeypatch):
        from nexusLIMS.harvester.sharepoint_calendar import get_auth
        with monkeypatch.context() as m:
            # remove environment variable so we get into file processing
            m.delenv('nexusLIMS_user')
            _ = get_auth(self.CREDENTIAL_FILE_ABS)

    def test_relative_path_to_credentials(self, monkeypatch):
        from nexusLIMS.harvester.sharepoint_calendar import get_auth
        os.chdir(os.path.dirname(__file__))
        with monkeypatch.context() as m:
            # remove environment variable so we get into file processing
            m.delenv('nexusLIMS_user')
            _ = get_auth(self.CREDENTIAL_FILE_REL)

    def test_bad_path_to_credentials(self, monkeypatch):
        from nexusLIMS.harvester.sharepoint_calendar import get_auth
        with monkeypatch.context() as m:
            # remove environment variable so we get into file processing
            m.delenv('nexusLIMS_user')
            cred_file = os.path.join('bogus_credentials.ini')
            with pytest.raises(AuthenticationError):
                _ = get_auth(cred_file)

    def test_bad_request_response(self, monkeypatch):
        with monkeypatch.context() as m:
            class MockResponse(object):
                def __init__(self):
                    self.status_code = 404

            def mock_get(url, auth, verify):
                return MockResponse()

            # User bad username so we don't get a valid response or lock miclims
            m.setenv('nexusLIMS_user', 'bad_user')

            # use monkeypatch to use our version of get for requests that
            # always returns a 404
            monkeypatch.setattr(requests, 'get', mock_get)
            with pytest.raises(requests.exceptions.ConnectionError):
                sc.fetch_xml(instrument_db['FEI-Titan-TEM-635816'])

    def test_fetch_xml_instrument_none(self, monkeypatch):
        with monkeypatch.context() as m:
            # use bad username so we don't get a response or lock miclims
            m.setenv('nexusLIMS_user', 'bad_user')
            with pytest.raises(AuthenticationError):
                sc.fetch_xml(instrument_db['FEI-Titan-TEM-635816'])

    def test_fetch_xml_instrument_bogus(self, monkeypatch):
        with monkeypatch.context() as m:
            # use bad username so we don't get a response or lock miclims
            m.setenv('nexusLIMS_user', 'bad_user')
            with pytest.raises(ValueError):
                sc.fetch_xml(instrument=5)

    def test_dump_calendars(self, tmp_path):
        from nexusLIMS.harvester.sharepoint_calendar import dump_calendars
        f = os.path.join(tmp_path, 'cal_output.xml')
        dump_calendars(instrument='FEI-Titan-TEM-635816', filename=f)

    def test_division_group_lookup(self):
        from nexusLIMS.harvester.sharepoint_calendar import get_events
        events = get_events(instrument='FEI-Titan-TEM-635816',
                            date='2019-03-06',
                            user='***REMOVED***')
        doc = etree.fromstring(events)
        assert doc.find('event/project/division').text == '642'
        assert doc.find('event/project/group').text == '00'

    def test_get_events_good_date(self):
        from nexusLIMS.harvester.sharepoint_calendar import get_events
        events_1 = get_events(instrument='FEI-Titan-TEM-635816',
                              date='2019-03-13')
        events_2 = get_events(instrument='FEI-Titan-TEM-635816',
                              date='March 13th, 2019')
        doc1 = etree.fromstring(events_1)
        doc2 = etree.fromstring(events_2)

        # test to make sure we extracted same event
        for el1, el2 in zip(doc1.find('event[1]').getchildren(),
                            doc2.find('event[1]').getchildren()):
            assert el1.text == el2.text

    def test_get_events_bad_date(self, caplog):
        from nexusLIMS.harvester.sharepoint_calendar import get_events

        get_events(instrument='FEI-Titan-TEM-635816', date='The Ides of March')

        assert 'Entered date could not be parsed; reverting to None...' in \
               caplog.text

    def test_calendar_parsing_event_number(self, parse_xml):
        """
        We will assume that if the number of elements for each case is the
        same, then we probably are parsing okay. This could be improved by
        actually testing the content of the elements (although that is done
        by test_parsed_event_content()). The number of events is going to
        increase as time goes on (since we're getting the calendar response
        dynamically), so we cannot know `a priori` how many there should be.
        """
        # Unpack the fixture tuple to use in our method
        raw_doc, parsed_docs = parse_xml

        # there should be 403 events to match the 403 entries in the raw xml
        parsed_event_list = parsed_docs['all'].findall('event')
        raw_entry_list = raw_doc.findall('entry')
        assert len(parsed_event_list) == len(raw_entry_list)
        # assert len(parsed_event_list) == 403

    def test_calendar_parsing_username(self, parse_xml):
        """
        We will assume that if the number of elements for each case is the
        same, then we probably are parsing okay. This could be improved by
        actually testing the content of the elements (although that is done
        by test_parsed_event_content())
        """
        # Unpack the fixture tuple to use in our method
        raw_doc, parsed_docs = parse_xml

        # test user parsing:
        # user '***REMOVED***' has 10 events on the Titan calendar
        raw_user_list = raw_doc.xpath("entry[./link/m:inline/entry/content/"
                                      "m:properties/d:UserName/text() = '***REMOVED***']",
                                      namespaces=raw_doc.nsmap)
        # parsed_docs['user'] is root <events> tag
        parse_xml_user_list = parsed_docs['user'].findall('event')

        assert len(raw_user_list) == len(parse_xml_user_list)
        assert len(parse_xml_user_list) == 10

    def test_calendar_parsing_date(self, parse_xml):
        """
        We will assume that if the number of elements for each case is the
        same, then we probably are parsing okay. This could be improved by
        actually testing the content of the elements (although that is done
        by test_parsed_event_content())
        """
        # Unpack the fixture tuple to use in our method
        raw_doc, parsed_docs = parse_xml

        # test date parsing:
        # 2019-03-06 has 2 events on the Titan calendar
        raw_date_list = raw_doc.xpath("entry[contains("
                                      "./content/m:properties/d:StartTime/"
                                      "text(), '2019-03-06')]",
                                      namespaces=raw_doc.nsmap)
        # parsed_docs['user'] is root <events> tag
        parse_xml_date_list = parsed_docs['date'].findall('event')

        assert len(raw_date_list) == len(parse_xml_date_list)
        assert len(parse_xml_date_list) == 2

    def test_calendar_parsing_username_and_date(self, parse_xml):
        """
        We will assume that if the number of elements for each case is the
        same, then we probably are parsing okay. This could be improved by
        actually testing the content of the elements (although that is done
        by test_parsed_event_content())
        """
        # Unpack the fixture tuple to use in our method
        raw_doc, parsed_docs = parse_xml

        # test date and user parsing:
        # 2019-03-06 has 2 events on the Titan calendar, one of which was
        # made by ***REMOVED***
        raw_date_list = raw_doc.xpath("entry[contains("
                                      "./content/m:properties/d:StartTime/"
                                      "text(), '2019-03-06') and "
                                      "./link/m:inline/entry/content/"
                                      "m:properties/d:UserName/text() = "
                                      "'***REMOVED***']",
                                      namespaces=raw_doc.nsmap)
        # parsed_docs['user'] is root <events> tag
        parse_xml_date_list = parsed_docs['date_and_user'].findall('event')

        assert len(raw_date_list) == len(parse_xml_date_list)
        assert len(parse_xml_date_list) == 1

    def test_parsed_event_content(self, parse_xml):
        """
        Test the content of the event that was parsed with the XSLT
        """
        # Unpack the fixture tuple to use in our method
        raw_doc, parsed_docs = parse_xml

        parsed_xml = parsed_docs['date_and_user']
        assert parsed_xml.tag == 'events'

        # Should be one event matching this condition
        event = parsed_docs['date_and_user'].find('event')
        tag_dict = OrderedDict([
            ('dateSearched', '2019-03-06'),
            ('userSearched', '***REMOVED***'),
            ('title', 'Bringing up HT'),
            ('instrument', 'FEITitanTEMEvents'),
            ('user', '\n  '),
            ('purpose', 'Still need to bring up HT '
                        'following water filter replacement'),
            ('sampleDetails', 'No sample'),
            ('description', None),
            ('startTime', '2019-03-06T09:00:00'),
            ('endTime', '2019-03-06T11:00:00'),
            ('link', instrument_db['FEI-Titan-TEM-635816'].api_url + '(501)'),
            ('eventId', '501')])

        user = parsed_docs['date_and_user'].find('event/user')
        link_idx = instrument_db['FEI-Titan-TEM-635816'].api_url.rfind('/')
        lnk_base = instrument_db['FEI-Titan-TEM-635816'].api_url[:link_idx]
        user_dict = OrderedDict([
            ('userName', '***REMOVED***'),
            ('name', '***REMOVED*** (Fed)'),
            ('email', '***REMOVED***'),
            ('phone', '***REMOVED***'),
            ('office', '***REMOVED***'),
            ('link', f'{lnk_base}/UserInformationList(224)'),
            ('userId', '224')])

        for k, v in tag_dict.items():
            if k == 'user':
                continue
            else:
                assert event.find(k).text == v

        for k, v in user_dict.items():
            assert user.find(k).text == v
