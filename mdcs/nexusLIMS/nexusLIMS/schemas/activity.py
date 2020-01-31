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

import os as _os
import pathlib as _pathlib
import logging as _logging
from datetime import datetime as _datetime
from xml.sax.saxutils import escape, unescape
import hyperspy.api_nogui as _hs
from nexusLIMS.extractors.digital_micrograph import \
    process_tecnai_microscope_info as _tecnai
from nexusLIMS import mmf_nexus_root_path as _mmf_path
from nexusLIMS import nexuslims_root_path as _nx_path
from nexusLIMS.extractors import parse_metadata as _parse_metadata
from nexusLIMS.extractors import flatten_dict as _flatten_dict

_logger = _logging.getLogger(__name__)


# TODO: Metadata parsing will require different method for each instrument
def read_metadata(sig):
    """
    For a signal like that contained in ``self.sigs``, parse the
    "important" metadata, so it can be compared to find common values
    that will be defined as AcquisitionActivity parameters

    Parameters
    ----------
    sig : :py:class:`hyperspy.signal.BaseSignal`
        The signal for which to parse the metadata

    Returns
    -------
    m : dict
        A dictionary containing all the "important" metadata from the given
        signal

    Notes
    -----

    Currently, the following tags are considered "important", but this will
    be modified for different instrument, file types, etc.:

    - General .dm3 tags (not guaranteed to be present):
        - ``ImageTags.Microscope_Info.Indicated_Magnification``
        - ``ImageTags.Microscope_Info.Actual_Magnification``
        - ``ImageTags.Microscope_Info.Csmm``
        - ``ImageTags.Microscope_Info.STEM_Camera_Length``
        - ``ImageTags.Microscope_Info.Voltage``

    - Tecnai info:
        - ``ImageTags.Tecnai.Microscope_Info['Gun_Name']``
        - ``ImageTags.Tecnai.Microscope_Info['Extractor_Voltage']``
        - ``ImageTags.Tecnai.Microscope_Info['Gun_Lens_No']``
        - ``ImageTags.Tecnai.Microscope_Info['Emission_Current']``
        - ``ImageTags.Tecnai.Microscope_Info['Spot']``
        - ``ImageTags.Tecnai.Microscope_Info['Mode']``
        - C2, C3, Obj, Dif lens strength:
            - ``ImageTags.Tecnai.Microscope_Info['C2_Strength', 'C3_Strength', 'Obj_Strength', 'Dif_Strength']``
        - ``ImageTags.Tecnai.Microscope_Info['Image_Shift_x'/'Image_Shift_y'])``
        - ``ImageTags.Tecnai.Microscope_Info['Stage_Position_x' (y/z/theta/phi)]``
        - C1/C2/Objective/SA aperture sizes:
            - ``ImageTags.Tecnai.Microscope_Info['(C1/C2/Obj/SA)_Aperture']``
        - ``ImageTags.Tecnai.Microscope_Info['Filter_Settings']['Mode']``
        - ``ImageTags.Tecnai.Microscope_Info['Filter_Settings']['Dispersion']``
        - ``ImageTags.Tecnai.Microscope_Info['Filter_Settings']['Aperture']``
        - ``ImageTags.Tecnai.Microscope_Info['Filter_Settings']['Prism_Shift']``
        - ``ImageTags.Tecnai.Microscope_Info['Filter_Settings']['Drift_Tube']``
        - ``ImageTags.Tecnai.Microscope_Info['Filter_Settings']['Total_Energy_Loss']``
    """
    m = {}
    # Obviously will need to be changed for non-dm3 data and other
    # instruments
    ImageTags = sig.original_metadata.ImageList.TagGroup0.ImageTags
    try:
        tecnai_info = _tecnai(ImageTags.Tecnai.Microscope_Info)
    except AttributeError: tecnai_info = None  # Not a tecnai image
    try:
        m['Indicated_Magnification'] = \
            ImageTags.Microscope_Info.Indicated_Magnification
    except AttributeError: pass
    try:
        m['Actual_Magnification'] = \
            ImageTags.Microscope_Info.Actual_Magnification
    except AttributeError: pass
    try:
        m['Csmm'] = ImageTags.Microscope_Info.Csmm
    except AttributeError: pass
    try:
        m['STEM_Camera_Length'] = \
            ImageTags.Microscope_Info.STEM_Camera_Length
    except AttributeError: pass
    try:
        m['Voltage'] = ImageTags.Microscope_Info.Voltage
    except AttributeError: pass

    if tecnai_info:
        for k in ['Gun_Name', 'Extractor_Voltage', 'Gun_Lens_No',
                  'Camera_Length', 'Emission_Current', 'Spot', 'Mode',
                  'C2_Strength', 'C3_Strength', 'Obj_Strength', 'Dif_Strength',
                  'Image_Shift_x', 'Image_Shift_y', 'Stage_Position_x',
                  'Stage_Position_y', 'Stage_Position_z',
                  'Stage_Position_theta', 'Stage_Position_phi',
                  'C1_Aperture', 'C2_Aperture', 'Obj_Aperture',
                  'SA_Aperture']:
            try:
                m[k] = tecnai_info[k]
            except KeyError:
                _logger.info(f'Tecnai.Microscope_Info.{k}' +
                             ' not found in the metadata dictionary')
        for k in ['Mode', 'Dispersion', 'Aperture', 'Prism_Shift',
                  'Drift_Tube', 'Total_Energy_Loss']:
            try:
                m[f'Filter.{k}'] = tecnai_info['Filter_Settings'][k]
            except KeyError:
                _logger.info(f'Filter_Settings.{k} not found' +
                             ' in the metadata dictionary')

    return m


