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
"""
**Attributes**

Attributes
----------
instrument_db : dict
    A dictionary of :py:class:`~nexusLIMS.instruments.Instrument` objects.

    Each object in this dictionary represents an instrument detected in the
    NexusLIMS remote database.
"""
import datetime
from typing import Union

from nexusLIMS.utils import is_subpath as _is_subpath
import sqlite3 as _sql3
import contextlib as _contextlib
import os as _os
import logging as _logging
import pytz as _pytz

_logging.basicConfig()
_logger = _logging.getLogger(__name__)
_logger.setLevel(_logging.INFO)


def _get_instrument_db():
    """
    Connect to the NexusLIMS database and get a list of all the instruments
    contained within

    Returns
    -------
    instrument_db : dict
        A dictionary of `Instrument` instances that describe all the
        instruments that were found in the ``instruments`` table of the
        NexusLIMS database
    """
    query = "SELECT * from instruments"
    # use contextlib to auto-close the connection and database cursors
    with _contextlib.closing(_sql3.connect(
            _os.environ['nexusLIMS_db_path'])) as conn:
        with conn:  # auto-commits
            with _contextlib.closing(conn.cursor()) as cursor:  # auto-closes
                results = cursor.execute(query).fetchall()
                col_names = list(map(lambda x: x[0], cursor.description))

    instr_db = {}
    for l in results:
        this_dict = {}
        for key, val in zip(col_names, l):
            this_dict[key] = val

        key = this_dict.pop('instrument_pid')
        this_dict['name'] = key
        # remove keys from this_dict that we don't know about yet so we don't
        # crash and burn if a new column is added
        known_cols = \
            ['api_url', 'calendar_name', 'calendar_url', 'location',
             'name', 'schema_name', 'property_tag', 'filestore_path',
             'computer_ip', 'computer_name', 'computer_mount', 'harvester',
             'timezone']
        this_dict = {k: this_dict[k] for k in known_cols}
        instr_db[key] = Instrument(**this_dict)

    return instr_db


class Instrument:
    """
    A simple object to hold information about an instrument in the Microscopy
    Nexus facility, fetched from the external NexusLIMS database

    Parameters
    ----------
    api_url : str or None
        The calendar API url for this instrument
    calendar_name : str or None
        The "user-friendly" name of the calendar for this instrument as
        displayed on the sharepoint resource (e.g. "FEI Titan TEM")
    calendar_url : str or None
        The URL to this instrument's web-accessible calendar on the
        sharepoint resource
    location : str or None
        The physical location of this instrument (building and room number)
    name : str or None
        The unique identifier for an instrument in the Nexus Microscopy facility
    schema_name : str or None
        The name of instrument as defined in the Nexus Microscopy schema and
        displayed in the records
    property_tag : str or None
        The NIST property tag for this instrument
    filestore_path : str or None
        The path (relative to the Nexus facility root) on the central file
        storage where this instrument stores its data
    computer_name : str or None
        The name of the 'support PC' connected to this instrument
    computer_ip : str or None
        The REN IP address of the 'support PC' connected to this instrument
    computer_mount : str or None
        The full path where the files are saved on the 'support PC' for the
        instrument (e.g. 'M:/')
    harvester : str or None
        The sub-module of :py:mod:`~nexusLIMS.harvesters` to use to harvest
        calendar events
    timezone : pytz.timezone, str, or None
        The timezone (as in the tzdata database) where this instrument is
        located. Used for properly localizing the display of timestamps.
    """
    def __init__(self,
                 api_url=None,
                 calendar_name=None,
                 calendar_url=None,
                 location=None,
                 name=None,
                 schema_name=None,
                 property_tag=None,
                 filestore_path=None,
                 computer_ip=None,
                 computer_name=None,
                 computer_mount=None,
                 harvester=None,
                 timezone=None):
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
        self.computer_ip = computer_ip
        self.computer_name = computer_name
        self.computer_mount = computer_mount
        self.harvester = harvester
        if isinstance(timezone, str):
            self.timezone = _pytz.timezone(timezone)
        else:
            self.timezone = timezone

    def __repr__(self):
        return f'Nexus Instrument: {self.name}\n' \
               f'API url:          {self.api_url}\n' \
               f'Calendar name:    {self.calendar_name}\n' \
               f'Calendar url:     {self.calendar_url}\n' \
               f'Schema name:      {self.schema_name}\n' \
               f'Location:         {self.location}\n' \
               f'Property tag:     {self.property_tag}\n' \
               f'Filestore path:   {self.filestore_path}\n' \
               f'Computer IP:      {self.computer_ip}\n' \
               f'Computer name:    {self.computer_name}\n' \
               f'Computer mount:   {self.computer_mount}\n' \
               f'Harvester:        {self.harvester}\n' \
               f'Timezone:         {self.timezone}'

    def __str__(self):
        return f'{self.name}' + f' in {self.location}' if self.location else ''

    def localize_datetime(self, dt: datetime.datetime) -> datetime.datetime:
        """
        Convert a date and time to the timezone of this instrument. If the
        supplied datetime is naive (i.e. does not have a timezone), it will be
        assumed to already be in the timezone of the instrument, and the
        displayed time will not change. If the timezone of the supplied
        datetime is different than the instrument's, the time will be
        adjusted to compensate for the timezone offset.

        Parameters
        ----------
        dt
            The datetime object to localize

        Returns
        -------
        datetime.datetime
            A datetime object with the same timezone as the instrument
        """
        if self.timezone is None:
            _logger.warning(f"Tried to localize a datetime with instrument "
                            f"that does not have timezone information ("
                            f"{self.name})")
            return dt
        if dt.tzinfo is None:
            # dt is timezone naive
            return self.timezone.localize(dt)
        else:
            # dt has timezone info
            return dt.astimezone(self.timezone)

    def localize_datetime_str(self, dt: datetime.datetime,
                              fmt: str = '%Y-%m-%d %H:%M:%S %Z') -> str:
        """
        Convert a date and time to the timezone of this instrument, returning
        a textual representation of the object, rather than the datetime
        itself. Uses :py:meth:`localize_datetime` for the actual conversion.

        Parameters
        ----------
        dt
            The datetime object ot localize
        fmt
            The strftime format string to use to format the output

        Returns
        -------
        str
            The formatted textual representation of the localized datetime
        """
        return self.localize_datetime(dt).strftime(fmt)


