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
from configparser import ConfigParser as _ConfigParser
from typing import Tuple, List, Callable, Optional

import certifi as _certifi
import tempfile as _tempfile
import os as _os
import subprocess as _sp
from datetime import datetime
from datetime import timedelta as _timedelta
from os.path import getmtime as _getmtime
import logging as _logging
import sys as _sys

from requests_ntlm import HttpNtlmAuth as _HttpNtlmAuth
from requests import Session as _Session
from requests.adapters import HTTPAdapter as _HTTPAdapter
from requests.adapters import Retry as _Retry

_logger = _logging.getLogger(__name__)
_logger.setLevel(_logging.INFO)

# hours to add to datetime objects (hack for poole testing -- should be -2 if
# running tests from Mountain Time on files in Eastern Time)
tz_offset = _timedelta(hours=0)


def setup_loggers(log_level):
    """
    Set logging level of all NexusLIMS loggers

    Parameters
    ----------
    log_level : int
        The level of logging, such as ``logging.DEBUG``
    """
    _logging.basicConfig(format='%(asctime)s %(name)s %(levelname)s: '
                                '%(message)s',
                         level=log_level)
    loggers = [_logging.getLogger(name) for name in
               _logging.root.manager.loggerDict if 'nexusLIMS' in name]
    for logger in loggers:
        logger.setLevel(log_level)


def nexus_req(url: str,
              fn: str,
              basic_auth: bool = False,
              token_auth: Optional[str] = None,
              **kwargs: Optional[dict]):
    """
    A helper method that wraps a function from :py:mod:`requests`, but adds a
    local certificate authority chain to validate any custom certificates and 
    allow authenticatation using NTLM. Will automatically retry on 500 errors
    using a strategy suggested here: https://stackoverflow.com/a/35636367

    Parameters
    ----------
    url
        The URL to fetch
    fn
        The function from the ``requests`` library to use (e.g.
        ``'GET'``, ``'POST'``, ``'PATCH'``, etc.)
    basic_auth
        If True, use only username and password for authentication rather than
        NTLM
    token_auth
        If a value is provided, it will be used as a token for authentication
        (only one of ``token_auth`` or ``basic_auth`` should be provided. The
        method will error if both are provided
    **kwargs :
        Other keyword arguments are passed along to the ``fn``

    Returns
    -------
    r : :py:class:`requests.Response`
        A requests response object

    Raises
    ------
    ValueError
        If multiple methods of authentication are provided to the function
    """
    if basic_auth and token_auth:
        raise ValueError('Both `basic_auth` and `token_auth` were provided. '
                         'Only one can be used at a time')

    from .harvesters import CA_BUNDLE_CONTENT

    # if token_auth is desired, add it to any existing headers passed along
    # with the request
    if token_auth:
        if 'headers' in kwargs:
            kwargs['headers']['Authorization'] = f"Token {token_auth}"
        else:
            kwargs['headers'] = {'Authorization': f"Token {token_auth}"}

    # set up a session to retry requests as needed
    s = _Session()
    retries = _Retry(total=5, 
                     backoff_factor=1, 
                     status_forcelist=[502, 503, 504])
    s.mount('https://', _HTTPAdapter(max_retries=retries))                 
    s.mount('http://', _HTTPAdapter(max_retries=retries))                 

    verify_arg = True
    with _tempfile.NamedTemporaryFile() as tmp:
        if CA_BUNDLE_CONTENT:
            with open(_certifi.where(), 'rb') as sys_cert:
                lines = sys_cert.readlines()
            tmp.writelines(lines)
            tmp.writelines(CA_BUNDLE_CONTENT)
            tmp.seek(0)
            verify_arg = tmp.name

        if token_auth:
            r = s.request(fn, url, 
                          verify=verify_arg, **kwargs)
        else:
            r = s.request(fn, url, auth=get_auth(basic=basic_auth), 
                          verify=verify_arg, **kwargs)

    return r


