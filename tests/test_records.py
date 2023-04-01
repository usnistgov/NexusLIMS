"""
Tests for record_builder module.

Tests functionality related to the building of records, such as the record builder
module, acquisition activity representations, session handling, and CDCS connections
"""
# pylint: disable=C0302,missing-function-docstring,too-many-lines,too-many-locals
# ruff: noqa: D102

import os
import shutil
from datetime import datetime as dt
from datetime import timedelta as td
from functools import partial
from pathlib import Path

import pytest
from lxml import etree

from nexusLIMS.builder import record_builder
from nexusLIMS.builder.record_builder import build_record
from nexusLIMS.db import make_db_query, session_handler
from nexusLIMS.db.session_handler import Session, SessionLog, db_query
from nexusLIMS.harvesters.nemo import utils as nemo_utils
from nexusLIMS.harvesters.reservation_event import ReservationEvent
from nexusLIMS.instruments import Instrument, instrument_db
from nexusLIMS.schemas import activity
from nexusLIMS.utils import current_system_tz


@pytest.fixture(name="_remove_nemo_gov_harvester")
def _remove_nemo_gov_harvester(monkeypatch):
    """
    Remove nemo.nist.gov harvester from environment.

    Helper fixture to remove the nemo.nist.gov harvester from the environment if it's
    present, since it has _a lot_ of usage events, and takes a long time to fetch
    from the API with the current set of tests.
    """
    nemo_var = None
    for k in os.environ:
        if "nemo.nist.gov/api" in os.getenv(k) and "address" in k:
            nemo_var = k

    if nemo_var:
        monkeypatch.delenv(nemo_var, raising=False)
        monkeypatch.delenv(nemo_var.replace("address", "token"), raising=False)
        monkeypatch.delenv(nemo_var.replace("address", "strftime_fmt"), raising=False)
        monkeypatch.delenv(nemo_var.replace("address", "strptime_fmt"), raising=False)
        monkeypatch.delenv(nemo_var.replace("address", "tz"), raising=False)
        yield
        monkeypatch.undo()


