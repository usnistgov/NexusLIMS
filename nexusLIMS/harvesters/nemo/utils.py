"""Various utility functions used by the NEMO harvester."""
import logging
import os
import re
from datetime import datetime
from typing import Dict, List, Optional, Tuple, Union
from urllib.parse import parse_qs, urljoin, urlparse

from nexusLIMS.db.session_handler import Session

from .connector import NemoConnector

logger = logging.getLogger(__name__)


def get_harvesters_enabled() -> List[NemoConnector]:
    """
    Return a list of enabled connectors based off the environment.

    Returns
    -------
    harvesters_enabled : List[NemoConnector]
        A list of NemoConnector objects representing the NEMO APIs enabled
        via environment settings
    """
    harvesters_enabled_str: List[str] = list(
        filter(lambda x: re.search("NEMO_address", x), os.environ.keys()),
    )
    harvesters_enabled = [
        NemoConnector(
            base_url=os.getenv(addr),
            token=os.getenv(addr.replace("address", "token")),
            strftime_fmt=os.getenv(addr.replace("address", "strftime_fmt")),
            strptime_fmt=os.getenv(addr.replace("address", "strptime_fmt")),
            timezone=os.getenv(addr.replace("address", "tz")),
        )
        for addr in harvesters_enabled_str
    ]
    return harvesters_enabled  # noqa: RET504


def add_all_usage_events_to_db(
    user: Optional[Union[str, int]] = None,
    dt_from: datetime = None,
    dt_to: datetime = None,
    tool_id: Optional[Union[int, List[int]]] = None,
):
    """
    Add all usage events to database for enabled NEMO connectors.

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
    for nemo_connector in get_harvesters_enabled():
        events = nemo_connector.get_usage_events(
            user=user,
            dt_range=(dt_from, dt_to),
            tool_id=tool_id,
        )
        for event in events:
            nemo_connector.write_usage_event_to_session_log(event["id"])


def get_usage_events_as_sessions(
    user: Union[str, int] = None,
    dt_from: datetime = None,
    dt_to: datetime = None,
    tool_id: Optional[Union[int, List[int]]] = None,
) -> List[Session]:
    """
    Get all usage events for enabled NEMO connectors as Sessions.

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
    for nemo_connector in get_harvesters_enabled():
        events = nemo_connector.get_usage_events(
            user=user,
            dt_range=(dt_from, dt_to),
            tool_id=tool_id,
        )
        for event in events:
            this_session = nemo_connector.get_session_from_usage_event(event["id"])
            # this_session could be None, and if the instrument from the
            # usage event is not in our DB, this_session.instrument could
            # also be None. In each case, we should ignore that one
            if this_session is not None and this_session.instrument is not None:
                sessions.append(this_session)

    return sessions


def get_connector_for_session(session: Session) -> NemoConnector:
    """
    Get the appropriate NEMO connector for a given Session.

    Given a :py:class:`~nexusLIMS.db.session_handler.Session`, find the matching
    :py:class:`~nexusLIMS.harvesters.nemo.NemoConnector` from the enabled
    list of NEMO harvesters.

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
    instr_base_url = urljoin(session.instrument.api_url, ".")

    for nemo_connector in get_harvesters_enabled():
        if nemo_connector.config["base_url"] in instr_base_url:
            return nemo_connector

    msg = (
        f"Did not find enabled NEMO harvester for "
        f'"{session.instrument.name}". Perhaps check environment '
        f"variables? The following harvesters are enabled: "
        f"{get_harvesters_enabled()}"
    )
    raise LookupError(msg)


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
    for nemo_connector in get_harvesters_enabled():
        if base_url in nemo_connector.config["base_url"]:
            return nemo_connector

    msg = (
        f"Did not find enabled NEMO harvester with url "
        f'containing "{base_url}". Perhaps check environment '
        f"variables? The following harvesters are enabled: "
        f"{get_harvesters_enabled()}"
    )
    raise LookupError(msg)


def process_res_question_samples(
    res_dict: Dict,
) -> Tuple[
    Optional[List[Optional[str]]],
    Optional[List[Optional[str]]],
    Optional[List[Optional[str]]],
    Optional[List[Optional[str]]],
]:
    """
    Process sample information from reservation questions.

    Parameters
    ----------
    res_dict
        The reservation dictionary (i.e. the response from the ``reservations`` api
        endpoint)
    """
    sample_details, sample_pid, sample_name, periodic_tables = [], [], [], []
    sample_group = _get_res_question_value("sample_group", res_dict)
    if sample_group is not None:
        # multiple samples form will have
        # res_dict['question_data']['sample_group']['user_input'] of form:
        #
        # _{
        # _  "0": {
        # _    "sample_name": "sample_pid_1",
        # _    "sample_or_pid": "PID",
        # _    "sample_details": "A sample with a PID and some more details"
        # _  },
        # _  "1": {
        # _    "sample_name": "sample name 1",
        # _    "sample_or_pid": "Sample Name",
        # _    "sample_details": "A sample with name and some additional detail",
        # _    "periodic_table": ["H", "Ti", "Cu", "Sb", "Re"]
        # _  },
        # _  ...
        # _
        # _}
        # each key "0", "1", "2", etc. represents a single sample the user
        # added via the "Add" button. There should always be at least one,
        # since sample information is required
        # the "periodic_table" key is optional, and won't be present if the
        # user did not select anything in that section of the questions
        for _, v in sample_group.items():
            if v["sample_or_pid"].lower() == "pid":
                sample_pid.append(v["sample_name"])
                sample_name.append(None)
            elif v["sample_or_pid"].lower() == "sample name":
                sample_name.append(v["sample_name"])
                sample_pid.append(None)
            else:
                sample_name.append(None)
                sample_pid.append(None)
            # as of NEMO 4.3.2, an empty textarea returns None rather than "",
            # so check for None first, then test string length
            if v["sample_details"] is not None and len(v["sample_details"]) > 0:
                sample_details.append(v["sample_details"])
            else:
                sample_details.append(None)
            if "periodic_table" in v:
                periodic_tables.append(v["periodic_table"])
            else:
                periodic_tables.append(None)
    else:  # pragma: no cover
        # non-multiple samples (old-style form) (this is deprecated,
        # so doesn't need coverage since we don't have reservations in this
        # style any longer)
        sample_details = [_get_res_question_value("sample_details", res_dict)]
        sample_pid = [None]
        sample_name = [_get_res_question_value("sample_name", res_dict)]
    return sample_details, sample_pid, sample_name, periodic_tables


def _get_res_question_value(value: str, res_dict: Dict) -> Optional[Union[str, Dict]]:
    if "question_data" in res_dict and res_dict["question_data"] is not None:
        if value in res_dict["question_data"]:
            return res_dict["question_data"][value].get("user_input", None)

        return None

    return None


def id_from_url(url: str) -> Optional[int]:
    """
    Get the value of the id query parameter stored in URL string.

    This is used to extract the value as needed from API strings.

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
    if "id" in query:
        return int(query["id"][0])

    return None
