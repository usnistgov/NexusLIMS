#  NIST Public License - 2023
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
"""Handle basic metadata extraction from files that do not have an extractor defined."""

import logging
import os
from datetime import datetime as dt

from nexusLIMS.instruments import get_instr_from_filepath

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


def get_basic_metadata(filename):
    """
    Get basic metadata from a file.

    Returns basic metadata from a file that's not currently interpretable by NexusLIMS.

    Parameters
    ----------
    filename : str
        path to a file saved in the harvested directory of the instrument

    Returns
    -------
    mdict : dict
        A description of the file in lieu of any metadata extracted from it.
    """
    mdict = {"nx_meta": {}}
    mdict["nx_meta"]["DatasetType"] = "Unknown"
    mdict["nx_meta"]["Data Type"] = "Unknown"

    # get the modification time (as ISO format):
    mtime = os.path.getmtime(filename)
    instr = get_instr_from_filepath(filename)
    mtime_iso = dt.fromtimestamp(
        mtime,
        tz=instr.timezone if instr else None,
    ).isoformat()
    mdict["nx_meta"]["Creation Time"] = mtime_iso

    return mdict
