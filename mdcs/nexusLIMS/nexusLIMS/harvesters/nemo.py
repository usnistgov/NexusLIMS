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
from uuid import uuid4

from nexusLIMS.utils import nexus_req, _get_timespan_overlap
from nexusLIMS.harvesters import ReservationEvent
from nexusLIMS.db.session_handler import SessionLog, Session, db_query
from nexusLIMS.instruments import get_instr_from_api_url

_logger = logging.getLogger(__name__)


class NoDataConsentException(Exception):
    """
    Exception to raise if a user has not given their consent to have data
    harvested
    """
    pass


class NemoConnector:
    tools: Dict[int, Dict]
    users: Dict[int, Dict]
    users_by_username: Dict[str, Dict]
    projects: Dict[int, Dict]
    
    def __init__(self, base_url: str, token: str):
        self.base_url = base_url
        self.token = token

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

    def get_tools(self, tool_id: Union[int, List[int]]) -> list:
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
        tools : list
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

        tools = self._api_caller(requests.get, 'tools/', p)

        for t in tools:
            # cache the tool results
            self.tools[t["id"]] = t

        return tools

    def get_users(self, user_id: Union[int, List[int], None] = None) -> list:
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
        users : list
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

    def get_projects(self, proj_id: Union[int, List[int]]) -> list:
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
        projects : list
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

        projects = self._api_caller(requests.get, 'projects/', p)

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
            p['start__gte'] = dt_from.isoformat()
        if dt_to:
            p['end__lte'] = dt_to.isoformat()
        if cancelled is not None:
            p['cancelled'] = cancelled

        if tool_id is not None:
            if isinstance(tool_id, list):
                p.update({"tool_id__in": ','.join([str(i) for i in tool_id])})
            else:
                p.update({"tool_id": str(tool_id)})

        reservations = self._api_caller(requests.get, 'reservations/', p)

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
                         tool_id: Union[int, List[int]] = None) -> List:
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
            usage event search (this should be the NEMO internal integer ID)

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
            p['start__gte'] = dt_from.isoformat()
        if dt_to:
            p['end__lte'] = dt_to.isoformat()
        if tool_id is not None:
            if hasattr(tool_id, '__iter__'):
                p.update({"tool_id__in": ','.join([str(i) for i in tool_id])})
            else:
                p.update({"tool_id": tool_id})

        usage_events = self._api_caller(requests.get, 'usage_events/', p)

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
        NexusLIMS (i.e. that have a row in the ``instruments`` table of the DB)

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
            if instr is None:
                _logger.warning(f"Usage event {event_id} was for an instrument "
                                f"({tool_api_url}) not known "
                                f"to NexusLIMS, so no records will be added "
                                f"to DB.")
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
                    timestamp=event['start'],
                    event_type='START',
                    user=event['user']['username'],
                    record_status='TO_BE_BUILT'
                )
                start_inserted = start_log.insert_log()

            # try to insert end log
            res = db_query("SELECT * FROM session_log WHERE session_identifier "
                           "= ? AND event_type = ?", (session_id, 'END'))
            if len(res[1]) > 0:
                # there was already a start log, so warn and don't do anything:
                _logger.warning(f"An 'END'   log with session id "
                                f"\"{session_id}\" was found in the the DB, "
                                f"so a new one will not be inserted for this "
                                f"event")
            else:
                end_log = SessionLog(
                    session_identifier=session_id,
                    instrument=instr.name,
                    timestamp=event['end'],
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
                dt_from=datetime.fromisoformat(event['start']),
                dt_to=datetime.fromisoformat(event['end']),
                user=event['user']['username']
            )
            return session
        else:
            _logger.warning(f"No usage event with id = {event_id} was found "
                            f"for '{self}'")
            return None

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
        users = self._api_caller(requests.get, 'users/', p)
        for u in users:
            # cache the users response by ID and username
            self.users[u["id"]] = u
            self.users_by_username[u["username"]] = u

        return users

    def _api_caller(self,
                    fn: Callable,
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
            The ``requests`` function (POST, GET, PATCH, etc.) to use for the
            API request
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
    harvesters_enabled : list of ~nexusLIMS.harvesters.nemo.NemoConnector
        A list of NemoConnector objects representing the NEMO APIs enabled
        via environment settings
    """
    harvesters_enabled_str: List[str] = \
        list(filter(lambda x: re.search('NEMO_address', x), os.environ.keys()))
    harvesters_enabled = [NemoConnector(os.getenv(addr),
                                        os.getenv(addr.replace('address',
                                                               'token')))
                          for addr in harvesters_enabled_str]
    return harvesters_enabled


def add_all_usage_events_to_db(user: Union[str, int] = None,
                               dt_from: datetime = None,
                               dt_to: datetime = None,
                               tool_id: Union[int, List[int]] = None):
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
        The tools(s) for which to add usage events. If ``None``, events will
        not be filtered by tool at all
    """
    for n in get_harvesters_enabled():
        events = n.get_usage_events(user=user, dt_from=dt_from,
                                    dt_to=dt_to, tool_id=tool_id)
        for e in events:
            n.write_usage_event_to_session_log(e['id'])


def get_usage_events_as_sessions(user: Union[str, int] = None,
                                 dt_from: datetime = None,
                                 dt_to: datetime = None,
                                 tool_id: Union[int, List[int]] = None) -> \
        List[Session]:
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
        not be filtered by tool at all
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


def get_connector_for_session(session: Session) -> Union[NemoConnector, None]:
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
    """
    instr_base_url = urljoin(session.instrument.api_url, '.')

    for n in get_harvesters_enabled():
        if n.base_url in instr_base_url:
            return n

    raise LookupError(f'Did not find enabled NEMO harvester for '
                      f'"{session.instrument.name}". Perhaps check environment '
                      f'variables? The following harvesters are enabled: '
                      f'{get_harvesters_enabled()}')


def res_event_from_session(session: Session) -> ReservationEvent:
    """
    Create an internal :py:class:`~nexusLIMS.harvesters.ReservationEvent`
    representation of a session by finding a matching reservation in the NEMO
    system and parsing the data contained within into a ``ReservationEvent``

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
    reservations = c.get_reservations(
        tool_id=tool_id,
        dt_from=session.dt_from - timedelta(days=2),
        dt_to=session.dt_to + timedelta(days=2)
    )

    starts = [datetime.fromisoformat(r['start']) for r in reservations]
    ends = [datetime.fromisoformat(r['end']) for r in reservations]

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
        res_event = ReservationEvent(
            experiment_title=None, instrument=session.instrument,
            last_updated=session.dt_to, username=session.user,
            created_by=None, start_time=session.dt_from,
            end_time=session.dt_to, reservation_type=None,
            experiment_purpose=None, sample_details=None,
            sample_pid=None, sample_name=None, project_name=None,
            project_id=None, project_ref=None, internal_id=None,
            division=None, group=None
        )
    else:
        max_overlap = overlaps.index(max(overlaps))
        # select the reservation with the most overlap
        res = reservations[max_overlap]

        # DONE: check for presence of sample_group in the reservation metadata
        #  and change the harvester to process the sample group metadata by
        #  providing lists to the ReservationEvent constructor
        sample_details, sample_pid, sample_name = \
            _process_res_question_samples(res)

        # DONE: respect user choice not to harvest data (data_consent)
        consent = _get_res_question_value('data_consent', res)
        if consent is not None:
            if consent.lower() in ['disagree', 'no', 'false', 'negative']:
                raise NoDataConsentException(f"Reservation {res['id']} "
                                             f"requested not to have their "
                                             f"data harvested")

        # Create ReservationEvent from NEMO reservation dict
        res_event = ReservationEvent(
            experiment_title=_get_res_question_value('experiment_title', res),
            instrument=session.instrument,
            last_updated=datetime.fromisoformat(res['creation_time']),
            username=res['user']['username'],
            user_full_name=f"{res['user']['first_name']} "
                           f"{res['user']['last_name']} "
                           f"({res['user']['username']})",
            created_by=res['creator']['username'],
            created_by_full_name=f"{res['creator']['first_name']} "
                                 f"{res['creator']['last_name']} "
                                 f"({res['creator']['username']})",
            start_time=datetime.fromisoformat(res['start']),
            end_time=datetime.fromisoformat(res['end']),
            reservation_type=None, # reservation type is not collected in NEMO
            experiment_purpose=_get_res_question_value('experiment_purpose',
                                                       res),
            sample_details=sample_details, sample_pid=sample_pid,
            sample_name=sample_name,
            project_name=[None],
            project_id=[_get_res_question_value('project_id', res)],
            project_ref=[None],
            internal_id=str(res['id']),
            division=None,
            group=None
        )
    return res_event

def _process_res_question_samples(res_dict: Dict) -> \
    Tuple[Union[List[Union[str, None]], None],
          Union[List[Union[str, None]], None],
          Union[List[Union[str, None]], None]]:
    sample_details, sample_pid, sample_name = [], [], []
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
        #     "sample_details": "A sample with a name and some additional detail"
        #   },
        #   ...
        # }
        # each key "0", "1", "2", etc. represents a single sample the user
        # added via the "Add" button. There should always be at least one,
        # since sample information is required
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
            if len(v['sample_details']) > 0:
                sample_details.append(v['sample_details'])
            else:
                sample_details.append(None)
    else:
        # non-multiple samples (old-style form)
        sample_details = [_get_res_question_value('sample_details', res_dict)]
        sample_pid = [None]
        sample_name = [_get_res_question_value('sample_name', res_dict)]
    return sample_details, sample_pid, sample_name

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
        ``https://***REMOVED***/api/usage_events/?id=9``

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
