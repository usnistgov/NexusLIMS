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
"""Utility functions used in potentially multiple places by NexusLIMS."""
import json
import logging
import os
import subprocess
import tempfile
import time
import warnings
from configparser import ConfigParser
from datetime import datetime, timedelta, timezone
from os.path import getmtime
from pathlib import Path
from shutil import copyfile
from typing import Any, Dict, List, Optional, Tuple, Union

import certifi
from requests import Session
from requests.adapters import HTTPAdapter, Retry
from requests_ntlm import HttpNtlmAuth

from .harvesters import CA_BUNDLE_CONTENT

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# hours to add to datetime objects (hack for poole testing -- should be -2 if
# running tests from Mountain Time on files in Eastern Time)
tz_offset = timedelta(hours=0)


def setup_loggers(log_level):
    """
    Set logging level of all NexusLIMS loggers.

    Parameters
    ----------
    log_level : int
        The level of logging, such as ``logging.DEBUG``
    """
    logging.basicConfig(
        format="%(asctime)s %(name)s %(levelname)s: %(message)s",
        level=log_level,
    )
    loggers = [
        logging.getLogger(name)
        for name in logging.root.manager.loggerDict  # pylint: disable=no-member
        if "nexusLIMS" in name
    ]
    for _logger in loggers:
        _logger.setLevel(log_level)


