import os
import tarfile
from nexusLIMS.extractors.quanta_tif import get_quanta_metadata
from nexusLIMS.extractors import digital_micrograph
from nexusLIMS import instruments


class TestDigitalMicrographExtractor:
    tars = \
        {'CTEM': 'titan_CTEM_zeroData.dm3.tar.gz',
         'DP': 'titan_DP_zeroData.dm3.tar.gz',
         'CORRUPTED': 'test_corrupted.dm3.tar.gz',
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
         '642_STEM_DIFF': '642_Titan_STEM_DIFFRACTION_dataZeroed.dm3.tar.gz',
         '642_OPMODE_DIFF':
             '642_Titan_opmode_diffraction_dataZeroed.dm3.tar.gz',
         '642_EELS_SI_DRIFT':
             '642_Titan_EELS_SI_driftcorr_dataZeroed.dm3.tar.gz',
         '642_EELS_PROC_1': '642_Titan_EELS_proc_1_dataZeroed.dm3.tar.gz',
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

    def test_dm3_extraction_ctem(self):
        assert os.path.exists(self.files['CTEM'])

        metadata = digital_micrograph.get_dm3_metadata(self.files['CTEM'])

    def test_dm3_extraction_dp(self):
        assert os.path.exists(self.files['DP'])

        metadata = digital_micrograph.get_dm3_metadata(self.files['DP'])

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
        pass

    def test_642_dm3(self, monkeypatch):
        # monkeypatch so DM extractor thinks this file came from FEI Titan TEM
        def mock_instr(_):
            return instruments.instrument_db['FEI-Titan-TEM-635816']
        monkeypatch.setattr(digital_micrograph,
                            "_get_instr", mock_instr)

        meta = digital_micrograph.get_dm3_metadata(self.files['642_STEM_DIFF'])
        meta = digital_micrograph.get_dm3_metadata(self.files[
                                                       '642_OPMODE_DIFF'])
        meta = digital_micrograph.get_dm3_metadata(self.files[
                                                       '642_EELS_PROC_1'])
        meta = digital_micrograph.get_dm3_metadata(self.files[
                                                       '642_EELS_SI_DRIFT'])

    def test_643_dm3(self, monkeypatch):
        # monkeypatch so DM extractor thinks this file came from FEI Titan STEM
        def mock_instr(_):
            return instruments.instrument_db['FEI-Titan-STEM-630901']

        monkeypatch.setattr(digital_micrograph,
                            "_get_instr", mock_instr)
        meta = digital_micrograph.get_dm3_metadata(self.files['643_EFTEM_DIFF'])
        meta = digital_micrograph.get_dm3_metadata(self.files['643_EELS_SI'])
        meta = digital_micrograph.get_dm3_metadata(
            self.files['643_EELS_PROC_INT_BG'])
        meta = digital_micrograph.get_dm3_metadata(
            self.files['643_EELS_PROC_THICK'])
        meta = digital_micrograph.get_dm3_metadata(self.files['643_EDS_SI'])
        meta = digital_micrograph.get_dm3_metadata(self.files[
                                                       '643_EELS_SI_DRIFT'])

    def test_jeol3010_dm3(self, monkeypatch):
        # monkeypatch so DM extractor thinks this file came from JEOL 3010
        def mock_instr(_):
            return instruments.instrument_db['JEOL-JEM3010-TEM-565989']

        monkeypatch.setattr(digital_micrograph,
                            "_get_instr", mock_instr)

        meta = digital_micrograph.get_dm3_metadata(self.files['JEOL3010_DIFF'])

    def test_try_decimal(self):
        from nexusLIMS.extractors.digital_micrograph import _try_decimal
        assert 'bogus' == _try_decimal('bogus')

    def test_zero_data(self):
        from nexusLIMS.extractors.digital_micrograph import _zero_data_in_dm3
        input_path = os.path.join(os.path.dirname(__file__), 'files',
                                  'test_STEM_image.dm3')
        output_fname = os.path.splitext(input_path)[0] + '_test.dm3'
        fname_1 = _zero_data_in_dm3(input_path, out_filename=None)
        fname_2 = _zero_data_in_dm3(input_path, out_filename=output_fname)
        fname_3 = _zero_data_in_dm3(input_path, compress=False)

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
        assert metadata['nx_meta']['Creation Time'] == '2019-03-26T16:42:24'
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
