#  NIST Public License - 2023
#
#  See the LICENSE file in the root of this project
#
"""Parse and extract metadata from files saved by Gatan's DigitalMicrograph software."""
import logging
import os
from datetime import datetime as dt
from pathlib import Path
from struct import error
from typing import Dict, List

import numpy as np
from hyperspy.exceptions import (
    DM3DataTypeError,
    DM3FileVersionError,
    DM3TagError,
    DM3TagIDError,
    DM3TagTypeError,
)
from hyperspy.io import load as hs_load

from nexusLIMS.extractors.utils import (
    _coerce_to_list,
    _find_val,
    _parse_filter_settings,
    _set_acquisition_device_name,
    _set_camera_binning,
    _set_eds_meta,
    _set_eels_meta,
    _set_eels_processing,
    _set_eels_spectrometer_meta,
    _set_exposure_time,
    _set_gms_version,
    _set_image_processing,
    _set_si_meta,
    _try_decimal,
)
from nexusLIMS.instruments import get_instr_from_filepath
from nexusLIMS.utils import (
    get_nested_dict_key,
    get_nested_dict_value_by_path,
    remove_dict_nones,
    remove_dtb_element,
    set_nested_dict_value,
    sort_dict,
    try_getting_dict_value,
)

logger = logging.getLogger(__name__)


def get_dm3_metadata(filename: Path):  # noqa: PLR0912
    """
    Get metadata from a dm3 or dm4 file.

    Returns the metadata from a .dm3 file saved by Digital Micrograph, with some
    non-relevant information stripped out, and instrument specific metadata parsed and
    added by one of the instrument-specific parsers.

    Parameters
    ----------
    filename : str
        path to a .dm3 file saved by Gatan's Digital Micrograph

    Returns
    -------
    metadata : dict or None
        The extracted metadata of interest. If None, the file could not be opened
    """
    # We do lazy loading so we don't actually read the data from the disk to
    # save time and memory.
    try:
        s = hs_load(filename, lazy=True)
    except (
        DM3DataTypeError,
        DM3FileVersionError,
        DM3TagError,
        DM3TagIDError,
        DM3TagTypeError,
        error,
    ) as exc:
        logger.warning(
            "File reader could not open %s, received exception: %s",
            filename,
            repr(exc),
        )
        return None

    if isinstance(s, list):
        # s is a list, rather than a single signal
        m_list = [{}] * len(s)
        for i, _ in enumerate(s):
            m_list[i] = s[i].original_metadata
    else:
        s = [s]
        m_list = [s[0].original_metadata]

    for i, m_tree in enumerate(m_list):
        # Important trees:
        #   DocumentObjectList
        #     Contains information about the display of the information, including bits
        #     about annotations that are included on top of the image data, the CLUT
        #     (color look-up table), data min/max.
        #
        #   ImageList
        #     Contains the actual image information

        # Remove the trees that are not of interest:
        for tag in [
            "ApplicationBounds",
            "LayoutType",
            "DocumentTags",
            "HasWindowPosition",
            "ImageSourceList",
            "Image_Behavior",
            "InImageMode",
            "MinVersionList",
            "NextDocumentObjectID",
            "PageSetup",
            "Page_Behavior",
            "SentinelList",
            "Thumbnails",
            "WindowPosition",
            "root",
        ]:
            m_tree = remove_dtb_element(m_tree, tag)  # noqa: PLW2901

        # Within the DocumentObjectList tree, we really only care about the
        # AnnotationGroupList for each TagGroup, so go into each TagGroup and
        # delete everything but that...
        # NB: the hyperspy DictionaryTreeBrowser __iter__ function returns each
        #   tree element as a tuple containing the tree name and the actual
        #   tree, so we loop through the tag names by taking the first part
        #   of the tuple:
        for tg_name, tag in m_tree.DocumentObjectList:
            # tg_name should be 'TagGroup0', 'TagGroup1', etc.
            keys = tag.keys()
            # we want to keep this, so remove from the list to loop through
            if "AnnotationGroupList" in keys:
                keys.remove("AnnotationGroupList")
            for k in keys:
                m_tree = remove_dtb_element(  # noqa: PLW2901
                    m_tree,
                    f"DocumentObjectList.{tg_name}.{k}",
                )

        for tg_name, tag in m_tree.ImageList:
            # tg_name should be 'TagGroup0', 'TagGroup1', etc.
            keys = tag.keys()
            # We want to keep 'ImageTags' and 'Name', so remove from list
            keys.remove("ImageTags")
            keys.remove("Name")
            for k in keys:
                # k should be in ['ImageData', 'UniqueID']
                m_tree = remove_dtb_element(  # noqa: PLW2901
                    m_tree,
                    f"ImageList.{tg_name}.{k}",
                )

        m_list[i] = m_tree.as_dictionary()

        # Get the instrument object associated with this file
        instr = get_instr_from_filepath(filename)
        # get the modification time (as ISO format):
        mtime = os.path.getmtime(filename)
        mtime_iso = dt.fromtimestamp(
            mtime,
            tz=instr.timezone if instr else None,
        ).isoformat()
        # if we found the instrument, then store the name as string, else None
        instr_name = instr.name if instr is not None else None
        m_list[i]["nx_meta"] = {}
        m_list[i]["nx_meta"]["fname"] = str(filename)
        # set type to Image by default
        m_list[i]["nx_meta"]["DatasetType"] = "Image"
        m_list[i]["nx_meta"]["Data Type"] = "TEM_Imaging"
        m_list[i]["nx_meta"]["Creation Time"] = mtime_iso
        m_list[i]["nx_meta"]["Data Dimensions"] = str(s[i].data.shape)
        m_list[i]["nx_meta"]["Instrument ID"] = instr_name
        m_list[i]["nx_meta"]["warnings"] = []
        m_list[i] = parse_dm3_microscope_info(m_list[i])
        m_list[i] = parse_dm3_eels_info(m_list[i])
        m_list[i] = parse_dm3_eds_info(m_list[i])
        m_list[i] = parse_dm3_spectrum_image_info(m_list[i])

        # if the instrument name is None, this check will be false, otherwise
        # look for the instrument in our list of instrument-specific parsers:
        if instr_name in _instr_specific_parsers:
            m_list[i] = _instr_specific_parsers[instr_name](m_list[i])

        # we don't need to save the filename, it's just for internal processing
        del m_list[i]["nx_meta"]["fname"]

        # sort the nx_meta dictionary (recursively) for nicer display
        m_list[i]["nx_meta"] = sort_dict(m_list[i]["nx_meta"])

    # return the first dictionary, which should contain the most information:
    return remove_dict_nones(m_list[0])


