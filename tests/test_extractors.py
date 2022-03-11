import os
import tarfile
import pytest
import numpy as np
import matplotlib.pyplot as plt
import hyperspy.api as hs
import logging
from datetime import datetime as dt

import nexusLIMS
from nexusLIMS import instruments
from .utils import tars, files
from nexusLIMS.extractors import digital_micrograph
from nexusLIMS.extractors import fei_emi
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
        fig = sig_to_thumbnail(self.twod_s.inav[:2, :2], f'output.png', )
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

    @pytest.mark.mpl_image_compare(style='default', tolerance=20)
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
        fig = down_sample_image(files['QUANTA_32BIT'][0],
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
        meta, thumb_fname = parse_metadata(fname=files[
            'PARSE_META_642_TITAN'][0])
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
        meta, thumb_fname = parse_metadata(fname=files['LIST_SIGNAL'][0])
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
        thumb_fname = files['LIST_SIGNAL'][0] + '.thumb.png'
        # create the thumbnail file so we can't overwrite
        open(thumb_fname, 'a').close()
        nexusLIMS.extractors._logger.setLevel(logging.INFO)
        meta, thumb_fname = parse_metadata(fname=files['LIST_SIGNAL'][0],
                                           overwrite=False)
        assert 'Preview already exists' in caplog.text
        os.remove(thumb_fname)
        os.remove(thumb_fname.replace('thumb.png', 'json'))

    def test_parse_metadata_quanta(self, monkeypatch):
        def mock_instr(_):
            return instruments.instrument_db['FEI-Quanta200-ESEM-633137_n']

        monkeypatch.setattr(nexusLIMS.extractors,
                            "_get_instr", mock_instr)

        meta, thumb_fname = parse_metadata(fname=files['QUANTA_TIF'][0])
        os.remove(thumb_fname)
        os.remove(thumb_fname.replace('thumb.png', 'json'))

    def test_parse_metadata_tif_other_instr(self, monkeypatch):
        def mock_instr(_):
            return None

        monkeypatch.setattr(nexusLIMS.extractors,
                            "_get_instr", mock_instr)

        meta, thumb_fname = parse_metadata(fname=files['QUANTA_TIF'][0])
        os.remove(thumb_fname)
        os.remove(thumb_fname.replace('thumb.png', 'json'))

    def test_parse_metadata_ser(self, ):
        TEST_FILE = os.path.join(
            os.path.dirname(__file__), "files",
            "***REMOVED***1_***REMOVED***_14.59.36 Scanning Acquire_dataZeroed_1.ser")
        meta, thumb_fname = parse_metadata(fname=TEST_FILE)
        os.remove(thumb_fname)
        os.remove(thumb_fname.replace('thumb.png', 'json'))

    def test_parse_metadata_no_dataset_type(self, monkeypatch):
        monkeypatch.setitem(nexusLIMS.extractors.extension_reader_map,
                            'tif', lambda x: {'nx_meta': {'key': 'val'}})

        meta, thumb_fname = parse_metadata(fname=files['QUANTA_TIF'][0])
        assert meta['nx_meta']['DatasetType'] == 'Misc'
        assert meta['nx_meta']['Data Type'] == 'Miscellaneous'
        assert meta['nx_meta']['key'] == 'val'

        os.remove(thumb_fname)
        os.remove(thumb_fname.replace('thumb.png', 'json'))

    def test_parse_metadata_bad_ser(self):
        # if we find a bad ser that can't be read, we should get minimal
        # metadata and a placeholder thumbnail image
        from nexusLIMS.extractors import PLACEHOLDER_PREVIEW
        import filecmp
        TEST_FILE = os.path.join(
            os.path.dirname(__file__), "files",
            "***REMOVED***13_unreadable_ser_1.ser")
        meta, thumb_fname = parse_metadata(fname=TEST_FILE)
        # assert that preview is same as our placeholder image (should be)
        assert filecmp.cmp(PLACEHOLDER_PREVIEW, thumb_fname, shallow=False)
        assert meta['nx_meta']['Data Type'] == 'Unknown'
        assert meta['nx_meta']['DatasetType'] == 'Misc'
        assert '***REMOVED***13_unreadable_ser.emi' in meta['nx_meta']['emi ' \
                                                                   'Filename']
        assert 'The .ser file could not be opened' in meta['nx_meta'][
            'Extractor Warning']

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
            return instruments.instrument_db['FEI-Titan-TEM-635816_n']

        monkeypatch.setattr(digital_micrograph,
                            "_get_instr", mock_instr)

        metadata = digital_micrograph.get_dm3_metadata(
            files['LIST_SIGNAL'][0])

        assert metadata['nx_meta']['Data Type'] == 'STEM_Imaging'
        assert metadata['nx_meta']['Imaging Mode'] == 'DIFFRACTION'
        assert metadata['nx_meta']['Microscope'] == 'Titan80-300_D3094'
        assert metadata['nx_meta']['Voltage'] == 300000.0

    def test_642_dm3(self, monkeypatch):
        # monkeypatch so DM extractor thinks this file came from FEI Titan TEM
        def mock_instr(_):
            return instruments.instrument_db['FEI-Titan-TEM-635816_n']

        monkeypatch.setattr(digital_micrograph,
                            "_get_instr", mock_instr)

        meta = digital_micrograph.get_dm3_metadata(files['642_STEM_DIFF'][0])
        assert meta['nx_meta']['Data Type'] == 'STEM_Diffraction'
        assert meta['nx_meta']['Imaging Mode'] == 'DIFFRACTION'
        assert meta['nx_meta']['Microscope'] == 'MSED Titan'
        assert meta['nx_meta']['Voltage'] == 300000.0

        meta = digital_micrograph.get_dm3_metadata(files[
                                                       '642_OPMODE_DIFF'][0])
        assert meta['nx_meta']['Data Type'] == 'TEM_Diffraction'
        assert meta['nx_meta']['Imaging Mode'] == 'DIFFRACTION'
        assert meta['nx_meta']['Microscope'] == 'MSED Titan'
        assert meta['nx_meta']['Voltage'] == 300000.0

        meta = digital_micrograph.get_dm3_metadata(files['642_EELS_PROC_1'][0])
        assert meta['nx_meta']['Data Type'] == 'STEM_EELS'
        assert meta['nx_meta']['Imaging Mode'] == 'DIFFRACTION'
        assert meta['nx_meta']['Microscope'] == 'MSED Titan'
        assert meta['nx_meta']['Voltage'] == 300000.0
        assert meta['nx_meta']['EELS']['Processing Steps'] == \
            'Aligned parent SI By Peak, Extracted from SI'
        assert meta['nx_meta']['EELS']['Spectrometer Aperture label'] == '2mm'

        meta = digital_micrograph.get_dm3_metadata(
            files['642_EELS_SI_DRIFT'][0])
        assert meta['nx_meta']['Data Type'] == 'EELS_Spectrum_Imaging'
        assert meta['nx_meta']['Imaging Mode'] == 'DIFFRACTION'
        assert meta['nx_meta']['Microscope'] == 'MSED Titan'
        assert meta['nx_meta']['Voltage'] == 300000.0
        assert meta['nx_meta']['EELS']['Convergence semi-angle (mrad)'] == 10.0
        assert meta['nx_meta']['EELS']['Spectrometer Aperture label'] == '2mm'
        assert meta['nx_meta']['Spectrum Imaging']['Artefact Correction'] == \
            'Spatial drift correction every 100 seconds'
        assert meta['nx_meta']['Spectrum Imaging']['Pixel time (s)'] == 0.05

        meta = digital_micrograph.get_dm3_metadata(files['642_TECNAI_MAG'][0])
        assert meta['nx_meta']['Data Type'] == 'TEM_Imaging'
        assert meta['nx_meta']['Imaging Mode'] == 'IMAGING'
        assert meta['nx_meta']['Microscope'] == 'MSED Titan'
        assert meta['nx_meta']['Indicated Magnification'] == 8100.0
        assert meta['nx_meta']['Tecnai User'] == 'MBK1'
        assert meta['nx_meta']['Tecnai Mode'] == 'TEM uP SA Zoom Image'

    def test_643_dm3(self, monkeypatch):
        # monkeypatch so DM extractor thinks this file came from FEI Titan STEM
        def mock_instr(_):
            return instruments.instrument_db['FEI-Titan-STEM-630901_n']

        monkeypatch.setattr(digital_micrograph,
                            "_get_instr", mock_instr)
        meta = digital_micrograph.get_dm3_metadata(files['643_EFTEM_DIFF'][0])
        assert meta['nx_meta']['Data Type'] == 'TEM_EFTEM_Diffraction'
        assert meta['nx_meta']['DatasetType'] == 'Diffraction'
        assert meta['nx_meta']['Imaging Mode'] == 'EFTEM DIFFRACTION'
        assert meta['nx_meta']['Microscope'] == 'Titan80-300_D3094'
        assert meta['nx_meta']['STEM Camera Length'] == 5.0
        assert meta['nx_meta']['EELS']['Spectrometer Aperture label'] == '5 mm'

        meta = digital_micrograph.get_dm3_metadata(files['643_EELS_SI'][0])
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
            files['643_EELS_PROC_INT_BG'][0])
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
            files['643_EELS_PROC_THICK'][0])
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

        meta = digital_micrograph.get_dm3_metadata(files['643_EDS_SI'][0])
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

        meta = digital_micrograph.get_dm3_metadata(
            files['643_EELS_SI_DRIFT'][0])
        assert meta['nx_meta']['Data Type'] == 'EELS_Spectrum_Imaging'
        assert meta['nx_meta']['DatasetType'] == 'SpectrumImage'
        assert meta['nx_meta']['Analytic Signal'] == 'EELS'
        assert meta['nx_meta']['Analytic Format'] == 'Spectrum image'
        assert meta['nx_meta']['Analytic Acquisition Mode'] == 'Parallel ' \
                                                               'dispersive'
        assert meta['nx_meta']['STEM Camera Length'] == 100.0
        assert meta['nx_meta']['EELS']['Exposure (s)'] == 0.5
        assert meta['nx_meta']['EELS']['Number of frames'] == 1
        assert meta['nx_meta']['Spectrum Imaging']['Acquisition Duration (s)'] \
            == 2173
        assert meta['nx_meta']['Spectrum Imaging']['Artefact Correction'] == \
            'Spatial drift correction every 1 row'
        assert meta['nx_meta']['Spectrum Imaging']['Scan Mode'] == '2D Array'

        meta = digital_micrograph.get_dm3_metadata(files['643_STEM_STACK'][0])
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
            return instruments.instrument_db['JEOL-JEM3010-TEM-565989_n']

        monkeypatch.setattr(digital_micrograph,
                            "_get_instr", mock_instr)

        meta = digital_micrograph.get_dm3_metadata(files['JEOL3010_DIFF'][0])
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
    QUANTA_TEST_FILE = files['QUANTA_TIF'][0]
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
        metadata = get_quanta_metadata(self.QUANTA_BAD_MDATA)
        assert metadata['nx_meta']['Extractor Warnings'] == \
               'Did not find expected FEI tags. Could not read metadata'
        assert metadata['nx_meta']['Data Type'] == 'Unknown'
        assert metadata['nx_meta']['Data Type'] == 'Unknown'

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


