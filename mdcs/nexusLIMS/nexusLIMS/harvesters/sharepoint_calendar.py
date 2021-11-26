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
import urllib as _urllib

import nexusLIMS
from requests_ntlm import HttpNtlmAuth as _HttpNtlmAuth
import pytz as _pytz
from pytz import timezone as _timezone
from lxml import etree as _etree
import ldap3 as _ldap3
from datetime import datetime as _datetime
from datetime import timedelta as _timedelta
from configparser import ConfigParser as _ConfigParser
from nexusLIMS.db.session_handler import Session as _Session
from nexusLIMS.instruments import Instrument as _Instrument
from nexusLIMS.instruments import instrument_db as _instr_db
from nexusLIMS.instruments import get_instr_from_calendar_name as _from_cal
from nexusLIMS.utils import nexus_req as _nexus_req
from nexusLIMS.utils import _get_timespan_overlap
from nexusLIMS.harvesters import ReservationEvent

_logger = _logging.getLogger(__name__)
INDENT = '  '

__all__ = ['res_event_from_session', 'res_event_from_xml',
           'AuthenticationError', 'get_auth', 'fetch_xml',
           'get_div_and_group', 'get_events', 'dump_calendars']


class AuthenticationError(Exception):
    """Class for showing an exception having to do with authentication"""
    def __init__(self, message):
        self.message = message


def res_event_from_xml(xml, date=None):
    """
    Creates a ReservationEvent from an xml response from
    :py:func:`~.fetch_xml` rather than providing values directly. If there are
    multiple events in the XML, it will only process the first one

    Parameters
    ----------
    xml : str
        Output of an API query to the Sharepoint calendar that contains a
        single event (which should be the case if start and end times were
        provided to :py:func:`~.fetch_xml`)
    date : None or datetime.datetime
        (Optional) a date to use in serializing the output in case there is
        no date information in the XML response (i.e. there were no
        reservations found for the date range searched)

    Notes
    -----
    Each attribute of the resulting ``ReservationEvent`` is mapped to a node
    in the XML API response, and will be ``None`` if the node cannot be found in
    the XML. Timestamps are given in either Zulu time (UTC) or with a
    local timestamp offset, so datetime attributes should be timezone-aware.

    Mapping of attributes:

    - ``experiment_title`` - present at
      ``/feed/entry/content/m:properties/d:TitleOfExperiment``
    - ``instrument`` - fetched using the name of the calendar, present at
      ``/feed/title``
    - ``last_updated`` - present at ``/feed/entry/updated``
    - ``username`` - present at
      ``/feed/entry/link[@title="UserName"]/m:inline/feed/entry/content/m:properties/d:UserName``
    - ``created_by`` - present at
      ``/feed/entry/link[@title="CreatedBy"]/m:inline/feed/entry/content/m:properties/d:UserName``
    - ``start_time`` - ``/feed/entry/content/m:properties/d:StartTime`` (The API
      response returns this value without a timezone, in the timezone of the
      sharepoint server
    - ``end_time`` - present at ``/feed/entry/content/m:properties/d:EndTime``
    - ``reservation_type`` - /feed/entry/content/m:properties/d:CategoryValue
    - ``experiment_purpose`` - present at
      ``/feed/entry/content/m:properties/d:ExperimentPurpose``
    - ``sample_details`` - present at
      ``/feed/entry/content/m:properties/d:SampleDetails``
    - ``sample_pid`` - not collected by the SharePoint form at this time
    - ``project_id`` - a non-persistent identifier string
      present at ``/feed/entry/content/m:properties/d:ProjectID``
    - ``internal_id`` - present at ``/feed/entry/content/m:properties/d:Id``

    Returns
    -------
    res_event : ReservationEvent
        An object representing an entry on the SharePoint calendar. Could
        be empty if no ``entry`` nodes are present in XML response
    """
    def _get_el_text(xpath):
        el = et.find(xpath, namespaces=et.nsmap)
        if el is None:
            return el
        else:
            return el.text

    et = _etree.fromstring(xml)

    # get instrument from calendar title
    instrument = _get_el_text('title')
    if instrument is not None:
        instrument = _from_cal(instrument)

    if _get_el_text('entry') is None:
        # no "entry" nodes were found, so return very basic ReservationEvent
        return ReservationEvent(instrument=instrument, start_time=date)

    title = _get_el_text('entry//d:TitleOfExperiment')
    sp_tz = _get_sharepoint_tz()
    updated = _get_el_text('entry/updated')
    if updated is not None:
        updated = _datetime.fromisoformat(updated)
    user_full_name = _get_el_text('entry/link[@title="UserName"]//d:Name')
    username = _get_el_text('entry/link[@title="UserName"]//d:UserName')
    created_by_full_name = _get_el_text(
        'entry/link[@title="CreatedBy"]//d:Name')
    created_by = _get_el_text('entry/link[@title="CreatedBy"]//d:UserName')
    start_time = _get_el_text('entry//d:StartTime')
    if start_time is not None:
        start_time = _timezone(sp_tz).localize(
            _datetime.fromisoformat(start_time))
    end_time = _get_el_text('entry//d:EndTime')
    if end_time is not None:
        end_time = _timezone(sp_tz).localize(
            _datetime.fromisoformat(end_time))
    category_value = _get_el_text('entry//d:CategoryValue')
    sample_details = _get_el_text('entry//d:SampleDetails')
    purpose = _get_el_text('entry//d:ExperimentPurpose')
    project_name = _get_el_text('entry//d:ProjectID')
    sharepoint_id = _get_el_text('entry/content//d:Id')

    return ReservationEvent(
        experiment_title=title, instrument=instrument, last_updated=updated,
        username=username, user_full_name=user_full_name,
        created_by=created_by, created_by_full_name=created_by_full_name,
        start_time=start_time, end_time=end_time,
        reservation_type=category_value, experiment_purpose=purpose,
        sample_details=sample_details, project_name=project_name,
        internal_id=sharepoint_id
    )


