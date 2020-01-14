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

# limit our imports to hopefully reduce loading time
import os as _os
import re as _re
import logging as _logging
import shutil as _shutil
import tarfile as _tarfile

from hyperspy.io import load as _hs_load
from hyperspy.exceptions import *
from hyperspy.io_plugins.digital_micrograph import \
    DigitalMicrographReader as _DMReader
from hyperspy.io_plugins.digital_micrograph import ImageObject as _ImageObject

from nexusLIMS.instruments import get_instr_from_filepath as _get_instr
from nexusLIMS.utils import get_nested_dict_key as _get_nest_dict_key
from nexusLIMS.utils import get_nested_dict_value_by_path as \
    _get_nest_dict_val_by_path
from nexusLIMS.utils import set_nested_dict_value as _set_nest_dict_val
from nexusLIMS.utils import try_getting_dict_value as _try_get_dict_val

from struct import error as _struct_error

# from hyperspy.misc.utils import DictionaryTreeBrowser as _DTB
_logger = _logging.getLogger(__name__)


def parse_643_titan(mdict):
    """
    Add/adjust metadata specific to the 643 FEI Titan
    ('`FEI-Titan-STEM-630901 in ***REMOVED***`') to the metadata dictionary

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
    # Currently, the 643 Titan does not add any metadata items that need to
    # be processed differently than the "default" dm3 tags, so for now this
    # method does nothing
    return mdict


def parse_642_titan(mdict):
    """
    Add/adjust metadata specific to the 642 FEI Titan
    ('`FEI-Titan-TEM-635816 in ***REMOVED***`') to the metadata dictionary

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
    path_to_tecnai = _get_nest_dict_key(mdict, 'Tecnai')

    if path_to_tecnai is None:
        # For whatever reason, the expected Tecnai Tag is not present,
        # so return to prevent errors below
        return mdict

    tecnai_value = _get_nest_dict_val_by_path(mdict, path_to_tecnai)
    microscope_info = tecnai_value['Microscope Info']
    tecnai_value['Microscope Info'] = \
        process_tecnai_microscope_info(microscope_info)
    _set_nest_dict_val(mdict, path_to_tecnai, tecnai_value)

    # - Tecnai info:
    #     - ImageTags.Tecnai.Microscope_Info['Gun_Name']
    #     - ImageTags.Tecnai.Microscope_Info['Extractor_Voltage']
    #     - ImageTags.Tecnai.Microscope_Info['Gun_Lens_No']
    #     - ImageTags.Tecnai.Microscope_Info['Emission_Current']
    #     - ImageTags.Tecnai.Microscope_Info['Spot']
    #     - ImageTags.Tecnai.Microscope_Info['Mode']
    #     - C2, C3, Obj, Dif lens strength:
    #         - ImageTags.Tecnai.Microscope_Info['C2_Strength',
    #                                            'C3_Strength',
    #                                            'Obj_Strength',
    #                                            'Dif_Strength']
    #     - ImageTags.Tecnai.Microscope_Info['Image_Shift_x'/'Image_Shift_y'])
    #     - ImageTags.Tecnai.Microscope_Info['Stage_Position_x' (y/z/theta/phi)]
    #     - C1/C2/Objective/SA aperture sizes:
    #         - ImageTags.Tecnai.Microscope_Info['(C1/C2/Obj/SA)_Aperture']
    #     - ImageTags.Tecnai.Microscope_Info['Filter_Settings']['Mode']
    #     - ImageTags.Tecnai.Microscope_Info['Filter_Settings']['Dispersion']
    #     - ImageTags.Tecnai.Microscope_Info['Filter_Settings']['Aperture']
    #     - ImageTags.Tecnai.Microscope_Info['Filter_Settings']['Prism_Shift']
    #     - ImageTags.Tecnai.Microscope_Info['Filter_Settings']['Drift_Tube']
    #     - ImageTags.Tecnai.Microscope_Info['Filter_Settings'][
    #           'Total_Energy_Loss']

    term_mapping = {
        'Gun_Name': 'Gun Name',
        'Extractor_Voltage': 'Extractor Voltage',
        'Gun_Lens_No': 'Gun Lens #',
        'Emission_Current': 'Emission Current',
        'Spot': 'Spot',
        'Mode': 'Tecnai Mode',
        'C2_Strength': 'C2 Lens Strength',
        'C3_Strength': 'C3 Lens Strength',
        'Obj_Strength': 'Objective Lens Strength',
        'Dif_Strength': 'Diffraction Lens Strength',
        'Image_Shift_x': 'Image Shift X',
        'Image_Shift_y': 'Image Shift Y',
        'Stage_Position_x': ['Stage Position', 'Stage X'],
        'Stage_Position_y': ['Stage Position', 'Stage Y'],
        'Stage_Position_z': ['Stage Position', 'Stage Z'],
        'Stage_Position_theta': ['Stage Position', 'Stage θ'],
        'Stage_Position_phi': ['Stage Position', 'Stage φ'],
        'C1_Aperture': 'C1 Aperture',
        'C2_Aperture': 'C2 Aperture',
        'Obj_Aperture': 'Objective Aperture',
        'SA_Aperture': 'Selected Area Aperture',
        ('Filter_Settings', 'Mode'): ['Tecnai Filter Settings', 'Mode'],
        ('Filter_Settings', 'Dispersion'): ['Tecnai Filter Settings',
                                            'Dispersion'],
        ('Filter_Settings', 'Aperture'): ['Tecnai Filter Settings', 'Aperture'],
        ('Filter_Settings', 'Prism_Shift'): ['Tecnai Filter Settings',
                                             'Prism Shift'],
        ('Filter_Settings', 'Drift_Tube'): ['Tecnai Filter Settings', 'Drift '
                                                                      'Tube'],
        ('Filter_Settings', 'Total_Energy_Loss'): ['Tecnai Filter Settings',
                                                   'Total Energy Loss'],
    }

    for in_term in term_mapping.keys():
        base = list(path_to_tecnai) + ['Microscope Info']
        out_term = term_mapping[in_term]
        if isinstance(in_term, str):
            in_term = [in_term]
        elif isinstance(in_term, tuple):
            in_term = list(in_term)
        if isinstance(out_term, str):
            out_term = [out_term]
        val = _try_get_dict_val(mdict, base + in_term)
        # only add the value to this list if we found it
        if val != 'not found' and val not in ['DO NOT EDIT', 'DO NOT ENTER']:
            _set_nest_dict_val(mdict, ['nx_meta'] + out_term, val)

    path = list(path_to_tecnai) + ['Specimen Info']
    val = _try_get_dict_val(mdict, path)
    if val != 'not found' and \
            val != 'Specimen information is not available yet':
        _set_nest_dict_val(mdict, ['nx_meta', 'Specimen'], val)

    return mdict


