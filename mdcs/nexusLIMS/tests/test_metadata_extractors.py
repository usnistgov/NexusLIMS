import os
from ..extractors import quanta_tif as qt
from configparser import ConfigParser


class TestMetadataExtraction:
    QUANTA_TEST_FILE = os.path.join(os.path.dirname(__file__),
                                    "files", "quad1image_001.tif")

    def test_quanta_extraction(self):
        metadata = qt.get_metadata(self.QUANTA_TEST_FILE)

        # Because the metadata is structured as an .ini file, we can user
        # ConfigParser to get the values from it easily
        meta = ConfigParser()
        meta.read_string(metadata)

        # test two values from each section
        assert meta.get('User', 'Date') == '12/18/2017'
        assert meta.get('User', 'Time') == '01:04:14 PM'
        assert meta.get('System', 'Type') == 'SEM'
        assert meta.get('System', 'Dnumber') == 'D8439'
        assert meta.getint('Beam', 'HV') == 30000
        assert meta.getint('Beam', 'Spot') == 3
        assert meta.get('EBeam', 'Source') == 'FEG'
        assert meta.get('EBeam', 'FinalLens') == 'S45'
        assert meta.getint('GIS', 'Number') == 0
        assert meta.getboolean('EScan', 'InternalScan')
        assert meta.get('EScan', 'Scan') == 'PIA 2.0'
        assert meta.getfloat('Stage', 'StageX') == 0.009654
        assert meta.getfloat('Stage', 'StageY') == 0.0146008
        assert meta.getint('Image', 'ResolutionX') == 1024
        assert meta.getint('Image', 'DigitalContrast') == 1
        assert meta.getfloat('Vacuum', 'ChPressure') == 79.8238
        assert meta.get('Vacuum', 'Gas') == 'Wet'
        assert meta.get('Specimen', 'Temperature') == ""
        assert meta.getint('Detectors', 'Number') == 1
        assert meta.get('Detectors', 'Name') == "LFD"
        assert meta.getfloat('LFD', 'Contrast') == 62.4088
        assert meta.getfloat('LFD', 'Brightness') == 45.7511
        assert meta.getint('Accessories', 'Number') == 0
        assert meta.getint('PrivateFei', 'BitShift') == 0
        assert meta.get('PrivateFei', 'DataBarSelected') == "DateTime " \
                                                            "dwell HV HFW " \
                                                            "pressure " \
                                                            "Label MicronBar"
        assert meta.get('HiResIllumination', 'BrightFieldIsOn') == ""
        assert meta.get('HiResIllumination', 'BrightFieldValue') == ""
