NexusLIMS database
==================

    `Last updated: June 13, 2022`

In order to accurately know an Experimental session has occurred (and a record
needs to be built) NexusLIMS relies on an external database that is stored
as a file accessible to the back-end. Due to its simple design and requirements,
the database is implemented using a single `SQLite <https://sqlite.org/index.html>`_
file stored in a location specified by the
:ref:`nexusLIMS_db_path <nexuslims-db-path>` environment variable. This database
is created using a custom |SQLSchemaLink|_ (documented below) and can be
easily backed up by simply copying the database file to a new location.
The contents and structure of the database can be inspected using a number
of open source tools, including the cross-platform software
`DB Browser for SQLite <https://sqlitebrowser.org/>`_.

This database fulfills two primary purposes (in its current implementation).
First, it serves as a location entries related to when
a user has started and finished an Experiment on an instrument, as well as
when the back-end has attempted (and completed) building a record based on that
Experiment (these entries are made by either the deprecated Session Logger app, or
one of the more modern harvester modules, such as py:mod:`~nexusLIMS.harvesters.nemo`.
The second purpose is to contain authoritative information about
the instruments in the facility, such as the instruments'
names, their reservation URLs, where a given instrument stores its data, etc.
Having this information centrally located facilitates maintenance in the event
the configuration changes in the future. These two sources of data are
represented as two `tables` within the database named `session_log` and
`instruments`, respectively. Specific documentation of each table and their
data columns are provided below.


The ``session_log`` table
+++++++++++++++++++++++++

As described above, the ``session_log`` table is where the instruments (and the
NexusLIMS back-end) store information that is used to determine what records
need to be built and which files should be included in a given record (see the
:doc:`record building <record_building>` documentation for more details).
Each row of this table represents a single timestamped log of a certain type of
event. If the deprecated :doc:`Session Logger App <session_logger_app>` is in use,
users (perhaps without realizing it) write to this table when they start the on an
instrument at the beginning of their session, and again when they click the `"End Session"`
button or close the application at the end of their experiment. Otherwise, the reservation
and usage event harvester code (such as :doc:`Session Logger App <session_logger_app>`) parses
the API response from the reservation system and adds rows to the ``session_log`` table
as required to represent an experiment on a particular instrument.

Together, these `"START"` and `"END"` logs (linked by a ``session_identifier``) represent a unit
of time on a given instrument, and indicate to the NexusLIMS back-end
that a record needs to be built for that instrument, containing files created
between the starting and ending timestamps. The back-end periodically polls
this database table for any logs with a status of `"TO_BE_BUILT"`, and fires off
the :doc:`record building <record_building>` process if any are found.
Upon completion of record building, the back-end updates the ``record_status``
of these logs as needed so that duplicate records are not created. The back-end
then continues polling the database indefinitely for any new sessions that need
to be built.

The following is a detailed description of the columns contained in the
``session_log`` table, their data types, and how they are used/constraints
placed on their values:

+------------------------+--------------+-------------------------------------+
|         Column         |  Data type   |             Description             |
+========================+==============+=====================================+
| ``id_session_log``     | INTEGER      | The auto-incrementing primary key   |
|                        |              | identifier for this table (just a   |
|                        |              | generic number).                    |
|                        |              |                                     |
|                        |              | `Checks:` must not be `NULL`        |
+------------------------+--------------+-------------------------------------+
| ``session_identifier`` | VARCHAR(36)  | A unique string (could be a UUID)   |
|                        |              | that is consistent among a single   |
|                        |              | record's `"START"`, `"END"`, and    |
|                        |              | `"RECORD_GENERATION"` events.       |
|                        |              |                                     |
|                        |              | `Checks:` must not be `NULL`        |
+------------------------+--------------+-------------------------------------+
| ``instrument``         | VARCHAR(100) | The instrument PID associated with  |
|                        |              | this session (this value is a       |
|                        |              | foreign key reference to the        |
|                        |              | ``instruments`` table).             |
|                        |              |                                     |
|                        |              | `Checks:` value must be one of      |
|                        |              | those from the ``instrument_pid``   |
|                        |              | column of the |instr-table|_        |
|                        |              | table.                              |
+------------------------+--------------+-------------------------------------+
| ``timestamp``          | DATETIME     | The date and time of the            |
|                        |              | logged event in ISO timestamp       |
|                        |              | format.                             |
|                        |              |                                     |
|                        |              | `Default:`                          |
|                        |              | ``strftime('%Y-%m-%dT%H:%M:%f',     |
|                        |              | 'now', 'localtime')``               |
|                        |              |                                     |
|                        |              | `Checks:` must not be `NULL`        |
+------------------------+--------------+-------------------------------------+
| ``event_type``         | TEXT         | The type of log for this session.   |
|                        |              |                                     |
|                        |              | `Checks:` must be one of            |
|                        |              | `"START"`, `"END"`, or              |
|                        |              | `"RECORD_GENERATION"`.              |
+------------------------+--------------+-------------------------------------+
| ``record_status``      | TEXT         | The status of the record            |
|                        |              | associated with this session.       |
|                        |              | This value will be updated after    |
|                        |              | a record is built for a given       |
|                        |              | session.                            |
|                        |              |                                     |
|                        |              | `Default:`                          |
|                        |              | `"WAITING_FOR_END"`                 |
|                        |              |                                     |
|                        |              | `Checks:` must be one of            |
|                        |              | `"WAITING_FOR_END"` (session has a  |
|                        |              | start event, but no end event),     |
|                        |              | `"TO_BE_BUILT"` (session has ended, |
|                        |              | but record not yet built),          |
|                        |              | `"COMPLETED"` (record has been      |
|                        |              | built successfully), `"ERROR"`      |
|                        |              | (some error happened during         |
|                        |              | record generation), or              |
|                        |              | `"NO_FILES_FOUND"` (record          |
|                        |              | generation occurred, but no files   |
|                        |              | matched time span)                  |
+------------------------+--------------+-------------------------------------+
| ``user``               | VARCHAR(50)  | A username associated with this     |
|                        |              | session (if known) -- this value    |
|                        |              | is not currently used by the        |
|                        |              | back-end since it is not reliable   |
|                        |              | across different instruments.       |
+------------------------+--------------+-------------------------------------+

.. |instr-table| replace:: ``instruments``
.. _instr-table:

The ``instruments`` table
+++++++++++++++++++++++++

This table serves as the authoritative data source for the NexusLIMS back-end
regarding information about the instruments in the Nexus Facility. By locating
this information in an external database, changes to instrument configuration
(or addition of a new instrument) requires making adjustments to just one
location, simplifying maintenance of the system. For example, when the
SharePoint calendar system version was transitioned from 2010 to 2016, the
calendar URLs changed, but after a simple update to the entries in this table,
the existing back-end code continued working with no other changes needed.

Likewise, when the Nexus facility migrated from the SharePoint-based reservation
system to the NEMO-based one, reconfiguring the instruments was as simple as
adding a duplicate row for each instrument with a different ``harvester`` value
and the new API endpoint location for that instrument.

**Back-end implementation details**

When the :py:mod:`nexusLIMS` module is imported, one of the "setup" tasks
performed is to perform a basic object-relational mapping between rows of
the ``instruments`` table from the database into
:py:class:`~nexusLIMS.instruments.Instrument` objects. These objects are
stored in a dictionary attribute named :py:data:`nexusLIMS.instruments.instrument_db`.
This is done by querying the database specified in the environment variable
:ref:`nexusLIMS_db_path <nexuslims-db-path>` and creating a dictionary of
:py:class:`~nexusLIMS.instruments.Instrument` objects that contain information
about all of the instruments specified in the database. These objects are used
widely throughout the code so that the database is only queried once at initial
import, rather than every time information is needed.

+--------------------+--------------+-----------------------------------------+
|       Column       |  Data type   |               Description               |
+====================+==============+=========================================+
| ``instrument_pid`` | VARCHAR(100) | The unique identifier for an instrument |
|                    |              | in the facility, currently (but not     |
|                    |              | required to be) built                   |
|                    |              | from the make, model, and type of       |
|                    |              | instrument, plus a unique numeric code  |
|                    |              | (e.g. ``FEI-Titan-TEM-635816`` )        |
+--------------------+--------------+-----------------------------------------+
| ``api_url``        | TEXT         | The calendar API endpoint url for this  |
|                    |              | instrument's scheduler                  |
+--------------------+--------------+-----------------------------------------+
| ``calendar_name``  | TEXT         | The "user-friendly" name of the         |
|                    |              | calendar for this instrument as         |
|                    |              | displayed on the reservation system     |
|                    |              | resource (e.g. "FEI Titan TEM")         |
+--------------------+--------------+-----------------------------------------+
| ``calendar_url``   | TEXT         | The URL to this instrument's            |
|                    |              | web-accessible calendar on the          |
|                    |              | SharePoint resource (if using)          |
+--------------------+--------------+-----------------------------------------+
| ``location``       | VARCHAR(100) | The physical location of this           |
|                    |              | instrument (building and room number)   |
+--------------------+--------------+-----------------------------------------+
| ``schema_name``    | TEXT         | The human-readable name of instrument   |
|                    |              | as defined in the Nexus Microscopy      |
|                    |              | schema and displayed in the records     |
+--------------------+--------------+-----------------------------------------+
| ``property_tag``   | VARCHAR(20)  | A unique numeric identifier for this    |
|                    |              | instrument (not used by NexusLIMS, but  |
|                    |              | for reference and potential future use) |
+--------------------+--------------+-----------------------------------------+
| ``filestore_path`` | TEXT         | The path (relative to central storage   |
|                    |              | location specified in                   |
|                    |              | :ref:`mmfnexus_path <mmfnexus-path>`)   |
|                    |              | where this instrument stores            |
|                    |              | its data (e.g. ``./Titan``)             |
+--------------------+--------------+-----------------------------------------+
| ``computer_name``  | TEXT         | The hostname of the `support PC`        |
|                    |              | connected to this instrument that runs  |
|                    |              | the `Session Logger App`. If this is    |
|                    |              | incorrect (or not included), the        |
|                    |              | logger application will fail when       |
|                    |              | attempting  to start a session from     |
|                    |              | the microscope (only relevant if using  |
|                    |              | the `Session Logger App`)               |
+--------------------+--------------+-----------------------------------------+
| ``computer_ip``    | VARCHAR(15)  | The IP address of the `support PC`      |
|                    |              | connected to this instrument (not       |
|                    |              | currently utilized)                     |
+--------------------+--------------+-----------------------------------------+
| ``computer_mount`` | TEXT         | The full path where the central file    |
|                    |              | storage is mounted and files are        |
|                    |              | saved on the 'support PC' for           |
|                    |              | the instrument (e.g. 'M:/'; only        |
|                    |              | relevant if using the `Session Logger   |
|                    |              | App`)                                   |
+--------------------+--------------+-----------------------------------------+
| ``harvester``      | TEXT         | The specific submodule within           |
|                    |              | :py:mod:`nexusLIMS.harvesters` that     |
|                    |              | should be used to harvest reservation   |
|                    |              | information for this instrument. At the |
|                    |              | time of writing, the only possible      |
|                    |              | values are ``nemo`` or                  |
|                    |              | ``sharepoint_calendar``.                |
+--------------------+--------------+-----------------------------------------+
| ``timezone``       | TEXT         | The timezone in which this instrument   |
|                    |              | is located, in the format of the IANA   |
|                    |              | timezone database (e.g.                 |
|                    |              | ``America/New_York``). This is used     |
|                    |              | to properly localize dates and times    |
|                    |              | when communicating with the harvester   |
|                    |              | APIs.                                   |
+--------------------+--------------+-----------------------------------------+

