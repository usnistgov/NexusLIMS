#  NIST Public License - 2020
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
"""Set up pytest configuration."""

# pylint: disable=unused-argument

import os
import shutil
import tarfile
from datetime import datetime as dt
from datetime import timedelta as td
from pathlib import Path

import pytest
from _pytest.monkeypatch import MonkeyPatch

from nexusLIMS.utils import current_system_tz

from .utils import delete_files, extract_files, tars

# use our test database for all tests (don't want to impact real one)
os.environ["nexusLIMS_db_path"] = str(
    Path(__file__).parent / "files" / "test_db.sqlite",
)
os.environ["nexusLIMS_path"] = str(Path(__file__).parent / "files" / "nexusLIMS_path")

# we don't want to mask mmfnexus directory, because the record builder tests
# need to look at the real files on the mmfnexus storage path


def pytest_configure(config):  # noqa: ARG001
    """
    Configure pytest.

    Allows plugins and conftest files to perform initial configuration.
    This hook is called for every plugin and initial conftest
    file after command line options have been parsed.

    Unpack the test_db at the very beginning since we need it right away
    when importing the instruments.py module (for instrument_db)
    """
    with tarfile.open(tars["DB"], "r:gz") as tar:
        tar.extractall(path=Path(tars["DB"]).parent)

    from nexusLIMS.db import make_db_query  # pylint: disable=import-outside-toplevel

    # update API URLs for marlin.nist.gov if we're using marlin-test.nist.gov:
    if "marlin-test.nist.gov" in os.environ.get("NEMO_address_1", ""):
        make_db_query(
            "UPDATE instruments "
            "SET api_url = "
            "REPLACE(api_url, '***REMOVED***', '***REMOVED***');",
        )
        make_db_query(
            "UPDATE session_log "
            "SET session_identifier = "
            "REPLACE(session_identifier, '***REMOVED***', '***REMOVED***');",
        )


def pytest_unconfigure(config):  # noqa: ARG001
    """
    Unconfigure pytest.

    if nexusLIMS_path is a subdirectory of the current tests directory
    (which it should be since we explicitly set it at the top of this file),
    remove it -- the  check for subdirectory is just a safety to make sure
    we don't nuke the real nexusLIMS_path. If we did that, we would
    have a bad time.
    """
    this_dir = Path(__file__).parent
    nx_dir = Path(os.getenv("nexusLIMS_path"))
    if this_dir in nx_dir.parents:
        records_dir = nx_dir / ".." / "records"
        if records_dir.exists():
            shutil.rmtree(records_dir)
        if nx_dir.exists():
            shutil.rmtree(nx_dir)


@pytest.fixture(scope="session")
def monkey_session():
    """Monkeypatch a whole Pytest session."""
    mpatch = MonkeyPatch()
    yield mpatch
    mpatch.undo()


@pytest.fixture(scope="session", name="_fix_mountain_time")
# pylint: disable=redefined-outer-name
def _fix_mountain_time(monkey_session):
    """
    Fix datetimes for MT/ET difference.

    Hack to determine if we need to adjust our datetime objects for the time
    difference between Boulder and G'burg.
    """
    import nexusLIMS.utils  # pylint: disable=import-outside-toplevel

    tz_string = current_system_tz().tzname(dt.now(tz=current_system_tz()))

    # if timezone is MST or MDT, we're 2 hours behind, so we need to adjust
    # datetime objects to match file store
    if tz_string in ["MST", "MDT"]:
        # get current timezone, and adjust tz_offset as needed
        monkey_session.setattr(nexusLIMS.utils, "tz_offset", td(hours=-2))
        monkey_session.setenv("ignore_mib", "True")
        monkey_session.setenv("is_mountain_time", "True")


@pytest.fixture(name="_cleanup_session_log")
def cleanup_session_log():
    """
    Cleanup the session log after a test.

    This fixture removes the rows for the usage event added in
    test_usage_event_to_session_log, so it doesn't mess up future record building tests.
    """
    # pylint: disable=import-outside-toplevel
    yield None
    from nexusLIMS.db.session_handler import db_query

    to_remove = (
        "https://***REMOVED***/api/usage_events/?id=29",
        "https://***REMOVED***/api/usage_events/?id=30",
        "https://***REMOVED***/api/usage_events/?id=31",
        "https://***REMOVED***/api/usage_events/?id=29",
        "https://***REMOVED***/api/usage_events/?id=30",
        "https://***REMOVED***/api/usage_events/?id=31",
        "https://***REMOVED***/api/usage_events/?id=385031",
        "test_session",
    )
    db_query(
        f"DELETE FROM session_log WHERE session_identifier IN "
        f'({",".join("?" * len(to_remove))})',
        to_remove,
    )


