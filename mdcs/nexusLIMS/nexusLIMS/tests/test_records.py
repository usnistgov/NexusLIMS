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
from collections import namedtuple
from glob import glob
from lxml import etree as et
from uuid import uuid4
from datetime import datetime as _dt
from nexusLIMS.tests.utils import tars, files
from nexusLIMS.harvester.sharepoint_calendar import AuthenticationError
import tarfile
import pytest


def setup_module():
    """
    Setup by extracting the compressed test files
    """
    for _, tarf in tars.items():
        with tarfile.open(tarf, 'r:gz') as tar:
            tar.extractall(path=os.path.dirname(tarf))


def teardown_module():
    """
    Teardown by deleting the extracted test files
    """
    for _, fn in files.items():
        os.remove(fn)


class TestRecordBuilder:
    def test_new_session_processor(self, monkeypatch):
        # set session_handler to use test database
        monkeypatch.setattr(session_handler, "_nx_db_path", files['DB'])
        monkeypatch.setattr(nexusLIMS.db, "_nx_db_path", files['DB'])

        # make record uploader just pretend by returning all files provided (
        # as if they were actually uploaded)
        monkeypatch.setattr(_rb, "_upload_record_files", lambda x: (x, x))

        # overwrite _nx_path so we write records to the test folder rather
        # than real nexusLIMS folder
        monkeypatch.setattr(_rb, "_nx_path",
                            os.path.join(os.path.dirname(__file__), 'files',
                                         'records'))

        # Override the build_records function to not generate previews (since
        # this is tested elsewhere) to speed things up
        from nexusLIMS.builder.record_builder import build_record
        monkeypatch.setattr(_rb, 'build_record',
                            partial(build_record, generate_previews=False))

        _rb.process_new_records()

        # tests on the database entries
        # after processing the records, there should be size added
        # "RECORD_GENERATION" logs, for a total of 18 logs
        assert len(make_db_query('SELECT * FROM session_log')) == 18
        assert len(make_db_query('SELECT * FROM session_log WHERE '
                                 '"event_type" = "RECORD_GENERATION"')) == 6
        assert len(make_db_query('SELECT * FROM session_log WHERE '
                                 '"record_status" = "TO_BE_BUILT"')) == 0
        assert len(make_db_query('SELECT * FROM session_log WHERE'
                                 '"record_status" = "NO_FILES_FOUND"')) == 3
        assert len(make_db_query('SELECT * FROM session_log WHERE'
                                 '"record_status" = "COMPLETED"')) == 15

        # tests on the XML records
        # there should be 5 completed records in the records/uploaded/ folder
        xmls = glob(os.path.join(os.path.dirname(__file__), 'files',
                                 'records', 'uploaded', '*.xml'))
        assert len(xmls) == 5

        # test some various values from the records saved to disk:
        expected = {
            '2018-11-13_FEI-Titan-TEM-635816_7de34313.xml': {
                '/title': '***REMOVED***',
                '//acquisitionActivity': 2,
                '//dataset': 27,
                '/summary/motivation': '***REMOVED***!',
                '/summary/instrument': 'FEI-Titan-TEM-635816'
            },
            '2019-07-24_JEOL-JEM3010-TEM-565989_41ec0ad1.xml': {
                '/title': '***REMOVED***',
                '//acquisitionActivity': 4,
                '//dataset': 34,
                '/summary/motivation': '***REMOVED*** '
                                       '***REMOVED*** '
                                       'beam',
                '/summary/instrument': 'JEOL-JEM3010-TEM-565989'
            },
            '2019-09-06_FEI-Quanta200-ESEM-633137_9c8f3a8d.xml': {
                '/title': 'Looking for Nickel Alloys',
                '//acquisitionActivity': 5,
                '//dataset': 28,
                '/summary/motivation': '***REMOVED*** '
                                       'nickel alloys using EDX spectroscopy.',
                '/summary/instrument': 'FEI-Quanta200-ESEM-633137'
            },
            '2019-11-06_FEI-Titan-STEM-630901_1dab79db.xml': {
                '/title': 'Reactor Samples',
                '//acquisitionActivity': 15,
                '//dataset': 38,
                '/summary/motivation': 'EELS mapping of layer intermixing.',
                '/summary/instrument': 'FEI-Titan-STEM-630901'
            },
            '2020-02-04_FEI-Titan-TEM-635816_1c3a6a8d.xml': {
                '/title': 'Experiment on the FEI Titan TEM on '
                          'Tuesday Feb. 04, 2020',
                '//acquisitionActivity': 4,
                '//dataset': 18,
                '/summary/motivation': None,
                '/summary/instrument': 'FEI-Titan-TEM-635816'
            },
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
        monkeypatch.setattr(session_handler, "_nx_db_path", files['DB'])
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

        def mock_build_record(instrument, dt_from, dt_to):
            return '<xml>Record that will not validate against NexusLIMS ' \
                   'Schema</xml>'

        monkeypatch.setattr(session_handler, "_nx_db_path", files['DB'])
        monkeypatch.setattr(_rb, '_get_sessions', mock_get_sessions)
        monkeypatch.setattr(_rb, 'build_record', mock_build_record)
        _rb.build_new_session_records()
        assert "ERROR" in caplog.text
        assert "Could not validate record, did not write to disk" in caplog.text

    def test_dump_record(self):
        out_fname = _rb.dump_record(instrument_db['FEI-Titan-TEM-635816'],
                                    dt_from=_dt.fromisoformat('2020-02-04T'
                                                              '09:00:00.000'),
                                    dt_to=_dt.fromisoformat('2020-02-04T'
                                                            '12:00:00.000'),
                                    generate_previews=False)
        os.remove(out_fname)


class TestActivity:
    @classmethod
    def setup_class(cls):
        cls.activities_str, cls.activities_list = _rb.build_acq_activities(
            instrument=instrument_db['FEI-Titan-TEM-635816'],
            dt_from=_dt.fromisoformat('2018-11-13T13:00:00.000'),
            dt_to=_dt.fromisoformat('2018-11-13T16:00:00.000'),
            generate_previews=False)

    def test_activity_repr(self):
        assert self.activities_list[0].__repr__() == \
            '             AcquisitionActivity; ' \
            'start: 2018-11-13T13:01:28.179682; ' \
            'end: 2018-11-13T13:19:14.635522'

    def test_activity_str(self):
        assert self.activities_list[0].__str__() == \
               '2018-11-13T13:01:28.179682 AcquisitionActivity '

    def test_add_file_bad_meta(self, monkeypatch, caplog):
        # make parse_metadata return None to force into error situation
        monkeypatch.setattr(activity, '_parse_metadata',
                            lambda fname, generate_preview: (None, ''))
        orig_activity_file_length = len(self.activities_list[0].files)
        self.activities_list[0].add_file(files['643_EELS_SI'])
        assert len(self.activities_list[0].files) == \
            orig_activity_file_length + 1
        assert f"Could not parse metadata of " \
               f"{files['643_EELS_SI']}" in caplog.text

    def test_add_file_bad_file(self):
        with pytest.raises(FileNotFoundError):
            self.activities_list[0].add_file('dummy_file_does_not_exist')

    def test_store_unique_before_setup(self, monkeypatch, caplog):
        a = self.activities_list[0]
        monkeypatch.setattr(a, 'setup_params', None)
        a.store_unique_metadata()
        assert 'setup_params has not been defined; call store_setup_params() ' \
               'prior to using this method. Nothing was done.' in caplog.text

    def test_as_xml(self):
        # setup a few values in the activity to trigger XML escaping:
        self.activities_list[0].setup_params['Acquisition Device'] = '<TEST>'
        self.activities_list[0].files[0] += '<&'
        self.activities_list[0].unique_meta[0]['Imaging Mode'] = '<IMAGING>'

        xml_str = self.activities_list[0].as_xml(seqno=0,
                                                 sample_id='sample_id',
                                                 indent_level=1, print_xml=True)


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
        # set session_handler to use test database
        monkeypatch.setattr(session_handler, "_nx_db_path", files['DB'])
        monkeypatch.setattr(nexusLIMS.db, "_nx_db_path", files['DB'])
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


class TestCDCS:
    def test_upload_and_delete_record(self):
        files_uploaded, record_ids = cdcs.upload_record_files([files['RECORD']])
        cdcs.delete_record(record_ids[0])

    def test_upload_and_delete_record_glob(self):
        prev_dir = os.getcwd()
        os.chdir(os.path.dirname(files['RECORD']))
        files_uploaded, record_ids = cdcs.upload_record_files(None)
        for id in record_ids:
            cdcs.delete_record(id)
        os.chdir(prev_dir)

    def test_upload_no_files_glob(self):
        prev_dir = os.getcwd()
        os.chdir(os.path.join(os.path.dirname(files['RECORD']), 'figs'))
        with pytest.raises(ValueError):
            files_uploaded, record_ids = cdcs.upload_record_files(None)
        os.chdir(prev_dir)

    def test_upload_file_bad_response(self, monkeypatch, caplog):
        Response = namedtuple('Response', 'status_code text')

        def mock_upload(xml_content, title):
            return Response(status_code=404,
                            text='This is a fake request error!'), 'dummy_id'
        monkeypatch.setattr(cdcs, 'upload_record_content', mock_upload)

        files_uploaded, record_ids = cdcs.upload_record_files([files['RECORD']])
        assert len(files_uploaded) == 0
        assert len(record_ids) == 0
        assert f'Could not upload {os.path.basename(files["RECORD"])}'

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
