import os as _os
import logging as _logging
from datetime import datetime as _datetime
import hyperspy.api_nogui as _hs
from nexusLIMS.extractors.digital_micrograph import \
    process_tecnai_microscope_info as _tecnai

_logger = _logging.getLogger(__name__)


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
                 files=None,
                 sigs=None,
                 meta=None):
        """
        Create a new AcquisitionActivity
        """
        self.start = start
        self.end = end
        self.mode = mode
        # Use None as defaults in __init__ so there are no mutables in __init__
        self.unique_params = set() if unique_params is None else unique_params
        self.setup_params = {} if setup_params is None else setup_params
        self.files = [] if files is None else files
        self.sigs = [] if sigs is None else sigs
        self.meta = [] if meta is None else meta

    def __repr__(self):
        return self.__str__()

    def __str__(self):
        return '{0:<12} AcquisitionActivity; '.format(self.mode) + \
               'start: {}; '.format(self.start.isoformat()) + \
               'end: {}'.format(self.end.isoformat())

    def add_file(self, fname):
        """
        Add a file to this activity's file list

        Parameters
        ----------
        fname : str
            The file to be added to the file list
        """
        if _os.path.exists(fname):
            self.files.append(fname)
            self.sigs.append(_hs.load(fname, lazy=True))
            self.meta.append({})
        else:
            raise FileNotFoundError(fname + ' was not found')
        _logger.warning('appended {} to files'.format(fname))
        _logger.warning('self.files is now {}'.format(self.files))

    def read_metadata(self):
        """
        For each signal in self.sigs, parse the "important" metadata, so it can
        be compared to find common values that will be defined as
        AcquisitionActivity parameters

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
        for i, s in enumerate(self.sigs):
            m = self.meta[i]
            # Obviously will need to be changed for non-dm3 data and other
            # instruments
            ImageTags = s.original_metadata.ImageList.TagGroup0.ImageTags
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
                      'Emission_Current', 'Spot', 'Mode', 'C2_Strength',
                      'C3_Strength', 'Obj_Strength', 'Dif_Strength',
                      'Image_Shift_x', 'Image_Shift_y', 'Stage_Position_x',
                      'Stage_Position_y', 'Stage_Position_z',
                      'Stage_Position_theta', 'Stage_Position_phi',
                      'C1_Aperture', 'C2_Aperture', 'Obj_Aperture',
                      'SA_Aperture']:
                try:
                    m[k] = tecnai_info[k]
                except KeyError:
                    _logger.warning('Tecnai.Microscope_Info.{}'.format(k) +
                                    ' not found in the metadata dictionary')
            for k in ['Mode', 'Dispersion', 'Aperture', 'Prism_Shift',
                      'Drift_Tube', 'Total_Energy_Loss']:
                try:
                    m['Filter.{}'.format(k)] = tecnai_info['Filter_Settings'][k]
                except KeyError:
                    _logger.warning('Filter_Settings.{} not found'.format(k) +
                                    ' in the metadata dictionary')

    #             pprint(m)
    #             print()

    def store_unique_params(self):
        """
        Analyze the metadata keys contained in this AcquisitionActivity and
        store the unique values in a set (``self.unique_params``)
        """
        if len(self.meta) == 0:
            _logger.info('Reading metadata for files in AcquisitionActivity')
            self.read_metadata()

        # self.meta is a list of dictionaries
        for m in self.meta:
            self.unique_params.update(m.keys())

    def determine_setup_params(self, values_to_search=None):
        """
        Search the metadata of files in this AcquisitionActivity for those
        containing identical values over all files, which will then be defined
        as parameters attributed to experimental setup, rather than individual
        datasets.

        Parameters
        ----------
        values_to_search : iterable type
            A list (or tuple, set, or other iterable) containing values to
            search for in the metadata dictionary list. If None (default), all
            values contained in any file will be searched.

        Returns
        -------
        setup_params : dict
            A dictionary containing the metadata keys and values that are
            consistent across all files in this AcquisitionActivity. This value
            is also stored as an attribute (``self.setup_params``) for this
            instance.
        """
        # Make sure metadata and unique params are defined before proceeding:
        if len(self.meta) == 0:
            _logger.info('Reading metadata for files in AcquisitionActivity')
            self.read_metadata()
        if len(self.unique_params) == 0:
            _logger.info('Storing unique parameters for files in '
                         'AcquisitionActivity')
            self.store_unique_params()

        if values_to_search is None:
            values_to_search = self.unique_params

        # m will be individual dictionaries, since meta is list of dicts
        for m, f in zip(self.meta, self.files):
            # loop through the values_to_search
            # for the first iteration, store any value found for a parameter
            # as a "setup parameter". if it is not found, do not store it (
            # and remove from values_to_search to prevent it being searched
            # on subsequent iterations. On the subsequent iterations,
            # test if values are same or different.
            # If different, then remove the key from setup_params and
            # values_to_search, so at the end only identical values remain
            # and duplicate value checks are minimized
            print(f)
            for vts in values_to_search:
                print(vts)
                print(m[vts])
                print()
