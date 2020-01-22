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
import configparser as _cp
import io as _io

from nexusLIMS.instruments import get_instr_from_filepath as _get_instr
from nexusLIMS.utils import get_nested_dict_key as _get_nest_dict_key
from nexusLIMS.utils import get_nested_dict_value_by_path as \
    _get_nest_dict_val_by_path
from nexusLIMS.utils import set_nested_dict_value as _set_nest_dict_val
from nexusLIMS.utils import try_getting_dict_value as _try_get_dict_val


def get_quanta_metadata(filename):
    """
    Returns the metadata (as a dictionary) from a .tif file saved by the FEI
    Quanta SEM in the Nexus Microscopy Facility. Specific tags of interest are
    duplicated under the root-level ``nx_meta`` node in the dictionary.

    Parameters
    ----------
    filename : str
        path to a .tif file saved by the Quanta

    Returns
    -------
    midct : dict
        The metadata text extracted from the file
    """
    with open(filename, 'rb') as f:
        content = f.read()
    metadata_bytes = content[content.find(b'[User]'):]
    metadata_str = metadata_bytes.decode().replace('\r\n', '\n')

    buf = _io.StringIO(metadata_str)
    config = _cp.ConfigParser()
    # make ConfigParser respect upper/lowercase values
    config.optionxform = lambda option: option
    config.read_file(buf)

    mdict = {}

    for itm in config.items():
        if itm[0] == 'DEFAULT':
            pass
        else:
            mdict[itm[0]] = {}
            for k, v in itm[1].items():
                mdict[itm[0]][k] = v

    mdict = parse_nx_meta(mdict)

    return mdict


def parse_nx_meta(mdict):
    """
    Parse the "important" metadata that is saved at specific places within
    the Quanta tag structure into a consistent place in the metadata dictionary
    returned by :py:meth:`get_quanta_metadata`.

    Parameters
    ----------
    mdict : dict
        A metadata dictionary as returned by :py:meth:`get_quanta_metadata`

    Returns
    -------
    mdict : dict
        The same metadata dictionary with some values added under the
        root-level ``nx_meta`` key
    """
    mdict['nx_meta'] = {}

    # The name of the beam, scan, and detector will determine which sections are
    # present (have not seen more than one beam/detector -- although likely
    # will be the case for dual beam FIB/SEM)
    beam_name = _try_get_dict_val(mdict, ['Beam', 'Beam'])
    det_name = _try_get_dict_val(mdict, ['Detectors', 'Name'])
    scan_name = _try_get_dict_val(mdict, ['Beam', 'Scan'])

    if beam_name != 'not found':
        mdict = parse_beam_info(mdict, beam_name)
    if scan_name != 'not found':
        mdict = parse_scan_info(mdict, scan_name)
    if det_name != 'not found':
        mdict = parse_det_info(mdict, det_name)

    to_parse = [
        (['Detectors', 'Name'], ['Detector Name']),
        (['Beam', 'HV'], ['Voltage']),
        (['Beam', 'Spot'], ['Spot Size']),
        # TODO: Parse other root-level metadata
    ]

    for m_in, m_out in to_parse:
        pass

    return mdict


def parse_beam_info(mdict, beam_name):
    """

    Parameters
    ----------
    mdict : dict
        A metadata dictionary as returned by :py:meth:`get_quanta_metadata`
    beam_name : str
        The "beam name" read from the root-level ``Beam`` node of the
        metadata dictionary

    Returns
    -------
    mdict : dict
        The same metadata dictionary with some values added under the
        root-level ``nx_meta`` key
    """
    # Values are in SI units, but we want easy to display, so include the
    # exponential factor that will get us from input unit (such as seconds)
    # to output unit (such as μs -- meaning factor = 6)
    to_parse = [
        ([beam_name, 'EmissionCurrent'], ['Emission Current (μA)'], 6),
        ([beam_name, 'HFW'], ['Horizontal Field Width (μm)'], 6),
        ([beam_name, 'HV'], ['Voltage (kV)'], -3),
        ([beam_name, 'SourceTiltX'], ['Beam Tilt X'], 1),
        ([beam_name, 'SourceTiltY'], ['Beam Tilt Y'], 1),
        ([beam_name, 'StageR'], ['Stage Position', 'R'], 1),
        ([beam_name, 'StageTa'], ['Stage Position', 'α'], 1),
        ([beam_name, 'StageTb'], ['Stage Position', 'β'], 1),
        ([beam_name, 'StageX'], ['Stage Position', 'X'], 1),
        ([beam_name, 'StageY'], ['Stage Position', 'Y'], 1),
        ([beam_name, 'StageZ'], ['Stage Position', 'Z'], 1),
        ([beam_name, 'StigmatorX'], ['Stigmator X Value'], 1),
        ([beam_name, 'StigmatorY'], ['Stigmator Y Value'], 1),
        ([beam_name, 'VFW'], ['Vertical Field Width (μm)'], 6),
        ([beam_name, 'WD'], ['Working Distance (mm)'], 3),
    ]
    for m_in, m_out, factor in to_parse:
        val = _try_get_dict_val(mdict, m_in)
        if val != 'not found':
            val = float(val) * 10**factor
            _set_nest_dict_val(mdict, ['nx_meta'] + m_out, val)

    # Add beam name to metadata:
    _set_nest_dict_val(mdict, ['nx_meta'] + ['Beam Name'], beam_name)

    # BeamShiftX and BeamShiftY require an additional test:
    bs_x_val = _try_get_dict_val(mdict, [beam_name, 'BeamShiftX'])
    bs_y_val = _try_get_dict_val(mdict, [beam_name, 'BeamShiftY'])
    if bs_x_val != 'not found' and float(bs_x_val) != 0:
        _set_nest_dict_val(mdict, ['nx_meta'] + ['Beam Shift X'],
                           float(bs_x_val))
    if bs_y_val != 'not found' and float(bs_y_val) != 0:
        _set_nest_dict_val(mdict, ['nx_meta'] + ['Beam Shift Y'],
                           float(bs_y_val))

    # TiltCorrectionAngle only if TiltCorrectionIsOn == 'yes'
    tilt_corr_on = _try_get_dict_val(mdict, [beam_name, 'TiltCorrectionIsOn'])
    if tilt_corr_on == 'yes':
        tilt_corr_val = _try_get_dict_val(mdict,
                                          [beam_name, 'TiltCorrectionAngle'])
        if tilt_corr_val != 'not found':
            _set_nest_dict_val(mdict,
                               ['nx_meta'] + ['Tilt Correction Angle'],
                               tilt_corr_val)

    return mdict