class TestRecordBuilder:
    """Tests the record building module."""

    # have to do these before modifying the database with the actual run tests
    @pytest.mark.skip(
        reason="no way of currently testing SharePoint with current "
        "deployment environment; SP harvesting is deprecated",
    )
    def test_dry_run_sharepoint_calendar(self):  # pragma: no cover
        sessions = session_handler.get_sessions_to_build()
        cal_event = record_builder.dry_run_get_sharepoint_reservation_event(sessions[0])
        assert cal_event.project_name[0] == "642.03.??"
        assert cal_event.username == "***REMOVED***"
        assert cal_event.experiment_title == "Looking for Nickel Alloys"
        assert cal_event.start_time == dt.fromisoformat("2019-09-06T16:30:00-04:00")

    @pytest.mark.usefixtures("_remove_nemo_gov_harvester")
    def test_dry_run_file_find(self):
        sessions = session_handler.get_sessions_to_build()
        # add at least one NEMO session to the file find (one is already in the
        # test database, but this get_usage_events_as_sessions call will add
        # two, including one with no files)
        sessions += nemo_utils.get_usage_events_as_sessions(
            dt_from=dt.fromisoformat("2021-08-02T00:00:00-04:00"),
            dt_to=dt.fromisoformat("2021-08-03T00:00:00-04:00"),
        )
        sessions += nemo_utils.get_usage_events_as_sessions(
            dt_from=dt.fromisoformat("2021-09-01T00:00:00-04:00"),
            dt_to=dt.fromisoformat("2021-09-02T00:00:00-04:00"),
        )
        # removal of SharePoint sessions from testing
        correct_files_per_session = [28, 37, 38, 55, 0, 18, 4, 4, 0]
        file_list_list = []
        for s, ans in zip(sessions, correct_files_per_session):
            found_files = record_builder.dry_run_file_find(s)
            file_list_list.append(found_files)
            # noinspection PyTypeChecker
            assert len(found_files) == ans

        assert (
            Path(os.environ["mmfnexus_path"])
            / "Titan/***REMOVED***/***REMOVED***/15 - 620k.dm3"
        ) in file_list_list[5]

        # file from NEMO session
        assert (
            Path(os.environ["mmfnexus_path"]) / "NexusLIMS/test_files/02 - 620k-2.dm3"
        ) in file_list_list[-2]

    @pytest.mark.usefixtures("_remove_nemo_gov_harvester")
    def test_process_new_records_dry_run(self):
        # just running to ensure coverage, tests are included above
        record_builder.process_new_records(
            dry_run=True,
            dt_to=dt.fromisoformat("2021-08-03T00:00:00-04:00"),
        )

    @pytest.mark.usefixtures("_remove_nemo_gov_harvester")
    def test_process_new_records_dry_run_no_sessions(
        self,
        monkeypatch,
        caplog,
    ):
        monkeypatch.setattr(record_builder, "get_sessions_to_build", list)
        # there shouldn't be any MARLIN sessions before July 1, 2017
        record_builder.process_new_records(
            dry_run=True,
            dt_to=dt.fromisoformat("2017-07-01T00:00:00-04:00"),
        )
        assert "No 'TO_BE_BUILT' sessions were found. Exiting." in caplog.text

    @pytest.mark.usefixtures("_remove_nemo_gov_harvester", "_cleanup_session_log")
    def test_process_new_records_no_files_warning(
        self,
        monkeypatch,
        caplog,
    ):
        # overload "get_sessions_to_build" to return just one session
        dt_str_from = "2019-09-06T17:00:00.000-06:00"
        dt_str_to = "2019-09-06T18:00:00.000-06:00"
        monkeypatch.setattr(
            record_builder,
            "get_sessions_to_build",
            lambda: [
                Session(
                    session_identifier="test_session",
                    instrument=instrument_db["testsurface-CPU_P1111111"],
                    dt_range=(
                        dt.fromisoformat(dt_str_from),
                        dt.fromisoformat(dt_str_to),
                    ),
                    user="test",
                ),
            ],
        )
        record_builder.process_new_records(
            dry_run=False,
            dt_to=dt.fromisoformat("2021-07-01T00:00:00-04:00"),
        )
        assert "No files found in " in caplog.text

    @pytest.fixture(name="_add_recent_test_session")
    def _add_recent_test_session(self, request, monkeypatch):
        # insert a dummy session to DB that was within past day so it gets
        # skipped (we assume no files are being regularly added into the test
        # instrument folder)

        # the ``request.param`` parameter controls whether the timestamps have
        # timezones attached
        if request.param:
            start_ts = dt.now(tz=current_system_tz()).replace(tzinfo=None) - td(days=1)
            end_ts = dt.now(tz=current_system_tz()).replace(tzinfo=None) - td(days=0.5)
        else:
            start_ts = dt.now(tz=current_system_tz()) - td(days=1)
            end_ts = dt.now(tz=current_system_tz()) - td(days=0.5)
        start = SessionLog(
            session_identifier="test_session",
            instrument="FEI-Titan-TEM-635816_n",
            timestamp=start_ts.isoformat(),
            event_type="START",
            user="test",
            record_status="TO_BE_BUILT",
        )
        start.insert_log()
        end = SessionLog(
            session_identifier="test_session",
            instrument="FEI-Titan-TEM-635816_n",
            timestamp=end_ts.isoformat(),
            event_type="END",
            user="test",
            record_status="TO_BE_BUILT",
        )
        end.insert_log()

        s = Session(
            session_identifier="test_session",
            instrument=instrument_db["FEI-Titan-TEM-635816_n"],
            dt_range=(start_ts, end_ts),
            user="test",
        )
        # return just our session of interest to build and disable nemo
        # harvester's add_all_usage_events_to_db method
        monkeypatch.setattr(record_builder, "get_sessions_to_build", lambda: [s])
        monkeypatch.setattr(
            record_builder.nemo_utils,
            "add_all_usage_events_to_db",
            lambda dt_from, dt_to: None,  # noqa: ARG005
        )
        monkeypatch.setattr(
            record_builder.nemo,
            "res_event_from_session",
            lambda session: ReservationEvent(
                experiment_title="test",
                instrument=session.instrument,
                username="test",
                start_time=session.dt_from,
                end_time=session.dt_to,
            ),
        )

    # this parametrize call provides "request.param" with values of True and
    # then False to the add_recent_test_session fixture, which is used to
    # test both timezone-aware and timezone-naive delay implementations
    # (see https://stackoverflow.com/a/36087408)
    @pytest.mark.parametrize("_add_recent_test_session", [True, False], indirect=True)
    @pytest.mark.usefixtures(
        "_add_recent_test_session",
        "_remove_nemo_gov_harvester",
        "_cleanup_session_log",
    )
    def test_process_new_records_within_delay(
        self,
        caplog,
    ):
        record_builder.process_new_records(dry_run=False)
        assert (
            "Configured record building delay has not passed; "
            "Removing previously inserted RECORD_GENERATION " in caplog.text
        )

        _, res = db_query(
            "SELECT * FROM session_log WHERE session_identifier = ?",
            ("test_session",),
        )
        inserted_row_count = 2
        assert res[0][5] == "TO_BE_BUILT"
        assert res[1][5] == "TO_BE_BUILT"
        assert len(res) == inserted_row_count

    @pytest.mark.usefixtures("_remove_nemo_gov_harvester", "_cleanup_session_log")
    def test_process_new_nemo_record_with_no_reservation(
        self,
        monkeypatch,
        caplog,
    ):
        """
        Test building record with no reservation.

        This test method tests building a record from a NEMO instrument with
        no matching reservation; should result in "COMPLETED" status
        """
        start_ts = "2020-01-01T12:00:00.000-05:00"
        end_ts = "2020-01-01T20:00:00.000-05:00"
        start = SessionLog(
            session_identifier="test_session",
            instrument="FEI-Titan-TEM-635816_n",
            timestamp=start_ts,
            event_type="START",
            user="test",
            record_status="TO_BE_BUILT",
        )
        start.insert_log()
        end = SessionLog(
            session_identifier="test_session",
            instrument="FEI-Titan-TEM-635816_n",
            timestamp=end_ts,
            event_type="END",
            user="test",
            record_status="TO_BE_BUILT",
        )
        end.insert_log()

        s = Session(
            session_identifier="test_session",
            instrument=instrument_db["testsurface-CPU_P1111111"],
            dt_range=(dt.fromisoformat(start_ts), dt.fromisoformat(end_ts)),
            user="test",
        )
        # return just our session of interest to build and disable nemo
        # harvester's add_all_usage_events_to_db method
        monkeypatch.setattr(record_builder, "get_sessions_to_build", lambda: [s])
        monkeypatch.setattr(
            record_builder.nemo_utils,
            "add_all_usage_events_to_db",
            lambda dt_from, dt_to: None,  # noqa: ARG005
        )

        record_builder.process_new_records(dry_run=False)

        assert (
            "No reservation found matching this session, so assuming "
            "NexusLIMS does not have user consent for data harvesting." in caplog.text
        )

        _, res = db_query(
            "SELECT * FROM session_log WHERE session_identifier = ?",
            ("test_session",),
        )
        assert res[0][5] == "NO_RESERVATION"
        assert res[1][5] == "NO_RESERVATION"
        assert res[2][5] == "NO_RESERVATION"

    @pytest.mark.usefixtures("_remove_nemo_gov_harvester")
    def test_new_session_processor(
        self,
        monkeypatch,
    ):
        # make record uploader just pretend by returning all files provided
        # (as if they were actually uploaded)
        monkeypatch.setattr(record_builder, "upload_record_files", lambda x: (x, x))

        # Override the build_records function to not generate previews (since
        # this is tested elsewhere) to speed things up
        monkeypatch.setattr(
            record_builder,
            "build_record",
            partial(build_record, generate_previews=False),
        )

        # use just datetime range that should have just one record from NEMO
        record_builder.process_new_records(
            dt_from=dt.fromisoformat("2021-08-02T00:00:00-04:00"),
            dt_to=dt.fromisoformat("2021-08-03T00:00:00-04:00"),
        )

        # tests on the database entries
        # after processing the records, there should be size added
        # "RECORD_GENERATION" logs, for a total of 18 logs
        total_session_log_count = 24
        record_generation_count = 8
        to_be_built_count = 0
        no_files_found_count = 3
        completed_count = 21
        assert (
            len(
                make_db_query("SELECT * FROM session_log"),
            )
            == total_session_log_count
        )
        assert (
            len(
                make_db_query(
                    "SELECT * FROM session_log WHERE "
                    '"event_type" = "RECORD_GENERATION"',
                ),
            )
            == record_generation_count
        )
        assert (
            len(
                make_db_query(
                    'SELECT * FROM session_log WHERE "record_status" = "TO_BE_BUILT"',
                ),
            )
            == to_be_built_count
        )
        assert (
            len(
                make_db_query(
                    "SELECT * FROM session_log WHERE"
                    '"record_status" = "NO_FILES_FOUND"',
                ),
            )
            == no_files_found_count
        )
        assert (
            len(
                make_db_query(
                    'SELECT * FROM session_log WHERE "record_status" = "COMPLETED"',
                ),
            )
            == completed_count
        )

        # tests on the XML records
        # there should be 6 completed records in the records/uploaded/ folder
        upload_path = Path(os.getenv("nexusLIMS_path")).parent / "records" / "uploaded"
        xmls = list(upload_path.glob("*.xml"))
        xml_count = 7
        assert len(xmls) == xml_count

        # test some various values from the records saved to disk:
        nexus_ns = "https://data.nist.gov/od/dm/nexus/experiment/v1.0"
        motives = [
            "Trying to find us some martensite!",
            "Electron beam dose effect of C36H74 paraffin "
            "polymer under DC electron beam",
            "Determine the composition of platinum nickel "
            "alloys using EDX spectroscopy.",
            "EELS mapping of layer intermixing.",
            None,
            "Examine more closely the epitaxial (or not) "
            "registrations between the various layers.",
            "To test the harvester with multiple samples",
        ]
        instr = {
            "titan": "FEI-Titan-TEM-635816",
            "jeol": "JEOL-JEM3010-TEM-565989",
            "stem": "FEI-Titan-STEM-630901",
            "quanta": "FEI-Quanta200-ESEM-633137",
            "surface": "testsurface-CPU_P1111111",
        }
        expected = {
            # ./Titan/***REMOVED***/181113 - ***REMOVED***- Titan/
            "2018-11-13_FEI-Titan-TEM-635816_n_91.xml": {
                f"/{{{nexus_ns}}}title": "Martensite search",
                f"//{{{nexus_ns}}}acquisitionActivity": 4,
                f"//{{{nexus_ns}}}dataset": 37,
                f"/{{{nexus_ns}}}summary/{{{nexus_ns}}}motivation": motives[0],
                f"/{{{nexus_ns}}}summary/{{{nexus_ns}}}instrument": instr["titan"],
                f"//{{{nexus_ns}}}sample": 1,
            },
            # ./JEOL3010/JEOL3010/***REMOVED***/***REMOVED***/20190724/
            "2019-07-24_JEOL-JEM3010-TEM-565989_n_93.xml": {
                f"/{{{nexus_ns}}}title": "Examining beam dose impacts",
                f"//{{{nexus_ns}}}acquisitionActivity": 6,
                f"//{{{nexus_ns}}}dataset": 55,
                f"/{{{nexus_ns}}}summary/{{{nexus_ns}}}motivation": motives[1],
                f"/{{{nexus_ns}}}summary/{{{nexus_ns}}}instrument": instr["jeol"],
                f"//{{{nexus_ns}}}sample": 1,
            },
            # ./Quanta/***REMOVED***/20190830_05... and ./Quanta/***REMOVED***/tmp/20190830_05...
            "2019-09-06_FEI-Quanta200-ESEM-633137_n_90.xml": {
                f"/{{{nexus_ns}}}title": "Looking for Nickel Alloys",
                f"//{{{nexus_ns}}}acquisitionActivity": 5,
                f"//{{{nexus_ns}}}dataset": 28,
                f"/{{{nexus_ns}}}summary/{{{nexus_ns}}}motivation": motives[2],
                f"/{{{nexus_ns}}}summary/{{{nexus_ns}}}instrument": instr["quanta"],
                f"//{{{nexus_ns}}}sample": 1,
            },
            # ./643Titan/***REMOVED***/191106 - ***REMOVED***/
            "2019-11-06_FEI-Titan-STEM-630901_n_92.xml": {
                f"/{{{nexus_ns}}}title": "Reactor Samples",
                f"//{{{nexus_ns}}}acquisitionActivity": 15,
                f"//{{{nexus_ns}}}dataset": 38,
                f"/{{{nexus_ns}}}summary/{{{nexus_ns}}}motivation": motives[3],
                f"/{{{nexus_ns}}}summary/{{{nexus_ns}}}instrument": instr["stem"],
                f"//{{{nexus_ns}}}sample": 1,
            },
            # ./Titan/***REMOVED***/200204 - ***REMOVED*** - Titan/
            "2020-02-04_FEI-Titan-TEM-635816_n_95.xml": {
                f"/{{{nexus_ns}}}title": "Experiment on the FEI Titan TEM on "
                "Tuesday Feb. 04, 2020",
                f"//{{{nexus_ns}}}acquisitionActivity": 4,
                f"//{{{nexus_ns}}}dataset": 18,
                f"/{{{nexus_ns}}}summary/{{{nexus_ns}}}motivation": motives[4],
                f"/{{{nexus_ns}}}summary/{{{nexus_ns}}}instrument": instr["titan"],
                f"//{{{nexus_ns}}}sample": 1,
            },
            # expected values for NEMO built record
            "2021-08-02_testsurface-CPU_P1111111_31.xml": {
                f"/{{{nexus_ns}}}title": "Tunnel Junction Inspection",
                f"//{{{nexus_ns}}}acquisitionActivity": 1,
                f"//{{{nexus_ns}}}dataset": 4,
                f"/{{{nexus_ns}}}summary/{{{nexus_ns}}}motivation": motives[5],
                f"/{{{nexus_ns}}}summary/{{{nexus_ns}}}instrument": instr["surface"],
                f"//{{{nexus_ns}}}sample": 1,
            },
            "2021-11-29_testsurface-CPU_P1111111_21.xml": {
                f"/{{{nexus_ns}}}title": "A test with multiple samples",
                f"//{{{nexus_ns}}}acquisitionActivity": 1,
                f"//{{{nexus_ns}}}dataset": 4,
                f"/{{{nexus_ns}}}summary/{{{nexus_ns}}}motivation": motives[6],
                f"/{{{nexus_ns}}}summary/{{{nexus_ns}}}instrument": instr["surface"],
                f"//{{{nexus_ns}}}sample": 4,
            },
        }
        for f in sorted(xmls):
            base_f = f.name
            root = etree.parse(f)

            xpath = f"/{{{nexus_ns}}}title"
            if root.find(xpath) is not None:
                assert root.find(xpath).text == expected[base_f][xpath]

            xpath = f"//{{{nexus_ns}}}acquisitionActivity"
            assert len(root.findall(xpath)) == expected[base_f][xpath]

            xpath = f"//{{{nexus_ns}}}dataset"
            assert len(root.findall(xpath)) == expected[base_f][xpath]

            xpath = f"/{{{nexus_ns}}}summary/{{{nexus_ns}}}motivation"
            if root.find(xpath) is not None:
                assert root.find(xpath).text == expected[base_f][xpath]
            else:
                assert root.find(xpath) == expected[base_f][xpath]

            xpath = f"/{{{nexus_ns}}}summary/{{{nexus_ns}}}instrument"
            assert root.find(xpath).get("pid") == expected[base_f][xpath]

            xpath = f"//{{{nexus_ns}}}sample"
            assert len(root.findall(xpath)) == expected[base_f][xpath]

            # remove record
            f.unlink()

        # clean up directory
        shutil.rmtree(upload_path.parent)

    @pytest.mark.usefixtures("_remove_nemo_gov_harvester")
    def test_record_builder_strategies(self, monkeypatch):
        # test session that only has one file present
        def mock_get_sessions():
            base_url = "https://marlin.nist.gov/api"
            return [
                session_handler.Session(
                    session_identifier=f"{base_url}/usage_events/?id=91",
                    instrument=instrument_db["FEI-Titan-TEM-635816_n"],
                    dt_range=(
                        dt.fromisoformat("2018-11-13T13:00:00.000-05:00"),
                        dt.fromisoformat("2018-11-13T16:00:00.000-05:00"),
                    ),
                    user="miclims",
                ),
            ]

        nexus_ns = "https://data.nist.gov/od/dm/nexus/experiment/v1.0"

        monkeypatch.setattr(record_builder, "get_sessions_to_build", mock_get_sessions)

        # make record uploader just pretend by returning all files provided (
        # as if they were actually uploaded)
        monkeypatch.setattr(record_builder, "upload_record_files", lambda x: (x, x))

        # Override the build_records function to not generate previews (since
        # this is tested elsewhere) to speed things up
        monkeypatch.setattr(
            record_builder,
            "build_record",
            partial(build_record, generate_previews=False),
        )

        # test the inclusive strategy
        monkeypatch.setenv("NexusLIMS_file_strategy", "inclusive")
        xml_files = record_builder.build_new_session_records()
        assert len(xml_files) == 1
        f = xml_files[0]

        root = etree.parse(f)
        aa_count = 4
        dataset_count = 41
        assert root.find(f"/{{{nexus_ns}}}title").text == "Martensite search"
        assert len(root.findall(f"//{{{nexus_ns}}}acquisitionActivity")) == aa_count
        assert len(root.findall(f"//{{{nexus_ns}}}dataset")) == dataset_count
        assert (
            root.find(f"/{{{nexus_ns}}}summary/{{{nexus_ns}}}motivation").text
            == "Trying to find us some martensite!"
        )
        assert (
            root.find(f"/{{{nexus_ns}}}summary/{{{nexus_ns}}}instrument").get("pid")
            == "FEI-Titan-TEM-635816"
        )
        assert len(root.findall(f"//{{{nexus_ns}}}sample")) == 1

        # remove record
        f.unlink()

        # test with undefined environment variable
        monkeypatch.delenv("NexusLIMS_file_strategy", raising=False)
        xml_files_no = record_builder.build_new_session_records()
        # rename first xml file so the next call to build_new_session_records doesn't
        # overwrite it
        new_path = shutil.move(
            xml_files_no[0],
            Path(str(xml_files_no[0]).replace("91", "91_no_strategy")),
        )
        xml_files_no = [Path(str(new_path))]

        # test with unsupported value for environment variable
        monkeypatch.setenv("NexusLIMS_file_strategy", "bob")
        xml_files_unsupported = record_builder.build_new_session_records()

        xml_files = xml_files_no + xml_files_unsupported

        xml_count = 2
        aa_count = 4
        dataset_count = 37

        assert len(xml_files) == xml_count
        for f in xml_files:
            root = etree.parse(f)

            assert root.find(f"/{{{nexus_ns}}}title").text == "Martensite search"
            assert len(root.findall(f"//{{{nexus_ns}}}acquisitionActivity")) == aa_count
            assert len(root.findall(f"//{{{nexus_ns}}}dataset")) == dataset_count
            assert (
                root.find(f"/{{{nexus_ns}}}summary/{{{nexus_ns}}}motivation").text
                == "Trying to find us some martensite!"
            )
            assert (
                root.find(f"/{{{nexus_ns}}}summary/{{{nexus_ns}}}instrument").get("pid")
                == "FEI-Titan-TEM-635816"
            )
            assert len(root.findall(f"//{{{nexus_ns}}}sample")) == 1

            # remove record
            f.unlink()

    @pytest.mark.usefixtures("_remove_nemo_gov_harvester")
    def test_new_session_bad_upload(
        self,
        monkeypatch,
        caplog,
    ):
        # set the methods used to determine if all records were uploaded to
        # just return known lists
        monkeypatch.setattr(
            record_builder,
            "build_new_session_records",
            lambda: ["dummy_file1", "dummy_file2", "dummy_file3"],
        )
        monkeypatch.setattr(record_builder, "upload_record_files", lambda _x: ([], []))

        record_builder.process_new_records(
            dt_from=dt.fromisoformat("2021-08-01T13:00:00-06:00"),
            dt_to=dt.fromisoformat("2021-09-05T20:00:00-06:00"),
        )
        assert (
            "Some record files were not uploaded: "
            "['dummy_file1', 'dummy_file2', 'dummy_file3']" in caplog.text
        )

    @pytest.mark.usefixtures("_remove_nemo_gov_harvester")
    def test_build_record_error(self, monkeypatch, caplog):
        def mock_get_sessions():
            return [
                session_handler.Session(
                    "dummy_id",
                    "no_instrument",
                    (dt.now(tz=current_system_tz()), dt.now(tz=current_system_tz())),
                    "None",
                ),
            ]

        monkeypatch.setattr(record_builder, "get_sessions_to_build", mock_get_sessions)
        record_builder.build_new_session_records()
        assert 'Marking dummy_id as "ERROR"' in caplog.text

    @pytest.mark.usefixtures("_remove_nemo_gov_harvester")
    def test_non_validating_record(
        self,
        monkeypatch,
        caplog,
    ):
        # pylint: disable=unused-argument
        def mock_get_sessions():
            return [
                session_handler.Session(
                    session_identifier="1c3a6a8d-9038-41f5-b969-55fd02e12345",
                    instrument=instrument_db["FEI-Titan-TEM-635816_n"],
                    dt_range=(
                        dt.fromisoformat("2020-02-04T09:00:00.000"),
                        dt.fromisoformat("2020-02-04T12:00:00.001"),
                    ),
                    user="None",
                ),
            ]

        def mock_build_record(
            session,  # noqa: ARG001
            sample_id=None,  # noqa: ARG001
            *,
            generate_previews=True,  # noqa: ARG001
        ):
            return "<xml>Record that will not validate against NexusLIMS Schema</xml>"

        monkeypatch.setattr(record_builder, "get_sessions_to_build", mock_get_sessions)
        monkeypatch.setattr(record_builder, "build_record", mock_build_record)
        record_builder.build_new_session_records()
        assert "ERROR" in caplog.text
        assert "Could not validate record, did not write to disk" in caplog.text

    @pytest.mark.usefixtures("_remove_nemo_gov_harvester")
    def test_dump_record(self):
        dt_str_from = "2021-08-02T12:00:00-06:00"
        dt_str_to = "2021-08-02T15:00:00-06:00"
        session = Session(
            session_identifier="an-identifier-string",
            instrument=instrument_db["testsurface-CPU_P1111111"],
            dt_range=(dt.fromisoformat(dt_str_from), dt.fromisoformat(dt_str_to)),
            user="unused",
        )
        out_fname = record_builder.dump_record(session=session, generate_previews=False)
        out_fname.unlink()

    @pytest.mark.usefixtures("_remove_nemo_gov_harvester")
    def test_no_sessions(self, monkeypatch):
        # monkeypatch to return empty list (as if there are no sessions)
        monkeypatch.setattr(record_builder, "get_sessions_to_build", list)
        with pytest.raises(SystemExit) as exception:
            record_builder.build_new_session_records()
        assert exception.type == SystemExit

    @pytest.mark.usefixtures("_remove_nemo_gov_harvester")
    def test_build_record_no_consent(
        self,
        monkeypatch,
        caplog,
    ):
        #  https://***REMOVED***/api/reservations/?id=168
        def mock_get_sessions():
            return [
                session_handler.Session(
                    session_identifier="test_session",
                    instrument=instrument_db["testsurface-CPU_P1111111"],
                    dt_range=(
                        dt.fromisoformat("2021-12-08T09:00:00.000-07:00"),
                        dt.fromisoformat("2021-12-08T12:00:00.000-07:00"),
                    ),
                    user="None",
                ),
            ]

        monkeypatch.setattr(record_builder, "get_sessions_to_build", mock_get_sessions)
        xmls_files = record_builder.build_new_session_records()

        _, res = db_query(
            "SELECT * FROM session_log WHERE session_identifier = ?",
            ("test_session",),
        )
        assert res[0][5] == "NO_CONSENT"
        assert (
            "Reservation 168 requested not to have their data harvested" in caplog.text
        )
        assert len(xmls_files) == 0  # no record should be returned

    @pytest.mark.usefixtures("_remove_nemo_gov_harvester")
    def test_build_record_single_file(self, monkeypatch):
        # test session that only has one file present
        def mock_get_sessions():
            return [
                session_handler.Session(
                    session_identifier="https://***REMOVED***/api/usage_events"
                    "/?id=-1",
                    instrument=instrument_db["testsurface-CPU_P1111111"],
                    dt_range=(
                        dt.fromisoformat("2021-11-29T11:28:01.000-07:00"),
                        dt.fromisoformat("2021-11-29T11:28:02.000-07:00"),
                    ),
                    user="None",
                ),
            ]

        nexus_ns = "https://data.nist.gov/od/dm/nexus/experiment/v1.0"

        monkeypatch.setattr(record_builder, "get_sessions_to_build", mock_get_sessions)

        # make record uploader just pretend by returning all files provided (
        # as if they were actually uploaded)
        monkeypatch.setattr(record_builder, "upload_record_files", lambda x: (x, x))

        xml_files = record_builder.build_new_session_records()
        assert len(xml_files) == 1

        aa_count = 1
        dataset_count = 1
        sample_count = 4

        f = xml_files[0]
        root = etree.parse(f)

        assert root.find(f"/{{{nexus_ns}}}title").text == "A test with multiple samples"
        assert len(root.findall(f"//{{{nexus_ns}}}acquisitionActivity")) == aa_count
        assert len(root.findall(f"//{{{nexus_ns}}}dataset")) == dataset_count
        assert (
            root.find(f"/{{{nexus_ns}}}summary/{{{nexus_ns}}}motivation").text
            == "To test the harvester with multiple samples"
        )
        assert (
            root.find(f"/{{{nexus_ns}}}summary/{{{nexus_ns}}}instrument").get("pid")
            == "testsurface-CPU_P1111111"
        )
        assert len(root.findall(f"//{{{nexus_ns}}}sample")) == sample_count
        assert (
            root.find(f"//{{{nexus_ns}}}dataset/{{{nexus_ns}}}preview").text
            == "/NexusLIMS/test_files/04%20-%20620k.dm3.thumb.png"
        )

        # remove record
        f.unlink()

    @pytest.mark.usefixtures("_remove_nemo_gov_harvester")
    def test_build_record_with_sample_elements(
        self,
        monkeypatch,
    ):
        # test session that only has one file present
        def mock_get_sessions():
            return [
                session_handler.Session(
                    session_identifier="https://***REMOVED***/api/usage_events"
                    "/?id=-1",
                    instrument=instrument_db["testsurface-CPU_P1111111"],
                    dt_range=(
                        dt.fromisoformat("2023-02-13T13:00:00.000-07:00"),
                        dt.fromisoformat("2023-02-13T14:00:00.000-07:00"),
                    ),
                    user="None",
                ),
            ]

        nexus_ns = "https://data.nist.gov/od/dm/nexus/experiment/v1.0"

        monkeypatch.setattr(record_builder, "get_sessions_to_build", mock_get_sessions)

        # make record uploader just pretend by returning all files provided (
        # as if they were actually uploaded)
        monkeypatch.setattr(record_builder, "upload_record_files", lambda x: (x, x))

        # override preview generation to save time
        monkeypatch.setattr(
            record_builder,
            "build_record",
            partial(build_record, generate_previews=False),
        )

        xml_files = record_builder.build_new_session_records()

        aa_count = 1
        dataset_count = 4
        sample_count = 3

        assert len(xml_files) == 1
        f = xml_files[0]
        root = etree.parse(f)

        assert (
            root.find(f"/{{{nexus_ns}}}title").text
            == "Test reservation for multiple samples, some with elements, some not"
        )
        assert len(root.findall(f"//{{{nexus_ns}}}acquisitionActivity")) == aa_count
        assert len(root.findall(f"//{{{nexus_ns}}}dataset")) == dataset_count
        assert (
            root.find(f"/{{{nexus_ns}}}summary/{{{nexus_ns}}}motivation").text
            == "testing"
        )
        assert (
            root.find(f"/{{{nexus_ns}}}summary/{{{nexus_ns}}}instrument").get("pid")
            == "testsurface-CPU_P1111111"
        )
        assert len(root.findall(f"//{{{nexus_ns}}}sample")) == sample_count

        # test sample element tags
        expected = [
            None,
            [
                f"{{{nexus_ns}}}S",
                f"{{{nexus_ns}}}Rb",
                f"{{{nexus_ns}}}Sb",
                f"{{{nexus_ns}}}Re",
                f"{{{nexus_ns}}}Cm",
            ],
            [f"{{{nexus_ns}}}Ir"],
        ]
        sample_elements = root.findall(f"//{{{nexus_ns}}}sample")
        for exp, element in zip(expected, sample_elements):
            this_element = element.find(f"{{{nexus_ns}}}elements")
            if exp is None:
                assert exp == this_element
            else:
                assert [i.tag for i in this_element] == exp

        # remove record
        f.unlink()

    def test_not_implemented_harvester(self):
        # need to create a session with an instrument with a bogus harvester
        i = Instrument(harvester="bogus")
        s = session_handler.Session(
            session_identifier="identifier",
            instrument=i,
            dt_range=(
                dt.fromisoformat("2021-12-09T11:40:00-07:00"),
                dt.fromisoformat("2021-12-09T11:41:00-07:00"),
            ),
            user="miclims",
        )
        with pytest.raises(NotImplementedError) as exception:
            record_builder.get_reservation_event(s)
        assert "Harvester bogus not found in nexusLIMS.harvesters" in str(
            exception.value,
        )

    def test_not_implemented_res_event_from_session(self, monkeypatch):
        # create a session, but mock remove the res_event_from_session
        # attribute from the nemo harvester to simulate a module that doesn't
        # have that method defined
        with monkeypatch.context() as m_patch:
            m_patch.delattr("nexusLIMS.harvesters.nemo.res_event_from_session")
            with pytest.raises(NotImplementedError) as exception:
                record_builder.get_reservation_event(
                    session_handler.Session(
                        session_identifier="identifier",
                        instrument=instrument_db["testsurface-CPU_P1111111"],
                        dt_range=(
                            dt.fromisoformat("2021-12-09T11:40:00-07:00"),
                            dt.fromisoformat("2021-12-09T11:41:00-07:00"),
                        ),
                        user="miclims",
                    ),
                )
            assert "res_event_from_session has not been implemented for" in str(
                exception.value,
            )


