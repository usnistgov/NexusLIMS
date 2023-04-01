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
"""
Parses and extract metadata from files saved by the TIA software.

Handles files saved by FEI's (now Thermo Fisher Scientific) TIA (Tecnai Imaging and
Analysis) software. This software package saves data in two types of files: ``.ser``
and ``.emi``. The ``.emi`` file contains metadata about the data acquisition, while
the (one or more) ``.ser`` files contain the actual collected data. Thus, access to
both is required for full metadata extraction and preview generation.
"""
import logging
import os
from datetime import datetime as dt
from pathlib import Path
from typing import List, Tuple

import numpy as np
from hyperspy.io import load as hs_load
from hyperspy.signal import BaseSignal

from nexusLIMS.instruments import get_instr_from_filepath
from nexusLIMS.utils import set_nested_dict_value, sort_dict, try_getting_dict_value

logger = logging.getLogger(__name__)


# noinspection PyBroadException
def get_ser_metadata(filename: Path):
    """
    Get metadat from .ser file.

    Returns metadata (as a dict) from an FEI .ser file + its associated .emi
    files, with some non-relevant information stripped.

    Parameters
    ----------
    filename
        Path to FEI .ser file

    Returns
    -------
    metadata : dict
        Metadata of interest which is extracted from the passed files. If
        files cannot be opened, at least basic metadata will be returned (
        creation time, etc.)
    """
    # ObjectInfo present in emi; ser_header_parameters present in .ser
    # ObjectInfo should contain all the interesting metadata,
    # while ser_header_parameters is mostly technical stuff not really of
    # interest to anyone
    warning, emi_filename, ser_error = None, None, False

    # pylint: disable=broad-exception-caught
    try:
        emi_filename, ser_index = get_emi_from_ser(filename)
        s, emi_loaded = _load_ser(emi_filename, ser_index)

    except FileNotFoundError:
        # if emi wasn't found, specifically mention that
        warning = (
            "NexusLIMS could not find a corresponding .emi metadata "
            "file for this .ser file. Metadata extraction will be "
            "limited."
        )
        logger.warning(warning)
        emi_loaded = False
        emi_filename = None

    except Exception:
        # otherwise, HyperSpy could not load the .emi, so give generic warning
        # that .emi could not be loaded for some reason:
        warning = (
            "The .emi metadata file associated with this "
            ".ser file could not be opened by NexusLIMS. "
            "Metadata extraction will be limited."
        )
        logger.warning(warning)
        emi_loaded = False

    if not emi_loaded:
        # pylint: disable=broad-exception-caught

        # if we couldn't load the emi, lets at least open the .ser to pull
        # out the ser_header_info
        try:
            s = hs_load(filename, only_valid_data=True, lazy=True)
        except Exception:
            warning = (
                "The .ser file could not be opened (perhaps file is "
                "corrupted?); Metadata extraction is not possible."
            )
            logger.warning(warning)
            # set s to an empty signal just so we can process some basic
            # metadata using same syntax as if we had read it correctly
            s = BaseSignal(np.zeros(1))
            ser_error = True

    metadata = s.original_metadata.as_dictionary()
    metadata["nx_meta"] = {}

    # if we've already encountered a warning, add that to the metadata,
    if warning:
        metadata["nx_meta"]["Extractor Warning"] = warning
    # otherwise check to ensure we actually have some metadata read from .emi
    elif "ObjectInfo" not in metadata or (
        "ExperimentalConditions" not in metadata["ObjectInfo"]
        and "ExperimentalDescription" not in metadata["ObjectInfo"]
    ):
        warning = (
            "No experimental metadata was found in the "
            "corresponding .emi file for this .ser. "
            "Metadata extraction will be limited."
        )
        logger.warning(warning)
        metadata["nx_meta"]["Extractor Warning"] = warning

    # if we successfully found the .emi file, add it to the metadata
    if emi_filename:
        rel_emi_fname = (
            str(emi_filename).replace(os.environ["mmfnexus_path"] + "/", "")
            if emi_filename
            else None
        )
        metadata["nx_meta"]["emi Filename"] = rel_emi_fname
    else:
        metadata["nx_meta"]["emi Filename"] = None

    # Get the instrument object associated with this file
    instr = get_instr_from_filepath(filename)

    # if we found the instrument, then store the name as string, else None
    instr_name = instr.name if instr is not None else None
    metadata["nx_meta"]["fname"] = filename
    # get the modification time:
    metadata["nx_meta"]["Creation Time"] = dt.fromtimestamp(
        os.path.getmtime(filename),
        tz=instr.timezone if instr else None,
    ).isoformat()
    metadata["nx_meta"]["Instrument ID"] = instr_name

    # we could not read the signal, so add some basic metadata and return
    if ser_error:
        return _handle_ser_error(metadata)

    metadata = parse_basic_info(metadata, s.data.shape, instr)
    metadata = parse_acquire_info(metadata)
    metadata = parse_experimental_conditions(metadata)
    metadata = parse_experimental_description(metadata)

    (
        metadata["nx_meta"]["Data Type"],
        metadata["nx_meta"]["DatasetType"],
    ) = parse_data_type(s, metadata)

    # we don't need to save the filename, it's just for internal processing
    del metadata["nx_meta"]["fname"]

    # sort the nx_meta dictionary (recursively) for nicer display
    metadata["nx_meta"] = sort_dict(metadata["nx_meta"])

    return metadata