def parse_643_titan(mdict):
    """
    Add/adjust metadata specific to the 643 FEI Titan.

    ('`FEI-Titan-STEM-630901 in *********`')

    Parameters
    ----------
    mdict : dict
        "raw" metadata dictionary as parsed by :py:func:`get_dm3_metadata`

    Returns
    -------
    mdict : dict
        The original metadata dictionary with added information specific to
        files originating from this microscope with "important" values contained
        under the ``nx_meta`` key at the root level
    """
    # The 643 Titan will likely have session info defined, but it may not be
    # accurate, so add it to the warning list
    for val in ["Detector", "Operator", "Specimen"]:
        mdict["nx_meta"]["warnings"].append([val])

    # the 643Titan sets the Imaging mode to "EFTEM DIFFRACTION" when an
    # actual diffraction pattern is taken
    if (
        "Imaging Mode" in mdict["nx_meta"]
        and mdict["nx_meta"]["Imaging Mode"] == "EFTEM DIFFRACTION"
    ):
        mdict["nx_meta"]["DatasetType"] = "Diffraction"
        mdict["nx_meta"]["Data Type"] = "TEM_EFTEM_Diffraction"

    return mdict


def parse_642_titan(mdict):
    """
    Add/adjust metadata specific to the 642 FEI Titan.

    ('`FEI-Titan-TEM-635816 in **********`')

    Parameters
    ----------
    mdict : dict
        "raw" metadata dictionary as parsed by :py:func:`get_dm3_metadata`

    Returns
    -------
    mdict : dict
        The original metadata dictionary with added information specific to
        files originating from this microscope with "important" values contained
        under the ``nx_meta`` key at the root level
    """
    # DONE: complete 642 titan metadata parsing including Tecnai tag
    path_to_tecnai = get_nested_dict_key(mdict, "Tecnai")

    if path_to_tecnai is None:
        # For whatever reason, the expected Tecnai Tag is not present,
        # so return to prevent errors below
        return mdict

    tecnai_value = get_nested_dict_value_by_path(mdict, path_to_tecnai)
    microscope_info = tecnai_value["Microscope Info"]
    tecnai_value["Microscope Info"] = process_tecnai_microscope_info(microscope_info)
    set_nested_dict_value(mdict, path_to_tecnai, tecnai_value)

    # - Tecnai info:
    #     _ ImageTags.Tecnai.Microscope_Info['Gun_Name']
    #     _ ImageTags.Tecnai.Microscope_Info['Extractor_Voltage']
    #     _ ImageTags.Tecnai.Microscope_Info['Gun_Lens_No']
    #     _ ImageTags.Tecnai.Microscope_Info['Emission_Current']
    #     _ ImageTags.Tecnai.Microscope_Info['Spot']
    #     _ ImageTags.Tecnai.Microscope_Info['Mode']
    #     _ C2, C3, Obj, Dif lens strength:
    #         - ImageTags.Tecnai.Microscope_Info['C2_Strength', 'C3_Strength',
    #                                            'Obj_Strength', 'Dif_Strength']
    #     _ ImageTags.Tecnai.Microscope_Info['Image_Shift_x'/'Image_Shift_y'])
    #     _ ImageTags.Tecnai.Microscope_Info['Stage_Position_x' (y/z/theta/phi)]
    #     _ C1/C2/Objective/SA aperture sizes:
    #         _ ImageTags.Tecnai.Microscope_Info['(C1/C2/Obj/SA)_Aperture']
    #     _ ImageTags.Tecnai.Microscope_Info['Filter_Settings']['Mode']
    #     _ ImageTags.Tecnai.Microscope_Info['Filter_Settings']['Dispersion']
    #     _ ImageTags.Tecnai.Microscope_Info['Filter_Settings']['Aperture']
    #     _ ImageTags.Tecnai.Microscope_Info['Filter_Settings']['Prism_Shift']
    #     _ ImageTags.Tecnai.Microscope_Info['Filter_Settings']['Drift_Tube']
    #     _ ImageTags.Tecnai.Microscope_Info['Filter_Settings'][
    #           'Total_Energy_Loss']

    term_mapping = {
        "Gun_Name": "Gun Name",
        "Extractor_Voltage": "Extractor Voltage (V)",
        "Camera_Length": "Camera Length (m)",
        "Gun_Lens_No": "Gun Lens #",
        "Emission_Current": "Emission Current (μA)",
        "Spot": "Spot",
        "Mode": "Tecnai Mode",
        "Defocus": "Defocus",
        "C2_Strength": "C2 Lens Strength (%)",
        "C3_Strength": "C3 Lens Strength (%)",
        "Obj_Strength": "Objective Lens Strength (%)",
        "Dif_Strength": "Diffraction Lens Strength (%)",
        "Microscope_Name": "Tecnai Microscope Name",
        "User": "Tecnai User",
        "Image_Shift_x": "Image Shift X (μm)",
        "Image_Shift_y": "Image Shift Y (μm)",
        "Stage_Position_x": ["Stage Position", "X (μm)"],
        "Stage_Position_y": ["Stage Position", "Y (μm)"],
        "Stage_Position_z": ["Stage Position", "Z (μm)"],
        "Stage_Position_theta": ["Stage Position", "θ (°)"],
        "Stage_Position_phi": ["Stage Position", "φ (°)"],
        "C1_Aperture": "C1 Aperture (μm)",
        "C2_Aperture": "C2 Aperture (μm)",
        "Obj_Aperture": "Objective Aperture (μm)",
        "SA_Aperture": "Selected Area Aperture (μm)",
        ("Filter_Settings", "Mode"): ["Tecnai Filter", "Mode"],
        ("Filter_Settings", "Dispersion"): ["Tecnai Filter", "Dispersion (eV/channel)"],
        ("Filter_Settings", "Aperture"): ["Tecnai Filter", "Aperture (mm)"],
        ("Filter_Settings", "Prism_Shift"): ["Tecnai Filter", "Prism Shift (eV)"],
        ("Filter_Settings", "Drift_Tube"): ["Tecnai Filter", "Drift Tube (eV)"],
        ("Filter_Settings", "Total_Energy_Loss"): [
            "Tecnai Filter",
            "Total Energy Loss (eV)",
        ],
    }

    for in_term, out_term in term_mapping.items():
        base = [*list(path_to_tecnai), "Microscope Info"]
        if isinstance(in_term, str):
            in_term = [in_term]  # noqa: PLW2901
        elif isinstance(in_term, tuple):
            in_term = list(in_term)  # noqa: PLW2901
        if isinstance(out_term, str):
            out_term = [out_term]  # noqa: PLW2901
        val = try_getting_dict_value(mdict, base + in_term)
        # only add the value to this list if we found it
        if val != "not found" and val not in ["DO NOT EDIT", "DO NOT ENTER"]:
            set_nested_dict_value(mdict, ["nx_meta", *out_term], val)

    path = [*list(path_to_tecnai), "Specimen Info"]
    val = try_getting_dict_value(mdict, path)
    if val not in ["not found", "Specimen information is not available yet"]:
        set_nested_dict_value(mdict, ["nx_meta", "Specimen"], val)

    # If `Tecnai Mode` is `STEM nP SA Zoom Diffraction`, it's diffraction
    if (
        "Tecnai Mode" in mdict["nx_meta"]
        and mdict["nx_meta"]["Tecnai Mode"] == "STEM nP SA Zoom Diffraction"
    ):
        logger.info(
            'Detected file as Diffraction type based on "Tecnai '
            'Mode" == "STEM nP SA Zoom Diffraction"',
        )
        mdict["nx_meta"]["DatasetType"] = "Diffraction"
        mdict["nx_meta"]["Data Type"] = "STEM_Diffraction"

    # also, if `Operation Mode` is `DIFFRACTION`, it's diffraction
    elif (
        "Operation Mode" in mdict["nx_meta"]
        and mdict["nx_meta"]["Operation Mode"] == "DIFFRACTION"
    ):
        logger.info(
            'Detected file as Diffraction type based on "Operation '
            'Mode" == "DIFFRACTION"',
        )
        mdict["nx_meta"]["DatasetType"] = "Diffraction"
        mdict["nx_meta"]["Data Type"] = "TEM_Diffraction"

    return mdict