def is_subpath(path, of_paths):
    """
    Helper function to determine if a given path is a "subpath" of a set of
    paths. Useful to help determine which instrument a given file comes from,
    given the instruments ``filestore_path`` and the path of the file to test.

    Parameters
    ----------
    path : str
        The path of the file (or directory) to test. This will usually be the
        absolute path to a file on the local filesystem (to be compared using
        the host-specific ``mmf_nexus_root_path``.
    of_paths : str or list
        The "higher-level" path to test against (or list thereof). In typical
        use, this will be a path joined of an instruments ``filestore_path``
        with the root-level ``mmf_nexus_root_path``

    Returns
    -------
    result : bool
        Whether or not path is a subpath of one of the directories in of_paths

    Examples
    --------
    >>> is_subpath('/path/to/file.dm3',
    ...            os.path.join(os.environ['mmfnexus_path'],
    ...                         titan.filestore_path))
    True
    """
    if isinstance(of_paths, str):
        of_paths = [of_paths]
    abs_of_paths = [_os.path.abspath(of_path) for of_path in of_paths]

    result = any(_os.path.abspath(path).startswith(subpath)
                 for subpath in abs_of_paths)

    return result


def get_nested_dict_value(nested_dict, value, prepath=()):
    """
    Use a recursive method to find a value in a dictionary of dictionaries
    (such as the metadata dictionaries we receive from the file parsers).
    Cribbed from: https://stackoverflow.com/a/22171182/1435788

    Parameters
    ----------
    nested_dict : dict
        Dictionary to search
    value : object
        Value to search for
    prepath : tuple
        "path" to prepend to the search to limit the search to only part of
        the dictionary

    Returns
    -------
    path : tuple or None
        The "path" through the dictionary (expressed as a tuple of keys) where
        value was found. If None, the value was not found in the dictionary.
    """
    for k, v in nested_dict.items():
        path = prepath + (k,)
        if v == value:                                   # found value
            return path
        elif hasattr(v, 'items'):                        # v is a dict
            p = get_nested_dict_value(v, value, path)    # recursive call
            if p is not None:
                return p


def get_nested_dict_key(nested_dict, key_to_find, prepath=()):
    """
    Use a recursive method to find a key in a dictionary of dictionaries
    (such as the metadata dictionaries we receive from the file parsers).
    Cribbed from: https://stackoverflow.com/a/22171182/1435788

    Parameters
    ----------
    nested_dict : dict
        Dictionary to search
    key_to_find : object
        Value to search for
    prepath : tuple
        "path" to prepend to the search to limit the search to only part of
        the dictionary

    Returns
    -------
    path : tuple or None
        The "path" through the dictionary (expressed as a tuple of keys) where
        value was found. If None, the value was not found in the dictionary.
    """
    for k, v in nested_dict.items():
        path = prepath + (k,)
        if k == key_to_find:                                 # found key
            return path
        elif hasattr(v, 'items'):                            # v is a dict
            p = get_nested_dict_key(v, key_to_find, path)    # recursive call
            if p is not None:
                return p


def get_nested_dict_value_by_path(nest_dict, path):
    """
    Get the value from within a nested dictionary structure by traversing into
    the dictionary as deep as that path found and returning that value

    Parameters
    ----------
    nest_dict : dict
        A dictionary of dictionaries that is to be queried
    path : tuple
        A tuple (or other iterable type) that specifies the subsequent keys
        needed to get to a a value within `nest_dict`

    Returns
    -------
    value : object or str
        The value at the path within the nested dictionary; if there's no
        value there, return the string `"not found"`
    """
    sub_dict = nest_dict
    for key in path:
        if key in sub_dict:
            sub_dict = sub_dict[key]
        else:
            sub_dict = 'not found'

    return sub_dict


def set_nested_dict_value(nest_dict, path, value):
    """
    Set a value within a nested dictionary structure by traversing into
    the dictionary as deep as that path found and changing it to `value`.
    Cribbed from https://stackoverflow.com/a/13688108/1435788

    Parameters
    ----------
    nest_dict : dict
        A dictionary of dictionaries that is to be queried
    path : tuple
        A tuple (or other iterable type) that specifies the subsequent keys
        needed to get to a a value within `nest_dict`
    value : object
        The value which will be given to the path in the nested dictionary

    Returns
    -------
    value : object
        The value at the path within the nested dictionary
    """
    for key in path[:-1]:
        nest_dict = nest_dict.setdefault(key, {})
    nest_dict[path[-1]] = value


