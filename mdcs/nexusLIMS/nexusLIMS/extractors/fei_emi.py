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

from hyperspy.io import load as _hs_load
from hyperspy.signal import BaseSignal as _BaseSignal
import logging as _logging
import os as _os
from datetime import datetime as _dt

from nexusLIMS.instruments import get_instr_from_filepath as _get_instr
from nexusLIMS.utils import _remove_dtb_element
from nexusLIMS.utils import get_nested_dict_key as _get_nest_dict_key
from nexusLIMS.utils import get_nested_dict_value_by_path as \
    _get_nest_dict_val_by_path
from nexusLIMS.utils import set_nested_dict_value as _set_nest_dict_val
from nexusLIMS.utils import try_getting_dict_value as _try_get_dict_val
from nexusLIMS.utils import _sort_dict
_logger = _logging.getLogger(__name__)


def get_ser_metadata(filename):
    """
    Returns metadata (as a dict) from an FEI .ser file + its associated .emi
    files, with some non-relevant information stripped.

    Parameters
    ----------
    filename : str
        Path to FEI .ser file

    Returns
    -------
    metadata : dict or None
        Metadata of interest which is extracted from the passed files. If None,
        the file could not be opened
    """
    # Trees:
    # ObjectInfo & ser_header_parameters

    # Loads in each .ser file associated with the passed .emi file into a list
    # Each .ser file contain the same information(?), so only need to work with
    # the first list element, s[0]
    try:
        emi_filename, ser_index = get_emi_from_ser(filename)
        # s = _hs_load(filename, lazy=True, only_valid_data=True)
        emi_s = _hs_load(emi_filename, lazy=True, only_valid_data=True)
        # if there is more than one dataset, emi_s will be a list, so pick
        # out the matching signal from the list, which will be the "index"
        # from the filename minus 1:
        if isinstance(emi_s, list):
            s = emi_s[ser_index - 1]
        # otherwise we should just have a regular signal, so make s the same
        # as the data loaded from the .emi
        elif isinstance(emi_s, _BaseSignal):
            s = emi_s
        else:
            raise IOError(f"Did not understand format of .emi file: "
                          f"{emi_filename}")
    except Exception as e:
        _logger.warning(f'File reader could not open {filename}, received '
                        f'exception: {e.__repr__()}')
        return None

    metadata = s.original_metadata.as_dictionary()

    # Get the instrument object associated with this file
    instr = _get_instr(filename)
    # get the modification time (as ISO format):
    mtime = _os.path.getmtime(filename)
    mtime_iso = _dt.fromtimestamp(mtime).isoformat()

    # if we found the instrument, then store the name as string, else None
    instr_name = instr.name if instr is not None else None
    metadata['nx_meta'] = {}
    metadata['nx_meta']['fname'] = filename
    # set type to STEM Image by default (this seems to be most common)
    metadata['nx_meta']['DatasetType'] = 'Image'
    metadata['nx_meta']['Data Type'] = 'STEM_Imaging'
    metadata['nx_meta']['Creation Time'] = mtime_iso

    # try to set creation time to acquisition time from metadata
    acq_time = _try_get_dict_val(metadata, ['ObjectInfo', 'AcquireDate'])
    if acq_time != 'not found':
        metadata['nx_meta']['Creation Time'] = \
            _dt.strptime(acq_time, '%a %b %d %H:%M:%S %Y').isoformat()

    # manufacturer is at high level, so parse it now
    manufacturer = _try_get_dict_val(metadata, ['ObjectInfo', 'Manufacturer'])
    if manufacturer != 'not found':
        metadata['nx_meta']['Manufacturer'] = \
            manufacturer

    metadata['nx_meta']['Data Dimensions'] = str(s.data.shape)
    metadata['nx_meta']['Instrument ID'] = instr_name
    metadata['nx_meta']['warnings'] = []

    metadata = parse_acquire_info(metadata)
    metadata = parse_experimental_conditions(metadata)
    metadata = parse_experimental_description(metadata)

    metadata['nx_meta']['Data Type'], metadata['nx_meta']['DatasetType'] = \
        parse_data_type(s, metadata)

    # we don't need to save the filename, it's just for internal processing
    del metadata['nx_meta']['fname']

    # sort the nx_meta dictionary (recursively) for nicer display
    metadata['nx_meta'] = _sort_dict(metadata['nx_meta'])

    return metadata


