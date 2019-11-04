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

import sqlite3
import sys
import re
import datetime
import os
import argparse
import subprocess
import time

testing = False

db_path = '\\***REMOVED***\\nexuslims'

db_name = 'nexuslims_db.sqlite'
password = os.environ['***REMOVED***']
verbosity = 0
ip_regex = r'(?:(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}' \
           r'(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)'


def log(to_print, this_verbosity):
    """
    Log a message to the console, only printing if the given verbosity is
    equal to or lower than the global threshold

    Parameters
    ----------
    to_print : str
        The message to log
    this_verbosity : int
        The verbosity level (higher is more verbose)
    """
    level_dict = {0: 'WARN', 1: 'INFO', 2: 'DEBUG'}
    if this_verbosity <= verbosity:
        print(f'{datetime.datetime.now().isoformat()}'
              f':{level_dict[this_verbosity]}: '
              f'{to_print}')


def get_computer_name():
    return os.environ['COMPUTERNAME']


def mount_network_share():
    # disconnect anything mounted at "N:/"
    log('unmounting existing N:', 2)
    p = subprocess.run(r'net use N: /delete /y', shell=True,
                       capture_output=True)
    # Connect to shared drive, windows does not allow multiple connections to
    # the same server, but you can trick it by using IP address instead of
    # DNS name...
    log('getting ip of cfse', 2)
    p = subprocess.run(r'nslookup ***REMOVED***', shell=True,
                       capture_output=True)
    ips = re.findall(ip_regex, str(p.stdout))
    if len(ips) == 1:
        ip = ips[0]
    else:
        raise ConnectionError('Could not find IP of network share')
    log(f'found ***REMOVED*** at {ip}', 2)
    log('mounting N:', 2)

    # mounting requires a security policy:
    # https://support.microsoft.com/en-us/help/968264/error-message-when-you-
    # try-to-map-to-a-network-drive-of-a-dfs-share-by
    mount_command = f'net use N: \\\\{ip}{db_path} ' + \
                    f'/user:NIST\\***REMOVED*** ***************'
    if testing:
        mount_command = f'net use N: \\\\{ip}{db_path} /user:NIST\\***REMOVED***'

    log(f'using "{mount_command}', 2)
    p = subprocess.run(mount_command, shell=True, capture_output=True)
    if p.stderr:
        log(str(p.stderr), 0)
        if '1312' in str(p.stderr):
            log('Visit https://support.microsoft.com/en-us/help/968264/error-'
                'message-when-you-try-to-map-to-a-network-drive-of-a-dfs'
                '-share-by\n'
                'to see how to allow mounting network drives as another user',
                0)
        raise ConnectionError('Could not mount network share to access '
                              'database')


def umount_network_share():
    log('unmounting N:', 2)
    p = subprocess.run(r'net use N: /del /y', shell=True, capture_output=True)
    if p.stderr:
        log(str(p.stderr), 0)


def get_instr_pid():
    # Get the instrument pid from the computer name of this computer
    with sqlite3.connect(f"N:\\{db_name}") as con:
        res = con.execute('SELECT instrument_pid from instruments WHERE '
                          f'computer_name is \'{get_computer_name()}\'')
        instrument_pid = res.fetchone()[0]
        log(f'Found instrument ID: {instrument_pid} using'
            f' {get_computer_name()}', 1)
    return instrument_pid


def process_start(instrument_pid, user=None):
    """
    Insert a session log for this computer's instrument with the given user
    (if provided)

    Parameters
    ----------
    instrument_pid : str
        The PID of the instrument to add a session log for
    user : str
        The user to attach to this record

    Returns
    -------
    id_session_log : int
        The id number of the session log that was added
    """
    insert_statement = "INSERT INTO session_log (instrument, event_type" + \
                       (", user)" if user else ") ") + \
                       f"VALUES ('{instrument_pid}', 'START'" + \
                       (f", '{user}');" if user else ");")

    log(f'insert_statement: {insert_statement}', 2)

    with sqlite3.connect(f"N:\\{db_name}") as con:
        _ = con.execute(insert_statement)
        res = con.execute('SELECT * FROM session_log WHERE '
                          'id_session_log = last_insert_rowid();')
        id_session_log = res.fetchone()
        log(f'Inserted row {id_session_log}', 1)


