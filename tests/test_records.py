import os
from functools import partial
import shutil

from nexusLIMS import cdcs
from nexusLIMS.instruments import instrument_db
from nexusLIMS.builder import record_builder as _rb
from nexusLIMS.schemas import activity
from nexusLIMS.db import session_handler
from nexusLIMS.db import make_db_query
from nexusLIMS.db.session_handler import db_query as dbq
from collections import namedtuple
from glob import glob
from lxml import etree as et
from uuid import uuid4
from datetime import datetime as _dt
from datetime import timedelta as _td
from .utils import files
from nexusLIMS.utils import AuthenticationError
from nexusLIMS.harvesters import nemo
import pytest


class TestRecordBuilder:

    @pytest.fixture()
    def remove_nemo_gov_harvester(self, monkeypatch):
        """
        Helper fixture to remove the ***REMOVED*** harvester from the
        environment if it's present, since it has _a lot_ of usage events,
        and takes a long time to fetch from the API with the current set of
        tests.
        """
        nemo_var = None
        for k in os.environ:
            if '***REMOVED***/api' in os.getenv(k) and 'address' in k:
                nemo_var = k

        if nemo_var:
            monkeypatch.delenv(nemo_var, raising=False)
            monkeypatch.delenv(nemo_var.replace('address', 'token'),
                               raising=False)
            monkeypatch.delenv(nemo_var.replace('address', 'strftime_fmt'),
                               raising=False)
            monkeypatch.delenv(nemo_var.replace('address', 'strptime_fmt'),
                               raising=False)
            monkeypatch.delenv(nemo_var.replace('address', 'tz'),
                               raising=False)
            yield
            monkeypatch.undo()

    # have to do these before modifying the database with the actual run tests
    @pytest.mark.skip(
        reason="no way of currently testing SharePoint with current "
               "deployment environment; SP harvesting is deprecated")
    def test_dry_run_sharepoint_calendar(self):   # pragma: no cover
        sessions = session_handler.get_sessions_to_build()
        cal_event = _rb.dry_run_get_sharepoint_reservation_event(sessions[0])
        assert cal_event.project_name[0] == '642.03.??'
        assert cal_event.username == '***REMOVED***'
        assert cal_event.experiment_title == 'Looking for Nickel Alloys'
        assert cal_event.start_time == _dt.fromisoformat(
            '2019-09-06T16:30:00-04:00')

    def test_dry_run_file_find(self, fix_mountain_time,
                               remove_nemo_gov_harvester):
        sessions = session_handler.get_sessions_to_build()
        # add at least one NEMO session to the file find (one is already in the
        # test database, but this get_usage_events_as_sessions call will add
        # two, including one with no files)
        sessions += nemo.get_usage_events_as_sessions(
            dt_from=_dt.fromisoformat('2021-08-02T00:00:00-04:00'),
            dt_to=_dt.fromisoformat('2021-08-03T00:00:00-04:00'))
        sessions += nemo.get_usage_events_as_sessions(
            dt_from=_dt.fromisoformat('2021-09-01T00:00:00-04:00'),
            dt_to=_dt.fromisoformat('2021-09-02T00:00:00-04:00'))
        # removal of SharePoint sessions from testing
        correct_files_per_session = [28, 37, 38, 55, 0, 18, 4, 4, 0]
        file_list_list = []
        for s, ans in zip(sessions, correct_files_per_session):
            found_files = _rb.dry_run_file_find(s)
            file_list_list.append(found_files)
            # noinspection PyTypeChecker
            assert len(found_files) == ans

        assert os.path.join(os.environ["mmfnexus_path"], 
                            'Titan/***REMOVED***/200204 - ***REMOVED*** - '
                            '***REMOVED*** - Titan/15 - 620k.dm3') \
                                in file_list_list[5]

        # file from NEMO session
        assert os.path.join(os.environ["mmfnexus_path"], 
                            'NexusLIMS/test_files/02 - 620k-2.dm3') \
                                in file_list_list[-2]

    def test_process_new_records_dry_run(self, remove_nemo_gov_harvester):
        # just running to ensure coverage, tests are included above
        _rb.process_new_records(dry_run=True,
                                dt_to=_dt.fromisoformat(
                                    '2021-08-03T00:00:00-04:00'))

    def test_process_new_records_dry_run_no_sessions(self,
                                                     remove_nemo_gov_harvester,
                                                     monkeypatch, caplog):
        monkeypatch.setattr(_rb, '_get_sessions', lambda: [])
        # there shouldn't be any MARLIN sessions before July 1, 2017
        _rb.process_new_records(dry_run=True,
                                dt_to=_dt.fromisoformat(
                                    '2017-07-01T00:00:00-04:00'))
        assert "No 'TO_BE_BUILT' sessions were found. Exiting." in caplog.text

    def test_process_new_records_no_files_warning(self,
                                                  remove_nemo_gov_harvester,
                                                  monkeypatch, caplog,
                                                  cleanup_session_log):
        from nexusLIMS.db.session_handler import Session
        # overload "_get_sessions" to return just one session
        dt_str_from = '2019-09-06T17:00:00.000-06:00'
        dt_str_to = '2019-09-06T18:00:00.000-06:00'
        monkeypatch.setattr(_rb, '_get_sessions', lambda: [
            Session(session_identifier='test_session',
                    instrument=instrument_db['testsurface-CPU_P1111111'],
                    dt_from=_dt.fromisoformat(dt_str_from),
                    dt_to=_dt.fromisoformat(dt_str_to),
                    user='test')
        ])
        _rb.process_new_records(dry_run=False,
                                dt_to=_dt.fromisoformat(
                                    '2021-07-01T00:00:00-04:00'))
        assert "No files found in " in caplog.text

    @pytest.fixture()
    def add_recent_test_session(self, request, monkeypatch):
        # insert a dummy session to DB that was within past day so it gets
        # skipped (we assume no files are being regularly added into the test
        # instrument folder)

        # the ``request.param`` parameter controls whether the timestamps have
        # timezones attached
        from nexusLIMS.db.session_handler import SessionLog, Session
        from nexusLIMS.harvesters import ReservationEvent

        if request.param:
            start_ts = _dt.now() - _td(days=1)
            end_ts = _dt.now() - _td(days=0.5)
        else:
            start_ts = _dt.now().astimezone() - _td(days=1)
            end_ts = _dt.now().astimezone() - _td(days=0.5)
        start = SessionLog(session_identifier='test_session',
                           instrument='FEI-Titan-TEM-635816_n',
                           timestamp=start_ts.isoformat(),
                           event_type='START', user='test',
                           record_status='TO_BE_BUILT')
        start.insert_log()
        end = SessionLog(session_identifier='test_session',
                         instrument='FEI-Titan-TEM-635816_n',
                         timestamp=end_ts.isoformat(),
                         event_type='END', user='test',
                         record_status='TO_BE_BUILT')
        end.insert_log()

        s = Session(session_identifier='test_session',
                    instrument=instrument_db['FEI-Titan-TEM-635816_n'],
                    dt_from=start_ts, dt_to=end_ts, user='test')
        # return just our session of interest to build and disable nemo
        # harvester's add_all_usage_events_to_db method
        monkeypatch.setattr(_rb, '_get_sessions', lambda: [s])
        monkeypatch.setattr(_rb._nemo, 'add_all_usage_events_to_db',
                            lambda dt_from, dt_to: None)
        monkeypatch.setattr(
            _rb._nemo, 'res_event_from_session',
            lambda session:
                ReservationEvent(experiment_title='test',
                                 instrument=session.instrument,
                                 username='test',
                                 start_time=session.dt_from,
                                 end_time=session.dt_to))

    # this parametrize call provides "request.param" with values of True and
    # then False to the add_recent_test_session fixture, which is used to
    # test both timezone-aware and timezone-naive delay implementations
    # (see https://stackoverflow.com/a/36087408)
    @pytest.mark.parametrize('add_recent_test_session', [True, False],
                             indirect=True)
    def test_process_new_records_within_delay(self,
                                              add_recent_test_session,
                                              remove_nemo_gov_harvester,
                                              monkeypatch, caplog,
                                              cleanup_session_log):
        _rb.process_new_records(dry_run=False)
        assert "Configured record building delay has not passed; " \
               "Removing previously inserted RECORD_GENERATION " in caplog.text

        _, res = dbq("SELECT * FROM session_log WHERE session_identifier = ?",
                     ("test_session", ))
        assert res[0][5] == 'TO_BE_BUILT'
        assert res[1][5] == 'TO_BE_BUILT'
        assert len(res) == 2

    def test_process_new_nemo_record_with_no_reservation(
            self, remove_nemo_gov_harvester, monkeypatch,
            caplog, cleanup_session_log):
        """
        This test method tests building a record from a NEMO instrument with
        no matching reservation; should result in "COMPLETED" status
        """
        from nexusLIMS.db.session_handler import SessionLog, Session
        start_ts = '2020-01-01T12:00:00.000-05:00'
        end_ts = '2020-01-01T20:00:00.000-05:00'
        start = SessionLog(session_identifier='test_session',
                           instrument='FEI-Titan-TEM-635816_n',
                           timestamp=start_ts, event_type='START', user='test',
                           record_status='TO_BE_BUILT')
        start.insert_log()
        end = SessionLog(session_identifier='test_session',
                         instrument='FEI-Titan-TEM-635816_n',
                         timestamp=end_ts, event_type='END', user='test',
                         record_status='TO_BE_BUILT')
        end.insert_log()

        s = Session(session_identifier='test_session',
                    instrument=instrument_db['testsurface-CPU_P1111111'],
                    dt_from=_dt.fromisoformat(start_ts),
                    dt_to=_dt.fromisoformat(end_ts),
                    user='test')
        # return just our session of interest to build and disable nemo
        # harvester's add_all_usage_events_to_db method
        monkeypatch.setattr(_rb, '_get_sessions', lambda: [s])
        monkeypatch.setattr(_rb._nemo, 'add_all_usage_events_to_db',
                            lambda dt_from, dt_to: None)

        _rb.process_new_records(dry_run=False)

        assert "No reservation found matching this session, so assuming " \
               "NexusLIMS does not have user consent for data harvesting." \
               in caplog.text

        _, res = dbq("SELECT * FROM session_log WHERE session_identifier = ?",
                     ("test_session", ))
        assert res[0][5] == 'NO_RESERVATION'
        assert res[1][5] == 'NO_RESERVATION'
        assert res[2][5] == 'NO_RESERVATION'

    def test_new_session_processor(self, remove_nemo_gov_harvester,
                                   monkeypatch, fix_mountain_time):
        # make record uploader just pretend by returning all files provided
        # (as if they were actually uploaded)
        monkeypatch.setattr(_rb, "_upload_record_files", lambda x: (x, x))

        # Override the build_records function to not generate previews (since
        # this is tested elsewhere) to speed things up
        from nexusLIMS.builder.record_builder import build_record
        monkeypatch.setattr(_rb, 'build_record',
                            partial(build_record, generate_previews=False))

        # use just datetime range that should have just one record from NEMO
        _rb.process_new_records(
            dt_from=_dt.fromisoformat('2021-08-02T00:00:00-04:00'),
            dt_to=_dt.fromisoformat('2021-08-03T00:00:00-04:00'))

        # tests on the database entries
        # after processing the records, there should be size added
        # "RECORD_GENERATION" logs, for a total of 18 logs
        assert len(make_db_query('SELECT * FROM session_log')) == 24
        assert len(make_db_query('SELECT * FROM session_log WHERE '
                                 '"event_type" = "RECORD_GENERATION"')) == 8
        assert len(make_db_query('SELECT * FROM session_log WHERE '
                                 '"record_status" = "TO_BE_BUILT"')) == 0
        assert len(make_db_query('SELECT * FROM session_log WHERE'
                                 '"record_status" = "NO_FILES_FOUND"')) == 3
        assert len(make_db_query('SELECT * FROM session_log WHERE'
                                 '"record_status" = "COMPLETED"')) == 21

        # tests on the XML records
        # there should be 6 completed records in the records/uploaded/ folder
        xmls = glob(os.path.join(os.getenv('nexusLIMS_path'), '..',
                                 'records', 'uploaded', '*.xml'))
        assert len(xmls) == 7

        # test some various values from the records saved to disk:
        NX = "https://data.nist.gov/od/dm/nexus/experiment/v1.0"
        expected = {
            # ./Titan/***REMOVED***/181113 - ***REMOVED*** - ***REMOVED*** - Titan/
            '2018-11-13_FEI-Titan-TEM-635816_n_91.xml': {
                f'/{{{NX}}}title': '***REMOVED***',
                f'//{{{NX}}}acquisitionActivity': 4,
                f'//{{{NX}}}dataset': 37,
                f'/{{{NX}}}summary/{{{NX}}}motivation': '***REMOVED*** '
                                                        '***REMOVED***',
                f'/{{{NX}}}summary/{{{NX}}}instrument': 'FEI-Titan-TEM-635816',
                f'//{{{NX}}}sample': 1
            },
            # ./JEOL3010/JEOL3010/***REMOVED***/***REMOVED***/20190724/
            '2019-07-24_JEOL-JEM3010-TEM-565989_n_93.xml': {
                f'/{{{NX}}}title': '***REMOVED***',
                f'//{{{NX}}}acquisitionActivity': 6,
                f'//{{{NX}}}dataset': 55,
                f'/{{{NX}}}summary/{{{NX}}}motivation':
                    '***REMOVED*** paraffin polymer '
                    '***REMOVED***',
                f'/{{{NX}}}summary/{{{NX}}}instrument':
                    'JEOL-JEM3010-TEM-565989',
                f'//{{{NX}}}sample': 1
            },
            # ./Quanta/***REMOVED***/20190830_05... and ./Quanta/***REMOVED***/tmp/20190830_05...
            '2019-09-06_FEI-Quanta200-ESEM-633137_n_90.xml': {
                f'/{{{NX}}}title': 'Looking for Nickel Alloys',
                f'//{{{NX}}}acquisitionActivity': 5,
                f'//{{{NX}}}dataset': 28,
                f'/{{{NX}}}summary/{{{NX}}}motivation':
                    '***REMOVED*** nickel alloys '
                    'using EDX spectroscopy.',
                f'/{{{NX}}}summary/{{{NX}}}instrument':
                    'FEI-Quanta200-ESEM-633137',
                f'//{{{NX}}}sample': 1
            },
            # ./643Titan/***REMOVED***/191106 - Reactor Specimen - 643 Titan/
            '2019-11-06_FEI-Titan-STEM-630901_n_92.xml': {
                f'/{{{NX}}}title': 'Reactor Samples',
                f'//{{{NX}}}acquisitionActivity': 15,
                f'//{{{NX}}}dataset': 38,
                f'/{{{NX}}}summary/{{{NX}}}motivation': 'EELS mapping of '
                                                        'layer intermixing.',
                f'/{{{NX}}}summary/{{{NX}}}instrument': 'FEI-Titan-STEM-630901',
                f'//{{{NX}}}sample': 1
            },
            # ./Titan/***REMOVED***/200204 - ***REMOVED*** - ***REMOVED*** - Titan/
            '2020-02-04_FEI-Titan-TEM-635816_n_95.xml': {
                f'/{{{NX}}}title': 'Experiment on the FEI Titan TEM on '
                                   'Tuesday Feb. 04, 2020',
                f'//{{{NX}}}acquisitionActivity': 4,
                f'//{{{NX}}}dataset': 18,
                f'/{{{NX}}}summary/{{{NX}}}motivation': None,
                f'/{{{NX}}}summary/{{{NX}}}instrument': 'FEI-Titan-TEM-635816',
                f'//{{{NX}}}sample': 1
            },
            # DONE: add expected values for NEMO built record
            '2021-08-02_testsurface-CPU_P1111111_31.xml': {
                f'/{{{NX}}}title': '***REMOVED***',
                f'//{{{NX}}}acquisitionActivity': 1,
                f'//{{{NX}}}dataset': 4,
                f'/{{{NX}}}summary/{{{NX}}}motivation':
                    '***REMOVED*** epitaxial (or not) '
                    'registrations ***REMOVED***.',
                f'/{{{NX}}}summary/{{{NX}}}instrument':
                    'testsurface-CPU_P1111111',
                f'//{{{NX}}}sample': 1
            },
            '2021-11-29_testsurface-CPU_P1111111_21.xml': {
                f'/{{{NX}}}title': 'A test with multiple samples',
                f'//{{{NX}}}acquisitionActivity': 1,
                f'//{{{NX}}}dataset': 4,
                f'/{{{NX}}}summary/{{{NX}}}motivation':
                    'To test the harvester with multiple samples',
                f'/{{{NX}}}summary/{{{NX}}}instrument':
                    'testsurface-CPU_P1111111',
                f'//{{{NX}}}sample': 4
            }
        }
        for f in sorted(xmls):
            base_f = os.path.basename(f)
            root = et.parse(f)

            xpath = f'/{{{NX}}}title'
            if root.find(xpath) is not None:
                assert root.find(xpath).text == expected[base_f][xpath]

            xpath = f'//{{{NX}}}acquisitionActivity'
            assert len(root.findall(xpath)) == expected[base_f][xpath]

            xpath = f'//{{{NX}}}dataset'
            assert len(root.findall(xpath)) == expected[base_f][xpath]

            xpath = f'/{{{NX}}}summary/{{{NX}}}motivation'
            if root.find(xpath) is not None:
                assert root.find(xpath).text == expected[base_f][xpath]
            else:
                assert root.find(xpath) == expected[base_f][xpath]

            xpath = f'/{{{NX}}}summary/{{{NX}}}instrument'
            assert root.find(xpath).get('pid') == expected[base_f][xpath]

            xpath = f'//{{{NX}}}sample'
            assert len(root.findall(xpath)) == expected[base_f][xpath]

            # remove record
            os.remove(f)

        # clean up directory
        shutil.rmtree(os.path.join(os.getenv('nexusLIMS_path'), '..',
                                   'records'))

    def test_new_session_bad_upload(self, remove_nemo_gov_harvester,
                                    monkeypatch, caplog):
        # set the methods used to determine if all records were uploaded to
        # just return known lists
        monkeypatch.setattr(_rb, 'build_new_session_records',
                            lambda: ['dummy_file1', 'dummy_file2',
                                     'dummy_file3'])
        monkeypatch.setattr(_rb, '_upload_record_files',
                            lambda x: ([], []))

        _rb.process_new_records(
            dt_from=_dt.fromisoformat('2021-08-01T13:00:00-06:00'),
            dt_to=_dt.fromisoformat('2021-09-05T20:00:00-06:00'))
        assert "Some record files were not uploaded: " \
               "['dummy_file1', 'dummy_file2', 'dummy_file3']" in caplog.text

    def test_build_record_error(self, remove_nemo_gov_harvester,
                                monkeypatch, caplog):
        def mock_get_sessions():
            return [session_handler.Session('dummy_id', 'no_instrument',
                                            _dt.now(), _dt.now(), 'None')]

        monkeypatch.setattr(_rb, '_get_sessions', mock_get_sessions)
        _rb.build_new_session_records()
        assert 'Marking dummy_id as "ERROR"' in caplog.text

    def test_non_validating_record(self, remove_nemo_gov_harvester,
                                   monkeypatch, caplog):
        def mock_get_sessions():
            return [session_handler.Session(
                session_identifier='1c3a6a8d-9038-41f5-b969-55fd02e12345',
                instrument=instrument_db['FEI-Titan-TEM-635816_n'],
                dt_from=_dt.fromisoformat('2020-02-04T09:00:00.000'),
                dt_to=_dt.fromisoformat('2020-02-04T12:00:00.000'),
                user='None')]

        def mock_build_record(session,
                              sample_id=None,
                              generate_previews=True):
            return '<xml>Record that will not validate against NexusLIMS ' \
                   'Schema</xml>'

        monkeypatch.setattr(_rb, '_get_sessions', mock_get_sessions)
        monkeypatch.setattr(_rb, 'build_record', mock_build_record)
        _rb.build_new_session_records()
        assert "ERROR" in caplog.text
        assert "Could not validate record, did not write to disk" in caplog.text

    def test_dump_record(self, remove_nemo_gov_harvester, monkeypatch,
                         fix_mountain_time):
        from nexusLIMS.db.session_handler import Session
        dt_str_from = '2021-08-02T12:00:00-06:00'
        dt_str_to = '2021-08-02T15:00:00-06:00'
        session = Session(session_identifier="an-identifier-string",
                          instrument=instrument_db['testsurface-CPU_P1111111'],
                          dt_from=_dt.fromisoformat(dt_str_from),
                          dt_to=_dt.fromisoformat(dt_str_to),
                          user='unused')
        out_fname = _rb.dump_record(session=session,
                                    generate_previews=False)
        os.remove(out_fname)

    def test_no_sessions(self, remove_nemo_gov_harvester, monkeypatch):
        # monkeypatch to return empty list (as if there are no sessions)
        monkeypatch.setattr(_rb, '_get_sessions', lambda: [])
        with pytest.raises(SystemExit) as e:
            _rb.build_new_session_records()
        assert e.type == SystemExit

    def test_build_record_no_consent(self, remove_nemo_gov_harvester,
                                     monkeypatch, caplog):
        #  https://***REMOVED***/api/reservations/?id=168
        def mock_get_sessions():
            return [session_handler.Session(
                session_identifier='test_session',
                instrument=instrument_db['testsurface-CPU_P1111111'],
                dt_from=_dt.fromisoformat('2021-12-08T09:00:00.000-07:00'),
                dt_to=_dt.fromisoformat('2021-12-08T12:00:00.000-07:00'),
                user='None')]

        monkeypatch.setattr(_rb, '_get_sessions', mock_get_sessions)
        xmls_files = _rb.build_new_session_records()

        _, res = dbq("SELECT * FROM session_log WHERE session_identifier = ?",
                     ("test_session", ))
        assert res[0][5] == 'NO_CONSENT'
        assert "Reservation 168 requested not to have their data harvested" \
               in caplog.text
        assert len(xmls_files) == 0  # no record should be returned

    def test_build_record_single_file(self, remove_nemo_gov_harvester,
                                      monkeypatch):
        # test session that only has one file present
        def mock_get_sessions():
            return [session_handler.Session(
                session_identifier='https://***REMOVED***/api/usage_events'
                                   '/?id=-1',
                instrument=instrument_db['testsurface-CPU_P1111111'],
                dt_from=_dt.fromisoformat('2021-11-29T11:28:01.000-07:00'),
                dt_to=_dt.fromisoformat('2021-11-29T11:28:02.000-07:00'),
                user='None')]

        NX = "https://data.nist.gov/od/dm/nexus/experiment/v1.0"

        monkeypatch.setattr(_rb, '_get_sessions', mock_get_sessions)

        # make record uploader just pretend by returning all files provided (
        # as if they were actually uploaded)
        monkeypatch.setattr(_rb, "_upload_record_files", lambda x: (x, x))

        xml_files = _rb.build_new_session_records()
        assert len(xml_files) == 1
        f = xml_files[0]
        root = et.parse(f)

        assert root.find(f'/{{{NX}}}title').text == \
               'A test with multiple samples'
        assert len(root.findall(f'//{{{NX}}}acquisitionActivity')) == 1
        assert len(root.findall(f'//{{{NX}}}dataset')) == 1
        assert root.find(f'/{{{NX}}}summary/{{{NX}}}motivation').text == \
               'To test the harvester with multiple samples'
        assert root.find(f'/{{{NX}}}summary/{{{NX}}}instrument').get('pid') == \
               'testsurface-CPU_P1111111'
        assert len(root.findall(f'//{{{NX}}}sample')) == 4

        # remove record
        os.remove(f)

    def test_build_record_with_sample_elements(
            self, remove_nemo_gov_harvester, monkeypatch):
        # test session that only has one file present
        def mock_get_sessions():
            return [session_handler.Session(
                session_identifier='https://***REMOVED***/api/usage_events'
                                   '/?id=-1',
                instrument=instrument_db['testsurface-CPU_P1111111'],
                dt_from=_dt.fromisoformat('2023-02-13T13:00:00.000-07:00'),
                dt_to=_dt.fromisoformat('2023-02-13T14:00:00.000-07:00'),
                user='None')]

        NX = "https://data.nist.gov/od/dm/nexus/experiment/v1.0"

        monkeypatch.setattr(_rb, '_get_sessions', mock_get_sessions)

        # make record uploader just pretend by returning all files provided (
        # as if they were actually uploaded)
        monkeypatch.setattr(_rb, "_upload_record_files", lambda x: (x, x))

        # override preview generation to save time
        from nexusLIMS.builder.record_builder import build_record
        monkeypatch.setattr(_rb, 'build_record',
                            partial(build_record, generate_previews=False))

        xml_files = _rb.build_new_session_records()
        assert len(xml_files) == 1
        f = xml_files[0]
        root = et.parse(f)

        assert root.find(f'/{{{NX}}}title').text == \
               'Test reservation for multiple samples, some with elements, some not'
        assert len(root.findall(f'//{{{NX}}}acquisitionActivity')) == 1
        assert len(root.findall(f'//{{{NX}}}dataset')) == 4
        assert root.find(f'/{{{NX}}}summary/{{{NX}}}motivation').text == \
               'testing'
        assert root.find(f'/{{{NX}}}summary/{{{NX}}}instrument').get('pid') == \
               'testsurface-CPU_P1111111'
        assert len(root.findall(f'//{{{NX}}}sample')) == 3

        # test sample element tags
        expected = [
            None,
            [f'{{{NX}}}S', f'{{{NX}}}Rb', f'{{{NX}}}Sb', f'{{{NX}}}Re', f'{{{NX}}}Cm'],
            [f'{{{NX}}}Ir']
        ]
        sample_elements = root.findall(f'//{{{NX}}}sample')
        for exp, e in zip(expected, sample_elements):
            el = e.find(f'{{{NX}}}elements')
            if exp is None:
                assert exp == el
            else:
                assert [i.tag for i in el] == exp

        # remove record
        os.remove(f)

    def test_not_implemented_harvester(self):
        # need to create a session with an instrument with a bogus harvester
        from nexusLIMS.instruments import Instrument
        i = Instrument(harvester="bogus")
        s = session_handler.Session(
            session_identifier='identifier',
            instrument=i,
            dt_from=_dt.fromisoformat('2021-12-09T11:40:00-07:00'),
            dt_to=_dt.fromisoformat('2021-12-09T11:41:00-07:00'),
            user='miclims'
        )
        with pytest.raises(NotImplementedError) as e:
            _rb.get_reservation_event(s)
        assert "Harvester bogus not found in nexusLIMS.harvesters" in \
               str(e.value)

    def test_not_implemented_res_event_from_session(self, monkeypatch):
        # create a session, but mock remove the res_event_from_session
        # attribute from the nemo harvester to simulate a module that doesn't
        # have that method defined
        with monkeypatch.context() as m:
            m.delattr("nexusLIMS.harvesters.nemo.res_event_from_session")
            with pytest.raises(NotImplementedError) as e:
                _rb.get_reservation_event(
                    session_handler.Session(
                        session_identifier='identifier',
                        instrument=instrument_db['testsurface-CPU_P1111111'],
                        dt_from=_dt.fromisoformat('2021-12-09T11:40:00-07:00'),
                        dt_to=_dt.fromisoformat('2021-12-09T11:41:00-07:00'),
                        user='miclims'
                    )
                )
            assert 'res_event_from_session has not been implemented for' in \
                   str(e.value)


