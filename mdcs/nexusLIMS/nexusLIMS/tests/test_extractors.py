import os
import tarfile
import pytest
import numpy as np
import matplotlib.pyplot as plt
import hyperspy.api as hs
import logging

import nexusLIMS
from nexusLIMS import instruments
from nexusLIMS.tests.utils import tars, files
from nexusLIMS.extractors import digital_micrograph
from nexusLIMS.extractors.quanta_tif import get_quanta_metadata
from nexusLIMS.extractors import thumbnail_generator
from nexusLIMS.extractors import parse_metadata, flatten_dict
from nexusLIMS.extractors.thumbnail_generator import sig_to_thumbnail
from nexusLIMS.extractors.thumbnail_generator import down_sample_image


class TestThumbnailGenerator:
    @classmethod
    def setup_class(cls):
        cls.s = hs.datasets.example_signals.EDS_TEM_Spectrum()
        cls.oned_s = hs.stack([cls.s * i for i in np.arange(.1, 1, .3)],
                              new_axis_name='x')
        cls.twod_s = hs.stack([cls.oned_s * i for i in np.arange(.1, 1, .3)],
                              new_axis_name='y')
        cls.threed_s = hs.stack([cls.twod_s * i for i in
                                np.arange(.1, 1, .3)], new_axis_name='z')

    @pytest.mark.mpl_image_compare(style='default')
    def test_0d_spectrum(self):
        self.s.metadata.General.title = 'Dummy spectrum'
        fig = sig_to_thumbnail(self.s, 'output.png')
        os.remove('output.png')
        return fig

    @pytest.mark.mpl_image_compare(style='default')
    def test_1d_spectrum_image(self):
        self.oned_s.metadata.General.title = 'Dummy line scan'
        fig = sig_to_thumbnail(self.oned_s, f'output.png')
        os.remove('output.png')
        return fig

    @pytest.mark.mpl_image_compare(style='default')
    def test_2d_spectrum_image(self):
        self.twod_s.metadata.General.title = 'Dummy 2D spectrum image'
        fig = sig_to_thumbnail(self.twod_s, f'output.png')
        os.remove('output.png')
        return fig

    @pytest.mark.mpl_image_compare(style='default')
    def test_2d_spectrum_image_nav_under_9(self):
        self.twod_s.metadata.General.title = 'Dummy 2D spectrum image'
        fig = sig_to_thumbnail(self.twod_s.inav[:2,:2], f'output.png',)
        os.remove('output.png')
        return fig

    @pytest.mark.mpl_image_compare(style='default')
    def test_3d_spectrum_image(self):
        self.threed_s.metadata.General.title = 'Dummy 3D spectrum image'
        fig = sig_to_thumbnail(self.threed_s, f'output.png')
        os.remove('output.png')
        return fig

    @pytest.mark.mpl_image_compare(style='default')
    def test_single_image(self):
        fig = sig_to_thumbnail(hs.load(files['643_EFTEM_DIFF']), f'output.png')
        os.remove('output.png')
        return fig

    @pytest.mark.mpl_image_compare(style='default')
    def test_single_not_dm3_image(self):
        s = hs.load(files['643_EFTEM_DIFF'])
        s.metadata.General.original_filename = 'not dm3'
        fig = sig_to_thumbnail(s, f'output.png')
        os.remove('output.png')
        return fig

    @pytest.mark.mpl_image_compare(style='default')
    def test_image_stack(self):
        fig = sig_to_thumbnail(hs.load(files['643_STEM_STACK']), f'output.png')
        os.remove('output.png')
        return fig

    @pytest.mark.mpl_image_compare(style='default')
    def test_4d_stem_type(self):
        fig = sig_to_thumbnail(hs.load(files['4D_STEM']), f'output.png')
        os.remove('output.png')
        return fig

    @pytest.mark.mpl_image_compare(style='default')
    def test_4d_stem_type_1(self):
        # nav size >= 4 but < 9
        fig = sig_to_thumbnail(hs.load(files['4D_STEM']).inav[:2, :3],
                               f'output.png')
        os.remove('output.png')
        return fig

    @pytest.mark.mpl_image_compare(style='default')
    def test_4d_stem_type_2(self):
        # nav size = 1
        fig = sig_to_thumbnail(hs.load(files['4D_STEM']).inav[:1, :2],
                               f'output.png')
        os.remove('output.png')
        return fig

    @pytest.mark.mpl_image_compare(style='default')
    def test_complex_image(self):
        fig = sig_to_thumbnail(hs.load(files['FFT']), f'output.png')
        os.remove('output.png')
        return fig

    @pytest.mark.mpl_image_compare(style='default')
    def test_higher_dimensional_signal(self):
        dict0 = {'size': 10, 'name': 'nav axis 3', 'units': 'nm',
                 'scale': 2, 'offset': 0}
        dict1 = {'size': 10, 'name': 'nav axis 2', 'units': 'pm',
                 'scale': 200, 'offset': 0}
        dict2 = {'size': 10, 'name': 'nav axis 1', 'units': 'mm',
                 'scale': 0.02, 'offset': 0}
        dict3 = {'size': 10, 'name': 'sig axis 3', 'units': 'eV',
                 'scale': 100, 'offset': 0}
        dict4 = {'size': 10, 'name': 'sig axis 2', 'units': 'Hz',
                 'scale': 0.2121, 'offset': 0}
        dict5 = {'size': 10, 'name': 'sig axis 1', 'units': 'radians',
                 'scale': 0.314, 'offset': 0}
        s = hs.signals.BaseSignal(np.zeros((10, 10, 10, 10, 10, 10),
                                           dtype=int),
                                  axes=[dict0, dict1, dict2, dict3, dict4,
                                        dict5])
        s = s.transpose(navigation_axes=3)
        s.metadata.General.title = 'Signal with higher-order dimensionality'
        fig = sig_to_thumbnail(s, f'output.png')
        os.remove('output.png')
        return fig

    @pytest.mark.mpl_image_compare(style='default')
    def test_survey_image(self):
        fig = sig_to_thumbnail(hs.load(files['643_SURVEY']), f'output.png')
        os.remove('output.png')
        return fig

    def test_annotation_error(self, monkeypatch):
        def monkey_get_annotation(a, b):
            raise ValueError("Mocked error for testing")
        monkeypatch.setattr(thumbnail_generator,
                            "_get_markers_dict", monkey_get_annotation)
        thumbnail_generator.add_annotation_markers(hs.load(files['643_SURVEY']))

    @pytest.mark.mpl_image_compare(style='default')
    def test_annotations(self):
        fig = sig_to_thumbnail(hs.load(files['642_ANNOTATIONS']), f'output.png')
        os.remove('output.png')
        return fig

    def test_downsample_image_errors(self):
        with pytest.raises(ValueError):
            # providing neither output size and factor should raise an error
            down_sample_image('', '')

        with pytest.raises(ValueError):
            # providing both output size and factor should raise an error
            down_sample_image('', '', output_size=(20, 20), factor=5)

    @pytest.mark.mpl_image_compare(style='default')
    def test_downsample_image_factor(self):
        fig = down_sample_image(TestQuantaExtractor.QUANTA_TEST_FILE,
                                'output.png', factor=3)
        os.remove('output.png')
        return fig

    @pytest.mark.mpl_image_compare(style='default')
    def test_downsample_image_32_bit(self):
        fig = down_sample_image(files['QUANTA_32BIT'],
                                'output.png', factor=2)
        os.remove('output.png')
        return fig

    @pytest.mark.mpl_image_compare(style='default')
    def test_downsample_image_output_size(self):
        fig = down_sample_image(TestQuantaExtractor.QUANTA_TEST_FILE,
                                'output.png', output_size=(500, 500))
        os.remove('output.png')
        return fig


