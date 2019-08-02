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

import os as _os
import time as _time
import pickle as _pickle
from nexusLIMS import record_builder


def find_new_sessions():
    """
    Checks through the files/folders which contain microscopy data to see which folders have been created or updated
    since the previous call of the function. All newly updated or created sessions since the last check will be
    processed via add_record_to_cdcs(path), creating a record and pushing it the CDCS client. The time of the
    previous run will be kept within an accompanying pickle file.
    """
    # TODO: Manage data path (allow for user input.?)
    data_path = '//***REMOVED***/***REMOVED***/mmfnexus/Titan/***REMOVED***'

    try:
        with open('prev_run.pk', 'rb') as f:
            last_check = _pickle.load(f)
    except FileNotFoundError as e:
        last_check = 0

    for f in _os.listdir(data_path):
        abs_path = _os.path.join(data_path, f)
        if _os.path.isdir(abs_path) and _os.path.getmtime(abs_path) > last_check:
            add_record_to_cdcs(abs_path)

    # last_check = _time.time()
    last_check = 0
    picklefile = 'prev_run.pk'
    with open(picklefile, 'wb') as f:
        _pickle.dump(last_check, f)


def add_record_to_cdcs(abs_path):
    """
    Builds an XML record associated with a given microscopy session (a folder indicated by 'path') and passes the
    resulting XML file to CDCS through its API, matching it with an appropriate schema.

    Parameters
    ----------
    abs_path : str
        A file path which corresponds to the folder pertaining to an individual microscopy session of which a record
        will be built.
    """
    path, file = _os.path.split(abs_path)
    date = _time.strftime('%Y-%m-%d', _time.gmtime(_os.path.getmtime(abs_path)))
    instr_list = {'7100Aztec': '',
                  '7100Jeol': 'jeol_sem',
                  'JEOL3010': 'jeol_tem',
                  'Quanta': 'quanta',
                  'Titan': 'msed_titan'}
    instrument = _os.path.basename(_os.path.split(path)[0])
    instrument = instr_list[instrument]  # Reassigns instrument to str from 'instr_list' which corresponds to how the
                                         # Sharepoint calendar accesses information
    user = _os.path.basename(path)
    record = record_builder.build_record(path=abs_path, instrument=instrument, date=date, user=user)

    # TODO: Push record to CDCS through API call


if __name__ == '__main__':
    """
    These lines are just for testing. For real use, import the methods you need and operate from there
    """
    find_new_sessions()