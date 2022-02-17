import os
import pytest
import requests
from lxml import etree
from datetime import datetime as dt
from datetime import timedelta
from nexusLIMS import harvesters
from nexusLIMS.harvesters import sharepoint_calendar as sc
from nexusLIMS.utils import nexus_req as _nexus_req, AuthenticationError
from nexusLIMS.harvesters import ReservationEvent
from nexusLIMS.db.session_handler import db_query
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


class TestSharepoint:
    CREDENTIAL_FILE_ABS = os.path.abspath(
        os.path.join(os.path.dirname(harvesters.__file__),
                     '..',
                     'credentials.ini.example'))
    CREDENTIAL_FILE_REL = 'credentials.ini.example'

    @pytest.mark.parametrize('instrument', list(instrument_db.values()),
                             ids=list(instrument_db.keys()))
    def test_downloading_valid_calendars(self, instrument):
        # Handle the two test instruments that we put into the database,
        # which will raise an error because their url values are bogus
        if instrument.name in ['testsurface-CPU_P1111111',
                               'testVDI-VM-JAT-111222']:
            pass
        else:
            if instrument.harvester == "sharepoint_calendar":
                sc.fetch_xml(instrument)

    def test_download_with_date(self):
        doc = etree.fromstring(
            sc.fetch_xml(instrument=instrument_db['FEI-Titan-TEM-635816'],
                         dt_from=dt.fromisoformat('2018-11-13T00:00:00'),
                         dt_to=dt.fromisoformat('2018-11-13T23:59:59')))
        # This day should have one entry:
        assert len(doc.findall('entry')) == 1

    def test_download_date_w_multiple_entries(self):
        # This should return an event by '***REMOVED***' from 1PM to 5PM on 11/20/2019
        doc = etree.fromstring(
            sc.fetch_xml(instrument=instrument_db['FEI-Titan-TEM-635816'],
                         dt_from=dt.fromisoformat('2019-11-20T13:40:20'),
                         dt_to=dt.fromisoformat('2019-11-20T17:30:00'))
        )
        # This day should have one entry (pared down from three):
        assert len(doc.findall('entry')) == 1
        # entry should be user ***REMOVED*** and title "NexusLIMS computer testing"
        assert doc.find('entry/title').text == "NexusLIMS computer testing"
        assert doc.find('entry/link[@title="UserName"]/'
                        'm:inline/feed/entry/content/m:properties/d:UserName',
                        namespaces=doc.nsmap).text == "***REMOVED***"

    def test_downloading_bad_calendar(self):
        with pytest.raises(KeyError):
            sc.fetch_xml('bogus_instr')

    def test_bad_username(self, monkeypatch):
        with monkeypatch.context() as m:
            m.setenv('nexusLIMS_user', 'bad_user')
            with pytest.raises(AuthenticationError):
                sc.fetch_xml(instrument_db['FEI-Titan-TEM-635816'])

    def test_absolute_path_to_credentials(self, monkeypatch):
        from nexusLIMS.utils import get_auth
        with monkeypatch.context() as m:
            # remove environment variable so we get into file processing
            m.delenv('nexusLIMS_user')
            _ = get_auth(self.CREDENTIAL_FILE_ABS)

    def test_relative_path_to_credentials(self, monkeypatch):
        from nexusLIMS.utils import get_auth
        os.chdir(os.path.dirname(__file__))
        with monkeypatch.context() as m:
            # remove environment variable so we get into file processing
            m.delenv('nexusLIMS_user')
            _ = get_auth(self.CREDENTIAL_FILE_REL)

    def test_bad_path_to_credentials(self, monkeypatch):
        from nexusLIMS.utils import get_auth
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

    def test_fetch_xml_only_dt_from(self):
        # at the time of writing this code (2021-09-13), there were 278 records
        # on the Titan STEM after Jan 1. 2020, which should only increase
        # over time
        xml = sc.fetch_xml(instrument_db['FEI-Titan-STEM-630901'],
                           dt_from=dt.fromisoformat('2020-01-01T00:00:00'))
        doc = etree.fromstring(xml)
        assert len(doc.findall('entry')) >= 278

    def test_fetch_xml_only_dt_to(self):
        # There are nine events prior to April 1, 2019 on the Titan STEM
        xml = sc.fetch_xml(instrument_db['FEI-Titan-STEM-630901'],
                           dt_to=dt.fromisoformat('2019-04-01T00:00:00'))
        doc = etree.fromstring(xml)
        assert len(doc.findall('entry')) == 9

    def test_sharepoint_fetch_xml_reservation_event(self):
        xml = \
            sc.fetch_xml(instrument=instrument_db['FEI-Titan-TEM-635816'],
                         dt_from=dt.fromisoformat('2018-11-13T00:00:00'),
                         dt_to=dt.fromisoformat('2018-11-13T23:59:59'))
        cal_event = sc.res_event_from_xml(xml)
        assert cal_event.experiment_title == '***REMOVED***'
        assert cal_event.internal_id == '470'
        assert cal_event.username == '***REMOVED***'
        assert cal_event.start_time == dt.fromisoformat(
            '2018-11-13T09:00:00-05:00')
        assert cal_event.url == 'https://***REMOVED***/Div/' + \
               'msed/MSED-MMF/Lists/FEI%20Titan%20Events/' + \
               'DispForm.aspx/?ID=470'

    def test_sharepoint_fetch_xml_reservation_event_no_entry(self):
        # tests when there is no matching event found
        xml = \
            sc.fetch_xml(instrument=instrument_db['FEI-Titan-TEM-635816'],
                         dt_from=dt.fromisoformat('2010-01-01T00:00:00'),
                         dt_to=dt.fromisoformat('2010-01-01T00:00:01'))
        cal_event = sc.res_event_from_xml(xml)
        assert cal_event.experiment_title is None
        assert cal_event.instrument.name == 'FEI-Titan-TEM-635816'
        assert cal_event.username is None

    def test_sharepoint_res_event_from_session(self):
        from nexusLIMS.db.session_handler import Session
        s = Session(session_identifier="test_identifier",
                    instrument=instrument_db['FEI-Titan-TEM-635816'],
                    dt_from=dt.fromisoformat('2018-11-13T00:00:00'),
                    dt_to=dt.fromisoformat('2018-11-13T23:59:59'),
                    user='unused')
        res_event = sc.res_event_from_session(s)
        assert res_event.experiment_title == '***REMOVED***'
        assert res_event.instrument.name == 'FEI-Titan-TEM-635816'
        assert res_event.internal_id == '470'
        assert res_event.username == '***REMOVED***'
        assert res_event.start_time == dt.fromisoformat(
            '2018-11-13T09:00:00-05:00')

    def test_reservation_event_repr(self):
        s = dt(2020, 8, 20, 12, 0, 0)
        e = dt(2020, 8, 20, 16, 0, 40)
        c = ReservationEvent(experiment_title='Test event',
                             instrument=instrument_db['FEI-Titan-TEM-635816'],
                             last_updated=dt.now(), username='***REMOVED***',
                             created_by='***REMOVED***', start_time=s, end_time=e,
                             reservation_type='category',
                             experiment_purpose='purpose',
                             sample_details='sample details',
                             project_id='projectID',
                             internal_id='999')
        assert c.__repr__() == 'Event for ***REMOVED*** on FEI-Titan-TEM-635816 from ' \
                               '2020-08-20T12:00:00-04:00 to 2020-08-20T' \
                               '16:00:40-04:00'

        c = ReservationEvent()
        assert c.__repr__() == 'No matching calendar event'

        c = ReservationEvent(instrument=instrument_db['FEI-Titan-TEM-635816'])
        assert c.__repr__() == 'No matching calendar event for ' \
                               'FEI-Titan-TEM-635816'

    def test_dump_calendars(self, tmp_path):
        from nexusLIMS.harvesters.sharepoint_calendar import dump_calendars
        f = os.path.join(tmp_path, 'cal_output.xml')
        dump_calendars(instrument='FEI-Titan-TEM-635816', filename=f)
        pass

    def test_division_group_lookup(self):
        from nexusLIMS.harvesters.sharepoint_calendar import get_div_and_group
        div, group = get_div_and_group('***REMOVED***')
        assert div == '641'
        assert group == '02'

    def test_get_events_good_date(self):
        from nexusLIMS.harvesters.sharepoint_calendar import get_events
        events_1 = get_events(instrument='FEI-Titan-TEM-635816',
                              dt_from=dt.fromisoformat('2019-03-13T08:00:00'),
                              dt_to=dt.fromisoformat('2019-03-13T16:00:00'))
        assert events_1.username is None
        assert events_1.created_by == '***REMOVED***'
        assert events_1.experiment_title == '***REMOVED***'

    def test_basic_auth(self):
        from nexusLIMS.utils import get_auth
        res = get_auth(basic=True)
        assert isinstance(res, tuple)

    def test_get_sharepoint_tz(self, monkeypatch):
        assert sc._get_sharepoint_tz() in ['America/New_York',
                                           'America/Chicago',
                                           'America/Denver',
                                           'America/Los_Angeles',
                                           'Pacific/Honolulu']

        # Create a fake response object that will have the right xml (like
        # would be returned if the server were in different time zones)
        class MockResponse(object):
            def __init__(self, text):
                self.text = \
                    """<?xml version="1.0" encoding="utf-8"?>
<feed xml:base="https://***REMOVED***/Div/msed/MSED-MMF/_api/"
      xmlns="http://www.w3.org/2005/Atom"
      xmlns:d="http://schemas.microsoft.com/ado/2007/08/dataservices"
      xmlns:m="http://schemas.microsoft.com/ado/2007/08/dataservices/metadata"
      xmlns:georss="http://www.georss.org/georss"
      xmlns:gml="http://www.opengis.net/gml">
""" + text + "</feed>"

        def mock_get_et(url, req):
            return MockResponse(text="""
            <content type="application/xml">
                <m:properties>
                    <d:Description>(UTC-05:00) Eastern Time (US and 
                    Canada)</d:Description>
                    <d:Id m:type="Edm.Int32">11</d:Id>
                    <d:Information m:type="SP.TimeZoneInformation">
                        <d:Bias m:type="Edm.Int32">360</d:Bias>
                        <d:DaylightBias m:type="Edm.Int32">-60</d:DaylightBias>
                        <d:StandardBias m:type="Edm.Int32">0</d:StandardBias>
                    </d:Information>
                </m:properties>
            </content>
            """)

        def mock_get_ct(url, req):
            return MockResponse(text="""
            <content type="application/xml">
                <m:properties>
                    <d:Description>(UTC-06:00) Central Time (US and 
                    Canada)</d:Description>
                    <d:Id m:type="Edm.Int32">11</d:Id>
                    <d:Information m:type="SP.TimeZoneInformation">
                        <d:Bias m:type="Edm.Int32">360</d:Bias>
                        <d:DaylightBias m:type="Edm.Int32">-60</d:DaylightBias>
                        <d:StandardBias m:type="Edm.Int32">0</d:StandardBias>
                    </d:Information>
                </m:properties>
            </content>
            """)

        def mock_get_mt(url, req):
            return MockResponse(text="""
            <content type="application/xml">
                <m:properties>
                    <d:Description>(UTC-07:00) Mountain Time (US and 
                    Canada)</d:Description>
                    <d:Id m:type="Edm.Int32">12</d:Id>
                    <d:Information m:type="SP.TimeZoneInformation">
                        <d:Bias m:type="Edm.Int32">420</d:Bias>
                        <d:DaylightBias m:type="Edm.Int32">-60</d:DaylightBias>
                        <d:StandardBias m:type="Edm.Int32">0</d:StandardBias>
                    </d:Information>
            </m:properties>
            </content>
            """)

        def mock_get_pt(url, req):
            return MockResponse(text="""
            <content type="application/xml">
                <m:properties>
                    <d:Description>(UTC-08:00) Pacific Time (US and 
                    Canada)</d:Description>
                    <d:Id m:type="Edm.Int32">13</d:Id>
                    <d:Information m:type="SP.TimeZoneInformation">
                        <d:Bias m:type="Edm.Int32">480</d:Bias>
                        <d:DaylightBias m:type="Edm.Int32">-60</d:DaylightBias>
                        <d:StandardBias m:type="Edm.Int32">0</d:StandardBias>
                    </d:Information>
                </m:properties>
            </content>
            """)

        def mock_get_ht(url, req):
            return MockResponse(text="""
            <content type="application/xml">
                <m:properties>
                    <d:Description>(UTC-10:00) Hawaii</d:Description>
                    <d:Id m:type="Edm.Int32">15</d:Id>
                    <d:Information m:type="SP.TimeZoneInformation">
                        <d:Bias m:type="Edm.Int32">600</d:Bias>
                        <d:DaylightBias m:type="Edm.Int32">-60</d:DaylightBias>
                        <d:StandardBias m:type="Edm.Int32">0</d:StandardBias>
                    </d:Information>
                </m:properties>
            </content>
            """)

        monkeypatch.setattr(sc, '_nexus_req', mock_get_et)
        assert sc._get_sharepoint_tz() == 'America/New_York'
        monkeypatch.setattr(sc, '_nexus_req', mock_get_ct)
        assert sc._get_sharepoint_tz() == 'America/Chicago'
        monkeypatch.setattr(sc, '_nexus_req', mock_get_mt)
        assert sc._get_sharepoint_tz() == 'America/Denver'
        monkeypatch.setattr(sc, '_nexus_req', mock_get_pt)
        assert sc._get_sharepoint_tz() == 'America/Los_Angeles'
        monkeypatch.setattr(sc, '_nexus_req', mock_get_ht)
        assert sc._get_sharepoint_tz() == 'Pacific/Honolulu'