# test file fixtures


# 643 Titan files
@pytest.fixture(scope="module")
def eftem_diff_643():
    """643 Titan EFTEM example diffraction."""
    files = extract_files("643_EFTEM_DIFF")
    yield files
    delete_files("643_EFTEM_DIFF")


@pytest.fixture(scope="module")
def stem_stack_643():
    """643 Titan example STEM stack."""
    files = extract_files("643_STEM_STACK")
    yield files
    delete_files("643_STEM_STACK")


@pytest.fixture(scope="module")
def survey_643():
    """643 Titan example survey image."""
    files = extract_files("643_SURVEY")
    yield files
    delete_files("643_SURVEY")


@pytest.fixture(scope="module")
def eels_si_643():
    """643 Titan example EELS spectrum image."""
    files = extract_files("643_EELS_SI")
    yield files
    delete_files("643_EELS_SI")


@pytest.fixture(scope="module")
def eels_proc_int_bg_643():
    """643 Titan example EELS SI with processing integration and background removal."""
    files = extract_files("643_EELS_PROC_INT_BG")
    yield files
    delete_files("643_EELS_PROC_INT_BG")


@pytest.fixture(scope="module")
def eels_proc_thick_643():
    """643 Titan example EELS spectrum image with thickness calculation."""
    files = extract_files("643_EELS_PROC_THICK")
    yield files
    delete_files("643_EELS_PROC_THICK")


@pytest.fixture(scope="module")
def eds_si_643():
    """643 Titan example EDS spectrum image."""
    files = extract_files("643_EDS_SI")
    yield files
    delete_files("643_EDS_SI")


@pytest.fixture(scope="module")
def eels_si_drift_643():
    """643 Titan example EELS spectrum image with drift correction."""
    files = extract_files("643_EELS_SI_DRIFT")
    yield files
    delete_files("643_EELS_SI_DRIFT")


@pytest.fixture(scope="module")
def annotations_643():
    """643 Titan example image with annotations."""
    files = extract_files("642_ANNOTATIONS")
    yield files
    delete_files("642_ANNOTATIONS")


@pytest.fixture(scope="module")
def four_d_stem():
    """4D STEM example."""
    files = extract_files("4D_STEM")
    yield files
    delete_files("4D_STEM")


@pytest.fixture(scope="module")
def fft():
    """FFT example."""
    files = extract_files("FFT")
    yield files
    delete_files("FFT")


@pytest.fixture(scope="module")
def corrupted_file():
    """Corrupted dm3 file example."""
    files = extract_files("CORRUPTED")
    yield files
    delete_files("CORRUPTED")


# JEOL 3010 files


@pytest.fixture(scope="module")
def jeol3010_diff():
    """JEOL 3010 example diffraction image."""
    files = extract_files("JEOL3010_DIFF")
    yield files
    delete_files("JEOL3010_DIFF")


# 642 Titan files


@pytest.fixture(scope="module")
def stem_diff_642():
    """642 Titan STEM diffraction."""
    files = extract_files("642_STEM_DIFF")
    yield files
    delete_files("642_STEM_DIFF")


@pytest.fixture(scope="module")
def opmode_diff_642():
    """STEM diffraction (in operation mode) from 642 Titan."""
    files = extract_files("642_OPMODE_DIFF")
    yield files
    delete_files("642_OPMODE_DIFF")


@pytest.fixture(scope="module")
def eels_proc_1_642():
    """EELS processing metadata from 642 Titan."""
    files = extract_files("642_EELS_PROC_1")
    yield files
    delete_files("642_EELS_PROC_1")


@pytest.fixture(scope="module")
def eels_si_drift_642():
    """EELS SI drift correction metadata from 642 Titan."""
    files = extract_files("642_EELS_SI_DRIFT")
    yield files
    delete_files("642_EELS_SI_DRIFT")


@pytest.fixture(scope="module")
def tecnai_mag_642():
    """Tecnai magnification metadata from 642 Titan."""
    files = extract_files("642_TECNAI_MAG")
    yield files
    delete_files("642_TECNAI_MAG")


# Quanta tiff files


@pytest.fixture(scope="module")
def quanta_test_file():
    """Quanta example."""
    files = extract_files("QUANTA_TIF")
    yield files
    delete_files("QUANTA_TIF")


@pytest.fixture(scope="module")
def quanta_32bit_test_file():
    """Quanta 32 bit example."""
    files = extract_files("QUANTA_32BIT")
    yield files
    delete_files("QUANTA_32BIT")