class TestExtractorModule:
    def test_parse_metadata_642_titan(self):
        meta, thumb_fname = parse_metadata(fname=files['PARSE_META_642_TITAN'])
        assert meta['nx_meta']['Acquisition Device'] == 'BM-UltraScan'
        assert meta['nx_meta']['Actual Magnification'] == 17677.0
        assert meta['nx_meta']['Cs(mm)'] == 1.2
        assert meta['nx_meta']['Data Dimensions'] == '(2048, 2048)'
        assert meta['nx_meta']['Data Type'] == 'TEM_Imaging'
        assert meta['nx_meta']['DatasetType'] == 'Image'
        assert len(meta['nx_meta']['warnings']) == 0

        os.remove(thumb_fname)
        os.remove(thumb_fname.replace('thumb.png', 'json'))

    def test_parse_metadata_list_signal(self):
        meta, thumb_fname = parse_metadata(fname=files['LIST_SIGNAL'])
        assert meta['nx_meta']['Acquisition Device'] == 'DigiScan'
        assert meta['nx_meta']['STEM Camera Length'] == 77.0
        assert meta['nx_meta']['Cs(mm)'] == 1.0
        assert meta['nx_meta']['Data Dimensions'] == '(512, 512)'
        assert meta['nx_meta']['Data Type'] == 'STEM_Imaging'
        assert meta['nx_meta']['DatasetType'] == 'Image'
        assert len(meta['nx_meta']['warnings']) == 0

        os.remove(thumb_fname)
        os.remove(thumb_fname.replace('thumb.png', 'json'))

    def test_parse_metadata_overwrite_false(self, caplog):
        thumb_fname = files['LIST_SIGNAL'] + '.thumb.png'
        # create the thumbnail file so we can't overwrite
        open(thumb_fname, 'a').close()
        nexusLIMS.extractors._logger.setLevel(logging.INFO)
        meta, thumb_fname = parse_metadata(fname=files['LIST_SIGNAL'],
                                           overwrite=False)
        assert 'Preview already exists' in caplog.text
        os.remove(thumb_fname)
        os.remove(thumb_fname.replace('thumb.png', 'json'))

    def test_parse_metadata_quanta(self, monkeypatch):
        def mock_instr(_):
            return instruments.instrument_db['FEI-Quanta200-ESEM-633137']
        monkeypatch.setattr(nexusLIMS.extractors,
                            "_get_instr", mock_instr)

        meta, thumb_fname = parse_metadata(fname=files['QUANTA_TIF'])
        os.remove(thumb_fname)
        os.remove(thumb_fname.replace('thumb.png', 'json'))

    def test_parse_metadata_tif_other_instr(self, monkeypatch):
        def mock_instr(_):
            return None
        monkeypatch.setattr(nexusLIMS.extractors,
                            "_get_instr", mock_instr)

        meta, thumb_fname = parse_metadata(fname=files['QUANTA_TIF'])
        os.remove(thumb_fname)
        os.remove(thumb_fname.replace('thumb.png', 'json'))

    def test_parse_metadata_no_dataset_type(self, monkeypatch):
        monkeypatch.setitem(nexusLIMS.extractors.extension_reader_map,
                            'tif', lambda x: {'nx_meta': {'key': 'val'}})

        meta, thumb_fname = parse_metadata(fname=files['QUANTA_TIF'])
        assert meta['nx_meta']['DatasetType'] == 'Misc'
        assert meta['nx_meta']['Data Type'] == 'Miscellaneous'
        assert meta['nx_meta']['key'] == 'val'

        os.remove(thumb_fname)
        os.remove(thumb_fname.replace('thumb.png', 'json'))

    def test_flatten_dict(self):
        dict_to_flatten = {
            'level1.1': 'level1.1v',
            'level1.2': {
                'level2.1': 'level2.1v'
            }
        }

        flattened = flatten_dict(dict_to_flatten)
        assert flattened == {
            'level1.1': 'level1.1v',
            'level1.2 level2.1': 'level2.1v'
        }


