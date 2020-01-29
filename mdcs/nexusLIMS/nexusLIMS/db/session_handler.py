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
from nexusLIMS import nexuslims_db_path as _nx_db_path
from nexusLIMS import mmf_nexus_root_path as _mmf_path
from datetime import datetime as _dt
from collections import namedtuple as _nt
import sqlite3 as _sql3
import contextlib as _contextlib
import logging as _logging

_logger = _logging.getLogger(__name__)

# use a couple namedtuples to keep track of information pulled from the database

# SessionLog is just a simple mapping of one row in the session_log table of
# the NexusLIMS database (all values are strings - instrument is the instr. PID)
SessionLog = _nt('SessionLog', 'session_identifier instrument timestamp '
                               'event_type user')

# Session is like above, but with combining two logs with status "TO_BE_BUILT"
# into one session with start and end points as datetime objects
# session_identifier and user are strings
# instrument is a nexusLIMS.instruments.Instrument object
# dt_from and dt_to are datetime.datetime objects
Session = _nt('Session', 'session_identifier instrument dt_from dt_to user')


def get_sessions_to_build():
    """
    Query the NexusLIMS database for pairs of logs with status
    ``'TO_BE_BUILT'`` and return the information needed to build a record for
    that session

    Returns
    -------
    sessions : list
        A list of ``namedtuple``s containing the sessions that the need their
        record built
    """
    sessions = []

    db_query = "SELECT session_identifier, instrument, timestamp, " \
               "event_type, user " \
               "FROM session_log WHERE record_status == 'TO_BE_BUILT'"

    # use contextlib to auto-close the connection and database cursors
    with _contextlib.closing(_sql3.connect(_nx_db_path)) as conn:
        with conn:  # auto-commits
            with _contextlib.closing(conn.cursor()) as cursor:  # auto-closes
                results = cursor.execute(db_query).fetchall()
                col_names = list(map(lambda x: x[0], cursor.description))
                # unpack each result into a namedtuple

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

    return sessions
