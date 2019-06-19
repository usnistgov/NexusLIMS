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

import pynoid
pynoid.mint()

import os
import uuid
import logging
import hyperspy.api_nogui as hs
from datetime import datetime
from nexusLIMS.schemas import activity
from nexusLIMS import AcquisitionActivity
from glob import glob
import socket
from timeit import default_timer as timer

_logger = logging.getLogger(__name__)
_logger.setLevel(logging.INFO)

hostname = socket.gethostname()

path_roots = dict(
    poole=dict(
        remote='/usr/local/mnt/***REMOVED***/',
        local='***REMOVED***NexusMicroscopyLIMS/test_data/'
    ),
    ***REMOVED***=dict(
        remote='/mnt/***REMOVED***/',
        local='***REMOVED***NexusMicroscopyLIMS/test_data/'
    )
)

path_root = path_roots[hostname]['remote']
path_to_search = os.path.join(path_root, 'mmfnexus/Titan/***REMOVED***/',
                              '181113 - ***REMOVED*** - ***REMOVED*** - Titan/')

logging.getLogger('hyperspy.io_plugins.digital_micrograph').setLevel(
    logging.WARNING)

files = glob(os.path.join(path_to_search, "*.dm3"))
files.sort(key=os.path.getmtime)
files = files[:-2]

mtimes = [''] * len(files)
modes = [''] * len(files)
start_timer = timer()
for i, f in enumerate(files):
    mode = hs.load(f, lazy=True).original_metadata.ImageList.TagGroup0.ImageTags.Microscope_Info.Imaging_Mode
    mtimes[i] = datetime.fromtimestamp(os.path.getmtime(f)).isoformat()
    modes[i] = mode
    this_mtime = datetime.fromtimestamp(
        os.path.getmtime(f)).strftime("%Y-%m-%d %H:%M:%S")
    _logger.info(f'{this_mtime} --- {mode} --- {f}')
end_timer = timer()

_logger.info(f'Loading files took {end_timer - start_timer:.2f} seconds')

activities = []

for i, (f, t, m) in enumerate(zip(files, mtimes, modes)):
    # temporarily ignore files with this year's date
    if t.startswith('2019'): continue

    # set last_mode to this mode if this is the first iteration; otherwise set
    # it to the last mode that we saw
    last_mode = m if i == 0 else modes[i - 1]

    # if this is the first iteration, start a new AcquisitionActivity and
    # add it to the list of activities
    if i == 0:
        _logger.debug(t)
        start_time = datetime.fromisoformat(t)
        aa = AcquisitionActivity(start=start_time, mode=m)
        activities.append(aa)

    # if this file's mode is the same as the last, just add it to the current
    # activity's file list
    if m == last_mode:
        activities[-1].add_file(f)

    # this file's mode is different, so it belongs to the next
    # AcquisitionActivity. End the current AcquisitionActivity and create a new
    # one with this file's information
    else:
        # AcquisitionActivty end time is previous mtime
        activities[-1].end = datetime.fromisoformat(mtimes[i - 1])
        # New AcquisitionActivity start time is t
        activities.append(AcquisitionActivity(start=datetime.fromisoformat(t),
                                              mode=m))
        activities[-1].add_file(f)

    # We have reached the last file, so end the current activity
    if i == len(files) - 1:
        activities[-1].end = datetime.fromisoformat(t)

INDENT = '    '

for i, a in enumerate(activities):
    AA_logger = logging.getLogger('nexusLIMS.schemas.activity')
    AA_logger.setLevel(logging.ERROR)
    a.store_setup_params()
    a.store_unique_metadata()

    a.as_xml(i, 'f81d3518-10af-4fab-9bd3-cfa2b0aea807',
             indent_level=1, print_xml=True)
    # print(f'<acquisitionActivity seqno="{i}">')
    # print(f'{INDENT}<startTime>{a.start.isoformat()}</startTime>')
    # print(f'{INDENT}<sampleID>f81d3518-10af-4fab-9bd3-cfa2b0aea807</sampleID>')
    # print()
    # print(f'{INDENT}<setup>')
    # for pk, pv in a.setup_params.items():
    #     print(f'{INDENT}{INDENT}<param name="{pk}">{pv}</param>')
    # print(f'{INDENT}</setup>')
    # print('')
    #
    # print(f'{INDENT}<notes source="ELN">')
    # print(f'{INDENT}{INDENT}<entry xsi:type="nx:TextEntry">')
    # print(f'{INDENT}{INDENT}{INDENT}<p>This is an example note entry for '
    #       f'an acquisitionActivity</p>'
    #       f'<p>Its text representation in Python is "{a}"</p>')
    # print(f'{INDENT}{INDENT}</entry>')
    # print(f'{INDENT}</notes>')
    #
    # #
    # mode_to_dataset_type_map = {
    #     'IMAGING': 'Image',
    #     'DIFFRACTION': 'Diffraction'
    # }
    # for f, m, um in zip(a.files, a.meta, a.unique_meta):
    #     # build path to thumbnail
    #     fname = os.path.basename(f)
    #     thumb_name = f'{fname}.thumb.png'
    #     thumb_path = os.path.join(os.path.dirname(f),
    #                               '.nexuslims',
    #                               thumb_name)
    #
    #     # f is string; um is a dictionary
    #     print(f'{INDENT}<dataset type="{mode_to_dataset_type_map[a.mode]}" '
    #           f'role="Experimental">')
    #     print(f'{INDENT}{INDENT}<name>{os.path.basename(f)}</name>')
    #     print(f'{INDENT}{INDENT}<location>{f}</location>')
    #     print(f'{INDENT}{INDENT}<preview>{thumb_path}</preview>')
    #     for meta_k, meta_v in um.items():
    #         print(f'{INDENT}{INDENT}<meta name="{meta_k}">{meta_v}</meta>')
    #     print(f'{INDENT}</dataset>')
    #
    # print(f'</acquisitionActivity>')
