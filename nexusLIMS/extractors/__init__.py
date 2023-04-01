"""
Extract metadata from various electron microscopy file types.

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
import inspect
import json
import logging
import shutil
from collections import abc
from datetime import datetime as dt
from pathlib import Path
from typing import Any, Callable, Dict, Optional, Tuple

import hyperspy.api_nogui as hs
import numpy as np

from nexusLIMS.instruments import get_instr_from_filepath
from nexusLIMS.utils import current_system_tz, replace_mmf_path
from nexusLIMS.version import __version__

from .basic_metadata import get_basic_metadata
from .digital_micrograph import get_dm3_metadata
from .fei_emi import get_ser_metadata
from .quanta_tif import get_quanta_metadata
from .thumbnail_generator import down_sample_image, sig_to_thumbnail

logger = logging.getLogger(__name__)
PLACEHOLDER_PREVIEW = Path(__file__).parent / "extractor_error.png"

extension_reader_map = {
    "dm3": get_dm3_metadata,
    "dm4": get_dm3_metadata,
    "tif": get_quanta_metadata,
    "ser": get_ser_metadata,
}


def _add_extraction_details(
    nx_meta: Dict,
    extractor_module: Callable,
) -> Dict[str, str]:
    """
    Add extraction details to the NexusLIMS metadata.

    Adds metadata about the extraction process, given an extractor module
    to the ``nx_meta`` metadata dictionary under the ``'NexusLIMS Extraction'``
    sub-key. The ``'Extractor Module'`` metadata key will contain the fully
    qualified path of a given extractor, e.g.
    ``nexusLIMS.extractors.basic_metadata``.

    Note
    ----
    If the ``'NexusLIMS Extraction'`` key already exists in the ``nx_meta``
    metadata dictionary, this method *will* overwrite its value.

    Parameters
    ----------
    nx_meta
        The metadata dictionary as returend by :py:meth:`parse_metadata`
    extractor_module
        The (callable) module for a specific metadata extractor from the
        :py:mod:`~nexusLIMS.extractors` module.

    Returns
    -------
    dict
        An updated ``nx_meta`` dictionary, containing extraction details

    """
    nx_meta["nx_meta"]["NexusLIMS Extraction"] = {
        "Date": dt.now(tz=current_system_tz()).isoformat(),
        "Module": inspect.getmodule(extractor_module).__name__,
        "Version": __version__,
    }

    return nx_meta


def parse_metadata(
    fname: Path,
    *,
    write_output: bool = True,
    generate_preview: bool = True,
    overwrite: bool = True,
) -> Tuple[Optional[Dict[str, Any]], Optional[Path]]:
    """
    Parse metadata from a file and optionaly generate a preview image.

    Given an input filename, read the file, determine what "type" of file (i.e.
    what instrument it came from) it is, filter the metadata (if necessary) to
    what we are interested in, and return it as a dictionary (writing to the
    NexusLIMS directory as JSON by default). Also calls the preview
    generation method, if desired.

    Parameters
    ----------
    fname
        The filename from which to read data
    write_output
        Whether to write the metadata dictionary as a json file in the NexusLIMS
        folder structure
    generate_preview
        Whether to generate the thumbnail preview of this dataset (that
        operation is not done in this method, it is just called from here so
        it can be done at the same time)
    overwrite
        Whether to overwrite the .json metadata file and thumbnail
        image if either exists

    Returns
    -------
    nx_meta : dict or None
        The "relevant" metadata that is of use for NexusLIMS. If None,
        the file could not be opened
    preview_fname : Path or None
        The file path of the generated preview image, or `None` if it was not
        requested
    """
    extension = fname.suffix[1:]

    # Dealing with files we can't parse and extract
    if extension not in extension_reader_map:
        extractor_method = get_basic_metadata
        generate_preview = False
        logger.info(
            "file extension was not in extension_reader_map; "
            "setting generate_preview to False",
        )

    else:
        extractor_method = extension_reader_map[extension]

    nx_meta = extractor_method(fname)
    nx_meta = _add_extraction_details(nx_meta, extractor_method)
    preview_fname = None

    # nx_meta should never be None, because the extractors are defensive and
    # will always return _something_
    if nx_meta is not None:
        # Set the dataset type to Misc if it was not set by the file reader
        if "DatasetType" not in nx_meta["nx_meta"]:
            nx_meta["nx_meta"]["DatasetType"] = "Misc"
            nx_meta["nx_meta"]["Data Type"] = "Miscellaneous"

        if write_output:
            out_fname = replace_mmf_path(fname, ".json")

            if not out_fname.exists() or overwrite:
                # Create the directory for the metadata file, if needed
                out_fname.parent.mkdir(parents=True, exist_ok=True)
                # Make sure that the nx_meta dict comes first in the json output
                out_dict = {"nx_meta": nx_meta["nx_meta"]}
                for k, v in nx_meta.items():
                    if k == "nx_meta":
                        pass
                    else:
                        out_dict[k] = v
                with out_fname.open(mode="w", encoding="utf-8") as f:
                    logger.debug("Dumping metadata to %s", out_fname)
                    json.dump(
                        out_dict,
                        f,
                        sort_keys=False,
                        indent=2,
                        cls=_CustomEncoder,
                    )

    if generate_preview:
        preview_fname = create_preview(fname=fname, overwrite=overwrite)

    return nx_meta, preview_fname


def create_preview(fname: Path, *, overwrite: bool) -> Path:
    """
    Generate a preview image for a given file using one of a few different methods.

    For most files, this method will try to load the file using HyperSpy and generate
    a preview using that library's capabilities.

    Parameters
    ----------
    fname
        The filename from which to read data
    overwrite
        Whether to overwrite the .json metadata file and thumbnail
        image if either exists

    Returns
    -------
    Path
        The filename of the generated preview image
    """
    preview_fname = replace_mmf_path(fname, ".thumb.png")

    extension = fname.suffix[1:]

    if extension == "tif":
        instr = get_instr_from_filepath(fname)
        instr_name = instr.name if instr is not None else None
        if instr_name == "FEI-Quanta200-ESEM-633137_n":
            # we know the output size we want for the Quanta
            output_size = (512, 471)
            down_sample_image(fname, out_path=preview_fname, output_size=output_size)
        else:
            factor = 2
            down_sample_image(fname, out_path=preview_fname, factor=factor)

    else:
        load_options = {"lazy": True}
        if extension == "ser":
            load_options["only_valid_data"] = True

        # noinspection PyBroadException
        try:
            s = hs.load(fname, **load_options)
        except Exception:  # pylint: disable=broad-exception-caught
            logger.warning(
                "Signal could not be loaded by HyperSpy. "
                "Using placeholder image for preview.",
            )
            preview_fname = replace_mmf_path(fname, ".thumb.png")
            shutil.copyfile(PLACEHOLDER_PREVIEW, preview_fname)
            return preview_fname

        # If s is a list of signals, use just the first one for
        # our purposes
        if isinstance(s, list):
            num_sigs = len(s)
            fname = s[0].metadata.General.original_filename
            s = s[0]
            s.metadata.General.title = (
                s.metadata.General.title
                + f' (1 of {num_sigs} total signals in file "{fname}")'
            )
        elif not s.metadata.General.title:
            s.metadata.General.title = s.metadata.General.original_filename.replace(
                extension,
                "",
            ).strip(".")

        # only generate the preview if it doesn't exist, or overwrite
        # parameter is explicitly provided
        if not preview_fname.is_file() or overwrite:
            logger.info("Generating preview: %s", preview_fname)
            # Create the directory for the thumbnail, if needed
            preview_fname.parent.mkdir(
                parents=True,
                exist_ok=True,
            )
            # Generate the thumbnail
            s.compute(show_progressbar=False)
            sig_to_thumbnail(s, out_path=preview_fname)
        else:
            logger.info("Preview already exists: %s", preview_fname)

    return preview_fname


def flatten_dict(_dict, parent_key="", separator=" "):
    """
    Flatten a nested dictionary into a single level.

    Utility method to take a nested dictionary structure and flatten it into a
    single level, separating the levels by a string as specified by
    ``separator``.

    Cribbed from: https://stackoverflow.com/a/6027615/1435788

    Parameters
    ----------
    _dict : dict
        The dictionary to flatten
    parent_key : str
        The "root" key to add to the existing keys
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
    for k, v in _dict.items():
        new_key = parent_key + separator + k if parent_key else k
        if isinstance(v, abc.MutableMapping):
            items.extend(flatten_dict(v, new_key, separator=separator).items())
        else:
            items.append((new_key, v))

    return dict(items)


class _CustomEncoder(json.JSONEncoder):
    """
    Allow non-serializable types to be written in a JSON format.

    A custom JSON Encoder class that will allow certain types to be serialized that are
    not able to be by default (taken from https://stackoverflow.com/a/27050186).
    """

    def default(self, o):
        if isinstance(o, np.integer):
            return int(o)
        if isinstance(o, np.floating):
            return float(o)
        if isinstance(o, np.ndarray):
            return o.tolist()
        if isinstance(o, np.bytes_):
            return o.decode()

        return super().default(o)
