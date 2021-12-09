import os
import nexusLIMS
from functools import partial
import shutil

from nexusLIMS import cdcs
from nexusLIMS.instruments import instrument_db
from nexusLIMS.builder import record_builder as _rb
from nexusLIMS.schemas import activity
from nexusLIMS.db import session_handler
from nexusLIMS.db import make_db_query
from nexusLIMS.db.session_handler import db_query as dbq
import nexusLIMS.utils
import time
from collections import namedtuple
from glob import glob
from lxml import etree as et
from uuid import uuid4
from datetime import datetime as _dt
from datetime import timedelta as _td
from nexusLIMS.tests.utils import files
from nexusLIMS.harvesters.sharepoint_calendar import AuthenticationError
from nexusLIMS.harvesters import nemo
import pytest


class TestRecordBuilder:

    # have to do these before modifying the database with the actual run tests
    def test_dry_run_sharepoint_calendar(self):
        sessions = session_handler.get_sessions_to_build()
        cal_event = _rb.dry_run_get_sharepoint_reservation_event(sessions[0])
        assert cal_event.project_name[0] == '642.03.??'
        assert cal_event.username == '***REMOVED***'
        assert cal_event.experiment_title == 'Looking for Nickel Alloys'
        assert cal_event.start_time == _dt.fromisoformat(
            '2019-09-06T16:30:00-04:00')

    def test_dry_run_file_find(self, fix_mountain_time):
        sessions = session_handler.get_sessions_to_build()
        # add at least one NEMO session to the file find (one is already in the
        # test database, but this get_usage_events_as_sessions call will add
        # another)
        sessions += nemo.get_usage_events_as_sessions(
            dt_from=_dt.fromisoformat('2021-08-02T00:00:00-04:00'),
            dt_to=_dt.fromisoformat('2021-08-03T00:00:00-04:00'))
        correct_files_per_session = [28, 37, 38, 55,  0, 18, 4, 4]
        file_list_list = []
        for s, ans in zip(sessions, correct_files_per_session):
            found_files = _rb.dry_run_file_find(s)
            file_list_list.append(found_files)
            # noinspection PyTypeChecker
            assert len(found_files) == ans

        assert f'{os.environ["mmfnexus_path"]}' \
               f'/Titan/***REMOVED***/200204 - ***REMOVED*** - ***REMOVED*** ' \
               f'- Titan/15 - 620k.dm3' in file_list_list[5]

        # file from NEMO session
        assert f'{os.environ["mmfnexus_path"]}' \
               f'/Titan/***REMOVED***/210801 - MTJ-MgO - ***REMOVED*** - Titan' \
               f'/02 - 620k.dm3' in file_list_list[-1]

    def test_process_new_records_dry_run(self):
        # just running to ensure coverage, tests are included above
        _rb.process_new_records(dry_run=True,
                                dt_to=_dt.fromisoformat(
                                    '2021-08-03T00:00:00-04:00'))

    def test_process_new_records_dry_run_no_sessions(self, monkeypatch, caplog):
        monkeypatch.setattr(_rb, '_get_sessions', lambda: [])
        # there shouldn't be any MARLIN sessions before July 1, 2021
        _rb.process_new_records(dry_run=True,
                                dt_to=_dt.fromisoformat(
                                    '2021-07-01T00:00:00-04:00'))
        assert "No 'TO_BE_BUILT' sessions were found. Exiting." in caplog.text

    def test_process_new_records_no_files_warning(self, monkeypatch, caplog):
        monkeypatch.setattr(_rb, "build_new_session_records", lambda: [])
        _rb.process_new_records(dry_run=False,
                                dt_to=_dt.fromisoformat(
                                    '2021-07-01T00:00:00-04:00'))
        assert "No XML files built, so no files uploaded" in caplog.text

    def test_new_session_processor(self, monkeypatch, fix_mountain_time):
        # make record uploader just pretend by returning all files provided (
        # as if they were actually uploaded)
        monkeypatch.setattr(_rb, "_upload_record_files", lambda x: (x, x))

        # overwrite nexusLIMS_path so we write records to the test folder rather
        # than real nexusLIMS folder
        monkeypatch.setenv("nexusLIMS_path",
                           os.path.join(os.path.dirname(__file__), 'files',
                                        'records'))

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
        xmls = glob(os.path.join(os.path.dirname(__file__), 'files',
                                 'records', 'uploaded', '*.xml'))
        assert len(xmls) == 7

        # test some various values from the records saved to disk:
        expected = {
            # ./Titan/***REMOVED***/181113 - ***REMOVED*** - ***REMOVED*** - Titan/
            '2018-11-13_FEI-Titan-TEM-635816_7de34313.xml': {
                '/title': '***REMOVED***',
                '//acquisitionActivity': 4,
                '//dataset': 37,
                '/summary/motivation': '***REMOVED***!',
                '/summary/instrument': 'FEI-Titan-TEM-635816',
                '//sample': 1
            },
            # ./JEOL3010/JEOL3010/***REMOVED***/***REMOVED***/20190724/
            '2019-07-24_JEOL-JEM3010-TEM-565989_41ec0ad1.xml': {
                '/title': '***REMOVED***',
                '//acquisitionActivity': 6,
                '//dataset': 55,
                '/summary/motivation': '***REMOVED*** '
                                       '***REMOVED*** '
                                       'beam',
                '/summary/instrument': 'JEOL-JEM3010-TEM-565989',
                '//sample': 1
            },
            # ./Quanta/***REMOVED***/20190830_05... and ./Quanta/***REMOVED***/tmp/20190830_05...
            '2019-09-06_FEI-Quanta200-ESEM-633137_9c8f3a8d.xml': {
                '/title': 'Looking for Nickel Alloys',
                '//acquisitionActivity': 5,
                '//dataset': 28,
                '/summary/motivation': '***REMOVED*** '
                                       'nickel alloys using EDX spectroscopy.',
                '/summary/instrument': 'FEI-Quanta200-ESEM-633137',
                '//sample': 1
            },
            # ./643Titan/***REMOVED***/191106 - Reactor Specimen - 643 Titan/
            '2019-11-06_FEI-Titan-STEM-630901_1dab79db.xml': {
                '/title': 'Reactor Samples',
                '//acquisitionActivity': 15,
                '//dataset': 38,
                '/summary/motivation': 'EELS mapping of layer intermixing.',
                '/summary/instrument': 'FEI-Titan-STEM-630901',
                '//sample': 1
            },
            # ./Titan/***REMOVED***/200204 - ***REMOVED*** - ***REMOVED*** - Titan/
            '2020-02-04_FEI-Titan-TEM-635816_1c3a6a8d.xml': {
                '/title': 'Experiment on the FEI Titan TEM on '
                          'Tuesday Feb. 04, 2020',
                '//acquisitionActivity': 4,
                '//dataset': 18,
                '/summary/motivation': None,
                '/summary/instrument': 'FEI-Titan-TEM-635816',
                '//sample': 1
            },
            # DONE: add expected values for NEMO built record
            '2021-08-02_FEI-Titan-TEM-635816_n_9.xml': {
                '/title': '***REMOVED***',
                '//acquisitionActivity': 1,
                '//dataset': 4,
                '/summary/motivation': '***REMOVED*** '
                                       '***REMOVED*** '
                                       '***REMOVED***.',
                '/summary/instrument': 'FEI-Titan-TEM-635816',
                '//sample': 1
            },
            '2021-11-29_testsurface-CPU_P1111111_21.xml': {
                '/title': 'A test with multiple samples',
                '//acquisitionActivity': 1,
                '//dataset': 4,
                '/summary/motivation': 'To test the harvester with '
                                       'multiple samples',
                '/summary/instrument': 'testsurface-CPU_P1111111',
                '//sample': 4
            }
        }
        for f in sorted(xmls):
            base_f = os.path.basename(f)
            root = et.parse(f)

            xpath = '/title'
            if root.find(xpath) is not None:
                assert root.find(xpath).text == expected[base_f][xpath]

            xpath = '//acquisitionActivity'
            assert len(root.findall(xpath)) == expected[base_f][xpath]

            xpath = '//dataset'
            assert len(root.findall(xpath)) == expected[base_f][xpath]

            xpath = '/summary/motivation'
            if root.find(xpath) is not None:
                assert root.find(xpath).text == expected[base_f][xpath]
            else:
                assert root.find(xpath) == expected[base_f][xpath]

            xpath = '/summary/instrument'
            assert root.find(xpath).get('pid') == expected[base_f][xpath]

            xpath = '//sample'
            assert len(root.findall(xpath)) == expected[base_f][xpath]

            # remove record
            os.remove(f)

        # clean up directory
        shutil.rmtree(os.path.join(os.path.dirname(__file__), 'files',
                                   'records'))

    def test_new_session_bad_upload(self, monkeypatch, caplog):
        # set the methods used to determine if all records were uploaded to
        # just return known lists
        monkeypatch.setattr(_rb, 'build_new_session_records',
                            lambda: ['dummy_file1', 'dummy_file2',
                                     'dummy_file3'])
        monkeypatch.setattr(_rb, '_upload_record_files',
                            lambda x: ([], []))

        _rb.process_new_records()
        assert "Some record files were not uploaded: " \
               "['dummy_file1', 'dummy_file2', 'dummy_file3']" in caplog.text

    def test_build_record_error(self, monkeypatch, caplog):
        def mock_get_sessions():
            return [session_handler.Session('dummy_id', 'no_instrument',
                                            _dt.now(), _dt.now(), 'None')]
        monkeypatch.setattr(_rb, '_get_sessions', mock_get_sessions)
        _rb.build_new_session_records()
        assert 'Marking dummy_id as "ERROR"' in caplog.text

    def test_non_validating_record(self, monkeypatch, caplog):
        def mock_get_sessions():
            return [session_handler.Session(
                session_identifier='1c3a6a8d-9038-41f5-b969-55fd02e12345',
                instrument=instrument_db['FEI-Titan-TEM-635816'],
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

    def test_dump_record(self, monkeypatch, fix_mountain_time):
        from nexusLIMS.db.session_handler import Session
        session = Session(session_identifier="an-identifier-string",
                          instrument=instrument_db['FEI-Titan-TEM-635816'],
                          dt_from=_dt.fromisoformat('2020-02-04T09:00:00.000'),
                          dt_to=_dt.fromisoformat('2020-02-04T12:00:00.000'),
                          user='unused')
        out_fname = _rb.dump_record(session=session,
                                    generate_previews=False)
        os.remove(out_fname)

    def test_no_sessions(self, monkeypatch):
        # monkeypatch to return empty list (as if there are no sessions)
        monkeypatch.setattr(_rb, '_get_sessions', lambda: [])
        with pytest.raises(SystemExit) as e:
            _rb.build_new_session_records()
        assert e.type == SystemExit

    def test_build_record_no_consent(self, monkeypatch, caplog):
        # DONE: test ignoring of session here. will require a
        #  reservation on NEMO that does not have data consent
        #  https://***REMOVED***/api/reservations/?id=168
        def mock_get_sessions():
            return [session_handler.Session(
                session_identifier='https://***REMOVED***/api/usage_events'
                                   '/?id=-1',
                instrument=instrument_db['testsurface-CPU_P1111111'],
                dt_from=_dt.fromisoformat('2021-12-08T09:00:00.000-07:00'),
                dt_to=_dt.fromisoformat('2021-12-08T12:00:00.000-07:00'),
                user='None')]

        monkeypatch.setattr(_rb, '_get_sessions', mock_get_sessions)
        xmls_files = _rb.build_new_session_records()
        assert "Reservation 168 requested not to have their data harvested" \
               in caplog.text
        assert len(xmls_files) == 0    # no record should be returned

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
    instr = instrument_db['FEI-Titan-TEM-635816']
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
        if 'is_mountain_time' in os.environ:    # pragma: no cover
            expected = '             AcquisitionActivity; ' \
                       'start: 2018-11-13T11:01:28.179682; ' \
                       'end: 2018-11-13T11:19:14.635522'
        else:                                   # pragma: no cover
            expected = '             AcquisitionActivity; ' \
                       'start: 2018-11-13T13:01:28.179682; ' \
                       'end: 2018-11-13T13:19:14.635522'
        assert gnu_find_activities['activities_list'][0].__repr__() == \
            expected

    def test_activity_str(self, gnu_find_activities):
        if 'is_mountain_time' in os.environ:    # pragma: no cover
            expected = '2018-11-13T11:01:28.179682 AcquisitionActivity '
        else:                                   # pragma: no cover
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
    def test_session_repr(self):
        s = session_handler.Session(
                session_identifier='1c3a6a8d-9038-41f5-b969-55fd02e12345',
                instrument=instrument_db['FEI-Titan-TEM-635816'],
                dt_from=_dt.fromisoformat('2020-02-04T09:00:00.000'),
                dt_to=_dt.fromisoformat('2020-02-04T12:00:00.000'),
                user='None')
        assert s.__repr__() == '2020-02-04T09:00:00 to ' \
                               '2020-02-04T12:00:00 on FEI-Titan-TEM-635816'

    def test_bad_db_status(self, monkeypatch):
        uuid = uuid4()
        q = f"INSERT INTO session_log " \
            f"(instrument, event_type, session_identifier, record_status) " \
            f"VALUES ('FEI-Titan-TEM-635816', 'START', " \
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
        instrument=instrument_db['FEI-Titan-TEM-635816'].name,
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
            args=('testing-session-log', ))

    def test_repr(self):
        assert self.sl.__repr__() == "SessionLog " \
            "(id=testing-session-log, " \
            "instrument=FEI-Titan-TEM-635816, " \
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


class TestCDCS:
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
