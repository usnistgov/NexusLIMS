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

from nexusLIMS import nexuslims_db_path
import sqlite3
import contextlib


def _get_instrument_db():
    """
    Connect to the NexusLIMS database and get a list of all the instruments
    contained within

    Returns
    -------
    instrument_db : dict
        A dictionary of `_Instrument` instances that describe all the
        instruments that were found in the ``instruments`` table of the
        NexusLIMS database
    """
    query = "SELECT * from instruments"
    # use contextlib to auto-close the connection and database cursors
    with contextlib.closing(sqlite3.connect(nexuslims_db_path)) as conn:
        with conn:  # auto-commits
            with contextlib.closing(conn.cursor()) as cursor:  # auto-closes
                results = cursor.execute(query).fetchall()
                col_names = list(map(lambda x: x[0], cursor.description))

    instr_db = {}
    for l in results:
        this_dict = {}
        for key, val in zip(col_names, l):
            this_dict[key] = val

        key = this_dict.pop('instrument_pid')
        this_dict['name'] = key
        instr_db[key] = _Instrument(**this_dict)

    return instr_db


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
                 filestore_path=None,
                 computer_ip=None,
                 computer_name=None,
                 computer_mount=None):
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

    def __repr__(self):
        return f'Nexus Instrument: {self.name}\n' \
               f'API url: {self.api_url}\n' \
               f'Calendar name: {self.calendar_name}\n' \
               f'Calendar url: {self.calendar_url}\n' \
               f'Schema name: {self.schema_name}\n' \
               f'Location: {self.location}\n' \
               f'Property tag: {self.property_tag}\n' \
               f'Filestore path: {self.filestore_path}\n' \
               f'Computer IP: {self.computer_ip}\n ' \
               f'Computer name: {self.computer_name}\n ' \
               f'Computer mount: {self.computer_mount}\n'

    def __str__(self):
        return f'{self.name}' + f' in {self.location}' if self.location else ''


instrument_db = _get_instrument_db()
