#! /usr/bin/env python

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

import os as _os
import re as _re
import logging as _logging
import requests as _requests

from requests_ntlm import HttpNtlmAuth as _HttpNtlmAuth
from lxml import etree as _etree
from dateparser import parse as _dp_parse
from datetime import datetime as _datetime
from configparser import ConfigParser as _ConfigParser
from nexusLIMS.instruments import instrument_db as _instr_db

_logger = _logging.getLogger(__name__)
XSLT_PATH = _os.path.join(_os.path.dirname(__file__), "cal_parser.xsl")
INDENT = '  '

__all__ = ['AuthenticationError', 'get_auth', 'fetch_xml',
           'parse_xml', 'get_events', 'wrap_events', 'dump_calendars']

class AuthenticationError(Exception):
    """Class for showing an exception having to do with authentication"""
    def __init__(self, message):
        self.message = message


# TODO: we need a class here that represents one entry from the calendar
class CalendarEvent:
    """
     A representation of a single calendar event returned from the SharePoint
     API

     Instances of this class correspond to AcquisitionActivity nodes in the
     `NexusLIMS schema <https://data.nist.gov/od/dm/nexus/experiment/v1.0>`_

     Attributes
     ----------
     start : datetime.datetime
         The start point of this AcquisitionActivity
     end : datetime.datetime
         The end point of this AcquisitionActivity
     mode : str
         The microscope mode for this AcquisitionActivity (i.e. 'IMAGING',
         'DIFFRACTION', 'SCANNING', etc.)
     unique_params : set
         A set of dictionary keys that comprises all unique metadata keys
         contained within the files of this AcquisitionActivity
     setup_params : dict
         A dictionary containing metadata about the data that is shared
         amongst all data files in this AcquisitionActivity
     unique_meta : list
         A list of dictionaries (one for each file in this
         AcquisitionActivity) containing metadata key-value pairs that are
         unique to each file in ``files`` (i.e. those that could not be moved
         into ``setup_params`)
     files : list
         A list of filenames belonging to this AcquisitionActivity
     sigs : list
         A list of *lazy* (to minimize loading times) HyperSpy signals in this
         AcquisitionActivity. HyperSpy is used to facilitate metadata reading
     meta : list
         A list of dictionaries containing the "important" metadata for each
         signal/file in ``sigs`` and ``files``
     """

    def __init__(self,
                 start=_datetime.now(),
                 end=_datetime.now(),
                 mode='',
                 unique_params=None,
                 setup_params=None,
                 unique_meta=None,
                 files=None,
                 sigs=None,
                 meta=None):

        self.start = start
        self.end = end
        self.mode = mode
        self.unique_params = set() if unique_params is None else unique_params
        self.setup_params = setup_params
        self.unique_meta = unique_meta
        self.files = [] if files is None else files
        self.sigs = [] if sigs is None else sigs
        self.meta = [] if meta is None else meta


