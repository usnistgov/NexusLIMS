import os as _os
import logging as _logging
from datetime import datetime as _datetime
import hyperspy.api_nogui as _hs
from nexusLIMS.extractors.digital_micrograph import \
    process_tecnai_microscope_info as _tecnai

_logger = _logging.getLogger(__name__)


def read_metadata(sig):
    """
    For a signal like that contained in ``self.sigs``, parse the
    "important" metadata, so it can be compared to find common values
    that will be defined as AcquisitionActivity parameters

    Parameters
    ----------
    sig : HyperSpy signal
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
    - General .dm3 tags:
        ImageTags.Microscope_Info.Indicated_Magnification
        ImageTags.Microscope_Info.Actual_Magnification
        ImageTags.Microscope_Info.Csmm
        ImageTags.Microscope_Info.STEM_Camera_Length
        ImageTags.Microscope_Info.Voltage

    - Tecnai info:
        ImageTags.Tecnai.Microscope_Info['Gun_Name']
        ImageTags.Tecnai.Microscope_Info['Extractor_Voltage']
        ImageTags.Tecnai.Microscope_Info['Gun_Lens_No']
        ImageTags.Tecnai.Microscope_Info['Emission_Current']
        ImageTags.Tecnai.Microscope_Info['Spot']
        ImageTags.Tecnai.Microscope_Info['Mode']
        C2, C3, Obj, Dif lens strength:
          ImageTags.Tecnai.Microscope_Info['C2_Strength', 'C3_Strength',
                                           'Obj_Strength', 'Dif_Strength']
        ImageTags.Tecnai.Microscope_Info['Image_Shift_x'/'Image_Shift_y'])
        ImageTags.Tecnai.Microscope_Info['Stage_Position_x' (y/z/theta/phi)]
        C1/C2/Objective/SA aperture sizes:
        ImageTags.Tecnai.Microscope_Info['(C1/C2/Obj/SA)_Aperture']
        ImageTags.Tecnai.Microscope_Info['Filter_Settings']['Mode']
        ImageTags.Tecnai.Microscope_Info['Filter_Settings']['Dispersion']
        ImageTags.Tecnai.Microscope_Info['Filter_Settings']['Aperture']
        ImageTags.Tecnai.Microscope_Info['Filter_Settings']['Prism_Shift']
        ImageTags.Tecnai.Microscope_Info['Filter_Settings']['Drift_Tube']
        ImageTags.Tecnai.Microscope_Info['Filter_Settings'][
        'Total_Energy_Loss']
    """
    m = {}
    # Obviously will need to be changed for non-dm3 data and other
    # instruments
    ImageTags = sig.original_metadata.ImageList.TagGroup0.ImageTags
    tecnai_info = _tecnai(ImageTags.Tecnai.Microscope_Info)
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
            _logger.warning(f'Tecnai.Microscope_Info.{k}' +
                            ' not found in the metadata dictionary')
    for k in ['Mode', 'Dispersion', 'Aperture', 'Prism_Shift',
              'Drift_Tube', 'Total_Energy_Loss']:
        try:
            m[f'Filter.{k}'] = tecnai_info['Filter_Settings'][k]
        except KeyError:
            _logger.warning(f'Filter_Settings.{k} not found' +
                            ' in the metadata dictionary')

    return m


# TODO: tests for all of AcquisitionActivity
class AcquisitionActivity:
    """
    A collection of files/metadata attributed to a physical acquisition activity

    Instances of this class correspond to AcquisitionActivity nodes in the
    `NexusLIMS schema <https://data.nist.gov/od/dm/nexus/experiment/v1.0>`_

    Attributes
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
        into ``setup_params`)
    files : list
        A list of filenames belonging to this AcquisitionActivity
    sigs : list
        A list of *lazy* (to minimize loading times) HyperSpy signals in this
        AcquisitionActivity. HyperSpy is used to facilitate metadata reading
    meta : list
        A list of dictionaries containing the "important" metadata for each
        signal/file in ``sigs`` and ``files``
    """

    def __init__(self,
                 start=_datetime.now(),
                 end=_datetime.now(),
                 mode='',
                 unique_params=None,
                 setup_params=None,
                 unique_meta=None,
                 files=None,
                 sigs=None,
                 meta=None):
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
        self.sigs = [] if sigs is None else sigs
        self.meta = [] if meta is None else meta

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
            s = _hs.load(fname, lazy=True)
            self.files.append(fname)
            self.sigs.append(s)
            self.meta.append(read_metadata(s))
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
        values_to_search : iterable type
            A list (or tuple, set, or other iterable) containing values to
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

        # DONE: implement setup parameter determination
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
