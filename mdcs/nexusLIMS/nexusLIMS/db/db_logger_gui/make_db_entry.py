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

# Code must be able to work under Python 3.4 (32-bit) due to limitations of
# the Windows XP-based microscope PCs. Using this version of Python with
# pyinstaller 3.5 seems to work on the 642 Titan

import sqlite3
import re
import datetime
import os
import argparse
import subprocess
import time
import sys
import contextlib
from uuid import uuid4
import queue
import string
from ctypes import windll


def get_drives():
    """
    Get the drive letters (uppercase) in current use by Windows

    Adapted from https://stackoverflow.com/a/827398/1435788

    Returns
    -------
    drives : :obj:`list` of str
        A list of drive letters currently in use
    """
    drives = []
    bitmask = windll.kernel32.GetLogicalDrives()
    for letter in string.ascii_uppercase:
        if bitmask & 1:
            drives.append(letter)
        bitmask >>= 1

    return drives


def get_free_drives():
    """
    Get currently unused drive letters, leaving out A through G and M for
    safety (since those are often Windows drives and the M drive is used for
    ``mmfnexus``

    Returns
    -------
    not_in_use : :obj:`list` of str
        A list of "safe" drive letters not currently in use
    """
    in_use = get_drives()
    not_in_use = [lett for lett in string.ascii_uppercase if lett not in in_use]
    not_in_use = [lett for lett in not_in_use if lett not in 'ABCDEFGM']
    return not_in_use


def get_first_free_drive():
    """
    Get the first available drive letter that is not being used on this computer

    Returns
    -------
    first_free : str
        The first free drive letter that should be safe to use with colon
        appended
    """
    first_free = get_free_drives()[0]
    return first_free + ':'