@pytest.fixture(scope="module")
def quanta_no_beam_meta():
    """Quanta example with no beam, scan, or system metadata."""
    files = extract_files("QUANTA_NO_BEAM")
    yield files
    delete_files("QUANTA_NO_BEAM")


# other assorted files


@pytest.fixture(scope="module")
def parse_meta_642_titan():
    """642 Titan file for metadata parsing test."""
    files = extract_files("PARSE_META_642_TITAN")
    yield files
    delete_files("PARSE_META_642_TITAN")


@pytest.fixture(scope="module")
def list_signal():
    """Signal returning a signal list."""
    files = extract_files("LIST_SIGNAL")
    yield files
    delete_files("LIST_SIGNAL")


@pytest.fixture(scope="module")
def fei_ser_files():
    """FEI .ser/.emi test files."""
    files = extract_files("FEI_SER")
    yield files
    delete_files("FEI_SER")


@pytest.fixture()
def fei_ser_files_function_scope():
    """FEI .ser/.emi test files."""
    files = extract_files("FEI_SER")
    yield files
    delete_files("FEI_SER")


# plain test files (not in .tar.gz archives, so do not need to delete at end)


@pytest.fixture(scope="module")
def basic_txt_file():
    """Plain txt file for basic extractor test."""
    return Path(__file__).parent / "files" / "basic_test.txt"


@pytest.fixture(scope="module")
def basic_txt_file_no_extension():
    """Plain txt file with no extention for basic extractor test."""
    return Path(__file__).parent / "files" / "basic_test_no_extension"


@pytest.fixture(scope="module")
def stem_image_dm3():
    """Small dm3 file for zeroing data test."""
    return Path(__file__).parent / "files" / "test_STEM_image.dm3"


@pytest.fixture(scope="module")
def quanta_bad_metadata():
    """Quanta tif file with bad metadata."""
    return Path(__file__).parent / "files" / "quanta_bad_metadata.tif"


@pytest.fixture(scope="module")
def quanta_just_modded_mdata():
    """Quanta tif file with modified metadata."""
    return Path(__file__).parent / "files" / "quanta_just_modded_mdata.tif"


@pytest.fixture(scope="module")
def text_paragraph_test_file():
    """Text file imitating a natural language note to self."""
    return Path(__file__).parent / "files" / "text_preview_test_paragraph.txt"


@pytest.fixture(scope="module")
def text_data_test_file():
    """Text file imitating textual data output, e.g. column data."""
    return Path(__file__).parent / "files" / "text_preview_test_data.txt"


@pytest.fixture(scope="module")
def basic_image_file():
    """Image file that is not data, e.g. a screenshot."""
    extract_files("IMAGE_FILES")
    yield Path(__file__).parent / "files" / "test_image_thumb_source.bmp"
    delete_files("IMAGE_FILES")


@pytest.fixture(scope="module")
def image_thumb_source_gif():
    """Image file in GIF format for thumbnail testing."""
    extract_files("IMAGE_FILES")
    yield Path(__file__).parent / "files" / "test_image_thumb_source.gif"
    delete_files("IMAGE_FILES")


@pytest.fixture(scope="module")
def image_thumb_source_png():
    """Image file in PNG format for thumbnail testing."""
    extract_files("IMAGE_FILES")
    yield Path(__file__).parent / "files" / "test_image_thumb_source.png"
    delete_files("IMAGE_FILES")


@pytest.fixture(scope="module")
def image_thumb_source_tif():
    """Image file in TIF format for thumbnail testing."""
    extract_files("IMAGE_FILES")
    yield Path(__file__).parent / "files" / "test_image_thumb_source.tif"
    delete_files("IMAGE_FILES")


@pytest.fixture(scope="module")
def image_thumb_source_jpg():
    """Image file in JPG format for thumbnail testing."""
    extract_files("IMAGE_FILES")
    yield Path(__file__).parent / "files" / "test_image_thumb_source.jpg"
    delete_files("IMAGE_FILES")


@pytest.fixture(scope="module")
def unreadable_image_file():
    """File with a .jpg extension that is not readable as an image."""
    return Path(__file__).parent / "files" / "unreadable_image.jpg"


@pytest.fixture(scope="module")
def binary_text_file():
    """File with a .txt extension that is not readable as plaintext."""
    return Path(__file__).parent / "files" / "binary_text.txt"


# XML record test file


@pytest.fixture(scope="module")
def xml_record_file():
    """Test XML record."""
    files = extract_files("RECORD")
    yield files
    delete_files("RECORD")