def _handle_ser_error(metadata):
    metadata["nx_meta"]["DatasetType"] = "Misc"
    metadata["nx_meta"]["Data Type"] = "Unknown"
    metadata["nx_meta"]["warnings"] = []
    # sort the nx_meta dictionary (recursively) for nicer display
    metadata["nx_meta"] = sort_dict(metadata["nx_meta"])
    del metadata["nx_meta"]["fname"]
    return metadata


def _load_ser(emi_filename: Path, ser_index: int):
    """
    Load an data file given the .emi filename and an index of which signal to use.

    Parameters
    ----------
    emi_filename
        The path to an .emi file
    ser_index
        Which .ser file to load data from, given the .emi file above

    Returns
    -------
    hyperspy.signal.BaseSignal
        The signal loaded by HyperSpy
    bool
        Whether the emi file was successfully loaded (should be true if no Exceptions)
    """
    # approach here is for every .ser we want to examine, load the
    # metadata from the corresponding .emi file. If multiple .ser files
    # are related to this emi, HyperSpy returns a list, so we select out
    # the right signal from that list if that's what is returned

    # make sure to load with "only_valid_data" so data shape is correct
    # loading the emi with HS will try loading the .ser too, so this will
    # fail if there's an issue with the .ser file
    emi_s = hs_load(emi_filename, lazy=True, only_valid_data=True)

    # if there is more than one dataset, emi_s will be a list, so pick
    # out the matching signal from the list, which will be the "index"
    # from the filename minus 1:
    if isinstance(emi_s, list):
        s = emi_s[ser_index - 1]

    # otherwise we should just have a regular signal, so make s the same
    # as the data loaded from the .emi
    elif isinstance(emi_s, BaseSignal):
        s = emi_s

    return s, True


def parse_basic_info(metadata, shape, instrument):
    """
    Parse basic metadata from file.

    Parse the metadata that is saved at specific places within
    the .emi tag structure into a consistent place in the metadata dictionary
    returned by :py:meth:`get_ser_metadata`. Specifically, this method handles
    the creation date, equipment manufacturer, and data shape/type.

    Parameters
    ----------
    metadata : dict
        A metadata dictionary as returned by :py:meth:`get_ser_metadata`
    shape
        The shape of the dataset
    instrument : Instrument
        The instrument this file was collected on

    Returns
    -------
    metadata : dict
        The same metadata dictionary with some values added under the
        root-level ``nx_meta`` key
    """
    # try to set creation time to acquisition time from metadata
    acq_time = try_getting_dict_value(metadata, ["ObjectInfo", "AcquireDate"])
    if acq_time != "not found":
        metadata["nx_meta"]["Creation Time"] = (
            dt.strptime(
                acq_time,
                "%a %b %d %H:%M:%S %Y",
            )
            .replace(tzinfo=instrument.timezone if instrument else None)
            .isoformat()
        )

    # manufacturer is at high level, so parse it now
    manufacturer = try_getting_dict_value(metadata, ["ObjectInfo", "Manufacturer"])
    if manufacturer != "not found":
        metadata["nx_meta"]["Manufacturer"] = manufacturer

    metadata["nx_meta"]["Data Dimensions"] = str(shape)
    metadata["nx_meta"]["warnings"] = []

    # set type to STEM Image by default (this seems to be most common)
    metadata["nx_meta"]["DatasetType"] = "Image"
    metadata["nx_meta"]["Data Type"] = "STEM_Imaging"

    return metadata