def parse_experimental_conditions(metadata):
    """
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
        ('DwellTimePath', ): 'Dwell Time Path (s)',
        ('FrameTime', ): 'Frame Time (s)',
        ('CameraNamePath', ): 'Camera Name Path',
        ('Binning', ): 'Binning',
        ('BeamPosition', ): 'Beam Position (μm)',
        ('EnergyResolution', ): 'Energy Resolution (eV)',
        ('IntegrationTime', ): 'Integration Time (s)',
        ('NumberSpectra', ): 'Number of Spectra',
        ('ShapingTime', ): 'Shaping Time (s)',
        ('ScanArea', ): 'Scan Area',
    }
    base = ['ObjectInfo', 'AcquireInfo']

    if _try_get_dict_val(metadata, base) != 'not found':
        metadata = map_keys(term_mapping, base, metadata)

    # remove units from beam position (if present)
    if 'Beam Position (μm)' in metadata['nx_meta']:
        metadata['nx_meta']['Beam Position (μm)'] = \
            metadata['nx_meta']['Beam Position (μm)'].replace(' um', '')

    return metadata


def parse_acquire_info(metadata):
    """
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
        ('AcceleratingVoltage', ): 'Microscope Accelerating Voltage (V)',
        ('Tilt1', ): 'Microscope Tilt 1',
        ('Tilt2', ): 'Microscope Tilt 2',
    }
    base = ['ObjectInfo', 'ExperimentalConditions', 'MicroscopeConditions']

    if _try_get_dict_val(metadata, base) != 'not found':
        metadata = map_keys(term_mapping, base, metadata)

    return metadata


def parse_experimental_description(metadata):
    """
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
    base = ['ObjectInfo', 'ExperimentalDescription']

    experimental_description = _try_get_dict_val(metadata, base)
    if experimental_description != 'not found' and isinstance(
            experimental_description, dict):
        term_mapping = {}
        for k in metadata['ObjectInfo']['ExperimentalDescription'].keys():
            term, unit = split_fei_metadata_units(k)
            if unit:
                unit = unit.replace('uA', 'μA').\
                            replace('um', 'μm').\
                            replace('deg', '°')
            term_mapping[(k, )] = f'{term}' + (f' ({unit})' if unit else '')
            # Make stage position a nested list
            if 'Stage' in term:
                term = term.replace('Stage ', '')
                term_mapping[(k, )] = ['Stage Position',
                                       f'{term}' + (f' ({unit})' if unit
                                                    else '')]
            # Make filter settings a nested list
            if 'Filter ' in term:
                term = term.replace('Filter ', '')
                term_mapping[(k, )] = ['Tecnai Filter',
                                       f'{term.title()}' +
                                       (f' ({unit})' if unit else '')]

        metadata = map_keys(term_mapping, base, metadata)

        # Microscope Mode often has excess spaces, so fix that if needed:
        if 'Mode' in metadata['nx_meta']:
            metadata['nx_meta']['Mode'] = metadata['nx_meta']['Mode'].strip()

    return metadata


def get_emi_from_ser(ser_fname):
    """
    Get the accompanying `.emi` filename from an ser filename. This method
    assumes that the `.ser` file will be the same name as the `.emi` file,
    but with an underscore and a digit appended. i.e. ``file.emi`` would
    result in `.ser` files named ``file_1.ser``, ``file_2.ser``, etc.

    Parameters
    ----------
    ser_fname : str
        The absolute path of an FEI TIA `.ser` data file

    Returns
    -------
    emi_fname : str
        The absolute path of the accompanying `.emi` metadata file
    index : int
        The number of this .ser file (i.e. 1, 2, 3, etc.)

    Raises
    ------
    FileNotFoundError
        If the accompanying .emi file cannot be resolved to be a file
    """
    # separate filename from extension
    filename = _os.path.splitext(ser_fname)[0]
    # remove everything after the last underscore and add the .emi extension
    emi_fname = '_'.join(filename.split('_')[:-1]) + '.emi'
    index = int(filename.split('_')[-1])

    if not _os.path.isfile(emi_fname):
        raise FileNotFoundError("Could not find .emi file with expected name:"
                                f"{emi_fname}")
    else:
        return emi_fname, index


def split_fei_metadata_units(metadata_term):
    """
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
    mdata_and_unit = tuple(metadata_term.split('_'))

    if len(mdata_and_unit) == 1:
        mdata_and_unit = mdata_and_unit + (None, )

    # capitalize any words in metadata term that are all lowercase:
    mdata_term = ' '.join([w.title() if w.islower() else w
                           for w in mdata_and_unit[0].split()])
    # replace weird "Stem" capitalization
    mdata_term = mdata_term.replace('Stem ', 'STEM ')

    mdata_and_unit = (mdata_term, mdata_and_unit[1])

    return mdata_and_unit


