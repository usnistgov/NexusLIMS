#  NIST Public License - 2019
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

import os
from nexusLIMS.instruments import *


class TestInstruments:
    def test_getting_instruments(self):
        assert isinstance(instrument_db, dict)

    def test_database_contains_instruments(self):
        from nexusLIMS.instruments import instrument_db
        instruments_to_test = ['FEI-Helios-DB-636663_n',
                               'FEI-Quanta200-ESEM-633137_n',
                               'FEI-Titan-STEM-630901_n',
                               'FEI-Titan-TEM-635816_n',
                               'Hitachi-S5500-SEM-635262_n',
                               'JEOL-JEM3010-TEM-565989_n',
                               'JEOL-JSM7100-SEM-N102656_n',
                               'Philips-EM400-TEM-599910_n']
        for i in instruments_to_test:
            assert i in instrument_db
            assert isinstance(instrument_db[i], Instrument)

        assert 'some_random_instrument' not in instrument_db

    def test_instrument_str(self):
        assert \
            str(instrument_db['FEI-Titan-TEM-635816_n']) == \
            'FEI-Titan-TEM-635816_n in ***REMOVED***'

    def test_instrument_repr(self):
        assert \
            repr(instrument_db['FEI-Titan-TEM-635816_n']) == \
            f'Nexus Instrument: FEI-Titan-TEM-635816_n\n' + \
            f'API url:          https://***REMOVED***/api/tools/?id=3\n' + \
            f'Calendar name:    FEI Titan TEM\n' + \
            f'Calendar url:     https://***REMOVED***/calendar/\n' + \
            f'Schema name:      FEI Titan TEM\n' \
            f'Location:         ***REMOVED***\n' \
            f'Property tag:     635816\n' \
            f'Filestore path:   ./Titan\n' \
            f'Computer IP:      None\n' \
            f'Computer name:    None\n' \
            f'Computer mount:   None\n' \
            f'Harvester:        nemo\n' \
            f'Timezone:         America/New_York'

    def test_get_instr_from_filepath(self):
        path = os.path.join(os.environ['mmfnexus_path'],
                            'Titan/***REMOVED***/***REMOVED***/'
                            '***REMOVED***/4_330mm.dm3')
        instr = get_instr_from_filepath(path)
        assert isinstance(instr, Instrument)
        assert instr.name == 'FEI-Titan-TEM-635816_n'

        instr = get_instr_from_filepath('bad_path_no_instrument')
        assert instr is None

    def test_get_instr_from_cal_name(self):
        instr = get_instr_from_calendar_name('id=3')
        assert isinstance(instr, Instrument)
        assert instr == instrument_db['FEI-Titan-TEM-635816_n']

    def test_get_instr_from_cal_name_none(self):
        instr = get_instr_from_calendar_name('bogus calendar name')
        assert instr is None

    def test_instrument_datetime_location_no_tz(self, monkeypatch, caplog):
        instr = instrument_db['FEI-Titan-TEM-635816_n']
        monkeypatch.setattr(instr, 'timezone', None)
        dt_naive = datetime.datetime.fromisoformat('2021-11-26T12:00:00.000')
        assert instr.localize_datetime(dt_naive) == dt_naive
        assert "Tried to localize a datetime with instrument" in caplog.text

    def test_instrument_datetime_localization(self):
        instr = instrument_db['FEI-Titan-TEM-635816_n']
        # instr timezone should be Eastern Time

        dt_naive = datetime.datetime.fromisoformat('2021-11-26T12:00:00.000')
        dt_mt = datetime.datetime.fromisoformat('2021-11-26T12:00:00.000-07:00')
        dt_et = datetime.datetime.fromisoformat('2021-11-26T12:00:00.000-05:00')

        def _strftime(dt):
            return dt.strftime('%Y-%m-%d %H:%M:%S %Z')

        assert _strftime(instr.localize_datetime(dt_naive)) == \
               '2021-11-26 12:00:00 EST'
        assert _strftime(instr.localize_datetime(dt_mt)) == \
               '2021-11-26 14:00:00 EST'
        assert _strftime(instr.localize_datetime(dt_et)) == \
               '2021-11-26 12:00:00 EST'

    def test_instrument_datetime_localization_str(self):
        instr = instrument_db['FEI-Titan-TEM-635816_n']
        dt_naive = datetime.datetime.fromisoformat('2021-11-26T12:00:00.000')
        dt_mt = datetime.datetime.fromisoformat('2021-11-26T12:00:00.000-07:00')
        dt_et = datetime.datetime.fromisoformat('2021-11-26T12:00:00.000-05:00')

        assert instr.localize_datetime_str(dt_naive) == \
               '2021-11-26 12:00:00 EST'
        assert instr.localize_datetime_str(dt_mt) == \
               '2021-11-26 14:00:00 EST'
        assert instr.localize_datetime_str(dt_et) == \
               '2021-11-26 12:00:00 EST'

    def test_instrument_from_api_url(self):
        returned_item = get_instr_from_api_url('https://***REMOVED***/api/'
                                               'tools/?id=10')
        assert returned_item == instrument_db['testsurface-CPU_P1111111']

    def test_instrument_from_api_url_none(self):
        returned_item = get_instr_from_api_url('https://***REMOVED***/api/'
                                               'tools/?id=-1')
        assert returned_item is None