def parse_experimental_conditions(metadata):
    """
    Parse experimental conditions.

    Parse the metadata that is saved at specific places within
    the .emi tag structure into a consistent place in the metadata dictionary
    returned by :py:meth:`get_ser_metadata`. Specifically looks at the
    "ExperimentalConditions" node of the metadata structure.

    Parameters
    ----------
    metadata : dict
        A metadata dictionary as returned by :py:meth:`get_ser_metadata`

    Returns
    -------
    metadata : dict
        The same metadata dictionary with some values added under the
        root-level ``nx_meta`` key
    """
    term_mapping = {
        ("DwellTimePath",): "Dwell Time Path (s)",
        ("FrameTime",): "Frame Time (s)",
        ("CameraNamePath",): "Camera Name Path",
        ("Binning",): "Binning",
        ("BeamPosition",): "Beam Position (μm)",
        ("EnergyResolution",): "Energy Resolution (eV)",
        ("IntegrationTime",): "Integration Time (s)",
        ("NumberSpectra",): "Number of Spectra",
        ("ShapingTime",): "Shaping Time (s)",
        ("ScanArea",): "Scan Area",
    }
    base = ["ObjectInfo", "AcquireInfo"]

    if try_getting_dict_value(metadata, base) != "not found":
        metadata = map_keys(term_mapping, base, metadata)

    # remove units from beam position (if present)
    if "Beam Position (μm)" in metadata["nx_meta"]:
        metadata["nx_meta"]["Beam Position (μm)"] = metadata["nx_meta"][
            "Beam Position (μm)"
        ].replace(" um", "")

    return metadata


def parse_acquire_info(metadata):
    """
    Parse acquisition conditions.

    Parse the metadata that is saved at specific places within
    the .emi tag structure into a consistent place in the metadata dictionary
    returned by :py:meth:`get_ser_metadata`. Specifically looks at the
    "AcquireInfo" node of the metadata structure.

    Parameters
    ----------
    metadata : dict
        A metadata dictionary as returned by :py:meth:`get_ser_metadata`

    Returns
    -------
    metadata : dict
        The same metadata dictionary with some values added under the
        root-level ``nx_meta`` key
    """
    term_mapping = {
        ("AcceleratingVoltage",): "Microscope Accelerating Voltage (V)",
        ("Tilt1",): "Microscope Tilt 1",
        ("Tilt2",): "Microscope Tilt 2",
    }
    base = ["ObjectInfo", "ExperimentalConditions", "MicroscopeConditions"]

    if try_getting_dict_value(metadata, base) != "not found":
        metadata = map_keys(term_mapping, base, metadata)

    return metadata  # noqa: RET504


def parse_experimental_description(metadata):
    """
    Parse experimental description.

    Parse the metadata that is saved at specific places within
    the .emi tag structure into a consistent place in the metadata dictionary
    returned by :py:meth:`get_ser_metadata`. Specifically looks at the
    "ExperimentalDescription" node of the metadata structure.

    Parameters
    ----------
    metadata : dict
        A metadata dictionary as returned by :py:meth:`get_ser_metadata`

    Returns
    -------
    metadata : dict
        The same metadata dictionary with some values added under the
        root-level ``nx_meta`` key

    Notes
    -----
    The terms to extract in this section were
    """
    # These terms were captured by looping through a selection of
    # representative .ser/.emi datafiles and running something like the
    # following
    base = ["ObjectInfo", "ExperimentalDescription"]

    experimental_description = try_getting_dict_value(metadata, base)
    if experimental_description != "not found" and isinstance(
        experimental_description,
        dict,
    ):
        term_mapping = {}
        for k in metadata["ObjectInfo"]["ExperimentalDescription"]:
            term, unit = split_fei_metadata_units(k)
            if unit:
                unit = unit.replace("uA", "μA").replace("um", "μm").replace("deg", "°")
            term_mapping[(k,)] = f"{term}" + (f" ({unit})" if unit else "")
            # Make stage position a nested list
            if "Stage" in term:
                term = term.replace("Stage ", "")
                term_mapping[(k,)] = [
                    "Stage Position",
                    f"{term}" + (f" ({unit})" if unit else ""),
                ]
            # Make filter settings a nested list
            if "Filter " in term:
                term = term.replace("Filter ", "")
                term_mapping[(k,)] = [
                    "Tecnai Filter",
                    f"{term.title()}" + (f" ({unit})" if unit else ""),
                ]

        metadata = map_keys(term_mapping, base, metadata)

        # Microscope Mode often has excess spaces, so fix that if needed:
        if "Mode" in metadata["nx_meta"]:
            metadata["nx_meta"]["Mode"] = metadata["nx_meta"]["Mode"].strip()

    return metadata


