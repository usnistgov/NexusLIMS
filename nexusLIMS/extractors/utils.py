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
"""Methods (primarily intended to be private) that are used by the other extractors."""

import logging
import re
import shutil
import tarfile
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Dict, List, Optional

from hyperspy.io_plugins.digital_micrograph import DigitalMicrographReader, ImageObject

from nexusLIMS.utils import set_nested_dict_value, try_getting_dict_value

logger = logging.getLogger(__name__)


def _coerce_to_list(meta_key):
    if isinstance(meta_key, str):
        return [meta_key]
    return meta_key


def _set_acquisition_device_name(mdict: Dict, pre_path: List[str]):
    val = try_getting_dict_value(mdict, [*pre_path, "Acquisition", "Device", "Name"])
    if val == "not found":
        val = try_getting_dict_value(mdict, [*pre_path, "DataBar", "Device Name"])
    if val != "not found":
        set_nested_dict_value(mdict, ["nx_meta", "Acquisition Device"], val)


def _set_exposure_time(mdict: Dict, pre_path: List[str]):
    val = try_getting_dict_value(
        mdict,
        [*pre_path, "Acquisition", "Parameters", "High Level", "Exposure (s)"],
    )
    if val == "not found":
        val = try_getting_dict_value(mdict, [*pre_path, "DataBar", "Exposure Time (s)"])
    if val != "not found":
        set_nested_dict_value(mdict, ["nx_meta", "Exposure Time (s)"], val)


def _set_gms_version(mdict: Dict, pre_path: List[str]):
    val = try_getting_dict_value(mdict, [*pre_path, "GMS Version", "Created"])
    if val != "not found":
        set_nested_dict_value(mdict, ["nx_meta", "GMS Version"], val)


def _set_camera_binning(mdict: Dict, pre_path: List[str]):
    val = try_getting_dict_value(
        mdict,
        [*pre_path, "Acquisition", "Parameters", "High Level", "Binning"],
    )
    if val != "not found":
        set_nested_dict_value(mdict, ["nx_meta", "Binning (Horizontal)"], val[0])
        set_nested_dict_value(mdict, ["nx_meta", "Binning (Vertical)"], val[1])


def _set_image_processing(mdict: Dict, pre_path: List[str]):
    #   ImageTags.Acquisition.Parameters["High Level"].Processing will be
    #   something like "Gain normalized" - not just for EELS so move this to
    #   general
    val = try_getting_dict_value(
        mdict,
        [*pre_path, "Acquisition", "Parameters", "High Level", "Processing"],
    )
    if val != "not found":
        set_nested_dict_value(mdict, ["nx_meta", "Camera/Detector Processing"], val)


def _set_eels_meta(mdict, base, meta_key):
    val = try_getting_dict_value(mdict, base + meta_key)
    # only add the value to this list if we found it, and it's not
    # one of the "facility-wide" set values that do not have any meaning:
    if val != "not found":
        # add last value of each parameter to the "EELS" sub-tree of nx_meta
        set_nested_dict_value(mdict, ["nx_meta", "EELS"] + [meta_key[-1]], val)


def _set_eels_spectrometer_meta(mdict, base, meta_key):
    val = try_getting_dict_value(mdict, base + meta_key)
    if val != "not found":
        # add last value of each param to the "EELS" sub-tree of nx_meta
        set_nested_dict_value(
            mdict,
            ["nx_meta", "EELS"] + ["Spectrometer " + meta_key[0]],
            val,
        )


