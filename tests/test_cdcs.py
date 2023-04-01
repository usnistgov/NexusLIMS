"""Tests functionality related to the interacting with the CDCS frontend."""
# pylint: disable=missing-function-docstring
# ruff: noqa: D102

import os
from collections import namedtuple
from pathlib import Path

import pytest

from nexusLIMS import cdcs
from nexusLIMS.utils import AuthenticationError


@pytest.mark.skipif(
    os.environ.get("test_cdcs_url") is None,
    reason="Test CDCS server not defined by 'test_cdcs_url' environment variable",
)
class TestCDCS:
    """Test the CDCS module."""

    @pytest.fixture(autouse=True)
    def _mock_test_cdcs_url(self, monkeypatch):
        """Mock 'cdcs_url' environment variable with 'test_cdcs_url' one."""
        monkeypatch.setenv("cdcs_url", os.environ.get("test_cdcs_url"))

    def test_upload_and_delete_record(self, xml_record_file):
        _files_uploaded, record_ids = cdcs.upload_record_files([xml_record_file[0]])
        cdcs.delete_record(record_ids[0])

    def test_upload_and_delete_record_glob(self, xml_record_file):
        prev_dir = Path.cwd()
        os.chdir(xml_record_file[0].parent)
        _files_uploaded, record_ids = cdcs.upload_record_files(None)
        for id_ in record_ids:
            cdcs.delete_record(id_)
        os.chdir(prev_dir)

    def test_upload_no_files_glob(self, xml_record_file):
        prev_dir = Path.cwd()
        os.chdir(xml_record_file[0].parent / "figs")
        with pytest.raises(ValueError, match="No .xml files were found"):
            _files_uploaded, _record_ids = cdcs.upload_record_files(None)
        os.chdir(prev_dir)

    def test_upload_file_bad_response(self, monkeypatch, xml_record_file, caplog):
        Response = namedtuple("Response", "status_code text")

        def mock_upload(_xml_content, _title):
            return (
                Response(status_code=404, text="This is a fake request error!"),
                "dummy_id",
            )

        monkeypatch.setattr(cdcs, "upload_record_content", mock_upload)

        files_uploaded, record_ids = cdcs.upload_record_files([xml_record_file[0]])
        assert len(files_uploaded) == 0
        assert len(record_ids) == 0
        assert f"Could not upload {xml_record_file[0].name}" in caplog.text

    def test_bad_auth(self, monkeypatch):
        monkeypatch.setenv("nexusLIMS_user", "baduser")
        monkeypatch.setenv("nexusLIMS_pass", "badpass")
        with pytest.raises(AuthenticationError):
            cdcs.get_workspace_id()
        with pytest.raises(AuthenticationError):
            cdcs.get_template_id()

    def test_delete_record_bad_response(self, monkeypatch, caplog):
        Response = namedtuple("Response", "status_code text")

        monkeypatch.setattr(
            cdcs,
            "nexus_req",
            lambda _x, _y, basic_auth: Response(  # noqa: ARG005
                status_code=404,
                text="This is a fake request error!",
            ),
        )
        cdcs.delete_record("dummy")
        assert "Received error while deleting dummy:" in caplog.text
        assert "This is a fake request error!" in caplog.text

    def test_upload_content_bad_response(self, monkeypatch, caplog):
        Response = namedtuple("Response", "status_code text json")

        # pylint: disable=unused-argument
        def mock_req(_a, _b, json=None, *, basic_auth=False):  # noqa: ARG001
            return Response(
                status_code=404,
                text="This is a fake request error!",
                json=lambda: [{"id": "dummy", "current": "dummy"}],
            )

        monkeypatch.setattr(cdcs, "nexus_req", mock_req)

        resp = cdcs.upload_record_content("<xml>content</xml>", "title")
        assert isinstance(resp, Response)
        assert "Got error while uploading title:" in caplog.text
        assert "This is a fake request error!" in caplog.text

    def test_no_env_variable(self, monkeypatch):
        # pylint: disable=protected-access
        monkeypatch.delenv("test_cdcs_url")
        monkeypatch.delenv("cdcs_url")
        with pytest.raises(ValueError, match="'cdcs_url' environment variable"):
            cdcs.cdcs_url()
