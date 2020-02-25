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

from nexusLIMS.instruments import instrument_db as _instr_db
import os as _os
from datetime import datetime as _dt
import sqlite3 as _sql3
import contextlib as _contextlib
import logging as _logging

_logger = _logging.getLogger(__name__)


class SessionLog:
    """
    A simple mapping of one row in the ``session_log`` table of the NexusLIMS
    database (all values are strings)

    Parameters
    ----------
    session_identifier : str
         A UUID4 (36-character string) that is consistent among a single
         record's `"START"`, `"END"`, and `"RECORD_GENERATION"` events
    instrument : str
        The instrument associated with this session (foreign key reference to
        the ``instruments`` table)
    timestamp : str
        The ISO format timestamp representing the date and time of the logged
        event
    event_type : str
        The type of log for this session (either `"START"`, `"END"`,
        or `"RECORD_GENERATION"`)
    user : str
        The NIST "short style" username associated with this session (if known)
    """
    def __init__(self, session_identifier, instrument,
                 timestamp, event_type, user):
        self.session_identifier = session_identifier
        self.instrument = instrument
        self.timestamp = timestamp
        self.event_type = event_type
        self.user = user


class Session:
    """
    A record of an individual session as read from the Nexus Microscopy
    facility session database. Created by combining two
    :py:class:`~nexusLIMS.db.session_handler.SessionLog` objects with status
    ``"TO_BE_BUILT"``.

    Parameters
    ----------
    session_identifier : str
        The UUIDv4 identifier for an individual session on an instrument
    instrument : ~nexusLIMS.instruments.Instrument
        An object representing the instrument associated with this session
    dt_from : :py:class:`~datetime.datetime`
        A :py:class:`~datetime.datetime` object representing the start of this
        session
    dt_to : :py:class:`~datetime.datetime`
        A :py:class:`~datetime.datetime` object representing the end of this
        session
    user : str
        The username associated with this session (may not be trustworthy)
    """
    def __init__(self, session_identifier, instrument, dt_from, dt_to, user):
        self.session_identifier = session_identifier
        self.instrument = instrument
        self.dt_from = dt_from
        self.dt_to = dt_to
        self.user = user

    def __repr__(self):
        return f'{self.dt_from.isoformat()} to {self.dt_to.isoformat()} on ' \
               f'{self.instrument.name}'

    def update_session_status(self, status):
        """
        Update the ``record_status`` in the session logs for this
        :py:class:`~nexusLIMS.db.session_handler.Session`

        Parameters
        ----------
        status : str
            One of `"COMPLETED"`, `"WAITING_FOR_END"`, `"TO_BE_BUILT"`,
            `"ERROR"`, `"NO_FILES_FOUND"` (the allowed values in the
            NexusLIMS database). Status value will be validated by the database

        Returns
        -------
        success : bool
            Whether or not the update operation was successful
        """
        update_query = f"UPDATE session_log SET record_status = '{status}' " \
                       f"WHERE session_identifier = '{self.session_identifier}'"
        success = False

        # use contextlib to auto-close the connection and database cursors
        with _contextlib.closing(_sql3.connect(
                _os.environ['nexusLIMS_db_path'])) as conn:
            with conn:  # auto-commits
                with _contextlib.closing(
                        conn.cursor()) as cursor:  # auto-closes
                    results = cursor.execute(update_query)
                    success = True

        return success

    def insert_record_generation_event(self):
        """
        Insert a log for this sesssion into the session database with
        ``event_type`` `"RECORD_GENERATION"`

        Returns
        -------
        success : bool
            Whether or not the update operation was successful
        """
        _logger.debug(f'Logging RECORD_GENERATION for '
                      f'{self.session_identifier}')
        insert_query = f"INSERT INTO session_log " \
                       f"(instrument, event_type, session_identifier, user) " \
                       f"VALUES ('{self.instrument.name}', " \
                       f"'RECORD_GENERATION', '{self.session_identifier}', " \
                       f"'{_os.environ['nexusLIMS_user']}');"
        success = False

        # use contextlib to auto-close the connection and database cursors
        with _contextlib.closing(_sql3.connect(
                _os.environ['nexusLIMS_db_path'])) as conn:
            with conn:  # auto-commits
                with _contextlib.closing(
                        conn.cursor()) as cursor:  # auto-closes
                    results = cursor.execute(insert_query)

        check_query = f"SELECT event_type, session_identifier, " \
                      f"id_session_log, " \
                      f"timestamp FROM session_log " \
                      f"WHERE instrument = '{self.instrument.name}' " \
                      f"AND event_type = 'RECORD_GENERATION'" \
                      f"ORDER BY timestamp DESC LIMIT 1;"

        # use contextlib to auto-close the connection and database cursors
        with _contextlib.closing(_sql3.connect(
                _os.environ['nexusLIMS_db_path'])) as conn:
            with conn:  # auto-commits
                with _contextlib.closing(
                        conn.cursor()) as cursor:  # auto-closes
                    results = cursor.execute(check_query)
                    res = results.fetchone()

        if res[0:2] == ('RECORD_GENERATION', self.session_identifier):
            _logger.debug(f'Confirmed RECORD_GENERATION insertion for'
                          f' {self.session_identifier}')
            success = True

        return success


def get_sessions_to_build():
    """
    Query the NexusLIMS database for pairs of logs with status
    ``'TO_BE_BUILT'`` and return the information needed to build a record for
    that session

    Returns
    -------
    sessions : list
        A list of :py:class:`~nexusLIMS.db.session_handler.Session` objects
        containing the sessions that the need their record built
    """
    sessions = []

    db_query = "SELECT session_identifier, instrument, timestamp, " \
               "event_type, user " \
               "FROM session_log WHERE record_status == 'TO_BE_BUILT'"

    # use contextlib to auto-close the connection and database cursors
    with _contextlib.closing(_sql3.connect(
            _os.environ['nexusLIMS_db_path'])) as conn:
        with conn:  # auto-commits
            with _contextlib.closing(conn.cursor()) as cursor:  # auto-closes
                results = cursor.execute(db_query).fetchall()
                col_names = list(map(lambda x: x[0], cursor.description))

    session_logs = [SessionLog(*i) for i in results]
    start_logs = [sl for sl in session_logs if sl.event_type == 'START']
    end_logs = [sl for sl in session_logs if sl.event_type == 'END']

    for sl in start_logs:
        # for every log that has a 'START', there should be one corresponding
        # log with 'END' that has the same session identifier. If not,
        # the database is in an inconsistent state and we should know about it
        el_list = [el for el in end_logs if el.session_identifier ==
                   sl.session_identifier]
        if len(el_list) != 1:
            # TODO: we should do something more intelligent here than just
            #  raising an error
            raise ValueError()

        el = el_list[0]
        dt_from = _dt.fromisoformat(sl.timestamp)
        dt_to = _dt.fromisoformat(el.timestamp)
        session = Session(session_identifier=sl.session_identifier,
                          instrument=_instr_db[sl.instrument],
                          dt_from=dt_from, dt_to=dt_to, user=sl.user)
        sessions.append(session)

    _logger.info(f'Found {len(sessions)} new sessions to build')
    return sessions
