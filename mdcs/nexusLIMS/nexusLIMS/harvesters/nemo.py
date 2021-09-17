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

from nexusLIMS.utils import nexus_req
from urllib.parse import urljoin
import requests
from pprint import pprint
import logging

_logger = logging.getLogger(__name__)


class NemoConnector:
    def __init__(self, base_url, token):
        self.base_url = base_url
        self.token = token

        # these attributes are used for "memoization" of NEMO content,
        # so it can be remembered and used for a cache lookup
        # keys should be NEMO internal IDs and values should be the
        # dictionary returned by the API
        self.tools = {}
        self.users = {}
        self.users_by_username = {}

    def __repr__(self):
        return f"Connection to NEMO API at {self.base_url}"

    def get_tools(self, tool_id):
        """
        Get a list of one or more tools from the NEMO API in a dictionary
        representation

        Parameters
        ----------
        tool_id : int or :obj:`list` of :obj:`int`
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
                _logger.debug(f"Using cached tool info for tools {tool_id}")
                return [self.tools[t_id] for t_id in tool_id]
            p = {"id__in": ','.join([str(i) for i in tool_id])}
        else:
            if tool_id in self.tools:
                _logger.debug(f"Using cached tool info for tool {tool_id}")
                return [self.tools[tool_id]]
            p = {"id": tool_id}

        url = urljoin(self.base_url, 'tools/')
        _logger.info(f"getting tools from {url} with parameters {p}")
        r = nexus_req(url, requests.get,
                      token_auth=self.token, params=p)
        r.raise_for_status()
        tools = r.json()

        for t in tools:
            self.tools[t["id"]] = t

        return tools

    def get_users(self, user_id=None):
        """
        Get a list of one or more users from the NEMO API in a dictionary
        representation. The results will be cached in the NemoConnector
        instance to prevent multiple API queries if not necessary

        Parameters
        ----------
        user_id : int or :obj:`list` of :obj:`int`
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
                              f" {user_id}")
                return [self.users[u_id] for u_id in user_id]
        # single user id
        else:
            p["id"] = user_id
            if user_id in self.users:
                _logger.debug(f"Using cached user info for user id {user_id}")
                return [self.users[user_id]]

        return self._get_users_helper(p)

    def get_users_by_username(self, username=None):
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
                _logger.debug(f"Using cached user info for username {username}")
                return [self.users_by_username[username]]
        else:
            p["username__in"] = ','.join(username)
            if all(uname in self.users_by_username for uname in username):
                _logger.debug(f"Using cached user info for users with id in"
                              f" {username}")
                return [self.users_by_username[uname] for uname in username]

        return self._get_users_helper(p)

    def _get_users_helper(self, p):
        """
        Takes care of calling the users API with certain parameters

        Parameters
        ----------
        p : dict
            A dictionary of query parameters for the API query

        Returns
        -------
        users : list
            A list (could be empty) of users that match the ids and/or
            usernames given
        """
        url = urljoin(self.base_url, 'users/')
        _logger.info(f"getting users from {url} with parameters {p}")
        r = nexus_req(url, requests.get,
                      token_auth=self.token, params=p)
        r.raise_for_status()

        users = r.json()
        for u in users:
            self.users[u["id"]] = u
            self.users_by_username[u["username"]] = u

        return users

    def get_reservations(self, dt_from=None, dt_to=None):
        pass