def get_emi_from_ser(ser_fname: Path) -> Path:
    """
    Get the accompanying `.emi` filename from an ser filename.

    This method assumes that the `.ser` file will be the same name as the `.emi` file,
    but with an underscore and a digit appended. i.e. ``file.emi`` would
    result in `.ser` files named ``file_1.ser``, ``file_2.ser``, etc.

    Parameters
    ----------
    ser_fname
        The absolute path of an FEI TIA `.ser` data file

    Returns
    -------
    emi_fname
        The absolute path of the accompanying `.emi` metadata file
    index : int
        The number of this .ser file (i.e. 1, 2, 3, etc.)

    Raises
    ------
    FileNotFoundError
        If the accompanying .emi file cannot be resolved to be a file
    """
    # separate filename from extension
    filename = ser_fname.parent / ser_fname.stem
    # remove everything after the last underscore and add the .emi extension
    emi_fname = Path("_".join(str(filename).split("_")[:-1]) + ".emi")
    index = int(str(filename).rsplit("_", maxsplit=1)[-1])

    if not emi_fname.is_file():
        msg = f"Could not find .emi file with expected name: {emi_fname}"
        raise FileNotFoundError(msg)
    return emi_fname, index


def split_fei_metadata_units(metadata_term):
    """
    Split metadata into value and units.

    If present, separate a metadata term into its value and units.
    In the FEI metadata structure, units are indicated separated by an
    underscore at the end of the term. i.e. ``High tension_kV`` indicates that
    the `High tension` metadata value has units of `kV`.

    Parameters
    ----------
    metadata_term : str
        The metadata term read from the FEI tag structure

    Returns
    -------
    mdata_and_unit : :obj:`tuple` of :obj:`str`
        A length-2 tuple with the metadata value name as the first
        item and the unit (if present) as the second item
    """
    mdata_and_unit = tuple(metadata_term.split("_"))

    if len(mdata_and_unit) == 1:
        mdata_and_unit = (*mdata_and_unit, None)

    # capitalize any words in metadata term that are all lowercase:
    mdata_term = " ".join(
        [w.title() if w.islower() else w for w in mdata_and_unit[0].split()],
    )
    # replace weird "Stem" capitalization
    mdata_term = mdata_term.replace("Stem ", "STEM ")

    mdata_and_unit = (mdata_term, mdata_and_unit[1])

    return mdata_and_unit


def map_keys(term_mapping, base, metadata):
    """
    Map keys into NexusLIMS metadata structure.

    Given a term mapping dictionary and a metadata dictionary, translate
    the input keys within the "raw" metadata into a parsed value in the
    "nx_meta" metadata structure.

    Parameters
    ----------
    term_mapping : dict
        Dictionary where keys are tuples of strings (the input terms),
        and values are either a single string or a list of strings (the
        output terms).
    base : list
        The 'root' path within the metadata dictionary of where to start
        applying the input terms
    metadata : dict
        A metadata dictionary as returned by :py:meth:`get_ser_metadata`

    Returns
    -------
    metadata : dict
        The same metadata dictionary with some values added under the
        root-level ``nx_meta`` key, as specified by ``term_mapping``

    Notes
    -----
    The ``term_mapping`` parameter should be a dictionary of the form:

    .. code-block:: python

        {
            ('val1_1', 'val1_2') : 'output_val_1',
            ('val1_1', 'val2_2') : 'output_val_2',
            etc.
        }

    Assuming ``base`` is ``['ObjectInfo', 'AcquireInfo']``, this would map
    the term present at ``ObjectInfo.AcquireInfo.val1_1.val1_2`` into
    ``nx_meta.output_val_1``, and ``ObjectInfo.AcquireInfo.val1_1.val2_2`` into
    ``nx_meta.output_val_2``, and so on. If one of the output terms is a list,
    the resulting metadata will be nested. `e.g.` ``['output_val_1',
    'output_val_2']`` would get mapped to ``nx_meta.output_val_1.output_val_2``.
    """
    for in_term in term_mapping:
        out_term = term_mapping[in_term]
        if isinstance(in_term, tuple):
            in_term = list(in_term)  # noqa: PLW2901
        if isinstance(out_term, str):
            out_term = [out_term]
        val = try_getting_dict_value(metadata, base + in_term)
        # only add the value to this list if we found it
        if val != "not found":
            set_nested_dict_value(
                metadata,
                ["nx_meta", *out_term],
                _convert_to_numeric(val),
            )

    return metadata


