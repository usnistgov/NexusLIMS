#  NIST Public License - 2021
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
"""
This module contains the functionality to harvest instruments, reservations,
etc. from an instance of NEMO (https://github.com/usnistgov/NEMO/), a
calendering and laboratory logistics application.
"""
from typing import Any, Callable, List, Union, Dict, Tuple, Optional

import re
import os
import requests
import logging
from urllib.parse import urljoin, urlparse, parse_qs
from datetime import datetime, timedelta
from pytz import timezone as pytz_timezone

from nexusLIMS.utils import nexus_req, _get_timespan_overlap
from nexusLIMS.harvesters import ReservationEvent
from nexusLIMS.db.session_handler import SessionLog, Session, db_query
from nexusLIMS.instruments import get_instr_from_api_url
from nexusLIMS.instruments import instrument_db

_logger = logging.getLogger(__name__)


class NoDataConsentException(Exception):
    """
    Exception to raise if a user has not given their consent to have data
    harvested
    """
    pass


class NoMatchingReservationException(Exception):
    """
    Exception to raise if there was no matching reservation (so we cannot assume
    to have consent to harvest their data)
    """
    pass


class NemoConnector:
    """
    A connection to an instance of the API of the NEMO laboratory management
    software. Provides helper methods for fetching data from the API.

    Parameters
    ----------
    base_url : str
        The "root" of the API including a trailing slash;
        e.g. 'https://nemo.url.com/api/'
    token : str
        An authentication token for this NEMO instance
    strftime_fmt : str
        The "date format" to use when encoding dates to send as filters to the
        NEMO API. Should follow the same convention as
        :ref:`strftime-strptime-behavior`. If ``None``, ISO 8601 format
        will be used.
    strptime_fmt : str
        The "date format" to use when decoding date strings received in the
        response from the API. Should follow the same convention as
        :ref:`strftime-strptime-behavior`. If ``None``, ISO 8601 format
        will be used.
    timezone : str
        The timezone to use when decoding date strings received in the
        response from the API. Should be a IANA time zone database string; e.g.
        "America/New_York". Useful if no timezone information is returned
        from an instance of the NEMO API. If ``None``, no timezone setting will
        be done and the code will use whatever was returned from the server
        as is.
    """
    tools: Dict[int, Dict]
    users: Dict[int, Dict]
    users_by_username: Dict[str, Dict]
    projects: Dict[int, Dict]
    
    def __init__(self, base_url: str, token: str,
                 strftime_fmt: Optional[str] = None,
                 strptime_fmt: Optional[str] = None,
                 timezone: Optional[str] = None):
        self.base_url = base_url
        self.token = token
        self.strftime_fmt = strftime_fmt
        self.strptime_fmt = strptime_fmt
        self.timezone = timezone

        # these attributes are used for "memoization" of NEMO content,
        # so it can be remembered and used for a cache lookup
        # keys should be NEMO internal IDs and values should be the
        # dictionary returned by the API
        self.tools = {}
        self.users = {}
        self.users_by_username = {}
        self.projects = {}

    def __repr__(self):
        return f"Connection to NEMO API at {self.base_url}"

    def strftime(self, date_dt) -> str:
        """
        Using the settings for this NemoConnector, convert a datetime object
        to a string that will be understood by the API. If the ``strftime_fmt``
        attribute for this NemoConnector is ``None``, ISO 8601 format will be
        used.

        Parameters
        ----------
        date_dt
            The date to be converted as a datetime object

        Returns
        -------
        date_str : str
            The date formatted as a string that will be understandable by the
            API for this NemoConnector
        """
        if self.strftime_fmt is None:
            return date_dt.isoformat()
        else:
            if '%z' in self.strftime_fmt or '%Z' in self.strftime_fmt:
                # make sure datetime is timezone aware if timezone is
                # indicated in strftime_fmt. Use NEMO_tz setting if present,
                # otherwise use local server timezone
                if date_dt.tzinfo is None:
                    if self.timezone:
                        date_dt = pytz_timezone(self.timezone).localize(date_dt)
                    else:
                        date_dt = date_dt.astimezone()
            return date_dt.strftime(self.strftime_fmt)

    def strptime(self, date_str) -> datetime:
        """
        Using the settings for this NemoConnector, convert a datetime string
        representation from the API into a datetime object that can be used
        in Python. If the ``strptime_fmt`` attribute for this NemoConnector
        is ``None``, ISO 8601 format will be assumed. If a timezone is
        specified for this server, the resulting datetime will be coerced to
        that timezone.

        Parameters
        ----------
        date_str
            The date formatted as a string that is returned by the
            API for this NemoConnector

        Returns
        -------
        date_dt : ~datetime.datetime
            The date to be converted as a datetime object
        """
        if self.strptime_fmt is None:
            date_dt = datetime.fromisoformat(date_str)
        else:
            # to be defensive here, try without microseconds as well if ".%f"
            # is in strptime_fmt and it fails (since sometimes NEMO doesn't
            # write microseconds for every time, even if it's supposed to
            try:
                date_dt = datetime.strptime(date_str, self.strptime_fmt)
            except ValueError as e:
                if '.%f' in self.strptime_fmt:
                    date_dt = datetime.strptime(date_str,
                                                self.strptime_fmt.replace(
                                                    '.%f', ''))
                else:
                    raise e   # pragma: no cover

        if self.timezone:
            # strip any timezone information from the datetime, then localize
            # with pytz to whatever timezone specified
            date_dt = date_dt.replace(tzinfo=None)
            date_dt = pytz_timezone(self.timezone).localize(date_dt)

        return date_dt

    def get_tools(self, tool_id: Union[int, List[int]]) -> List[Dict]:
        """
        Get a list of one or more tools from the NEMO API in a dictionary
        representation

        Parameters
        ----------
        tool_id
            The tool(s) to fetch, as indexed by the NEMO instance (i.e.
            ``tool_id`` should be the internal primary key used by NEMO to
            identify the tool. If an empty list is given, all tools will be
            returned.

        Returns
        -------
        tools : List[Dict]
            A list (could be empty) of tools that match the id (or ids) given
            in ``tool_id``

        Raises
        ------
        requests.exceptions.HTTPError
            Raised if the request to the API did not go through correctly
        """
        if hasattr(tool_id, '__iter__'):
            if all(t_id in self.tools for t_id in tool_id):
                _logger.debug(f"Using cached tool info for tools {tool_id}"
                              f": {[self.tools[t]['name'] for t in tool_id]}")
                return [self.tools[t_id] for t_id in tool_id]
            p = {"id__in": ','.join([str(i) for i in tool_id])}
        else:
            if tool_id in self.tools:
                _logger.debug(f"Using cached tool info for tool {tool_id}:"
                              f" \"{self.tools[tool_id]['name']}\"")
                return [self.tools[tool_id]]
            p = {"id": tool_id}

        tools = self._api_caller('GET', 'tools/', p)

        for t in tools:
            # cache the tool results
            self.tools[t["id"]] = t

        return tools

    def get_users(self, user_id: Union[int, List[int], None] = None) -> \
            List[Dict]:
        """
        Get a list of one or more users from the NEMO API in a dictionary
        representation. The results will be cached in the NemoConnector
        instance to prevent multiple API queries if not necessary

        Parameters
        ----------
        user_id
            The user(s) to fetch, as indexed by the NEMO instance (i.e.
            ``user_id`` should be the internal primary key used by NEMO to
            identify the user. If an empty list or None is given, all users
            will be returned.

        Returns
        -------
        users : List[Dict]
            A list (could be empty) of users that match the ids and/or
            usernames given

        Raises
        ------
        requests.exceptions.HTTPError
            Raised if the request to the API did not go through correctly
        """
        p = {}

        # list of user ids
        if hasattr(user_id, '__iter__'):
            p["id__in"] = ','.join([str(i) for i in user_id])
            if all(u_id in self.users for u_id in user_id):
                _logger.debug(f"Using cached user info for users with id in"
                              f" {user_id}: "
                              f"{[self.users[u]['username'] for u in user_id]}")
                return [self.users[u_id] for u_id in user_id]
        # single user id
        else:
            p["id"] = user_id
            if user_id in self.users:
                _logger.debug(f"Using cached user info for user id {user_id}: "
                              f"\"{self.users[user_id]['username']}\"")
                return [self.users[user_id]]

        return self._get_users_helper(p)

    def get_users_by_username(self, username=None) -> List:
        """
        Get a list of one or more users from the NEMO API in a dictionary
        representation. The results will be cached in the NemoConnector
        instance to prevent multiple API queries if not necessary

        Parameters
        ----------
        username : str or :obj:`list` of :obj:`str`
            The user(s) to fetch, as indexed by their usernames in the NEMO
            instance. If an empty list or None is given, all users
            will be returned.

        Returns
        -------
        users : list
            A list (could be empty) of users that match the ids and/or
            usernames given

        Raises
        ------
        requests.exceptions.HTTPError
            Raised if the request to the API did not go through correctly
        """
        p = {}
        if isinstance(username, (str,)):
            p["username"] = username
            if username in self.users_by_username:
                _logger.debug(f"Using cached user info for username "
                              f"\"{username}\"")
                return [self.users_by_username[username]]
        else:
            p["username__in"] = ','.join(username)
            if all(uname in self.users_by_username for uname in username):
                _logger.debug(f"Using cached user info for users with id in"
                              f" {username}")
                return [self.users_by_username[uname] for uname in username]

        return self._get_users_helper(p)

    def get_projects(self, proj_id: Union[int, List[int]]) -> List[Dict]:
        """
        Get a list of one or more projects from the NEMO API in a dictionary
        representation. The local cache will be checked prior to fetching
        from the API to save a network request if possible.

        Parameters
        ----------
        proj_id
            The project(s) to fetch, as indexed by the NEMO instance (i.e.
            ``proj_id`` should be the internal primary key used by NEMO to
            identify the project. If an empty list is given, all projects
            will be returned.

        Returns
        -------
        projects : List[Dict]
            A list (could be empty) of projects that match the id (or ids) given
            in ``proj_id``

        Raises
        ------
        requests.exceptions.HTTPError
            Raised if the request to the API did not go through correctly
        """
        if hasattr(proj_id, '__iter__'):
            if all(p_id in self.projects for p_id in proj_id):
                _logger.debug(f"Using cached project info for projects"
                              f" {proj_id}: "
                              f"{[self.projects[p]['name'] for p in proj_id]}")
                return [self.projects[p_id] for p_id in proj_id]
            p = {"id__in": ','.join([str(i) for i in proj_id])}
        else:
            if proj_id in self.projects:
                _logger.debug(f"Using cached project info for project"
                              f" {proj_id}: \""
                              f"{self.projects[proj_id]['name']}\"")
                return [self.projects[proj_id]]
            p = {"id": proj_id}

        projects = self._api_caller('GET', 'projects/', p)

        for p in projects:
            # expand the only_allow_tools node
            if 'only_allow_tools' in p:
                p.update({'only_allow_tools':
                          [self.get_tools(t)[0] for t in p[
                              'only_allow_tools']]})
            self.projects[p["id"]] = p

        return projects

    def get_reservations(self,
                         dt_from: datetime = None,
                         dt_to: datetime = None,
                         tool_id: Union[int, List[int]] = None,
                         cancelled: Union[None, bool] = False) -> List[Dict]:
        """
        Return a list of reservations from the API, filtered by date
        (inclusive). If only one argument is provided, the API will return all
        reservations either before or after the parameter. With no arguments,
        the method will return all reservations. The method will
        "auto-expand" linked information such as user, project, tool, etc. so
        results will have a full dictionary for each of those fields, rather
        than just the index (as returned from the API).

        Parameters
        ----------
        dt_from
            The "starting point" of the time range; only reservations at or
            after this point in time will be returned
        dt_to
            The "ending point" of the time range; only reservations at
            or prior to this point in time will be returned
        tool_id
            A tool identifier (or list of them) to limit the scope of the
            reservation search (this should be the NEMO internal integer ID)
        cancelled
            Whether to get canceled or active reservations in the response
            (default is False -- meaning non-cancelled active reservations
            are returned by default). Set to None to include all reservations
            regardless of whether they are cancelled or active.

        Returns
        -------
        reservations : List[Dict]
            A list (could be empty) of reservations that match the date range
            supplied
        """
        p = {}

        if dt_from:
            p['start__gte'] = self.strftime(dt_from)
        if dt_to:
            p['end__lte'] = self.strftime(dt_to)
        if cancelled is not None:
            p['cancelled'] = cancelled

        if tool_id is not None:
            if isinstance(tool_id, list):
                p.update({"tool_id__in": ','.join([str(i) for i in tool_id])})
            else:
                p.update({"tool_id": str(tool_id)})

        reservations = self._api_caller('GET', 'reservations/', p)

        for r in reservations:
            # expand various fields within the reservation data
            if r['user']:
                u = self.get_users(r['user'])
                if u:
                    r.update({'user': u[0]})
            if r['creator']:
                u = self.get_users(r['creator'])
                if u:
                    r.update({'creator': u[0]})
            if r['tool']:
                t = self.get_tools(r['tool'])
                if t:
                    r.update({'tool': t[0]})
            if r['project']:
                p = self.get_projects(r['project'])
                if p:
                    r.update({'project': p[0]})
            if r['cancelled_by']:
                u = self.get_users(r['cancelled_by'])
                if u:
                    r.update({'cancelled_by': u[0]})

        return reservations

    def get_usage_events(self,
                         event_id: Union[int, List[int]] = None,
                         user: Union[str, int] = None,
                         dt_from: datetime = None,
                         dt_to: datetime = None,
                         tool_id: Union[int, List[int], None] = None) -> List:
        """
        Return a list of usage events from the API, filtered by date
        (inclusive). If only one argument is provided, the API will return all
        reservations either before or after the parameter. With no arguments,
        the method will return all reservations. The method will
        "auto-expand" linked information such as user, project, tool, etc. so
        results will have a full dictionary for each of those fields, rather
        than just the index (as returned from the API).

        Parameters
        ----------
        event_id
            The NEMO integer identifier (or a list of them) to fetch. If
            ``None``, the returned usage events will not be filtered by ID
            number
        user
            The user for which to fetch usage events, as either an integer
            representing their id in the NEMO instance, or as a string
            containing their username.  If ``None`` is given, usage events
            from all users will be returned.
        dt_from
            The "starting point" of the time range; only usage events
            starting at or after this point in time will be returned
        dt_to
            The "ending point" of the time range; only usage events ending at
            or prior to this point in time will be returned
        tool_id
            A tool identifier (or list of them) to limit the scope of the
            usage event search (this should be the NEMO internal integer ID).
            Regardless of what value is given, this method will always limit
            the API query to tools specified in the NexusLIMS DB for this 
            harvester 

        Returns
        -------
        usage_events : List
            A list (could be empty) of usage events that match the filters
            supplied
        """
        p = {}
        if event_id is not None:
            if hasattr(event_id, '__iter__'):
                p.update({"id__in": ','.join([str(i) for i in event_id])})
            else:
                p.update({"id": event_id})
        if user:
            if isinstance(user, str):
                u_id = self.get_users_by_username(user)[0]['id']
            else:
                u_id = user
            p['user_id'] = u_id
        if dt_from:
            p['start__gte'] = self.strftime(dt_from)
        if dt_to:
            p['end__lte'] = self.strftime(dt_to)

        # filtering for tool; if at the end of this block tool_id is an empty
        # list, we should just immediately return an empty list, since either
        # there were no tools for this connector in our DB, or the tools 
        # specified were not found in the DB, so we know there are no 
        # usage_events of interest
        this_connectors_tools = self.get_known_tool_ids()
        if tool_id is None:
            # by default (no tool_id specified), we should fetch events from
            # only the tools known to the NexusLIMS DB for this connector 
            tool_id = this_connectors_tools
        if isinstance(tool_id, int):
            # coerce tool_id to list to make subsequent processing easier
            tool_id = [tool_id]
        
        # limit tool_id to values that are present in this_connectors_tools 
        tool_id = [i for i in tool_id if i in this_connectors_tools]

        # if tool_id is empty, we should just return
        if not tool_id:
            return []
        else:
            p.update({"tool_id__in": ','.join([str(i) for i in tool_id])})
            
        usage_events = self._api_caller('GET', 'usage_events/', p)

        for event in usage_events:
            # expand various fields within the usage event data
            if event['user']:
                user = self.get_users(event['user'])
                if user:
                    event.update({'user': user[0]})
            if event['operator']:
                user = self.get_users(event['operator'])
                if user:
                    event.update({'operator': user[0]})
            if event['project']:
                proj = self.get_projects(event['project'])
                if proj:
                    event.update({'project': proj[0]})
            if event['tool']:
                tool = self.get_tools(event['tool'])
                if tool:
                    event.update({'tool': tool[0]})

        return usage_events

    def write_usage_event_to_session_log(self,
                                         event_id: int) -> None:
        """
        Inserts two rows (if needed) into the ``session_log`` (marking the start
        and end of a usage event), only for instruments recognized by
        NexusLIMS (i.e. that have a row in the ``instruments`` table of the DB).
        If the usage event has not ended yet, no action is performed

        Parameters
        ----------
        event_id
            The NEMO id number for the event to insert

        """
        event = self.get_usage_events(event_id=event_id)
        if event:
            # get_usage_events returns list, so pick out first one
            event = event[0]
            tool_api_url = f"{self.base_url}tools/?id={event['tool']['id']}"
            instr = get_instr_from_api_url(tool_api_url)
            if instr is None:  # pragma: no cover
                # this shouldn't happen since we limit our usage event API call
                # only to instruments contained in our DB, but we can still
                # defend against it regardless
                _logger.warning(f"Usage event {event_id} was for an instrument "
                                f"({tool_api_url}) not known "
                                f"to NexusLIMS, so no records will be added "
                                f"to DB.")
                return
            if event['end'] is None:
                _logger.warning(f"Usage event {event_id} has not yet ended, "
                                f"so no records will be added to DB.")
                return
            session_id = f"{self.base_url}usage_events/?id={event['id']}"

            # try to insert start log
            res = db_query("SELECT * FROM session_log WHERE session_identifier "
                           "= ? AND event_type = ?", (session_id, 'START'))
            if len(res[1]) > 0:
                # there was already a start log, so warn and don't do anything:
                _logger.warning(f"A  'START' log with session id "
                                f"\"{session_id}\" was found in the the DB, "
                                f"so a new one will not be inserted for this "
                                f"event")
            else:
                start_log = SessionLog(
                    session_identifier=session_id,
                    instrument=instr.name,
                    # make sure to coerce format to ISO before putting in DB
                    timestamp=self.strptime(event['start']).isoformat(),
                    event_type='START',
                    user=event['user']['username'],
                    record_status='TO_BE_BUILT'
                )
                start_inserted = start_log.insert_log()

            # try to insert end log
            res = db_query("SELECT * FROM session_log WHERE session_identifier "
                           "= ? AND event_type = ?", (session_id, 'END'))
            if len(res[1]) > 0:
                # there was already an end log, so warn and don't do anything:
                _logger.warning(f"An 'END'   log with session id "
                                f"\"{session_id}\" was found in the the DB, "
                                f"so a new one will not be inserted for this "
                                f"event")
            else:
                end_log = SessionLog(
                    session_identifier=session_id,
                    instrument=instr.name,
                    # make sure to coerce format to ISO before putting in DB
                    timestamp=self.strptime(event['end']).isoformat(),
                    event_type='END',
                    user=event['user']['username'],
                    record_status='TO_BE_BUILT'
                )
                end_inserted = end_log.insert_log()
        else:
            _logger.warning(f"No usage event with id = {event_id} was found "
                            f"for {self}")

    def get_session_from_usage_event(self, event_id: int) -> Union[Session,
                                                                   None]:
        """
        Get a :py:class:`~nexusLIMS.db.session_handler.Session`
        representation of a usage event for use in dry runs of the record
        builder

        Parameters
        ----------
        event_id
            The NEMO id number for the event to insert

        Returns
        -------
        session : ~nexusLIMS.db.session_handler.Session
            A representation of the usage_event from NEMO as a
            :py:class:`~nexusLIMS.db.session_handler.Session` object
        """
        event = self.get_usage_events(event_id=event_id)
        if event:
            event = event[0]
            # we cannot reliably test an unended event, so exlcude from coverage
            if event['start'] is not None and event['end'] is None: # pragma: no cover
                _logger.warning(
                    f"Usage event with id = {event_id} has not yet ended "
                    f"for '{self}'")
                return None
            instr = get_instr_from_api_url(f"{self.base_url}tools/?id="
                                           f"{event['tool']['id']}")
            session_id = f"{self.base_url}usage_events/?id={event_id}"
            session = Session(
                session_identifier=session_id,
                instrument=instr,
                dt_from=self.strptime(event['start']),
                dt_to=self.strptime(event['end']),
                user=event['user']['username']
            )
            return session
        else:
            _logger.warning(f"No usage event with id = {event_id} was found "
                            f"for '{self}'")
            return None

    def get_known_tool_ids(self) -> List[int]:
        """
        Inspect the ``api_url`` values of known Instruments (from 
        the ``instruments`` table in the DB), and extract their tool_id number
        if it is from this NemoConnector

        Returns
        -------
        tool_ids : List[int]
            The list of tool ID numbers known to NexusLIMS for this harvester
        """
        tool_ids = []

        for k, v in instrument_db.items():
            if self.base_url in v.api_url:
                # Instrument is associated with this connector
                parsed_url = urlparse(v.api_url)
                # extract 'id' query parameter from url
                tool_id = parse_qs(parsed_url.query)['id'][0]
                tool_ids.append(int(tool_id))

        return tool_ids

    def _get_users_helper(self, p: Dict[str, str]) -> list:
        """
        Takes care of calling the users API with certain parameters

        Parameters
        ----------
        p
            A dictionary of query parameters for the API query

        Returns
        -------
        users
            A list (could be empty) of users that match the ids and/or
            usernames given
        """
        users = self._api_caller('GET', 'users/', p)
        for u in users:
            # cache the users response by ID and username
            self.users[u["id"]] = u
            self.users_by_username[u["username"]] = u

        return users

    def _api_caller(self,
                    fn: str,
                    endpoint: str,
                    p: Dict[str, str]) -> List[Dict[str, Any]]:
        """
        Helper function to deduplicate actual calls to the API. Takes care of
        building the full URL from the base URL and specific endpoint,
        as well as authentication, passing of parameters, and parsing the
        results.

        Parameters
        ----------
        fn
            The ``requests`` function (``'POST'``, ``'GET'``, 
            ``'PATCH'``, etc.) to use for the API request
        endpoint
            The API endpoint to use. Should be formatted with a trailing
            slash and no leading slash. i.e. the endpoint for Projects data
            should be supplied as ``'projects/'``
        p
            The URL parameters to pass along with the request. These are
            generally filters for the API data such as ``id`` or a date range
            or something similar.

        Returns
        -------
        results
            The API response, formatted as a list of dict objects
        """
        url = urljoin(self.base_url, endpoint)
        _logger.info(f"getting data from {url} with parameters {p}")
        r = nexus_req(url, fn,
                      token_auth=self.token, params=p)
        r.raise_for_status()
        results = r.json()
        return results