@pytest.fixture(scope="module", name="_gnu_find_activities")
def gnu_find_activities():
    """Find specific activity for testing."""
    instr = instrument_db["FEI-Titan-TEM-635816_n"]
    dt_from = dt.fromisoformat("2018-11-13T13:00:00.000-05:00")
    dt_to = dt.fromisoformat("2018-11-13T16:00:00.000-05:00")
    activities_list = record_builder.build_acq_activities(
        instrument=instr,
        dt_from=dt_from,
        dt_to=dt_to,
        generate_previews=False,
    )

    return {
        "instr": instr,
        "dt_from": dt_from,
        "dt_to": dt_to,
        "activities_list": activities_list,
    }


class TestActivity:
    """Test the representation and functionality of acquisition activities."""

    @pytest.mark.skip(reason="method deprecated in v1.2.0")
    def test_gnu_find_vs_pure_python(
        self,
        monkeypatch,
        _gnu_find_activities,  # noqa: PT019
    ):  # pragma: no cover
        # force the GNU find method to fail
        def mock_gnu_find(_path, _dt_from, _dt_to, _extensions, _followlinks):
            msg = "Mock failure for GNU find method"
            raise RuntimeError(msg)

        monkeypatch.setattr(record_builder, "gnu_find_files_by_mtime", mock_gnu_find)
        activities_list_python_find = record_builder.build_acq_activities(
            instrument=_gnu_find_activities["instr"],
            dt_from=_gnu_find_activities["dt_from"],
            dt_to=_gnu_find_activities["dt_to"],
            generate_previews=False,
        )

        for i, this_activity in enumerate(activities_list_python_find):
            assert str(_gnu_find_activities["activities_list"][i]) == str(this_activity)

    def test_activity_repr(self, _gnu_find_activities):  # noqa: PT019
        expected = (
            "             AcquisitionActivity; "
            "start: 2018-11-13T13:01:28.179682-05:00; "
            "end: 2018-11-13T13:19:14.635522-05:00"
        )
        assert repr(_gnu_find_activities["activities_list"][0]) == expected

    def test_activity_str(self, _gnu_find_activities):  # noqa: PT019
        expected = "2018-11-13T13:01:28.179682-05:00 AcquisitionActivity "
        assert str(_gnu_find_activities["activities_list"][0]) == expected

    def test_add_file_bad_meta(
        self,
        monkeypatch,
        caplog,
        _gnu_find_activities,  # noqa: PT019
        eels_si_643,
    ):
        # make parse_metadata return None to force into error situation
        monkeypatch.setattr(
            activity,
            "parse_metadata",
            lambda fname, generate_preview: (None, ""),  # noqa: ARG005
        )
        orig_activity_file_length = len(
            _gnu_find_activities["activities_list"][0].files,
        )
        _gnu_find_activities["activities_list"][0].add_file(eels_si_643[0])
        assert (
            len(_gnu_find_activities["activities_list"][0].files)
            == orig_activity_file_length + 1
        )
        assert f"Could not parse metadata of {eels_si_643[0]}" in caplog.text

    def test_add_file_bad_file(self, _gnu_find_activities):  # noqa: PT019
        with pytest.raises(FileNotFoundError):
            _gnu_find_activities["activities_list"][0].add_file(
                Path("dummy_file_does_not_exist"),
            )

    def test_store_unique_before_setup(
        self,
        monkeypatch,
        caplog,
        _gnu_find_activities,  # noqa: PT019
    ):
        activity_1 = _gnu_find_activities["activities_list"][0]
        monkeypatch.setattr(activity_1, "setup_params", None)
        activity_1.store_unique_metadata()
        assert (
            "setup_params has not been defined; call store_setup_params() "
            "prior to using this method. Nothing was done." in caplog.text
        )

    def test_as_xml(self, _gnu_find_activities):  # noqa: PT019
        activity_1 = _gnu_find_activities["activities_list"][0]
        # setup a few values in the activity to trigger XML escaping:
        activity_1.setup_params["Acquisition Device"] = "<TEST>"
        activity_1.files[0] += "<&"
        activity_1.unique_meta[0]["Imaging Mode"] = "<IMAGING>"

        _ = activity_1.as_xml(seqno=0, sample_id="sample_id")