class TestDigitalMicrographExtractor:
    def test_corrupted_file(self):
        assert digital_micrograph.get_dm3_metadata(
            files['CORRUPTED']) is None

    def test_dm3_list_file(self, monkeypatch):
        # monkeypatch so DM extractor thinks this file came from FEI Titan TEM
        def mock_instr(_):
            return instruments.instrument_db['FEI-Titan-TEM-635816']
        monkeypatch.setattr(digital_micrograph,
                            "_get_instr", mock_instr)

        metadata = digital_micrograph.get_dm3_metadata(
            files['LIST_SIGNAL'])

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

        meta = digital_micrograph.get_dm3_metadata(files['642_STEM_DIFF'])
        assert meta['nx_meta']['Data Type'] == 'STEM_Diffraction'
        assert meta['nx_meta']['Imaging Mode'] == 'DIFFRACTION'
        assert meta['nx_meta']['Microscope'] == 'MSED Titan'
        assert meta['nx_meta']['Voltage'] == 300000.0

        meta = digital_micrograph.get_dm3_metadata(files[
                                                       '642_OPMODE_DIFF'])
        assert meta['nx_meta']['Data Type'] == 'TEM_Diffraction'
        assert meta['nx_meta']['Imaging Mode'] == 'DIFFRACTION'
        assert meta['nx_meta']['Microscope'] == 'MSED Titan'
        assert meta['nx_meta']['Voltage'] == 300000.0

        meta = digital_micrograph.get_dm3_metadata(files['642_EELS_PROC_1'])
        assert meta['nx_meta']['Data Type'] == 'STEM_EELS'
        assert meta['nx_meta']['Imaging Mode'] == 'DIFFRACTION'
        assert meta['nx_meta']['Microscope'] == 'MSED Titan'
        assert meta['nx_meta']['Voltage'] == 300000.0
        assert meta['nx_meta']['EELS']['Processing Steps'] == \
            'Aligned parent SI By Peak, Extracted from SI'
        assert meta['nx_meta']['EELS']['Spectrometer Aperture label'] == '2mm'

        meta = digital_micrograph.get_dm3_metadata(files['642_EELS_SI_DRIFT'])
        assert meta['nx_meta']['Data Type'] == 'EELS_Spectrum_Imaging'
        assert meta['nx_meta']['Imaging Mode'] == 'DIFFRACTION'
        assert meta['nx_meta']['Microscope'] == 'MSED Titan'
        assert meta['nx_meta']['Voltage'] == 300000.0
        assert meta['nx_meta']['EELS']['Convergence semi-angle (mrad)'] == 10.0
        assert meta['nx_meta']['EELS']['Spectrometer Aperture label'] == '2mm'
        assert meta['nx_meta']['Spectrum Imaging']['Artefact Correction'] == \
            'Spatial drift correction every 100 seconds'
        assert meta['nx_meta']['Spectrum Imaging']['Pixel time (s)'] == 0.05

        meta = digital_micrograph.get_dm3_metadata(files['642_TECNAI_MAG'])
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
        meta = digital_micrograph.get_dm3_metadata(files['643_EFTEM_DIFF'])
        assert meta['nx_meta']['Data Type'] == 'TEM_EFTEM_Diffraction'
        assert meta['nx_meta']['DatasetType'] == 'Diffraction'
        assert meta['nx_meta']['Imaging Mode'] == 'EFTEM DIFFRACTION'
        assert meta['nx_meta']['Microscope'] == 'Titan80-300_D3094'
        assert meta['nx_meta']['STEM Camera Length'] == 5.0
        assert meta['nx_meta']['EELS']['Spectrometer Aperture label'] == '5 mm'

        meta = digital_micrograph.get_dm3_metadata(files['643_EELS_SI'])
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
            files['643_EELS_PROC_INT_BG'])
        assert meta['nx_meta']['Data Type'] == 'STEM_EELS'
        assert meta['nx_meta']['DatasetType'] == 'Spectrum'
        assert meta['nx_meta']['Analytic Signal'] == 'EELS'
        assert meta['nx_meta']['Analytic Format'] == 'Image'
        assert meta['nx_meta']['STEM Camera Length'] == 48.0
        assert meta['nx_meta']['EELS']['Background Removal Model'] == \
            'Power Law'
        assert meta['nx_meta']['EELS']['Processing Steps'] == \
            'Background Removal, Signal Integration'

        meta = digital_micrograph.get_dm3_metadata(files['643_EELS_PROC_THICK'])
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

        meta = digital_micrograph.get_dm3_metadata(files['643_EDS_SI'])
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

        meta = digital_micrograph.get_dm3_metadata(files['643_EELS_SI_DRIFT'])
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

        meta = digital_micrograph.get_dm3_metadata(files['643_STEM_STACK'])
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

        meta = digital_micrograph.get_dm3_metadata(files['JEOL3010_DIFF'])
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
        for fn in [fname_1, fname_2, fname_3]:
            assert os.path.isfile(fn)

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

        for fn in [fname_1, fname_2, fname_3]:
            if os.path.isfile(fn):
                os.remove(fn)


class TestQuantaExtractor:
    QUANTA_TEST_FILE = files['QUANTA_TIF']
    QUANTA_BAD_MDATA = os.path.join(os.path.dirname(__file__),
                                    "files", "quanta_bad_metadata.tif")
    QUANTA_MODDED_MDATA = os.path.join(os.path.dirname(__file__),
                                       "files", "quanta_just_modded_mdata.tif")

    def test_quanta_extraction(self):
        metadata = get_quanta_metadata(self.QUANTA_TEST_FILE)

        # test 'nx_meta' values of interest
        assert metadata['nx_meta']['Data Type'] == 'SEM_Imaging'
        assert metadata['nx_meta']['DatasetType'] == 'Image'
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
        assert metadata['nx_meta']['warnings'] == [['Operator']]

        assert metadata['nx_meta']['Scan Rotation (°)'] == 179.9947
        assert metadata['nx_meta']['Tilt Correction Angle'] == 0.0121551
        assert metadata['nx_meta']['Specimen Temperature (K)'] == 'j'
        assert len(metadata['nx_meta']['Chamber Pressure (mPa)']) == 7000