def parse_data_type(s, metadata):
    """
    Parse the data type from the signal's metadata.

    Determine `"Data Type"` and `"DatasetType"` for the given .ser file based
    off of metadata and signal characteristics. This method is used to
    determine whether the image is TEM or STEM, Image or Diffraction,
    Spectrum or Spectrum Image, etc.

    Due to lack of appropriate metadata written by the FEI software,
    a heuristic of axis limits and size is used to determine whether a
    spectrum's data type is EELS or EDS. This may not be a perfect
    determination.

    Parameters
    ----------
    s : :py:class:`hyperspy.signal.BaseSignal` (or subclass)
        The HyperSpy signal that contains the data of interest
    metadata : dict
        A metadata dictionary as returned by :py:meth:`get_ser_metadata`

    Returns
    -------
    data_type : str
        The string that should be stored at metadata['nx_meta']['Data Type']
    dataset_type : str
        The string that should be stored at metadata['nx_meta']['DatasetType']
    """
    # default value that will be overwritten if the conditions below are met
    dataset_type = "Misc"

    # instrument configuration
    instr_conf = []
    _set_instrument_type(instr_conf, metadata)

    # images have signal dimension of two:
    if s.axes_manager.signal_dimension == 2:  # noqa: PLR2004
        instr_mod, dataset_type = _signal_dim_2(metadata)

    # if signal dimension is 1, it's a spectrum and not an image
    elif s.axes_manager.signal_dimension == 1:
        instr_mod = ["Spectrum"]
        dataset_type = "Spectrum"
        if s.axes_manager.navigation_dimension > 0:
            instr_mod.append("Imaging")
            dataset_type = "SpectrumImage"
        # do some basic axis value analysis to guess signal type since we
        # don't have any indication of EELS vs. EDS; assume 5 keV and above
        # is EDS
        if s.axes_manager.signal_axes[0].high_value > 5000:  # noqa: PLR2004
            if "EDS" not in instr_conf:
                instr_conf.append("EDS")
        # EELS spectra are usually 2048 channels
        elif s.axes_manager.signal_axes[0].size == 2048:  # noqa: PLR2004
            instr_conf.append("EELS")

    data_type = "_".join(instr_conf + instr_mod)

    return data_type, dataset_type


def _set_instrument_type(instr_conf, metadata):
    # sometimes there is no metadata for follow-on signals in an .emi/.ser
    # bundle (i.e. .ser files after the first one)
    if "Mode" in metadata["nx_meta"]:
        if "STEM" in metadata["nx_meta"]["Mode"]:
            instr_conf.append("STEM")
        elif "TEM" in metadata["nx_meta"]["Mode"]:
            instr_conf.append("TEM")
    # if there is no metadata read from .emi, make determination
    # off of instrument (this is really a guess)
    elif metadata["nx_meta"]["Instrument ID"] is not None:
        if "STEM" in metadata["nx_meta"]["Instrument ID"]:
            instr_conf.append("STEM")
        else:
            instr_conf.append("TEM")
    else:
        # default to TEM, (since STEM is technically a sub-technique of TEM)
        instr_conf.append("TEM")


def _signal_dim_2(metadata) -> Tuple[List[str], str]:
    """
    Parse data type for a Signal with "signal dimension" of size 2.

    Parameters
    ----------
    metadata

    Returns
    -------
    list of str
        The instrument mode
    str
        The dataset type
    """
    # default to an image dataset type for 2 dimensional signal
    dataset_type = "Image"
    # instrument modality:
    instr_mod = ["Imaging"]
    if "Mode" in metadata["nx_meta"]:
        if "Image" in metadata["nx_meta"]["Mode"]:
            instr_mod = ["Imaging"]
            dataset_type = "Image"
        elif "Diffraction" in metadata["nx_meta"]["Mode"]:
            # Diffraction mode is only actually diffraction in TEM mode,
            # In STEM, imaging happens in diffraction mode
            if "STEM" in metadata["nx_meta"]["Mode"]:
                instr_mod = ["Imaging"]
                dataset_type = "Image"
            elif "TEM" in metadata["nx_meta"]["Mode"]:
                instr_mod = ["Diffraction"]
                dataset_type = "Diffraction"
    return instr_mod, dataset_type


def _convert_to_numeric(val):
    if isinstance(val, str):
        if "." in val:
            try:
                return float(val)
            except ValueError:
                return val
        else:
            try:
                return int(val)
            except ValueError:
                return val
    else:
        return val
