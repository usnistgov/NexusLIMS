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

import urllib.parse as _urlparse
from nexusLIMS import calendar_root_url


def _get_cal_url(instr_id):
    cal_url = _urlparse.urljoin(f'{calendar_root_url}',
                                f'Lists/{instr_id}/calendar.aspx')
    return cal_url


def _get_api_url(instr_id):
    api_url = _urlparse.urljoin(f'{calendar_root_url}',
                                f'_vti_bin/ListData.svc/{instr_id}')
    return api_url


class _Instrument:
    """
    A simple object to hold information about an instrument in the Microscopy
    Nexus facility

    Attributes
    ----------
    api_url : str or None
    calendar_name : str or None
    calendar_url : str or None
    location : str or None
    name : str or None
    schema_name : str or None
    property_tag : str or None
    filestore_path : str or None
    """
    def __init__(self,
                 api_url=None,
                 calendar_name=None,
                 calendar_url=None,
                 location=None,
                 name=None,
                 schema_name=None,
                 property_tag=None,
                 filestore_path=None):
        """
        Create a new Instrument
        """
        self.api_url = api_url
        self.calendar_name = calendar_name
        self.calendar_url = calendar_url
        self.location = location
        self.name = name
        self.schema_name = schema_name
        self.property_tag = property_tag
        self.filestore_path = filestore_path

    def __repr__(self):
        return f'Nexus Instrument: {self.name}\n' \
               f'API url: {self.api_url}\n' \
               f'Calendar name: {self.calendar_name}\n' \
               f'Calendar url: {self.calendar_url}\n' \
               f'Schema name: {self.schema_name}\n' \
               f'Location: {self.location}\n' \
               f'Property tag: {self.property_tag}\n' \
               f'Filestore path: {self.filestore_path}'

    def __str__(self):
        return f'{self.name}' + f' in {self.location}' if self.location else ''


instrument_db = {
    'FEI-Helios-DB-636663':
        _Instrument(api_url=_get_api_url('FEIHeliosDBEvents'),
                    calendar_name='FEI HeliosDB',
                    calendar_url=_get_cal_url('FEI%20HeliosDB'),
                    location='***REMOVED***',
                    name='FEI-Helios-DB-636663',
                    schema_name='FEI Helios',
                    property_tag='636663',
                    filestore_path=None),
    'FEI-Quanta200-ESEM-633137':
        _Instrument(api_url=_get_api_url('FEIQuanta200Events'),
                    calendar_name='FEI Quanta200',
                    calendar_url=_get_cal_url('FEI%20Quanta200%20Events'),
                    location='***REMOVED***',
                    name='FEI-Quanta200-ESEM-633137',
                    schema_name='FEI Quanta200',
                    property_tag='633137',
                    filestore_path='./Quanta'),
    'FEI-Titan-STEM-630901':
        _Instrument(api_url=_get_api_url('FEITitanSTEMEvents'),
                    calendar_name='FEI Titan STEM',
                    calendar_url=_get_cal_url('MMSD%20Titan'),
                    location='***REMOVED***',
                    name='FEI-Titan-STEM-630901',
                    schema_name='FEI Titan STEM',
                    property_tag='630901',
                    filestore_path=None),
    'FEI-Titan-TEM-635816':
        _Instrument(api_url=_get_api_url('FEITitanTEMEvents'),
                    calendar_name='FEI Titan TEM',
                    calendar_url=_get_cal_url('FEI%20Titan%20Events'),
                    location='***REMOVED***',
                    name='FEI-Titan-TEM-635816',
                    schema_name='FEI Titan TEM',
                    property_tag='635816',
                    filestore_path='./Titan'),
    'Hitachi-S4700-SEM-606559':
        _Instrument(api_url=_get_api_url('HitachiS4700Events'),
                    calendar_name='Hitachi S4700',
                    calendar_url=_get_cal_url('Hitachi%20S4700%20Events'),
                    location='***REMOVED***',
                    name='Hitachi-S4700-SEM-606559',
                    schema_name='Hitachi S4700',
                    property_tag='606559',
                    filestore_path=None),
    'Hitachi-S5500-SEM-635262':
        _Instrument(api_url=_get_api_url('HitachiS5500Events'),
                    calendar_name='Hitachi-S5500',
                    calendar_url=_get_cal_url('HitachiS5500'),
                    location='***REMOVED***',
                    name='Hitachi-S5500-SEM-635262',
                    schema_name='Hitachi S5500',
                    property_tag='635262',
                    filestore_path=None),
    'JEOL-JEM3010-TEM-565989':
        _Instrument(api_url=_get_api_url('JEOLJEM3010Events'),
                    calendar_name='JEOL JEM3010',
                    calendar_url=_get_cal_url('JEOL%20JEM3010%20Events'),
                    location='***REMOVED***',
                    name='JEOL-JEM3010-TEM-565989',
                    schema_name='JEOL JEM3010',
                    property_tag='565989',
                    filestore_path='./JEOL3010'),
    'JEOL-JSM7100-SEM-N102656':
        _Instrument(api_url=_get_api_url('JEOLJSM7100Events'),
                    calendar_name='JEOL JSM7100',
                    calendar_url=_get_cal_url('JEOL%20JSM7100%20Events'),
                    location='***REMOVED***',
                    name='JEOL-JSM7100-SEM-N102656',
                    schema_name='JEOL JSM7100',
                    property_tag='N102656',
                    filestore_path='./7100Jeol'),
    'Philips-CM30-TEM-540388':
        _Instrument(api_url=_get_api_url('PhilipsCM30Events'),
                    calendar_name='Philips CM30',
                    calendar_url=_get_cal_url('Philips%20CM30%20Events'),
                    location='Unknown',
                    name='Philips-CM30-TEM-540388',
                    schema_name='Philips CM30',
                    property_tag='540388',
                    filestore_path=None),
    'Philips-EM400-TEM-599910':
        _Instrument(api_url=_get_api_url('PhilipsEM400Events'),
                    calendar_name='Philips EM400',
                    calendar_url=_get_cal_url('Philips%20EM400%20Events'),
                    location='***REMOVED***',
                    name='Philips-EM400-TEM-599910',
                    schema_name='Philips EM400',
                    property_tag='599910',
                    filestore_path=None)
}