def _set_eels_processing(mdict, pre_path):
    # Process known tags under "processing":
    #   ImageTags.Processing will be a list of things done (in multiple
    #   TagGroups) - things like Compute thickness, etc.
    val = try_getting_dict_value(mdict, [*pre_path, "Processing"])
    if val != "not found" and isinstance(val, dict):
        # if val is a dict, then there were processing steps applied
        eels_ops = []
        for _, v in val.items():
            # k will be TagGroup0, TagGroup1, etc.
            # v will be dictionaries specifying the process step
            # AlignSIByPeak, DataPicker, SpectrumCalibrate,
            # Compute Thickness, Background Removal, Signal Integration
            operation = v["Operation"]
            param = v["Parameters"]
            if operation == "AlignSIByPeak":
                eels_ops.append("Aligned parent SI By Peak")
            elif operation == "Background Removal":
                val = try_getting_dict_value(param, ["Model"])
                if val != "not found":
                    set_nested_dict_value(
                        mdict,
                        ["nx_meta", "EELS", "Background Removal Model"],
                        val,
                    )
                eels_ops.append(operation)
            elif operation == "SpectrumCalibrate":
                eels_ops.append("Calibrated Post-acquisition")
            elif operation == "Compute Thickness":
                mdict = _process_thickness_metadata(mdict, [*pre_path, "EELS"])
                eels_ops.append(operation)
            elif operation == "DataPicker":
                eels_ops.append("Extracted from SI")
            elif operation == "Signal Integration":
                eels_ops.append(operation)
        if eels_ops:
            # remove duplicates (convert to set) and sort alphabetically:
            set_nested_dict_value(
                mdict,
                ["nx_meta", "EELS", "Processing Steps"],
                ", ".join(sorted(set(eels_ops))),
            )


def _process_thickness_metadata(mdict, base):
    abs_thick = try_getting_dict_value(
        mdict,
        [*base, "Thickness", "Absolute", "Measurement"],
    )
    abs_units = try_getting_dict_value(mdict, [*base, "Thickness", "Absolute", "Units"])
    abs_mfp = try_getting_dict_value(
        mdict,
        [*base, "Thickness", "Absolute", "Mean Free Path"],
    )
    rel_thick = try_getting_dict_value(
        mdict,
        [*base, "Thickness", "Relative", "Measurement"],
    )
    if abs_thick != "not found":
        set_nested_dict_value(
            mdict,
            ["nx_meta", "EELS", f"Thickness (absolute) [{abs_units}]"],
            abs_thick,
        )
    if abs_mfp != "not found":
        set_nested_dict_value(
            mdict,
            ["nx_meta", "EELS", "Thickness (absolute) mean free path"],
            abs_mfp[0],
        )
    if rel_thick != "not found":
        set_nested_dict_value(
            mdict,
            ["nx_meta", "EELS", "Thickness (relative) [t/λ]"],
            rel_thick,
        )

    return mdict


def _set_eds_meta(mdict, base, meta_key):
    val = try_getting_dict_value(mdict, base + meta_key)
    # only add the value to this list if we found it, and it's not
    # one of the "facility-wide" set values that do not have any meaning:
    if val != "not found":
        # add last value of each parameter to the "EDS" sub-tree of nx_meta
        set_nested_dict_value(
            mdict,
            ["nx_meta", "EDS"] + [meta_key[-1] if len(meta_key) > 1 else meta_key[0]],
            val,
        )


def _set_si_meta(mdict, pre_path, meta_key):
    val = try_getting_dict_value(mdict, [*pre_path, "SI", *meta_key])
    if val != "not found":
        # add last value of each parameter to the "EDS" sub-tree of
        # nx_meta
        set_nested_dict_value(mdict, ["nx_meta", "EDS"] + [meta_key[-1]], val)


def _try_decimal(val):
    try:
        val = Decimal(val)
        val = float(val)
    except (ValueError, InvalidOperation):
        pass
    return val