def try_getting_dict_value(d, key):
    """
    This method will try to get a value from a dictionary (potentially
    nested) and fail silently if the value is not found, returning None.

    Parameters
    ----------
    d : dict
        The dictionary from which to get a value
    key : str or tuple
        The key to query, or if an iterable container type (tuple, list,
        etc.) is given, the path into a nested dictionary to follow

    Returns
    -------
    val : object or str
        The value of the dictionary specified by `key`. If the dictionary
        does not have a key, returns the string `"not found"` without raising an
        error
    """
    try:
        if isinstance(key, str):
            return d[key]
        elif hasattr(key, '__iter__'):
            return get_nested_dict_value_by_path(d, key)
    except (KeyError, TypeError) as e:
        return 'not found'


def find_dirs_by_mtime(path: str, 
                       dt_from: datetime,
                       dt_to: datetime,
                       followlinks: bool = True) -> List[str]:
    """
    Given two timestamps, find the directories under a path that were
    last modified between the two

    .. deprecated:: 0.0.9
          `find_dirs_by_mtime` is not recommended for use to find files for
          record inclusion, because subsequent modifications to a directory
          (e.g. the user wrote a text file or did some analysis afterwards)
          means no files will be returned from that directory (because it is
          not searched)

    Parameters
    ----------
    path
        The root path from which to start the search
    dt_from
        The "starting" point of the search timeframe
    dt_to
        The "ending" point of the search timeframe
    followlinks
        Argument passed on to py:func:`os.walk` to control whether
        symbolic links are followed

    Returns
    -------
    dirs : list
        A list of the directories that have modification times within the time range provided
    """
    dirs = []

    # adjust the datetime objects with the tz_offset (usually should be 0) if
    # they are naive
    if dt_from.tzinfo is None:
        dt_from += tz_offset
    if dt_to.tzinfo is None:
        dt_to += tz_offset

    # use os.walk and only inspect the directories for mtime (much fewer
    # comparisons than looking at every file):
    _logger.info(f'Finding directories modified between {dt_from.isoformat()} '
                 f'and {dt_to.isoformat()}')
    for dirpath, _, _ in _os.walk(path, followlinks=followlinks):
        if dt_from.timestamp() < _getmtime(dirpath) < dt_to.timestamp():
            dirs.append(dirpath)
    return dirs


def find_files_by_mtime(path, dt_from, dt_to):
    """
    Given two timestamps, find files under a path that were
    last modified between the two.

    Parameters
    ----------
    path : str
        The root path from which to start the search
    dt_from : datetime.datetime
        The "starting" point of the search timeframe
    dt_to : datetime.datetime
        The "ending" point of the search timeframe

    Returns
    -------
    files : list
        A list of the files that have modification times within the
        time range provided (sorted by modification time)
    """
    # find only the directories that have been modified between these two
    # timestamps (should be much faster than inspecting all files)
    # Note: this doesn't work reliably, so just look in entire path...
    # dirs = find_dirs_by_mtime(path, dt_from, dt_to)

    dirs = [path]

    # adjust the datetime objects with the tz_offset (usually should be 0) if
    # they are naive
    if dt_from.tzinfo is None:
        dt_from += tz_offset
    if dt_to.tzinfo is None:
        dt_to += tz_offset

    files = set()    # use a set here (faster and we won't have duplicates)
    # for each of those directories, walk the file tree and inspect the
    # actual files:
    for d in dirs:
        for dirpath, _, filenames in _os.walk(d, followlinks=True):
            for f in filenames:
                fname = _os.path.abspath(_os.path.join(dirpath, f))
                if dt_from.timestamp() < _getmtime(fname) < dt_to.timestamp():
                    files.add(fname)

    # convert the set to a list and sort my mtime
    files = list(files)
    files.sort(key=_getmtime)

    return files