def parse_642_jeol(mdict):
    """
    Add/adjust metadata specific to the 642 FEI Titan.

    ('`JEOL-JEM3010-TEM-565989 in *********`')

    Parameters
    ----------
    mdict : dict
        "raw" metadata dictionary as parsed by :py:func:`get_dm3_metadata`

    Returns
    -------
    mdict : dict
        The original metadata dictionary with added information specific to
        files originating from this microscope with "important" values contained
        under the ``nx_meta`` key at the root level
    """
    # Currently, the Stroboscope does not add any metadata items that need to
    # be processed differently than the "default" dm3 tags (and it barely has
    # any metadata anyway), so this method does not need to do anything

    # To try to detect diffraction pattern, we will check the file name
    # against commonly used terms for saving diffraction patterns (not even
    # close to perfect, but at least it's something)
    for s in ["Diff", "SAED", "DP"]:
        if (
            s.lower() in mdict["nx_meta"]["fname"]
            or s.upper() in mdict["nx_meta"]["fname"]
            or s in mdict["nx_meta"]["fname"]
        ):
            logger.info(
                'Detected file as Diffraction type based on "%s" in the filename',
                s,
            )
            mdict["nx_meta"]["DatasetType"] = "Diffraction"
            mdict["nx_meta"]["Data Type"] = "TEM_Diffraction"

    mdict["nx_meta"]["warnings"].append(["DatasetType"])
    mdict["nx_meta"]["warnings"].append(["Data Type"])

    return mdict


