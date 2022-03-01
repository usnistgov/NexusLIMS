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

from typing import Union, List
from nexusLIMS.instruments import instrument_db as _instr_db, Instrument
import os as _os
from datetime import datetime as _dt
import sqlite3 as _sql3
import contextlib as _contextlib
import logging as _logging

_logger = _logging.getLogger(__name__)


def db_query(query, args=None):
    if args is None:
        args = tuple()
    success = False
    with _contextlib.closing(_sql3.connect(
            _os.environ['nexusLIMS_db_path'])) as conn:
        with conn:  # auto-commits
            with _contextlib.closing(conn.cursor()) as cursor:
                results = cursor.execute(query, args).fetchall()
                success = True
    return success, results


class SessionLog:
    """
    A simple mapping of one row in the ``session_log`` table of the NexusLIMS
    database (all values are strings)

    Parameters
    ----------
    session_identifier
         A unique string that is consistent among a single
         record's `"START"`, `"END"`, and `"RECORD_GENERATION"` events (often a
         UUID, but is not required to be so)
    instrument
        The instrument associated with this session (foreign key reference to
        the ``instruments`` table)
    timestamp
        The ISO format timestamp representing the date and time of the logged
        event
    event_type
        The type of log for this session (either `"START"`, `"END"`,
        or `"RECORD_GENERATION"`)
    user
        The NIST "short style" username associated with this session (if known)
    record_status
        The status to use for this record (defaults to ``'TO_BE_BUILT'``
    """
    def __init__(self, session_identifier: str, instrument: str,
                 timestamp: str, event_type: str, user: str,
                 record_status: Union[str, None] = None):
        self.session_identifier = session_identifier
        self.instrument = instrument
        self.timestamp = timestamp
        self.event_type = event_type
        self.user = user
        self.record_status = record_status if record_status else 'TO_BE_BUILT'

    def __repr__(self):
        return f"SessionLog (id={self.session_identifier}, " \
               f"instrument={self.instrument}, " \
               f"timestamp={self.timestamp}, " \
               f"event_type={self.event_type}, " \
               f"user={self.user}, " \
               f"record_status={self.record_status})"

    def insert_log(self) -> bool:
        """
        Inserts a log into the database with the information contained within
        this SessionLog's attributes (used primarily for NEMO ``usage_event``
        integration). It will check for the presence of a matching record first
        and warn without inserting anything if it finds one.

        Returns
        -------
        success : bool
            Whether or not the session log row was inserted successfully
        """
        query = "SELECT * FROM session_log " \
                "WHERE session_identifier=? AND " \
                "instrument=? AND " \
                "timestamp=? AND " \
                "event_type=? AND " \
                "record_status=? AND " \
                "user=?"
        args = (self.session_identifier, self.instrument, self.timestamp,
                self.event_type, self.record_status, self.user)

        success, results = db_query(query, args)
        if results:
            # There was a matching record in the DB, so warn and return success
            _logger.warning(f"SessionLog already existed in DB, so no "
                            f"row was added: {self}")
            return success

        query = "INSERT INTO session_log(session_identifier, instrument, " \
                "timestamp, event_type, record_status, user) VALUES " \
                "(?, ?, ?, ?, ?, ?)"
        success, results = db_query(query, args)

        return success


class Session:
    """
    A record of an individual session as read from the Nexus Microscopy
    facility session database. Created by combining two
    :py:class:`~nexusLIMS.db.session_handler.SessionLog` objects with status
    ``"TO_BE_BUILT"``.

    Parameters
    ----------
    session_identifier : str
        The unique identifier for an individual session on an instrument
    instrument : Instrument
        An object representing the instrument associated with this session
    dt_from : datetime.datetime
        A :py:class:`~datetime.datetime` object representing the start of this
        session
    dt_to : datetime.datetime
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
            Whether the update operation was successful
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

    def insert_record_generation_event(self) -> dict:
        """
        Insert a log for this session into the session database with
        ``event_type`` `"RECORD_GENERATION"` and the current time (with local
        system timezone) as the timestamp.

        Returns
        -------
        res : dict
            A dictionary containing the results from the query to check that
            a RECORD_GENERATION event was added
        """
        _logger.debug(f'Logging RECORD_GENERATION for '
                      f'{self.session_identifier}')
        insert_query = "INSERT INTO session_log " \
                       "(instrument, event_type, session_identifier, " \
                       "user, timestamp) VALUES (?, ?, ?, ?, ?)"
        args = (self.instrument.name, 'RECORD_GENERATION',
                self.session_identifier, _os.getenv('nexusLIMS_user'),
                _dt.now().astimezone())
        success = False

        # use contextlib to auto-close the connection and database cursors
        with _contextlib.closing(_sql3.connect(
                _os.environ['nexusLIMS_db_path'])) as conn:
            with conn:  # auto-commits
                with _contextlib.closing(
                        conn.cursor()) as cursor:  # auto-closes
                    results = cursor.execute(insert_query, args)

        check_query = "SELECT id_session_log, event_type, " \
                      "session_identifier, timestamp FROM session_log " \
                      "WHERE instrument = ?" \
                      "AND event_type = ?" \
                      "ORDER BY timestamp DESC LIMIT 1"
        args = (self.instrument.name, 'RECORD_GENERATION')

        # use contextlib to auto-close the connection and database cursors
        with _contextlib.closing(_sql3.connect(
                _os.environ['nexusLIMS_db_path'])) as conn:
            conn.row_factory = _sql3.Row
            with conn:  # auto-commits
                with _contextlib.closing(
                        conn.cursor()) as cursor:  # auto-closes
                    results = cursor.execute(check_query, args)
                    res = results.fetchone()

        event_match = res['event_type'] == 'RECORD_GENERATION'
        id_match = res['session_identifier'] == self.session_identifier
        if event_match and id_match:
            _logger.debug(f'Confirmed RECORD_GENERATION insertion for'
                          f' {self.session_identifier}')
            success = True

        return dict(res)


def get_sessions_to_build() -> List[Session]:
    """
    Query the NexusLIMS database for pairs of logs with status
    ``'TO_BE_BUILT'`` and return the information needed to build a record for
    that session

    Returns
    -------
    sessions : List[Session]
        A list of :py:class:`~nexusLIMS.db.session_handler.Session` objects
        containing the sessions that the need their record built. Will be an
        empty list if there's nothing to do.
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
            raise ValueError(f"There was not exactly one 'END' log for this "
                             f"'START' log; len(el_list) was {len(el_list)};"
                             f"sl was {sl}; el_list was {el_list}")

        el = el_list[0]
        dt_from = _dt.fromisoformat(sl.timestamp)
        dt_to = _dt.fromisoformat(el.timestamp)
        session = Session(session_identifier=sl.session_identifier,
                          instrument=_instr_db[sl.instrument],
                          dt_from=dt_from, dt_to=dt_to, user=sl.user)
        sessions.append(session)

    _logger.info(f'Found {len(sessions)} new sessions to build')
    return sessions