# return enabled NEMO harvesters based on environment
def get_harvesters_enabled() -> List[NemoConnector]:
    """
    Check the environment for NEMO settings and return a list of connectors
    based off the values found

    Returns
    -------
    harvesters_enabled : List[NemoConnector]
        A list of NemoConnector objects representing the NEMO APIs enabled
        via environment settings
    """
    harvesters_enabled_str: List[str] = \
        list(filter(lambda x: re.search('NEMO_address', x), os.environ.keys()))
    harvesters_enabled = [
        NemoConnector(base_url=os.getenv(addr),
                      token=os.getenv(addr.replace('address', 'token')),
                      strftime_fmt=os.getenv(addr.replace('address',
                                                          'strftime_fmt')),
                      strptime_fmt=os.getenv(addr.replace('address',
                                                          'strptime_fmt')),
                      timezone=os.getenv(addr.replace('address', 'tz')))
        for addr in harvesters_enabled_str]
    return harvesters_enabled


def add_all_usage_events_to_db(user: Union[str, int] = None,
                               dt_from: datetime = None,
                               dt_to: datetime = None,
                               tool_id: Union[int, List[int], None] = None):
    """
    Loop through enabled NEMO connectors and add each one's usage events to
    the NexusLIMS ``session_log`` database table (if required).

    Parameters
    ----------
    user
        The user(s) for which to add usage events. If ``None``, events will
        not be filtered by user at all
    dt_from
        The point in time after which usage events will be added. If ``None``,
        no date filtering will be performed
    dt_to
        The point in time before which usage events will be added. If
        ``None``, no date filtering will be performed
    tool_id
        The tools(s) for which to add usage events. If ``'None'`` (default), 
        the tool IDs for each instrument in the NexusLIMS DB will be extracted 
        and used to limit the API response
    """
    for n in get_harvesters_enabled():
        events = n.get_usage_events(user=user, dt_from=dt_from,
                                    dt_to=dt_to, tool_id=tool_id)
        for e in events:
            n.write_usage_event_to_session_log(e['id'])


