"""Defines the NemoConnector class that is used to interface with the NEMO API."""

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple, Union
from urllib.parse import parse_qs, urljoin, urlparse

from pytz import timezone as pytz_timezone

from nexusLIMS.db.session_handler import Session, SessionLog, db_query
from nexusLIMS.instruments import get_instr_from_api_url, instrument_db
from nexusLIMS.utils import nexus_req

logger = logging.getLogger(__name__)


class NemoConnector:
    """
    A connection to an instance of the API of the NEMO laboratory management software.

    Provides helper methods for fetching data from the API.

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

    def __init__(  # pylint: disable=too-many-arguments # noqa: PLR0913
        self,
        base_url: str,
        token: str,
        strftime_fmt: Optional[str] = None,
        strptime_fmt: Optional[str] = None,
        timezone: Optional[str] = None,
    ):
        self.config = {
            "base_url": base_url,
            "token": token,
            "strftime_fmt": strftime_fmt,
            "strptime_fmt": strptime_fmt,
            "timezone": timezone,
        }

        # these attributes are used for "memoization" of NEMO content,
        # so it can be remembered and used for a cache lookup
        # keys should be NEMO internal IDs and values should be the
        # dictionary returned by the API
        self.tools = {}
        self.users = {}
        self.users_by_username = {}
        self.projects = {}

    def __repr__(self):
        """Return custom representation of a NemoConnector."""
        return f"Connection to NEMO API at {self.config['base_url']}"

    def strftime(self, date_dt) -> str:
        """
        Convert datetime to appropriate string format for this connector.

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
        if self.config["strftime_fmt"] is None:
            return date_dt.isoformat()

        if (
            "%z" in self.config["strftime_fmt"] or "%Z" in self.config["strftime_fmt"]
        ) and date_dt.tzinfo is None:
            # make sure datetime is timezone aware if timezone is
            # indicated in strftime_fmt. Use NEMO_tz setting if present,
            # otherwise use local server timezone
            if self.config["timezone"]:
                date_dt = pytz_timezone(self.config["timezone"]).localize(date_dt)
            else:
                date_dt = date_dt.astimezone()
        return date_dt.strftime(self.config["strftime_fmt"])

    def strptime(self, date_str) -> datetime:
        """
        Convert string to datetime using this connector's API date format.

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
        if self.config["strptime_fmt"] is None:
            date_dt = datetime.fromisoformat(date_str)
        else:
            # to be defensive here, try without microseconds as well if ".%f"
            # is in strptime_fmt and it fails (since sometimes NEMO doesn't
            # write microseconds for every time, even if it's supposed to
            try:
                date_dt = datetime.strptime(  # noqa: DTZ007
                    date_str,
                    self.config["strptime_fmt"],
                )
            except ValueError as exception:
                if ".%f" in self.config["strptime_fmt"]:
                    date_dt = datetime.strptime(  # noqa: DTZ007
                        date_str,
                        self.config["strptime_fmt"].replace(".%f", ""),
                    )
                else:
                    raise ValueError(str(exception)) from exception  # pragma: no cover

        if self.config["timezone"]:
            # strip any timezone information from the datetime, then localize
            # with pytz to whatever timezone specified
            date_dt = date_dt.replace(tzinfo=None)
            date_dt = pytz_timezone(self.config["timezone"]).localize(date_dt)

        return date_dt

    def get_tools(self, tool_id: Union[int, List[int]]) -> List[Dict]:
        """
        Get a list of one or more tools from the NEMO API in a dictionary.

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
        if hasattr(tool_id, "__iter__"):
            if all(t_id in self.tools for t_id in tool_id):
                logger.debug(
                    "Using cached tool info for tools %s: %s",
                    tool_id,
                    [self.tools[t]["name"] for t in tool_id],
                )
                return [self.tools[t_id] for t_id in tool_id]
            params = {"id__in": ",".join([str(i) for i in tool_id])}
        else:
            if tool_id in self.tools:
                logger.debug(
                    'Using cached tool info for tool %s: "%s"',
                    tool_id,
                    self.tools[tool_id]["name"],
                )
                return [self.tools[tool_id]]
            params = {"id": tool_id}

        tools = self._api_caller("GET", "tools/", params)

        for tool in tools:
            # cache the tool results
            self.tools[tool["id"]] = tool

        return tools

    def get_users(self, user_id: Optional[Union[int, List[int]]] = None) -> List[Dict]:
        """
        Get a list of one or more users from the NEMO API in a dictionary.

        The results will be cached in the NemoConnector instance to prevent multiple
        API queries if not necessary.

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
        params = {}

        # list of user ids
        if hasattr(user_id, "__iter__"):
            params["id__in"] = ",".join([str(i) for i in user_id])
            if all(u_id in self.users for u_id in user_id):
                logger.debug(
                    "Using cached user info for users with id in %s: %s",
                    user_id,
                    [self.users[u]["username"] for u in user_id],
                )
                return [self.users[u_id] for u_id in user_id]
        # single user id
        else:
            params["id"] = user_id
            if user_id in self.users:
                logger.debug(
                    'Using cached user info for user id %s: "%s"',
                    user_id,
                    self.users[user_id]["username"],
                )
                return [self.users[user_id]]

        return self._get_users_helper(params)

    def get_users_by_username(self, username=None) -> List:
        """
        Get a list of one or more users from the NEMO API in a dictionary.

        The results will be cached in the NemoConnector
        instance to prevent multiple API queries if not necessary.

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
        params = {}
        if isinstance(username, str):
            params["username__iexact"] = username
            if username in self.users_by_username:
                logger.debug('Using cached user info for username "%s"', username)
                return [self.users_by_username[username]]
        else:
            params["username__in"] = ",".join(username)
            if all(uname in self.users_by_username for uname in username):
                logger.debug("Using cached user info for users with id in %s", username)
                return [self.users_by_username[uname] for uname in username]

        return self._get_users_helper(params)

    def get_projects(self, proj_id: Union[int, List[int]]) -> List[Dict]:
        """
        Get a list of one or more projects from the NEMO API in a dictionary.

        The local cache will be checked prior to fetching
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
        if hasattr(proj_id, "__iter__"):
            if all(p_id in self.projects for p_id in proj_id):
                logger.debug(
                    "Using cached project info for projects %s: %s",
                    proj_id,
                    [self.projects[p]["name"] for p in proj_id],
                )
                return [self.projects[p_id] for p_id in proj_id]
            params = {"id__in": ",".join([str(i) for i in proj_id])}
        else:
            if proj_id in self.projects:
                logger.debug(
                    'Using cached project info for project %s: "%s"',
                    proj_id,
                    self.projects[proj_id]["name"],
                )
                return [self.projects[proj_id]]
            params = {"id": proj_id}

        projects = self._api_caller("GET", "projects/", params)

        for params in projects:
            # expand the only_allow_tools node
            if "only_allow_tools" in params:
                params.update(
                    {
                        "only_allow_tools": [
                            self.get_tools(t)[0] for t in params["only_allow_tools"]
                        ],
                    },
                )
            self.projects[params["id"]] = params

        return projects

    def get_reservations(
        self,
        dt_from: datetime = None,
        dt_to: datetime = None,
        tool_id: Optional[Union[int, List[int]]] = None,
        *,
        cancelled: Optional[bool] = False,
    ) -> List[Dict]:
        """
        Get reservations from the NEMO API filtered in various ways.

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
        params = {}

        if dt_from:
            params["start__gte"] = self.strftime(dt_from)
        if dt_to:
            params["end__lte"] = self.strftime(dt_to)
        if cancelled is not None:
            params["cancelled"] = cancelled

        if tool_id is not None:
            if isinstance(tool_id, list):
                params.update({"tool_id__in": ",".join([str(i) for i in tool_id])})
            else:
                params.update({"tool_id": str(tool_id)})

        reservations = self._api_caller("GET", "reservations/", params)

        parsed_reservations = []
        for reservation in reservations:
            parsed_reservations.append(self._parse_reservation(reservation))

        return parsed_reservations

    def _parse_reservation(self, reservation: dict) -> dict:
        # expand various fields within the reservation data
        if reservation["user"]:
            user = self.get_users(reservation["user"])
            if user:
                reservation.update({"user": user[0]})
        if reservation["creator"]:
            user = self.get_users(reservation["creator"])
            if user:
                reservation.update({"creator": user[0]})
        if reservation["tool"]:
            tool = self.get_tools(reservation["tool"])
            if tool:
                reservation.update({"tool": tool[0]})
        if reservation["project"]:
            params = self.get_projects(reservation["project"])
            if params:
                reservation.update({"project": params[0]})
        if reservation["cancelled_by"]:
            user = self.get_users(reservation["cancelled_by"])
            if user:
                reservation.update({"cancelled_by": user[0]})
        return reservation

    def get_usage_events(
        self,
        event_id: Optional[Union[int, List[int]]] = None,
        user: Optional[Union[str, int]] = None,
        dt_range: Optional[Tuple[Optional[datetime], Optional[datetime]]] = None,
        tool_id: Optional[Union[int, List[int]]] = None,
    ) -> List:
        """
        Get usage events from the NEMO API filtered in various ways.

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
        dt_range
            The "starting" and "end" points of the time range; only usage events
            starting between these points in time will be returned
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
        params = self._parse_dt_range(dt_range, {})

        if event_id is not None:
            if hasattr(event_id, "__iter__"):
                params.update({"id__in": ",".join([str(i) for i in event_id])})
            else:
                params.update({"id": event_id})
        if user:
            if isinstance(user, str):
                u_id = self.get_users_by_username(user)[0]["id"]
            else:
                u_id = user
            params["user_id"] = u_id

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

        params.update({"tool_id__in": ",".join([str(i) for i in tool_id])})

        usage_events = self._api_caller("GET", "usage_events/", params)

        parsed_events = []
        for event in usage_events:
            parsed_events.append(self._parse_event(event))

        return parsed_events

    def _parse_dt_range(
        self,
        dt_range: Optional[Tuple[Optional[datetime], Optional[datetime]]],
        params: Dict,
    ) -> Dict:
        if dt_range is not None:
            dt_from, dt_to = dt_range
            if dt_from is not None:
                params["start__gte"] = self.strftime(dt_from)
            if dt_to is not None:
                params["end__lte"] = self.strftime(dt_to)
        return params

    def _parse_event(self, event: dict) -> dict:
        # expand various fields within the usage event data
        if event["user"]:
            user = self.get_users(event["user"])
            if user:
                event.update({"user": user[0]})
        if event["operator"]:
            user = self.get_users(event["operator"])
            if user:
                event.update({"operator": user[0]})
        if event["project"]:
            proj = self.get_projects(event["project"])
            if proj:
                event.update({"project": proj[0]})
        if event["tool"]:
            tool = self.get_tools(event["tool"])
            if tool:
                event.update({"tool": tool[0]})
        return event

    def write_usage_event_to_session_log(self, event_id: int) -> None:
        """
        Write a usage event to the NexusLIMS database session log.

        Inserts two rows (if needed) into the ``session_log`` (marking the start
        and end of a usage event), only for instruments recognized by
        NexusLIMS (i.e. that have a row in the ``instruments`` table of the DB).
        If the usage event has not ended yet, no action is performed.

        Parameters
        ----------
        event_id
            The NEMO id number for the event to insert

        """
        event = self.get_usage_events(event_id=event_id)
        if event:
            # get_usage_events returns list, so pick out first one
            event = event[0]
            tool_api_url = f"{self.config['base_url']}tools/?id={event['tool']['id']}"
            instr = get_instr_from_api_url(tool_api_url)
            if instr is None:  # pragma: no cover
                # this shouldn't happen since we limit our usage event API call
                # only to instruments contained in our DB, but we can still
                # defend against it regardless
                logger.warning(
                    "Usage event %s was for an instrument (%s) not known "
                    "to NexusLIMS, so no records will be added to DB.",
                    event_id,
                    tool_api_url,
                )
                return
            if event["end"] is None:
                logger.warning(
                    "Usage event %s has not yet ended, so no records "
                    "will be added to DB.",
                    event_id,
                )
                return
            session_id = f"{self.config['base_url']}usage_events/?id={event['id']}"

            # try to insert start log
            res = db_query(
                "SELECT * FROM session_log WHERE session_identifier "
                "= ? AND event_type = ?",
                (session_id, "START"),
            )
            if len(res[1]) > 0:
                # there was already a start log, so warn and don't do anything:
                logger.warning(
                    "A 'START' log with session id \"%s\" was found in the the DB, "
                    "so a new one will not be inserted for this event",
                    session_id,
                )
            else:
                start_log = SessionLog(
                    session_identifier=session_id,
                    instrument=instr.name,
                    # make sure to coerce format to ISO before putting in DB
                    timestamp=self.strptime(event["start"]).isoformat(),
                    event_type="START",
                    user=event["user"]["username"],
                    record_status="TO_BE_BUILT",
                )
                start_log.insert_log()

            # try to insert end log
            res = db_query(
                "SELECT * FROM session_log WHERE session_identifier "
                "= ? AND event_type = ?",
                (session_id, "END"),
            )
            if len(res[1]) > 0:
                # there was already an end log, so warn and don't do anything:
                logger.warning(
                    "An 'END' log with session id \"%s\" was found in the the DB, "
                    "so a new one will not be inserted for this event",
                    session_id,
                )
            else:
                end_log = SessionLog(
                    session_identifier=session_id,
                    instrument=instr.name,
                    # make sure to coerce format to ISO before putting in DB
                    timestamp=self.strptime(event["end"]).isoformat(),
                    event_type="END",
                    user=event["user"]["username"],
                    record_status="TO_BE_BUILT",
                )
                end_log.insert_log()
        else:
            logger.warning(
                "No usage event with id = %s was found for %s",
                event_id,
                self,
            )

    def get_session_from_usage_event(self, event_id: int) -> Optional[Session]:
        """
        Get a Session representation of a usage event.

        Get a :py:class:`~nexusLIMS.db.session_handler.Session`
        representation of a usage event for use in dry runs of the record
        builder.

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
            if event["start"] is not None and event["end"] is None:  # pragma: no cover
                logger.warning(
                    "Usage event with id = %s has not yet ended for '%s'",
                    event_id,
                    self,
                )
                return None
            instr = get_instr_from_api_url(
                f"{self.config['base_url']}tools/?id={event['tool']['id']}",
            )
            session_id = f"{self.config['base_url']}usage_events/?id={event_id}"
            session = Session(
                session_identifier=session_id,
                instrument=instr,
                dt_range=(self.strptime(event["start"]), self.strptime(event["end"])),
                user=event["user"]["username"],
            )
            return session

        logger.warning("No usage event with id = %s was found for '%s'", event_id, self)
        return None

    def get_known_tool_ids(self) -> List[int]:
        """
        Get NEMO tool ID values from the NexusLIMS database.

        Inspect the ``api_url`` values of known Instruments (from
        the ``instruments`` table in the DB), and extract their tool_id number
        if it is from this NemoConnector.

        Returns
        -------
        tool_ids : List[int]
            The list of tool ID numbers known to NexusLIMS for this harvester
        """
        tool_ids = []

        for _, v in instrument_db.items():
            if self.config["base_url"] in v.api_url:
                # Instrument is associated with this connector
                parsed_url = urlparse(v.api_url)
                # extract 'id' query parameter from url
                tool_id = parse_qs(parsed_url.query)["id"][0]
                tool_ids.append(int(tool_id))

        return tool_ids

    def _get_users_helper(self, params: Dict[str, str]) -> list:
        """
        Call the users API with certain parameters.

        Parameters
        ----------
        params
            A dictionary of query parameters for the API query

        Returns
        -------
        users
            A list (could be empty) of users that match the ids and/or
            usernames given
        """
        users = self._api_caller("GET", "users/", params)
        for user in users:
            # cache the users response by ID and username
            self.users[user["id"]] = user
            self.users_by_username[user["username"]] = user

        return users

    def _api_caller(
        self,
        verb: str,
        endpoint: str,
        params: Dict[str, str],
    ) -> List[Dict[str, Any]]:
        """
        Make a call to the NEMO API.

        Helper function to deduplicate actual calls to the API. Takes care of
        building the full URL from the base URL and specific endpoint,
        as well as authentication, passing of parameters, and parsing the
        results.

        Parameters
        ----------
        verb
            The ``requests`` verb (``'POST'``, ``'GET'``,
            ``'PATCH'``, etc.) to use for the API request
        endpoint
            The API endpoint to use. Should be formatted with a trailing
            slash and no leading slash. i.e. the endpoint for Projects data
            should be supplied as ``'projects/'``
        params
            The URL parameters to pass along with the request. These are
            generally filters for the API data such as ``id`` or a date range
            or something similar.

        Returns
        -------
        results
            The API response, formatted as a list of dict objects
        """
        url = urljoin(self.config["base_url"], endpoint)
        logger.info("getting data from %s with parameters %s", url, params)
        response = nexus_req(url, verb, token_auth=self.config["token"], params=params)
        response.raise_for_status()

        return response.json()