def get_auth(filename="credentials.ini"):
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

    Returns
    -------
    auth : ``requests_ntlm.HttpNtlmAuth``
        NTLM authentication handler for ``requests``

    Notes
    -----
        The credentials file is expected to have a section named
        ``[nexus_credentials]`` and two values: ``username`` and
        ``password``. See the ``credentials.ini.example`` file included in
        the repository as an example.
    """
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

    domain = 'nist'
    path = domain + '\\' + username

    auth = _HttpNtlmAuth(path, passwd)
    
    return auth 


def fetch_xml(instrument=None):
    """
    Get the XML responses from the Nexus Sharepoint calendar for one,
    multiple, or all instruments.

    Parameters
    ----------
    instrument : None, str, or list
        As defined in :py:func:`~.get_events`
        One or more of ['msed_titan', 'quanta', 'jeol_sem', 'hitachi_sem',
        'jeol_tem', 'cm30', 'em400', 'hitachi_s5500', 'mmsd_titan',
        'fei_helios_db'], or None. If None, events from all instruments will be
        returned.

    Returns
    -------
    api_response : list
        A list of strings containing the XML calendar information for each
        instrument requested, stripped of the empty default namespace
    """
    # DONE: parse instrument input and loop through to generate total output
    #       [x] add logic for getting list of instruments to process
    #       [x] concatenate XML output from each transform into single XML
    #           document

    # Paths for Nexus Instruments that can be booked through sharepoint
    # calendar, mapped to more user-friendly names
    # Instrument names can be found at
    # https://***REMOVED***/***REMOVED***/_vti_bin/ListData.svc
    # and
    # https://***REMOVED***nexuslims/NexusMicroscopyLIMS/wikis/Sharepoint-Calendar-Information

    # Parse instrument parameter input, leaving inst_to_fetch as list of
    # nexuslims.instruments._Instrument objects
    if instrument is None:
        inst_to_fetch = list(_instr_db.values())
    elif isinstance(instrument, str):
        inst_to_fetch = [_instr_db[instrument]]
    elif hasattr(instrument, '__iter__'):
        inst_to_fetch = [_instr_db[i] for i in instrument]
    else:
        _logger.warning('Entered instrument "{}" could not be parsed; '
                        'reverting to None...'.format(instrument))
        inst_to_fetch = list(_instr_db.values())

    api_response = [''] * len(inst_to_fetch)

    for i, instr in enumerate(inst_to_fetch):
        instr_url = instr.api_url + '?$expand=CreatedBy'
        _logger.info("Fetching Nexus calendar events from {}".format(instr_url))
        r = _requests.get(instr_url, auth=get_auth())
        _logger.info("  {} -- {} -- response: {}".format(instr.name,
                                                         instr_url,
                                                         r.status_code))

        if r.status_code == 401:
            # Authentication did not succeed and we received an *Unauthorized*
            # response from the server
            raise AuthenticationError('Could not authenticate to the Nexus '
                                      'SharePoint Calendar. Please check the '
                                      'credentials and try again.')

        if r.status_code == 200:
            # XML elements have a default namespace prefix (Atom format),
            # but lxml does not like an empty prefix, so it is easiest to
            # just sanitize the input and remove the namespaces as in
            # https://stackoverflow.com/a/18160164/1435788:
            xml = _re.sub(r'\sxmlns="[^"]+"', '', r.text, count=1)

            # API returns utf-8 encoding, so encode correctly
            xml = bytes(xml, encoding='utf-8')
            api_response[i] = xml
        else:
            raise _requests.exceptions.\
                ConnectionError('Could not access Nexus SharePoint Calendar '
                                'API at "{}"'.format(instr_url))

    return api_response


def parse_xml(xml, date=None, user=None):
    """
    Parse and translate an XML string from the API into a nicer format

    Parameters
    ----------
    xml : str or bytes
        A string containing XML, such as that returned by :py:func:`~.fetch_xml`
    date : None or str
        Either None or a YYYY-MM-DD date string indicating the date from
        which events should be fetched (note: the start time of each entry
        is what will be compared). If None, no date filtering will be
        performed.
    user : None or str
        Either None or a valid NIST username (the short format: e.g. "ear1"
        instead of ernst.august.ruska@nist.gov).

    Returns
    -------
    simplified_dom : ``lxml.XSLT`` transformation result
    """
    parser = _etree.XMLParser(remove_blank_text=True, encoding='utf-8')

    # load XML structure from  string
    root = _etree.fromstring(xml, parser)

    # use LXML to load XSLT stylesheet into xsl_transform
    # (note, etree.XSLT needs to be called on a root _Element
    # not an _ElementTree)
    xsl_dom = _etree.parse(XSLT_PATH, parser).getroot()
    xsl_transform = _etree.XSLT(xsl_dom)

    # setup parameters for passing to XSLT parser
    date_param = "''" if date is None else "'{}'".format(date)
    # DONE: parsing of username
    user_param = "''" if user is None else "'{}'".format(user)

    # do XSLT transformation
    simplified_dom = xsl_transform(root,
                                   date=date_param,
                                   user=user_param)

    return simplified_dom


# DONE: split up fetching calendar from server and parsing XML response
def get_events(instrument=None, date=None, user=None, wrap=True):
    """
    Get calendar events for a particular instrument on the Microscopy Nexus,
    on some date, or by some user

    Parameters
    ----------
    instrument : None, str, or list
        One or more of ['msed_titan', 'quanta', 'jeol_sem', 'hitachi_sem',
        'jeol_tem', 'cm30', 'em400', 'hitachi_s5500', 'mmsd_titan',
        'fei_helios_db'], or ``None``. If ``None``, all instruments will be
        returned.

    date : None or str
        Either None or a YYYY-MM-DD date string indicating the date from
        which events should be fetched (note: the start time of each entry
        is what will be compared). If None, no date filtering will be
        performed. Date will be parsed by :py:func:`dateparser.parse`,
        but providing the date in the ISO standard format is preferred for
        consistent behavior.

    user : None or str
        Either None or a valid NIST username (the short format: e.g. ``"ear1"``
        instead of ernst.august.ruska@nist.gov). If None, no user filtering
        will be performed. No verification of username is performed,
        so it is up to the user to make sure this is correct.

    wrap : bool
        Boolean used to choose whether to apply the wrap_events() function to the output XML string.

    Returns
    -------
    output : str
        A well-formed XML document in a string, containing one or more <event>
        tags that contain information about each reservation, including title,
        instrument, user information, reservation purpose, sample details,
        description, and date/time information.
    """

    # DONE: parsing of date
    # Use dateparser to get python datetime input, and return as YYYY-MM-DD
    if date is not None:
        date_datetime = _dp_parse(date, settings={'STRICT_PARSING': True})
        if date_datetime:
            date = _datetime.strftime(date_datetime, '%Y-%m-%d')
        else:
            _logger.warning("Entered date could not be parsed; reverting to "
                            "None...")
            date = None

    output = ''
    xml_strings = fetch_xml(instrument)
    for xml in xml_strings:
        # parse the xml into a string, and then indent
        output += INDENT + str(parse_xml(xml, date, user)).\
            replace('\n', '\n' + INDENT)

    if wrap:
        output = wrap_events(output)

    return output


def wrap_events(events_string):
    """
    Helper function to turn events string from :py:func:`~.get_events` into a
    well-formed XML file with proper indentation

    Parameters
    ----------
    events_string : str

    Returns
    -------
    result : str
        The full XML file as a string
    """
    # Holder for final XML output with proper header
    result = """<?xml version="1.0"?>
    <events>
    {}<dateRetrieved>{}</dateRetrieved>
    """.format(INDENT, _datetime.now().isoformat())
    # add indent to first line and all newlines:
    events_string = INDENT + events_string
    events_string = events_string.replace('\n', '\n' + INDENT)
    result += events_string
    result = result.strip().strip('\n')
    result += "\n</events>"

    return result


def dump_calendars(instrument=None, user=None, date=None,
                   filename='cal_events.xml'):
    """
    Write the results of :py:func:`~.get_events` to a file
    """
    with open(filename, 'w') as f:
        text = get_events(instrument=instrument, date=date, user=user)
        f.write(text)

# if __name__ == '__main__':
#     """
#     These lines are just for testing. For real use, import the methods you
#     need and operate from there
#     """
#     _logging.basicConfig(level=_logging.INFO)
#     dump_calendars(instrument='msed_titan')
#     dump_calendars(date='2019-02-28')
#     _logging.info(get_events(instrument=None))
#     _logging.info(get_events(date='2019-02-25'))
#     _logging.info(get_events(user='***REMOVED***'))
#     _logging.info(get_events(date='2018-12-26', user='***REMOVED***'))
#     _logging.info(get_events())