@pytest.fixture(scope='module')
def gnu_find_activities(fix_mountain_time):
    instr = instrument_db['FEI-Titan-TEM-635816_n']
    dt_from = _dt.fromisoformat('2018-11-13T13:00:00.000')
    dt_to = _dt.fromisoformat('2018-11-13T16:00:00.000')
    activities_list = _rb.build_acq_activities(
        instrument=instr, dt_from=dt_from, dt_to=dt_to,
        generate_previews=False)

    yield {'instr': instr,
           'dt_from': dt_from,
           'dt_to': dt_to,
           'activities_list': activities_list}


class TestActivity:
    def test_gnu_find_vs_pure_python(self, monkeypatch,
                                     fix_mountain_time,
                                     gnu_find_activities):
        # force the GNU find method to fail
        def mock_gnu_find(x, y, z, q):
            raise RuntimeError('Mock failure for GNU find method')

        monkeypatch.setattr(_rb, '_gnu_find_files', mock_gnu_find)
        self.activities_list_python_find = \
            _rb.build_acq_activities(
                instrument=gnu_find_activities['instr'],
                dt_from=gnu_find_activities['dt_from'],
                dt_to=gnu_find_activities['dt_to'],
                generate_previews=False)

        for i in range(len(self.activities_list_python_find)):
            assert str(gnu_find_activities['activities_list'][i]) == \
                   str(self.activities_list_python_find[i])

    def test_activity_repr(self, gnu_find_activities):
        if 'is_mountain_time' in os.environ:  # pragma: no cover
            expected = '             AcquisitionActivity; ' \
                       'start: 2018-11-13T11:01:28.179682; ' \
                       'end: 2018-11-13T11:19:14.635522'
        else:  # pragma: no cover
            expected = '             AcquisitionActivity; ' \
                       'start: 2018-11-13T13:01:28.179682; ' \
                       'end: 2018-11-13T13:19:14.635522'
        assert gnu_find_activities['activities_list'][0].__repr__() == \
               expected

    def test_activity_str(self, gnu_find_activities):
        if 'is_mountain_time' in os.environ:  # pragma: no cover
            expected = '2018-11-13T11:01:28.179682 AcquisitionActivity '
        else:  # pragma: no cover
            expected = '2018-11-13T13:01:28.179682 AcquisitionActivity '
        assert gnu_find_activities['activities_list'][0].__str__() == \
               expected

    def test_add_file_bad_meta(self, monkeypatch, caplog,
                               gnu_find_activities):
        # make parse_metadata return None to force into error situation
        monkeypatch.setattr(activity, '_parse_metadata',
                            lambda fname, generate_preview: (None, ''))
        orig_activity_file_length = \
            len(gnu_find_activities['activities_list'][0].files)
        gnu_find_activities['activities_list'][0].add_file(
            files['643_EELS_SI'][0])
        assert len(gnu_find_activities['activities_list'][0].files) == \
               orig_activity_file_length + 1
        assert f"Could not parse metadata of " \
               f"{files['643_EELS_SI'][0]}" in caplog.text

    def test_add_file_bad_file(self, gnu_find_activities):
        with pytest.raises(FileNotFoundError):
            gnu_find_activities['activities_list'][0].add_file(
                'dummy_file_does_not_exist')

    def test_store_unique_before_setup(self, monkeypatch, caplog,
                                       gnu_find_activities):
        a = gnu_find_activities['activities_list'][0]
        monkeypatch.setattr(a, 'setup_params', None)
        a.store_unique_metadata()
        assert 'setup_params has not been defined; call store_setup_params() ' \
               'prior to using this method. Nothing was done.' in caplog.text

    def test_as_xml(self, gnu_find_activities):
        a = gnu_find_activities['activities_list'][0]
        # setup a few values in the activity to trigger XML escaping:
        a.setup_params['Acquisition Device'] = '<TEST>'
        a.files[0] += '<&'
        a.unique_meta[0]['Imaging Mode'] = '<IMAGING>'

        xml_el = a.as_xml(seqno=0, sample_id='sample_id',
                          print_xml=True)


