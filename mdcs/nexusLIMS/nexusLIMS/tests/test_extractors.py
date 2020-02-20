import os
import tarfile
from nexusLIMS.extractors.quanta_tif import get_quanta_metadata
from nexusLIMS.extractors import digital_micrograph
from nexusLIMS import instruments
import pytest


class TestDigitalMicrographExtractor:
    tars = \
        {'CORRUPTED': 'test_corrupted.dm3.tar.gz',
         'LIST_SIGNAL': 'list_signal_dataZeroed.dm3.tar.gz',
         '643_EFTEM_DIFF': '643_EFTEM_DIFFRACTION_dataZeroed.dm3.tar.gz',
         '643_EELS_SI': '643_Titan_EELS_SI_dataZeroed.dm3.tar.gz',
         '643_EELS_PROC_THICK':
             '643_Titan_EELS_proc_thickness_dataZeroed.dm3.tar.gz',
         '643_EELS_PROC_INT_BG':
             '643_Titan_EELS_proc_integrate_and_bg_dataZeroed.dm3.tar.gz',
         '643_EELS_SI_DRIFT':
             '643_Titan_EELS_SI_driftcorr_dataZeroed.dm3.tar.gz',
         '643_EDS_SI': '643_Titan_EDS_SI_dataZeroed.dm4.tar.gz',
         '643_STEM_STACK': '643_Titan_STEM_stack_dataZeroed.dm3.tar.gz',
         '642_STEM_DIFF': '642_Titan_STEM_DIFFRACTION_dataZeroed.dm3.tar.gz',
         '642_OPMODE_DIFF':
             '642_Titan_opmode_diffraction_dataZeroed.dm3.tar.gz',
         '642_EELS_SI_DRIFT':
             '642_Titan_EELS_SI_driftcorr_dataZeroed.dm3.tar.gz',
         '642_EELS_PROC_1': '642_Titan_EELS_proc_1_dataZeroed.dm3.tar.gz',
         '642_TECNAI_MAG': '642_Titan_Tecnai_mag_dataZeroed.dm3.tar.gz',
         'JEOL3010_DIFF': 'JEOL3010_diffraction_dataZeroed.dm3.tar.gz'
         }

    for name, f in tars.items():
        tars[name] = os.path.join(os.path.dirname(__file__), 'files', f)

    files = {}
    for k, v in tars.items():
        files[k] = v.strip('.tar.gz')

    @classmethod
    def setup_class(cls):
        """
        Setup the class by extracting the compressed test files
        """
        for name, tarf in cls.tars.items():
            with tarfile.open(tarf, 'r:gz') as tar:
                tar.extractall(path=os.path.dirname(tarf))

    @classmethod
    def teardown_class(cls):
        """
        Teardown the class by deleting the extracted test files
        """
        for name, f in cls.files.items():
            os.remove(f)

    def test_corrupted_file(self):
        assert digital_micrograph.get_dm3_metadata(
            self.files['CORRUPTED']) is None

    def test_dm3_list_file(self, monkeypatch):
        # monkeypatch so DM extractor thinks this file came from FEI Titan TEM
        def mock_instr(_):
            return instruments.instrument_db['FEI-Titan-TEM-635816']
        monkeypatch.setattr(digital_micrograph,
                            "_get_instr", mock_instr)

        metadata = digital_micrograph.get_dm3_metadata(
            self.files['LIST_SIGNAL'])

        assert metadata['nx_meta']['Data Type'] == 'STEM_Imaging'
        assert metadata['nx_meta']['Imaging Mode'] == 'DIFFRACTION'
        assert metadata['nx_meta']['Microscope'] == 'Titan80-300_D3094'
        assert metadata['nx_meta']['Voltage'] == 300000.0

    def test_642_dm3(self, monkeypatch):
        # monkeypatch so DM extractor thinks this file came from FEI Titan TEM
        def mock_instr(_):
            return instruments.instrument_db['FEI-Titan-TEM-635816']
        monkeypatch.setattr(digital_micrograph,
                            "_get_instr", mock_instr)

        meta = digital_micrograph.get_dm3_metadata(self.files['642_STEM_DIFF'])
        assert meta['nx_meta']['Data Type'] == 'STEM_Diffraction'
        assert meta['nx_meta']['Imaging Mode'] == 'DIFFRACTION'
        assert meta['nx_meta']['Microscope'] == 'MSED Titan'
        assert meta['nx_meta']['Voltage'] == 300000.0

        meta = digital_micrograph.get_dm3_metadata(self.files[
                                                       '642_OPMODE_DIFF'])
        assert meta['nx_meta']['Data Type'] == 'TEM_Diffraction'
        assert meta['nx_meta']['Imaging Mode'] == 'DIFFRACTION'
        assert meta['nx_meta']['Microscope'] == 'MSED Titan'
        assert meta['nx_meta']['Voltage'] == 300000.0

        meta = digital_micrograph.get_dm3_metadata(self.files[
                                                       '642_EELS_PROC_1'])
        assert meta['nx_meta']['Data Type'] == 'STEM_EELS'
        assert meta['nx_meta']['Imaging Mode'] == 'DIFFRACTION'
        assert meta['nx_meta']['Microscope'] == 'MSED Titan'
        assert meta['nx_meta']['Voltage'] == 300000.0
        assert meta['nx_meta']['EELS']['Processing Steps'] == \
            'Aligned parent SI By Peak, Extracted from SI'
        assert meta['nx_meta']['EELS']['Spectrometer Aperture label'] == '2mm'

        meta = digital_micrograph.get_dm3_metadata(self.files[
                                                       '642_EELS_SI_DRIFT'])
        assert meta['nx_meta']['Data Type'] == 'EELS_Spectrum_Imaging'
        assert meta['nx_meta']['Imaging Mode'] == 'DIFFRACTION'
        assert meta['nx_meta']['Microscope'] == 'MSED Titan'
        assert meta['nx_meta']['Voltage'] == 300000.0
        assert meta['nx_meta']['EELS']['Convergence semi-angle (mrad)'] == 10.0
        assert meta['nx_meta']['EELS']['Spectrometer Aperture label'] == '2mm'
        assert meta['nx_meta']['Spectrum Imaging']['Artefact Correction'] == \
            'Spatial drift correction every 100 seconds'
        assert meta['nx_meta']['Spectrum Imaging']['Pixel time (s)'] == 0.05

        meta = digital_micrograph.get_dm3_metadata(self.files[
                                                       '642_TECNAI_MAG'])
        assert meta['nx_meta']['Data Type'] == 'TEM_Imaging'
        assert meta['nx_meta']['Imaging Mode'] == 'IMAGING'
        assert meta['nx_meta']['Microscope'] == 'MSED Titan'
        assert meta['nx_meta']['Indicated Magnification'] == 8100.0
        assert meta['nx_meta']['Tecnai User'] == 'MBK1'
        assert meta['nx_meta']['Tecnai Mode'] == 'TEM uP SA Zoom Image'

    def test_643_dm3(self, monkeypatch):
        # monkeypatch so DM extractor thinks this file came from FEI Titan STEM
        def mock_instr(_):
            return instruments.instrument_db['FEI-Titan-STEM-630901']

        monkeypatch.setattr(digital_micrograph,
                            "_get_instr", mock_instr)
        meta = digital_micrograph.get_dm3_metadata(self.files['643_EFTEM_DIFF'])
        assert meta['nx_meta']['Data Type'] == 'TEM_EFTEM_Diffraction'
        assert meta['nx_meta']['DatasetType'] == 'Diffraction'
        assert meta['nx_meta']['Imaging Mode'] == 'EFTEM DIFFRACTION'
        assert meta['nx_meta']['Microscope'] == 'Titan80-300_D3094'
        assert meta['nx_meta']['STEM Camera Length'] == 5.0
        assert meta['nx_meta']['EELS']['Spectrometer Aperture label'] == '5 mm'

        meta = digital_micrograph.get_dm3_metadata(self.files['643_EELS_SI'])
        assert meta['nx_meta']['Data Type'] == 'EELS_Spectrum_Imaging'
        assert meta['nx_meta']['DatasetType'] == 'SpectrumImage'
        assert meta['nx_meta']['Imaging Mode'] == 'DIFFRACTION'
        assert meta['nx_meta']['Operation Mode'] == 'SCANNING'
        assert meta['nx_meta']['STEM Camera Length'] == 60.0
        assert meta['nx_meta']['EELS']['Convergence semi-angle (mrad)'] == 13.0
        assert meta['nx_meta']['EELS']['Exposure (s)'] == 0.5
        assert meta['nx_meta']['Spectrum Imaging']['Pixel time (s)'] == 0.5
        assert meta['nx_meta']['Spectrum Imaging']['Scan Mode'] == 'LineScan'
        assert meta['nx_meta']['Spectrum Imaging']['Acquisition Duration (s)'] \
            == 605

        meta = digital_micrograph.get_dm3_metadata(
            self.files['643_EELS_PROC_INT_BG'])
        assert meta['nx_meta']['Data Type'] == 'STEM_EELS'
        assert meta['nx_meta']['DatasetType'] == 'Spectrum'
        assert meta['nx_meta']['Analytic Signal'] == 'EELS'
        assert meta['nx_meta']['Analytic Format'] == 'Image'
        assert meta['nx_meta']['STEM Camera Length'] == 48.0
        assert meta['nx_meta']['EELS']['Background Removal Model'] == \
            'Power Law'
        assert meta['nx_meta']['EELS']['Processing Steps'] == \
            'Background Removal, Signal Integration'

        meta = digital_micrograph.get_dm3_metadata(
            self.files['643_EELS_PROC_THICK'])
        assert meta['nx_meta']['Data Type'] == 'STEM_EELS'
        assert meta['nx_meta']['DatasetType'] == 'Spectrum'
        assert meta['nx_meta']['Analytic Signal'] == 'EELS'
        assert meta['nx_meta']['Analytic Format'] == 'Spectrum'
        assert meta['nx_meta']['STEM Camera Length'] == 60.0
        assert meta['nx_meta']['EELS']['Exposure (s)'] == 0.05
        assert meta['nx_meta']['EELS']['Integration time (s)'] == 0.25
        assert meta['nx_meta']['EELS']['Processing Steps'] == \
            'Calibrated Post-acquisition, Compute Thickness'
        assert meta['nx_meta']['EELS']['Thickness (absolute) [nm]'] == \
            pytest.approx(85.29884338378906, 0.1)

        meta = digital_micrograph.get_dm3_metadata(self.files['643_EDS_SI'])
        assert meta['nx_meta']['Data Type'] == 'EDS_Spectrum_Imaging'
        assert meta['nx_meta']['DatasetType'] == 'SpectrumImage'
        assert meta['nx_meta']['Analytic Signal'] == 'X-ray'
        assert meta['nx_meta']['Analytic Format'] == 'Spectrum image'
        assert meta['nx_meta']['STEM Camera Length'] == 77.0
        assert meta['nx_meta']['EDS']['Real time (SI Average)'] == \
            pytest.approx(0.9696700292825698, 0.1)
        assert meta['nx_meta']['EDS']['Live time (SI Average)'] == \
            pytest.approx(0.9696700292825698, 0.1)
        assert meta['nx_meta']['Spectrum Imaging']['Pixel time (s)'] == 1.0
        assert meta['nx_meta']['Spectrum Imaging']['Scan Mode'] == 'LineScan'
        assert meta['nx_meta']['Spectrum Imaging'][
            'Spatial Sampling (Horizontal)'] == 100

        meta = digital_micrograph.get_dm3_metadata(self.files[
                                                       '643_EELS_SI_DRIFT'])
        assert meta['nx_meta']['Data Type'] == 'EELS_Spectrum_Imaging'
        assert meta['nx_meta']['DatasetType'] == 'SpectrumImage'
        assert meta['nx_meta']['Analytic Signal'] == 'EELS'
        assert meta['nx_meta']['Analytic Format'] == 'Spectrum image'
        assert meta['nx_meta']['Analytic Acquisition Mode'] == 'Parallel ' \
                                                               'dispersive'
        assert meta['nx_meta']['STEM Camera Length'] == 100.0
        assert meta['nx_meta']['EELS']['Exposure (s)'] == 0.5
        assert meta['nx_meta']['EELS']['Number of frames'] == 1
        assert meta['nx_meta']['Spectrum Imaging']['Acquisition Duration (s)']\
            == 2173
        assert meta['nx_meta']['Spectrum Imaging']['Artefact Correction'] == \
            'Spatial drift correction every 1 row'
        assert meta['nx_meta']['Spectrum Imaging']['Scan Mode'] == '2D Array'

        meta = digital_micrograph.get_dm3_metadata(self.files['643_STEM_STACK'])
        assert meta['nx_meta']['Data Type'] == 'STEM_Imaging'
        assert meta['nx_meta']['DatasetType'] == 'Image'
        assert meta['nx_meta']['Acquisition Device'] == 'DigiScan'
        assert meta['nx_meta']['Cs(mm)'] == 1.0
        assert meta['nx_meta']['Data Dimensions'] == '(12, 1024, 1024)'
        assert meta['nx_meta']['Indicated Magnification'] == 7200000.0
        assert meta['nx_meta']['STEM Camera Length'] == 100.0

    def test_jeol3010_dm3(self, monkeypatch):
        # monkeypatch so DM extractor thinks this file came from JEOL 3010
        def mock_instr(_):
            return instruments.instrument_db['JEOL-JEM3010-TEM-565989']

        monkeypatch.setattr(digital_micrograph,
                            "_get_instr", mock_instr)

        meta = digital_micrograph.get_dm3_metadata(self.files['JEOL3010_DIFF'])
        assert meta['nx_meta']['Data Type'] == 'TEM_Diffraction'
        assert meta['nx_meta']['DatasetType'] == 'Diffraction'
        assert meta['nx_meta']['Acquisition Device'] == 'Orius '
        assert meta['nx_meta']['Microscope'] == 'JEM3010 UHR'
        assert meta['nx_meta']['Data Dimensions'] == '(2672, 4008)'
        assert meta['nx_meta']['Facility'] == 'Microscopy Nexus'
        assert meta['nx_meta']['Camera/Detector Processing'] == \
            'Gain Normalized'

    def test_try_decimal(self):
        from nexusLIMS.extractors.digital_micrograph import _try_decimal
        # this function should just return the input if it cannot be
        # converted to a decimal
        assert 'bogus' == _try_decimal('bogus')

    def test_zero_data(self):
        from nexusLIMS.extractors.digital_micrograph import _zero_data_in_dm3
        input_path = os.path.join(os.path.dirname(__file__), 'files',
                                  'test_STEM_image.dm3')
        output_fname = os.path.splitext(input_path)[0] + '_test.dm3'
        fname_1 = _zero_data_in_dm3(input_path, out_filename=None)
        fname_2 = _zero_data_in_dm3(input_path, out_filename=output_fname)
        fname_3 = _zero_data_in_dm3(input_path, compress=False)

        # All three files should have been created
        for f in [fname_1, fname_2, fname_3]:
            assert os.path.isfile(f)

        # The first two files should be compressed so data is smaller
        assert os.path.getsize(input_path) > os.path.getsize(fname_1)
        assert os.path.getsize(input_path) > os.path.getsize(fname_2)
        # The last should be the same size
        assert os.path.getsize(input_path) == os.path.getsize(fname_3)

        meta_in = digital_micrograph.get_dm3_metadata(input_path)
        meta_3 = digital_micrograph.get_dm3_metadata(fname_3)

        # Creation times will be different, so remove that metadata
        del meta_in['nx_meta']['Creation Time']
        del meta_3['nx_meta']['Creation Time']

        # All other metadata should be equal
        assert meta_in == meta_3

        for f in [fname_1, fname_2, fname_3]:
            if os.path.isfile(f):
                os.remove(f)