class TestNemoIntegration:
    """
    Testing NEMO integration. These tests aren't great since they're not
    general and require a running NEMO server (but we have to test
    integration, and I'm not about to write a whole NEMO installation into
    the test...). All of that is to say that if you want to run these tests
    in a different environment, these tests will have to be rewritten.
    """

    @pytest.fixture
    def nemo_connector(self):
        """
        A NemoConnector instance that can be used for valid tests
        """
        assert 'NEMO_address_1' in os.environ
        assert 'NEMO_token_1' in os.environ
        from nexusLIMS.harvesters.nemo import NemoConnector
        return NemoConnector(base_url=os.getenv('NEMO_address_1'),
                             token=os.getenv('NEMO_token_1'),
                             strftime_fmt=os.getenv('NEMO_strftime_fmt_1'),
                             strptime_fmt=os.getenv('NEMO_strptime_fmt_1'),
                             timezone=os.getenv('NEMO_tz_1'))

    @pytest.fixture
    def bogus_nemo_connector_url(self):
        """
        A NemoConnector with a bad URL and token that should fail
        """
        from nexusLIMS.harvesters.nemo import NemoConnector
        return NemoConnector("https://a_url_that_doesnt_exist/",
                             "notneeded")

    @pytest.fixture
    def bogus_nemo_connector_token(self):
        """
        A NemoConnector with a bad URL and token that should fail
        """
        from nexusLIMS.harvesters.nemo import NemoConnector
        return NemoConnector(os.environ['NEMO_address_1'],
                             "badtokenvalue")

    def test_nemo_connector_repr(self, nemo_connector):
        assert str(nemo_connector) == f"Connection to NEMO API at " \
                                      f"{os.environ['NEMO_address_1']}"

    def test_nemo_multiple_harvesters_enabled(self, monkeypatch):
        monkeypatch.setenv("NEMO_address_2", "https://nemo.address.com/api/")
        monkeypatch.setenv("NEMO_token_2", "sometokenvalue")

        from nexusLIMS.harvesters import nemo
        assert len(nemo.get_harvesters_enabled()) == 2
        assert str(nemo.get_harvesters_enabled()[1]) == \
               f"Connection to NEMO API at " \
               f"{os.environ['NEMO_address_2']}"

    def test_nemo_harvesters_enabled(self):
        from nexusLIMS.harvesters import nemo
        assert len(nemo.get_harvesters_enabled()) >= 1
        assert str(nemo.get_harvesters_enabled()[0]) == \
               f"Connection to NEMO API at " \
               f"{os.environ['NEMO_address_1']}"

    def test_getting_nemo_data(self):
        from nexusLIMS.utils import nexus_req
        from urllib.parse import urljoin
        from requests import get as _get
        r = nexus_req(url=urljoin(os.environ['NEMO_address_1'],
                                  'api/reservations'),
                      fn=_get, token_auth=os.environ['NEMO_token_1'])

    @pytest.mark.parametrize("test_user_id_input,"
                             "expected_usernames",
                             [(3, ["***REMOVED***"]),
                              ([2, 3, 4], ["***REMOVED***", "***REMOVED***", "***REMOVED***"]),
                              (-1, [])])
    def test_get_users(self, nemo_connector, test_user_id_input,
                       expected_usernames):
        users = nemo_connector.get_users(user_id=test_user_id_input)
        # test for the username in each entry, and compare as a set so it's an
        # unordered and deduplicated comparison
        assert set([u['username'] for u in users]) == set(expected_usernames)

    @pytest.mark.parametrize("test_username_input,"
                             "expected_usernames",
                             [('***REMOVED***', ["***REMOVED***"]),
                              (['***REMOVED***', '***REMOVED***', '***REMOVED***'],
                               ["***REMOVED***", "***REMOVED***", "***REMOVED***"]),
                              ('ernst_ruska', [])])
    def test_get_users_by_username(self, nemo_connector,
                                   test_username_input, expected_usernames):
        users = nemo_connector.get_users_by_username(
            username=test_username_input)
        # test for the username in each entry, and compare as a set so it's an
        # unordered and deduplicated comparison
        assert set([u['username'] for u in users]) == set(expected_usernames)

    def test_get_users_memoization(self):
        # to test the memoization of user data, we have to use one instance
        # of NemoConnector rather than a new one from the fixture for each call
        n = harvesters.nemo.NemoConnector(os.environ['NEMO_address_1'],
                                          os.environ['NEMO_token_1'])
        to_test = [(3, ["***REMOVED***"]),
                   ([2, 3, 4], ["***REMOVED***", "***REMOVED***", "***REMOVED***"]),
                   (-1, []),
                   ([2, 3], ["***REMOVED***", "***REMOVED***"]),
                   (2, ["***REMOVED***"])]
        for u_id, expected in to_test:
            users = n.get_users(u_id)
            assert set([u['username'] for u in users]) == set(expected)

    def test_get_users_by_username_memoization(self):
        # to test the memoization of user data, we have to use one instance
        # of NemoConnector rather than a new one from the fixture for each call
        from nexusLIMS.harvesters.nemo import NemoConnector
        n = NemoConnector(os.environ['NEMO_address_1'],
                          os.environ['NEMO_token_1'])
        to_test = [('***REMOVED***', ["***REMOVED***"]),
                   (['***REMOVED***', '***REMOVED***', '***REMOVED***'], ["***REMOVED***", "***REMOVED***", "***REMOVED***"]),
                   ('ernst_ruska', []),
                   (['***REMOVED***', '***REMOVED***'], ['***REMOVED***', '***REMOVED***']),
                   ('***REMOVED***', ['***REMOVED***'])]
        for uname, expected in to_test:
            users = n.get_users_by_username(uname)
            assert set([u['username'] for u in users]) == set(expected)

    def test_get_users_bad_url(self, bogus_nemo_connector_url):
        with pytest.raises(requests.exceptions.ConnectionError):
            bogus_nemo_connector_url.get_users()

    def test_get_users_bad_token(self, bogus_nemo_connector_token):
        with pytest.raises(requests.exceptions.HTTPError) as e:
            bogus_nemo_connector_token.get_users()
        assert "401" in str(e.value)
        assert "Unauthorized" in str(e.value)

    @pytest.mark.parametrize("test_tool_id_input,expected_names",
                             [(1, ["643 Titan (S)TEM (probe corrected)"]),
                              ([1, 15], ["643 Titan (S)TEM (probe corrected)",
                                         "642 JEOL 3010"]),
                              ([1, 15, 3], ["643 Titan (S)TEM (probe "
                                            "corrected)",
                                            "642 JEOL 3010",
                                            "642 FEI Titan"]),
                              (-1, [])])
    def test_get_tools(self, nemo_connector,
                       test_tool_id_input, expected_names):
        tools = nemo_connector.get_tools(test_tool_id_input)
        # test for the tool name in each entry, and compare as a set so it's an
        # unordered and deduplicated comparison
        assert set([t['name'] for t in tools]) == set(expected_names)

    def test_get_tools_memoization(self):
        # to test the memoization of tool data, we have to use one instance
        # of NemoConnector rather than a new one from the fixture for each call
        from nexusLIMS.harvesters.nemo import NemoConnector
        n = NemoConnector(os.environ['NEMO_address_1'],
                          os.environ['NEMO_token_1'])
        to_test = [([1, 15, 3], ["643 Titan (S)TEM (probe corrected)",
                                 "642 JEOL 3010",
                                 "642 FEI Titan"]),
                   (15, ["642 JEOL 3010"]),
                   ([15, 3], ["642 JEOL 3010",
                              "642 FEI Titan"])]
        for t_id, expected in to_test:
            tools = n.get_tools(t_id)
            assert set([t['name'] for t in tools]) == set(expected)

    @pytest.mark.parametrize("test_proj_id_input,expected_names",
                             [(16, ["Test"]),
                              ([13, 14], ["Gaithersburg", "Boulder"]),
                              ([13, 14, 15], ["Gaithersburg", "Boulder",
                                              "ODI"]),
                              (-1, [])])
    def test_get_projects(self, nemo_connector,
                          test_proj_id_input, expected_names):
        proj = nemo_connector.get_projects(test_proj_id_input)
        # test for the project name in each entry, and compare as a set so
        # it's an unordered and deduplicated comparison
        assert set([p['name'] for p in proj]) == set(expected_names)

    def test_get_projects_memoization(self):
        # to test the memoization of project data, we have to use one instance
        # of NemoConnector rather than a new one from the fixture for each call
        from nexusLIMS.harvesters.nemo import NemoConnector
        n = NemoConnector(os.environ['NEMO_address_1'],
                          os.environ['NEMO_token_1'])
        to_test = [([13, 14, 15], ["Gaithersburg", "Boulder", "ODI"]),
                   (16, ["Test"]),
                   ([13, 14], ["Gaithersburg", "Boulder"])]
        for p_id, expected in to_test:
            projects = n.get_projects(p_id)
            assert set([p['name'] for p in projects]) == set(expected)

    def test_get_reservations(self, nemo_connector):
        # not sure best way to test this, but defaults should return at least
        # as many dictionaries as were present on the day these tests were
        # written (Sept. 20, 2021)
        defaults = nemo_connector.get_reservations()
        assert len(defaults) > 10
        assert all([key in defaults[0] for key in ['id', 'question_data',
                                                   'creation_time', 'start',
                                                   'end']])
        assert all([isinstance(d, dict) for d in defaults])

        dt_test = dt.fromisoformat('2021-09-15T00:00:00-06:00')
        date_gte = nemo_connector.get_reservations(dt_from=dt_test)
        assert all([dt.fromisoformat(d['start']) >= dt_test for d in date_gte])

        dt_test = dt.fromisoformat('2021-09-17T23:59:59-06:00')
        date_lte = nemo_connector.get_reservations(dt_to=dt_test)
        assert all([dt.fromisoformat(d['end']) <= dt_test for d in date_lte])

        dt_test_from = dt.fromisoformat('2021-09-15T00:00:00-06:00')
        dt_test_to = dt.fromisoformat('2021-09-17T23:59:59-06:00')
        date_both = nemo_connector.get_reservations(dt_from=dt_test_from,
                                                    dt_to=dt_test_to)
        assert all([
            dt.fromisoformat(d['start']) >= dt_test_from and
            dt.fromisoformat(d['end']) <= dt_test_to
            for d in date_both
        ])

        cancelled = nemo_connector.get_reservations(cancelled=True)
        assert all([d['cancelled'] is True for d in cancelled])

        one_tool = nemo_connector.get_reservations(tool_id=10)
        assert all([d['tool']['id'] == 10 for d in one_tool])

        multi_tool = nemo_connector.get_reservations(tool_id=[15, 10])
        assert all([d['tool']['id'] in [15, 10] for d in multi_tool])

    def test_get_usage_events(self, nemo_connector):
        # not sure best way to test this, but defaults should return at least
        # as many dictionaries as were present on the day these tests were
        # written (Sept. 20, 2021)
        defaults = nemo_connector.get_usage_events()
        assert len(defaults) >= 2
        assert all([key in defaults[0] for key in ['id', 'start', 'end',
                                                   'run_data', 'user',
                                                   'operator', 'project',
                                                   'tool']])
        assert all([isinstance(d, dict) for d in defaults])

        dt_test = dt.fromisoformat('2021-09-01T00:00:00-06:00')
        date_gte = nemo_connector.get_usage_events(dt_from=dt_test)
        assert all([dt.fromisoformat(d['start']) >= dt_test for d in date_gte])

        dt_test = dt.fromisoformat('2021-09-13T23:59:59-06:00')
        date_lte = nemo_connector.get_usage_events(dt_to=dt_test)
        assert all([dt.fromisoformat(d['end']) <= dt_test for d in date_lte])

        dt_test_from = dt.fromisoformat('2021-09-01T12:00:00-06:00')
        dt_test_to = dt.fromisoformat('2021-09-01T23:00:00-06:00')
        date_both = nemo_connector.get_usage_events(dt_from=dt_test_from,
                                                    dt_to=dt_test_to)
        assert all([
            dt.fromisoformat(d['start']) >= dt_test_from and
            dt.fromisoformat(d['end']) <= dt_test_to
            for d in date_both
        ])
        assert len(date_both) == 1

        one_tool = nemo_connector.get_usage_events(tool_id=10)
        assert all([d['tool']['id'] == 10 for d in one_tool])

        multi_tool = nemo_connector.get_usage_events(tool_id=[10, 3])
        assert all([d['tool']['id'] in [10, 3] for d in multi_tool])

        username_test = nemo_connector.get_usage_events(user='***REMOVED***')
        assert all([d['user']['id'] == 3 for d in username_test])

        user_id_test = nemo_connector.get_usage_events(user=3)  # ***REMOVED***
        assert all([d['user']['username'] == '***REMOVED***' for d in user_id_test])

        dt_test_from = dt.fromisoformat('2021-09-01T00:01:00-06:00')
        dt_test_to = dt.fromisoformat('2021-09-02T16:02:00-06:00')
        multiple_test = nemo_connector.get_usage_events(user=3,
                                                        dt_from=dt_test_from,
                                                        dt_to=dt_test_to,
                                                        tool_id=10)
        # should return one usage event
        assert len(multiple_test) == 1
        assert multiple_test[0]['user']['username'] == '***REMOVED***'

        # test event_id
        one_event = nemo_connector.get_usage_events(event_id=29)
        assert len(one_event) == 1
        assert one_event[0]['user']['username'] == '***REMOVED***'

        multi_events = nemo_connector.get_usage_events(event_id=[29, 30])
        assert len(multi_events) == 2

    def test_get_events_no_tool_short_circuit(self, nemo_connector):
        # this test is to make sure we return an empty list faster if the
        # tool requested is not part of what's in our DB
        assert nemo_connector.get_usage_events(tool_id=[-5, -4]) == []

    @pytest.fixture
    def cleanup_session_log(self):
        # this fixture removes the rows for the usage event added in
        # test_usage_event_to_session_log, so it doesn't mess up future
        # record building tests
        yield None
        to_remove = ('https://***REMOVED***/api/usage_events/?id=29',
                     'https://***REMOVED***/api/usage_events/?id=30',
                     'https://***REMOVED***/api/usage_events/?id=31',
                     'https://***REMOVED***/api/usage_events/?id=385031')
        db_query(f'DELETE FROM session_log WHERE session_identifier IN '
                 f'({",".join("?" * len(to_remove))})', to_remove)
        pass

    def test_add_all_usage_events_to_db(self, cleanup_session_log):
        success_before, results_before = db_query('SELECT * FROM session_log;')
        from nexusLIMS.harvesters import nemo
        # currently, this only adds instruments from the test tool on
        # ***REMOVED***
        nemo.add_all_usage_events_to_db(tool_id=10)
        success_after, results_after = db_query('SELECT * FROM session_log;')

    def test_usage_event_to_session_log(self,
                                        nemo_connector,
                                        cleanup_session_log):
        success_before, results_before = db_query('SELECT * FROM session_log;')
        nemo_connector.write_usage_event_to_session_log(30)
        success_after, results_after = db_query('SELECT * FROM session_log;')
        assert len(results_after) - len(results_before) == 2

        success, results = db_query('SELECT * FROM session_log ORDER BY '
                                    'id_session_log DESC LIMIT 2;')
        # session ids are same:
        assert results[0][1] == results[1][1]
        assert results[0][1].endswith("/api/usage_events/?id=30")
        # record status
        assert results[0][5] == 'TO_BE_BUILT'
        assert results[1][5] == 'TO_BE_BUILT'
        # event type
        assert results[0][4] == 'END'
        assert results[1][4] == 'START'

    def test_nemo_dot_gov_usage_event_to_session_log(self,
                                                     cleanup_session_log):
        from nexusLIMS.harvesters import nemo
        # if ***REMOVED*** connector is enabled by environment variables,
        # run a test on the format of the resulting timestamps in the DB
        try:
            n = nemo.get_connector_by_base_url('***REMOVED***')
            success_before, results_before = db_query(
                'SELECT * FROM session_log;')
            n.write_usage_event_to_session_log(385031)
            success_after, results_after = db_query(
                'SELECT * FROM session_log;')
            assert len(results_after) - len(results_before) == 2

            success, results = db_query('SELECT * FROM session_log ORDER BY '
                                        'id_session_log DESC LIMIT 2;')
            # session ids are same:
            assert results[0][1] == results[1][1]
            assert results[0][1].endswith("/api/usage_events/?id=385031")
            # record status
            assert results[0][5] == 'TO_BE_BUILT'
            assert results[1][5] == 'TO_BE_BUILT'
            # event type
            assert results[0][4] == 'END'
            assert results[1][4] == 'START'

            # convert from isoformat and check dates to make sure we put
            # things in the right format
            import pytz
            end_dt = dt.fromisoformat(results[0][3])
            start_dt = dt.fromisoformat(results[1][3])
            assert end_dt == pytz.timezone('America/New_York').localize(
                dt(2022, 2, 10, 16, 4, 1))
            assert start_dt == pytz.timezone('America/New_York').localize(
                dt(2022, 2, 10, 14, 10, 45))

        except LookupError:  # pragma: no cover
            pytest.skip("***REMOVED*** harvester not enabled")

    def test_get_connector_by_base_url(self):
        from nexusLIMS.harvesters import nemo
        with pytest.raises(LookupError):
            nemo.get_connector_by_base_url('bogus_connector')

    def test_usage_event_to_session_log_non_existent_event(self,
                                                           caplog,
                                                           nemo_connector):
        success_before, results_before = db_query('SELECT * FROM session_log;')
        nemo_connector.write_usage_event_to_session_log(0)
        success_after, results_after = db_query('SELECT * FROM session_log;')
        assert 'No usage event with id = 0 was found' in caplog.text
        assert 'WARNING' in caplog.text
        assert len(results_after) == len(results_before)

    def test_usage_event_to_session(self, nemo_connector):
        session = nemo_connector.get_session_from_usage_event(30)
        assert session.dt_from == \
               dt.fromisoformat('2021-09-05T13:57:00.000000-06:00')
        assert session.dt_to == \
               dt.fromisoformat('2021-09-05T17:00:00.000000-06:00')
        assert session.user == '***REMOVED***'
        assert session.instrument == instrument_db['testsurface-CPU_P1111111']

    def test_usage_event_to_session_non_existent_event(self,
                                                       caplog,
                                                       nemo_connector):
        session = nemo_connector.get_session_from_usage_event(0)
        assert 'No usage event with id = 0 was found' in caplog.text
        assert 'WARNING' in caplog.text
        assert session is None

    def test_res_event_from_session(self):
        from nexusLIMS.db.session_handler import Session
        from nexusLIMS.harvesters import nemo
        s = Session('test_matching_reservation',
                    instrument_db['testsurface-CPU_P1111111'],
                    dt.fromisoformat('2021-08-02T11:00:00-06:00'),
                    dt.fromisoformat('2021-08-02T16:00:00-06:00'),
                    user='***REMOVED***')
        res_event = nemo.res_event_from_session(s)
        assert res_event.instrument == instrument_db['testsurface-CPU_P1111111']
        assert res_event.experiment_title == '***REMOVED***'
        assert res_event.experiment_purpose == \
               '***REMOVED*** ***REMOVED*** ' \
               '***REMOVED***.'
        assert res_event.sample_name[0] == "***REMOVED***'s ***REMOVED***"
        assert res_event.project_id[0] is None
        assert res_event.username == '***REMOVED***'
        assert res_event.internal_id == '187'
        assert res_event.url == \
               'https://***REMOVED***/event_details/reservation/187/'

    def test_res_event_from_session_no_matching_sessions(self):
        from nexusLIMS.db.session_handler import Session
        from nexusLIMS.harvesters import nemo
        s = Session('test_no_reservations',
                    instrument_db['FEI-Titan-TEM-635816_n'],
                    dt.fromisoformat('2021-08-10T15:00:00-06:00'),
                    dt.fromisoformat('2021-08-10T16:00:00-06:00'),
                    user='***REMOVED***')
        res_event = nemo.res_event_from_session(s)
        assert res_event.username == '***REMOVED***'
        assert res_event.start_time == dt.fromisoformat(
            '2021-08-10T15:00:00-06:00')
        assert res_event.end_time == dt.fromisoformat(
            '2021-08-10T16:00:00-06:00')

    def test_res_event_from_session_no_overlapping_sessions(self):
        from nexusLIMS.db.session_handler import Session
        from nexusLIMS.harvesters import nemo
        s = Session('test_no_reservations',
                    instrument_db['testsurface-CPU_P1111111'],
                    dt.fromisoformat('2021-08-05T15:00:00-06:00'),
                    dt.fromisoformat('2021-08-05T16:00:00-06:00'),
                    user='***REMOVED***')
        res_event = nemo.res_event_from_session(s)
        assert res_event.username == '***REMOVED***'
        assert res_event.start_time == dt.fromisoformat(
            '2021-08-05T15:00:00-06:00')
        assert res_event.end_time == dt.fromisoformat(
            '2021-08-05T16:00:00-06:00')

    def test_no_connector_for_session(self):
        from nexusLIMS.db.session_handler import Session
        from nexusLIMS.instruments import Instrument
        from nexusLIMS.harvesters import nemo
        s = Session('test_no_reservations',
                    Instrument(name='Dummy instrument'),
                    dt.fromisoformat('2021-08-05T15:00:00-06:00'),
                    dt.fromisoformat('2021-08-05T16:00:00-06:00'),
                    user='***REMOVED***')
        with pytest.raises(LookupError) as e:
            nemo.get_connector_for_session(s)

        assert "Did not find enabled NEMO harvester for " \
               "\"Dummy instrument\"" in str(e.value)

    def test_bad_res_question_value(self, nemo_connector):
        from nexusLIMS.harvesters import nemo
        dt_from = dt.fromisoformat('2021-08-02T00:00:00-06:00')
        dt_to = dt.fromisoformat('2021-08-03T00:00:00-06:00')
        res = nemo_connector.get_reservations(tool_id=10,
                                              dt_from=dt_from, dt_to=dt_to)[0]
        val = nemo._get_res_question_value('bad_value', res)
        assert val is None

    def test_no_res_questions(self, nemo_connector):
        from nexusLIMS.harvesters import nemo
        dt_from = dt.fromisoformat('2021-08-03T00:00:00-06:00')
        dt_to = dt.fromisoformat('2021-08-04T00:00:00-06:00')
        res = nemo_connector.get_reservations(tool_id=10,
                                              dt_from=dt_from, dt_to=dt_to)[0]
        val = nemo._get_res_question_value('project_id', res)
        assert val is None

    def test_bad_id_from_url(self):
        from nexusLIMS.harvesters import nemo
        this_id = nemo.id_from_url('https://test.com/?notid=4')
        assert this_id is None

    def test_process_res_question_samples(self):
        from nexusLIMS.harvesters.nemo import _process_res_question_samples
        # use a mocked reservation API response for testing of processing
        r = {
            'id': 140,
            'question_data': {
                'project_id': {'user_input': 'NexusLIMS'},
                'experiment_title': {'user_input': 'A test with multiple '
                                                   'samples'},
                'experiment_purpose': {'user_input': 'To test the harvester '
                                                     'with multiple samples'},
                'data_consent': {'user_input': 'Agree'},
                'sample_group': {
                    'user_input': {
                        '0': {
                            'sample_name': 'sample_pid_1',
                            'sample_or_pid': 'PID',
                            'sample_details': 'A sample with a PID and some '
                                              'more details'
                        },
                        '1': {
                            'sample_name': 'sample name 1',
                            'sample_or_pid': 'Sample Name',
                            'sample_details': 'A sample with a name and some '
                                              'additional detail'},
                        '2': {
                            'sample_name': 'sample_pid_2',
                            'sample_or_pid': 'PID',
                            'sample_details': ''},
                        '3': {
                            'sample_name': 'sample name 2',
                            'sample_or_pid': 'Sample Name',
                            'sample_details': ''}
                    }}},
            'creation_time': '2021-11-29T10:38:00-07:00',
            'start': '2021-11-29T10:00:00-07:00',
            'end': '2021-11-29T12:00:00-07:00',
            'title': ''
        }
        details, pid, name = _process_res_question_samples(r)
        assert details == ['A sample with a PID and some more details',
                           'A sample with a name and some additional detail',
                           None, None]
        assert pid == ['sample_pid_1', None, 'sample_pid_2', None]
        assert name == [None, 'sample name 1', None, 'sample name 2']

        # set some of the sample_or_pid values to something bogus to make
        # sure name and pid get set to None
        for i in range(4):
            r['question_data']['sample_group'][
                'user_input'][str(i)]['sample_or_pid'] = 'bogus'

        details, pid, name = _process_res_question_samples(r)
        assert details == ['A sample with a PID and some more details',
                           'A sample with a name and some additional detail',
                           None, None]
        assert pid == [None, None, None, None]
        assert name == [None, None, None, None]

    def test_get_tool_ids(self, nemo_connector):
        tool_ids = nemo_connector.get_known_tool_ids()
        for t_id in [1, 3, 4, 5, 6, 7, 8, 9, 10, 15]:
            assert t_id in tool_ids

    def test_no_consent_no_questions(self, nemo_connector):
        from nexusLIMS.db.session_handler import Session
        from nexusLIMS.harvesters import nemo

        # should match https://***REMOVED***/api/reservations/?id=188
        s = Session(session_identifier='blah-blah',
                    instrument=instrument_db['testsurface-CPU_P1111111'],
                    dt_from=dt.fromisoformat('2021-08-03T10:00-06:00'),
                    dt_to=dt.fromisoformat('2021-08-03T17:00-06:00'),
                    user='***REMOVED***')
        with pytest.raises(nemo.NoDataConsentException) as e:
            nemo.res_event_from_session(s)
        assert 'did not have data_consent defined, so we should not harvest' \
               in str(e.value)

    def test_no_consent_user_disagree(self, nemo_connector):
        from nexusLIMS.db.session_handler import Session
        from nexusLIMS.harvesters import nemo

        # should match https://***REMOVED***/api/reservations/?id=189
        s = Session(session_identifier='blah-blah',
                    instrument=instrument_db['testsurface-CPU_P1111111'],
                    dt_from=dt.fromisoformat('2021-08-04T10:00-06:00'),
                    dt_to=dt.fromisoformat('2021-08-04T17:00-06:00'),
                    user='***REMOVED***')
        with pytest.raises(nemo.NoDataConsentException) as e:
            nemo.res_event_from_session(s)
        assert 'requested not to have their data harvested' \
               in str(e.value)

    def test_usage_event_not_yet_ended(self,
                                       nemo_connector,
                                       monkeypatch,
                                       caplog):
        # we need to test nemo.write_usage_event_to_session_log does not write
        # anything to the database in the event a usage event is in progress.
        # to do so, we will mock nemo.NemoConnector.get_usage_events to return
        # a predefined list of our making
        our_dict = \
            {
                'id': 0,
                'start': '2022-01-12T11:44:25.384309-05:00',
                'end': None,
                'tool': {'id': 8, 'name': '643 FEI Quanta 200 (ESEM)'}
            }
        monkeypatch.setattr(nemo_connector, 'get_usage_events',
                            lambda event_id: [our_dict])

        success_before, results_before = db_query('SELECT * FROM session_log;')
        nemo_connector.write_usage_event_to_session_log(event_id=0)
        success_after, results_after = db_query('SELECT * FROM session_log;')

        # make sure warning was logged
        assert "Usage event 0 has not yet ended" in caplog.text

        # number of session logs should be identical before and after call
        assert len(results_before) == len(results_after)

    def test_connector_strftime(self):
        """
        Test the conversion of datetime objects to strings according to a
        connector's settings.
        """
        from nexusLIMS.harvesters.nemo import NemoConnector
        from pytz import timezone

        ny = timezone('America/New_York')
        date_no_ms = dt(2022, 2, 16, 9, 39, 0, 0)
        date_w_ms = dt(2022, 2, 16, 9, 39, 0, 1)
        date_no_ms_tz = ny.localize(date_no_ms)
        date_w_ms_tz = ny.localize(date_w_ms)

        # test with no format settings (isoformat)
        c = NemoConnector(base_url='https://example.org',
                          token='not_needed')
        assert c.strftime(date_no_ms) == '2022-02-16T09:39:00'
        assert c.strftime(date_w_ms) == '2022-02-16T09:39:00.000001'
        assert c.strftime(date_no_ms_tz) == '2022-02-16T09:39:00-05:00'
        assert c.strftime(date_w_ms_tz) == '2022-02-16T09:39:00.000001-05:00'

        # test a few custom formats
        c = NemoConnector(base_url='https://example.org',
                          token='not_needed',
                          strftime_fmt='%Y-%m-%dT%H:%M:%S%z')
        assert c.strftime(date_no_ms) == '2022-02-16T09:39:00-0700'
        assert c.strftime(date_w_ms) == '2022-02-16T09:39:00-0700'
        assert c.strftime(date_no_ms_tz) == '2022-02-16T09:39:00-0500'
        assert c.strftime(date_w_ms_tz) == '2022-02-16T09:39:00-0500'

        # test %z in strftime_fmt for naive datetime with self.timezone set
        c = NemoConnector(base_url='https://example.org',
                          token='not_needed',
                          strftime_fmt='%Y-%m-%dT%H:%M:%S%z',
                          timezone='America/New_York')
        assert c.strftime(dt(2022, 2, 16, 23, 6, 12, 50, tzinfo=None)) == \
            '2022-02-16T23:06:12-0500'

    def test_connector_strptime(self):
        """
        Test the conversion of string to datetime objects according
        to a connector's settings.
        """
        from nexusLIMS.harvesters.nemo import NemoConnector
        from pytz import timezone

        ny = timezone('America/New_York')
        datestr_no_ms = '2022-02-16T09:39:00'
        datestr_w_ms = '2022-02-16T09:39:00.000001'
        datestr_no_ms_tz = '2022-02-16T09:39:00-05:00'
        datestr_w_ms_tz = '2022-02-16T09:39:00.000001-05:00'
        date_no_ms = dt(2022, 2, 16, 9, 39, 0, 0)
        date_w_ms = dt(2022, 2, 16, 9, 39, 0, 1)
        date_no_ms_tz = ny.localize(date_no_ms)
        date_w_ms_tz = ny.localize(date_w_ms)

        # test with no format settings (isoformat)
        c = NemoConnector(base_url='https://example.org', token='not_needed')
        assert c.strptime(datestr_no_ms) == date_no_ms
        assert c.strptime(datestr_w_ms) == date_w_ms
        assert c.strptime(datestr_no_ms_tz) == date_no_ms_tz
        assert c.strptime(datestr_w_ms_tz) == date_w_ms_tz

        # test "iso-like" formats w/ and w/o timezone
        c = NemoConnector(base_url='https://example.org', token='not_needed',
                          strptime_fmt='%Y-%m-%dT%H:%M:%S')
        c_tz = NemoConnector(base_url='https://example.org', token='not_needed',
                             strptime_fmt='%Y-%m-%dT%H:%M:%S%z')

        datestr_no_ms = '2022-02-16T09:39:00'
        datestr_w_ms = '2022-02-16T09:39:00.000001'
        datestr_no_ms_tz = '2022-02-16T09:39:00-05:00'
        datestr_w_ms_tz = '2022-02-16T09:39:00.000001-05:00'

        assert c.strptime(datestr_no_ms) == date_no_ms
        with pytest.raises(ValueError):  # should error since our fmt has no ms
            assert c.strptime(datestr_w_ms) == date_w_ms
        with pytest.raises(ValueError):  # should error since our fmt has no TZ
            assert c.strptime(datestr_no_ms_tz) == date_no_ms_tz
        with pytest.raises(ValueError):  # should error since our fmt has no TZ
            assert c.strptime(datestr_w_ms_tz) == date_w_ms_tz

        with pytest.raises(ValueError):  # should error since fmt expects TZ
            assert c_tz.strptime(datestr_no_ms) == date_no_ms
        with pytest.raises(ValueError):  # should error since our fmt has no ms
            assert c_tz.strptime(datestr_w_ms) == date_w_ms
        assert c_tz.strptime(datestr_no_ms_tz) == date_no_ms_tz
        with pytest.raises(ValueError):  # should error since our fmt has no ms
            assert c_tz.strptime(datestr_w_ms_tz) == date_w_ms_tz

        # test format seen on ***REMOVED***
        c2 = NemoConnector(base_url='https://example.org', token='not_needed',
                           strptime_fmt='%m-%d-%Y %H:%M:%S')
        datestr_no_ms = '02-16-2022 09:39:00'
        date_no_ms = dt(2022, 2, 16, 9, 39, 0, 0)
        assert c2.strptime(datestr_no_ms) == date_no_ms

        # test format seen on ***REMOVED*** coerced to timezone
        c3 = NemoConnector(base_url='https://example.org', token='not_needed',
                           strptime_fmt='%m-%d-%Y %H:%M:%S',
                           timezone='America/New_York')
        datestr_no_ms = '02-16-2022 09:39:00'
        assert c3.strptime(datestr_no_ms) == date_no_ms_tz

        # test format with timezone coerced to different timezone (this will
        # keep the time the same, but switch the timezone to whatever
        # specified without adjusting the time)
        c4 = NemoConnector(base_url='https://example.org', token='not_needed',
                           strptime_fmt='%Y-%m-%dT%H:%M:%S%z',
                           timezone='America/Denver')
        # input is 9AM in Eastern time
        datestr_no_ms_tz = '2022-02-16T09:39:00-05:00'
        # result will be 9AM MT, so 2 hours past date_no_ms_tz (which is
        # 9AM ET)
        assert c4.strptime(datestr_no_ms_tz) == \
               date_no_ms_tz + timedelta(hours=2)
        assert c4.strptime(datestr_no_ms_tz) == \
               dt.fromisoformat('2022-02-16T09:39:00-07:00')