def get_usage_events_as_sessions(user: Union[str, int] = None,
                                 dt_from: datetime = None,
                                 dt_to: datetime = None,
                                 tool_id: Union[int, List[int], None] = None) \
        -> List[Session]:
    """
    Loop through enabled NEMO connectors and return each one's usage events to
    as :py:class:`~nexusLIMS.db.session_handler.Session` objects without
    writing logs to the ``session_log`` table. Mostly used for doing dry runs
    of the record builder.

    Parameters
    ----------
    user
        The user(s) for which to fetch usage events. If ``None``, events will
        not be filtered by user at all
    dt_from
        The point in time after which usage events will be fetched. If ``None``,
        no date filtering will be performed
    dt_to
        The point in time before which usage events will be fetched. If
        ``None``, no date filtering will be performed
    tool_id
        The tools(s) for which to fetch usage events. If ``None``, events will
        only be filtered by tools known in the NexusLIMS DB for each connector 
    """
    sessions = []
    for n in get_harvesters_enabled():
        events = n.get_usage_events(user=user, dt_from=dt_from,
                                    dt_to=dt_to, tool_id=tool_id)
        for e in events:
            this_session = n.get_session_from_usage_event(e['id'])
            # this_session could be None, and if the instrument from the
            # usage event is not in our DB, this_session.instrument could
            # also be None. In each case, we should ignore that one
            if this_session is not None and this_session.instrument is not None:
                sessions.append(this_session)

    return sessions