def map_keys(term_mapping, base, metadata):
    """
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
    for in_term in term_mapping.keys():
        out_term = term_mapping[in_term]
        if isinstance(in_term, tuple):
            in_term = list(in_term)
        if isinstance(out_term, str):
            out_term = [out_term]
        val = _try_get_dict_val(metadata, base + in_term)
        # only add the value to this list if we found it
        if val != 'not found':
            _set_nest_dict_val(metadata, ['nx_meta'] + out_term,
                               _convert_to_numeric(val))

    return metadata


def parse_data_type(s, metadata):
    """
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
    dataset_type = 'Misc'

    # instrument configuration
    instr_conf = []
    # sometimes there is no metadata for follow-on signals in an .emi/.ser
    # bundle (i.e. .ser files after the first one)
    if 'Mode' in metadata['nx_meta']:
        if 'STEM' in metadata['nx_meta']['Mode']:
            instr_conf.append('STEM')
        elif 'TEM' in metadata['nx_meta']['Mode']:
            instr_conf.append('TEM')
    else:
        # if there is no metadata read from .emi, assume STEM because it
        # seems to happen most for spectra
        instr_conf.append('STEM')

    # instrument modality:
    instr_mod = []

    # images have signal dimension of two:
    if s.axes_manager.signal_dimension == 2 and 'Mode' in metadata['nx_meta']:
        if 'Image' in metadata['nx_meta']['Mode']:
            instr_mod.append('Imaging')
            dataset_type = 'Image'
        elif 'Diffraction' in metadata['nx_meta']['Mode']:
            # Diffraction mode is only actually diffraction in TEM mode,
            # In STEM, imaging happens in diffraction mode
            if 'STEM' in metadata['nx_meta']['Mode']:
                instr_mod.append('Imaging')
                dataset_type = 'Image'
            elif 'TEM' in metadata['nx_meta']['Mode']:
                instr_mod.append('Diffraction')
                dataset_type = 'Diffraction'
    # if signal dimension is 1, it's a spectrum and not an image
    elif s.axes_manager.signal_dimension == 1:
        instr_mod = ['Spectrum']
        dataset_type = 'Spectrum'
        if s.axes_manager.navigation_dimension > 0:
            instr_mod.append('Imaging')
            dataset_type = 'SpectrumImage'
        # do some basic axis value analysis to guess signal type since we
        # don't have any indication of EELS vs. EDS; assume 5 keV and above
        # is EDS
        if s.axes_manager.signal_axes[0].high_value > 5000:
            if 'EDS' not in instr_conf:
                instr_conf.append('EDS')
        else:
            # EELS spectra are usually 2048 channels
            if s.axes_manager.signal_axes[0].size == 2048:
                instr_conf.append('EELS')

    data_type = '_'.join(instr_conf + instr_mod)

    return data_type, dataset_type


def _convert_to_numeric(val):
    if isinstance(val, str):
        if '.' in val:
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