instrument_db = _get_instrument_db()


def get_instr_from_filepath(path):
    """
    Using the NexusLIMS database, get an instrument object by a given path.

    Parameters
    ----------
    path : str
        A path (relative or absolute) to a file saved in the central
        filestore that will be used to search for a matching instrument

    Returns
    -------
    instrument : Instrument or None
        An `_Instrument` instance matching the path, or None if no match was
        found

    Examples
    --------
    >>> inst = get_instr_from_filepath('/mnt/***REMOVED***/Titan/***REMOVED***/' +
    ...                                '***REMOVED***/' +
    ...                                '***REMOVED***/4_330mm.dm3')
    >>> str(inst)
    'FEI-Titan-TEM-635816 in ***REMOVED***'
    """
    for k, v in instrument_db.items():
        if _is_subpath(path, _os.path.join(_os.environ["mmfnexus_path"],
                                           v.filestore_path)):
            return v

    return None


def get_instr_from_calendar_name(cal_name):
    """
    Using the NexusLIMS database, get an instrument object by a given path.

    Parameters
    ----------
    cal_name : str
        A calendar name (e.g. "FEITitanTEMEvents") that will be used to search
        for a matching instrument in the ``api_url`` values

    Returns
    -------
    instrument : Instrument or None
        An `_Instrument` instance matching the path, or None if no match was
        found

    Examples
    --------
    >>> inst = get_instr_from_calendar_name('FEITitanTEMEvents')
    >>> str(inst)
    'FEI-Titan-TEM-635816 in ***REMOVED***'
    """
    for k, v in instrument_db.items():
        if cal_name in v.api_url:
            return v

    return None


def get_instr_from_api_url(api_url: str) -> Union[None, Instrument]:
    """
    Using the NexusLIMS database, get an instrument object by a given api_url.

    Parameters
    ----------
    api_url
        An api_url (e.g. "FEITitanTEMEvents") that will be used to search
        for a matching instrument in the ``api_url`` values

    Returns
    -------
    Instrument
        An ``Instrument`` instance matching the ``api_url``, or ``None`` if no
        match was found

    Examples
    --------
    >>> inst = get_instr_from_api_url('https://***REMOVED***/api/tools/?id=1')
    >>> str(inst)
    'FEI-Titan-STEM-630901_n in ***REMOVED***'
    """
    for k, v in instrument_db.items():
        if api_url == v.api_url:
            return v

    return None