_instr_specific_parsers = {
    "FEI-Titan-STEM-630901_n": parse_643_titan,
    "FEI-Titan-TEM-635816_n": parse_642_titan,
    "JEOL-JEM3010-TEM-565989_n": parse_642_jeol,
}


def get_pre_path(mdict: Dict) -> List[str]:
    """
    Get the appropriate pre-path in the metadata tag structure for a given signal.

    Get the path into a dictionary where the important DigitalMicrograph metadata is
    expected to be found. If the .dm3/.dm4 file contains a stack of images, the
    important metadata for NexusLIMS is not at its usual place and is instead under a
    `plan info` tag, so this method will determine if the stack metadata is present and
    return the correct path.

    Parameters
    ----------
    mdict : dict
        A metadata dictionary as returned by :py:meth:`get_dm3_metadata`

    Returns
    -------
    A list containing the subsequent keys that need to be traversed to
    get to the point in the `mdict` where the important metadata is stored
    """
    # test if we have a stack
    stack_val = try_getting_dict_value(
        mdict,
        ["ImageList", "TagGroup0", "ImageTags", "plane info"],
    )
    if stack_val != "not found":
        # we're in a stack
        pre_path = [
            "ImageList",
            "TagGroup0",
            "ImageTags",
            "plane info",
            "TagGroup0",
            "source tags",
        ]
    else:
        pre_path = ["ImageList", "TagGroup0", "ImageTags"]

    return pre_path


