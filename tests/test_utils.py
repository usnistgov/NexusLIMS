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

from nexusLIMS.utils import *
from nexusLIMS.utils import _zero_bytes
from nexusLIMS.extractors import extension_reader_map as _ext
from nexusLIMS.extractors import quanta_tif
from datetime import datetime
from requests import get
import os
import sys
from io import BytesIO
from lxml import etree
import pytest
import logging
from datetime import timedelta as _td


class TestUtils:
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

    def test_find_dirs_by_mtime(self, fix_mountain_time, monkeypatch):
        path = os.path.join(os.environ["mmfnexus_path"], "JEOL3010")
        dt_from = datetime.fromisoformat("2019-07-24T11:00:00.000")
        dt_to = datetime.fromisoformat("2019-07-24T16:00:00.000")
        dirs = find_dirs_by_mtime(path, dt_from, dt_to)

        assert len(dirs) == 3
        for d in ['JEOL3010/***REMOVED***/***REMOVED***/20190724/M1_DC_Beam',
                  'JEOL3010/***REMOVED***/***REMOVED***/20190724/M2_DC_Beam_Dose_1',
                  'JEOL3010/***REMOVED***/***REMOVED***/20190724/M3_DC_Beam_Dose_2']:
            assert os.path.join(path, d) in dirs

    def test_gnu_find(self, fix_mountain_time):
        files = gnu_find_files_by_mtime(
            os.path.join(os.environ["mmfnexus_path"], "Titan"),
            dt_from=datetime.fromisoformat("2018-11-13T13:00:00.000"),
            dt_to=datetime.fromisoformat("2018-11-13T16:00:00.000"),
            extensions=_ext.keys()
        )

        assert len(files) == 37

    def test_gnu_and_pure_find_together(self):
        # both file-finding methods should return the same list (when sorted
        # by mtime) for the same path and date range
        path = os.path.join(os.environ["mmfnexus_path"], "JEOL3010")
        dt_from = datetime.fromisoformat("2019-07-24T11:00:00.000")
        dt_to = datetime.fromisoformat("2019-07-24T16:00:00.000")
        gnu_files = gnu_find_files_by_mtime(path, dt_from=dt_from,
                                            dt_to=dt_to, extensions=_ext.keys())
        find_files = find_files_by_mtime(path, dt_from=dt_from, dt_to=dt_to)

        gnu_files = sorted(gnu_files)
        find_files = sorted(find_files)

        assert len(gnu_files) == 55
        assert len(find_files) == 55
        assert gnu_files == find_files

    def test_gnu_find_not_implemented(self, monkeypatch):
        monkeypatch.setattr(sys, 'platform', 'win32')

        with pytest.raises(NotImplementedError):
            files = gnu_find_files_by_mtime(
                os.path.join(os.environ["mmfnexus_path"], "643Titan"),
                dt_from=datetime.fromisoformat("2019-11-06T15:00:00.000"),
                dt_to=datetime.fromisoformat("2019-11-06T18:00:00.000"),
                extensions=_ext.keys())

    def test_gnu_find_not_on_path(self, monkeypatch):
        monkeypatch.setenv('PATH', '.')

        with pytest.raises(RuntimeError) as e:
            files = gnu_find_files_by_mtime(
                os.path.join(os.environ["mmfnexus_path"], "643Titan"),
                dt_from=datetime.fromisoformat("2019-11-06T15:00:00.000"),
                dt_to=datetime.fromisoformat("2019-11-06T18:00:00.000"),
                extensions=_ext.keys())
        assert str(e.value) == 'find command was not found on the system PATH'

    def test_gnu_find_stderr(self):
        with pytest.raises(RuntimeError) as e:
            # bad path should cause output to stderr, which should raise error
            files = gnu_find_files_by_mtime(
                '...............',
                dt_from=datetime.fromisoformat("2019-11-06T15:00:00.000"),
                dt_to=datetime.fromisoformat("2019-11-06T18:00:00.000"),
                extensions=_ext.keys())
        assert '...............' in str(e.value)

    def test_zero_bytes(self):
        import gzip
        import shutil
        TEST_FILE = os.path.join(
            os.path.dirname(__file__), "files", "quad1image_001.tif")

        new_fname = _zero_bytes(TEST_FILE, 0, 973385)

        # try compressing old and new to ensure size is improved
        new_gz = new_fname + '.gz'
        old_gz = TEST_FILE + '.gz'
        with open(TEST_FILE, 'rb') as f_in:
            with gzip.open(old_gz, 'wb') as f_out:
                shutil.copyfileobj(f_in, f_out)
        with open(new_fname, 'rb') as f_in:
            with gzip.open(new_gz, 'wb') as f_out:
                shutil.copyfileobj(f_in, f_out)
        new_gz_size = os.stat(new_gz).st_size
        old_gz_size = os.stat(old_gz).st_size
        assert new_gz_size < old_gz_size

        # check to ensure metadata remains the same
        mdata_new = quanta_tif.get_quanta_metadata(new_fname)
        mdata_old = quanta_tif.get_quanta_metadata(TEST_FILE)
        del mdata_old['nx_meta']['Creation Time']
        del mdata_new['nx_meta']['Creation Time']
        assert mdata_new == mdata_old

        os.remove(new_gz)
        os.remove(new_fname)
        os.remove(old_gz)

    def test_zero_bytes_ser_processing(self):
        TEST_FILE = os.path.join(
            os.path.dirname(__file__), "files",
            "***REMOVED***12_no_accompanying_emi_dataZeroed_1.ser")
        # zero a selection of bytes (doesn't matter which ones)
        new_fname = _zero_bytes(TEST_FILE, 0, 973385)
        assert new_fname == os.path.join(
            os.path.dirname(__file__), "files",
            "***REMOVED***12_no_accompanying_emi_dataZeroed_dataZeroed_1.ser")
        os.remove(new_fname)

    def test_setup_loggers(self):
        setup_loggers(logging.DEBUG)
        assert logging.getLogger(
            'nexusLIMS').getEffectiveLevel() == logging.DEBUG
        assert logging.getLogger(
            'nexusLIMS.extractors').getEffectiveLevel() == logging.DEBUG

    def test_bad_auth_options(self):
        with pytest.raises(ValueError):
            # giving
            nexus_req("http://example.com", get, basic_auth=True,
                      token_auth='test')

    def test_header_addition_nexus_req(self):
        r = nexus_req(os.environ['NEMO_address_1'], get,
                      token_auth=os.environ['NEMO_token_1'],
                      headers={'test_header': 'test_header_val'})
        assert 'test_header' in r.request.headers
        assert r.request.headers['test_header'] == 'test_header_val'
        assert 'users' in r.json()

    def test_has_delay_passed_no_val(self, monkeypatch, caplog):
        monkeypatch.setenv('nexusLIMS_file_delay_days', 'bad_float')
        assert not has_delay_passed(datetime.now())
        assert 'The environment variable value of nexusLIMS_file_delay_days' \
               in caplog.text
