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
"""The NexusLIMS back-end software.

This module contains the software required to monitor a database for sessions
logged by users on instruments that are part of the NIST Electron Microscopy
Nexus Facility. Based off this information, records representing individual
experiments are automatically generated and uploaded to the front-end NexusLIMS
CDCS instance for users to browse, query, and edit.

Example
-------
In most cases, the only code that needs to be run directly is initiating the
record builder to look for new sessions, which can be done by running the
:py:mod:`~nexusLIMS.builder.record_builder` module directly:

.. code-block:: bash

    $ python -m nexusLIMS.builder.record_builder

Refer to :ref:`record-building` for more details.

**Configuration variables**

The following variables should be defined as environment variables in your
session, or in the ``.env`` file in the root of this package's repository.
See the ``.env.example`` file for more documentation and examples.

.. _NexusLIMS-file-strategy:

`NexusLIMS_file_strategy`
    Defines the strategy used to find files associated with experimental records.
    A value of ``exclusive`` will `only` add files for which NexusLIMS knows how
    to generate preview images and extract metadata.  A value of ``inclusive``
    will include all files found, even if preview generation/detailed metadata
    extraction is not possible.

.. _NexusLIMS-ignore-patterns:

`NexusLIMS_ignore_patterns`
    The patterns defined in this variable (which should be provided as a
    JSON-formatted string) will be ignored when finding files. A default value
    is provided in the ``.env.example`` file that should work for most users,
    but this setting allows for further customization of the file-finding routine.

.. _nexusLIMS-user:

`nexusLIMS_user`
    The username used to authenticate to sharepoint calendar resources and CDCS

.. _nexusLIMS-pass:

`nexusLIMS_pass`
    The password used to authenticate to sharepoint calendar resources and CDCS

.. _mmfnexus-path:

`mmfnexus_path`
    The path (should be already mounted) to the root folder containing data
    from the Electron Microscopy Nexus. This folder is accessible read-only,
    and it is where data is written to by instruments in the Electron
    Microscopy Nexus. The file paths for specific instruments (specified in
    the NexusLIMS database) are relative to this root.

.. _nexusLIMS-path:

`nexusLIMS_path`
    The root path used by NexusLIMS for various needs. This folder is used to
    store the NexusLIMS database, generated records, individual file metadata
    dumps and preview images, and anything else that is needed by the back-end
    system.

.. _nexusLIMS-db-path:

`nexusLIMS_db_path`
    The direct path to the NexusLIMS SQLite database file that contains
    information about the instruments in the Nexus Facility, as well as logs
    for the sessions created by users using the Session Logger Application.

.. _nemo-address:

`NEMO_address_X`
    The path to a NEMO instance's API endpoint. Should be something like
    ``https://www.nemo.com/api/`` (make sure to include the trailing slash).
    The value ``_X`` can be replaced with any value (such as
    ``NEMO_address_1``). NexusLIMS supports having multiple NEMO reservation
    systems enabled at once (useful if your instruments are split over a few
    different management systems). To enable this behavior, create multiple
    pairs of environment variables for each instance, where the suffix ``_X``
    changes for each pair (`e.g.` you could have ``NEMO_address_1`` paired with
    ``NEMO_token_1``, ``NEMO_address_2`` paired with ``NEMO_token_2``, etc.).

.. _nemo-token:

`NEMO_token_X`
    An API authentication token from the corresponding NEMO installation
    (specified in ``NEMO_address_X``) that
    will be used to authorize requests to the NEMO API. This token can be
    obtained by visiting the "Detailed Administration" page in the NEMO
    instance, and then creating a new token under the "Tokens" menu. Note that
    this token will authenticate as a particular user, so you may wish to set
    up a "dummy" or "functional" user account in the NEMO instance for these
    operations.

.. _nemo-strftime-fmt:
.. _nemo-strptime-fmt:

`NEMO_strftime_fmt_X` and `NEMO_strptime_fmt_X`
    These options are optional, and control how dates/times are sent to
    (`strftime`) and interpreted from (`strptime`) the API. If "`strftime_fmt`"
    and/or "`strptime_fmt`" are not provided, the standard ISO 8601 format
    for datetime representation will be used (which should work with the
    default NEMO settings). These options are configurable to allow for
    support of non-default date format settings on a NEMO server. The formats
    should be provided using the standard datetime library syntax for
    encoding date and time information (see :ref:`strftime-strptime-behavior`
    for details).

.. _nemo-tz:

`NEMO_tz_1`
    Also optional; If the "`tz`" option is provided, the datetime
    strings received from the NEMO API will be coerced into the given timezone.
    The timezone should be specified using the IANA "tz database" name (see
    https://en.wikipedia.org/wiki/List_of_tz_database_time_zones). This option
    should not be supplied for NEMO servers that return time zone information in
    their API response, since it will override the timezone of the returned
    data. It is mostly useful for servers that return reservation/usage event
    times without any timezone information. Providing it helps properly map
    file creation times to usage event times.
"""
# pylint: disable=invalid-name

import logging

from dotenv import load_dotenv

# load environment variables from a .env file if present
load_dotenv()


def _filter_hyperspy_messages(record):  # pragma: no cover
    """Filter HyperSpy API import warnings within the NexusLIMS codebase."""
    # this only triggers if the hs.preferences.GUIs.warn_if_guis_are_missing
    # preference is set to True
    if record.msg.startswith("The ipywidgets GUI") or record.msg.startswith(
        "The traitsui GUI",
    ):
        return False
    # unless we come across another HyperSpy error, this line won't be
    # reached, so exclude from coverage
    return True


# connect the filter function to the HyperSpy logger
logging.getLogger("hyperspy.api").addFilter(_filter_hyperspy_messages)

# tweak some logger levels
logging.getLogger("matplotlib.font_manager").disabled = True
logging.getLogger("matplotlib").setLevel(logging.WARNING)
logging.getLogger("PIL.PngImagePlugin").setLevel(logging.WARNING)

# set log message format
logging.basicConfig(format="%(asctime)s %(name)s %(levelname)s: %(message)s")
