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
from typing import Dict, Any, Iterable, Callable

from nexusLIMS.utils import nexus_req
from urllib.parse import urljoin
import requests
from pprint import pprint
import logging
from datetime import datetime
from typing import List, Union, Dict

_logger = logging.getLogger(__name__)


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
        tools
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
        users
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
        users
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
        projects
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
        reservations
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

        if tool_id:
            if hasattr(tool_id, '__iter__'):
                p.update({"tool_id__in": ','.join([str(i) for i in tool_id])})
            else:
                p.update({"tool_id": tool_id})

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
                         user: Union[str, int] = None,
                         dt_from: datetime = None,
                         dt_to: datetime = None,
                         tool_id: Union[int, List[int]] = None):
        p = {}
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
        if tool_id:
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
