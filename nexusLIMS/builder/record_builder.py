#  NIST Public License - 2019
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
Builds NexusLIMS records.

Attributes
----------
XSD_PATH
    A string containing the path to the Nexus Experiment schema file,
    which is used to validate XML records built by this module
"""
import argparse
import logging
import os
import shutil
import sys
from datetime import datetime as dt
from datetime import timedelta as td
from importlib import import_module, util
from io import BytesIO
from pathlib import Path
from timeit import default_timer
from typing import List, Optional
from uuid import uuid4

from lxml import etree

from nexusLIMS import version
from nexusLIMS.cdcs import upload_record_files
from nexusLIMS.db.session_handler import Session, db_query, get_sessions_to_build
from nexusLIMS.extractors import extension_reader_map as ext_map
from nexusLIMS.harvesters import nemo, sharepoint_calendar
from nexusLIMS.harvesters.nemo import utils as nemo_utils
from nexusLIMS.harvesters.reservation_event import ReservationEvent
from nexusLIMS.schemas import activity
from nexusLIMS.schemas.activity import AcquisitionActivity, cluster_filelist_mtimes
from nexusLIMS.utils import (
    current_system_tz,
    find_files_by_mtime,
    gnu_find_files_by_mtime,
    has_delay_passed,
)

logger = logging.getLogger(__name__)
XSD_PATH: str = Path(activity.__file__).parent / "nexus-experiment.xsd"


def build_record(
    session: Session,
    sample_id: Optional[str] = None,
    *,
    generate_previews: bool = True,
) -> str:
    """
    Build a NexusLIMS XML record of an Experiment.

    Construct an XML document conforming to the NexusLIMS schema from a
    directory containing microscopy data files. Accepts either a
    :py:class:`~nexusLIMS.db.session_handler.Session` object or an Instrument
    and date range (for backwards compatibility). For calendar parsing,
    currently no logic is implemented for a query that returns multiple records.

    Parameters
    ----------
    session
        A :py:class:`~nexusLIMS.db.session_handler.Session` or ``None``. If
        a value is provided, ``instrument``, ``dt_from``, ``dt_to`` and ``user``
        will be ignored, and the values from the Session object will be used
        instead
    sample_id
        A unique identifier pointing to a sample identifier for data
        collected in this record. If None, a UUIDv4 will be generated
    generate_previews
        Whether to create the preview thumbnail images

    Returns
    -------
    xml_record : str
        A formatted string containing a well-formed and valid XML document
        for the data contained in the provided path
    """
    if sample_id is None:
        sample_id = str(uuid4())

    # setup XML namespaces
    nx_namespace = "https://data.nist.gov/od/dm/nexus/experiment/v1.0"
    xsi_namespace = "http://www.w3.org/2001/XMLSchema-instance"
    ns_map = {None: nx_namespace, "xsi": xsi_namespace, "nx": nx_namespace}
    xml = etree.Element("Experiment", nsmap=ns_map)

    logger.info(
        "Getting calendar events with instrument: %s, from %s to %s, "
        "user: %s; using harvester: %s",
        session.instrument.name,
        session.dt_from.isoformat(),
        session.dt_to.isoformat(),
        session.user,
        session.instrument.harvester,
    )
    # this returns a nexusLIMS.harvesters.reservation_event.ReservationEvent
    res_event = get_reservation_event(session)

    output = res_event.as_xml()

    for child in output:
        xml.append(child)

    logger.info(
        "Building acquisition activities for timespan from %s to %s",
        session.dt_from.isoformat(),
        session.dt_to.isoformat(),
    )
    activities = build_acq_activities(
        session.instrument,
        session.dt_from,
        session.dt_to,
        generate_previews,
    )
    for i, this_activity in enumerate(activities):
        a_xml = this_activity.as_xml(i, sample_id)
        xml.append(a_xml)

    return etree.tostring(
        xml,
        xml_declaration=True,
        encoding="UTF-8",
        pretty_print=True,
    ).decode()


def get_reservation_event(session: Session) -> ReservationEvent:
    """
    Get a ReservationEvent representation of a Session.

    Handles the abstraction of choosing the right "version" of the
    ``res_event_from_session`` method from the harvester specified in the
    instrument database. This allows for one consistent function name to call
    a different method depending on which harvester is specified for each
    instrument (currently just NEMO or Sharepoint).

    Parameters
    ----------
    session
        The :py:class:`~nexusLIMS.db.session_handler.Session` for which to
        fetch a matching
        :py:class:`~nexusLIMS.harvesters.reservation_event.ReservationEvent` from
        the relevant harvester

    Returns
    -------
    res_event : ~nexusLIMS.harvesters.reservation_event.ReservationEvent
        A :py:class:`~nexusLIMS.harvesters.reservation_event.ReservationEvent`
        representation of a reservation that matches the instrument and timespan
        specified in ``session``.
    """
    # try to find module and raise error if not found:
    if (
        util.find_spec(f".{session.instrument.harvester}", "nexusLIMS.harvesters")
        is None
    ):
        msg = (
            f"Harvester {session.instrument.harvester} not found in "
            "nexusLIMS.harvesters"
        )
        raise NotImplementedError(msg)

    # use import_module to choose the correct harvester based on the instrument
    harvester = import_module(
        f".{session.instrument.harvester}",
        "nexusLIMS.harvesters",
    )
    # for PyCharm typing, explicitly specify what modules may be in `harvester`
    # harvester: Union[nemo, sharepoint_calendar]  # noqa: ERA001
    # DONE: check if that method exists for the given harvester and raise
    #  NotImplementedError if not
    if not hasattr(harvester, "res_event_from_session"):
        msg = (
            f"res_event_from_session has not been implemented for {harvester}, which "
            f"is required to use this method."
        )
        raise NotImplementedError(msg)

    return harvester.res_event_from_session(session)


def build_acq_activities(instrument, dt_from, dt_to, generate_previews):
    """
    Build an XML string representation of each AcquisitionActivity for a session.

    This includes setup parameters and metadata
    associated with each dataset obtained during a microscopy session. Unique
    AcquisitionActivities are delimited via clustering of file collection
    time to detect "long" breaks during a session.

    Parameters
    ----------
    instrument : :py:class:`~nexusLIMS.instruments.Instrument`
        One of the NexusLIMS instruments contained in the
        :py:attr:`~nexusLIMS.instruments.instrument_db` database.
        Controls what instrument calendar is used to get events.
    dt_from : datetime.datetime
        The starting timestamp that will be used to determine which files go
        in this record
    dt_to : datetime.datetime
        The ending timestamp used to determine the last point in time for
        which files should be associated with this record
    generate_previews : bool
        Whether or not to create the preview thumbnail images

    Returns
    -------
    activities : :obj:`list` of
    :obj:`~nexusLIMS.schemas.activity.AcquisitionActivity`:
        The list of :py:class:`~nexusLIMS.schemas.activity.AcquisitionActivity`
        objects generated for the record
    """
    logging.getLogger("hyperspy.io_plugins.digital_micrograph").setLevel(
        logging.WARNING,
    )

    start_timer = default_timer()
    path = Path(os.environ["mmfnexus_path"]) / instrument.filestore_path

    # find the files to be included (list of Paths)
    files = get_files(path, dt_from, dt_to)

    logger.info(
        "Found %i files in %.2f seconds",
        len(files),
        default_timer() - start_timer,
    )

    # raise error if no file found were found
    if len(files) == 0:
        msg = "No files found in this time range"
        raise FileNotFoundError(msg)

    # get the timestamp boundaries of acquisition activities
    aa_bounds = cluster_filelist_mtimes(files)

    # add the last file's modification time to the boundaries list to make
    # the loop below easier to process
    aa_bounds.append(files[-1].stat().st_mtime)

    activities: List[Optional[AcquisitionActivity]] = [None] * len(aa_bounds)

    i = 0
    aa_idx = 0
    while i < len(files):
        f = files[i]
        mtime = f.stat().st_mtime

        # check this file's mtime, if it is less than this iteration's value
        # in the AA bounds, then it belongs to this iteration's AA
        # if not, then we should move to the next activity
        if mtime <= aa_bounds[aa_idx]:
            # if current activity index is None, we need to start a new AA:
            if activities[aa_idx] is None:
                activities[aa_idx] = AcquisitionActivity(
                    start=dt.fromtimestamp(mtime, tz=instrument.timezone),
                )

            # add this file to the AA
            logger.info(
                "Adding file %i/%i %s to activity %i",
                i,
                len(files),
                str(f).replace(os.environ["mmfnexus_path"], "").strip("/"),
                aa_idx,
            )
            activities[aa_idx].add_file(fname=f, generate_preview=generate_previews)
            # assume this file is the last one in the activity (this will be
            # true on the last iteration where mtime is <= to the
            # aa_bounds value)
            activities[aa_idx].end = dt.fromtimestamp(mtime, tz=instrument.timezone)
            i += 1
        else:
            # this file's mtime is after the boundary and is thus part of the
            # next activity, so increment AA counter and reprocess file (do
            # not increment i)
            aa_idx += 1

    # Remove any "None" activities from list
    activities: List[AcquisitionActivity] = [a for a in activities if a is not None]

    logger.info("Finished detecting activities")
    for i, this_activity in enumerate(activities):
        logger.info("Activity %i: storing setup parameters", i)
        this_activity.store_setup_params()
        logger.info("Activity %i: storing unique metadata values", i)
        this_activity.store_unique_metadata()

    return activities


def get_files(
    path: Path,
    dt_from: dt,
    dt_to: dt,
) -> List[Path]:
    """
    Get files under a path that were last modified between the two given timestamps.

    Parameters
    ----------
    path
        The file path in which to search for files
    dt_from : datetime.datetime
        The starting timestamp that will be used to determine which files go
        in this record
    dt_to : datetime.datetime
        The ending timestamp used to determine the last point in time for
        which files should be associated with this record

    Returns
    -------
    files : List[pathlib.Path]
        A list of the files that have modification times within the
        time range provided (sorted by modification time)
    """
    logger.info("Starting new file-finding in %s", path)

    # read file finding strategy from environment and set to default of exclusive
    strategy = os.environ.get("NexusLIMS_file_strategy", default="exclusive").lower()
    if strategy not in ["inclusive", "exclusive"]:
        logger.warning(
            'File finding strategy (env variable "NexusLIMS_file_strategy") had '
            'an unexpected value: "%s". Setting value to "exclusive".',
            strategy,
        )
        strategy = "exclusive"

    extension_arg = None if strategy == "inclusive" else ext_map.keys()

    try:
        files = gnu_find_files_by_mtime(path, dt_from, dt_to, extensions=extension_arg)

    # exclude following from coverage because find_files_by_mtime is deprecated as of
    # 1.2.0 and does not support extensions at all (like the above method)
    except (NotImplementedError, RuntimeError) as exception:  # pragma: no cover
        logger.warning(
            "GNU find returned error: %s\nFalling back to pure Python implementation",
            exception,
        )
        files = find_files_by_mtime(path, dt_from, dt_to)
    return files


def dump_record(
    session: Session,
    filename: Optional[Path] = None,
    *,
    generate_previews: bool = True,
) -> Path:
    """
    Dump a record to an XML file.

    Writes an XML record for a :py:class:`~nexusLIMS.db.session_handler.Session`
    composed of information pulled from the appropriate reservation system
    as well as metadata extracted from the microscope data (e.g. dm3 or
    other files).

    Parameters
    ----------
    session : nexusLIMS.db.session_handler.Session
        A :py:class:`~nexusLIMS.db.session_handler.Session` object
        representing a unit of time on one of the instruments known to NexusLIMS
    filename : typing.Optional[pathlib.Path]
        The filename of the dumped xml file to write. If None, a default name
        will be generated from the other parameters
    generate_previews : bool
        Whether or not to create the preview thumbnail images

    Returns
    -------
    filename : pathlib.Path
        The name of the created record that was returned
    """
    if filename is None:
        filename = Path(
            "compiled_record"
            + (f"_{session.instrument.name}" if session.instrument else "")
            + session.dt_from.strftime("_%Y-%m-%d")
            + (f"_{session.user}" if session.user else "")
            + ".xml",
        )
    filename.parent.mkdir(parents=True, exist_ok=True)
    with filename.open(mode="w", encoding="utf-8") as f:
        text = build_record(session=session, generate_previews=generate_previews)
        f.write(text)
    return filename


def validate_record(xml_filename):
    """
    Validate an .xml record against the Nexus schema.

    Parameters
    ----------
    xml_filename : str or io.StringIO or io.BytesIO
        The path to the xml file to be validated (can also be a file-like
        object like StringIO or BytesIO)

    Returns
    -------
    validates : bool
        Whether the record validates against the Nexus schema
    """
    xsd_doc = etree.parse(XSD_PATH)  # noqa: S320
    xml_schema = etree.XMLSchema(xsd_doc)
    xml_doc = etree.parse(xml_filename)  # noqa: S320

    return xml_schema.validate(xml_doc)


def build_new_session_records() -> List[Path]:
    """
    Build records for new sessions from the database.

    Uses :py:func:`~nexusLIMS.db.session_handler.get_sessions_to_build`) and builds
    those records using :py:func:`build_record` (saving to the NexusLIMS folder), and
    returns a list of resulting .xml files to be uploaded to CDCS.

    Returns
    -------
    xml_files : typing.List[pathlib.Path]
        A list of record files that were successfully built and saved to
        centralized storage
    """
    # get the list of sessions with 'TO_BE_BUILT' status; does not fetch new
    # usage events from any NEMO instances;
    # nexusLIMS.harvesters.nemo.add_all_usage_events_to_db() must be used
    # first to do so
    sessions = get_sessions_to_build()
    if not sessions:
        sys.exit("No 'TO_BE_BUILT' sessions were found. Exiting.")
    xml_files = []
    # loop through the sessions
    for s in sessions:
        try:
            db_row = s.insert_record_generation_event()
            record_text = build_record(session=s)
        except (  # pylint: disable=broad-exception-caught
            FileNotFoundError,
            Exception,
        ) as exception:
            if isinstance(exception, FileNotFoundError):
                # if no files were found for this session log, mark it as so in
                # the database
                path = Path(os.environ["mmfnexus_path"]) / s.instrument.filestore_path
                logger.warning(
                    "No files found in %s between %s and %s",
                    path,
                    s.dt_from.isoformat(),
                    s.dt_to.isoformat(),
                )

                if has_delay_passed(s.dt_to):
                    logger.warning(
                        'Marking %s as "NO_FILES_FOUND"',
                        s.session_identifier,
                    )
                    s.update_session_status("NO_FILES_FOUND")
                else:
                    # if the delay hasn't passed, log and delete the record
                    # generation event we inserted previously
                    logger.warning(
                        "Configured record building delay has not passed; "
                        "Removing previously inserted RECORD_GENERATION row for %s",
                        s.session_identifier,
                    )
                    db_query(
                        "DELETE FROM session_log WHERE id_session_log = ?",
                        (  # pylint: disable=used-before-assignment
                            db_row["id_session_log"],
                        ),
                    )
            elif isinstance(exception, nemo.exceptions.NoDataConsentError):
                logger.warning(
                    "User requested this session not be harvested, "
                    "so no record was built. %s",
                    exception,
                )
                logger.info('Marking %s as "NO_CONSENT"', s.session_identifier)
                s.update_session_status("NO_CONSENT")
            elif isinstance(exception, nemo.exceptions.NoMatchingReservationError):
                logger.warning(
                    "No matching reservation found for this session, "
                    "so assuming no consent was given. %s",
                    exception,
                )
                logger.info('Marking %s as "NO_RESERVATION"', s.session_identifier)
                s.update_session_status("NO_RESERVATION")
            else:
                logger.exception("Could not generate record text")
                logger.exception('Marking %s as "ERROR"', s.session_identifier)
                s.update_session_status("ERROR")
        else:
            xml_files = _record_validation_flow(record_text, s, xml_files)

    return xml_files


def _record_validation_flow(record_text, s, xml_files) -> List[Path]:
    if validate_record(BytesIO(bytes(record_text, "UTF-8"))):
        logger.info("Validated newly generated record")
        # generate filename for saved record and make sure path exists
        # DONE: fix this for NEMO records since session_identifier is
        #  a URL and it doesn't work right
        if s.instrument.harvester == "nemo":
            # for NEMO session_identifier is a URL of usage_event
            unique_suffix = f"{nemo_utils.id_from_url(s.session_identifier)}"
        else:  # pragma: no cover
            # assume session_identifier is a UUID
            unique_suffix = f'{s.session_identifier.split("-")[0]}'
        basename = (
            f'{s.dt_from.strftime("%Y-%m-%d")}_'
            f"{s.instrument.name}_"
            f"{unique_suffix}.xml"
        )
        filename = Path(os.environ["nexusLIMS_path"]).parent / "records" / basename
        filename.parent.mkdir(parents=True, exist_ok=True)
        # write the record to disk and append to list of files generated
        with filename.open(mode="w", encoding="utf-8") as f:
            f.write(record_text)
        logger.info("Wrote record to %s", filename)
        xml_files.append(Path(filename))
        # Mark this session as completed in the database
        logger.info('Marking %s as "COMPLETED"', s.session_identifier)
        s.update_session_status("COMPLETED")
    else:
        logger.error('Marking %s as "ERROR"', s.session_identifier)
        logger.error("Could not validate record, did not write to disk")
        s.update_session_status("ERROR")
    return xml_files


def process_new_records(
    *,
    dry_run: bool = False,
    dt_from: Optional[dt] = None,
    dt_to: Optional[dt] = None,
):
    """
    Process new records (this is the main entrypoint to the record builder).

    Using :py:meth:`build_new_session_records()`, process new records,
    save them to disk, and upload them to the NexusLIMS CDCS instance.

    Parameters
    ----------
    dry_run
        Controls whether or not records will actually be built. If ``True``,
        session harvesting and file finding will be performed, but no preview
        images or records will be built. Can be used to see what _would_ happen
        if ``dry_run`` is set to ``False``.
    dt_from
        The point in time after which sessions will be fetched. If ``None``,
        no date filtering will be performed. This parameter currently only
        has an effect for the NEMO harvester. All SharePoint events will always
        be fetched.
    dt_to
        The point in time before which sessions will be fetched. If ``None``,
        no date filtering will be performed. This parameter currently only
        has an effect for the NEMO harvester. All SharePoint events will always
        be fetched.
    """
    if dry_run:
        logger.info("!!DRY RUN!! Only finding files, not building records")
        # get 'TO_BE_BUILT' sessions from the database
        sessions = get_sessions_to_build()
        # get Session objects for NEMO usage events without adding to DB
        # DONE: NEMO usage events fetched should take a time range;
        sessions += nemo_utils.get_usage_events_as_sessions(
            dt_from=dt_from,
            dt_to=dt_to,
        )
        if not sessions:
            logger.warning("No 'TO_BE_BUILT' sessions were found. Exiting.")
            return
        for s in sessions:
            # at this point, sessions can be from any type of harvester
            logger.info("")
            logger.info("")
            # DONE: generalize this from just sharepoint to any harvester
            #       (prob. new function that takes session and determines
            #       where it came from and then gets the matching reservation
            #       event)
            get_reservation_event(s)
            dry_run_file_find(s)
    else:
        # DONE: NEMO usage events fetcher should take a time range; we also
        #  need a consistent response for testing
        nemo_utils.add_all_usage_events_to_db(dt_from=dt_from, dt_to=dt_to)
        xml_files = build_new_session_records()
        if len(xml_files) == 0:
            logger.warning("No XML files built, so no files uploaded")
        else:
            files_uploaded, _ = upload_record_files(xml_files)
            for f in files_uploaded:
                uploaded_dir = Path(f).parent / "uploaded"
                Path(uploaded_dir).mkdir(parents=True, exist_ok=True)

                shutil.copy2(f, uploaded_dir)
                Path(f).unlink()
            files_not_uploaded = [f for f in xml_files if f not in files_uploaded]

            if len(files_not_uploaded) > 0:
                logger.error(
                    "Some record files were not uploaded: %s",
                    files_not_uploaded,
                )
    return


def dry_run_get_sharepoint_reservation_event(
    s: Session,
) -> ReservationEvent:  # pragma: no cover
    """
    Get the calendar event that *would* be used based off the supplied session.

    Only implemented for the Sharepoint harvester.

    Parameters
    ----------
    s
        A session read from the database

    Returns
    -------
    res_event : ~nexusLIMS.harvesters.reservation_event.ReservationEvent
        A list of strings containing the files that would be included for the
        record of this session (if it were not a dry run)
    """
    xml = sharepoint_calendar.fetch_xml(s.instrument, s.dt_from, s.dt_to)
    res_event = sharepoint_calendar.res_event_from_xml(xml)
    logger.info(res_event)
    return res_event


def dry_run_file_find(s: Session) -> List[Path]:
    """
    Get the files that *would* be included for a record built for the supplied session.

    Parameters
    ----------
    s : nexusLIMS.db.session_handler.Session
        A session read from the database

    Returns
    -------
    files : typing.List[pathlib.Path]
        A list of Paths containing the files that would be included for the
        record of this session (if it were not a dry run)
    """
    path = Path(os.environ["mmfnexus_path"]) / s.instrument.filestore_path
    logger.info(
        "Searching for files for %s in %s between %s and %s",
        s.instrument.name,
        path,
        s.dt_from.isoformat(),
        s.dt_to.isoformat(),
    )
    files = get_files(path, s.dt_from, s.dt_to)

    logger.info("Results for %s on %s:", s.session_identifier, s.instrument)
    if len(files) == 0:
        logger.warning("No files found for this session")
    else:
        logger.info("Found %i files for this session", len(files))
    for f in files:
        mtime = dt.fromtimestamp(
            f.stat().st_mtime,
            tz=s.instrument.timezone,
        ).isoformat()
        logger.info("*mtime* %s - %s", mtime, f)
    return files


if __name__ == "__main__":  # pragma: no cover
    # If running as a module, process new records (with some control flags)
    from nexusLIMS.utils import setup_loggers

    parser = argparse.ArgumentParser()

    # Optional argument flag which defaults to False
    parser.add_argument(
        "-n",
        "--dry-run",
        action="store_true",
        dest="dry_run",
        default=False,
    )

    # Optional verbosity counter (eg. -v, -vv, -vvv, etc.)
    parser.add_argument(
        "-v",
        "--verbose",
        action="count",
        default=0,
        help="Verbosity (-v, -vv); corresponds to python logging level. "
        "0 is WARN, 1 (-v) is INFO, 2 (-vv) is DEBUG. ERROR and "
        "CRITICAL are always shown.",
    )

    # Specify output of "--version"
    parser.add_argument(
        "--version",
        action="version",
        version=f"%(prog)s (version {version})",
    )

    args = parser.parse_args()

    # set up logging
    logging_levels = {0: logging.WARNING, 1: logging.INFO, 2: logging.DEBUG}

    if args.dry_run and args.verbose <= 0:
        logger.warning('Increasing verbosity so output of "dry-run" will be shown')
        args.verbose = 1

    setup_loggers(logging_levels[args.verbose])
    # when running as script, __name__ is "__main__", so we need to set level
    # explicitly since the setup_loggers function won't find it
    logger.setLevel(logging_levels[args.verbose])

    # by default only fetch the last week's worth of data from the NEMO
    # harvesters to speed things up
    process_new_records(
        dry_run=args.dry_run,
        dt_from=dt.now(tz=current_system_tz()) - td(weeks=1),
    )