def gnu_find_files_by_mtime(
        path: str,
        dt_from: datetime,
        dt_to: datetime,
        extensions: Optional[List[str]] = None,
        followlinks: bool = True
) -> List[str]:
    """
    Given two timestamps, find files under a path that were
    last modified between the two. Uses the system-provided GNU ``find``
    command. In basic testing, this method was found to be approximately 3 times
    faster than using :py:meth:`find_files_by_mtime` (which is implemented in
    pure Python).

    Parameters
    ----------
    path
        The root path from which to start the search, relative to
        the :ref:`mmfnexus_path <mmfnexus-path>` environment setting.
    dt_from
        The "starting" point of the search timeframe
    dt_to
        The "ending" point of the search timeframe
    extensions
        A list of strings representing the extensions to find
    followlinks
        Whether to follow symlinks using the ``find`` command via 
        the ``-H`` command line flag. This is useful when the 
        :ref:`mmfnexus_path <mmfnexus-path>` is actually a directory
        of symlinks. If this is the case and ``followlinks`` is 
        ``False``, no files will ever be found because the ``find``
        command will not "dereference" the symbolic links it finds.
        See comments in the code for more comments on implementation
        of this feature.

    Returns
    -------
    files
        A list of the files that have modification times within the
        time range provided (sorted by modification time)

    Raises
    ------
    NotImplementedError
        If the system running this code is not Linux-based
    RuntimeError
        If the find command cannot be found, or running it results in output
        to `stderr`
    """
    _logger.info(f'Using GNU `find` to search for files')
    # Verify we're running on Linux
    if not _sys.platform.startswith('linux'):
        raise NotImplementedError('gnu_find_files_by_mtime only implemented '
                                  'for Linux')

    if path[-1] == '/':
        _logger.warning(f'Removing trailing slash from path: "{path}"')
        path = path[:-1]

    def _which(fname):
        def _is_exec(f):
            return _os.path.isfile(f) and _os.access(f, _os.X_OK)

        # Check to see if find command is on PATH:
        exec_file = fname

        for p in _os.environ["PATH"].split(_os.pathsep):
            exe_file = _os.path.join(p, exec_file)
            if _is_exec(exe_file):
                return exe_file

        return False

    if not _which('find'):
        raise RuntimeError('find command was not found on the system PATH')

    # adjust the datetime objects with the tz_offset (usually should be 0) if
    # they are naive
    if dt_from.tzinfo is None:
        dt_from += tz_offset
    if dt_to.tzinfo is None:
        dt_to += tz_offset

    # join the given path with the root storage folder
    find_path = _os.path.join(_os.environ["mmfnexus_path"], path)

    
    # if "followlinks" is provided, the "find" command is split into two parts; 
    # This code is to support when `mmfnexus_path` is a directory of symbolic links
    # to instrument storage locations, rather than actual directories

    # The simplest option would be to provide the "-L" flag to "find", which instructs
    # the program to "dereference" all symbolic links it finds. In testing, this
    # was found to slow the file finding operation by at least an order of magnitude,
    # inflating run-times from a few minutes to over an hour; instead, we do
    # a two part operation:

    # First, we search from the root path for any symbolic links that point
    # to directories; If the root path is a (relatively) small directory consisting
    # of mostly symbolic links, this operation should be very fast.
 
    # Based off the results of the first search, we then use "find" with the
    # "-H" flag to dereference only the paths provided as a command line option
    # for "find". We assume in this implementation there will not be symlinks 
    # in the instrument data folders themselves. This method further assumes that
    # the folder specified by "path" is either a symlink itself, or a directory 
    # containing one or more symlinks. It _should_ still work if this is not the
    # case, but may be slower, since it will run two "find" commands over the whole
    # directory tree in that case.
    if followlinks:
        find_path = _os.path.join(_os.environ["mmfnexus_path"], path)
        cmd = f'find {find_path} -type l -xtype d -print0'
        _logger.info(f'Running followlinks find via subprocess: "{cmd}"')
        out = _sp.Popen(cmd, shell=True,
                    stdin=_sp.PIPE, stdout=_sp.PIPE, stderr=_sp.PIPE)
        (stdout, stderr) = out.communicate()
        paths = stdout.split(b'\x00')
        paths = [f.decode() for f in paths if len(f) > 0]
        _logger.info(f'Found the following symlinks: "{paths}"')
        if paths:
            find_path = ' '.join([f'"{p}"' for p in paths])
            _logger.info(f"find_path is: '{find_path}'")

    # Actually run find command (ignoring mib files if specified by
    # environment variable):
    filetype_regex = '|'.join(extensions)

    cmd = f'find ' + \
          ('-H ' if followlinks else '') + \
          f'{find_path} ' + \
          f'-type f ' + \
          f'-regextype posix-egrep ' + \
          f'-regex ".*\\.({filetype_regex})$" ' + \
          f'-newermt "{dt_from.isoformat()}" ' + \
          f'\\! -newermt "{dt_to.isoformat()}" ' + \
          (f'\\! -name "*.mib" ' if 'ignore_mib' in _os.environ else '') + \
          f'-print0'

    _logger.info(f'Running via subprocess: "{cmd}"')
    out = _sp.Popen(cmd, shell=True,
                    stdin=_sp.PIPE, stdout=_sp.PIPE, stderr=_sp.PIPE)

    (stdout, stderr) = out.communicate()

    if len(stderr) > 0:
        # find command returned an error
        raise RuntimeError(stderr)

    files = stdout.split(b'\x00')
    files = [f.decode() for f in files if len(f) > 0]

    # convert to set and back to remove duplicates and sort my mtime
    files = list(set(files))
    files.sort(key=_getmtime)
    _logger.info(f"Found {len(files)} files")
    return files


