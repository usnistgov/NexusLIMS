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

# Code has been update to work under Python 3.4 (32-bit) due to limitations of
# the Windows XP-based microscope PCs. Using this version of Python with
# pyinstaller 3.5 seems to work on the 642 Titan

import sqlite3
import re
import datetime
import os
import argparse
import subprocess

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
        print('{}'.format(datetime.datetime.now().isoformat()) +
              ':{}: '.format(level_dict[this_verbosity]) +
              '{}'.format(to_print))


def run_cmd(cmd):
    try:
        p = subprocess.check_output(cmd,
                                    shell=True,
                                    stderr=subprocess.STDOUT)
    except subprocess.CalledProcessError as e:
        p = e.output
        log('command {} returned with error (code {}): {}'.format(
            e.cmd.replace(password, '**************'),
            e.returncode,
            e.output), 0)
    return p


def get_computer_name():
    return os.environ['COMPUTERNAME']


def mount_network_share():
    # disconnect anything mounted at "N:/"
    log('unmounting existing N:', 2)
    p = run_cmd(r'net use N: /delete /y')

    # Connect to shared drive, windows does not allow multiple connections to
    # the same server, but you can trick it by using IP address instead of
    # DNS name...
    log('getting ip of cfse', 2)
    p = run_cmd(r'nslookup ***REMOVED***')
    log('output of nslookup: {}'.format(str(p)), 2)
    result = str(p).index('Name:')
    ips = re.findall(ip_regex, str(p)[result:])

    if len(ips) == 1:
        ip = ips[0]
    else:
        raise EnvironmentError('Could not find IP of network share')

    log('found ***REMOVED*** at {}'.format(ip), 2)
    log('mounting N:', 2)

    # mounting requires a security policy:
    # https://support.microsoft.com/en-us/help/968264/error-message-when-you-
    # try-to-map-to-a-network-drive-of-a-dfs-share-by
    mount_command = 'net use N: \\\\{}{} '.format(ip, db_path) + \
                    '/user:NIST\\***REMOVED*** {}'.format(password)
    if testing:
        mount_command = 'net use N: \\\\{}{} /user:NIST\\***REMOVED***'.format(ip,
                                                                     db_path)

    log('using "{}'.format(mount_command).replace(password,
                                                  '**************'), 2)
    p = run_cmd(mount_command)

    if 'error' in str(p):
        if '1312' in str(p):
            log('Visit https://support.microsoft.com/en-us/help/968264/error-'
                'message-when-you-try-to-map-to-a-network-drive-of-a-dfs'
                '-share-by\n'
                'to see how to allow mounting network drives as another user.'
                '\n(You\'ll need to change '
                'HKLM\\System\\CurrentControlSet\\Control\\Lsa'
                '\\DisableDomanCreds to 0 in the registry)',
                0)
        raise ConnectionError('Could not mount network share to access '
                              'database')


def umount_network_share():
    log('unmounting N:', 2)
    p = run_cmd(r'net use N: /del /y')
    if 'error' in str(p):
        log(str(p), 0)


def get_instr_pid():
    # Get the instrument pid from the computer name of this computer
    with sqlite3.connect("N:\\{}".format(db_name)) as con:
        res = con.execute('SELECT instrument_pid from instruments WHERE '
                          'computer_name is \'{}\''.format(get_computer_name()))
        instrument_pid = res.fetchone()[0]
        log('Found instrument ID: {} using'.format(instrument_pid) +
            ' {}'.format(get_computer_name()), 1)
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
                       "VALUES ('{}', 'START'".format(instrument_pid) + \
                       (", '{}');".format(user) if user else ");")

    log('insert_statement: {}'.format(insert_statement), 2)

    with sqlite3.connect("N:\\{}".format(db_name)) as con:
        _ = con.execute(insert_statement)
        res = con.execute('SELECT * FROM session_log WHERE '
                          'id_session_log = last_insert_rowid();')
        id_session_log = res.fetchone()
        log('Inserted row {}'.format(id_session_log), 1)


def process_end(instrument_pid, user=None):
    user_string = "AND user='{}'".format(user) if user else ''

    insert_statement = "INSERT INTO session_log (instrument, event_type, " \
                       "record_status" + \
                       (", user) " if user else ") ") + \
                       "VALUES ('{}', 'END', 'TO_BE_BUILT'".format(instrument_pid) + \
                       (", '{}');".format(user) if user else ");")

    # Get the most recent 'START' entry for this instrument
    get_last_start_id_query = "SELECT id_session_log FROM session_log " + \
                              "WHERE instrument = '{}' AND ".format(
                                  instrument_pid) + \
                              "event_type = 'START' {} AND ".format(
                                  user_string) + \
                              "record_status = 'WAITING_FOR_END'" + \
                              "ORDER BY timestamp DESC " + \
                              "LIMIT 1;"
    log('query: {}'.format(get_last_start_id_query), 2)
    with sqlite3.connect("N:\\{}".format(db_name)) as con:
        log('insert_statement: {}'.format(insert_statement), 2)
        _ = con.execute(insert_statement)

        res = con.execute('SELECT * FROM session_log WHERE '
                          'id_session_log = last_insert_rowid();')
        id_session_log = res.fetchone()
        log('Inserted row {}'.format(id_session_log), 1)

        res = con.execute(get_last_start_id_query)
        results = res.fetchall()
        if len(results) == 0:
            raise LookupError("No matching 'START' event found")
        last_start_id = results[-1][0]
        log('SELECT instrument results: {}'.format(last_start_id), 2)

        res = con.execute("SELECT * FROM session_log WHERE " +
                          "id_session_log = {}".format(last_start_id))
        log('Row to be updated: {}'.format(res.fetchone()), 1)

        update_statement = "UPDATE session_log SET " + \
                           "record_status = 'TO_BE_BUILT' WHERE " + \
                           "id_session_log = {}".format(last_start_id)

        _ = con.execute(update_statement)

        res = con.execute("SELECT * FROM session_log WHERE " + \
                          "id_session_log = {}".format(last_start_id))
        log('Row after updating: {}'.format(res.fetchone()), 1)


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

    log('username is {}'.format(username), 1)

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
        error_string = "event_type must be either 'START' or" + \
                       " 'END'; '{}' provided".format(args.event_type)
        raise ValueError(error_string)

    log('running `umount_network_share()`', 2)
    umount_network_share()