def parse_dm3_microscope_info(mdict):
    """
    Parse the "microscope info" metadata.

    Parse the "important" metadata that is saved at specific places within the DM3 tag
    structure into a consistent place in the metadata dictionary returned by
    :py:meth:`get_dm3_metadata`. Specifically looks at the "Microscope Info",
    "Session Info", and "Meta Data" nodes (these are not present on every microscope).

    Parameters
    ----------
    mdict : dict
        A metadata dictionary as returned by :py:meth:`get_dm3_metadata`

    Returns
    -------
    mdict : dict
        The same metadata dictionary with some values added under the
        root-level ``nx_meta`` key
    """
    if "nx_meta" not in mdict:
        mdict["nx_meta"] = {}  # pragma: no cover

    pre_path = get_pre_path(mdict)

    # General "microscope info" .dm3 tags (not present on all instruments):
    for meta_key in [
        "Indicated Magnification",
        "Actual Magnification",
        "Cs(mm)",
        "STEM Camera Length",
        "Voltage",
        "Operation Mode",
        "Specimen",
        "Microscope",
        "Operator",
        "Imaging Mode",
        "Illumination Mode",
        "Name",
        "Field of View (\u00b5m)",
        "Facility",
        ["Stage Position", "Stage Alpha"],
        ["Stage Position", "Stage Beta"],
        ["Stage Position", "Stage X"],
        ["Stage Position", "Stage Y"],
        ["Stage Position", "Stage Z"],
    ]:
        base = [*pre_path, "Microscope Info"]
        meta_key = _coerce_to_list(meta_key)  # noqa: PLW2901

        val = try_getting_dict_value(mdict, base + meta_key)
        # only add the value to this list if we found it, and it's not one of
        # the "facility-wide" set values that do not have any meaning:
        if (
            val != "not found"
            and val not in ["DO NOT EDIT", "DO NOT ENTER"]
            and val != []
        ):
            # change output of "Stage Position" to unicode characters
            if "Stage Position" in meta_key:
                meta_key[-1] = (
                    meta_key[-1]
                    .replace("Alpha", "α")  # noqa: RUF001
                    .replace("Beta", "β")
                    .replace("Stage ", "")
                )
            set_nested_dict_value(mdict, ["nx_meta", *meta_key], val)

    # General "session info" .dm3 tags (sometimes this information is stored
    # here instead of under "Microscope Info":
    for meta_key in ["Detector", "Microscope", "Operator", "Specimen"]:
        base = [*pre_path, "Session Info"]
        meta_key = _coerce_to_list(meta_key)  # noqa: PLW2901

        val = try_getting_dict_value(mdict, base + meta_key)
        # only add the value to this list if we found it, and it's not
        # one of the "facility-wide" set values that do not have any meaning:
        if (
            val != "not found"
            and val not in ["DO NOT EDIT", "DO NOT ENTER"]
            and val != []
        ):
            set_nested_dict_value(mdict, ["nx_meta", *meta_key], val)

    # General "Meta Data" .dm3 tags
    for meta_key in [
        "Acquisition Mode",
        "Format",
        "Signal",
        # this one is seen sometimes in EDS signals:
        ["Experiment keywords", "TagGroup1", "Label"],
    ]:
        base = [*pre_path, "Meta Data"]
        meta_key = _coerce_to_list(meta_key)  # noqa: PLW2901

        val = try_getting_dict_value(mdict, base + meta_key)
        # only add the value to this list if we found it, and it's not
        # one of the "facility-wide" set values that do not have any meaning:
        if (
            val != "not found"
            and val not in ["DO NOT EDIT", "DO NOT ENTER"]
            and val != []
        ):
            if "Label" in meta_key:
                set_nested_dict_value(mdict, ["nx_meta"] + ["Analytic Label"], val)
            else:
                set_nested_dict_value(
                    mdict,
                    ["nx_meta"] + [f"Analytic {lbl}" for lbl in meta_key],
                    val,
                )

    # acquisition device name:
    _set_acquisition_device_name(mdict, pre_path)

    # exposure time:
    _set_exposure_time(mdict, pre_path)

    # GMS version:
    _set_gms_version(mdict, pre_path)

    # camera binning:
    _set_camera_binning(mdict, pre_path)

    # image processing:
    _set_image_processing(mdict, pre_path)

    if (
        "Illumination Mode" in mdict["nx_meta"]
        and "STEM" in mdict["nx_meta"]["Illumination Mode"]
    ):
        mdict["nx_meta"]["Data Type"] = "STEM_Imaging"

    return mdict


def parse_dm3_eels_info(mdict):
    """
    Parse EELS information from the metadata.

    Parses metadata from the DigitalMicrograph tag structure that concerns any
    EELS acquisition or spectrometer settings, placing it in an ``EELS``
    dictionary underneath the root-level ``nx_meta`` node.

    Parameters
    ----------
    mdict : dict
        A metadata dictionary as returned by :py:meth:`get_dm3_metadata`

    Returns
    -------
    mdict : dict
        The metadata dict with all the "EELS-specific" metadata added under ``nx_meta``
    """
    pre_path = get_pre_path(mdict)

    # EELS .dm3 tags of interest:
    base = [*pre_path, "EELS"]
    for meta_key in [
        ["Acquisition", "Exposure (s)"],
        ["Acquisition", "Integration time (s)"],
        ["Acquisition", "Number of frames"],
        ["Experimental Conditions", "Collection semi-angle (mrad)"],
        ["Experimental Conditions", "Convergence semi-angle (mrad)"],
    ]:
        _set_eels_meta(mdict, base, meta_key)

    # different instruments have the spectrometer information in different
    # places...
    if mdict["nx_meta"]["Instrument ID"] == "FEI-Titan-TEM-635816_n":
        base = [*pre_path, "EELS", "Acquisition", "Spectrometer"]
    elif mdict["nx_meta"]["Instrument ID"] == "FEI-Titan-STEM-630901_n":
        base = [*pre_path, "EELS Spectrometer"]
    else:
        base = None
    if base is not None:
        for meta_key in [
            "Aperture label",
            "Dispersion (eV/ch)",
            "Energy loss (eV)",
            "Instrument name",
            "Drift tube enabled",
            "Drift tube voltage (V)",
            "Slit inserted",
            "Slit width (eV)",
            "Prism offset (V)",
            "Prism offset enabled ",
        ]:
            meta_key = [meta_key]  # noqa: PLW2901
            _set_eels_spectrometer_meta(mdict, base, meta_key)

    _set_eels_processing(mdict, pre_path)

    # Set the dataset type to Spectrum if any EELS tags were added
    if "EELS" in mdict["nx_meta"]:
        logger.info("Detected file as Spectrum type based on presence of EELS metadata")
        mdict["nx_meta"]["DatasetType"] = "Spectrum"
        if "STEM" in mdict["nx_meta"]["Illumination Mode"]:
            mdict["nx_meta"]["Data Type"] = "STEM_EELS"
        else:
            mdict["nx_meta"]["Data Type"] = "TEM_EELS"

    return mdict