class TestSession:
    @pytest.fixture()
    def session(self):
        s = session_handler.Session(
            session_identifier='test_session',
            instrument=instrument_db['FEI-Titan-TEM-635816_n'],
            dt_from=_dt.fromisoformat('2020-02-04T09:00:00.000'),
            dt_to=_dt.fromisoformat('2020-02-04T12:00:00.000'),
            user='None')
        return s

    def test_session_repr(self, session):
        assert session.__repr__() == '2020-02-04T09:00:00 to ' \
                                     '2020-02-04T12:00:00 on ' \
                                     'FEI-Titan-TEM-635816_n'

    def test_record_generation_timestamp(self, session, cleanup_session_log):
        from nexusLIMS.db.session_handler import db_query
        row_dict = session.insert_record_generation_event()
        _, res = \
            db_query("SELECT timestamp FROM session_log WHERE "
                     "id_session_log = ?", (row_dict['id_session_log'],))
        assert _dt.fromisoformat(res[0][0]).tzinfo is not None

    def test_bad_db_status(self, monkeypatch):
        uuid = uuid4()
        q = f"INSERT INTO session_log " \
            f"(instrument, event_type, session_identifier, record_status) " \
            f"VALUES ('FEI-Titan-TEM-635816_n', 'START', " \
            f"'{uuid}', 'TO_BE_BUILT');"
        make_db_query(q)
        # because we put in an extra START log with TO_BE_BUILT status,
        # this should raise an error:
        with pytest.raises(ValueError):
            session_handler.get_sessions_to_build()

        # remove the session log we added
        q = f"DELETE FROM session_log WHERE session_identifier = '{uuid}'"
        make_db_query(q)