def get_connector_for_session(session: Session) -> NemoConnector:
    """
    Given a :py:class:`~nexusLIMS.db.session_handler.Session`, find the matching
    :py:class:`~nexusLIMS.harvesters.nemo.NemoConnector` from the enabled
    list of NEMO harvesters

    Parameters
    ----------
    session
        The session for which a NemoConnector is needed

    Returns
    -------
    n : ~nexusLIMS.harvesters.nemo.NemoConnector
        The connector object that allows for querying the NEMO API for the
        instrument contained in ``session``

    Raises
    ------
    LookupError
        Raised if a matching connector is not found
    """
    instr_base_url = urljoin(session.instrument.api_url, '.')

    for n in get_harvesters_enabled():
        if n.base_url in instr_base_url:
            return n

    raise LookupError(f'Did not find enabled NEMO harvester for '
                      f'"{session.instrument.name}". Perhaps check environment '
                      f'variables? The following harvesters are enabled: '
                      f'{get_harvesters_enabled()}')


def get_connector_by_base_url(base_url: str) -> NemoConnector:
    """
    Get an enabled NemoConnector by inspecting the ``base_url``.

    Parameters
    ----------
    base_url
        A portion of the API url to search for

    Returns
    -------
    n : ~nexusLIMS.harvesters.nemo.NemoConnector
        The enabled NemoConnector instance

    Raises
    ------
    LookupError
        Raised if a matching connector is not found
    """
    for n in get_harvesters_enabled():
        if base_url in n.base_url:
            return n

    raise LookupError(f'Did not find enabled NEMO harvester with url '
                      f'containing "{base_url}". Perhaps check environment '
                      f'variables? The following harvesters are enabled: '
                      f'{get_harvesters_enabled()}')