def parse_dm3_eds_info(mdict):
    """
    Parse EDS information from the dm3 metadata.

    Parses metadata from the DigitalMicrograph tag structure that concerns any
    EDS acquisition or spectrometer settings, placing it in an ``EDS``
    dictionary underneath the root-level ``nx_meta`` node. Metadata values
    that are commonly incorrect or may be placeholders are specified in a
    list under the ``nx_meta.warnings`` node.

    Parameters
    ----------
    mdict : dict
        A metadata dictionary as returned by :py:meth:`get_dm3_metadata`

    Returns
    -------
    mdict : dict
        The metadata dictionary with all the "EDS-specific" metadata
        added as sub-node under the ``nx_meta`` root level dictionary
    """
    pre_path = get_pre_path(mdict)

    # EELS .dm3 tags of interest:
    base = [*pre_path, "EDS"]

    for meta_key in [
        ["Acquisition", "Continuous Mode"],
        ["Acquisition", "Count Rate Unit"],
        ["Acquisition", "Dispersion (eV)"],
        ["Acquisition", "Energy Cutoff (V)"],
        ["Acquisition", "Exposure (s)"],
        ["Count rate"],
        ["Detector Info", "Active layer"],
        ["Detector Info", "Azimuthal angle"],
        ["Detector Info", "Dead layer"],
        ["Detector Info", "Detector type"],
        ["Detector Info", "Elevation angle"],
        ["Detector Info", "Fano"],
        ["Detector Info", "Gold layer"],
        ["Detector Info", "Incidence angle"],
        ["Detector Info", "Solid angle"],
        ["Detector Info", "Stage tilt"],
        ["Detector Info", "Window thickness"],
        ["Detector Info", "Window type"],
        ["Detector Info", "Zero fwhm"],
        ["Live time"],
        ["Real time"],
    ]:
        _set_eds_meta(mdict, base, meta_key)

    # test to see if the SI attribute is present in the metadata dictionary.
    # If so, then some relevant EDS values are located there, rather
    # than in the root-level EDS tag (all the EDS.Acquisition tags from
    # above)
    if try_getting_dict_value(mdict, [*pre_path, "SI"]) != "not found":
        for meta_key in [
            ["Acquisition", "Continuous Mode"],
            ["Acquisition", "Count Rate Unit"],
            ["Acquisition", "Dispersion (eV)"],
            ["Acquisition", "Energy Cutoff (V)"],
            ["Acquisition", "Exposure (s)"],
        ]:
            _set_si_meta(mdict, pre_path, meta_key)

        # for an SI EDS dataset, set "Live time", "Real time" and "Count rate"
        # to the averages stored in the ImageList.TagGroup0.ImageTags.EDS.Images
        # values
        im_dict = try_getting_dict_value(mdict, [*pre_path, "EDS", "Images"])
        if isinstance(im_dict, dict):
            for k, v in im_dict.items():
                if k in mdict["nx_meta"]["EDS"]:
                    del mdict["nx_meta"]["EDS"][k]
                # this should work for 2D (spectrum image) as well as 1D
                # (linescan) datasets since DM saves this information as a 1D
                # list regardless of original data shape
                avg_val = np.array(v).mean()
                set_nested_dict_value(
                    mdict,
                    ["nx_meta", "EDS"] + [f"{k} (SI Average)"],
                    avg_val,
                )

    # Add the .dm3 EDS values to the warnings list, since they might not be
    # accurate
    for meta_key in [
        ["Count rate"],
        ["Detector Info", "Active layer"],
        ["Detector Info", "Azimuthal angle"],
        ["Detector Info", "Dead layer"],
        ["Detector Info", "Detector type"],
        ["Detector Info", "Elevation angle"],
        ["Detector Info", "Fano"],
        ["Detector Info", "Gold layer"],
        ["Detector Info", "Incidence angle"],
        ["Detector Info", "Solid angle"],
        ["Detector Info", "Stage tilt"],
        ["Detector Info", "Window thickness"],
        ["Detector Info", "Window type"],
        ["Detector Info", "Zero fwhm"],
        ["Live time"],
        ["Real time"],
    ]:
        if try_getting_dict_value(mdict, base + meta_key) != "not found":
            mdict["nx_meta"]["warnings"].append(
                ["EDS"] + [meta_key[-1] if len(meta_key) > 1 else meta_key[0]],
            )

    # Set the dataset type to Spectrum if any EDS tags were added
    if "EDS" in mdict["nx_meta"]:
        logger.info("Detected file as Spectrum type based on presence of EDS metadata")
        mdict["nx_meta"]["DatasetType"] = "Spectrum"
        if "STEM" in mdict["nx_meta"]["Illumination Mode"]:
            mdict["nx_meta"]["Data Type"] = "STEM_EDS"
        else:
            # no known files match this mode, so skip for coverage
            mdict["nx_meta"]["Data Type"] = "TEM_EDS"  # pragma: no cover

    return mdict