class DBSessionLogger:
    ip_regex = r'(?:(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}' \
               r'(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)'

    def __init__(self,
                 verbosity=0,
                 db_name='nexuslims_db.sqlite',
                 user=None,
                 hostname='***REMOVED***'):
        """

        Parameters
        ----------
        verbosity : int
        testing
        db_name
        user : str
            The user to attach to this record
        """
        self.log_text = ""
        self.verbosity = verbosity
        self.testing = 'nexuslims_testing' in os.environ
        self.db_name = db_name
        self.drive_letter = get_first_free_drive()
        self.user = user
        self.hostname = hostname
        self.session_started = False
        self.session_start_time = None
        self.last_entry_type = None
        self.last_session_id = None
        self.last_session_row_number = None
        self.last_session_ts = None
        self.progress_num = 0

        if self.testing:
            # Values for testing from local machine (XP mode)
            self.verbosity = 10   # make testing very verbose
            self.log('(TEST) Found testing environment variable', 1)
            self.db_path = os.path.abspath('Z:\\')
            self.db_name = 'test_db.sqlite'
            # Make sure to mount cifs with nobrl option, or else sqlite will
            # fail with a "Database is Locked" error
            self.password = None
            self.full_path = os.path.join(self.db_path, self.db_name)
            self.cpu_name = "***REMOVED***"
            self.user = '***REMOVED***'
            self.log('(TEST) Using {} as path to db'.format(self.full_path), 2)
            self.log('(TEST) Using {} as cpu name'.format(self.cpu_name), 2)
            self.log('(TEST) if not testing, self.full_path would be '
                     '{}\\{}'.format(self.drive_letter, db_name), 1)
        else:
            # actual values to use in production
            self.db_path = '\\***REMOVED***\\nexuslims'
            try:
                self.password = os.environ['***REMOVED***']
            except KeyError as e:
                self.log('Could not find environment variable '
                         '"***REMOVED***"', -1)
                self.log_exception(e)
                self.password = e
            self.full_path = '{}\\{}'.format(self.drive_letter, db_name)
            self.cpu_name = os.environ['COMPUTERNAME']

        self.session_id = str(uuid4())
        self.instr_pid = None
        self.instr_schema_name = None

        self.log('Used drives are: {}'.format(get_drives()), 2)
        self.log('Unused drives are: {}'.format(get_free_drives()), 2)
        self.log('First available drive letter is {}'.format(
            self.drive_letter), 2)

    def log(self, to_print, this_verbosity):
        """
        Log a message to the console, only printing if the given verbosity is
        equal to or lower than the global threshold. Also save it in this
        instance's ``log_text`` attribute (regardless of verbosity)

        Parameters
        ----------
        to_print : str
            The message to log
        this_verbosity : int
            The verbosity level (higher is more verbose)
        """
        level_dict = {-1: 'ERROR', 0: ' WARN', 1: ' INFO', 2: 'DEBUG'}
        str_to_log = '{}'.format(datetime.datetime.now().isoformat()) + \
                     ':{}'.format(level_dict[this_verbosity]) + \
                     ': {}'.format(to_print)
        if this_verbosity <= self.verbosity:
            print(str_to_log)
        self.log_text += str_to_log + '\n'

    def log_exception(self, e):
        """
        Log an exception to the console and the ``log_text``

        Parameters
        ----------
        e : Exception
        """
        indent = " " * 34
        template = indent + "Exception of type {0} occurred. Arguments:\n" + \
                            indent + "{1!r}"
        message = template.format(type(e).__name__, e.args)
        print(message)
        self.log_text += message + '\n'

    def check_exit_queue(self, thread_queue, exit_queue):
        """
        Check to see if a queue (``q``) has anything in it. If so,
        immediately exit.

        Parameters
        ----------
        thread_queue : queue.Queue
        exit_queue : queue.Queue
        """
        if exit_queue is not None:
            try:
                res = exit_queue.get(0)
                if res:
                    self.log("Received termination signal from GUI thread", 0)
                    thread_queue.put(ChildProcessError("Terminated from GUI "
                                                       "thread"))
                    sys.exit("Saw termination queue entry")
            except queue.Empty:
                pass

    def run_cmd(self, cmd):
        """
        Run a command using the subprocess module and return the output. Note
        that because we want to run the eventual logger without a console
        visible, we do not have access to the standard stdin, stdout,
        and stderr, and these need to be redirected ``subprocess`` pipes,
        accordingly.

        Parameters
        ----------
        cmd : str
            The command to run (will be run in a new Windows `cmd` shell).
            ``stderr`` will be redirected for ``stdout`` and included in the
            returned output

        Returns
        -------
        output : str
            The output of ``cmd``
        """
        try:
            # Redirect stderr to stdout, and then stdout and stdin to
            # subprocess.PIP
            p = subprocess.Popen(cmd,
                                 shell=True,
                                 stderr=subprocess.STDOUT,
                                 stdout=subprocess.PIPE,
                                 stdin=subprocess.PIPE)
            p.stdin.close()
            p.wait()
            output = p.stdout.read().decode()
        except subprocess.CalledProcessError as e:
            p = e.output.decode()
            self.log('command {} returned with error (code {}): {}'.format(
                e.cmd.replace(self.password, '**************'),
                e.returncode,
                e.output), 0)
        return output

    def mount_network_share(self):
        """
        Mount the path containing the database to the first free drive letter
        found using Windows `cmd`. Due to some Windows limitations,
        this requires looking up the server's IP address
        and mounting using the IP rather than the actual domain name
        """
        # we should not have to disconnect anything because we're using free
        # letter:
        # self.log('unmounting existing N:', 2)
        # _ = self.run_cmd(r'net use N: /delete /y')

        # Connect to shared drive, windows does not allow multiple connections
        # to the same server, but you can trick it by using IP address
        # instead of DNS name... nslookup command sometimes fails,
        # but parsing the output of ping seems to work
        self.log('getting ip of {}'.format(self.hostname), 2)
        p = self.run_cmd(r'ping {} -n 1'.format(self.hostname))
        self.log('output of ping: {}'.format(p), 2)

        # The second line contains "pinging hostname [ip]..."
        ip = None
        have_ip = False

        ip_line = p.split('\r\n')[1]
        ips = re.findall(DBSessionLogger.ip_regex, ip_line)
        have_ip = True
        if len(ips) == 1:
            ip = ips[0]
        else:
            self.log("Ping did not return a parsable IP", -1)
            raise EnvironmentError('Could not find IP of network share in '
                                   'output of ping command')
        self.log('found ***REMOVED*** at {}'.format(ip), 2)

        if isinstance(self.password, Exception):
            raise EnvironmentError("***REMOVED*** environment variable is "
                                   "not defined. Please contact "
                                   "***REMOVED*** for assistance.")

        current_mounts = str(self.run_cmd('net use')).split('\r\n')
        self.log('Currently mounted: ', 2)
        do_mount = True
        self.log('Looking for '
                 r'{}\{}'.format(ip if have_ip else
                                 self.hostname,
                                 self.db_path).replace(r'\\', '\\'), 2)
        for m in current_mounts:
            self.log(m, 2)
            if r'{}\{}'.format(ip if have_ip else
                               self.hostname,
                               self.db_path).replace(r'\\', '\\') in m:
                old_drive_letter = self.drive_letter
                self.drive_letter = m.split()[0]
                if 'test_db' in os.environ:
                    self.log('(TEST) Using test db at '
                             '{}'.format(self.full_path), 0)
                else:
                    self.full_path = '{}\\{}'.format(self.drive_letter,
                                                     self.db_name)
                    self.log('{} is already mounted'.format(self.drive_letter),
                             0)
                do_mount = False

        if do_mount:
            mount_command = 'net use {} \\\\{}{} '.format(self.drive_letter,
                                                          ip if have_ip else
                                                          self.hostname,
                                                          self.db_path) + \
                            '/user:NIST\\***REMOVED*** {}'.format(self.password)
            self.log('mounting {}'.format(self.drive_letter), 2)

            # mounting requires a security policy:
            # https://support.microsoft.com/en-us/help/968264/error-message-when-
            # you-try-to-map-to-a-network-drive-of-a-dfs-share-by

            self.log('using "{}'.format(
                mount_command).replace(self.password, '**************'), 2)
            p = self.run_cmd(mount_command)

            if 'error' in str(p):
                if '1312' in str(p):
                    self.log('Visit https://bit.ly/38DvqVh\n'
                             'to see how to allow mounting network drives as '
                             'another user.\n'
                             '(You\'ll need to change HKLM\\System\\'
                             'CurrentControlSet\\Control\\Lsa\\'
                             'DisableDomanCreds '
                             'to 0 in the registry)', 0)
                raise ConnectionError('Could not mount network share to access '
                                      'database' + " (\"DisableDomanCreds\" "
                                                   "error)" if '1312' in str(p)
                                                   else "")
        else:
            self.log('Using existing mount point {}'.format(
                self.drive_letter), 1)

    def umount_network_share(self):
        """
        Unmount the network share using the Windows `cmd`
        """
        self.log('unmounting {}'.format(self.drive_letter), 2)
        p = self.run_cmd(r'net use {} /del /y'.format(self.drive_letter))
        if 'error' in str(p):
            self.log(str(p), 0)

    def get_instr_pid(self):
        """
        Using the name of this computer, get the matching instrument PID from
        the database

        Returns
        -------
        instrument_pid : str
            The PID for the instrument corresponding to this computer
        """
        # Get the instrument pid from the computer name of this computer
        with contextlib.closing(sqlite3.connect(self.full_path)) as con:
            self.log('Looking in database for computer name matching '
                     '{}'.format(self.cpu_name), 1)
            with con as cur:
                res = cur.execute('SELECT instrument_pid, schema_name '
                                  'from instruments '
                                  'WHERE '
                                  'computer_name is '
                                  '\'{}\''.format(self.cpu_name))
                one_result = res.fetchone()
                self.log('Database result is {}'.format(one_result), 2)
                if one_result is not None:
                    instrument_pid, instrument_schema_name = one_result
                else:
                    instrument_pid, instrument_schema_name = (None, None)

            self.log('instrument_pid: {} / '.format(instrument_pid) +
                     'instrument_schema_name: '
                     '{}'.format(instrument_schema_name), 2)
            if instrument_pid is None:
                raise sqlite3.DataError('Could not find an instrument matching '
                                        'this computer\'s name '
                                        '({}) '.format(self.cpu_name) +
                                        'in the database!\n\n'
                                        'This should not happen. Please '
                                        'contact ***REMOVED*** as soon as '
                                        'possible.')
            else:
                self.log('Found instrument ID: '
                         '{} using '.format(instrument_pid) +
                         '{}'.format(self.cpu_name), 1)
        return instrument_pid, instrument_schema_name

    def last_session_ended(self, thread_queue=None, exit_queue=None):
        """
        Check the database for this instrument to make sure that the last
        entry in the db was an "END" (properly ended). If it's not, return
        False so the GUI can query the user for additional input on how to
        proceed.

        Parameters
        ----------
        thread_queue : queue.Queue
            Main queue for communication with the GUI
        exit_queue : queue.Queue
            Queue containing any errors so the GUI knows to exit as needed

        Returns
        -------
        state_is_consistent : bool
            If the database is consistent (i.e. the last log for this
            instrument is an "END" log), return True. If not (it's a "START"
            log), return False
        """
        try:
            self.check_exit_queue(thread_queue, exit_queue)
            if self.instr_pid is None:
                raise AttributeError(
                    "Instrument PID must be set before checking "
                    "the database for any related sessions")
        except Exception as e:
            if thread_queue:
                thread_queue.put(e)
            self.log("Error encountered while checking that last record for "
                     "this instrument was an \"END\" log", -1)
            return False

        # Get last inserted line for this instrument that is not a record
        # generation (should be either a START or END)
        query_statement = 'SELECT event_type, session_identifier, ' \
                          'id_session_log, timestamp FROM session_log WHERE ' \
                          'instrument = "{}" '.format(self.instr_pid) + \
                          'AND NOT event_type = "RECORD_GENERATION" ' + \
                          'ORDER BY timestamp DESC LIMIT 1'

        self.log('last_session_ended query: {}'.format(query_statement), 2)

        self.check_exit_queue(thread_queue, exit_queue)
        with contextlib.closing(sqlite3.connect(self.full_path)) as con:
            with con as cur:
                try:
                    self.check_exit_queue(thread_queue, exit_queue)
                    res = cur.execute(query_statement)
                    row = res.fetchone()
                    if row is None:
                        # If there is no result, this must be the first time
                        # we're connecting to the database with this
                        # instrument, so pretend the last session was "END"
                        self.last_entry_type = "END"
                    else:
                        self.last_entry_type, self.last_session_id, \
                        self.last_session_row_number, self.last_session_ts = row
                    if self.last_entry_type == "END":
                        self.log('Verified database consistency for the '
                                 '{}'.format(self.instr_schema_name), 1)
                        if thread_queue:
                            thread_queue.put(('Verified database consistency '
                                              'for the {}'.format(
                                                  self.instr_schema_name),
                                              self.progress_num))
                            self.progress_num += 1
                        return True
                    elif self.last_entry_type == "START":
                        self.log('Database is inconsistent for the '
                                 '{} '.format(self.instr_schema_name) +
                                 '(last entry [id_session_log = '
                                 '{}]'.format(self.last_session_row_number) +
                                 ' was a "START")', 0)
                        if thread_queue:
                            thread_queue.put(('Database is inconsistent!',
                                              self.progress_num))
                            self.progress_num += 1
                        return False
                    else:
                        raise sqlite3.IntegrityError(
                            "Last entry for the "
                            "{} ".format(self.instr_schema_name) +
                            "was neither \"START\" or \"END\" (value was "
                            "\"{}\")".format(self.last_entry_type))
                except Exception as e:
                    if thread_queue:
                        thread_queue.put(e)
                    self.log("Error encountered while verifying "
                             "database consistency for the "
                             "{}".format(self.instr_schema_name), -1)
                    self.log_exception(e)
                    return False
        pass

    def process_start(self, thread_queue=None, exit_queue=None):
        """
        Insert a session `'START'` log for this computer's instrument

        Returns True if successful, False if not
        """
        insert_statement = "INSERT INTO session_log (instrument, " \
                           " event_type, session_identifier" + \
                           (", user) " if self.user else ") ") + \
                           "VALUES ('{}', 'START', ".format(self.instr_pid) + \
                           "'{}'".format(self.session_id) + \
                           (", '{}');".format(self.user) if self.user else ");")

        self.log('insert_statement: {}'.format(insert_statement), 2)

        self.check_exit_queue(thread_queue, exit_queue)
        # Get last entered row with this session_id (to make sure it's correct)
        with contextlib.closing(sqlite3.connect(self.full_path)) as con:
            with con as cur:
                try:
                    self.check_exit_queue(thread_queue, exit_queue)
                    _ = cur.execute(insert_statement)
                    self.session_started = True
                    if thread_queue:
                        thread_queue.put(('"START" session inserted into db',
                                          self.progress_num))
                        self.progress_num += 1
                except Exception as e:
                    if thread_queue:
                        thread_queue.put(e)
                    self.log("Error encountered while inserting \"START\" "
                             "entry into database", -1)
                    return False
            with con as cur:
                try:
                    self.check_exit_queue(thread_queue, exit_queue)
                    r = cur.execute("SELECT * FROM session_log WHERE "
                                    "session_identifier="
                                    "'{}' ".format(self.session_id) +
                                    "AND event_type = 'START'"
                                    "ORDER BY timestamp DESC " +
                                    "LIMIT 1;")
                except Exception as e:
                    if thread_queue:
                        thread_queue.put(e)
                    self.log("Error encountered while verifying that session"
                             "was started", -1)
                    return False
                id_session_log = r.fetchone()
            self.check_exit_queue(thread_queue, exit_queue)
            self.log('Verified insertion of row {}'.format(id_session_log), 1)
            self.session_start_time = datetime.datetime.strptime(
                id_session_log[3], "%Y-%m-%dT%H:%M:%S.%f")
            if thread_queue:
                thread_queue.put(('Verified "START" session inserted into db',
                                  self.progress_num))
                self.progress_num += 1

            return True

    def process_end(self, thread_queue=None, exit_queue=None):
        """
        Insert a session `'END'` log for this computer's instrument,
        and change the status of the corresponding `'START'` entry from
        `'WAITING_FOR_END'` to `'TO_BE_BUILT'`
        """
        user_string = "AND user='{}'".format(self.user) if self.user else ''

        insert_statement = "INSERT INTO session_log " \
                           "(instrument, event_type, " \
                           "record_status, session_identifier" + \
                           (", user) " if self.user else ") ") + \
                           "VALUES ('{}',".format(self.instr_pid) + \
                           "'END', 'TO_BE_BUILT', " + \
                           "'{}'".format(self.session_id) + \
                           (", '{}');".format(self.user) if self.user else ");")

        # Get the most 'START' entry for this instrument and session id
        get_last_start_id_query = "SELECT id_session_log FROM session_log " + \
                                  "WHERE instrument = " + \
                                  "'{}' ".format(self.instr_pid) + \
                                  "AND event_type = 'START' " + \
                                  "{} ".format(user_string) + \
                                  "AND session_identifier = " + \
                                  "'{}'".format(self.session_id) + \
                                  "AND record_status = 'WAITING_FOR_END';"
        self.log('query: {}'.format(get_last_start_id_query), 2)

        with sqlite3.connect(self.full_path) as con:
            self.log('Inserting END; insert_statement: {}'.format(
                insert_statement), 2)
            try:
                self.check_exit_queue(thread_queue, exit_queue)
                _ = con.execute(insert_statement)
                if thread_queue:
                    thread_queue.put(('"END" session log inserted into db',
                                      self.progress_num))
                    self.progress_num += 1
            except Exception as e:
                if thread_queue:
                    thread_queue.put(e)
                self.log("Error encountered while insert \"END\" log for "
                         "session", -1)
                return False

            try:
                self.check_exit_queue(thread_queue, exit_queue)
                res = con.execute("SELECT * FROM session_log WHERE "
                                  "session_identifier="
                                  "'{}' ".format(self.session_id) +
                                  "AND event_type = 'END'"
                                  "ORDER BY timestamp DESC " +
                                  "LIMIT 1;")
            except Exception as e:
                if thread_queue:
                    thread_queue.put(e)
                self.log("Error encountered while verifying that session"
                         "was ended", -1)
                return False
            id_session_log = res.fetchone()
            self.log('Inserted row {}'.format(id_session_log), 1)
            if thread_queue:
                thread_queue.put(('Verified "END" session inserted into db',
                                  self.progress_num))
                self.progress_num += 1

            try:
                self.check_exit_queue(thread_queue, exit_queue)
                res = con.execute(get_last_start_id_query)
                results = res.fetchall()
                if len(results) == 0:
                    raise LookupError("No matching 'START' event found")
                elif len(results) > 1:
                    raise LookupError("More than one 'START' event found with "
                                      "session_identifier = "
                                      "'{}'".format(self.session_id))
                last_start_id = results[-1][0]
                self.log('SELECT instrument results: {}'.format(last_start_id),
                         2)
                if thread_queue:
                    thread_queue.put(('Matching "START" session log found',
                                      self.progress_num))
                    self.progress_num += 1
            except Exception as e:
                if thread_queue:
                    thread_queue.put(e)
                self.log("Error encountered while getting matching \"START\" "
                         "log", -1)
                return False

            try:
                # Update previous START event record status
                self.check_exit_queue(thread_queue, exit_queue)
                res = con.execute("SELECT * FROM session_log WHERE " +
                                  "id_session_log = {}".format(last_start_id))
                self.log('Row to be updated: {}'.format(res.fetchone()), 1)
                if thread_queue:
                    thread_queue.put(('Matching "START" session log found',
                                      self.progress_num))
                    self.progress_num += 1
                update_statement = "UPDATE session_log SET " + \
                                   "record_status = 'TO_BE_BUILT' WHERE " + \
                                   "id_session_log = {}".format(last_start_id)
                self.check_exit_queue(thread_queue, exit_queue)
                _ = con.execute(update_statement)
                if thread_queue:
                    thread_queue.put(('Matching "START" session log\'s status '
                                      'updated',
                                      self.progress_num))
                    self.progress_num += 1

                self.check_exit_queue(thread_queue, exit_queue)
                res = con.execute("SELECT * FROM session_log WHERE " +
                                  "id_session_log = {}".format(last_start_id))
                if thread_queue:
                    thread_queue.put(('Verified updated row',
                                      self.progress_num))
                    self.progress_num += 1
            except Exception as e:
                if thread_queue:
                    thread_queue.put(e)
                self.log("Error encountered while updating matching \"START\" "
                         "log's status", -1)
                return False

            self.log('Row after updating: {}'.format(res.fetchone()), 1)
            self.log('Finished ending session {}'.format(self.session_id), 1)

            return True

    def db_logger_setup(self, thread_queue=None, exit_queue=None):
        self.log('username is {}'.format(self.user), 1)
        self.log('computer name is {}'.format(self.cpu_name), 1)
        try:
            self.check_exit_queue(thread_queue, exit_queue)
            if sys.platform == 'win32' and not self.testing:
                self.log('running `mount_network_share()`', 2)
                self.mount_network_share()
            elif sys.platform == 'linux' or self.testing:
                self.log('on linux/testing; skipping '
                         '`mount_network_share()`', 2)
                self.log('sleeping for 1 second to simulate network lag', 2)
                time.sleep(1)
            if not os.path.isfile(self.full_path):
                raise FileNotFoundError('Could not find NexusLIMS database at '
                                        '{}'.format(self.full_path))
            else:
                self.log('Path to database is {}'.format(self.full_path), 1)
        except Exception as e:
            thread_queue.put(e)
            self.log("Could not mount the network share holding the "
                     "database. Details:", -1)
            self.log_exception(e)
            return False
        if thread_queue:
            self.progress_num = 1
            thread_queue.put(('Mounted network share', self.progress_num))
            self.progress_num += 1
        self.log('running `get_instr_pid()`', 2)
        try:
            self.check_exit_queue(thread_queue, exit_queue)
            self.instr_pid, self.instr_schema_name = self.get_instr_pid()
        except Exception as e:
            thread_queue.put(e)
            self.log("Could not fetch instrument PID and name from database. "
                     "Details:", -1)
            self.log_exception(e)
            return False
        self.log('Found PID: {} and name: {}'.format(self.instr_pid,
                                                     self.instr_schema_name), 2)
        if thread_queue:
            thread_queue.put(('Instrument PID found', self.progress_num))
            self.progress_num += 1

        return True

    def db_logger_teardown(self, thread_queue=None, exit_queue=None):
        try:
            if thread_queue:
                thread_queue.put(('Unmounting the database network share',
                                  self.progress_num))
                self.progress_num += 1
            self.check_exit_queue(thread_queue, exit_queue)
            if sys.platform == 'win32' and not self.testing:
                self.log('running `umount_network_share()`', 2)
                self.umount_network_share()
            elif sys.platform == 'linux' or self.testing:
                self.log('on linux/testing; skipping '
                         '`umount_network_share()`', 2)
                self.log('sleeping for 1 second to simulate network lag', 2)
                time.sleep(1)
        except Exception as e:
            thread_queue.put(e)
            self.log("Could not unmount the network share holding the "
                     "database. Details:", -1)
            self.log_exception(e)
            return False
        if thread_queue:
            thread_queue.put(('Unmounted network share', self.progress_num))
            self.progress_num += 1

        self.log('Finished unmounting network share', 2)
        return True


