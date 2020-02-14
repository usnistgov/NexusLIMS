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
from math import degrees
from decimal import Decimal as _Decimal
from decimal import InvalidOperation as _invalidOp

from nexusLIMS.instruments import get_instr_from_filepath as _get_instr
from nexusLIMS.utils import _sort_dict
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
    user_idx = content.find(b'[User]')
    # if the user_idx is -1, it means the [User] tag was not found in the
    # file, and so the metadata is missing (so we should just return 0)
    if user_idx == -1:
        return None
    metadata_bytes = content[user_idx:]
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

    mdict['nx_meta'] = {}
    # assume all datasets coming from Quanta are Images, currently
    mdict['nx_meta']['DatasetType'] = 'Image'

    instr = _get_instr(filename)
    # if we found the instrument, then store the name as string, else None
    instr_name = instr.name if instr is not None else None
    mdict['nx_meta']['Instrument ID'] = instr_name
    mdict['nx_meta']['warnings'] = []

    mdict = parse_nx_meta(mdict)

    # sort the nx_meta dictionary (recursively) for nicer display
    mdict['nx_meta'] = _sort_dict(mdict['nx_meta'])

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
    if 'nx_meta' not in mdict:
        mdict['nx_meta'] = {}

    # The name of the beam, scan, and detector will determine which sections are
    # present (have not seen more than one beam/detector -- although likely
    # will be the case for dual beam FIB/SEM)
    beam_name = _try_get_dict_val(mdict, ['Beam', 'Beam'])
    det_name = _try_get_dict_val(mdict, ['Detectors', 'Name'])
    scan_name = _try_get_dict_val(mdict, ['Beam', 'Scan'])

    # some parsers are broken off into helper methods:
    if beam_name != 'not found':
        mdict = parse_beam_info(mdict, beam_name)
    if scan_name != 'not found':
        mdict = parse_scan_info(mdict, scan_name)
    if det_name != 'not found':
        mdict = parse_det_info(mdict, det_name)
    if _try_get_dict_val(mdict, ['System']) != 'not found':
        mdict = parse_system_info(mdict)

    # process the rest of the metadata tags:

    # process beam spot size
    val = _try_get_dict_val(mdict, ['Beam', 'Spot'])
    if val != 'not found':
        try:
            val = _Decimal(val)
        except (ValueError, _invalidOp):
            pass
        _set_nest_dict_val(mdict, ['nx_meta'] + ['Spot Size'],
                           float(val) if isinstance(val, _Decimal) else val)

    # process drift correction
    val = _try_get_dict_val(mdict, ['Image', 'DriftCorrected'])
    if val != 'not found':
        # set to true if the value is 'On'
        val = val == 'On'
        _set_nest_dict_val(mdict, ['nx_meta'] + ['Drift Correction Applied'],
                           val)

    # process frame integration
    val = _try_get_dict_val(mdict, ['Image', 'Integrate'])
    if val != 'not found':
        try:
            val = int(val)
            if val > 1:
                _set_nest_dict_val(mdict, ['nx_meta'] + ['Frames Integrated'],
                                   val)
        except ValueError:
            pass

    # process mag mode
    val = _try_get_dict_val(mdict, ['Image', 'MagnificationMode'])
    if val != 'not found':
        try:
            val = int(val)
        except ValueError:
            pass
        _set_nest_dict_val(mdict, ['nx_meta'] + ['Magnification Mode'], val)

    # Process "ResolutionX/Y" (data size)
    x_val = _try_get_dict_val(mdict, ['Image', 'ResolutionX'])
    y_val = _try_get_dict_val(mdict, ['Image', 'ResolutionY'])
    try:
        x_val = int(x_val)
        y_val = int(y_val)
    except ValueError:
        pass
    if x_val != 'not found' and y_val != 'not found':
        _set_nest_dict_val(mdict, ['nx_meta', 'Data Dimensions'],
                           str((x_val, y_val)))

    # test for specimen temperature value if present and non-empty
    temp_val = _try_get_dict_val(mdict, ['Specimen', 'Temperature'])
    if temp_val != 'not found' and temp_val != '':
        try:
            temp_val = _Decimal(temp_val)
        except (ValueError, _invalidOp):
            pass
        _set_nest_dict_val(mdict, ['nx_meta', 'Specimen Temperature (K)'],
                           float(temp_val) if isinstance(temp_val, _Decimal)
                           else temp_val)

    # # parse SpecTilt (think this is specimen pre-tilt, but not definite)
    # # tests showed that this is always the same value as StageT, so we do not
    # # need to parse this one
    # val = _try_get_dict_val(mdict, ['Stage', 'SpecTilt'])
    # if val != 'not found' and val != '0':
    #     _set_nest_dict_val(mdict, ['nx_meta', 'Stage Position',
    #                                'Specimen Tilt'], val)

    # Get user ID (sometimes it's not correct because the person left the
    # instrument logged in as the previous user, so make sure to add it to
    # the warnings list
    user_val = _try_get_dict_val(mdict, ['User', 'User'])
    if user_val != 'not found':
        _set_nest_dict_val(mdict, ['nx_meta', 'Operator'], user_val)
        mdict['nx_meta']['warnings'].append(['Operator'])

    # parse acquisition date and time
    acq_date_val = _try_get_dict_val(mdict, ['User', 'Date'])
    acq_time_val = _try_get_dict_val(mdict, ['User', 'Time'])
    if acq_date_val != 'not found':
        _set_nest_dict_val(mdict, ['nx_meta', 'Acquisition Date'], acq_date_val)
    if acq_time_val != 'not found':
        _set_nest_dict_val(mdict, ['nx_meta', 'Acquisition Time'], acq_time_val)

    # parse vacuum mode
    vac_val = _try_get_dict_val(mdict, ['Vacuum', 'UserMode'])
    if user_val != 'not found':
        _set_nest_dict_val(mdict, ['nx_meta', 'Vacuum Mode'], vac_val)

    # parse chamber pressure
    ch_pres_val = _try_get_dict_val(mdict, ['Vacuum', 'ChPressure'])
    if ch_pres_val != 'not found' and ch_pres_val != '':
        # keep track of original digits so we don't propagate float errors
        try:
            ch_pres_val = _Decimal(ch_pres_val)
        except _invalidOp:
            ch_pres_val = float(ch_pres_val)
        if _try_get_dict_val(mdict,
                             ['nx_meta', 'Vacuum Mode']) == 'High vacuum':
            ch_pres_str = 'Chamber Pressure (mPa)'
            ch_pres_val = ch_pres_val * 10**3
        else:
            ch_pres_str = 'Chamber Pressure (Pa)'
            ch_pres_val = ch_pres_val
        _set_nest_dict_val(mdict, ['nx_meta', ch_pres_str],
                           float(ch_pres_val) if
                           isinstance(ch_pres_val, _Decimal) else ch_pres_val)

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
        ([beam_name, 'SourceTiltX'], ['Beam Tilt X'], 0),
        ([beam_name, 'SourceTiltY'], ['Beam Tilt Y'], 0),
        ([beam_name, 'StageR'], ['Stage Position', 'R'], 0),
        ([beam_name, 'StageTa'], ['Stage Position', 'α'], 0),
        # all existing quanta images have a value of zero for beta
        # ([beam_name, 'StageTb'], ['Stage Position', 'β'], 0),
        ([beam_name, 'StageX'], ['Stage Position', 'X'], 0),
        ([beam_name, 'StageY'], ['Stage Position', 'Y'], 0),
        ([beam_name, 'StageZ'], ['Stage Position', 'Z'], 0),
        ([beam_name, 'StigmatorX'], ['Stigmator X Value'], 0),
        ([beam_name, 'StigmatorY'], ['Stigmator Y Value'], 0),
        ([beam_name, 'VFW'], ['Vertical Field Width (μm)'], 6),
        ([beam_name, 'WD'], ['Working Distance (mm)'], 3),
    ]
    for m_in, m_out, factor in to_parse:
        val = _try_get_dict_val(mdict, m_in)
        if val != 'not found' and val != '':
            val = _Decimal(val) * _Decimal(str(10**factor))
            _set_nest_dict_val(mdict, ['nx_meta'] + m_out,
                               float(val) if isinstance(val, _Decimal) else val)

    # Add beam name to metadata:
    _set_nest_dict_val(mdict, ['nx_meta'] + ['Beam Name'], beam_name)

    # BeamShiftX and BeamShiftY require an additional test:
    bs_x_val = _try_get_dict_val(mdict, [beam_name, 'BeamShiftX'])
    bs_y_val = _try_get_dict_val(mdict, [beam_name, 'BeamShiftY'])
    if bs_x_val != 'not found' and _Decimal(bs_x_val) != 0:
        _set_nest_dict_val(mdict, ['nx_meta'] + ['Beam Shift X'],
                           float(_Decimal(bs_x_val)))
    if bs_y_val != 'not found' and _Decimal(bs_y_val) != 0:
        _set_nest_dict_val(mdict, ['nx_meta'] + ['Beam Shift Y'],
                           float(_Decimal(bs_y_val)))

    # only parse scan rotation if value is not zero:
    # Not sure what the units of this value are... looks like radians because
    # unique values range from 0 to 6.24811 - convert to degrees for display
    scan_rot_val = _try_get_dict_val(mdict, [beam_name, 'ScanRotation'])
    if scan_rot_val != 'not found' and _Decimal(scan_rot_val) != 0:
        scan_rot_dec = _Decimal(scan_rot_val)   # make scan_rot a Decimal
        # get number of digits in Decimal value (so we don't artificially
        # introduce extra precision)
        digits = abs(scan_rot_dec.as_tuple().exponent)
        # round the final float value to that number of digits
        scan_rot_val = round(degrees(scan_rot_dec), digits)
        _set_nest_dict_val(mdict, ['nx_meta', 'Scan Rotation (°)'],
                           scan_rot_val)

    # TiltCorrectionAngle only if TiltCorrectionIsOn == 'yes'
    tilt_corr_on = _try_get_dict_val(mdict, [beam_name, 'TiltCorrectionIsOn'])
    if tilt_corr_on == 'yes':
        tilt_corr_val = _try_get_dict_val(mdict,
                                          [beam_name, 'TiltCorrectionAngle'])
        if tilt_corr_val != 'not found':
            tilt_corr_val = float(_Decimal(tilt_corr_val))
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
        ([scan_name, 'FrameTime'], ['Total Frame Time (s)'], 0),
        ([scan_name, 'HorFieldsize'], ['Horizontal Field Width (μm)'], 6),
        ([scan_name, 'VerFieldsize'], ['Vertical Field Width (μm)'], 6),
        ([scan_name, 'PixelHeight'], ['Pixel Width (nm)'], 9),
        ([scan_name, 'PixelWidth'], ['Pixel Height (nm)'], 9),
    ]

    for m_in, m_out, factor in to_parse:
        val = _try_get_dict_val(mdict, m_in)
        if val != 'not found' and val != '':
            val = _Decimal(val) * _Decimal(str(10**factor))
            _set_nest_dict_val(mdict, ['nx_meta'] + m_out,
                               float(val) if isinstance(val, _Decimal) else val)

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
                val = _Decimal(val)
                if m_in == [det_name, 'Setting']:
                    # if "Setting" value is numeric, it's just the Grid
                    # voltage so skip it
                    continue
            except (ValueError, _invalidOp):
                pass
            _set_nest_dict_val(mdict, ['nx_meta'] + m_out,
                               float(val) if isinstance(val, _Decimal) else val)

    _set_nest_dict_val(mdict, ['nx_meta'] + ['Detector Name'], det_name)

    return mdict


