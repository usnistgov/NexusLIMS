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
"""The NexusLIMS backend software.

This module contains the software required to monitor a database for sessions
logged by users on instruments that are part of the NIST Electron Microscopy
Nexus Facility. Based off this information, records representing individual
experiments are automatically generated and uploaded to the frontend NexusLIMS
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
session, or in the ``.env`` file in the root of this package's repository (if
you are running using ``pipenv``.

.. _nexusLIMS-user:

`nexusLIMS_user`
    The username used to authenticate to calendar resources and CDCS

.. _nexusLIMS-pass:

`nexusLIMS_pass`
    The password used to authenticate to calendar resources and CDCS

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
    dumps and preview images, and anything else that is needed by the backend
    system.

.. _nexusLIMS-db-path:

`nexusLIMS_db_path`
    The direct path to the NexusLIMS SQLite database file that contains
    information about the instruments in the Nexus Facility, as well as logs
    for the sessions created by users using the Session Logger Application.
"""

from ._urls import calendar_root_url
from ._urls import ldap_url

# raise ValueError('nexusLIMS import')
