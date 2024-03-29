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
"""
A module to handle communication with the NexusLIMS database.

Also performs basic database ORM tasks. The top-level module has a helper function to
make a database query (:py:meth:`make_db_query`), while the
:py:mod:`~nexusLIMS.db.session_handler` submodule is primarily concerned with mapping
session log information from the database into python objects for use in other parts of
the NexusLIMS backend.
"""

import contextlib
import os
import sqlite3


def make_db_query(query):
    """
    Execute a query on the NexusLIMS database and return the results as a list.

    Parameters
    ----------
    query : str
        The SQL query to execute

    Returns
    -------
    res_list : :obj:`list` of :obj:`tuple`
        The results of the SQL query
    """
    # use contextlib to auto-close the connection and database cursors
    with contextlib.closing(  # noqa: SIM117
        sqlite3.connect(os.environ["nexusLIMS_db_path"]),
    ) as connection:
        with connection:
            with contextlib.closing(connection.cursor()) as cursor:
                results = cursor.execute(query)
                return results.fetchall()