def parse_system_info(mdict):
    """
    Parses the `System` portion of the metadata dictionary from the Quanta to
    get values such as software version, chamber config, etc.

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
    to_parse = [
        (['System', 'Chamber'], ['Chamber ID']),
        (['System', 'Pump'], ['Vacuum Pump']),
        (['System', 'SystemType'], ['System Type']),
        (['System', 'Stage'], ['Stage Description'])
    ]

    for m_in, m_out in to_parse:
        val = _try_get_dict_val(mdict, m_in)
        if val != 'not found':
            _set_nest_dict_val(mdict, ['nx_meta'] + m_out, val)

    # Parse software info into one output tag:
    output_vals = []
    val = _try_get_dict_val(mdict, ['System', 'Software'])
    if val != 'not found':
        output_vals.append(val)
    val = _try_get_dict_val(mdict, ['System', 'BuildNr'])
    if val != 'not found':
        output_vals.append(f'(build {val})')
    if len(output_vals) > 0:
        _set_nest_dict_val(mdict, ['nx_meta'] + ['Software Version'],
                           ' '.join(output_vals))

    # parse column and type into one output tag:
    output_vals = []
    val = _try_get_dict_val(mdict, ['System', 'Column'])
    if val != 'not found':
        output_vals.append(val)
    val = _try_get_dict_val(mdict, ['System', 'Type'])
    if val != 'not found':
        output_vals.append(val)
    if len(output_vals) > 0:
        _set_nest_dict_val(mdict, ['nx_meta'] + ['Column Type'],
                           ' '.join(output_vals))

    return mdict