def _sort_dict(item):
    return {k: _sort_dict(v) if isinstance(v, dict) else v
            for k, v in sorted(item.items(), key=lambda i: i[0].lower())}


def _remove_dtb_element(tree, path):
    """
    Helper method that uses exec to delete a specific leaf of a
    DictionaryTreeBrowser using a string

    Parameters
    ----------
    tree : :py:class:`~hyperspy.misc.utils.DictionaryTreeBrowser`
        the ``DictionaryTreeBrowser`` object to remove the object from
    path : str
        period-delimited path to a DTB element

    Returns
    -------
    tree : :py:class:`~hyperspy.misc.utils.DictionaryTreeBrowser`
    """
    to_del = 'tree.{}'.format(path)
    try:

        exec('del {}'.format(to_del))
    except AttributeError as _:
        # Log the failure and continue
        _logger.debug('_remove_dtb_element: Could not find {}'.format(to_del))

    return tree


def _zero_bytes(fname, bytes_from, bytes_to):
    """
    A helper method to set certain byte locations within a file to zero,
    which can help for creating highly-compressible test files

    Parameters
    ----------
    fname : str
    bytes_from : int or :obj:`list` of str
        The position of the file (in decimal) at which to start zeroing
    bytes_to : int or :obj:`list` of str
        The position of the file (in decimal) at which to stop zeroing. If
        list, must be the same length as list given in ``bytes_from``

    Returns
    -------
    new_fname : str
        The modified file that has it's bytes zeroed
    """
    from shutil import copyfile
    filename, ext = _os.path.splitext(fname)
    if fname.endswith('.ser'):
        index = int(filename.split('_')[-1])
        basename = '_'.join(filename.split('_')[:-1])
        new_fname = f'{basename}_dataZeroed_{index}{ext}'
    else:
        new_fname = f'{filename}_dataZeroed{ext}'
    copyfile(fname, new_fname)

    if isinstance(bytes_from, int):
        bytes_from = [bytes_from]
        bytes_to = [bytes_to]

    with open(new_fname, 'r+b') as f:
        for bf, bt in zip(bytes_from, bytes_to):
            f.seek(bf)
            f.write(b'\0' * (bt - bf))

    return new_fname