def cmdline_args():
    # Make parser object
    p = argparse.ArgumentParser(
        description="""This program will mount the nexuslims directory
                       on ***REMOVED***, connect to the nexuslims_db.sqlite
                       database, and insert an entry into the 
                       session log.""",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter)

    p.add_argument("event_type", type=str,
                   help="the type of event")
    p.add_argument("user", type=str, nargs='?',
                   help="NIST username associated with this session (current "
                        "windows logon name will be used if not provided)",
                   default=None)
    p.add_argument("-v", "--verbosity", type=int, choices=[0, 1, 2], default=0,
                   help="increase output verbosity")

    return p.parse_args()


def gui_start_callback(verbosity=2, testing=False):
    """
    Process the start of a session when the GUI is opened

    Returns
    -------
    db_logger : DBSessionLogger
        The session logger instance for this session (contains all the
        information about instrument, computer, session_id, etc.)
    """
    db_logger = DBSessionLogger(verbosity=verbosity,
                                testing=testing,
                                user=None if testing else
                                os.environ['username'])
    db_logger.db_logger_setup()
    db_logger.process_start()
    db_logger.db_logger_teardown()

    return db_logger


def gui_end_callback(db_logger):
    """
    Process the end of a session when the button is clicked or the GUI window
    is closed.

    Parameters
    ----------
    db_logger : DBSessionLogger
        The session logger instance for this session (contains all the
        information about instrument, computer, session_id, etc.)
    """
    db_logger.db_logger_setup()
    db_logger.process_end()
    db_logger.db_logger_teardown()