# TODO: tests for all of AcquisitionActivity
class AcquisitionActivity:
    """
    A collection of files/metadata attributed to a physical acquisition activity

    Instances of this class correspond to AcquisitionActivity nodes in the
    `NexusLIMS schema <https://data.nist.gov/od/dm/nexus/experiment/v1.0>`_

    Parameters
    ----------
    start : datetime.datetime
        The start point of this AcquisitionActivity
    end : datetime.datetime
        The end point of this AcquisitionActivity
    mode : str
        The microscope mode for this AcquisitionActivity (i.e. 'IMAGING',
        'DIFFRACTION', 'SCANNING', etc.)
    unique_params : set
        A set of dictionary keys that comprises all unique metadata keys
        contained within the files of this AcquisitionActivity
    setup_params : dict
        A dictionary containing metadata about the data that is shared
        amongst all data files in this AcquisitionActivity
    unique_meta : list
        A list of dictionaries (one for each file in this
        AcquisitionActivity) containing metadata key-value pairs that are
        unique to each file in ``files`` (i.e. those that could not be moved
        into ``setup_params``)
    files : list
        A list of filenames belonging to this AcquisitionActivity
    previews : list
        A list of filenames pointing to the previews for each file in
        ``files``
    sigs : list
        A list of *lazy* (to minimize loading times) HyperSpy signals in
        this AcquisitionActivity. HyperSpy is used to facilitate metadata
        reading
    meta : list
        A list of dictionaries containing the "important" metadata for each
        signal/file in ``sigs`` and ``files``
    warnings : list
        A list of metadata values that may be untrustworthy because of the
        software
    """

    def __init__(self,
                 start=_datetime.now(),
                 end=_datetime.now(),
                 mode='',
                 unique_params=None,
                 setup_params=None,
                 unique_meta=None,
                 files=None,
                 previews=None,
                 sigs=None,
                 meta=None,
                 warnings=None):
        """
        Create a new AcquisitionActivity
        """
        self.start = start
        self.end = end
        self.mode = mode
        self.unique_params = set() if unique_params is None else unique_params
        self.setup_params = setup_params
        self.unique_meta = unique_meta
        self.files = [] if files is None else files
        self.previews = [] if previews is None else previews
        self.sigs = [] if sigs is None else sigs
        self.meta = [] if meta is None else meta
        self.warnings = [] if warnings is None else warnings

    def __repr__(self):
        return f'{self.mode:<12} AcquisitionActivity; ' + \
               f'start: {self.start.isoformat()}; ' + \
               f'end: {self.end.isoformat()}'

    def __str__(self):
        return f'{self.start.isoformat()} AcquisitionActivity {self.mode}'

    def add_file(self, fname):
        """
        Add a file to this activity's file list, read it into a Signal,
        and read its metadata

        Parameters
        ----------
        fname : str
            The file to be added to the file list
        """
        if _os.path.exists(fname):
            self.files.append(fname)
            meta, preview_fname = _parse_metadata(fname,
                                                  generate_preview=False)

            if meta is None:
                # Something bad happened, so we need to alert the user
                _logger.warning(f'Could not parse metadata of {fname}')
                pass
            else:
                s = _hs.load(fname, lazy=True)
                self.previews.append(preview_fname)
                self.sigs.append(s)
                self.meta.append(_flatten_dict(meta['nx_meta']))
                # TODO: figure out if this is working...
                self.warnings.append([' '.join(w)
                                      for w in meta['nx_meta']['warnings']])
        else:
            raise FileNotFoundError(fname + ' was not found')
        _logger.debug(f'appended {fname} to files')
        _logger.debug(f'self.files is now {self.files}')

    def store_unique_params(self):
        """
        Analyze the metadata keys contained in this AcquisitionActivity and
        store the unique values in a set (``self.unique_params``)
        """
        # self.meta is a list of dictionaries
        for m in self.meta:
            self.unique_params.update(m.keys())

    def store_setup_params(self, values_to_search=None):
        """
        Search the metadata of files in this AcquisitionActivity for those
        containing identical values over all files, which will then be defined
        as parameters attributed to experimental setup, rather than individual
        datasets.

        Stores a dictionary containing the metadata keys and values that are
        consistent across all files in this AcquisitionActivity as an
        attribute (``self.setup_params``).

        Parameters
        ----------
        values_to_search : list
            A list (or tuple, set, or other iterable type) containing values to
            search for in the metadata dictionary list. If None (default), all
            values contained in any file will be searched.
        """
        # Make sure unique params are defined before proceeding:
        if self.unique_params == set():
            _logger.info('Storing unique parameters for files in '
                         'AcquisitionActivity')
            self.store_unique_params()

        if values_to_search is None:
            values_to_search = self.unique_params

        # TODO: tests for setup parameter determination
        # m will be individual dictionaries, since meta is list of dicts
        i = 0
        setup_params = {}
        for m, f in zip(self.meta, self.files):
            # loop through the values_to_search
            # print(f)
            # using .copy() on the set allows us to remove values during each
            # iteration, as described in:
            # https://stackoverflow.com/a/22847851/1435788
            for vts in values_to_search.copy():
                # for the first iteration through the list of dictionaries,
                # store any value found for a parameter
                # as a "setup parameter". if it is not found, do not store it
                # and remove from values_to_search to prevent it being searched
                # on subsequent iterations.
                if i == 0:
                    if vts in m:
                        # this value was found in m, so store it
                        setup_params[vts] = m[vts]
                        _logger.debug(f'iter: {i}; adding {vts} = {m[vts]} to '
                                      f'setup_params')
                    else:
                        # this value wasn't present in m, so it can't be
                        # common to all, so remove it:
                        _logger.debug(f'iter: {i}; removing {vts}')
                        values_to_search.remove(vts)
                # On the subsequent iterations test if values are same/different
                # If different, then remove the key from setup_params and
                # values_to_search, so at the end only identical values remain
                # and duplicate value checks are minimized
                else:
                    if vts not in setup_params:
                        # this condition should probably not be reached,
                        # but if it is, it means this value, which should
                        # have already been added to setup_params is somehow
                        # new, so delete vts from values to search
                        _logger.debug(f'iter: {i}; removing {vts}')
                        values_to_search.remove(vts)
                    if vts in m:
                        if setup_params[vts] == m[vts]:
                            # value in m matches that already in setup_params
                            # so allow it to stay in setup_params
                            pass
                        else:
                            # value does not match, so this must be a
                            # individual dataset metadata, so remove it from
                            # setup_params, and remove it from values_to_search
                            _logger.debug(f'iter: {i}; vts={vts} - '
                                          f'm[vts]={m[vts]} != '
                                          f'setup_params[vts]='
                                          f'{setup_params[vts]}; removing '
                                          f'{vts} from setup_params and values '
                                          f'to search')
                            del setup_params[vts]
                            values_to_search.remove(vts)
            i += 1

        self.setup_params = setup_params

    def store_unique_metadata(self):
        """
        For each file in this AcquisitionActivity, stores the metadata that
        is unique rather than common to the entire AcquisitionActivity (which
        are kept in ``self.setup_params``.
        """
        if self.setup_params is None:
            _logger.warning(f'{self} -- setup_params has not been defined; '
                            f'call store_setup_params() prior to using this '
                            f'method. Nothing was done.')
            return
        else:
            unique_meta = []
            for i, m in enumerate(self.meta):
                tmp_unique = {}
                # loop through each metadata dict, and if a given key k in m is
                # not present in self.setup_params, add it it to the
                # current dictionary (u_m) of unique_meta
                for k, v in m.items():
                    if k not in self.setup_params:
                        # this means k is unique to this file, so add it to
                        # unique_meta
                        tmp_unique[k] = v
                unique_meta.append(tmp_unique)

        # store what we calculated as unique metadata into the attribute
        self.unique_meta = unique_meta

    def as_xml(self, seqno, sample_id,
               indent_level=1, print_xml=False):
        """
        Build an XML string representation of this AcquisitionActivity (for
        use in instances of the NexusLIMS schema)

        Parameters
        ----------
        seqno : int
            An integer number representing what number activity this is in a
            sequence of activities.
        sample_id : str
            A unique identifier pointing to a sample identifier. No checks
            are done on this value; it is merely reproduced in the XML output
        indent_level : int
            (Default is 1) the level of indentation to use in exporting. If
            0, no lines will be indented. A value of 1 should be appropriate
            for most cases as used in the Nexus schema
        print_xml : bool
            Whether to print the XML output to the console or not (Default:
            False)

        Returns
        -------
        activity_xml : str
            A string representing this AcquisitionActivity (note: is not a
            properly-formed complete XML document since it does not have a
            header or namespace definitions)
        """

        aqAc_xml = ''
        INDENT = '  ' * indent_level
        line_ending = '\n'

        aqAc_xml += f'{INDENT}<acquisitionActivity seqno="{seqno}">{line_ending}'
        aqAc_xml += f'{INDENT*2}<startTime>{self.start.isoformat()}' \
                        f'</startTime>{line_ending}'
        aqAc_xml += f'{INDENT*2}<sampleID>{sample_id}</sampleID>{line_ending}'
        aqAc_xml += f'{INDENT*2}<setup>{line_ending}'
        for pk, pv in sorted(self.setup_params.items()):
            # TODO: account for warnings here
            if pk == 'warnings':
                pass
            else:
                if isinstance(pv, str) and any(c in pv for c in '<&'):
                    pv = escape(pv)
                # for setup parameters, a key in the first dataset's warning
                # list is the same as in all of them
                pk_warning = pk in self.warnings[0]
                aqAc_xml += f'{INDENT*3}<param name="{pk}"' + \
                            (' warning="true">' if pk_warning else '>') + \
                            f'{pv}</param>{line_ending}'
        aqAc_xml += f'{INDENT*2}</setup>{line_ending}'

        # This is kind of a temporary hack until I figure out a better solution
        # TODO: fix determination of dataset types
        mode_to_dataset_type_map = {
            'IMAGING': 'Image',
            'DIFFRACTION': 'Diffraction'
        }
        for f, m, um, w in zip(self.files, self.meta,
                               self.unique_meta, self.warnings):
            # escape any bad characters in the filename
            if isinstance(f, str) and any(c in f for c in '<&'):
                f = escape(f)

            # build path to thumbnail
            rel_fname = f.replace(_mmf_path, '')
            rel_thumb_name = f'{rel_fname}.thumb.png'

            # f is string; um is a dictionary, w is a list
            aqAc_xml += f'{INDENT*2}<dataset ' \
                        f'type="{mode_to_dataset_type_map[self.mode]}" ' \
                        f'role="Experimental">{line_ending}'
            aqAc_xml += f'{INDENT*3}<name>{_os.path.basename(f)}' \
                        f'</name>{line_ending}'
            aqAc_xml += f'{INDENT*3}<location>{rel_fname}' \
                        f'</location>{line_ending}'
            aqAc_xml += f'{INDENT*3}<preview>{rel_thumb_name}' \
                        f'</preview>{line_ending}'
            for meta_k, meta_v in sorted(um.items()):
                if meta_k == 'warnings':
                    pass
                else:
                    if isinstance(meta_v, str) and \
                            any(c in meta_v for c in '<&'):
                        meta_v = escape(meta_v)
                    meta_k_warning = meta_k in w
                    aqAc_xml += f'{INDENT*3}<meta name="{meta_k}"' + \
                                (' warning="true">' if
                                 meta_k_warning else '>') + \
                                f'{meta_v}</meta>{line_ending}'
            aqAc_xml += f'{INDENT*2}</dataset>{line_ending}'

        aqAc_xml += f'{INDENT}</acquisitionActivity>{line_ending}'

        if print_xml:
            print(aqAc_xml)

        return aqAc_xml