class TestSessionLog:
    sl = session_handler.SessionLog(
        session_identifier='testing-session-log',
        instrument=instrument_db['FEI-Titan-TEM-635816_n'].name,
        timestamp='2020-02-04T09:00:00.000',
        event_type='START',
        user='ear1',
        record_status='TO_BE_BUILT'
    )

    @pytest.fixture
    def cleanup_session_log(self):
        # this fixture removes the rows for the session logs added in
        # this test class, so it doesn't mess up future record building tests
        yield None
        # below runs on test teardown
        dbq(query='DELETE FROM session_log WHERE session_identifier = ?',
            args=('testing-session-log',))

    def test_repr(self):
        assert self.sl.__repr__() == "SessionLog " \
                                     "(id=testing-session-log, " \
                                     "instrument=FEI-Titan-TEM-635816_n, " \
                                     "timestamp=2020-02-04T09:00:00.000, " \
                                     "event_type=START, " \
                                     "user=ear1, " \
                                     "record_status=TO_BE_BUILT)"

    def test_insert_log(self):
        _, res_before = dbq(query='SELECT * FROM session_log', args=None)
        self.sl.insert_log()
        _, res_after = dbq(query='SELECT * FROM session_log', args=None)
        assert len(res_after) - len(res_before) == 1

    def test_insert_duplicate_log(self, caplog, cleanup_session_log):
        result = self.sl.insert_log()
        assert 'WARNING' in caplog.text
        assert 'SessionLog already existed in DB, so no row was added:' in \
               caplog.text
        assert result