def parse_dm3_spectrum_image_info(mdict):
    """
    Parse "spectrum image" information from the metadata.

    Parses metadata that concerns any spectrum imaging information (the "SI" tag) and
    places it in a "Spectrum Imaging" dictionary underneath the root-level ``nx_meta``
    node. Metadata values that are commonly incorrect or may be placeholders are
    specified in a list under the ``nx_meta.warnings`` node.

    Parameters
    ----------
    mdict : dict
        A metadata dictionary as returned by :py:meth:`get_dm3_metadata`

    Returns
    -------
    mdict : dict
        The metadata dictionary with all the "EDS-specific" metadata
        added as sub-node under the ``nx_meta`` root level dictionary
    """
    pre_path = get_pre_path(mdict)

    # Spectrum imaging .dm3 tags of interest:
    base = [*pre_path, "SI"]

    for m_in, m_out in [
        (["Acquisition", "Pixel time (s)"], ["Pixel time (s)"]),
        (["Acquisition", "SI Application Mode", "Name"], ["Scan Mode"]),
        (
            ["Acquisition", "Spatial Sampling", "Height (pixels)"],
            ["Spatial Sampling (Vertical)"],
        ),
        (
            ["Acquisition", "Spatial Sampling", "Width (pixels)"],
            ["Spatial Sampling (Horizontal)"],
        ),
        (
            ["Acquisition", "Scan Options", "Sub-pixel sampling"],
            ["Sub-pixel Sampling Factor"],
        ),
    ]:
        val = try_getting_dict_value(mdict, base + m_in)
        # only add the value to this list if we found it, and it's not
        # one of the "facility-wide" set values that do not have any meaning:
        if val != "not found":
            # add last value of each parameter to the "EDS" sub-tree of nx_meta
            set_nested_dict_value(mdict, ["nx_meta", "Spectrum Imaging", *m_out], val)

    # Check spatial drift correction separately:
    drift_per_val = try_getting_dict_value(
        mdict,
        [*base, "Acquisition", "Artefact Correction", "Spatial Drift", "Periodicity"],
    )
    drift_unit_val = try_getting_dict_value(
        mdict,
        [*base, "Acquisition", "Artefact Correction", "Spatial Drift", "Units"],
    )
    if drift_per_val != "not found" and drift_unit_val != "not found":
        val_to_set = f"Spatial drift correction every {drift_per_val} {drift_unit_val}"
        # make sure statement looks gramatically correct
        if drift_per_val == 1:
            val_to_set = val_to_set.replace("(s)", "")
        else:
            val_to_set = val_to_set.replace("(s)", "s")
        # fix for "seconds(s)" (*********...)
        if val_to_set[-2:] == "ss":
            val_to_set = val_to_set[:-1]
        set_nested_dict_value(
            mdict,
            ["nx_meta", "Spectrum Imaging", "Artefact Correction"],
            val_to_set,
        )

    start_val = try_getting_dict_value(mdict, [*base, "Acquisition", "Start time"])
    end_val = try_getting_dict_value(mdict, [*base, "Acquisition", "End time"])
    if start_val != "not found" and end_val != "not found":
        start_dt = dt.strptime(start_val, "%I:%M:%S %p")  # noqa: DTZ007
        end_dt = dt.strptime(end_val, "%I:%M:%S %p")  # noqa: DTZ007
        duration = (end_dt - start_dt).seconds  # Calculate acquisition duration
        set_nested_dict_value(
            mdict,
            ["nx_meta", "Spectrum Imaging", "Acquisition Duration (s)"],
            duration,
        )

    # Set the dataset type to SpectrumImage if it is already a Spectrum ( otherwise it's
    # just a STEM image) and any Spectrum Imaging tags were added
    if (
        "Spectrum Imaging" in mdict["nx_meta"]
        and mdict["nx_meta"]["DatasetType"] == "Spectrum"
    ):
        logger.info(
            "Detected file as SpectrumImage type based on "
            "presence of spectral metadata and spectrum imaging "
            "info",
        )
        mdict["nx_meta"]["DatasetType"] = "SpectrumImage"
        mdict["nx_meta"]["Data Type"] = "Spectrum_Imaging"
        if "EELS" in mdict["nx_meta"]:
            mdict["nx_meta"]["Data Type"] = "EELS_Spectrum_Imaging"
        if "EDS" in mdict["nx_meta"]:
            mdict["nx_meta"]["Data Type"] = "EDS_Spectrum_Imaging"

    return mdict


