.. _record-building:

Record building workflow
========================

    `Last updated: February 18, 2020`

This page describes the process used to build records based on the data
saved by instruments in the Electron Microscopy Nexus facility using NexusLIMS.
At the bottom is an `activity diagram <activity-diagram_>`_ that illustrates
how the different modules work together to generate records from the centralized
file storage and the NexusLIMS session database. Throughout this page, links
are made to the `API Documentation <api.html>`_ as appropriate for further
detail about the methods and classes used during record generation.

General Approach
++++++++++++++++

Because the instruments cannot communicate directly with the NexusLIMS backend,
we utilize a polling approach to detect when a new record should be built.
The process described on this page happens periodically (using a system
scheduling tool such as ``systemd`` or ``cron``).
The record builder begins by running
``python -m nexusLIMS.builder.record_builder``, which will run the
:py:func:`~nexusLIMS.builder.record_builder.process_new_records` function. This
function initiates one iteration of the record builder, which will query the
NexusLIMS database for any sessions that are waiting to have their record built
and then proceed to build them and upload them to the NexusLIMS CDCS instance.
As part of this process (and explained in detail below), the centralized file
system is searched for files matching the session logs in the database, which
then have their metadata extracted and are parsed into `Acquisition Activities`.
These activities are written to the .xml record, which is validated against the
Nexus Microscopy Schema, and finally uploaded to the
`NexusLIMS CDCS instance <https://***REMOVED***>`_ if everything goes
according to plan. If not, an error is logged to the database for that session
and the operators of NexusLIMS are notified so the issue can be corrected.

Finding New Sessions
++++++++++++++++++++

The session finding is initiated by
:py:func:`~nexusLIMS.builder.record_builder.process_new_records`, which
immediately calls
:py:func:`~nexusLIMS.builder.record_builder.build_new_session_records`, which in
turn uses :py:func:`~nexusLIMS.db.session_handler.get_sessions_to_build` to
query the NexusLIMS database for sessions awaiting processing (the database
location can be referenced within the code as
:py:data:`~nexusLIMS.nexuslims_db_path`). This method interrogates the database
for session logs with a status of ``TO_BE_BUILT`` using the query:

.. code-block:: sql

    SELECT (session_identifier, instrument, timestamp, event_type, user)
    FROM session_log WHERE record_status == 'TO_BE_BUILT';

The results of this query are stored as
:py:class:`~nexusLIMS.db.session_handler.SessionLog` objects, which are then
combined into :py:class:`~nexusLIMS.db.session_handler.Session` objects by
finding ``START`` and ``END`` logs with the same ``session_identifier`` value.
The method returns a list of :py:class:`~nexusLIMS.db.session_handler.Session`
objects to the record builder, which are processed one at a time.

Building a Single Record
++++++++++++++++++++++++

With the list of :py:class:`~nexusLIMS.db.session_handler.Session` instances
returned by :py:func:`~nexusLIMS.db.session_handler.get_sessions_to_build`, the
code then loops through each :py:class:`~nexusLIMS.db.session_handler.Session`,
executing a number of steps at each iteration (which are expanded upon below).

Overview
^^^^^^^^

1.  `(link) <starting-record-builder_>`_
    Execute :py:func:`~nexusLIMS.builder.record_builder.build_record` for the
    instrument and time range specified by the
    :py:class:`~nexusLIMS.db.session_handler.Session`
2.  `(link) <querying-sharepoint_>`_
    Fetch any associated calendar information for this
    :py:class:`~nexusLIMS.db.session_handler.Session` using
    :py:func:`~nexusLIMS.harvester.sharepoint_calendar.get_events`
3.  `(link) <identifying-files_>`_
    Identify files that NexusLIMS knows how to parse within the time range using
    :py:func:`~nexusLIMS.utils.find_files_by_mtime`; if no files are found,
    mark the session as ``NO_FILES_FOUND`` in the database using
    :py:meth:`~nexusLIMS.db.session_handler.Session.update_session_status` and
    continue with step 1 for the next
    :py:class:`~nexusLIMS.db.session_handler.Session` in the list.
4.  `(link) <build-activities_>`_
    Separate the files into discrete activities (represented by
    :py:class:`~nexusLIMS.schemas.activity.AcquisitionActivity`) by inferring
    logical breaks in the file's acquisition times using
    :py:func:`~nexusLIMS.schemas.activity.cluster_filelist_mtimes`.