class TestSerEmiExtractor:
    def test_642_stem_image_1(self):
        TEST_FILE = os.path.join(
            os.path.dirname(__file__), "files",
            "***REMOVED***1_***REMOVED***_14.59.36 Scanning Acquire_dataZeroed_1.ser")
        meta = fei_emi.get_ser_metadata(TEST_FILE)
        assert meta['nx_meta']['DatasetType'] == 'Image'
        assert meta['nx_meta']['Data Type'] == 'STEM_Imaging'
        assert meta['nx_meta']['Data Dimensions'] == '(1024, 1024)'
        assert meta['nx_meta']['Creation Time'] == \
            dt(year=2018, month=11, day=13, hour=15, minute=00,
               second=31).isoformat()
        assert meta['nx_meta']['Magnification (x)'] == 28500
        assert meta['nx_meta']['Mode'] == 'STEM nP SA Zoom Diffraction'
        assert meta['nx_meta']['Stage Position'] == {
            'A (°)': -0.84,
            'B (°)': 0.0,
            'X (μm)': -195.777,
            'Y (μm)': -132.325,
            'Z (μm)': 128.364}
        assert meta['nx_meta']['User'] == 'MBK1'
        assert meta['nx_meta']['C2 Lens (%)'] == 22.133

    def test_642_stem_image_2(self):
        TEST_FILE = os.path.join(
            os.path.dirname(__file__), "files",
            "***REMOVED***1_***REMOVED***_14.59.36 Scanning Acquire_dataZeroed_2.ser")
        meta = fei_emi.get_ser_metadata(TEST_FILE)
        assert meta['nx_meta']['Defocus (μm)'] == 0
        assert meta['nx_meta']['Data Dimensions'] == '(1024, 1024)'
        assert meta['nx_meta']['Gun Lens'] == 6
        assert meta['nx_meta']['Gun Type'] == 'FEG'
        assert meta['nx_meta']['C2 Aperture (μm)'] == 50.0
        assert meta['nx_meta']['DatasetType'] == 'Image'
        assert meta['nx_meta']['Data Type'] == 'STEM_Imaging'
        assert meta['nx_meta']['Creation Time'] == \
            dt(year=2018, month=11, day=13, hour=15, minute=00,
               second=31).isoformat()

    def test_642_single_stem_image(self):
        TEST_FILE = os.path.join(
            os.path.dirname(__file__), "files",
            "***REMOVED***2_***REMOVED***_HAADF_dataZeroed_1.ser")
        meta = fei_emi.get_ser_metadata(TEST_FILE)
        assert meta['nx_meta']['DatasetType'] == 'Image'
        assert meta['nx_meta']['Data Type'] == 'STEM_Imaging'
        assert meta['nx_meta']['Data Dimensions'] == '(1024, 1024)'
        assert meta['nx_meta']['Creation Time'] == \
            dt(year=2019, month=6, day=28, hour=15, minute=53,
               second=31).isoformat()
        assert meta['nx_meta']['C1 Aperture (μm)'] == 2000
        assert meta['nx_meta']['Mode'] == 'STEM nP SA Zoom Image'
        assert meta['nx_meta']['Stage Position'] == {
            'A (°)': 0.0,
            'B (°)': 0.0,
            'X (μm)': -31.415,
            'Y (μm)': 42.773,
            'Z (μm)': -10.576}
        assert meta['nx_meta']['SA Aperture'] == 'retracted'
        assert meta['ObjectInfo']['Uuid'] == \
            'cb7d82b8-5405-42fc-aa71-7680721a6e32'

    def test_642_eds_spectrum_image(self):
        TEST_FILE = os.path.join(
            os.path.dirname(__file__), "files",
            "***REMOVED***3_***REMOVED***_13.50.23 Spectrum image_dataZeroed_1.ser")
        meta = fei_emi.get_ser_metadata(TEST_FILE)
        assert meta['nx_meta']['DatasetType'] == 'SpectrumImage'
        assert meta['nx_meta']['Data Type'] == 'STEM_EDS_Spectrum_Imaging'
        assert meta['nx_meta']['Data Dimensions'] == '(9, 10, 3993)'
        assert meta['nx_meta']['Creation Time'] == \
            dt(year=2019, month=7, day=17, hour=13, minute=50,
               second=22).isoformat()
        assert meta['nx_meta']['Microscope Accelerating Voltage (V)'] == 300000
        assert meta['nx_meta']['Camera Length (m)'] == 0.195
        assert meta['nx_meta']['Stage Position'] == {
            'A (°)': 9.57,
            'B (°)': 0.0,
            'X (μm)': -505.273,
            'Y (μm)': -317.978,
            'Z (μm)': 15.525}
        assert meta['nx_meta']['Spot Size'] == 6
        assert meta['nx_meta']['Magnification (x)'] == 14000.0

    def test_642_eds_line_scan_1(self):
        TEST_FILE = os.path.join(
            os.path.dirname(__file__), "files",
            "***REMOVED***4_***REMOVED***_15.42.57 Spectrum profile_dataZeroed_1.ser")
        meta = fei_emi.get_ser_metadata(TEST_FILE)
        assert meta['nx_meta']['DatasetType'] == 'SpectrumImage'
        assert meta['nx_meta']['Data Type'] == 'STEM_EDS_Spectrum_Imaging'
        assert meta['nx_meta']['Data Dimensions'] == '(100, 3993)'
        assert meta['nx_meta']['Creation Time'] == \
            dt(year=2019, month=11, day=1, hour=15, minute=42,
               second=16).isoformat()
        assert meta['nx_meta']['Dwell Time Path (s)'] == 6e-6
        assert meta['nx_meta']['Defocus (μm)'] == -1.12
        assert meta['nx_meta']['Stage Position'] == {
            'A (°)': 7.32,
            'B (°)': -3.57,
            'X (μm)': 20.528,
            'Y (μm)': 243.295,
            'Z (μm)': 45.491}
        assert meta['nx_meta']['STEM Rotation Correction (°)'] == -12.3
        assert meta['nx_meta']['Frame Time (s)'] == 1.88744

    def test_642_eds_line_scan_2(self):
        TEST_FILE = os.path.join(
            os.path.dirname(__file__), "files",
            "***REMOVED***4_***REMOVED***_15.43.21 Spectrum positions_dataZeroed_1.ser")
        meta = fei_emi.get_ser_metadata(TEST_FILE)
        assert meta['nx_meta']['DatasetType'] == 'SpectrumImage'
        assert meta['nx_meta']['Data Type'] == 'STEM_EDS_Spectrum_Imaging'
        assert meta['nx_meta']['Data Dimensions'] == '(6, 3993)'
        assert meta['nx_meta']['Creation Time'] == \
            dt(year=2019, month=7, day=17, hour=15, minute=43,
               second=21).isoformat()
        assert meta['nx_meta']['Diffraction Lens (%)'] == 34.922
        assert meta['nx_meta']['Defocus (μm)'] == -0.145
        assert meta['nx_meta']['Stage Position'] == {
            'A (°)': 9.57,
            'B (°)': 0,
            'X (μm)': -565.778,
            'Y (μm)': -321.364,
            'Z (μm)': 17.126}
        assert meta['nx_meta']['Manufacturer'] == 'FEI (ISAS)'
        assert meta['nx_meta']['Microscope'] == 'Microscope Titan 300 ' \
                                                'kV D3188 SuperTwin'

    def test_642_eds_spectrum(self):
        TEST_FILE = os.path.join(
            os.path.dirname(__file__), "files",
            "***REMOVED***5_***REMOVED***_16.02.37 EDX Acquire_dataZeroed_1.ser")
        meta = fei_emi.get_ser_metadata(TEST_FILE)
        assert meta['nx_meta']['DatasetType'] == 'Spectrum'
        assert meta['nx_meta']['Data Type'] == 'TEM_EDS_Spectrum'
        assert meta['nx_meta']['Data Dimensions'] == '(3993,)'
        assert meta['nx_meta']['Creation Time'] == \
            dt(year=2019, month=12, day=11, hour=16, minute=2,
               second=38).isoformat()
        assert meta['nx_meta']['Energy Resolution (eV)'] == 10
        assert meta['nx_meta']['Integration Time (s)'] == 25
        assert meta['nx_meta']['Stage Position'] == {
            'A (°)': 0,
            'B (°)': 0.11,
            'X (μm)': -259.807,
            'Y (μm)': 18.101,
            'Z (μm)': 7.06}
        assert meta['nx_meta']['Manufacturer'] == 'EDAX'
        assert meta['nx_meta']['Emission (μA)'] == 145.0

    def test_642_diffraction(self):
        TEST_FILE = os.path.join(
            os.path.dirname(__file__), "files",
            "***REMOVED***6_igor_saed2_1a(-28p57_-1p4)_dl300_dataZeroed_1.ser")
        meta = fei_emi.get_ser_metadata(TEST_FILE)
        assert meta['nx_meta']['DatasetType'] == 'Diffraction'
        assert meta['nx_meta']['Data Type'] == 'TEM_Diffraction'
        assert meta['nx_meta']['Data Dimensions'] == '(2048, 2048)'
        assert meta['nx_meta']['Creation Time'] == \
            dt(year=2018, month=10, day=30, hour=17, minute=1,
               second=3).isoformat()
        assert meta['nx_meta']['Camera Name Path'] == 'BM-UltraScan'
        assert meta['nx_meta']['Camera Length (m)'] == 0.3
        assert meta['nx_meta']['Stage Position'] == {
            'A (°)': -28.59,
            'B (°)': 0.0,
            'X (μm)': -91.527,
            'Y (μm)': -100.11,
            'Z (μm)': 210.133}
        assert meta['nx_meta']['Manufacturer'] == 'FEI'
        assert meta['nx_meta']['Extraction Voltage (V)'] == 4400

    def test_642_image_stack_1(self):
        TEST_FILE = os.path.join(
            os.path.dirname(__file__), "files",
            "***REMOVED***7_igor_haadfseries1_dataZeroed_1.ser")
        meta = fei_emi.get_ser_metadata(TEST_FILE)
        assert meta['nx_meta']['DatasetType'] == 'Image'
        assert meta['nx_meta']['Data Type'] == 'STEM_Imaging'
        assert meta['nx_meta']['Data Dimensions'] == '(20, 2048, 2048)'
        assert meta['nx_meta']['Creation Time'] == \
            dt(year=2019, month=3, day=28, hour=21, minute=14,
               second=16).isoformat()
        assert meta['nx_meta']['Dwell Time Path (s)'] == 0.000002
        assert meta['nx_meta']['C2 Aperture (μm)'] == 50.0
        assert meta['nx_meta']['Stage Position'] == {
            'A (°)': 2.9,
            'B (°)': 0.0,
            'X (μm)': -207.808,
            'Y (μm)': 111.327,
            'Z (μm)': 74.297}
        assert meta['nx_meta']['Gun Type'] == 'FEG'
        assert meta['nx_meta']['Diffraction Lens (%)'] == 38.91

    def test_642_image_stack_2(self):
        TEST_FILE = os.path.join(
            os.path.dirname(__file__), "files",
            "***REMOVED***7_igor_haadfseries3_dataZeroed_1.ser")
        meta = fei_emi.get_ser_metadata(TEST_FILE)
        assert meta['nx_meta']['DatasetType'] == 'Image'
        assert meta['nx_meta']['Data Type'] == 'STEM_Imaging'
        assert meta['nx_meta']['Data Dimensions'] == '(20, 2048, 2048)'
        assert meta['nx_meta']['Creation Time'] == \
            dt(year=2019, month=3, day=28, hour=22, minute=41,
               second=0).isoformat()
        assert meta['nx_meta']['Frame Time (s)'] == 10
        assert meta['nx_meta']['C1 Aperture (μm)'] == 2000
        assert meta['nx_meta']['Stage Position'] == {
            'A (°)': 4.53,
            'B (°)': 0.0,
            'X (μm)': -207.438,
            'Y (μm)': 109.996,
            'Z (μm)': 76.932}
        assert meta['nx_meta']['Gun Lens'] == 5
        assert meta['nx_meta']['Tecnai Filter']['Mode'] is None

    def test_642_diffraction_stack(self):
        TEST_FILE = os.path.join(
            os.path.dirname(__file__), "files",
            "***REMOVED***7_v***REMOVED***_2***REMOVED*** "
            "D245mm SAED 7b0 fx27k TEM6g 4s_dataZeroed_1.ser")
        meta = fei_emi.get_ser_metadata(TEST_FILE)
        assert meta['nx_meta']['DatasetType'] == 'Diffraction'
        assert meta['nx_meta']['Data Type'] == 'TEM_Diffraction'
        assert meta['nx_meta']['Data Dimensions'] == '(33, 1024, 1024)'
        assert meta['nx_meta']['Creation Time'] == \
            dt(year=2018, month=12, day=13, hour=13, minute=33,
               second=47).isoformat()
        assert meta['nx_meta']['C2 Lens (%)'] == 43.465
        assert meta['nx_meta']['C2 Aperture (μm)'] == 100
        assert meta['nx_meta']['Stage Position'] == {
            'A (°)': 1.86,
            'B (°)': 0.0,
            'X (μm)': -179.33,
            'Y (μm)': -31.279,
            'Z (μm)': -158.512}
        assert meta['nx_meta']['OBJ Aperture'] == 'retracted'
        assert meta['nx_meta']['Mode'] == 'TEM uP SA Zoom Diffraction'

    def test_642_emi_list_image_spectrum_1(self):
        TEST_FILE_1 = os.path.join(
            os.path.dirname(__file__), "files",
            "***REMOVED***8_igor_eds1_dataZeroed_1.ser")
        TEST_FILE_2 = os.path.join(
            os.path.dirname(__file__), "files",
            "***REMOVED***8_igor_eds1_dataZeroed_2.ser")
        meta_1 = fei_emi.get_ser_metadata(TEST_FILE_1)
        meta_2 = fei_emi.get_ser_metadata(TEST_FILE_2)

        assert meta_1['nx_meta']['DatasetType'] == 'Image'
        assert meta_1['nx_meta']['Data Type'] == 'STEM_Imaging'
        assert meta_1['nx_meta']['Data Dimensions'] == '(2048, 2048)'
        assert meta_1['nx_meta']['High Tension (kV)'] == 300
        assert meta_1['nx_meta']['Gun Lens'] == 6
        assert meta_1['nx_meta']['Stage Position'] == {
            'A (°)': 9.21,
            'B (°)': 0.0,
            'X (μm)': -202.298,
            'Y (μm)': -229.609,
            'Z (μm)': 92.45}

        assert meta_2['nx_meta']['DatasetType'] == 'Spectrum'
        assert meta_2['nx_meta']['Data Type'] == 'STEM_EDS_Spectrum'
        assert meta_2['nx_meta']['Data Dimensions'] == '(3993,)'
        assert meta_2['nx_meta']['Beam Position (μm)'] == '(-0.99656, 0.74289)'
        assert meta_2['nx_meta']['Diffraction Lens (%)'] == 37.347
        assert meta_2['nx_meta']['Objective Lens (%)'] == 87.987
        assert meta_2['nx_meta']['Stage Position'] == {
            'A (°)': 9.21,
            'B (°)': 0.0,
            'X (μm)': -202.296,
            'Y (μm)': -229.616,
            'Z (μm)': 92.45}

    def test_642_emi_list_image_spectrum_2(self):
        TEST_FILE_1 = os.path.join(
            os.path.dirname(__file__), "files",
            "***REMOVED***8_igor_eds2a_dataZeroed_1.ser")
        TEST_FILE_2 = os.path.join(
            os.path.dirname(__file__), "files",
            "***REMOVED***8_igor_eds2a_dataZeroed_2.ser")
        TEST_FILE_3 = os.path.join(
            os.path.dirname(__file__), "files",
            "***REMOVED***8_igor_eds2a_dataZeroed_3.ser")
        TEST_FILE_4 = os.path.join(
            os.path.dirname(__file__), "files",
            "***REMOVED***8_igor_eds2a_dataZeroed_4.ser")
        TEST_FILE_5 = os.path.join(
            os.path.dirname(__file__), "files",
            "***REMOVED***8_igor_eds2a_dataZeroed_5.ser")
        meta_1 = fei_emi.get_ser_metadata(TEST_FILE_1)
        meta_2 = fei_emi.get_ser_metadata(TEST_FILE_2)
        meta_3 = fei_emi.get_ser_metadata(TEST_FILE_3)
        meta_4 = fei_emi.get_ser_metadata(TEST_FILE_4)
        meta_5 = fei_emi.get_ser_metadata(TEST_FILE_5)

        assert meta_1['nx_meta']['DatasetType'] == 'Image'
        assert meta_1['nx_meta']['Data Type'] == 'STEM_Imaging'
        assert meta_1['nx_meta']['Data Dimensions'] == '(512, 512)'
        assert meta_1['nx_meta']['Creation Time'] == \
            dt(year=2019, month=6, day=13, hour=19, minute=52,
               second=6).isoformat()
        assert meta_1['nx_meta']['Diffraction Lens (%)'] == 37.347
        assert meta_1['nx_meta']['Spot Size'] == 7
        assert meta_1['nx_meta']['Manufacturer'] == 'FEI (ISAS)'
        assert meta_1['nx_meta']['Stage Position'] == {
            'A (°)': 9.21,
            'B (°)': 0.0,
            'X (μm)': -202.296,
            'Y (μm)': -229.618,
            'Z (μm)': 92.45}

        # the remaining spectra don't have metadata, only a UUID
        for m, u in \
            zip([meta_2, meta_3, meta_4, meta_5],
                ['5bb5972e-276a-40c3-87c5-eb9ef3f4cb12',
                 '36c60afe-f7e4-4356-b351-f329347fb464',
                 '76e6b908-f988-48cb-adab-2c64fd6de24e',
                 '9eabdd9d-6cb7-41c3-b234-bb44670a14f6']):
            assert m['nx_meta']['DatasetType'] == 'Spectrum'
            # this might be incorrect, but we have no way of determining
            assert m['nx_meta']['Data Type'] == 'TEM_EDS_Spectrum'
            assert m['nx_meta']['Data Dimensions'] == '(3993,)'
            assert m['ObjectInfo']['Uuid'] == u
            assert 'Manufacturer' not in m['nx_meta']

    def test_642_emi_list_haadf_diff_stack(self):
        TEST_FILE_1 = os.path.join(
            os.path.dirname(__file__), "files",
            "***REMOVED***9_v***REMOVED***_92118 ***REMOVED*** x10k TEM10d2 "
            "large w  f saed10_dataZeroed_1.ser")
        TEST_FILE_2 = os.path.join(
            os.path.dirname(__file__), "files",
            "***REMOVED***9_v***REMOVED***_92118 ***REMOVED*** x10k TEM10d2 "
            "large w  f saed10_dataZeroed_2.ser")
        meta_1 = fei_emi.get_ser_metadata(TEST_FILE_1)
        meta_2 = fei_emi.get_ser_metadata(TEST_FILE_2)

        assert meta_1['nx_meta']['DatasetType'] == 'Diffraction'
        assert meta_1['nx_meta']['Data Type'] == 'TEM_Diffraction'
        assert meta_1['nx_meta']['Data Dimensions'] == '(77, 1024, 1024)'
        assert meta_1['nx_meta']['Creation Time'] == \
            dt(year=2018, month=9, day=21, hour=14, minute=17,
               second=25).isoformat()
        assert meta_1['nx_meta']['Binning'] == 2
        assert meta_1['nx_meta']['Tecnai Filter']['Mode'] == 'Spectroscopy'
        assert meta_1['nx_meta']['Tecnai Filter']['Selected Aperture'] == '3mm'
        assert meta_1['nx_meta']['Image Shift X (μm)'] == 0.003
        assert meta_1['nx_meta']['Mode'] == 'TEM uP SA Zoom Diffraction'
        assert meta_1['nx_meta']['Stage Position'] == {
            'A (°)': 0,
            'B (°)': 0,
            'X (μm)': -135.782,
            'Y (μm)': 637.285,
            'Z (μm)': 77.505}

        assert meta_2['nx_meta']['DatasetType'] == 'Image'
        assert meta_2['nx_meta']['Data Type'] == 'TEM_Imaging'
        assert meta_2['nx_meta']['Data Dimensions'] == '(4, 1024, 1024)'
        assert meta_2['nx_meta']['Creation Time'] == \
            dt(year=2018, month=9, day=21, hour=14, minute=25,
               second=11).isoformat()
        assert meta_2['nx_meta']['Dwell Time Path (s)'] == 0.8
        assert meta_2['nx_meta']['Emission (μA)'] == 135.0
        assert meta_2['nx_meta']['Magnification (x)'] == 10000
        assert meta_2['nx_meta']['Image Shift X (μm)'] == 0.003
        assert meta_2['nx_meta']['Mode'] == 'TEM uP SA Zoom Image'
        assert meta_2['nx_meta']['Stage Position'] == {
            'A (°)': 0,
            'B (°)': 0,
            'X (μm)': -135.787,
            'Y (μm)': 637.281,
            'Z (μm)': 77.505}

    def test_642_emi_list_four_images(self):
        TEST_FILE_1 = os.path.join(
            os.path.dirname(__file__), "files",
            "***REMOVED***10_v***REMOVED***_***REMOVED*** Si membUS100_C35Q33 "
            "l2266CL130mmx160kSTEM lw15corner_dataZeroed_1.ser")
        TEST_FILE_2 = os.path.join(
            os.path.dirname(__file__), "files",
            "***REMOVED***10_v***REMOVED***_***REMOVED*** Si membUS100_C35Q33 "
            "l2266CL130mmx160kSTEM lw15corner_dataZeroed_2.ser")
        TEST_FILE_3 = os.path.join(
            os.path.dirname(__file__), "files",
            "***REMOVED***10_v***REMOVED***_***REMOVED*** Si membUS100_C35Q33 "
            "l2266CL130mmx160kSTEM lw15corner_dataZeroed_3.ser")
        TEST_FILE_4 = os.path.join(
            os.path.dirname(__file__), "files",
            "***REMOVED***10_v***REMOVED***_***REMOVED*** Si membUS100_C35Q33 "
            "l2266CL130mmx160kSTEM lw15corner_dataZeroed_4.ser")

        for m in [fei_emi.get_ser_metadata(f) for f in [TEST_FILE_1,
                                                        TEST_FILE_2,
                                                        TEST_FILE_3,
                                                        TEST_FILE_4]]:
            assert m['nx_meta']['DatasetType'] == 'Image'
            assert m['nx_meta']['Data Type'] == 'STEM_Imaging'
            assert m['nx_meta']['Data Dimensions'] == '(2048, 2048)'

            assert m['nx_meta']['Creation Time'] == \
                dt(year=2018, month=11, day=14, hour=17, minute=9,
                   second=55).isoformat()
            assert m['nx_meta']['Frame Time (s)'] == 30.199
            assert m['nx_meta']['Tecnai Filter']['Selected Dispersion ('
                                                 'eV/Channel)'] == 0.1
            assert m['nx_meta']['Microscope'] == 'Microscope Titan 300 kV ' \
                                                 'D3188 SuperTwin'
            assert m['nx_meta']['Mode'] == 'STEM nP SA Zoom Diffraction'
            assert m['nx_meta']['Spot Size'] == 8
            assert m['nx_meta']['Gun Lens'] == 5
            assert m['nx_meta']['Gun Type'] == 'FEG'
            assert m['nx_meta']['Stage Position'] == {
                'A (°)': 0,
                'B (°)': 0,
                'X (μm)': -116.939,
                'Y (μm)': -65.107,
                'Z (μm)': 79.938}

    def test_643_stem_image(self):
        TEST_FILE = os.path.join(
            os.path.dirname(__file__), "files",
            "643Titan_1_a***REMOVED***_09.45.36 Scanning Acquire_dataZeroed_1.ser")
        meta = fei_emi.get_ser_metadata(TEST_FILE)
        assert meta['nx_meta']['DatasetType'] == 'Image'
        assert meta['nx_meta']['Data Type'] == 'STEM_Imaging'
        assert meta['nx_meta']['Data Dimensions'] == '(1024, 1024)'
        assert meta['nx_meta']['Creation Time'] == \
            dt(year=2011, month=11, day=16, hour=9, minute=46,
               second=13).isoformat()
        assert meta['nx_meta']['C2 Lens (%)'] == 8.967
        assert meta['nx_meta']['C2 Aperture (μm)'] == 40
        assert meta['nx_meta']['Stage Position'] == {
            'A (°)': 0,
            'B (°)': 0,
            'X (μm)': 46.293,
            'Y (μm)': -14.017,
            'Z (μm)': -127.155}
        assert meta['nx_meta']['STEM Rotation Correction (°)'] == 12.4
        assert meta['nx_meta']['User'] == 'SUPERVISOR'
        assert meta['nx_meta']['Microscope'] == 'Microscope Titan 300 kV ' \
                                                'D3094 SuperTwin'

    def test_643_eds_and_eels_spectrum_image(self):
        TEST_FILE_EDS = os.path.join(
            os.path.dirname(__file__), "files",
            "643Titan_2_a***REMOVED***_16.10.32 Spectrum image_dataZeroed_1.ser")
        TEST_FILE_EELS = os.path.join(
            os.path.dirname(__file__), "files",
            "643Titan_2_a***REMOVED***_16.10.32 Spectrum image_dataZeroed_2.ser")
        meta_1 = fei_emi.get_ser_metadata(TEST_FILE_EDS)
        meta_2 = fei_emi.get_ser_metadata(TEST_FILE_EELS)

        assert meta_1['nx_meta']['DatasetType'] == 'SpectrumImage'
        assert meta_1['nx_meta']['Data Type'] == 'STEM_EDS_Spectrum_Imaging'
        assert meta_1['nx_meta']['Data Dimensions'] == '(40, 70, 4000)'
        assert meta_1['nx_meta']['Creation Time'] == \
            dt(year=2011, month=11, day=16, hour=16, minute=8,
               second=54).isoformat()
        assert meta_1['nx_meta']['Frame Time (s)'] == 10
        assert meta_1['nx_meta']['Emission (μA)'] == 237.3
        assert meta_1['nx_meta']['Tecnai Filter']['Selected '
                                                  'Aperture'] == '2.5 mm'
        assert meta_1['nx_meta']['Tecnai Filter']['Slit '
                                                  'State'] == 'Retracted'

        assert meta_2['nx_meta']['DatasetType'] == 'SpectrumImage'
        assert meta_2['nx_meta']['Data Type'] == 'STEM_EELS_Spectrum_Imaging'
        assert meta_2['nx_meta']['Data Dimensions'] == '(40, 70, 2048)'
        assert meta_2['nx_meta']['Creation Time'] == \
            dt(year=2011, month=11, day=16, hour=16, minute=32,
               second=27).isoformat()
        assert meta_2['nx_meta']['Energy Resolution (eV)'] == 10
        assert meta_2['nx_meta']['Integration Time (s)'] == 0.5
        assert meta_2['nx_meta']['Extraction Voltage (V)'] == 4500
        assert meta_2['nx_meta']['Camera Length (m)'] == 0.06
        assert meta_2['nx_meta']['C2 Lens (%)'] == 8.967
        assert meta_2['nx_meta']['C3 Aperture (μm)'] == 1000

    def test_643_image_stack(self):
        TEST_FILE = os.path.join(
            os.path.dirname(__file__), "files",
            "643Titan_3_a***REMOVED***_17.08.14 Scanning Acquire_Before Full 360 "
            "Dataset_2_dataZeroed_1.ser")
        meta = fei_emi.get_ser_metadata(TEST_FILE)
        assert meta['nx_meta']['DatasetType'] == 'Image'
        assert meta['nx_meta']['Data Type'] == 'STEM_Imaging'
        assert meta['nx_meta']['Data Dimensions'] == '(5, 1024, 1024)'
        assert meta['nx_meta']['Creation Time'] == \
            dt(year=2012, month=1, day=31, hour=13, minute=43,
               second=40).isoformat()
        assert meta['nx_meta']['Frame Time (s)'] == 2.0
        assert meta['nx_meta']['C1 Aperture (μm)'] == 2000
        assert meta['nx_meta']['C2 Lens (%)'] == 14.99
        assert meta['nx_meta']['Defocus (μm)'] == -2.593
        assert meta['nx_meta']['Microscope'] == 'Microscope Titan 300 kV ' \
                                                'D3094 SuperTwin'
        assert meta['nx_meta']['Mode'] == 'STEM nP SA Zoom Diffraction'
        assert meta['nx_meta']['Magnification (x)'] == 80000

    def test_643_image_stack_2_newer(self):
        TEST_FILE = os.path.join(
            os.path.dirname(__file__), "files",
            "643Titan_4_a***REMOVED***_005_STEM_80kXemi_dataZeroed_1.ser")
        meta = fei_emi.get_ser_metadata(TEST_FILE)
        assert meta['nx_meta']['DatasetType'] == 'Image'
        assert meta['nx_meta']['Data Type'] == 'STEM_Imaging'
        assert meta['nx_meta']['Data Dimensions'] == '(2, 512, 512)'
        assert meta['nx_meta']['Creation Time'] == \
            dt(year=2020, month=3, day=11, hour=16, minute=33,
               second=38).isoformat()
        assert meta['nx_meta']['Frame Time (s)'] == 6.34179
        assert meta['nx_meta']['Dwell Time Path (s)'] == 0.000001
        assert meta['nx_meta']['C2 Aperture (μm)'] == 10
        assert meta['nx_meta']['C3 Lens (%)'] == -37.122
        assert meta['nx_meta']['Defocus (μm)'] == -0.889
        assert meta['nx_meta']['Microscope'] == 'Microscope Titan 300 kV ' \
                                                'D3094 SuperTwin'
        assert meta['nx_meta']['Mode'] == 'STEM nP SA Zoom Diffraction'
        assert meta['nx_meta']['Magnification (x)'] == 80000
        assert meta['nx_meta']['STEM Rotation (°)'] == -90.0

    def test_no_emi_error(self, caplog):
        TEST_FILE = os.path.join(
            os.path.dirname(__file__), "files",
            "***REMOVED***12_no_accompanying_emi_dataZeroed_1.ser")
        meta = fei_emi.get_ser_metadata(TEST_FILE)

        assert 'Extractor Warning' in meta['nx_meta']
        assert 'NexusLIMS could not find a corresponding .emi metadata ' + \
               'file for this .ser file' in meta['nx_meta']['Extractor Warning']
        assert 'NexusLIMS could not find a corresponding .emi metadata ' + \
               'file for this .ser file' in caplog.text
        assert meta['nx_meta']['emi Filename'] is None

    def test_unreadable_ser(self, caplog):
        # if the ser is unreadable, neither the emi or the ser can be read,
        # so we will get the bare minimum of metadata back from the parser
        TEST_FILE = os.path.join(
            os.path.dirname(__file__), "files",
            "***REMOVED***13_unreadable_ser_1.ser")
        meta = fei_emi.get_ser_metadata(TEST_FILE)
        assert 'nx_meta' in meta
        assert meta['nx_meta']['Data Type'] == 'Unknown'
        assert meta['nx_meta']['DatasetType'] == 'Misc'
        assert 'Creation Time' in meta['nx_meta']
        assert '***REMOVED***13_unreadable_ser.emi' in \
               meta['nx_meta']['emi Filename']
        assert 'The .emi metadata file associated with this .ser file could ' \
               'not be opened by NexusLIMS.' in caplog.text
        assert 'The .ser file could not be opened (perhaps file is ' \
               'corrupted?)' in caplog.text

    @staticmethod
    def _helper_test(caplog):
        TEST_FILE = os.path.join(
            os.path.dirname(__file__), "files",
            "***REMOVED***14_unreadable_emi_1.ser")
        meta = fei_emi.get_ser_metadata(TEST_FILE)
        assert 'nx_meta' in meta
        assert 'ser_header_parameters' in meta
        assert 'The .emi metadata file associated with this .ser file could ' \
               'not be opened by NexusLIMS' in caplog.text
        assert 'The .emi metadata file associated with this .ser file could ' \
               'not be opened by NexusLIMS' in meta['nx_meta']['Extractor '
                                                               'Warning']
        assert meta['nx_meta']['Data Dimensions'] == '(1024, 1024)'
        assert meta['nx_meta']['DatasetType'] == 'Image'
        return meta

    def test_unreadable_emi(self, caplog):
        # if emi is unreadable, we should still get basic metadata from the ser
        meta = TestSerEmiExtractor._helper_test(caplog)
        assert meta['nx_meta']['Data Type'] == 'TEM_Imaging'

    def test_instr_mode_parsing_with_unreadable_emi_tem(self, monkeypatch,
                                                        caplog):
        # if emi is unreadable, we should get imaging mode based off
        # instrument, but testing directory doesn't allow proper handling of
        # this, so monkeypatch get_instr_from_filepath
        def mock_get_instr(filename):
            return instruments.instrument_db['FEI-Titan-TEM-635816_n']
        monkeypatch.setattr(fei_emi, '_get_instr', mock_get_instr)
        meta = TestSerEmiExtractor._helper_test(caplog)
        assert meta['nx_meta']['Data Type'] == 'TEM_Imaging'

    def test_instr_mode_parsing_with_unreadable_emi_stem(self, monkeypatch,
                                                         caplog):
        # if emi is unreadable, we should get imaging mode based off
        # instrument, but testing directory doesn't allow proper handling of
        # this, so monkeypatch get_instr_from_filepath
        def mock_get_instr(filename):
            return instruments.instrument_db['FEI-Titan-STEM-630901_n']
        monkeypatch.setattr(fei_emi, '_get_instr', mock_get_instr)
        meta = TestSerEmiExtractor._helper_test(caplog)
        assert meta['nx_meta']['Data Type'] == 'STEM_Imaging'
