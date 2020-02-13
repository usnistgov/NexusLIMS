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
from .thumbnail_generator import down_sample_image as _down_sample
from nexusLIMS import mmf_nexus_root_path as _mmf_path
from nexusLIMS import nexuslims_root_path as _nx_path
from nexusLIMS.utils import SortedDictEncoder
from nexusLIMS.instruments import get_instr_from_filepath as _get_instr
import hyperspy.api_nogui as _hs
import logging as _logging
import collections as _collections

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
    preview_fname : str or None
        The file path of the generated preview image, or `None` if it was not
        requested
    """

    extension = _os.path.splitext(fname)[1][1:]

    nx_meta = extension_reader_map[extension](fname)
    preview_fname = None

    if nx_meta is not None:
        # Set the dataset type to Misc if it was not set by the file reader
        if 'DatasetType' not in nx_meta['nx_meta']:
            nx_meta['nx_meta']['DatasetType'] = 'Misc'

        if write_output:
            out_fname = fname.replace(_mmf_path, _nx_path) + '.json'
            if not _os.path.isfile(out_fname) or overwrite:
                # Create the directory for the metadata file, if needed
                _pathlib.Path(_os.path.dirname(out_fname)).mkdir(parents=True,
                                                                 exist_ok=True)
                with open(out_fname, 'w') as f:
                    _logger.debug(f'Dumping metadata to {out_fname}')
                    _json.dump(nx_meta, f, sort_keys=True,
                               cls=SortedDictEncoder, indent=2)

        if generate_preview:
            preview_fname = fname.replace(_mmf_path, _nx_path) + '.thumb.png'
            if extension == 'tif':
                instr = _get_instr(fname)
                instr_name = instr.name if instr is not None else None
                if instr_name == 'FEI-Quanta200-ESEM-633137':
                    # we know the output size we want for the Quanta
                    output_size = (512, 471)
                    _down_sample(fname,
                                 out_path=preview_fname,
                                 output_size=output_size)
                else:
                    factor = 2
                    _down_sample(fname,
                                 out_path=preview_fname,
                                 factor=factor)

            else:
                s = _hs.load(fname, lazy=True)

                # If s is a list of signals, use just the first one for
                # our purposes
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
                else:
                    _logger.info(f'Preview already exists: {preview_fname}')

    return nx_meta, preview_fname


def flatten_dict(d, parent_key='', separator=' '):
    """
    Take a nested dictionary and flatten it into a single level, separating
    the levels by a string as specified by `separator`

    Cribbed from: https://stackoverflow.com/a/6027615/1435788

    Parameters
    ----------
    d : dict
        The dictionary to flatten
    parent_key : str
        The "root" key to add to add to the existing keys
    separator : str
        The string to use to separate values in the flattened keys (i.e.
        {'a': {'b': 'c'}} would become {'a' + sep + 'b': 'c'})

    Returns
    -------
    flattened_dict : str
        The dictionary with depth one, with nested dictionaries flattened
        into root-level keys
    """
    items = []
    for k, v in d.items():
        new_key = parent_key + separator + k if parent_key else k
        if isinstance(v, _collections.MutableMapping):
            items.extend(flatten_dict(v, new_key, separator=separator).items())
        else:
            items.append((new_key, v))

    flattened_dict = dict(items)

    return flattened_dict