def process_tecnai_microscope_info(  # noqa: PLR0915
    microscope_info,
    delimiter="\u2028",
):
    """
    Process the Microscope_Info metadata string into a dictionary of key-value pairs.

    This method is only relevant for FEI Titan TEMs that write additional metadata into
    a unicode-delimited string at a certain place in the DM3 tag structure

    Parameters
    ----------
    microscope_info : str
        The string of data obtained from the Tecnai.Microscope_Info leaf of the metadata
    delimiter : str
        The value (a unicode string) used to split the ``microscope_info`` string.

    Returns
    -------
    info_dict : dict
        The information contained in the string, in a more easily-digestible form.
    """
    info_dict = {}
    tecnai_info = microscope_info.split(delimiter)
    info_dict["Microscope_Name"] = _find_val("Microscope ", tecnai_info)  # String
    info_dict["User"] = _find_val("User ", tecnai_info)  # String

    tmp = _find_val("Gun ", tecnai_info)
    info_dict["Gun_Name"] = tmp[: tmp.index(" Extr volt")]
    tmp = tmp[tmp.index(info_dict["Gun_Name"]) + len(info_dict["Gun_Name"]) :]  # String

    tmp = tmp.replace("Extr volt ", "")
    info_dict["Extractor_Voltage"] = int(tmp.split()[0])  # Integer (volts)

    tmp = tmp[tmp.index("Gun Lens ") + len("Gun Lens ") :]
    info_dict["Gun_Lens_No"] = int(tmp.split()[0])  # Integer

    tmp = tmp[tmp.index("Emission ") + len("Emission ") :]
    info_dict["Emission_Current"] = _try_decimal(tmp.split("uA")[0])  # Decimal (microA)

    tmp = _find_val("Mode ", tecnai_info)
    info_dict["Mode"] = tmp[: tmp.index(" Defocus")]  # String
    # 'Mode' should be five terms long, and the last term is either 'Image',
    # 'Diffraction', (or maybe something else)

    # Decimal val (micrometer)
    if "Magn " in tmp:  # Imaging mode
        info_dict["Defocus"] = _try_decimal(tmp.split("Defocus (um) ")[1].split()[0])
    elif "CL " in tmp:  # Diffraction mode
        info_dict["Defocus"] = _try_decimal(tmp.split("Defocus ")[1].split()[0])

    # This value changes based on whether in image or diffraction mode (mag or CL)
    # Integer
    if info_dict["Mode"].split()[4] == "Image":
        info_dict["Magnification"] = int(tmp.split("Magn ")[1].strip("x"))
    # Decimal
    elif info_dict["Mode"].split()[4] == "Diffraction":
        info_dict["Camera_Length"] = _try_decimal(tmp.split("CL ")[1].strip("m"))

    # Integer (1 to 5)
    info_dict["Spot"] = int(_find_val("Spot ", tecnai_info))

    # Decimals - Lens strengths expressed as a "%" value
    info_dict["C2_Strength"] = _try_decimal(_find_val("C2 ", tecnai_info).strip("%"))
    info_dict["C3_Strength"] = _try_decimal(_find_val("C3 ", tecnai_info).strip("%"))
    info_dict["Obj_Strength"] = _try_decimal(_find_val("Obj ", tecnai_info).strip("%"))
    info_dict["Dif_Strength"] = _try_decimal(_find_val("Dif ", tecnai_info).strip("%"))

    # Decimal values (micrometers)
    tmp = _find_val("Image shift ", tecnai_info).strip("um")
    info_dict["Image_Shift_x"] = _try_decimal(tmp.split("/")[0])
    info_dict["Image_Shift_y"] = _try_decimal(tmp.split("/")[1])

    # Decimal values are given in micrometers and degrees
    tmp = _find_val("Stage ", tecnai_info).split(",")
    tmp = [_try_decimal(t.strip(" umdeg")) for t in tmp]
    info_dict["Stage_Position_x"] = tmp[0]
    info_dict["Stage_Position_y"] = tmp[1]
    info_dict["Stage_Position_z"] = tmp[2]
    info_dict["Stage_Position_theta"] = tmp[3]
    info_dict["Stage_Position_phi"] = tmp[4]

    def __read_aperture(val, tecnai_info_):
        """Test if aperture has value or is retracted."""
        try:
            value = _find_val(val, tecnai_info_).strip(" um")
            res = int(value)
        except (ValueError, AttributeError):
            res = None
        return res

    # Either an integer value or None (indicating the aperture was not
    # inserted or tag did not exist in the metadata)
    info_dict["C1_Aperture"] = __read_aperture("C1 Aperture: ", tecnai_info)
    info_dict["C2_Aperture"] = __read_aperture("C2 Aperture: ", tecnai_info)
    info_dict["Obj_Aperture"] = __read_aperture("OBJ Aperture: ", tecnai_info)
    info_dict["SA_Aperture"] = __read_aperture("SA Aperture: ", tecnai_info)

    # Nested dictionary
    info_dict = _parse_filter_settings(info_dict, tecnai_info)

    return info_dict