def process_end(instrument_pid, user=None):
    user_string = f"AND user='{user}'" if user else ''

    insert_statement = "INSERT INTO session_log (instrument, event_type, " \
                       "record_status" + \
                       (", user) " if user else ") ") + \
                       f"VALUES ('{instrument_pid}', 'END', 'TO_BE_BUILT'" + \
                       (f", '{user}');" if user else ");")

    # Get the most recent 'START' entry for this instrument
    get_last_start_id_query = f"SELECT id_session_log FROM session_log " \
                              f"WHERE instrument = '{instrument_pid}' AND " \
                              f"event_type = 'START' {user_string} AND " \
                              f"record_status = 'WAITING_FOR_END'" \
                              f"ORDER BY timestamp DESC " \
                              f"LIMIT 1;"
    log(f'query: {get_last_start_id_query}', 2)
    with sqlite3.connect(f"N:\\{db_name}") as con:
        log(f'insert_statement: {insert_statement}', 2)
        _ = con.execute(insert_statement)

        res = con.execute('SELECT * FROM session_log WHERE '
                          'id_session_log = last_insert_rowid();')
        id_session_log = res.fetchone()
        log(f'Inserted row {id_session_log}', 1)

        res = con.execute(get_last_start_id_query)
        results = res.fetchall()
        if len(results) == 0:
            raise LookupError("No matching 'START' event found")
        last_start_id = results[-1][0]
        log(f'SELECT instrument results: {last_start_id}', 2)

        res = con.execute(f"SELECT * FROM session_log WHERE "
                          f"id_session_log = {last_start_id}")
        log(f'Row to be updated: {res.fetchone()}', 1)

        update_statement = f"UPDATE session_log SET " \
                           f"record_status = 'TO_BE_BUILT' WHERE " \
                           f"id_session_log = {last_start_id}"

        _ = con.execute(update_statement)

        res = con.execute(f"SELECT * FROM session_log WHERE "
                          f"id_session_log = {last_start_id}")
        log(f'Row after updating: {res.fetchone()}', 1)


def cmdline_args():
    # Make parser object
    p = argparse.ArgumentParser(description=
                                """
                                This program will mount the nexuslims directory
                                on ***REMOVED***, connect to the nexuslims_db.sqlite
                                database, and insert an entry into the 
                                session log.
                                """,
                                formatter_class=
                                argparse.ArgumentDefaultsHelpFormatter)

    p.add_argument("event_type", type=str,
                   help="the type of event")
    p.add_argument("user", type=str, nargs='?',
                   help="NIST username associated with this session (current "
                        "windows logon name will be used if not provided)",
                   default=None)
    p.add_argument("-v", "--verbosity", type=int, choices=[0, 1, 2], default=0,
                   help="increase output verbosity")

    return p.parse_args()

if __name__ == '__main__':

    log('parsing arguments', 2)
    args = cmdline_args()
    verbosity = args.verbosity
    if not args.user:
        username = os.environ['username']
    else:
        username = args.user

    log(f'username is {username}', 1)

    log('running `mount_network_share()`', 2)
    mount_network_share()

    log('running `get_instr_pid()`', 2)
    instr_pid = get_instr_pid()

    if args.event_type == 'START':
        process_start(instr_pid, user=username)
    elif args.event_type == 'END':
        process_end(instr_pid, user=username)
    else:
        log('running `umount_network_share()`', 2)
        umount_network_share()
        error_string = f"event_type must be either 'START' or" + \
                       f" 'END'; '{args.event_type}' provided"
        raise ValueError(error_string)

    log('running `umount_network_share()`', 2)
    umount_network_share()