def nexus_req(
    url: str,
    function: str,
    *,
    basic_auth: bool = False,
    token_auth: Optional[str] = None,
    **kwargs: Optional[dict],
):
    """
    Make a request from NexusLIMS.

    A helper method that wraps a function from :py:mod:`requests`, but adds a
    local certificate authority chain to validate any custom certificates and
    allow authenticatation using NTLM. Will automatically retry on 500 errors
    using a strategy suggested here: https://stackoverflow.com/a/35636367.

    Parameters
    ----------
    url
        The URL to fetch
    function
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
        msg = (
            "Both `basic_auth` and `token_auth` were provided. "
            "Only one can be used at a time"
        )
        raise ValueError(msg)

    # if token_auth is desired, add it to any existing headers passed along
    # with the request
    if token_auth:
        if "headers" in kwargs:
            kwargs["headers"]["Authorization"] = f"Token {token_auth}"
        else:
            kwargs["headers"] = {"Authorization": f"Token {token_auth}"}

    # set up a session to retry requests as needed
    s = Session()
    retries = Retry(total=5, backoff_factor=1, status_forcelist=[502, 503, 504])
    s.mount("https://", HTTPAdapter(max_retries=retries))
    s.mount("http://", HTTPAdapter(max_retries=retries))

    verify_arg = True
    with tempfile.NamedTemporaryFile() as tmp:
        if CA_BUNDLE_CONTENT:
            with Path(certifi.where()).open(mode="rb") as sys_cert:
                lines = sys_cert.readlines()
            tmp.writelines(lines)
            tmp.writelines(CA_BUNDLE_CONTENT)
            tmp.seek(0)
            verify_arg = tmp.name

        if token_auth:
            response = s.request(function, url, verify=verify_arg, **kwargs)
        else:
            response = s.request(
                function,
                url,
                auth=get_auth(basic=basic_auth),
                verify=verify_arg,
                **kwargs,
            )

    return response


def is_subpath(path: Path, of_paths: Union[Path, List[Path]]):
    """
    Return if this path is a subpath of other paths.

    Helper function to determine if a given path is a "subpath" of a set of
    paths. Useful to help determine which instrument a given file comes from,
    given the instruments ``filestore_path`` and the path of the file to test.

    Parameters
    ----------
    path
        The path of the file (or directory) to test. This will usually be the
        absolute path to a file on the local filesystem (to be compared using
        the host-specific ``mmf_nexus_root_path``.
    of_paths
        The "higher-level" path to test against (or list thereof). In typical
        use, this will be a path joined of an instruments ``filestore_path``
        with the root-level ``mmf_nexus_root_path``

    Returns
    -------
    result : bool
        Whether or not path is a subpath of one of the directories in of_paths

    Examples
    --------
    >>> is_subpath(Path('/path/to/file.dm3'),
    ...            Path(os.environ['mmfnexus_path'] /
    ...                 titan.filestore_path))
    True
    """
    if isinstance(of_paths, Path):
        of_paths = [of_paths]

    return any(subpath in path.parents for subpath in of_paths)


def get_nested_dict_value(nested_dict, value, prepath=()):
    """
    Get a value from nested dictionaries.

    Use a recursive method to find a value in a dictionary of dictionaries
    (such as the metadata dictionaries we receive from the file parsers).
    Cribbed from: https://stackoverflow.com/a/22171182/1435788.

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
        path = (*prepath, k)
        if v == value:  # found value
            return path
        if hasattr(v, "items"):  # v is a dict
            dict_val = get_nested_dict_value(v, value, path)  # recursive call
            if dict_val is not None:
                return dict_val
    return None


def get_nested_dict_key(nested_dict, key_to_find, prepath=()):
    """
    Get a key from nested dictionaries.

    Use a recursive method to find a key in a dictionary of dictionaries
    (such as the metadata dictionaries we receive from the file parsers).
    Cribbed from: https://stackoverflow.com/a/22171182/1435788.

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
        path = (*prepath, k)
        if k == key_to_find:  # found key
            return path
        if hasattr(v, "items"):  # v is a dict
            dict_key = get_nested_dict_key(v, key_to_find, path)  # recursive call
            if dict_key is not None:
                return dict_key
    return None


def get_nested_dict_value_by_path(nest_dict, path):
    """
    Get a nested dictionary value by path.

    Get the value from within a nested dictionary structure by traversing into
    the dictionary as deep as that path found and returning that value.

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
        sub_dict = sub_dict[key] if key in sub_dict else "not found"

    return sub_dict


def set_nested_dict_value(nest_dict, path, value):
    """
    Set a nested dictionary value by path.

    Set a value within a nested dictionary structure by traversing into
    the dictionary as deep as that path found and changing it to `value`.
    Cribbed from https://stackoverflow.com/a/13688108/1435788.

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


def try_getting_dict_value(dict_, key):
    """
    Try to get a nested dictionary value.

    This method will try to get a value from a dictionary (potentially
    nested) and fail silently if the value is not found, returning None.

    Parameters
    ----------
    dict_ : dict
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
            return dict_[key]
        if hasattr(key, "__iter__"):
            return get_nested_dict_value_by_path(dict_, key)
        # we shouldn't reach this line, but always good to return a consistent
        # value just in case
        return "not found"  # pragma: no cover # noqa: TRY300
    except (KeyError, TypeError):
        return "not found"


def find_dirs_by_mtime(
    path: str,
    dt_from: datetime,
    dt_to: datetime,
    *,
    followlinks: bool = True,
) -> List[str]:
    """
    Find directories modified between two times.

    Given two timestamps, find the directories under a path that were
    last modified between the two.

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
        A list of the directories that have modification times within the
        time range provided
    """
    dirs = []

    # adjust the datetime objects with the tz_offset (usually should be 0) if
    # they are naive
    if dt_from.tzinfo is None:
        dt_from += tz_offset  # pragma: no cover
    if dt_to.tzinfo is None:
        dt_to += tz_offset  # pragma: no cover

    # use os.walk and only inspect the directories for mtime (much fewer
    # comparisons than looking at every file):
    logger.info(
        "Finding directories modified between %s and %s",
        dt_from.isoformat(),
        dt_to.isoformat(),
    )
    for dirpath, _, _ in os.walk(path, followlinks=followlinks):
        if dt_from.timestamp() < getmtime(dirpath) < dt_to.timestamp():
            dirs.append(dirpath)
    return dirs


def find_files_by_mtime(path: Path, dt_from, dt_to) -> List[Path]:  # pragma: no cover
    """
    Find files motified between two times.

    Given two timestamps, find files under a path that were
    last modified between the two.

    Parameters
    ----------
    path
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
    warnings.warn(
        "find_files_by_mtime has been deprecated in v1.2.0 and is "
        "no longer tested or supported. Please use "
        "gnu_find_files_by_mtime() instead",
        DeprecationWarning,
        stacklevel=2,
    )
    # find only the directories that have been modified between these two
    # timestamps (should be much faster than inspecting all files)
    # Note: this doesn't work reliably, so just look in entire path...

    dirs = [path]

    # adjust the datetime objects with the tz_offset (usually should be 0) if
    # they are naive
    if dt_from.tzinfo is None:
        dt_from += tz_offset
    if dt_to.tzinfo is None:
        dt_to += tz_offset

    files = set()  # use a set here (faster and we won't have duplicates)
    # for each of those directories, walk the file tree and inspect the
    # actual files:
    for directory in dirs:
        for dirpath, _, filenames in os.walk(directory, followlinks=True):
            for f in filenames:
                fname = Path(dirpath) / f
                if dt_from.timestamp() < getmtime(fname) < dt_to.timestamp():
                    files.add(fname)

    # convert the set to a list and sort my mtime
    files = list(files)
    files.sort(key=getmtime)

    return files


def gnu_find_files_by_mtime(
    path: Path,
    dt_from: datetime,
    dt_to: datetime,
    extensions: Optional[List[str]] = None,
    *,
    followlinks: bool = True,
) -> List[Path]:
    """
    Find files modified between two times.

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
        A list of strings representing the extensions to find. If None,
        all files between are found between the two times.
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
    List[str]
        A list of the files that have modification times within the
        time range provided (sorted by modification time)

    Raises
    ------
    RuntimeError
        If the find command cannot be found, or running it results in output
        to `stderr`
    """
    logger.info("Using GNU `find` to search for files")

    def _which(fname):
        def _is_exec(f):
            return Path(f).is_file() and os.access(f, os.X_OK)

        # Check to see if find command is on PATH:
        for exe in os.environ["PATH"].split(os.pathsep):
            exe_file = str(Path(exe) / fname)
            if _is_exec(exe_file):
                return exe_file

        return False

    if not _which("find"):
        msg = "find command was not found on the system PATH"
        raise RuntimeError(msg)

    # adjust the datetime objects with the tz_offset (usually should be 0) if
    # they are naive
    dt_from += tz_offset if dt_from.tzinfo is None else timedelta(0)
    dt_to += tz_offset if dt_to.tzinfo is None else timedelta(0)

    # join the given path with the root storage folder
    find_path = Path(os.environ["mmfnexus_path"]) / path

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
        find_path = Path(os.environ["mmfnexus_path"]) / path
        cmd = ["find", str(find_path), "-type", "l", "-xtype", "d", "-print0"]
        logger.info('Running followlinks find via subprocess.run: "%s"', cmd)
        out = subprocess.run(cmd, capture_output=True, check=True)
        paths = [f.decode() for f in out.stdout.split(b"\x00") if len(f) > 0]
        logger.info('Found the following symlinks: "%s"', paths)
        if paths:
            find_path = paths  # make find_path a list of str here for later use
            logger.info("find_path is: '%s'", find_path)

    # check if find_path is a Path and convert it to list if so:
    find_path = [find_path] if isinstance(find_path, Path) else find_path

    # Actually run find command (ignoring mib files if specified by
    # environment variable):

    cmd = ["find", "-H" if followlinks else ""]
    cmd += [str(p) for p in find_path]
    cmd += [
        "-type",
        "f",
        "-newermt",
        dt_from.isoformat(),
        "-not",
        "-newermt",
        dt_to.isoformat(),
    ]

    # add extensions as -iname patterns to find arguments
    if extensions is not None:
        cmd += ["("]
        for ext in extensions:
            cmd += ["-iname", f"*.{ext}", "-o"]
        cmd.pop()
        cmd += [")"]

    # if we need to ignore patterns, add them as an "and (-not -iname ...)"
    # syntax as find arguments
    if "NexusLIMS_ignore_patterns" in os.environ:
        ignore_patterns = json.loads(os.environ.get("NexusLIMS_ignore_patterns"))
        if ignore_patterns:
            cmd += ["-and", "("]
            for i in ignore_patterns:
                cmd += ["-not", "-iname", i, "-and"]
            cmd.pop()
            cmd += [")"]

    # add -print0 at the end since it will preempt our filename
    # patterns if we add it at the beginning
    cmd += ["-print0"]

    logger.info('Running via subprocess.run: "%s"', cmd)
    logger.info('Running via subprocess.run (as string): "%s"', " ".join(cmd))
    out = subprocess.run(cmd, capture_output=True, check=True)
    files = out.stdout.split(b"\x00")
    files = [Path(f.decode()) for f in files if len(f) > 0]

    # convert to set and back to remove duplicates and sort my mtime
    files = list(set(files))
    files.sort(key=getmtime)
    logger.info("Found %i files", len(files))
    return files


def sort_dict(item):
    """Recursively sort a dictionary by keys."""
    return {
        k: sort_dict(v) if isinstance(v, dict) else v
        for k, v in sorted(item.items(), key=lambda i: i[0].lower())
    }


def remove_dtb_element(tree, path):
    """
    Remove an element from a DictionaryTreeBrowser by setting it to None.

    Helper method that sets a specific leaf of a DictionaryTreeBrowser to None.
    Use with :py:meth:`remove_dict_nones` to fully remove the desired DTB element after
    setting it to None (after converting DTB to dictionary).

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
    tree.set_item(path, None)

    return tree


def remove_dict_nones(dictionary: Dict[Any, Any]) -> Dict[Any, Any]:
    """
    Delete keys with a value of ``None`` in a dictionary, recursively.

    Taken from https://stackoverflow.com/a/4256027.

    Parameters
    ----------
    dictionary
        The dictionary, with keys that have None values removed

    Returns
    -------
    dict
        The same dictionary, but with "Nones" removed
    """
    for key, value in list(dictionary.items()):
        if value is None:
            del dictionary[key]
        elif isinstance(value, dict):
            remove_dict_nones(value)
    return dictionary


def _zero_bytes(fname: Path, bytes_from, bytes_to) -> Path:
    """
    Set certain byte locations within a file to zero.

    This method helps creating highly-compressible test files.

    Parameters
    ----------
    fname
    bytes_from : int or :obj:`list` of str
        The position of the file (in decimal) at which to start zeroing
    bytes_to : int or :obj:`list` of str
        The position of the file (in decimal) at which to stop zeroing. If
        list, must be the same length as list given in ``bytes_from``

    Returns
    -------
    new_fname
        The modified file that has it's bytes zeroed
    """
    filename, ext = fname.stem, fname.suffix
    if ext == ".ser":
        index = int(filename.split("_")[-1])
        basename = "_".join(filename.split("_")[:-1])
        new_fname = fname.parent / f"{basename}_dataZeroed_{index}{ext}"
    else:
        new_fname = fname.parent / f"{filename}_dataZeroed{ext}"
    copyfile(fname, new_fname)

    if isinstance(bytes_from, int):
        bytes_from = [bytes_from]
        bytes_to = [bytes_to]

    with Path(new_fname).open(mode="r+b") as f:
        for from_byte, to_byte in zip(bytes_from, bytes_to):
            f.seek(from_byte)
            f.write(b"\0" * (to_byte - from_byte))

    return new_fname


def get_timespan_overlap(
    range_1: Tuple[datetime, datetime],
    range_2: Tuple[datetime, datetime],
) -> timedelta:
    """
    Find the amount of overlap between two time spans.

    Adapted from https://stackoverflow.com/a/9044111.

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
    datetime.timedelta
        The amount of overlap between the time ranges
    """
    latest_start = max(range_1[0], range_2[0])
    earliest_end = min(range_1[1], range_2[1])
    delta = earliest_end - latest_start

    return max(timedelta(0), delta)


def get_auth(filename: Optional[Path] = None, *, basic: bool = False):
    """
    Get an authentication scheme for NexusLIMS requests.

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
    if filename is None:
        filename = Path("credentials.ini")

    # DONE: this should be moved out of sharepoint calendar an into general
    #  utils since it's used for CDCS as well
    try:
        username = os.environ["nexusLIMS_user"]
        passwd = os.environ["nexusLIMS_pass"]
        logger.info("Authenticating using environment variables")
    except KeyError as exception:
        # if absolute path was provided, use that, otherwise find filename in
        # this directory
        if filename.is_absolute():
            pass
        else:
            filename = Path(__file__).parent / filename

        # Raise error if the configuration file is not found
        if not filename.is_file():
            msg = (
                "No credentials were specified with "
                "environment variables, and credential "
                f"file {filename} was not found"
            )
            raise AuthenticationError(msg) from exception

        config = ConfigParser()
        config.read(filename)

        username = config.get("nexus_credentials", "username")
        passwd = config.get("nexus_credentials", "password")

    if basic:
        # return just username and password (for BasicAuthentication)
        return username, passwd

    domain = "nist"
    path = domain + "\\" + username

    return HttpNtlmAuth(path, passwd)


def has_delay_passed(date: datetime) -> bool:
    """
    Check if the current time is greater than the configured delay.

    Check if the current time is greater than the configured (or default) record
    building delay configured in the ``nexusLIMS_file_delay_days`` environment variable.
    If the date given is timezone-aware, the current time in that timezone will be
    compared.

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
        delay = float(os.getenv("nexusLIMS_file_delay_days", "2"))
    except ValueError:
        # if it cannot be coerced to a number, warn and set to the
        # default of 2 days
        logger.warning(
            "The environment variable value of nexusLIMS_file_delay_days (%s) could "
            "not be understood as a number, so using the default of 2 days.",
            os.getenv("nexusLIMS_file_delay_days"),
        )
        delay = 2

    delay = timedelta(days=delay)

    now = (
        datetime.now()  # noqa: DTZ005
        if date.tzinfo is None
        else datetime.now(date.tzinfo)
    )

    delta = now - date

    return delta > delay


def current_system_tz():
    """Get the current system timezone information."""
    return (
        timezone(timedelta(seconds=-time.altzone), time.tzname[1])
        if time.daylight
        else timezone(timedelta(seconds=-time.timezone), time.tzname[0])
    )


def replace_mmf_path(path: Path, suffix: str) -> Path:
    """
    Given an input "mmfnexus_path" path, generate equivalent "nexusLIMS_path" path.

    If the given path is not a subpath of "mmfnexus_path", a warning will be logged
    and the suffix will just be added at the end.

    Parameters
    ----------
    path
        The input path, which is expected to be a subpath of the mmfnexus_path directory
    suffix
        Any added suffix to add to the path (useful for appending with a new extension,
        such as ``.json``)

    Returns
    -------
    pathlib.Path
        A resolved pathlib.Path object pointing to the new path
    """
    mmf_path = Path(os.environ["mmfnexus_path"])
    nexuslims_path = Path(os.environ["nexusLIMS_path"])

    if mmf_path not in path.parents:
        logger.warning("%s is not a sub-path of %s", path, os.environ["mmfnexus_path"])
    return Path(str(path).replace(str(mmf_path), str(nexuslims_path)) + suffix)


class AuthenticationError(Exception):
    """Class for showing an exception having to do with authentication."""

    def __init__(self, message):
        self.message = message
