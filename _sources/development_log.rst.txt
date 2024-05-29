v1.4.2 (2024-05-29)
===================

Bug fixes
---------

- Added workaround for issue where duplicate section titles would cause error in
  ``quanta_tif`` extractor. (`#136 <https://gitlab.nist.gov/gitlab/nexuslims/NexusMicroscopyLIMS/-/issues/136>`_)


v1.4.1 (2023-09-20)
===================

Bug fixes
---------

- Resolved issue where text files that can't be opened with any encoding caused the record
  builder to crash (`#134 <https://gitlab.nist.gov/gitlab/nexuslims/NexusMicroscopyLIMS/-/issues/134>`_)


Documentation improvements
--------------------------

- Documented internal release and deploy process on Wiki


v1.4.0 (2023-09-19)
===================

New features
------------

- Added ability to generate previews for "plain" image files (e.g. ``.jpg``, ``.png``,
  etc.) and plain text files. (`#128 <https://gitlab.nist.gov/gitlab/nexuslims/NexusMicroscopyLIMS/-/issues/128>`_)


Bug fixes
---------

- Fix problem arising from NEMO API change that removed ``username`` keyword. (`#131 <https://gitlab.nist.gov/gitlab/nexuslims/NexusMicroscopyLIMS/-/issues/131>`_)


v1.3.1 (2023-05-19)
===================

Bug fixes
---------

- Fixed issue where "process new records" script was emailing an error alert on conditions
  that were not errors. (`#126 <https://gitlab.nist.gov/gitlab/nexuslims/NexusMicroscopyLIMS/-/issues/126>`_)


Miscellaneous/Development changes
---------------------------------

- Fixed pipeline runner to not run tests when they're not needed. (`#129 <https://gitlab.nist.gov/gitlab/nexuslims/NexusMicroscopyLIMS/-/issues/129>`_)


v1.3.0 (2023-04-14)
===================

New features
------------

- Add support for reading ``.spc`` and ``.msa`` EDS spectrum files produced by EDAX
  acquisition softwares. (`#122 <#>`_)


Documentation improvements
--------------------------

- Add `towncrier <https://towncrier.readthedocs.io/>`_ to manage documentation of
  changes in a semi-automated manner. (`#125 <#>`_)


v1.2.0 (2023-03-31)
===================

New features
------------

- Added new "default" extractor for filetypes we don't know how to read
  that will add very basic file-based metadata otherwise (`#121 <#>`_)
- Added a configuration environment variable for file finding
  (``NexusLIMS_file_strategy``). A value of ``"inclusive"`` will add all files found in
  the time range of a session to the record (even if we don't know how to parse it beyond
  basic metadata). A value of ``"exclusive"`` will exlcude files that do not have an
  explicit extractor defined (this was the previous behavior) (`#121 <#>`_)
- Added a way to "ignore" files during the file finding routine via an environment
  variable named ``NexusLIMS_ignore_patterns``. It should be a JSON-formatted list
  provided as a string. Each item of the list will be passed to the GNU find command
  as a pattern to ignore. (`#121 <#>`_)


Bug fixes
---------