def parse_scan_info(mdict, scan_name):
    """
    Parses the `Scan` portion of the metadata dictionary (on a Quanta this is
    always `"EScan"`) to get values such as dwell time, field width, and pixel
    size

    Parameters
    ----------
    mdict : dict
        A metadata dictionary as returned by :py:meth:`get_quanta_metadata`
    scan_name : str
        The "scan name" read from the root-level ``Beam`` node of the
        metadata dictionary

    Returns
    -------
    mdict : dict
        The same metadata dictionary with some values added under the
        root-level ``nx_meta`` key
    """
    # Values are in SI units, but we want easy to display, so include the
    # exponential factor that will get us from input unit (such as seconds)
    # to output unit (such as μs -- meaning factor = 6)
    to_parse = [
        ([scan_name, 'Dwell'], ['Pixel Dwell Time (μs)'], 6),
        ([scan_name, 'FrameTime'], ['Total Frame Time (s)'], 1),
        ([scan_name, 'HorFieldsize'], ['Horizontal Field Width (μm)'], 6),
        ([scan_name, 'VerFieldsize'], ['Vertical Field Width (μm)'], 6),
        ([scan_name, 'PixelHeight'], ['Pixel Width (nm)'], 9),
        ([scan_name, 'PixelWidth'], ['Pixel Height (nm)'], 9)
    ]

    for m_in, m_out, factor in to_parse:
        val = _try_get_dict_val(mdict, m_in)
        if val != 'not found':
            val = float(val) * 10**factor
            _set_nest_dict_val(mdict, ['nx_meta'] + m_out, val)

    return mdict


def parse_det_info(mdict, det_name):
    """
    Parses the `Detector` portion of the metadata dictionary from the Quanta to
    get values such as brightness, contrast, signal, etc.

    Parameters
    ----------
    mdict : dict
        A metadata dictionary as returned by :py:meth:`get_quanta_metadata`
    det_name : str
        The "detector name" read from the root-level ``Beam`` node of the
        metadata dictionary

    Returns
    -------
    mdict : dict
        The same metadata dictionary with some values added under the
        root-level ``nx_meta`` key
    """
    to_parse = [
        ([det_name, 'Brightness'], ['Detector Brightness Setting']),
        ([det_name, 'Contrast'], ['Detector Contrast Setting']),
        ([det_name, 'EnhancedContrast'], ['Detector Enhanced Contrast '
                                          'Setting']),
        ([det_name, 'Signal'], ['Detector Signal']),
        ([det_name, 'Grid'], ['Detector Grid Voltage (V)']),
        ([det_name, 'Setting'], ['Detector Setting'])
    ]

    for m_in, m_out in to_parse:
        val = _try_get_dict_val(mdict, m_in)
        if val != 'not found':
            try:
                val = float(val)
                if m_in == [det_name, 'Setting']:
                    # if "Setting" value is numeric, it's just the Grid
                    # voltage so skip it
                    continue
            except ValueError:
                pass
            _set_nest_dict_val(mdict, ['nx_meta'] + m_out, val)

    _set_nest_dict_val(mdict, ['nx_meta'] + ['Detector Name'], det_name)

    return mdict