def _get_timespan_overlap(range_1: Tuple[datetime, datetime],
                          range_2: Tuple[datetime, datetime]) -> _timedelta:
    """
    Find the amount of overlap between two time spans. Adapted from
    https://stackoverflow.com/a/9044111

    Parameters
    ----------
    range_1
        Tuple of length 2 of datetime objects: first is the start of the time
        range and the second is the end of the time range
    range_2
        Tuple of length 2 of datetime objects: first is the start of the time
        range and the second is the end of the time range

    Returns
    -------
    overlap
        The amount of overlap between the time ranges
    """
    latest_start = max(range_1[0], range_2[0])
    earliest_end = min(range_1[1], range_2[1])
    delta = earliest_end - latest_start
    overlap = max(_timedelta(0), delta)

    return overlap


def get_auth(filename="credentials.ini", basic=False):
    """
    Set up NTLM authentication for the Microscopy Nexus using an account
    as specified from a file that lives in the package root named
    .credentials (or some other value provided as a parameter).
    Alternatively, the stored credentials can be overridden by supplying two
    environment variables: ``nexusLIMS_user`` and ``nexusLIMS_pass``. These
    variables will be queried first, and if not found, the method will
    attempt to use the credential file.

    Parameters
    ----------
    filename : str
        Name relative to this file (or absolute path) of file from which to
        read the parameters
    basic : bool
        If True, return only username and password rather than NTLM
        authentication

    Returns
    -------
    auth : ``requests_ntlm.HttpNtlmAuth`` or tuple
        NTLM authentication handler for ``requests``

    Notes
    -----
        The credentials file is expected to have a section named
        ``[nexus_credentials]`` and two values: ``username`` and
        ``password``. See the ``credentials.ini.example`` file included in
        the repository as an example.
    """
    # DONE: this should be moved out of sharepoint calendar an into general
    #  utils since it's used for CDCS as well
    try:
        username = _os.environ['nexusLIMS_user']
        passwd = _os.environ['nexusLIMS_pass']
        _logger.info("Authenticating using environment variables")
    except KeyError:
        # if absolute path was provided, use that, otherwise find filename in
        # this directory
        if _os.path.isabs(filename):
            pass
        else:
            filename = _os.path.join(_os.path.dirname(__file__), filename)

        # Raise error if the configuration file is not found
        if not _os.path.isfile(filename):
            raise AuthenticationError("No credentials were specified with "
                                      "environment variables, and credential "
                                      "file {} was not found".format(filename))

        config = _ConfigParser()
        config.read(filename)

        username = config.get("nexus_credentials", "username")
        passwd = config.get("nexus_credentials", "password")

    if basic:
        # return just username and password (for BasicAuthentication)
        return username, passwd

    domain = 'nist'
    path = domain + '\\' + username

    auth = _HttpNtlmAuth(path, passwd)

    return auth


def has_delay_passed(date: datetime) -> bool:
    """
    Helper method to check if the current time is greater than the configured
    (or default) record building delay configured in the
    ``nexusLIMS_file_delay_days`` environment variable. If the date given is
    timezone-aware, the current time in that timezone will be compared.

    Parameters
    ----------
    date
        The datetime to check; can be either timezone aware or naive

    Returns
    -------
    bool
        Whether the current time is greater than the given date plus the
        configurable delay.
    """
    try:
        # get record builder delay from environment settings
        delay = float(_os.getenv('nexusLIMS_file_delay_days', 2))
    except ValueError:
        # if it cannot be coerced to a number, warn and set to the
        # default of 2 days
        _logger.warning(
            f'The environment variable value of '
            f'nexusLIMS_file_delay_days '
            f'({_os.getenv("nexusLIMS_file_delay_days")}) could '
            f'not be understood as a number, so using the default '
            f'of 2 days.')
        delay = 2

    delay = _timedelta(days=delay)

    if date.tzinfo is None:
        # compare naive datetime
        now = datetime.now()
    else:
        # compare timezone-aware datetime using current time in that timezone
        now = datetime.now(date.tzinfo)

    delta = now - date

    return delta > delay


class AuthenticationError(Exception):
    """Class for showing an exception having to do with authentication"""
    def __init__(self, message):
        self.message = message