def res_event_from_session(session: Session) -> ReservationEvent:
    """
    Create an internal :py:class:`~nexusLIMS.harvesters.ReservationEvent`
    representation of a session by finding a matching reservation in the NEMO
    system and parsing the data contained within into a ``ReservationEvent``

    This method assumes a certain format for the "reservation questions"
    associated with each reservation and parses that information into the resulting
    ``ReservationEvent``. The most critical of these is the ``data_consent`` field.
    If an affirmative response in this field is not found (because the user declined
    consent or the reservation questions are missing), a record will not be built.

    The following JSON object represents a minimal schema for a set of NEMO "Reservation
    Questions" that will satisfy the expectations of this method. Please see the
    NEMO documentation on this feature for more details.

    .. highlight:: json
    .. code-block:: json

        [
          {
            "type": "textbox",
            "name": "project_id",
            "title": "Project ID",
          },
          {
            "type": "textbox",
            "name": "experiment_title",
            "title": "Title of Experiment",
          },
          {
            "type": "textarea",
            "name": "experiment_purpose",
            "title": "Experiment Purpose",
          },
          {
            "type": "radio",
            "title": "Agree to NexusLIMS curation",
            "choices": ["Agree", "Disagree"],
            "name": "data_consent",
            "default_choice": "Agree"
          },
          {
            "type": "group",
            "title": "Sample information",
            "name": "sample_group",
            "questions": [
              {
                "type": "textbox",
                "name": "sample_name",
                "title": "Sample Name / PID",
              },
              {
                "type": "radio",
                "title": "Sample or PID?",
                "choices": ["Sample Name", "PID"],
                "name": "sample_or_pid",
              },
              {
                "type": "textarea",
                "name": "sample_details",
                "title": "Sample Details",
              }
            ]
          }
        ]

    Parameters
    ----------
    session
        The session for which to get a reservation event

    Returns
    -------
    res_event : ~nexusLIMS.harvesters.ReservationEvent
        The matching reservation event
    """
    # a session has instrument, dt_from, dt_to, and user

    # we should fetch all reservations +/- two days, and then find the one
    # with the maximal overlap with the session time range
    # probably don't want to filter by user for now, since sometimes users
    # will enable/reserve on behalf of others, etc.

    # in order to get reservations, we need a NemoConnector
    c = get_connector_for_session(session)

    # tool id can be extracted from instrument api_url query parameter
    tool_id = id_from_url(session.instrument.api_url)

    # get reservation with maximum overlap (like sharepoint_calendar.fetch_xml)
    dt_f = session.dt_from - timedelta(days=2)
    dt_t = session.dt_to + timedelta(days=2)
    reservations = c.get_reservations(
        tool_id=tool_id,
        dt_from=dt_f,
        dt_to=dt_t
    )

    _logger.info(f"Found {len(reservations)} reservations between {dt_f} and "
                 f"{dt_t} with ids: "
                 f"{[i['id'] for i in reservations]}")
    for i, res in enumerate(reservations):
        _logger.debug(f"Reservation {i+1}: {c.base_url}reservations/?id"
                      f"={res['id']} from {res['start']} to {res['end']}")

    starts = [c.strptime(r['start']) for r in reservations]
    ends = [c.strptime(r['end']) for r in reservations]

    overlaps = [_get_timespan_overlap((session.dt_from, session.dt_to),
                                      (s, e)) for s, e in zip(starts, ends)]

    # DONE:
    #   need to handle if there are no matching sessions (i.e. reservations is
    #   an empty list
    #   also need to handle if there is no overlap at all with any reservation
    if len(reservations) == 0 or max(overlaps) == timedelta(0):
        # there were no reservations that matched this usage event time range,
        # or none of the reservations overlapped with the usage event
        # so we'll use what limited information we have from the usage event
        # session
        _logger.warning(f"No reservations found with overlap for this usage "
                        f"event, so raising NoDataConsentException")
        raise NoMatchingReservationException(
            "No reservation found matching this session, so assuming NexusLIMS "
            "does not have user consent for data harvesting.")
    else:
        max_overlap = overlaps.index(max(overlaps))
        # select the reservation with the most overlap
        res = reservations[max_overlap]
        _logger.info(f"Using reservation "
                     f"{c.base_url}reservations/?id={res['id']} as match for "
                     f"usage event {session.session_identifier} with overlap "
                     f"of {max(overlaps)}")

        # DONE: check for presence of sample_group in the reservation metadata
        #  and change the harvester to process the sample group metadata by
        #  providing lists to the ReservationEvent constructor
        sample_details, sample_pid, sample_name, sample_elements = \
            _process_res_question_samples(res)

        # DONE: respect user choice not to harvest data (data_consent)
        consent = 'disagree'
        consent = _get_res_question_value('data_consent', res)
        # consent will be None here if it wasn't given (i.e. there was no
        # data_consent field in the reservation questions)
        if consent is None:
            raise NoDataConsentException(f"Reservation {res['id']} "
                                         f"did not have data_consent defined, "
                                         f"so we should not harvest its data")

        if consent.lower() in ['disagree', 'no', 'false', 'negative']:
            raise NoDataConsentException(f"Reservation {res['id']} "
                                         f"requested not to have their "
                                         f"data harvested")

        url = c.base_url.replace('api/',
                                 f'event_details/reservation/{res["id"]}/')

        # Create ReservationEvent from NEMO reservation dict
        res_event = ReservationEvent(
            experiment_title=_get_res_question_value('experiment_title', res),
            instrument=session.instrument,
            last_updated=c.strptime(res['creation_time']),
            username=res['user']['username'],
            user_full_name=f"{res['user']['first_name']} "
                           f"{res['user']['last_name']} "
                           f"({res['user']['username']})",
            created_by=res['creator']['username'],
            created_by_full_name=f"{res['creator']['first_name']} "
                                 f"{res['creator']['last_name']} "
                                 f"({res['creator']['username']})",
            start_time=c.strptime(res['start']),
            end_time=c.strptime(res['end']),
            reservation_type=None, # reservation type is not collected in NEMO
            experiment_purpose=_get_res_question_value('experiment_purpose',
                                                       res),
            sample_details=sample_details, sample_pid=sample_pid,
            sample_name=sample_name, sample_elements=sample_elements,
            project_name=[None],
            project_id=[_get_res_question_value('project_id', res)],
            project_ref=[None],
            internal_id=str(res['id']),
            division=None,
            group=None,
            url=url
        )
    return res_event


