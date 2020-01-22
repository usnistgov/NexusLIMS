"""
This module contains the code used to harvest metadata from various file types
generated from instruments in the Electron Microscopy Nexus facility.
"""
import os as _os
import json as _json
import pathlib as _pathlib
from .quanta_tif import get_quanta_metadata
from .digital_micrograph import get_dm3_metadata
from .thumbnail_generator import sig_to_thumbnail as _s2thumb
from nexusLIMS import mmf_nexus_root_path as _mmf_path
from nexusLIMS import nexuslims_root_path as _nx_path
from nexusLIMS.utils import SortedDictEncoder
import hyperspy.api_nogui as _hs
import logging as _logging

_logger = _logging.getLogger(__name__)

extension_reader_map = {
    'dm3': get_dm3_metadata,
    'dm4': get_dm3_metadata,
    'tif': get_quanta_metadata
}


def parse_metadata(fname, write_output=True, generate_preview=True,
                   overwrite=True):
    """
    Given an input filename, read the file, determine what "type" of file (i.e.
    what instrument it came from) it is, filter the metadata (if necessary) to
    what we are interested in, and return it as a dictionary (writing to the
    NexusLIMS directory as JSON by default). Also calls the preview
    generation method, if desired.

    Parameters
    ----------
    fname : str
        The filename from which to read data
    write_output : bool
        Whether to write the metadata dictionary as a json file in the NexusLIMS
        folder structure
    generate_preview : bool
        Whether to generate the thumbnail preview of this dataset (that
        operation is not done in this method, it is just called from here so
        it can be done at the same time)
    overwrite : bool
        Whether or not to overwrite the .json metadata file and thumbnail
        image if either exists

    Returns
    -------
    nx_meta : dict or None
        The "relevant" metadata that is of use for NexusLIMS. If None,
        the file could not be opened
    """

    extension = _os.path.splitext(fname)[1][1:]

    nx_meta = extension_reader_map[extension](fname)

    if nx_meta is not None:
        if write_output:
            out_fname = fname.replace(_mmf_path, _nx_path) + '.json'
            if not _os.path.isfile(out_fname) or overwrite:
                # Create the directory for the metadata file, if needed
                _pathlib.Path(_os.path.dirname(out_fname)).mkdir(parents=True,
                                                                 exist_ok=True)
                with open(out_fname, 'w') as f:
                    _json.dump(nx_meta, f, sort_keys=True,
                               cls=SortedDictEncoder, indent=2)

        if generate_preview:
            preview_fname = fname.replace(_mmf_path, _nx_path) + '.thumb.png'
            s = _hs.load(fname, lazy=True)

            # If s is a list of signals, use just the first one for our purposes
            if isinstance(s, list):
                num_sigs = len(s)
                fname = s[0].metadata.General.original_filename
                s = s[0]
                s.metadata.General.title = \
                    s.metadata.General.title + \
                    f' (1 of {num_sigs} total signals in file "{fname}")'

            # only generate the preview if it doesn't exist, or overwrite
            # parameter is explicitly provided
            if not _os.path.isfile(preview_fname) or overwrite:
                _logger.info(f'Generating preview: {preview_fname}')
                # Create the directory for the thumbnail, if needed
                _pathlib.Path(_os.path.dirname(preview_fname)).mkdir(
                    parents=True, exist_ok=True)
                # Generate the thumbnail
                s.compute(progressbar=False)
                _s2thumb(s, out_path=preview_fname)

    return nx_meta