def _parse_filter_settings(info_dict, tecnai_info):
    try:
        info_dict["Filter_Settings"] = {}
        tecnai_filter_info = tecnai_info[
            tecnai_info.index("Filter related settings:") + 1 :
        ]
        # String
        info_dict["Filter_Settings"]["Mode"] = _find_val("Mode: ", tecnai_filter_info)
        # Decimal (eV/channel)  # noqa: ERA001
        tmp = _find_val("Selected dispersion: ", tecnai_filter_info)
        if tmp is not None:
            tmp = re.sub(r"\[eV/Channel\]", "", tmp)
            info_dict["Filter_Settings"]["Dispersion"] = _try_decimal(tmp)

        # Decimal (millimeter)  # noqa: ERA001
        tmp = _find_val("Selected aperture: ", tecnai_filter_info)
        if tmp is not None:
            tmp = tmp.strip("m")
            info_dict["Filter_Settings"]["Aperture"] = _try_decimal(tmp)

        # Decimal (eV)  # noqa: ERA001
        tmp = _find_val("Prism shift: ", tecnai_filter_info)
        if tmp is not None:
            tmp = re.sub(r"\[eV\]", "", tmp)
            info_dict["Filter_Settings"]["Prism_Shift"] = _try_decimal(tmp)

        # Decimal (eV)  # noqa: ERA001
        tmp = _find_val("Drift tube: ", tecnai_filter_info)
        if tmp is not None:
            tmp = re.sub(r"\[eV\]", "", tmp)
            info_dict["Filter_Settings"]["Drift_Tube"] = _try_decimal(tmp)

        # Decimal (eV)  # noqa: ERA001
        tmp = _find_val("Total energy loss: ", tecnai_filter_info)
        if tmp is not None:
            tmp = re.sub(r"\[eV\]", "", tmp)
            info_dict["Filter_Settings"]["Total_Energy_Loss"] = _try_decimal(tmp)
    except ValueError:
        logger.info("Filter settings not found in Tecnai microscope info")

    return info_dict


def _zero_data_in_dm3(
    filename: Path,
    out_filename: Optional[Path] = None,
    *,
    compress=True,
) -> Path:
    """
    Zero out data in a DM3 file.

    Helper method that will overwrite the data in a dm3 image file  with
    zeros and save it as either another dm3, or as a compressed archive (used
    for creating files for the test suite that don't take up tons of space).
    Since the resulting file is just some text metadata and zeros, it should
    be highly compressible (initial tests allowed for a 16MB file to be
    compressed to ~100KB).

    Parameters
    ----------
    filename
        Path to file to be modified
    out_filename
        Name with which to save the output file. If None, it will be
        automatically generated from the ``filename``.
    compress
        Whether to compress the files into a tar.gz file

    Returns
    -------
    Path
        The path of the compressed (or zeroed) file
    """
    # zero out extent of data in DM3 file and compress to tar.gz:
    if not out_filename:
        mod_fname = filename.parent / (filename.stem + "_dataZeroed" + filename.suffix)
    else:
        mod_fname = out_filename

    shutil.copyfile(filename, mod_fname)

    # Do some lower-level reading on the .dm3 file to get the ImageObject refs
    with filename.open(mode="rb") as f:
        dm_reader = DigitalMicrographReader(f)
        dm_reader.parse_file()
        images = [
            ImageObject(im_dict, f) for im_dict in dm_reader.get_image_dictionaries()
        ]

    # write zeros to the file in the data block (offset + size in bytes
    # information is obtained from the ImageObject ref)
    # NB: currently this is just tested for single-image .dm3 files. Spectra
    # and image stacks will probably work differently.
    with mod_fname.open(mode="r+b") as f:
        f.seek(images[0].imdict.ImageData.Data.offset)
        f.write(b"\x00" * images[0].imdict.ImageData.Data.size_bytes)

    # compress the output, if requested
    if compress:
        tar_path = Path(f"{mod_fname}.tar.gz")
        with tarfile.open(tar_path, "w:gz") as tar:
            tar.add(mod_fname)
        out_fpath = tar_path
        mod_fname.unlink()
    else:
        out_fpath = mod_fname

    return out_fpath


def _find_val(s_to_find, list_to_search):
    """
    Find a value in a list.

    Return the first value in list_to_search that contains s_to_find, or
    None if it is not found.

    Note: If needed, this could be improved to use regex instead, which
          would provide more control over the patterns to return
    """
    res = [x for x in list_to_search if s_to_find in x]
    if len(res) > 0:
        res = res[0]
        # remove the string we searched for from the beginning of the res
        return re.sub("^" + s_to_find, "", res)

    return None