def _process_res_question_samples(res_dict: Dict) -> \
    Tuple[Union[List[Union[str, None]], None],
          Union[List[Union[str, None]], None],
          Union[List[Union[str, None]], None],
          Union[List[Union[str, None]], None]]:
    sample_details, sample_pid, sample_name, periodic_tables = [], [], [], []
    sample_group = _get_res_question_value('sample_group', res_dict)
    if sample_group is not None:
        # multiple samples form will have
        # res_dict['question_data']['sample_group']['user_input'] of form:
        #
        # {
        #   "0": {
        #     "sample_name": "sample_pid_1",
        #     "sample_or_pid": "PID",
        #     "sample_details": "A sample with a PID and some more details"
        #   },
        #   "1": {
        #     "sample_name": "sample name 1",
        #     "sample_or_pid": "Sample Name",
        #     "sample_details": "A sample with name and some additional detail",
        #     "periodic_table": ["H", "Ti", "Cu", "Sb", "Re"]
        #   },
        #   ...
        # }
        # each key "0", "1", "2", etc. represents a single sample the user
        # added via the "Add" button. There should always be at least one,
        # since sample information is required
        # the "periodic_table" key is optional, and won't be present if the user did not select anything in that
        # section of the questions
        for k, v in sample_group.items():
            if v['sample_or_pid'].lower() == "pid":
                sample_pid.append(v['sample_name'])
                sample_name.append(None)
            elif v['sample_or_pid'].lower() == 'sample name':
                sample_name.append(v['sample_name'])
                sample_pid.append(None)
            else:
                sample_name.append(None)
                sample_pid.append(None)
            # as of NEMO 4.3.2, an empty textarea returns None rather than "",
            # so check for None first, then test string length
            if v['sample_details'] is not None and len(v['sample_details']) > 0:
                sample_details.append(v['sample_details'])
            else:
                sample_details.append(None)
            if 'periodic_table' in v:
                periodic_tables.append(v['periodic_table'])
            else:
                periodic_tables.append(None)
    else:  # pragma: no cover
        # non-multiple samples (old-style form) (this is deprecated,
        # so doesn't need coverage since we don't have reservations in this
        # style any longer)
        sample_details = [_get_res_question_value('sample_details', res_dict)]
        sample_pid = [None]
        sample_name = [_get_res_question_value('sample_name', res_dict)]
    return sample_details, sample_pid, sample_name, periodic_tables


def _get_res_question_value(value: str, res_dict: Dict) -> Union[str, Dict,
                                                                 None]:
    if 'question_data' in res_dict and res_dict['question_data'] is not None:
        if value in res_dict['question_data']:
            return res_dict['question_data'][value].get('user_input', None)
        else:
            return None
    else:
        return None


def id_from_url(url: str) -> Union[None, int]:
    """
    Get the value of the id query parameter stored in URL string. This is
    used to extract the value as needed from API strings

    Parameters
    ----------
    url
        The URL to parse, such as
        ``https://nemo.url.com/api/usage_events/?id=9``

    Returns
    -------
    this_id : None or int
        The id value if one is present, otherwise ``None``
    """
    query = parse_qs(urlparse(url).query)
    if 'id' in query:
        this_id = int(query['id'][0])
        return this_id
    else:
        return None