def parse_642_jeol(mdict):
    """
    Add/adjust metadata specific to the 642 FEI Titan
    ('`JEOL-JEM3010-TEM-565989 in ***REMOVED***`') to the metadata dictionary

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
    return mdict


_instr_specific_parsers = {
    'FEI-Titan-STEM-630901': parse_643_titan,
    'FEI-Titan-TEM-635816': parse_642_titan,
    'JEOL-JEM3010-TEM-565989': parse_642_jeol
}


def get_pre_path(mdict):
    """
    Get the path into a dictionary where the important DigitalMicrograph
    metadata is expected to be found. If the .dm3/.dm4 file contains a stack
    of images, the important metadata for NexusLIMS is not at its usual place
    and is instead under a `plan info` tag, so this method will determine if the
    stack metadata is present and return the correct path. ``pre_path`` will
    be something like ``['ImageList', 'TagGroup0', 'ImageTags', 'plane
    info', 'TagGroup0', 'source tags']``.

    Parameters
    ----------
    mdict : dict
        A metadata dictionary as returned by :py:meth:`get_dm3_metadata`

    Returns
    -------
    pre_path : list
        A list containing the subsequent keys that need to be traversed to
        get to the point in the `mdict` where the important metadata is stored
    """
    # test if we have a stack
    stack_val = _try_get_dict_val(mdict, ['ImageList', 'TagGroup0',
                                          'ImageTags', 'plane info'])
    if stack_val != 'not found':
        # we're in a stack
        pre_path = ['ImageList', 'TagGroup0', 'ImageTags', 'plane info',
                    'TagGroup0', 'source tags']
    else:
        pre_path = ['ImageList', 'TagGroup0', 'ImageTags']

    return pre_path


def parse_dm3_microscope_info(mdict):
    """
    Parse the "important" metadata that is saved at specific places within
    the DM3 tag structure into a consistent place in the metadata dictionary
    returned by :py:meth:`get_dm3_metadata`. Specifically looks at the
    "Microscope Info", "Session Info", and "Meta Data" nodes of the tag
    structure (these are not present on every microscope)

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
    if 'nx_meta' not in mdict: mdict['nx_meta'] = {}

    pre_path = get_pre_path(mdict)

    # General "microscope info" .dm3 tags (not present on all instruments):
    for m in ['Indicated Magnification', 'Actual Magnification', 'Cs(mm)',
              'STEM Camera Length', 'Voltage', 'Operation Mode', 'Specimen',
              'Microscope', 'Operator', 'Imaging Mode', 'Illumination Mode',
              'Name', 'Field of View (\u00b5m)', 'Facility',
              ['Stage Position', 'Stage Alpha'],
              ['Stage Position', 'Stage Beta'],
              ['Stage Position', 'Stage X'],
              ['Stage Position', 'Stage Y'],
              ['Stage Position', 'Stage Z']]:
        base = pre_path + ['Microscope Info']
        if isinstance(m, str):
            m = [m]
        val = _try_get_dict_val(mdict, base + m)
        # only add the value to this list if we found it, and it's not one of
        # the "facility-wide" set values that do not have any meaning:
        if val != 'not found' and val not in ['DO NOT EDIT', 'DO NOT ENTER'] \
                and val != []:
            if 'Stage Position' in m:
                m[-1] = m[-1].replace('Alpha', 'α').replace('Beta', 'β')
            _set_nest_dict_val(mdict, ['nx_meta'] + m, val)

    # General "session info" .dm3 tags (sometimes this information is stored
    # here instead of under "Microscope Info":
    for m in ['Detector', 'Microscope', 'Operator', 'Specimen']:
        base = pre_path + ['Session Info']
        if isinstance(m, str):
            m = [m]

        val = _try_get_dict_val(mdict, base + m)
        # only add the value to this list if we found it, and it's not
        # one of the "facility-wide" set values that do not have any meaning:
        if val != 'not found' and val not in ['DO NOT EDIT', 'DO NOT ENTER'] \
                and val != []:
            _set_nest_dict_val(mdict, ['nx_meta'] + m, val)

    # General "Meta Data" .dm3 tags
    for m in ['Acquisition Mode', 'Format', 'Signal',
              # this one is seen sometimes in EDS signals:
              ['Experiment keywords', 'TagGroup1', 'Label']]:
        base = pre_path + ['Meta Data']
        if isinstance(m, str):
            m = [m]

        val = _try_get_dict_val(mdict, base + m)
        # only add the value to this list if we found it, and it's not
        # one of the "facility-wide" set values that do not have any meaning:
        if val != 'not found' and val not in ['DO NOT EDIT', 'DO NOT ENTER'] \
                and val != []:
            if 'Label' in m:
                _set_nest_dict_val(mdict, ['nx_meta'] + ['Analytic Label'], val)
            else:
                _set_nest_dict_val(mdict, ['nx_meta'] +
                                   [f'Analytic {lbl}' for lbl in m], val)

    # Get acquisition device name:
    val = _try_get_dict_val(mdict,
                            pre_path + ['Acquisition', 'Device', 'Name'])
    if val == 'not found':
        val = _try_get_dict_val(mdict,
                                pre_path + ['DataBar', 'Device Name'])
    if val != 'not found':
        _set_nest_dict_val(mdict, ['nx_meta', 'Acquisition Device'], val)

    # Get exposure time:
    val = _try_get_dict_val(mdict, pre_path +
                            ['Acquisition', 'Parameters', 'High Level',
                             'Exposure (s)'])
    if val == 'not found':
        val = _try_get_dict_val(mdict,
                                pre_path + ['DataBar', 'Exposure Time (s)'])
    if val != 'not found':
        _set_nest_dict_val(mdict, ['nx_meta', 'Exposure Time (s)'], val)

    # Get GMS version:
    val = _try_get_dict_val(mdict, pre_path +
                            ['GMS Version', 'Created'])
    if val != 'not found':
        _set_nest_dict_val(mdict, ['nx_meta', 'GMS Version'], val)

    return mdict


def parse_dm3_eels_info(mdict):
    """
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
        The metadata dictionary with all the "EELS-specific" metadata added as
        sub-node under the ``nx_meta`` root level dictionary
    """
    pre_path = get_pre_path(mdict)

    # EELS .dm3 tags of interest:
    base = pre_path + ['EELS']
    for m in [['Acquisition', 'Exposure (s)'],
              ['Acquisition', 'Integration time (s)'],
              ['Acquisition', 'Number of frames'],
              ["Experimental Conditions", "Collection semi-angle (mrad)"],
              ["Experimental Conditions", "Convergence semi-angle (mrad)"]]:
        val = _try_get_dict_val(mdict, base + m)
        # only add the value to this list if we found it, and it's not
        # one of the "facility-wide" set values that do not have any meaning:
        if val != 'not found':
            # add last value of each parameter to the "EELS" sub-tree of nx_meta
            _set_nest_dict_val(mdict, ['nx_meta', 'EELS'] + [m[-1]], val)

    # different instruments have the spectrometer information in different
    # places...
    if mdict['nx_meta']['Instrument ID'] == 'FEI-Titan-TEM-635816':
        base = pre_path + ['EELS', 'Acquisition', 'Spectrometer']
    elif mdict['nx_meta']['Instrument ID'] == 'FEI-Titan-STEM-630901':
        base = pre_path + ['EELS Spectrometer']
    else:
        base = None
    if base is not None:
        for m in ["Aperture label", "Dispersion (eV/ch)", "Energy loss (eV)",
                  "Instrument name", "Drift tube enabled",
                  "Drift tube voltage (V)", "Slit inserted",
                  "Slit width (eV)", "Prism offset (V)",
                  "Prism offset enabled "]:
            m = [m]
            val = _try_get_dict_val(mdict, base + m)
            if val != 'not found':
                # add last value of each param to the "EELS" sub-tree of nx_meta
                _set_nest_dict_val(mdict,
                                   ['nx_meta', 'EELS'] +
                                   ["Spectrometer " + m[0]],
                                   val)

    return mdict


def parse_dm3_eds_info(mdict):
    """
    Parses metadata from the DigitalMicrograph tag structure that concerns any
    EDS acquisition or spectrometer settings, placing it in an ``EDS``
    dictionary underneath the root-level ``nx_meta`` node.

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
    # TODO: actually implement EDS
    pre_path = get_pre_path(mdict)

    # EELS .dm3 tags of interest:
    base = pre_path + ['EDS']

    for m in [['Acquisition', 'Continuous Mode'],
              ['Acquisition', 'Count Rate Unit'],
              ['Acquisition', 'Dispersion (eV)'],
              ['Acquisition', 'Energy Cutoff (V)'],
              ['Acquisition', 'Exposure (s)'],
              ['Count rate'],
              ['Detector Info', 'Active layer'],
              ['Detector Info', 'Azimuthal angle'],
              ['Detector Info', 'Dead layer'],
              ['Detector Info', 'Detector type'],
              ['Detector Info', 'Elevation angle'],
              ['Detector Info', 'Fano'],
              ['Detector Info', 'Gold layer'],
              ['Detector Info', 'Incidence angle'],
              ['Detector Info', 'Solid angle'],
              ['Detector Info', 'Stage tilt'],
              ['Detector Info', 'Window thickness'],
              ['Detector Info', 'Window type'],
              ['Detector Info', 'Zero fwhm'],
              ['Live time'],
              ['Real time']]:
        val = _try_get_dict_val(mdict, base + m)
        # only add the value to this list if we found it, and it's not
        # one of the "facility-wide" set values that do not have any meaning:
        if val != 'not found':
            # add last value of each parameter to the "EDS" sub-tree of nx_meta
            _set_nest_dict_val(mdict, ['nx_meta', 'EDS'] +
                               [m[-1] if len(m) > 1 else m[0]], val)

    return mdict


def process_tecnai_microscope_info(microscope_info, delimiter=u'\u2028'):
    """
    Process the Microscope_Info metadata string from an FEI Titan
    TEM into a dictionary of key-value pairs

    Parameters
    ----------
    microscope_info : str
        The string of data obtained from the original_metadata.ImageList.\
        TagGroup0.ImageTags.Tecnai.Microscope_Info leaf of the metadata tree
        obtained when loading a .dm3 file as a HyperSpy signal
    delimiter : str
        The value (a unicode string) used to split the ``microscope_info``
        string. Should not need to be provided (this value is hard-coded in
        DigitalMicrograph), but specified as a parameter for future
        flexibility

    Returns
    -------
    info_dict : dict
        The information contained in the string, in a more easily-digestible
        form.
    """

    def __find_val(s_to_find, list_to_search):
        """
        Return the first value in list_to_search that contains s_to_find, or
        None if it is not found

        Note: If needed, this could be improved to use regex instead, which
              would provide more control over the patterns to return
        """
        res = [x for x in list_to_search if s_to_find in x]
        if len(res) > 0:
            res = res[0]
            # remove the string we searched for from the beginning of the res
            return _re.sub("^" + s_to_find, "", res)
        else:
            return None

    info_dict = {}

    # split the string into a list
    tecnai_info = microscope_info.split(delimiter)

    # String
    info_dict['Microscope_Name'] = \
        __find_val('Microscope ', tecnai_info)

    # String
    info_dict['User'] = __find_val('User ', tecnai_info)

    # String
    tmp = __find_val('Gun ', tecnai_info)
    info_dict['Gun_Name'] = tmp[:tmp.index(' Extr volt')]
    tmp = tmp[tmp.index(info_dict['Gun_Name']) + len(info_dict['Gun_Name']):]

    # Integer (volts)
    tmp = tmp.strip('Extr volt ')
    info_dict['Extractor_Voltage'] = int(tmp.split()[0])

    # Integer
    tmp = tmp[tmp.index('Gun Lens ') + len('Gun Lens '):]
    info_dict['Gun_Lens_No'] = int(tmp.split()[0])

    # Float (microAmps)
    tmp = tmp[tmp.index('Emission ') + len('Emission '):]
    info_dict['Emission_Current'] = float(tmp.split('uA')[0])

    # String
    tmp = __find_val('Mode ', tecnai_info)
    info_dict['Mode'] = tmp[:tmp.index(' Defocus')]
    # 'Mode' should be five terms long, and the last term is either 'Image',
    # 'Diffraction', (or maybe something else)

    # Float (micrometer)
    if 'Magn ' in tmp:  # Imaging mode
        info_dict['Defocus'] = float(tmp.split('Defocus (um) ')[1].split()[0])
    elif 'CL ' in tmp:  # Diffraction mode
        info_dict['Defocus'] = float(tmp.split('Defocus ')[1].split()[0])

    # This value changes based on whether in image or diffraction mode
    # (magnification or camera length)
    # Integer
    if info_dict['Mode'].split()[4] == 'Image':
        info_dict['Magnification'] = int(tmp.split('Magn ')[1].strip('x'))
    # Float
    elif info_dict['Mode'].split()[4] == 'Diffraction':
        info_dict['Camera_Length'] = float(tmp.split('CL ')[1].strip('m'))

    # Integer (1 to 5)
    info_dict['Spot'] = int(__find_val('Spot ', tecnai_info))

    # Float - Lens strengths expressed as a "%" value
    info_dict['C2_Strength'] = float(__find_val('C2 ', tecnai_info).strip('%'))
    info_dict['C3_Strength'] = float(__find_val('C3 ', tecnai_info).strip('%'))
    info_dict['Obj_Strength'] = float(
        __find_val('Obj ', tecnai_info).strip('%'))
    info_dict['Dif_Strength'] = float(
        __find_val('Dif ', tecnai_info).strip('%'))

    # Float (micrometers)
    tmp = __find_val('Image shift ', tecnai_info).strip('um')
    info_dict['Image_Shift_x'] = float(tmp.split('/')[0])
    info_dict['Image_Shift_y'] = float(tmp.split('/')[1])

    # Float values are given in micrometers and degrees
    tmp = __find_val('Stage ', tecnai_info).split(',')
    tmp = [float(t.strip(' umdeg')) for t in tmp]
    info_dict['Stage_Position_x'] = tmp[0]
    info_dict['Stage_Position_y'] = tmp[1]
    info_dict['Stage_Position_z'] = tmp[2]
    info_dict['Stage_Position_theta'] = tmp[3]
    info_dict['Stage_Position_phi'] = tmp[4]

    def __read_aperture(val, tecnai_info_):
        """Helper method to test if aperture has value or is retracted"""
        try:
            value = __find_val(val, tecnai_info_)
            value = value.strip(' um')
            res = int(value)
        except (ValueError, AttributeError):
            res = None
        return res

    # Either an integer value or None (indicating the aperture was not
    # inserted or tag did not exist in the metadata)
    info_dict['C1_Aperture'] = __read_aperture('C1 Aperture: ', tecnai_info)
    info_dict['C2_Aperture'] = __read_aperture('C2 Aperture: ', tecnai_info)
    info_dict['Obj_Aperture'] = __read_aperture('OBJ Aperture: ', tecnai_info)
    info_dict['SA_Aperture'] = __read_aperture('SA Aperture: ', tecnai_info)

    # Nested dictionary
    try:
        info_dict['Filter_Settings'] = {}
        tecnai_filter_info = tecnai_info[tecnai_info.index(
            'Filter related settings:') + 1:]
        # String
        info_dict['Filter_Settings']['Mode'] = __find_val('Mode: ',
                                                          tecnai_filter_info)
        # Float (eV/channel)
        tmp = __find_val('Selected dispersion: ', tecnai_filter_info)
        if tmp is not None:
            tmp = _re.sub(r'\[eV/Channel\]', '', tmp)
            info_dict['Filter_Settings']['Dispersion'] = float(tmp)

        # Float (millimeter)
        tmp = __find_val('Selected aperture: ', tecnai_filter_info)
        if tmp is not None:
            tmp = tmp.strip('m')
            info_dict['Filter_Settings']['Aperture'] = float(tmp)

        # Float (eV)
        tmp = __find_val('Prism shift: ', tecnai_filter_info)
        if tmp is not None:
            tmp = _re.sub(r'\[eV\]', '', tmp)
            info_dict['Filter_Settings']['Prism_Shift'] = float(tmp)

        # Float (eV)
        tmp = __find_val('Drift tube: ', tecnai_filter_info)
        if tmp is not None:
            tmp = _re.sub(r'\[eV\]', '', tmp)
            info_dict['Filter_Settings']['Drift_Tube'] = float(tmp)

        # Float (eV)
        tmp = __find_val('Total energy loss: ', tecnai_filter_info)
        if tmp is not None:
            tmp = _re.sub(r'\[eV\]', '', tmp)
            info_dict['Filter_Settings']['Total_Energy_Loss'] = float(tmp)
    except ValueError as _:
        _logger.info('Filter settings not found in Tecnai microscope info')

    return info_dict


def get_dm3_metadata(filename):
    """
    Returns the metadata (as a dict) from a .dm3 file saved by the Gatan's
    Digital Micrograph in the Nexus Microscopy Facility, with some
    non-relevant information stripped out, and instrument specific metadata
    parsed and added by one of the instrument-specific parsers.

    Parameters
    ----------
    filename : str
        path to a .dm3 file saved by Gatan's Digital Micrograph

    Returns
    -------
    metadata : dict or None
        The metadata of interest extracted from the file. If None, the file
        could not be opened
    """
    # We do lazy loading so we don't actually read the data from the disk to
    # save time and memory.
    try:
        s = _hs_load(filename, lazy=True)
    except (DM3DataTypeError, DM3FileVersionError, DM3TagError,
            DM3TagIDError, DM3TagTypeError, _struct_error) as e:
        _logger.warning(f'File reader could not open {filename}, received '
                        f'exception: {e.__repr__()}')
        return None

    if isinstance(s, list):
        # s is a list, rather than a single signal
        m_list = [{}] * len(s)
        for i in range(len(s)):
            m_list[i] = s[i].original_metadata
    else:
        m_list = [s.original_metadata]

    for i, m_tree in enumerate(m_list):
        # Important trees:
        #   DocumentObjectList
        #     Contains information about the display of the information,
        #     including bits about annotations that are included on top of the
        #     image data, the CLUT (color look-up table), data min/max.
        #
        #   ImageList
        #     Contains the actual image information

        # Remove the trees that are not of interest:
        for t in ['ApplicationBounds', 'LayoutType', 'DocumentTags',
                  'HasWindowPosition', 'ImageSourceList',  'Image_Behavior',
                  'InImageMode', 'MinVersionList', 'NextDocumentObjectID',
                  'PageSetup', 'Page_Behavior', 'SentinelList', 'Thumbnails',
                  'WindowPosition', 'root']:
            m_tree = _remove_dtb_element(m_tree, t)

        # Within the DocumentObjectList tree, we really only care about the
        # AnnotationGroupList for each TagGroup, so go into each TagGroup and
        # delete everything but that...
        # NB: the hyperspy DictionaryTreeBrowser __iter__ function returns each
        #   tree element as a tuple containing the tree name and the actual
        #   tree, so we loop through the tag names by taking the first part
        #   of the tuple:
        for tg_name, tg in m_tree.DocumentObjectList:
            # tg_name should be 'TagGroup0', 'TagGroup1', etc.
            keys = tg.keys()
            # we want to keep this, so remove from the list to loop through
            if 'AnnotationGroupList' in keys:
                keys.remove('AnnotationGroupList')
            for k in keys:
                # k should be in ['AnnotationType', 'BackgroundColor',
                # 'BackgroundMode', 'FillMode', etc.]
                m_tree = _remove_dtb_element(m_tree, 'DocumentObjectList.'
                                                     '{}.{}'.format(tg_name, k))

        for tg_name, tg in m_tree.ImageList:
            # tg_name should be 'TagGroup0', 'TagGroup1', etc.
            keys = tg.keys()
            # We want to keep 'ImageTags' and 'Name', so remove from list
            keys.remove('ImageTags')
            keys.remove('Name')
            for k in keys:
                # k should be in ['ImageData', 'UniqueID']
                m_tree = _remove_dtb_element(m_tree, 'ImageList.'
                                                     '{}.{}'.format(tg_name, k))

        # Get the instrument object associated with this file
        instr = _get_instr(filename)
        # if we found the instrument, then store the name as string, else None
        instr_name = instr.name if instr is not None else None
        m_list[i]['nx_meta'] = {}
        m_list[i]['nx_meta']['Instrument ID'] = instr_name
        m_list[i] = m_tree.as_dictionary()
        m_list[i] = parse_dm3_microscope_info(m_list[i])
        m_list[i] = parse_dm3_eels_info(m_list[i])
        m_list[i] = parse_dm3_eds_info(m_list[i])

        # if the instrument name is None, this check will be false, otherwise
        # look for the instrument in our list of instrument-specific parsers:
        if instr_name in _instr_specific_parsers.keys():
            m_list[i] = _instr_specific_parsers[instr_name](m_list[i])

    if len(m_list) == 1:
        return m_list[0]
    else:
        m_list_dict = {}
        for i in range(len(m_list)):
            m_list_dict[f'Signal {i}'] = m_list[i]
        return m_list_dict


def _remove_dtb_element(tree, path):
    """
    Helper method that uses exec to delete a specific leaf of a
    DictionaryTreeBrowser using a string

    Parameters
    ----------
    tree : :py:class:`~hyperspy.misc.utils.DictionaryTreeBrowser`
        the ``DictionaryTreeBrowser`` object to remove the object from
    path : str
        period-delimited path to a DTB element

    Returns
    -------
    tree : :py:class:`~hyperspy.misc.utils.DictionaryTreeBrowser`
    """
    to_del = 'tree.{}'.format(path)
    try:

        exec('del {}'.format(to_del))
    except AttributeError as _:
        # Log the failure and continue
        _logger.info('_remove_dtb_element: Could not find {}'.format(to_del))

    return tree


def _zero_data_in_dm3(filename, out_filename=None, compress=True):
    """
    Helper method that will overwrite the data in a dm3 image file  with
    zeros and save it as either another dm3, or as a compressed archive (used
    for creating files for the test suite that don't take up tons of space).
    Since the resulting file is just some text metadata and zeros, it should
    be highly compressible (initial tests allowed for a 16MB file to be
    compressed to ~100KB).

    Parameters
    ----------
    filename : str
        Path to file to be modified
    out_filename : None or str
        Name with which to save the output file. If None, it will be
        automatically generated from the ``filename``.
    compress : bool
        Whether or not to compress the files into a tar.gz file

    Returns
    -------
    out_fname : str
        The path of the compressed (or zeroed) file
    """
    # zero out extent of data in DM3 file and compress to tar.gz:
    splitext = _os.path.splitext(filename)
    if not out_filename:
        mod_fname = splitext[0] + '_dataZeroed' + splitext[1]
    else:
        mod_fname = out_filename

    _shutil.copyfile(filename, mod_fname)

    # Do some lower-level reading on the .dm3 file to get the ImageObject refs
    with open(filename, 'rb') as f:
        dm = _DMReader(f)
        dm.parse_file()
        images = [_ImageObject(im_dict, f) for im_dict in
                  dm.get_image_dictionaries()]

    # write zeros to the file in the data block (offset + size in bytes
    # information is obtained from the ImageObject ref)
    # NB: currently this is just tested for single-image .dm3 files. Spectra
    # and image stacks will probably work differently.
    with open(mod_fname, 'r+b') as f:
        f.seek(images[0].imdict.ImageData.Data.offset)
        f.write(b'\x00' * images[0].imdict.ImageData.Data.size_bytes)

    # compress the output, if requested
    if compress:
        with _tarfile.open('{}.tar.gz'.format(mod_fname), 'w:gz') as tar:
            tar.add(mod_fname)
        out_fname = '{}.tar.gz'.format(mod_fname)
        _os.remove(mod_fname)
    else:
        out_fname = mod_fname

    return out_fname
