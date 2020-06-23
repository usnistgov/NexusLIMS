"""
This module contains the code used to harvest metadata from various file types
generated from instruments in the Electron Microscopy Nexus facility.

Extractors should return a dictionary containing the values to be displayed
in NexusLIMS as a sub-dictionary under the key ``nx_meta``. The remaining keys
will be for the metadata as extracted. Under ``nx_meta``, a few keys are
expected (although not enforced):

* ``'Creation Time'`` - ISO format date and time as a string
* ``'Data Type'`` - a human-readable description of the data type separated by
  underscores - e.g "STEM_Imaging", "TEM_EDS", etc.
* ``'DatasetType'`` - determines the value of the Type attribute for the dataset
  (defined in the schema)
* ``'Data Dimensions'`` - dimensions of the dataset, surrounded by parentheses,
  separated by commas as a string- e.g. '(12, 1024, 1024)'
* ``'Instrument ID'`` - instrument PID pulled from the instrument database
"""
import os as _os
import json as _json
import pathlib as _pathlib
import numpy as _np
from .quanta_tif import get_quanta_metadata
from .digital_micrograph import get_dm3_metadata
from .fei_emi import get_ser_metadata
from .thumbnail_generator import sig_to_thumbnail as _s2thumb
from .thumbnail_generator import down_sample_image as _down_sample
from nexusLIMS.instruments import get_instr_from_filepath as _get_instr
import hyperspy.api_nogui as _hs
import logging as _logging
import collections as _collections

_logger = _logging.getLogger(__name__)

extension_reader_map = {
    'dm3': get_dm3_metadata,
    'dm4': get_dm3_metadata,
    'tif': get_quanta_metadata,
    'ser': get_ser_metadata
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
            nx_meta['nx_meta']['Data Type'] = 'Miscellaneous'

        if write_output:
            out_fname = fname.replace(_os.environ["mmfnexus_path"], _os.environ["nexusLIMS_path"]) + '.json'
            if not _os.path.isfile(out_fname) or overwrite:
                # Create the directory for the metadata file, if needed
                _pathlib.Path(_os.path.dirname(out_fname)).mkdir(parents=True,
                                                                 exist_ok=True)
                # Make sure that the nx_meta dict comes first in the json output
                out_dict = {'nx_meta': nx_meta['nx_meta']}
                for k, v in nx_meta.items():
                    if k == 'nx_meta':
                        pass
                    else:
                        out_dict[k] = v
                with open(out_fname, 'w') as f:
                    _logger.debug(f'Dumping metadata to {out_fname}')
                    _json.dump(out_dict, f, sort_keys=False,
                               indent=2, cls=_CustomEncoder)

        if generate_preview:
            preview_fname = fname.replace(_os.environ["mmfnexus_path"], _os.environ["nexusLIMS_path"]) + '.thumb.png'
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
                load_options = {'lazy': True}
                if extension == 'ser':
                    load_options['only_valid_data'] = True

                s = _hs.load(fname, **load_options)

                # If s is a list of signals, use just the first one for
                # our purposes
                if isinstance(s, list):
                    num_sigs = len(s)
                    fname = s[0].metadata.General.original_filename
                    s = s[0]
                    s.metadata.General.title = \
                        s.metadata.General.title + \
                        f' (1 of {num_sigs} total signals in file "{fname}")'
                elif s.metadata.General.title == '':
                    s.metadata.General.title = \
                        s.metadata.General.original_filename.replace(
                            extension, '').strip('.')

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
    Utility method to take a nested dictionary structure and flatten it into a
    single level, separating the levels by a string as specified by
    ``separator``

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


class _CustomEncoder(_json.JSONEncoder):
    """
    A custom JSON Encoder class that will allow certain types to be
    serialized that are not able to be by default (taken from
    https://stackoverflow.com/a/27050186)
    """
    def default(self, obj):
        if isinstance(obj, _np.integer):
            return int(obj)
        elif isinstance(obj, _np.floating):
            return float(obj)
        elif isinstance(obj, _np.ndarray):
            return obj.tolist()
        elif isinstance(obj, _np.bytes_):
            return obj.decode()
        else:
            return super(_CustomEncoder, self).default(obj)