class TestReservationEvent:
    def test_full_reservation_constructor(self):
        res_event = ReservationEvent(
            experiment_title="A test title",
            instrument=instrument_db['FEI-Titan-TEM-635816'],
            last_updated=dt.fromisoformat("2021-09-15T16:04:00"),
            username='***REMOVED***', created_by='***REMOVED***',
            start_time=dt.fromisoformat("2021-09-15T03:00:00"),
            end_time=dt.fromisoformat("2021-09-15T16:00:00"),
            reservation_type="A test event",
            experiment_purpose="To test the constructor",
            sample_details=["A sample that was loaded into a microscope for "
                            "testing"],
            sample_pid=["***REMOVED***.5"],
            sample_name=["The test sample"],
            project_name=["NexusLIMS"], project_id=["***REMOVED***.1.5"],
            project_ref=["https://www.example.org"], internal_id="42308",
            division="641", group="00"
        )

        xml = res_event.as_xml()
        assert xml.find('title').text == "A test title"
        assert xml.find('id').text == "42308"
        assert xml.find('summary/experimenter').text == "***REMOVED***"
        assert xml.find('summary/instrument').text == "FEI Titan TEM"
        assert xml.find('summary/instrument').get("pid") == \
               "FEI-Titan-TEM-635816"
        assert xml.find('summary/reservationStart').text == \
               "2021-09-15T03:00:00-04:00"
        assert xml.find('summary/reservationEnd').text == "2021-09-15T" \
                                                          "16:00:00-04:00"
        assert xml.find('summary/motivation').text == "To test the constructor"
        assert xml.find('sample').get("ref") == "***REMOVED***.5"
        assert xml.find('sample/name').text == "The test sample"
        assert xml.find('sample/description').text == \
               "A sample that was loaded into a microscope for testing"
        assert xml.find('project/name').text == "NexusLIMS"
        assert xml.find('project/division').text == "641"
        assert xml.find('project/group').text == "00"
        assert xml.find('project/project_id').text == "***REMOVED***.1.5"
        assert xml.find('project/ref').text == "https://www.example.org"

    def test_full_reservation_constructor_instr_none(self):
        res_event = ReservationEvent(
            experiment_title="A test title for no instrument",
            instrument=None,
            last_updated=dt.fromisoformat("2021-09-15T16:04:00"),
            username='***REMOVED***', created_by='***REMOVED***',
            start_time=dt.fromisoformat("2021-09-15T03:00:00"),
            end_time=dt.fromisoformat("2021-09-15T16:00:00"),
            reservation_type="A test event",
            experiment_purpose="To test the constructor again",
            sample_details=["A sample that was loaded into a microscope for "
                            "testing again"],
            sample_pid=["***REMOVED***.6"],
            sample_name=["The test sample again"],
            project_name=["NexusLIMS!"], project_id=["***REMOVED***.1.6"],
            project_ref=["https://www.example.org"], internal_id="42309",
            division="641", group="00"
        )
        xml = res_event.as_xml()
        assert xml.find('title').text == "A test title for no instrument"
        assert xml.find('id').text == "42309"
        assert xml.find('summary/experimenter').text == "***REMOVED***"
        assert xml.find('summary/reservationStart').text == \
               "2021-09-15T03:00:00"
        assert xml.find('summary/reservationEnd').text == "2021-09-15T" \
                                                          "16:00:00"
        assert xml.find('summary/motivation').text == "To test the " \
                                                      "constructor again"
        assert xml.find('sample').get("ref") == "***REMOVED***.6"
        assert xml.find('sample/name').text == "The test sample again"
        assert xml.find('sample/description').text == \
               "A sample that was loaded into a microscope for testing again"
        assert xml.find('project/name').text == "NexusLIMS!"
        assert xml.find('project/division').text == "641"
        assert xml.find('project/group').text == "00"
        assert xml.find('project/project_id').text == "***REMOVED***.1.6"
        assert xml.find('project/ref').text == "https://www.example.org"

    def test_res_event_without_title(self):
        res_event = ReservationEvent(
            experiment_title=None,
            instrument=instrument_db['FEI-Titan-TEM-635816'],
            last_updated=dt.fromisoformat("2021-09-15T16:04:00"),
            username='***REMOVED***', created_by='***REMOVED***',
            start_time=dt.fromisoformat("2021-09-15T04:00:00"),
            end_time=dt.fromisoformat("2021-09-15T17:00:00"),
            reservation_type="A test event",
            experiment_purpose="To test a reservation with no title",
            sample_details=["A sample that was loaded into a microscope for "
                            "testing"],
            sample_pid=["***REMOVED***.6"],
            sample_name=["The test sample name"],
            project_name=["NexusLIMS"], project_id=["***REMOVED***.1.6"],
            project_ref=["https://www.example.org"], internal_id="48328",
            division="641", group="00"
        )

        xml = res_event.as_xml()
        assert xml.find('title').text == "Experiment on the FEI Titan TEM on " \
                                         "Wednesday Sep. 15, 2021"
        assert xml.find('id').text == "48328"
        assert xml.find('summary/experimenter').text == "***REMOVED***"
        assert xml.find('summary/instrument').text == "FEI Titan TEM"
        assert xml.find('summary/instrument').get("pid") == \
               "FEI-Titan-TEM-635816"
        assert xml.find('summary/reservationStart').text == \
               "2021-09-15T04:00:00-04:00"
        assert xml.find('summary/reservationEnd').text == "2021-09-15T" \
                                                          "17:00:00-04:00"
        assert xml.find('summary/motivation').text == "To test a reservation " \
                                                      "with no title"
        assert xml.find('sample').get("ref") == "***REMOVED***.6"
        assert xml.find('sample/name').text == "The test sample name"
        assert xml.find('sample/description').text == \
               "A sample that was loaded into a microscope for testing"
        assert xml.find('project/name').text == "NexusLIMS"
        assert xml.find('project/division').text == "641"
        assert xml.find('project/group').text == "00"
        assert xml.find('project/project_id').text == "***REMOVED***.1.6"
        assert xml.find('project/ref').text == "https://www.example.org"

    def test_check_arg_lists(self):
        ReservationEvent(
            sample_details=["A sample that was loaded into a microscope for "
                            "testing"],
            sample_pid=["***REMOVED***.6"],
            sample_name=["The test sample name"])
        with pytest.raises(ValueError) as e:
            ReservationEvent(
                sample_details=["detail 1", "detail 2"],
                sample_pid=["***REMOVED***.6"],
                sample_name=["sample_name1", "sample_name2", "sample_name3"])
        assert 'Length of sample arguments must be the same' in str(e.value)

        with pytest.raises(ValueError) as e:
            ReservationEvent(
                sample_details=["detail 1"],
                sample_pid=["***REMOVED***.6"],
                sample_name=["sample_name1", "sample_name2", "sample_name3"])
        assert 'Length of sample arguments must be the same' in str(e.value)

        with pytest.raises(ValueError) as e:
            ReservationEvent(
                project_ref=["ref 1", "ref 2"],
                project_id=["***REMOVED***.6"],
                project_name=["project_name1", "project_name2",
                              "project_name3"])
        assert 'Length of project arguments must be the same' in str(e.value)