5.  `(link) <parse-metadata_>`_
    For each file, add it to the appropriate activity using
    :py:meth:`~nexusLIMS.schemas.activity.AcquisitionActivity.add_file`, which
    in turn uses :py:func:`~nexusLIMS.extractors.parse_metadata` to extract
    known metadata and :py:mod:`~nexusLIMS.extractors.thumbnail_generator` to
    generate a web-accessible preview image of the dataset. These files are
    saved within the :py:data:`~nexusLIMS.nexuslims_root_path` directory.
6.  `(link) <separate-setup-parameters_>`_
    Once all the individual files have been processed, their metadata is
    inspected and any values that are common to all files are assigned as
    :py:class:`~nexusLIMS.schemas.activity.AcquisitionActivity`
    `Setup Parameters`, while unique values are left associated with the
    individual files.
7.  `(link) <validating-the-record_>`_
    After all activities are processed and exported to XML, the records are
    validated against the schema using
    :py:func:`~nexusLIMS.builder.record_builder.validate_record`.
8.  `(link) <upload-records_>`_
    Any records created are uploaded to the NexusLIMS CDCS instance using
    :py:func:`~nexusLIMS.cdcs.upload_record_files`

.. _starting-record-builder:

Initiating :py:func:`~nexusLIMS.builder.record_builder.build_record`
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Prior to calling :py:func:`~nexusLIMS.builder.record_builder.build_record` for
a given :py:class:`~nexusLIMS.db.session_handler.Session`,
:py:meth:`~nexusLIMS.db.session_handler.Session.insert_record_generation_event`
is called for the :py:class:`~nexusLIMS.db.session_handler.Session` to insert a
log into the database that a record building attempt was made. This is done
to fully document all actions taken by NexusLIMS.

After this log is inserted into the database,
:py:func:`~nexusLIMS.builder.record_builder.build_record` is called using the
:py:class:`~nexusLIMS.instruments.Instrument` and timestamps associated with
the given :py:class:`~nexusLIMS.db.session_handler.Session`. The code
begins the record by writing basic XML header information before querying the
reservation system for additional information about the experiment.

.. _querying-sharepoint:

Querying the SharePoint Calendar
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Since users must make reservations on the SharePoint calendar, this is an
important source of metadata for the experimental records created by NexusLIMS.
Information from these calendar "events" is included throughout the record,
although it primarily informs the information contained in the ``<summary>``
element, including information such as who made the reservation, what the
experiment's motivation was, what sample was examined, etc.

To obtain this information, the
:py:func:`~nexusLIMS.harvester.sharepoint_calendar.get_events` function from the
:py:mod:`~nexusLIMS.harvester.sharepoint_calendar` harvester module is used.
This function authenticates to and queries the SharePoint API, and receives
an XML response representing any reservations found that match the timespan of
the :py:class:`~nexusLIMS.db.session_handler.Session`. This XML is then
translated using the XSLT file (path specified by
:py:data:`~nexusLIMS.builder.record_builder.XSLT_PATH`) into a format that is
compatible with the Nexus Microscopy Schema. This result is added to the XML
representation of the current record.

If no matching events are found, some basic details are added to the
``<summary>`` section of the record using the information that can be accessed,
such as the instrument the Experiment was performed on, as well as the date and
time.

.. _identifying-files:

Identifying Files to Include
^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. _build-activities:

Separating Acquisition Activities
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. _parse-metadata:

Parsing Individual Files' Metadata
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. _separate-setup-parameters:

Determining Setup Parameters
^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. _validating-the-record:

Validating the Built Records
^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. _upload-records:

Uploading Completed Records
^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. _activity-diagram:

Record Generation Diagram
+++++++++++++++++++++++++

The following diagram illustrates the logic (described above) that is used to
generate ``Experiment`` records and upload them to the NexusLIMS CDCS instance.
To better inspect the diagram, right click the image and select
"View Image", "Open image in new tab", or the equivalent option in your browser
to be able to zoom and pan.

The diagram should be fairly self-explanatory, but in general: the green dot
represents the start of the record builder code, and any red dots represent a
possible ending point (depending on the conditions found during operation). The
different columns represent the parts of the process that occur in different
modules/sub-packages within the ``nexusLIMS`` package. In general, the diagram
can be read by simply following the arrows. The only exception is for the orange
boxes, which indicate a jump to the other orange box in the bottom left,
representing when an individual session is updated in the database.

.. uml:: diagrams/record_building.plantuml