- Fixed Poetry not installing due to change in upstream installer location (`#117 <#>`_)
- Fixed issue where record builder would not run (and we wouldn't even be alerted!)
  if the network shares for ``mmfnexus_path`` and ``nexusLIMS_path`` were not mounted. (`#118 <#>`_)
- Fixed bug introduced by change to API response for reservation questions in NEMO 4.3.2 (`#119 <#>`_)
- Fix for development bug introduced by upgrade of tox package to 4.0.


Enhancements
------------

- Added support for ``"NO_CONSENT"`` and ``"NO_RESERVATION"`` statuses in the
  ``session_log`` table of the NexusLIMS database (`#105 <#>`_)
- Harvesters (and other parts of the code that use network resources) will now retry
  their requests if they fail in order to make the record building process more resilient (`#112 <#>`_)
- Harvester will now read periodic table element information from NEMO reservation
  questions and include them in the XML records. Also updated the schema and CDCS XSLT
  to allow for and display this information in the front end. (`#120 <#>`_)
- File finding now works on a directory of symbolic links (in addition to a regular
  folder hierarchy).


Documentation improvements
--------------------------

- Improved documentation to be public-facing and also set up structure for public
  repository at https://github.com/usnistgov/nexuslims,
  https://github.com/usnistgov/NexusLIMS-CDCS, and
  https://github.com/usnistgov/nexuslims-cdcs-docker (`#111 <#>`_)
- Add NIST branding to documentation via header/footer script from pages.nist.gov (`#113 <#>`_)


Miscellaneous/Development changes
---------------------------------

- If the record building delay has not passed and no files were found, a
  ``RECORD_GENERATION`` event will no longer be added to the ``session_log`` table
  in the database to avoid cluttering things up. (`#107 <#>`_)
- Public facing branches are now excluded from CI/CD pipeline to prevent test failures (`#114 <#>`_)
- Updated code to use various linters, including
  `isort <https://pycqa.github.io/isort/>`_, `black <https://github.com/psf/black>`_,
  `pylint <https://pylint.readthedocs.io/en/latest/>`_, and
  `ruff <https://beta.ruff.rs/docs/>`_. (`#121 <#>`_)
- Add support for Python 3.10(.9)
- Moved URL configration to environment variables
- Updated third-party dependencies to recent latest versions


Deprecations and/or Removals
----------------------------

- Remove support for Python 3.7.X
- Removed unused LDAP code


v1.1.1 (2022-06-15)
===================

Bug fixes
---------

- Fixed issue where record builder would crash if only one file was found during the
  activity (and added explicit test for this condition). (`#96 <#>`_)
- Fix issue in NEMO harvester where not-yet-ended sessions would cause the harvester
  to try to insert rows that violated database constraints. (`#99 <#>`_)
- Implemented a "lockfile" system so concurrent runs of the record builder will not
  be allowed, preventing extra entries in the ``session_log`` table that were causing
  errors. (`#101 <#>`_)
- Fix reading reservation and usage event times from NEMO servers with differing datetime
  formats. (`#103 <#>`_)
- The NEMO harvester no longer attempts to build records without explicit "data consent"
  supplied by the user during the reservation questions (previously, if no reservation
  was found, the harvester would return a generic event and a record would still be built). (`#104 <#>`_)
- Fixed bug where null bytes in a TIFF file caused an error in metadata extraction (`#110 <#>`_)


Enhancements
------------

- Add ability for record builder to insert a link to reservation information in the
  ``summary`` node (modified schema to hold this and record builder to insert it). (`#90 <#>`_)
- Contributed a `PR <https://github.com/usnistgov/NEMO/pull/97>`_ to the upstream NEMO
  project to allow for displaying of a single reservation, so that we may link to it
  and include it as a reference in records built by NexusLIMS. (`#92 <#>`_)
- Made the default `data_consent` value for the NEMO harvester False, so we will not
  harvest data from sessions that do not have reservation questions defined (users
  now have to opt-in to have their data curated by NexusLIMS). (`#93 <#>`_)
- NEMO harvester now limits its API requests to only tools defined in the NexusLIMS
  database, which is more efficient and greatly speeds up the harvesting process. (`#94 <#>`_)
- The record builder will now retry for a configurable number of days if it does not find
  any files for a session (useful for machines that have a delay in data syncing to
  centralized file storage). Configured via the ``nexusLIMS_file_delay_days`` environment
  variable. (`#102 <#>`_)
- Made datetime formats for NEMO API harvester configurable (both sending and receiving)
  so that it can work regardless of configuration on the NEMO server. (`#103 <#>`_)
- Record generation events in the database now have timezone information for better
  specificity in multi-timezone setups. (`#106 <#>`_)
- Add ``pid`` attribute to Experiment schema to allow for integration with CDCS's handle
  implementation. (`#109 <#>`_)


Miscellaneous/Development changes
---------------------------------

- Configured tests to run on-premises, which speeds up various testing operations. (`#57 <#>`_)
- Drastically restructured repository to look more like a proper Python library than just
  a collection of files and scripts. (`#60 <#>`_)
- Migrated project organization and packaging from
  `pipenv <https://pipenv.pypa.io/en/latest/>`_ to `poetry <https://python-poetry.org/>`_. (`#88 <#>`_)
- Fixed some tests that started failing due to tool ID changes on our local NEMO server. (`#97 <#>`_)
- Improved logging from NEMO harvester making it easier to debug issues when they occur. (`#98 <#>`_)
- Session processing script is now smarter about email alerts. (`#100 <#>`_)
- CI/CD pipeline will now retry failed tests (should be more resilient against transient
  failures due to network issues).
- Made some changes to the codebase in preparation of making it public-facing on Github.


Deprecations and/or Removals
----------------------------

- Removed a variety of associated files that were not important for the Python package
  (old presentations, diagrams, reports, etc.) (`#60 <#>`_)
- :py:mod:`nexusLIMS.harvesters.sharepoint_calendar` module was deprecated after
  the SharePoint calendaring system was decommissioned in the Nexus facility. All
  harvester development will center around NEMO for the foreseeable future. (`#108 <#>`_)
- Removed enumeration restriction on PIDs from the schema so it is more general (and
  easier to add new instruments without having to do an XML schema migration). (`#110 <#>`_)


v1.1.0 (2021-12-12)
===================

New features
------------

- Major new feature in this release is the implementation of a reservation and metadata
  harvester for the `NEMO <https://github.com/usnistgov/NEMO>`_ facility management
  system. All planned future feature development will focus on this harvester, and the
  SharePoint calendar harvester will be deprecated in a future release. See the
  :std:doc:`record_building` docs and the :std:doc:`api/nexusLIMS.harvesters.nemo` docs
  for more details. (`#89 <#>`_)


Enhancements
------------

- Add support to NEMO harvester for multiple samples in a set of reservation questions.
  The required structure for reservation questions is documented in the
  :py:func:`nexusLIMS.harvesters.nemo.res_event_from_session` function.
- Added ability to specify timezone information for instruments in the NexusLIMS database,
  which helps fully qualify all dates and times so file finding works as expected when
  inspecting files stored on servers in different timezones.
- Updated detail XLST to display multiple samples for a record if present (since this
  is now possible using the NEMO reservation questions).


Documentation improvements
--------------------------

- Documented new NEMO harvester and updated record generation documentation to describe
  how the process works with multiple harvesters.
- Fixed broken image paths in README.


Miscellaneous/Development changes
---------------------------------

- .. |pipenv| replace:: ``pipenv``
  .. _pipenv: https://pipenv.pypa.io/en/latest/
  .. |poetry2| replace:: ``poetry``
  .. _poetry2: https://python-poetry.org/
  .. |tox| replace:: ``tox``
  .. _tox: https://tox.wiki/en/latest/

  Migrated project structure from |pipenv|_ to |poetry2|_ for better dependency
  resolution, easier and faster deployment, and configuration of project via
  ``pyproject.toml``. Also implemented |tox|_ for the running of tests, doc builds,
  and pipelines. (`#88 <#>`_)
- Refactored some functions from the SharePoint harvester into the
  :py:mod:`nexusLIMS.utils` module for easier use throughout the rest of the codebase.

Deprecations and/or Removals
----------------------------

- Removed the "Session Logger" application in favor of using NEMO and its usage events
  to track session timestamps.


v1.0.1 (2021-09-15)
===================

New features
------------

- Implemented a "file viewer" on the front-end NexusLIMS application which also allows
  for downloading single, multiple, or all data files from a particular record in
  ``.zip`` archives. (`#61 <#>`_)
- Implemented a metadata extractor for ``.ser`` and ``.emi`` files produced by the TIA
  application on FEI TEMs. (`#62 <#>`_)
- Added ability to export a record as XML in the front end NexusLIMS application. (`#65 <#>`_)
- Added a "tutorial" feature to the front-end of the NexusLIMS application, which leads
  users through a tour describing what the various parts of the application do. (`#71 <#>`_)
- Added new "dry run" mode and additional verbosity options to record builder that allow
  one to see what records `would` be built without actually doing anything. (`#77 <#>`_)


Bug fixes
---------

- Fixed issue where Session Logger app was failing due to incompatibilities between
  the code and certain database states. (`#53 <#>`_)
- Fixed issue where Session Logger app was leaving behind a temporary file on the
  microscope computers by making it clean up after itself. (`#55 <#>`_)
- Fixed issue where multiple copies of the Session Logger app were able to be run at the
  same time, which shouldn't have been possible. (`#59 <#>`_)
- Fixed the "back to previous" button in the front-end application that was broken. (`#64 <#>`_)
- Fixed issue with SharePoint harvester where records were being assigned to the person
  who `created` a calendar event, not the person whose name was on the actual event. (`#72 <#>`_)
- Fixed a deployment issue related to ``pipenv`` and how it specifies packages to be
  installed. (`#73 <#>`_)
- Fixed issues with ``.ser`` file handling (and contributed various fixes upstream to the
  HyperSpy project: `1 <https://github.com/hyperspy/hyperspy/pull/2533>`_,
  `2 <https://github.com/hyperspy/hyperspy/pull/2531>`_,
  `3 <https://github.com/hyperspy/hyperspy/pull/2529>`_). (`#74 <#>`_)


Enhancements
------------

- Added customized loading text while the list of records is loading in the front-end
  NexusLIMS application. (`#58 <#>`_)
- Tweaked heuristic in SharePoint harvester to better match sessions to calendar events
  (previously, if there were multiple reservations in one day, they may have been
  incorrectly attributed to a session). (`#67 <#>`_)
- Added explicit support for Python 3.8.X versions. (`#75 <#>`_)
- Implemented bash script to run record builder automatically, which can then be scheduled
  via a tool such as ``cron``. (`#76 <#>`_)
- Added version information to Session Logger app to make it easier for users to know
  if they are up to date or not. (`#79 <#>`_)
- Small tweak to make acquisition activity links easier to click in record display. (`#81 <#>`_)


Documentation improvements
--------------------------

- Added "taxonomy" of terms used in the NexusLIMS project to the documentation (see
  :std:doc:`taxonomy` for details). (`#40 <#>`_)
- Added XML Schema documentation for the Nexus ``Experiment`` schema to the documentation
  (see :std:doc:`schema_documentation` for details). (`#51 <#>`_)
- Added links to NexusLIMS documentation in the front-end NexusLIMS CDCS application. (`#68 <#>`_)
- Added many documentation pages to more thoroughly explain how NexusLIMS works,
  including improvements to the project README, as well as the following pages:
  :std:doc:`database`, :std:doc:`session_logger_app`, :std:doc:`development`,
  and pages about data security.


Miscellaneous/Development changes
---------------------------------

- Improvement to logging to make it easier to debug records not being built correctly. (`#80 <#>`_)
- Added new :py:class:`~nexusLIMS.harvesters.reservation_event.ReservationEvent` class
  to abstract the concept of a calendar reservation event. This reduces dependencies on
  the SharePoint-specific way things were written before and will help in the future
  implementation of the NEMO harvester.
- Fix some issues with tests not running correctly due to changes of paths in
  ``mmfnexus_path``.
- Improvements to the CI/CD pipelines so multiple pipelines can run at once without error.


v0.0.9 (2020-02-24) - First real working release
================================================

New features
------------

- Added extractor for TIFF image files produced by FEI SEM and FIB instruments.
- Record builder can now be run automatically and will do the whole process (probing
  database, finding files, extracting metadata, building record XML, and uploading to
  CDCS frontend).


Enhancements
------------

- Acquisition activities are now split up by clustering of file acquisition times, rather
  than inspecting when an instrument switches modes. This is more realistic to how
  microscopes are used in practice (see
  :ref:`Activity Clustering <build-activities>` for more details).
- Added "instrument specific" parsing for DigitalMicrograph files
- Added :py:mod:`nexusLIMS.cdcs` module to handle interactions with the CDCS front-end.
- Added a "Data Type" to all metadata extractions that will attempt to classify what sort
  of data a file is ("STEM EELS", "TEM Image", "SEM EDS", etc.).
- Configuration of program options is now mostly done via environment variables rather
  than values hard-coded into the source code.
- Drastically improved file finding time by utilizing GNU ``find`` to identify files in
  a record rather than a pure Python implementation.
- Records now use a "dummy title" if no matching reservation is found for a session.
- Thumbnail previews of DigitalMicrograph files will now include image annotations.
- Updated SharePoint calendar harvester to be compatible with SharePoint 2016.
- Various XSLT enhancements for better display of record data.


Documentation improvements
--------------------------

- Added record building documentation: :std:doc:`record_building`.


Miscellaneous/Development changes
---------------------------------

- Added helper script to update XLST on NexusLIMS front-end via API, making things easier
  for development.
- Fully implemented tests to ensure 100% of codebase is covered by test functions.
- Refactored record builder and harvester to use
  :py:class:`~nexusLIMS.instruments.Instrument` instances rather than string parsing.


v0.0.2 (2020-01-08) - Pre-release version
=========================================

New features
------------

- Added ability to use custom CA certificate for network communications (useful if
  communicating with servers with self-signed certificates). (`#49 <#>`_)
- Added javascript-powered XLST for more interactive and fully-featured display of records
  in the CDCS front-end (T. Bina).
- Added session logging .exe application that can be deployed on individual microscope PCs
  to specify when a session starts and ends (used to get timestamps for file finding
  during record building). See :doc:`session_logger_app` for more details.
- Finished implementation of building ``AcquisitionActivity`` representations of
  experiments, which are then translated into XML for the final record.
- Implemented prototype record builder script for automated record generation (T. Bina).
- Preview images are now generated for known dataset types during the creation of
  acquisition activities in record building.


Bug fixes
---------

- Updated endpoint for sharepoint calendar API that had broken due to a change in that service. (`#37 <#>`_)
- Fixed issue where schema had duplicate "labels" for certain fields that was causing
  a confusing display in the CDCS "curate" page. (`#42 <#>`_)


Enhancements
------------

- Added other Nexus instruments to the schema so we can have records from more than just
  a single ``Instrument`` (as it was in initial testing). (`#32 <#>`_)
- Added a ``unit`` attribute to parameter values in the `Nexus Experiment` schema. (`#41 <#>`_)
- Added a place to insert "project" information into `Nexus Experiment` schema (`#44 <#>`_)
- Improved the implementation of the ``Instrument`` type within the `Nexus Experiment`
  schema. (`#45 <#>`_)
- Added spiffy logo for NexusLIMS (see :ref:`the README<logo>` for more details on its
  origins).
- Formatted repository as a proper Python package that can be installed via ``pip``.
- Generalized metadata extraction process in anticipation of implementing extractors for
  additional file types.
- Instrument configuration is now fully pulled from NexusLIMS DB, rather than hard-coded
  in the application code.
- XSLT now properly displays preview images rather than a placeholder for each dataset.


Documentation improvements
--------------------------

- Fix links in README to point to new upstream project location. (`#36 <#>`_)
- Added basic documentation for NexusLIMS package and link via a badge on the README. (`#43 <#>`_)


Miscellaneous/Development changes
---------------------------------

- Moved project out of a personal account and into it's own NexusLIMS group on Gitlab. (`#29 <#>`_)
- Added dedicated folder (separate form data storage location) for NexusLIMS to write
  dumps of extracted metadata and preview images. (`#38 <#>`_)
- Added database initialization script to create correct NexusLIMS DB structure.
- Refactored record builder and calendar harvesting into separate submodules to better
  delineate functionality of the various parts of NexusLIMS

v0.0.1 (2019-03-26) - Pre-release version
=========================================

New features
------------

- Implemented SharePoint calendar metadata harvesting for equipment reservations. (`#26 <#>`_)
- Added metadata extractor for FEI TIFF image files produced by SEMs and FIBs. (`#35 <#>`_)
- Created repository to hold initial work on NexusLIMS. 

Enhancements
------------

- Added a concept of "role" (experimental, calibration, etc.) to datasets in the
  `Nexus Experiment` schema (`#23 <#>`_)


Miscellaneous/Development changes
---------------------------------

- Added CI/CD pipeline for backend tests. (`#30 <#>`_)