class TestQuantaExtractor:
    QUANTA_TEST_FILE = os.path.join(os.path.dirname(__file__),
                                    "files", "quad1image_001.tif")
    QUANTA_BAD_MDATA = os.path.join(os.path.dirname(__file__),
                                    "files", "quanta_bad_metadata.tif")
    QUANTA_MODDED_MDATA = os.path.join(os.path.dirname(__file__),
                                       "files", "quanta_just_modded_mdata.tif")

    def test_quanta_extraction(self):
        metadata = get_quanta_metadata(self.QUANTA_TEST_FILE)

        # test 'nx_meta' values of interest
        assert metadata['nx_meta']['Data Type'] == 'SEM_Imaging'
        assert metadata['nx_meta']['DatasetType'] == 'Image'
        assert metadata['nx_meta']['Creation Time'] == \
            '2019-03-26T16:42:24.234538'
        assert metadata['nx_meta']['warnings'] == [['Operator']]

        # test two values from each of the native sections
        assert metadata['User']['Date'] == '12/18/2017'
        assert metadata['User']['Time'] == '01:04:14 PM'
        assert metadata['System']['Type'] == 'SEM'
        assert metadata['System']['Dnumber'] == 'D8439'
        assert metadata['Beam']['HV'] == '30000'
        assert metadata['Beam']['Spot'] == '3'
        assert metadata['EBeam']['Source'] == 'FEG'
        assert metadata['EBeam']['FinalLens'] == 'S45'
        assert metadata['GIS']['Number'] == '0'
        assert metadata['EScan']['InternalScan']
        assert metadata['EScan']['Scan'] == 'PIA 2.0'
        assert metadata['Stage']['StageX'] == '0.009654'
        assert metadata['Stage']['StageY'] == '0.0146008'
        assert metadata['Image']['ResolutionX'] == '1024'
        assert metadata['Image']['DigitalContrast'] == '1'
        assert metadata['Vacuum']['ChPressure'] == '79.8238'
        assert metadata['Vacuum']['Gas'] == 'Wet'
        assert metadata['Specimen']['Temperature'] == ""
        assert metadata['Detectors']['Number'] == '1'
        assert metadata['Detectors']['Name'] == "LFD"
        assert metadata['LFD']['Contrast'] == '62.4088'
        assert metadata['LFD']['Brightness'] == '45.7511'
        assert metadata['Accessories']['Number'] == '0'
        assert metadata['PrivateFei']['BitShift'] == '0'
        assert metadata['PrivateFei']['DataBarSelected'] == \
            "DateTime dwell HV HFW pressure Label MicronBar"
        assert metadata['HiResIllumination']['BrightFieldIsOn'] == ""
        assert metadata['HiResIllumination']['BrightFieldValue'] == ""

    def test_bad_metadata(self):
        assert get_quanta_metadata(self.QUANTA_BAD_MDATA) is None

    def test_modded_metadata(self):
        metadata = get_quanta_metadata(self.QUANTA_MODDED_MDATA)

        # test 'nx_meta' values of interest
        assert metadata['nx_meta']['Data Type'] == 'SEM_Imaging'
        assert metadata['nx_meta']['DatasetType'] == 'Image'
        assert metadata['nx_meta']['Creation Time'] == '2020-02-20T00:52:55'
        assert metadata['nx_meta']['warnings'] == [['Operator']]

        assert metadata['nx_meta']['Scan Rotation (°)'] == 179.9947
        assert metadata['nx_meta']['Tilt Correction Angle'] == 0.0121551
        assert metadata['nx_meta']['Specimen Temperature (K)'] == 'j'
        assert len(metadata['nx_meta']['Chamber Pressure (mPa)']) == 7000
