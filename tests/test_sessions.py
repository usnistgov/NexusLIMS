"""Tests functionality related to handling of session objects."""
# pylint: disable=missing-function-docstring
# ruff: noqa: D102

from datetime import datetime as dt
from uuid import uuid4

import pytest

from nexusLIMS.db import make_db_query, session_handler
from nexusLIMS.db.session_handler import db_query
from nexusLIMS.instruments import instrument_db


class TestSession:
    """Test the Session class representing a unit of time on an instrument."""

    @pytest.fixture()
    def session(self):
        return session_handler.Session(
            session_identifier="test_session",
            instrument=instrument_db["FEI-Titan-TEM-635816_n"],
            dt_range=(
                dt.fromisoformat("2020-02-04T09:00:00.000"),
                dt.fromisoformat("2020-02-04T12:00:00.000"),
            ),
            user="None",
        )

    def test_session_repr(self, session):
        assert (
            repr(session) == "2020-02-04T09:00:00 to "
            "2020-02-04T12:00:00 on "
            "FEI-Titan-TEM-635816_n"
        )

    @pytest.mark.usefixtures("_cleanup_session_log")
    def test_record_generation_timestamp(self, session):
        row_dict = session.insert_record_generation_event()
        _, res = db_query(
            "SELECT timestamp FROM session_log WHERE id_session_log = ?",
            (row_dict["id_session_log"],),
        )
        assert dt.fromisoformat(res[0][0]).tzinfo is not None

    def test_bad_db_status(self):
        uuid = uuid4()
        query = (
            f"INSERT INTO session_log "
            f"(instrument, event_type, session_identifier, record_status) "
            f"VALUES ('FEI-Titan-TEM-635816_n', 'START', "
            f"'{uuid}', 'TO_BE_BUILT');"
        )
        make_db_query(query)
        # because we put in an extra START log with TO_BE_BUILT status,
        # this should raise an error:
        with pytest.raises(
            ValueError,
            match="There was not exactly one 'END' log for this 'START' log; ",
        ):
            session_handler.get_sessions_to_build()

        # remove the session log we added
        query = f"DELETE FROM session_log WHERE session_identifier = '{uuid}'"
        make_db_query(query)


class TestSessionLog:
    """
    Test the SessionLog class.

    A SessionLog object represents a single row in the session_log table of the
    NexusLIMS database
    """

    sl = session_handler.SessionLog(
        session_identifier="testing-session-log",
        instrument=instrument_db["FEI-Titan-TEM-635816_n"].name,
        timestamp="2020-02-04T09:00:00.000",
        event_type="START",
        user="ear1",
        record_status="TO_BE_BUILT",
    )

    @pytest.fixture(name="_record_cleanup_session_log")
    def cleanup_session_log(self):
        # this fixture removes the rows for the session logs added in
        # this test class, so it doesn't mess up future record building tests
        yield None
        # below runs on test teardown
        db_query(
            query="DELETE FROM session_log WHERE session_identifier = ?",
            args=("testing-session-log",),
        )

    def test_repr(self):
        assert (
            repr(self.sl) == "SessionLog "
            "(id=testing-session-log, "
            "instrument=FEI-Titan-TEM-635816_n, "
            "timestamp=2020-02-04T09:00:00.000, "
            "event_type=START, "
            "user=ear1, "
            "record_status=TO_BE_BUILT)"
        )

    def test_insert_log(self):
        _, res_before = db_query(query="SELECT * FROM session_log", args=None)
        self.sl.insert_log()
        _, res_after = db_query(query="SELECT * FROM session_log", args=None)
        assert len(res_after) - len(res_before) == 1

    @pytest.mark.usefixtures("_record_cleanup_session_log")
    def test_insert_duplicate_log(self, caplog):
        result = self.sl.insert_log()
        assert "WARNING" in caplog.text
        assert "SessionLog already existed in DB, so no row was added:" in caplog.text
        assert result