def get_div_and_group(username):
    """
    Query the NIST active directory to get division and group information for a
    user.

    Parameters
    ----------
    username : str
        a valid NIST username (the short format: e.g. "ear1"
        instead of ernst.august.ruska@nist.gov).

    Returns
    -------
    div, group : str
        The division and group numbers for the user (as strings)
    """
    server = _ldap3.Server(nexusLIMS.ldap_url)
    with _ldap3.Connection(server, auto_bind=True) as conn:
        conn.search('***REMOVED***',
                    f'(***REMOVED***{username}***REMOVED***)',
                    attributes=['*'])
        res = conn.entries[0]

    div = res.nistdivisionnumber.value
    group = res.nistgroupnumber.value

    return div, group


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
        authentication (like what is used for CDCS access rather than for
        NIST network resources)

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


def fetch_xml(instrument, dt_from=None, dt_to=None):
    """
    Get the XML responses from the Nexus Sharepoint calendar for one,
    multiple, or all instruments.

    Parameters
    ----------
    instrument : :py:class:`~nexusLIMS.instruments.Instrument`
        As defined in :py:func:`~.get_events`,
        one of the NexusLIMS instruments contained in the
        :py:attr:`~nexusLIMS.instruments.instrument_db` database.
        Controls what instrument calendar is used to get events
    dt_from : :py:class:`~datetime.datetime` or None
        A :py:class:`~datetime.datetime` object representing the start of a
        calendar event to search for.
        If ``dt_from`` and ``dt_to`` are `None`, no date filtering will be done.
        If just ``dt_from`` is `None`, all events from the beginning of the
        calendar record will be returned up until ``dt_to``.
    dt_to : :py:class:`~datetime.datetime` or None
        A :py:class:`~datetime.datetime` object representing the end of
        calendar event to search for.
        If ``dt_from`` and ``dt_to`` are `None`, no date filtering will be done.
        If just ``dt_to`` is `None`, all events from the ``dt_from`` to the
        present will be returned.

    Returns
    -------
    api_response : str
        A string containing the XML calendar information for each
        instrument requested, stripped of the empty default namespace. If
        ``dt_from`` and ``dt_to`` are provided, it will contain just one
        `"entry"` representing a single event on the calendar

    Notes
    -----
    To find the right event, an API request to the Sharepoint Calendar will
    be made for all events starting on the same day as ``dt_from``. This
    could result in multiple events being returned if there is more than one
    session scheduled on that microscope for that day. To find the right one,
    the timespan between each event's ``StartTime`` and ``EndTime`` returned
    from the calendar will be compared with the timespan between ``dt_from`` and
    ``dt_to``. The event with the greatest overlap will be taken as the
    correct one. This approach should allow for some flexibility in terms of
    non-exact matching between the reserved timespans and those recorded by
    the session logger.
    """

    # Paths for Nexus Instruments that can be booked through sharepoint
    # Instrument names can be found at
    # https://***REMOVED***/***REMOVED***/_vti_bin/ListData.svc
    # and
    # https://***REMOVED***nexuslims/NexusMicroscopyLIMS/wikis/Sharepoint-Calendar-Information

    # Parse instrument parameter input, leaving inst_to_fetch as list of
    # nexuslims.instruments.Instrument objects
    if isinstance(instrument, str):
        # try to convert from instrument PID string to actual instrument
        try:
            instrument = _instr_db[instrument]
        except KeyError:
            raise KeyError('Entered instrument string "{}" could not be '
                           'parsed'.format(instrument))
    elif isinstance(instrument, _Instrument):
        pass
    else:
        raise ValueError('Entered instrument '
                         '"{}" could not be parsed'.format(instrument))

    api_response = ''

    instr_url = instrument.api_url + '?$expand=CreatedBy,UserName'

    # build the date filtering string depending on datetime input
    if dt_from is None and dt_to is None:
        pass
    elif dt_from is None:
        # for API, we need to add a day to dt_to so we can use "lt" as filter
        to_str = (dt_to + _timedelta(days=1)).strftime('%Y-%m-%d')
        instr_url += f"&$filter=StartTime lt DateTime'{to_str}'"
    elif dt_to is None:
        # for API, we subtract day from dt_from to ensure we don't miss any
        # sessions close to the UTC offset (mostly for sessions scheduled at
        # midnight)
        from_str = (dt_from - _timedelta(days=1)).strftime('%Y-%m-%d')
        instr_url += f"&$filter=StartTime ge DateTime'{from_str}'"
    else:
        # we ask the API for all events that start on same day as dt_from
        from_str = (dt_from - _timedelta(days=1)).strftime('%Y-%m-%d')
        to_str = (dt_from + _timedelta(days=1)).strftime('%Y-%m-%d')
        instr_url += f"&$filter=StartTime ge DateTime'{from_str}' and " \
                     f"StartTime lt DateTime'{to_str}'"

    _logger.info("Fetching Nexus calendar events from {}".format(instr_url))
    r = _nexus_req(instr_url, _requests.get)
    _logger.info("  {} -- {} -- response: {}".format(instrument.name,
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
        api_response = xml
    else:
        raise _requests.exceptions.\
            ConnectionError('Could not access Nexus SharePoint Calendar '
                            'API at "{}"'.format(instr_url))

    # identify which event matches the one we searched for (if there's more
    # than one, and we supplied both dt_from and dt_to) and remove the other
    # events from the api response as needed
    if dt_from is not None and dt_to is not None:
        doc = _etree.fromstring(api_response)
        entries = doc.findall('entry')
        # more than one calendar event was found for this date
        if len(entries) > 1:
            starts, ends = [], []
            for e in entries:
                ns = _etree.fromstring(xml).nsmap
                starts.append(e.find('.//d:StartTime', namespaces=ns).text)
                ends.append(e.find('.//d:EndTime', namespaces=ns).text)
            starts = [_datetime.fromisoformat(s) for s in starts]
            ends = [_datetime.fromisoformat(e) for e in ends]

            # starts and ends are lists of datetimes representing the start and
            # end of each event returned by the API, so get how much each
            # range overlaps with the range dt_from to dt_to
            overlaps = [_get_timespan_overlap((dt_from, dt_to), (s, e))
                        for s, e in zip(starts, ends)]

            # find which 'entry' is the one that matches our timespan
            max_overlap = overlaps.index(max(overlaps))
            # create a list of entry indices to remove by excluding the one
            # with maximal overlap
            to_remove = list(range(len(overlaps)))
            del to_remove[max_overlap]

            # loop through in reverse order so we don't mess up the numbering
            # of the entry elements
            for idx in to_remove[::-1]:
                # XPath numbering starts at 1, so add one to idx
                doc.remove(doc.find(f'entry[{idx + 1}]'))

            # api_response will now have non-relevant entry items removed
            api_response = _etree.tostring(doc)

    return api_response


def get_events(instrument=None,
               dt_from=None,
               dt_to=None,
               user=None,
               division=None,
               group=None):
    """
    Get calendar events for a particular instrument on the Microscopy Nexus,
    on some date, or by some user

    Parameters
    ----------
    instrument : :py:class:`~nexusLIMS.instruments.Instrument` or str
        One of the NexusLIMS instruments contained in the
        :py:attr:`~nexusLIMS.instruments.instrument_db` database.
        Controls what instrument calendar is used to get events. If string,
        value should be one of the instrument PIDs from the Nexus facility.
    dt_from : :py:class:`~datetime.datetime` or None
        A :py:class:`~datetime.datetime` object representing the start of a
        calendar event to search for, as in :py:func:`~.fetch_xml`.
        If ``dt_from`` and ``dt_to`` are `None`, no date filtering will be done.
        If just ``dt_from`` is `None`, all events from the beginning of the
        calendar record will be returned up until ``dt_to``.
    dt_to : :py:class:`~datetime.datetime` or None
        A :py:class:`~datetime.datetime` object representing the end of
        calendar event to search for, as in :py:func:`~.fetch_xml`.
        If ``dt_from`` and ``dt_to`` are `None`, no date filtering will be done.
        If just ``dt_to`` is `None`, all events from the ``dt_from`` to the
        present will be returned.
    user : None or str
        Either None or a valid NIST username (the short format: e.g. ``"ear1"``
        instead of ernst.august.ruska@nist.gov). If None, no user filtering
        will be performed. No verification of username is performed,
        so it is up to the user to make sure this is correct.
    division : None or str
        The division number of the project. If provided, this string will be
        replicated under the "project" information in the outputted XML. If
        ``None`` (and ``user`` is provided), the division will be queried
        from the active directory server.
    group : None or str
        The group number of the project. If provided, this string will be
        replicated under the "project" information in the outputted XML. If
        ``None`` (and ``user`` is provided), the group will be queried
        from the active directory server.

    Returns
    -------
    res_event : ReservationEvent
        A ``ReservationEvent`` in a string, containing information about a
        single reservation, including title, instrument, user information,
        reservation purpose, sample details, description, and date/time
        information.
    """

    xml = fetch_xml(instrument, dt_from=dt_from, dt_to=dt_to)

    res_event = res_event_from_xml(xml, date=dt_from)
    _logger.info(res_event)

    # currently not using division and group code

    # if not division and not group and user:
    #     _logging.info('Querying LDAP for division and group info')
    #     division, group = get_div_and_group(user)

    return res_event


def dump_calendars(instrument=None, user=None, dt_from=None, dt_to=None,
                   group=None, division=None,
                   filename='cal_events.xml'):
    """
    Write the results of :py:func:`~.get_events` to a file.

    Parameters
    ----------
    instrument : :py:class:`~nexusLIMS.instruments.Instrument` or str
        One of the NexusLIMS instruments contained in the
        :py:attr:`~nexusLIMS.instruments.instrument_db` database.
        Controls what instrument calendar is used to get events. If value is
        a string, it should be one of the instrument PIDs from the Nexus
        facility
    dt_from : :py:class:`~datetime.datetime` or None
        A :py:class:`~datetime.datetime` object representing the start of a
        calendar event to search for, as in :py:func:`~.fetch_xml`.
        If ``dt_from`` and ``dt_to`` are `None`, no date filtering will be done.
        If just ``dt_from`` is `None`, all events from the beginning of the
        calendar record will be returned up until ``dt_to``.
    dt_to : :py:class:`~datetime.datetime` or None
        A :py:class:`~datetime.datetime` object representing the end of
        calendar event to search for, as in :py:func:`~.fetch_xml`.
        If ``dt_from`` and ``dt_to`` are `None`, no date filtering will be done.
        If just ``dt_to`` is `None`, all events from the ``dt_from`` to the
        present will be returned.
    user : None or str
        Either None or a valid NIST username (the short format: e.g. ``"ear1"``
        instead of ernst.august.ruska@nist.gov). If None, no user filtering
        will be performed. No verification of username is performed,
        so it is up to the user to make sure this is correct.
    division : None or str
        The division number of the project. If provided, this string will be
        replicated under the "project" information in the outputted XML. If
        ``None`` (and ``user`` is provided), the division will be queried
        from the active directory server.
    group : None or str
        The group number of the project. If provided, this string will be
        replicated under the "project" information in the outputted XML. If
        ``None`` (and ``user`` is provided), the group will be queried
        from the active directory server.
    filename : str
        The filename to which the events should be written
    """
    with open(filename, 'w') as f:
        res_event = get_events(instrument=instrument, dt_from=dt_from,
                               dt_to=dt_to, user=user, division=division,
                               group=group)
        f.write(_etree.tostring(res_event.as_xml(), xml_declaration=True,
                                encoding='UTF-8', pretty_print=True).decode())


def _get_sharepoint_date_string(dt):
    """
    Using the ``nexusLIMS_timezone`` environment variable, convert a "naive"
    datetime object to a string with the proper offset to be correctly
    handled by the Sharepoint API. This timezone should be one listed as part
    of the
    `tz database <https://en.wikipedia.org/wiki/List_of_tz_database_time_zones_>`.

    The reason this is necessary is that the Sharepoint calendar API uses UTC
    datetime, but displays them in the local timezone, so we need to convert
    our local datetime to UTC.  i.e. if you have an event that is
    displayed on the calendar as starting at 2019-07-24T00:00:00 (midnight on
    July 24th), an API query datetime greater than or equal to that time
    will not work unless you convert to UTC (2019-07-23T20:00:00.000)


    Parameters
    ----------
    dt : :py:class:`~datetime.datetime`
        The "naive" local timezone datetime object (i.e. as displayed in the
        sharepoint calendar)

    Returns
    -------
    dt_str : str
        The datetime formatted in ISO format, adjusted for the timezone
        offset (for Eastern time, that's four hours during DST and 5 hours in
        standard time)
    """
    if 'nexusLIMS_timezone' not in _os.environ:
        raise EnvironmentError('Please make sure the "nexusLIMS_timezone" '
                               'variable is set as part of your environment '
                               'before using this function')

    tz = _timezone(_os.environ['nexusLIMS_timezone'])
    dt_str = _pytz.utc.localize(dt).astimezone(tz).strftime('%Y-%m-%dT%H:%M:%S')

    return dt_str


def _get_sharepoint_tz():
    """
    Based on the response from the Sharepoint API, get the timezone of the
    server in tz database format (only implemented for US timezones, since
    Sharepoint uses non-standard time zone names)

    Returns
    -------
    timezone : str or None
        The timezone in tz database format
    """
    cdcs_url = nexusLIMS._urls.calendar_root_url
    r = _nexus_req(cdcs_url + '/_api/web/RegionalSettings/TimeZone',
                   _requests.get)
    et = _etree.fromstring(r.text.encode())
    tz_description = et.find('.//d:Description', namespaces=et.nsmap)
    if tz_description is not None:
        tz_description = tz_description.text

    timezone = None

    if 'Eastern Time' in tz_description:
        timezone = 'America/New_York'
    elif 'Central Time' in tz_description:
        timezone = 'America/Chicago'
    elif 'Mountain Time' in tz_description:
        timezone = 'America/Denver'
    elif 'Pacific Time' in tz_description:
        timezone = 'America/Los_Angeles'
    elif 'Hawaii' in tz_description:
        timezone = 'Pacific/Honolulu'

    return timezone


def res_event_from_session(session: _Session) -> ReservationEvent:
    return get_events(instrument=session.instrument,
                      dt_from=session.dt_from,
                      dt_to=session.dt_to,
                      user=session.user)
