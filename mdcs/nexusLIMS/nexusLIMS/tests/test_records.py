import os
import nexusLIMS
from functools import partial

from nexusLIMS import mmf_nexus_root_path as _mmf_path
from nexusLIMS import cdcs
from nexusLIMS.instruments import instrument_db
from nexusLIMS.builder import record_builder as _rb
from nexusLIMS.utils import find_dirs_by_mtime
from nexusLIMS.db import session_handler
from lxml import etree as et
from uuid import UUID as _UUID
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

        # make record uploader just pretend by returning all files provided (
        # as if they were actually uploaded)
        monkeypatch.setattr(_rb, "_upload_record_files", lambda x: x)

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

    def test_new_session_bad_upload(self, monkeypatch, caplog):
        # set the methods used to determine if all records were uploaded to
        # just return known lists
        monkeypatch.setattr(_rb, 'build_new_session_records',
                            lambda: ['dummy_file1', 'dummy_file2',
                                     'dummy_file3'])
        monkeypatch.setattr(_rb, '_upload_record_files',
                            lambda x: [])

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


class TestActivity:
    pass


class TestCDCS:
    def test_bad_auth(self, monkeypatch):
        monkeypatch.setenv('nexusLIMS_user', 'baduser')
        monkeypatch.setenv('nexusLIMS_pass', 'badpass')
        with pytest.raises(AuthenticationError):
            cdcs.get_workspace_id()
        with pytest.raises(AuthenticationError):
            cdcs.get_template_id()

    #
    # def test_new_session_builder(self):
    #     _rb.build_new_session_records()
    #
    # def test_quanta_record_1(self):
    #     starting_time = _dt.fromisoformat('2019-12-23T08:40:50.484')
    #     ending_time = _dt.fromisoformat('2019-12-23T09:20:28.343')
    #     # Build the XML record and write it to a file
    #     filename = _rb.dump_record(instrument_db['FEI-Quanta200-ESEM-633137'],
    #                                starting_time,
    #                                ending_time,
    #                                filename=None)
    #
    # def test_quanta_record_2(self):
    #     starting_time = _dt.fromisoformat('2020-01-09T11:10:51.093')
    #     ending_time = _dt.fromisoformat('2020-01-09T14:02:30.000')
    #     # Build the XML record and write it to a file
    #     filename = _rb.dump_record(instrument_db['FEI-Quanta200-ESEM-633137'],
    #                                starting_time,
    #                                ending_time,
    #                                filename=None,
    #                                generate_previews=gen_prev)
    #
    # def test_quanta_record_3(self):
    #     starting_time = _dt.fromisoformat('2020-01-29+13:12:27.015')
    #     ending_time = _dt.fromisoformat('2020-01-29+17:12:42.438')
    #     # Build the XML record and write it to a file
    #     filename = _rb.dump_record(instrument_db['FEI-Quanta200-ESEM-633137'],
    #                                starting_time,
    #                                ending_time,
    #                                filename=None,
    #                                generate_previews=gen_prev)
    #
    #
    # def test_643_1(self):
    #     starting_time = _dt.fromisoformat('2020-01-21T14:18:58.393')
    #     ending_time = _dt.fromisoformat('2020-01-21T16:42:54.211')
    #     # Build the XML record and write it to a file
    #     filename = _rb.dump_record(instrument_db['FEI-Titan-STEM-630901'],
    #                                starting_time,
    #                                ending_time,
    #                                filename=None,
    #                                generate_previews=gen_prev)
    #
    # def test_642_***REMOVED***_with_cal(self):
    #     starting_time = _dt.fromisoformat('2020-01-28T09:18:52.093')
    #     ending_time = _dt.fromisoformat('2020-01-29T10:20:41.484')
    #     # Build the XML record and write it to a file
    #     filename = _rb.dump_record(instrument_db['FEI-Titan-TEM-635816'],
    #                                starting_time,
    #                                ending_time,
    #                                filename=None,
    #                                user='***REMOVED***',
    #                                generate_previews=gen_prev)
    #
    # def test_643_***REMOVED***_EELS_no_cal(self):
    #     starting_time = _dt.fromisoformat('2019-11-10T05:10:00')
    #     ending_time = _dt.fromisoformat('2019-11-10T10:29:17')
    #     # Build the XML record and write it to a file
    #     filename = _rb.dump_record(instrument_db['FEI-Titan-STEM-630901'],
    #                                starting_time,
    #                                ending_time,
    #                                filename=None,
    #                                date='2019-11-10',
    #                                user='***REMOVED***',
    #                                generate_previews=gen_prev)
    #
    # def test_record_builder(self):
    #
    #     # This will come from the database, but hard code for now
    #     starting_time = _dt(year=2018, month=11, day=13,
    #                         hour=13, minute=00)          # 2019-11-13 11:00 AM
    #     ending_time = _dt(year=2018, month=11, day=13,
    #                       hour=15, minute=30)            # 2019-11-13  3:30 PM
    #
    #     # Build the XML record and write it to a file
    #     filename = _rb.dump_record(instrument_db['FEI-Titan-TEM-635816'],
    #                                starting_time,
    #                                ending_time,
    #                                filename=None,
    #                                date='2018-11-13',
    #                                user='***REMOVED***',
    #                                generate_previews=gen_prev)
    #     # # Read the generated XML file using ElementTree
    #     # assert _os.path.isfile(filename)
    #     # record = et.parse(filename).getroot()
    #     # acq_acts = record.findall('acquisitionActivity')
    #     #
    #     # # Test some generated parts taken from the SharePoint calendar as well
    #     # # as from the microscope metadata
    #     # assert record.tag == f'{{{record.nsmap["nx"]}}}Experiment'
    #     # assert record[0].tag == 'title'
    #     # assert record.find('summary/experimenter').text == \
    #     #     '***REMOVED*** (Fed)'
    #     # assert record.find('summary/instrument').attrib['pid'] == \
    #     #     'FEI-Titan-TEM-635816'
    #     # assert record.find('summary/reservationEnd').text == \
    #     #     '2018-11-13T16:00:00'
    #     # assert record.find('sample/name').text == 'AM 17-4'
    #     # assert record.find('id').text == '470'
    #     # assert len(acq_acts) == 9
    #     # for aa in acq_acts:
    #     #     ids = aa.findall('sampleID')
    #     #     for id in ids:
    #     #         # If this raises an error, it's not a valid UUID
    #     #         val = _UUID(id.text, version=4)
    #
    #     # os.remove(filename)
    #
    # def test_old_643titan_record_builder(self):
    #     # This should pick out Andy's older NiCr tomography experiment
    #     starting_time = _dt.fromisoformat('2016-04-22T15:55:00.000')
    #     ending_time = _dt.fromisoformat('2016-04-22T17:30:00.000')
    #
    #     # Build the XML record and write it to a file
    #     filename = _rb.dump_record(instrument_db['FEI-Titan-STEM-630901'],
    #                                starting_time,
    #                                ending_time,
    #                                filename=None,
    #                                generate_previews=gen_prev)
    #
    #     # # # Read the generated XML file using ElementTree
    #     # assert _os.path.isfile(filename)
    #     # record = et.parse(filename).getroot()
    #     # acq_acts = record.findall('acquisitionActivity')
    #     # assert len(acq_acts) == 1
    #     # assert record.tag == f'{{{record.nsmap["nx"]}}}Experiment'
    #     # assert record[0].tag == 'title'
    #     #
    #     # # should be 13 datasets found
    #     # assert len(record.findall('acquisitionActivity/dataset')) == 13
    #     #
    #     # # there is no matching calendar info, so summary should be empty
    #     # assert len(record.find('summary').getchildren()) == 0
    #     #
    #     # # test some setup parameters
    #     # assert record.find('acquisitionActivity/setup/param['
    #     #                    '@name="Instrument ID"]').text == 'FEI-Titan-' \
    #     #                                                      'STEM-630901'
    #     # assert record.find('acquisitionActivity/setup/param['
    #     #                    '@name="Illumination Mode"]').text == 'STEM ' \
    #     #                                                          'NANOPROBE'
    #     # assert record.find('acquisitionActivity/setup/param['
    #     #                    '@name="GMS Version"]').text == '2.32.888.0'
    #
    # def test_new_643titan_record_builder(self):
    #     # This will come from the database, but hard code for testing to pick
    #     # out a recent (at the time this was written) experiment
    #     starting_time = _dt.fromisoformat('2020-01-29T12:10:39.010')
    #     ending_time = _dt.fromisoformat('2020-01-29T20:10:28.405')
    #
    #     dirs = find_dirs_by_mtime(_os.path.join(_mmf_path, '643Titan'),
    #                               starting_time, ending_time)
    #
    #     # Build the XML record and write it to a file
    #     filename = _rb.dump_record(instrument_db['FEI-Titan-STEM-630901'],
    #                                dt_from=starting_time,
    #                                dt_to=ending_time,
    #                                filename=None,
    #                                generate_previews=gen_prev)

        # # # Read the generated XML file using ElementTree
        # assert _os.path.isfile(filename)
        # record = et.parse(filename).getroot()
        # acq_acts = record.findall('acquisitionActivity')
        # assert len(acq_acts) == 1
        #
        # assert record.tag == f'{{{record.nsmap["nx"]}}}Experiment'
        # assert record[0].tag == 'title'
        # assert record.find('summary/experimenter').text == \
        #     'Johnston-Peck, Aaron C. (Fed)'
        # assert record.find('summary/instrument').attrib['pid'] == \
        #     'FEI-Titan-STEM-630901'
        # assert record.find('summary/reservationEnd').text == \
        #     '2020-01-29T19:00:00'
        # assert record.find('sample/name').text == 'Pd/Al2O3'
        # assert record.find('id').text == '171'
        #
        # # test some of the metadata found
        # assert len(record.findall('acquisitionActivity/dataset')) == 74
        # assert record.find('acquisitionActivity/setup/param['
        #                    '@name="Detector"]').text == 'GIF CCD'
        # assert record.find('acquisitionActivity/setup/param['
        #                    '@name="Illumination Mode"]').text == 'STEM ' \
        #                                                          'NANOPROBE'
        # assert record.find('acquisitionActivity/setup/param['
        #                    '@name="STEM Camera Length"]').text == '100.0'
        #
        # for aa in acq_acts:
        #     ids = aa.findall('sampleID')
        #     for id in ids:
        #         # If this raises an error, it's not a valid UUID
        #         val = _UUID(id.text, version=4)