@pytest.mark.skipif(os.environ.get('test_cdcs_url') is None,
                    reason="Test CDCS server not defined by 'test_cdcs_url' environment variable")
class TestCDCS:
    @pytest.fixture(autouse=True)
    def mock_test_cdcs_url(self, monkeypatch):
        """Mock 'cdcs_url' environment variable with 'test_cdcs_url' one"""
        monkeypatch.setenv('cdcs_url', os.environ.get('test_cdcs_url'))
        yield

    def test_upload_and_delete_record(self):
        files_uploaded, record_ids = cdcs.upload_record_files(
            [files['RECORD'][0]])
        cdcs.delete_record(record_ids[0])

    def test_upload_and_delete_record_glob(self):
        prev_dir = os.getcwd()
        os.chdir(os.path.dirname(files['RECORD'][0]))
        files_uploaded, record_ids = cdcs.upload_record_files(None)
        for id in record_ids:
            cdcs.delete_record(id)
        os.chdir(prev_dir)

    def test_upload_no_files_glob(self):
        prev_dir = os.getcwd()
        os.chdir(os.path.join(os.path.dirname(files['RECORD'][0]), 'figs'))
        with pytest.raises(ValueError):
            files_uploaded, record_ids = cdcs.upload_record_files(None)
        os.chdir(prev_dir)

    def test_upload_file_bad_response(self, monkeypatch, caplog):
        Response = namedtuple('Response', 'status_code text')

        def mock_upload(xml_content, title):
            return Response(status_code=404,
                            text='This is a fake request error!'), 'dummy_id'

        monkeypatch.setattr(cdcs, 'upload_record_content', mock_upload)

        files_uploaded, record_ids = cdcs.upload_record_files(
            [files['RECORD'][0]])
        assert len(files_uploaded) == 0
        assert len(record_ids) == 0
        assert f'Could not upload {os.path.basename(files["RECORD"][0])}'

    def test_bad_auth(self, monkeypatch):
        monkeypatch.setenv('nexusLIMS_user', 'baduser')
        monkeypatch.setenv('nexusLIMS_pass', 'badpass')
        with pytest.raises(AuthenticationError):
            cdcs.get_workspace_id()
        with pytest.raises(AuthenticationError):
            cdcs.get_template_id()

    def test_delete_record_bad_response(self, monkeypatch, caplog):
        Response = namedtuple('Response', 'status_code text')

        monkeypatch.setattr(cdcs, '_nx_req',
                            lambda x, y, basic_auth: Response(
                                status_code=404,
                                text='This is a fake request error!'))
        cdcs.delete_record('dummy')
        assert 'Got error while deleting dummy:' in caplog.text
        assert 'This is a fake request error!' in caplog.text

    def test_upload_content_bad_response(self, monkeypatch, caplog):
        Response = namedtuple('Response', 'status_code text json')

        def mock_req(a, b, json=None, basic_auth=False):
            return Response(status_code=404,
                            text='This is a fake request error!',
                            json=lambda: [{'id': 'dummy', 'current': 'dummy'}])

        monkeypatch.setattr(cdcs, '_nx_req', mock_req)

        resp = cdcs.upload_record_content('<xml>content</xml>', 'title')
        assert isinstance(resp, Response)
        assert 'Got error while uploading title:' in caplog.text
        assert 'This is a fake request error!' in caplog.text

    def test_no_env_variable(self, monkeypatch):
        monkeypatch.delenv('test_cdcs_url')
        monkeypatch.delenv('cdcs_url')
        with pytest.raises(ValueError):
            cdcs._cdcs_url()
