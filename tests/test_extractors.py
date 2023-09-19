# pylint: disable=C0302,C0116
# ruff: noqa: D102, PLR2004

"""Tests the extraction of metadata and generation of preview images from data files."""

import base64
import filecmp
import json
import logging
import os
from datetime import datetime as dt
from pathlib import Path

import hyperspy.api as hs
import numpy as np
import pytest

import nexusLIMS
from nexusLIMS import instruments
from nexusLIMS.extractors import (
    PLACEHOLDER_PREVIEW,
    digital_micrograph,
    fei_emi,
    flatten_dict,
    parse_metadata,
    thumbnail_generator,
)
from nexusLIMS.extractors.basic_metadata import get_basic_metadata
from nexusLIMS.extractors.edax import get_msa_metadata, get_spc_metadata
from nexusLIMS.extractors.quanta_tif import get_quanta_metadata
from nexusLIMS.extractors.thumbnail_generator import (
    down_sample_image,
    image_to_square_thumbnail,
    sig_to_thumbnail,
    text_to_thumbnail,
)
from nexusLIMS.extractors.utils import _try_decimal, _zero_data_in_dm3
from nexusLIMS.version import __version__

from .utils import assert_images_equal, get_full_file_path


class TestThumbnailGenerator:  # pylint: disable=too-many-public-methods
    """Tests the generation of thumbnail preview images."""

    @pytest.fixture()
    def output_path(self):
        output = Path("output.png")
        yield output
        output.unlink()

    @classmethod
    def setup_class(cls):
        cls.s = hs.datasets.example_signals.EDS_TEM_Spectrum()
        cls.oned_s = hs.stack(
            [cls.s * i for i in np.arange(0.1, 1, 0.3)],
            new_axis_name="x",
        )
        cls.twod_s = hs.stack(
            [cls.oned_s * i for i in np.arange(0.1, 1, 0.3)],
            new_axis_name="y",
        )
        cls.threed_s = hs.stack(
            [cls.twod_s * i for i in np.arange(0.1, 1, 0.3)],
            new_axis_name="z",
        )

    @pytest.mark.mpl_image_compare(style="default")
    def test_0d_spectrum(self, output_path):
        self.s.metadata.General.title = "Dummy spectrum"
        return sig_to_thumbnail(self.s, output_path)

    @pytest.mark.mpl_image_compare(style="default")
    def test_1d_spectrum_image(self, output_path):
        self.oned_s.metadata.General.title = "Dummy line scan"
        return sig_to_thumbnail(self.oned_s, output_path)

    @pytest.mark.mpl_image_compare(style="default")
    def test_2d_spectrum_image(self, output_path):
        self.twod_s.metadata.General.title = "Dummy 2D spectrum image"
        return sig_to_thumbnail(self.twod_s, output_path)

    @pytest.mark.mpl_image_compare(style="default")
    def test_2d_spectrum_image_nav_under_9(self, output_path):
        self.twod_s.metadata.General.title = "Dummy 2D spectrum image"
        return sig_to_thumbnail(
            self.twod_s.inav[:2, :2],
            output_path,
        )

    @pytest.mark.mpl_image_compare(style="default")
    def test_3d_spectrum_image(self, output_path):
        self.threed_s.metadata.General.title = "Dummy 3D spectrum image"
        return sig_to_thumbnail(self.threed_s, output_path)

    @pytest.mark.mpl_image_compare(style="default")
    def test_single_image(self, eftem_diff_643, output_path):
        return sig_to_thumbnail(hs.load(eftem_diff_643), output_path)

    @pytest.mark.mpl_image_compare(style="default")
    def test_single_not_dm3_image(self, eftem_diff_643, output_path):
        s = hs.load(eftem_diff_643)
        s.metadata.General.original_filename = "not dm3"
        return sig_to_thumbnail(s, output_path)

    @pytest.mark.mpl_image_compare(style="default")
    def test_image_stack(self, stem_stack_643, output_path):
        return sig_to_thumbnail(hs.load(stem_stack_643), output_path)

    @pytest.mark.mpl_image_compare(style="default")
    def test_4d_stem_type(self, four_d_stem, output_path):
        return sig_to_thumbnail(hs.load(four_d_stem), output_path)

    @pytest.mark.mpl_image_compare(style="default")
    def test_4d_stem_type_1(self, four_d_stem, output_path):
        # nav size >= 4 but < 9
        return sig_to_thumbnail(hs.load(four_d_stem).inav[:2, :3], output_path)

    @pytest.mark.mpl_image_compare(style="default")
    def test_4d_stem_type_2(self, four_d_stem, output_path):
        # nav size = 1
        return sig_to_thumbnail(hs.load(four_d_stem).inav[:1, :2], output_path)

    @pytest.mark.mpl_image_compare(style="default", tolerance=20)
    def test_complex_image(self, fft, output_path):
        return sig_to_thumbnail(hs.load(fft), output_path)

    @pytest.mark.mpl_image_compare(style="default")
    def test_higher_dimensional_signal(self, output_path):
        dict0 = {
            "size": 10,
            "name": "nav axis 3",
            "units": "nm",
            "scale": 2,
            "offset": 0,
        }
        dict1 = {
            "size": 10,
            "name": "nav axis 2",
            "units": "pm",
            "scale": 200,
            "offset": 0,
        }
        dict2 = {
            "size": 10,
            "name": "nav axis 1",
            "units": "mm",
            "scale": 0.02,
            "offset": 0,
        }
        dict3 = {
            "size": 10,
            "name": "sig axis 3",
            "units": "eV",
            "scale": 100,
            "offset": 0,
        }
        dict4 = {
            "size": 10,
            "name": "sig axis 2",
            "units": "Hz",
            "scale": 0.2121,
            "offset": 0,
        }
        dict5 = {
            "size": 10,
            "name": "sig axis 1",
            "units": "radians",
            "scale": 0.314,
            "offset": 0,
        }
        s = hs.signals.BaseSignal(
            np.zeros((10, 10, 10, 10, 10, 10), dtype=int),
            axes=[dict0, dict1, dict2, dict3, dict4, dict5],
        )
        s = s.transpose(navigation_axes=3)
        s.metadata.General.title = "Signal with higher-order dimensionality"
        return sig_to_thumbnail(s, output_path)

    @pytest.mark.mpl_image_compare(style="default")
    def test_survey_image(self, survey_643, output_path):
        return sig_to_thumbnail(hs.load(survey_643), output_path)

    def test_annotation_error(self, monkeypatch, survey_643):
        def monkey_get_annotation(_1, _2):
            msg = "Mocked error for testing"
            raise ValueError(msg)

        monkeypatch.setattr(
            thumbnail_generator,
            "_get_markers_dict",
            monkey_get_annotation,
        )
        thumbnail_generator.add_annotation_markers(hs.load(survey_643))

    @pytest.mark.mpl_image_compare(style="default")
    def test_annotations(self, annotations_643, output_path):
        return sig_to_thumbnail(hs.load(annotations_643), output_path)

    def test_downsample_image_errors(self):
        with pytest.raises(
            ValueError,
            match="One of output_size or factor must be provided",
        ):
            # providing neither output size and factor should raise an error
            down_sample_image("", "")

        with pytest.raises(
            ValueError,
            match="Only one of output_size or factor should be provided",
        ):
            # providing both output size and factor should raise an error
            down_sample_image("", "", output_size=(20, 20), factor=5)

    @pytest.mark.mpl_image_compare(style="default")
    def test_downsample_image_factor(self, quanta_test_file, output_path):
        return down_sample_image(quanta_test_file[0], output_path, factor=3)

    @pytest.mark.mpl_image_compare(style="default")
    def test_downsample_image_32_bit(self, quanta_32bit_test_file, output_path):
        return down_sample_image(quanta_32bit_test_file[0], output_path, factor=2)

    @pytest.mark.mpl_image_compare(style="default")
    def test_downsample_image_output_size(self, quanta_test_file, output_path):
        return down_sample_image(
            quanta_test_file[0],
            output_path,
            output_size=(500, 500),
        )

    @pytest.mark.mpl_image_compare(style="default")
    def test_text_paragraph_to_thumbnail(self, text_paragraph_test_file, output_path):
        return text_to_thumbnail(text_paragraph_test_file, output_path)

    @pytest.mark.mpl_image_compare(style="default")
    def test_text_data_to_thumbnail(self, text_data_test_file, output_path):
        return text_to_thumbnail(text_data_test_file, output_path)

    @pytest.mark.mpl_image_compare(style="default")
    def test_text_ansi_to_thumbnail(self, text_ansi_test_file, output_path):
        return text_to_thumbnail(text_ansi_test_file, output_path)

    def test_png_to_thumbnail(self, output_path, image_thumb_source_png):
        baseline_thumb_png = (
            Path(__file__).parent / "files" / "figs" / "test_image_thumb_png.png"
        )
        image_to_square_thumbnail(image_thumb_source_png, output_path, 500)
        assert_images_equal(baseline_thumb_png, output_path)

    def test_bmp_to_thumbnail(self, output_path, basic_image_file):
        baseline_thumb_bmp = (
            Path(__file__).parent / "files" / "figs" / "test_image_thumb_bmp.png"
        )
        image_to_square_thumbnail(basic_image_file, output_path, 500)
        assert_images_equal(baseline_thumb_bmp, output_path)

    def test_gif_to_thumbnail(self, output_path, image_thumb_source_gif):
        baseline_thumb_gif = (
            Path(__file__).parent / "files" / "figs" / "test_image_thumb_gif.png"
        )
        image_to_square_thumbnail(image_thumb_source_gif, output_path, 500)
        assert_images_equal(baseline_thumb_gif, output_path)

    def test_jpg_to_thumbnail(self, output_path, image_thumb_source_jpg):
        baseline_thumb_jpg = (
            Path(__file__).parent / "files" / "figs" / "test_image_thumb_jpg.png"
        )
        image_to_square_thumbnail(image_thumb_source_jpg, output_path, 500)
        assert_images_equal(baseline_thumb_jpg, output_path)

    def test_tif_to_thumbnail(self, output_path, image_thumb_source_tif):
        baseline_thumb_tif = (
            Path(__file__).parent / "files" / "figs" / "test_image_thumb_tif.png"
        )
        image_to_square_thumbnail(image_thumb_source_tif, output_path, 500)
        assert_images_equal(baseline_thumb_tif, output_path)

    def test_assert_image_fail(self, image_thumb_source_tif, quanta_test_file):
        """Sanity check that for images that are not the same."""
        with pytest.raises(AssertionError):
            assert_images_equal(image_thumb_source_tif, quanta_test_file[0])


class TestExtractorModule:
    """Tests the methods from __init__.py of nexusLIMS.extractors."""

    @classmethod
    def remove_thumb_and_json(cls, fname):
        fname.unlink()
        Path(str(fname).replace("thumb.png", "json")).unlink()

    def test_parse_metadata_642_titan(self, parse_meta_642_titan):
        meta, thumb_fname = parse_metadata(fname=parse_meta_642_titan[0])
        assert meta["nx_meta"]["Acquisition Device"] == "BM-UltraScan"
        assert meta["nx_meta"]["Actual Magnification"] == 17677.0
        assert meta["nx_meta"]["Cs(mm)"] == 1.2
        assert meta["nx_meta"]["Data Dimensions"] == "(2048, 2048)"
        assert meta["nx_meta"]["Data Type"] == "TEM_Imaging"
        assert meta["nx_meta"]["DatasetType"] == "Image"
        assert len(meta["nx_meta"]["warnings"]) == 0
        assert (
            meta["nx_meta"]["NexusLIMS Extraction"]["Module"]
            == "nexusLIMS.extractors.digital_micrograph"
        )
        assert meta["nx_meta"]["NexusLIMS Extraction"]["Version"] == __version__

        self.remove_thumb_and_json(thumb_fname)

    def test_parse_metadata_list_signal(self, list_signal):
        meta, thumb_fname = parse_metadata(fname=list_signal[0])
        assert meta["nx_meta"]["Acquisition Device"] == "DigiScan"
        assert meta["nx_meta"]["STEM Camera Length"] == 77.0
        assert meta["nx_meta"]["Cs(mm)"] == 1.0
        assert meta["nx_meta"]["Data Dimensions"] == "(512, 512)"
        assert meta["nx_meta"]["Data Type"] == "STEM_Imaging"
        assert meta["nx_meta"]["DatasetType"] == "Image"
        assert len(meta["nx_meta"]["warnings"]) == 0
        assert (
            meta["nx_meta"]["NexusLIMS Extraction"]["Module"]
            == "nexusLIMS.extractors.digital_micrograph"
        )
        assert meta["nx_meta"]["NexusLIMS Extraction"]["Version"] == __version__

        self.remove_thumb_and_json(thumb_fname)

    def test_parse_metadata_overwrite_false(self, caplog, list_signal):
        thumb_fname = Path(str(list_signal[0]) + ".thumb.png")
        # create the thumbnail file so we can't overwrite
        with thumb_fname.open(mode="a", encoding="utf-8") as _:
            pass
        nexusLIMS.extractors.logger.setLevel(logging.INFO)
        _, thumb_fname = parse_metadata(fname=list_signal[0], overwrite=False)
        assert "Preview already exists" in caplog.text
        self.remove_thumb_and_json(thumb_fname)

    def test_parse_metadata_quanta(self, monkeypatch, quanta_test_file):
        def mock_instr(_):
            return instruments.instrument_db["FEI-Quanta200-ESEM-633137_n"]

        monkeypatch.setattr(
            nexusLIMS.extractors.utils,
            "get_instr_from_filepath",
            mock_instr,
        )
        monkeypatch.setattr(
            nexusLIMS.extractors,
            "get_instr_from_filepath",
            mock_instr,
        )

        _, thumb_fname = parse_metadata(fname=quanta_test_file[0])
        self.remove_thumb_and_json(thumb_fname)

    def test_parse_metadata_tif_other_instr(self, monkeypatch, quanta_test_file):
        def mock_instr(_):
            return None

        monkeypatch.setattr(
            nexusLIMS.extractors.utils,
            "get_instr_from_filepath",
            mock_instr,
        )

        meta, thumb_fname = parse_metadata(fname=quanta_test_file[0])
        assert (
            meta["nx_meta"]["NexusLIMS Extraction"]["Module"]
            == "nexusLIMS.extractors.quanta_tif"
        )
        assert meta["nx_meta"]["NexusLIMS Extraction"]["Version"] == __version__
        self.remove_thumb_and_json(thumb_fname)

    def test_parse_metadata_edax_spc(self):
        test_file = Path(__file__).parent / "files" / "647_leo_edax_test.spc"
        _, thumb_fname = parse_metadata(fname=test_file)

        # test encoding of np.void metadata filler values
        json_path = Path(str(thumb_fname).replace("thumb.png", "json"))
        with json_path.open("r", encoding="utf-8") as _file:
            json_meta = json.load(_file)

        filler_val = json_meta["original_metadata"]["filler3"]
        assert filler_val == "PQoOQgAAgD8="

        expected_void = np.void(b"\x3D\x0A\x0E\x42\x00\x00\x80\x3F")
        assert np.void(base64.b64decode(filler_val)) == expected_void

        self.remove_thumb_and_json(thumb_fname)

    def test_parse_metadata_edax_msa(self):
        test_file = Path(__file__).parent / "files" / "647_leo_edax_test.msa"
        _, thumb_fname = parse_metadata(fname=test_file)
        self.remove_thumb_and_json(thumb_fname)

    def test_parse_metadata_ser(self, fei_ser_files):
        test_file = [
            i
            for i in fei_ser_files
            if "14.59.36 Scanning Acquire_dataZeroed_1.ser" in str(i)
        ][0]

        meta, thumb_fname = parse_metadata(fname=test_file)
        assert (
            meta["nx_meta"]["NexusLIMS Extraction"]["Module"]
            == "nexusLIMS.extractors.fei_emi"
        )
        assert meta["nx_meta"]["NexusLIMS Extraction"]["Version"] == __version__
        self.remove_thumb_and_json(thumb_fname)

    def test_parse_metadata_no_dataset_type(self, monkeypatch, quanta_test_file):
        monkeypatch.setitem(
            nexusLIMS.extractors.extension_reader_map,
            "tif",
            lambda _x: {"nx_meta": {"key": "val"}},
        )

        meta, thumb_fname = parse_metadata(fname=quanta_test_file[0])
        assert meta["nx_meta"]["DatasetType"] == "Misc"
        assert meta["nx_meta"]["Data Type"] == "Miscellaneous"
        assert meta["nx_meta"]["key"] == "val"
        assert meta["nx_meta"]["NexusLIMS Extraction"]["Version"] == __version__

        self.remove_thumb_and_json(thumb_fname)

    def test_parse_metadata_bad_ser(self, fei_ser_files):
        # if we find a bad ser that can't be read, we should get minimal
        # metadata and a placeholder thumbnail image
        test_file = [
            i for i in fei_ser_files if "642Titan_13_unreadable_ser_1.ser" in str(i)
        ][0]

        meta, thumb_fname = parse_metadata(fname=test_file)
        # assert that preview is same as our placeholder image (should be)
        assert filecmp.cmp(PLACEHOLDER_PREVIEW, thumb_fname, shallow=False)
        assert meta["nx_meta"]["Data Type"] == "Unknown"
        assert meta["nx_meta"]["DatasetType"] == "Misc"
        assert (
            meta["nx_meta"]["NexusLIMS Extraction"]["Module"]
            == "nexusLIMS.extractors.fei_emi"
        )
        assert meta["nx_meta"]["NexusLIMS Extraction"]["Version"] == __version__
        assert "642Titan_13_unreadable_ser.emi" in meta["nx_meta"]["emi Filename"]
        assert (
            "The .ser file could not be opened" in meta["nx_meta"]["Extractor Warning"]
        )

        self.remove_thumb_and_json(thumb_fname)

    def test_parse_metadata_basic_extractor(self, basic_txt_file_no_extension):
        meta, thumb_fname = parse_metadata(fname=basic_txt_file_no_extension)

        assert thumb_fname is None
        assert meta["nx_meta"]["Data Type"] == "Unknown"
        assert meta["nx_meta"]["DatasetType"] == "Unknown"
        assert (
            meta["nx_meta"]["NexusLIMS Extraction"]["Module"]
            == "nexusLIMS.extractors.basic_metadata"
        )
        assert meta["nx_meta"]["NexusLIMS Extraction"]["Version"] == __version__

        # remove json file
        Path(
            str(basic_txt_file_no_extension).replace(
                os.environ["mmfnexus_path"],
                os.environ["nexusLIMS_path"],
            )
            + ".json",
        ).unlink()

    def test_parse_metadata_with_image_preview(self, basic_image_file):
        meta, thumb_fname = parse_metadata(fname=basic_image_file)

        assert thumb_fname.is_file()
        assert meta["nx_meta"]["Data Type"] == "Unknown"
        assert meta["nx_meta"]["DatasetType"] == "Unknown"
        assert (
            meta["nx_meta"]["NexusLIMS Extraction"]["Module"]
            == "nexusLIMS.extractors.basic_metadata"
        )
        assert meta["nx_meta"]["NexusLIMS Extraction"]["Version"] == __version__

        self.remove_thumb_and_json(thumb_fname)

    def test_parse_metadata_with_text_preview(self, basic_txt_file):
        meta, thumb_fname = parse_metadata(fname=basic_txt_file)

        assert thumb_fname.is_file()
        assert meta["nx_meta"]["Data Type"] == "Unknown"
        assert meta["nx_meta"]["DatasetType"] == "Unknown"
        assert (
            meta["nx_meta"]["NexusLIMS Extraction"]["Module"]
            == "nexusLIMS.extractors.basic_metadata"
        )
        assert meta["nx_meta"]["NexusLIMS Extraction"]["Version"] == __version__

        self.remove_thumb_and_json(thumb_fname)

    def test_no_thumb_for_unreadable_image(self, unreadable_image_file):
        meta, thumb_fname = parse_metadata(fname=unreadable_image_file)

        assert thumb_fname is None
        assert meta["nx_meta"]["Data Type"] == "Unknown"
        assert meta["nx_meta"]["DatasetType"] == "Unknown"
        assert (
            meta["nx_meta"]["NexusLIMS Extraction"]["Module"]
            == "nexusLIMS.extractors.basic_metadata"
        )
        assert meta["nx_meta"]["NexusLIMS Extraction"]["Version"] == __version__

    def test_no_thumb_for_binary_text_file(self, binary_text_file):
        meta, thumb_fname = parse_metadata(fname=binary_text_file)

        assert thumb_fname is None
        assert meta["nx_meta"]["Data Type"] == "Unknown"
        assert meta["nx_meta"]["DatasetType"] == "Unknown"
        assert (
            meta["nx_meta"]["NexusLIMS Extraction"]["Module"]
            == "nexusLIMS.extractors.basic_metadata"
        )
        assert meta["nx_meta"]["NexusLIMS Extraction"]["Version"] == __version__

    def test_flatten_dict(self):
        dict_to_flatten = {
            "level1.1": "level1.1v",
            "level1.2": {"level2.1": "level2.1v"},
        }

        flattened = flatten_dict(dict_to_flatten)
        assert flattened == {"level1.1": "level1.1v", "level1.2 level2.1": "level2.1v"}


@pytest.fixture(name="_titan_tem_db")
def _fixture_titan_tem_db(monkeypatch):
    """Monkeypatch so DM extractor thinks this file came from FEI Titan TEM."""
    monkeypatch.setattr(
        "nexusLIMS.extractors.digital_micrograph.get_instr_from_filepath",
        lambda _x: instruments.instrument_db["FEI-Titan-TEM-635816_n"],
    )


@pytest.fixture(name="_titan_643_tem_db")
def _fixture_titan_643_tem_db(monkeypatch):
    """Monkeypatch so DM extractor thinks this file came from FEI Titan STEM."""
    monkeypatch.setattr(
        "nexusLIMS.extractors.digital_micrograph.get_instr_from_filepath",
        lambda _x: instruments.instrument_db["FEI-Titan-STEM-630901_n"],
    )


class TestDigitalMicrographExtractor:
    """Tests nexusLIMS.extractors.digital_migrograph."""

    def test_corrupted_file(self, corrupted_file):
        assert digital_micrograph.get_dm3_metadata(corrupted_file) is None

    @pytest.mark.usefixtures("_titan_tem_db")
    def test_dm3_list_file(self, list_signal):
        metadata = digital_micrograph.get_dm3_metadata(list_signal[0])

        assert metadata["nx_meta"]["Data Type"] == "STEM_Imaging"
        assert metadata["nx_meta"]["Imaging Mode"] == "DIFFRACTION"
        assert metadata["nx_meta"]["Microscope"] == "Titan80-300_D3094"
        assert metadata["nx_meta"]["Voltage"] == 300000.0

    @pytest.mark.usefixtures("_titan_tem_db")
    def test_642_dm3_diffraction(
        self,
        stem_diff_642,
        opmode_diff_642,
    ):
        meta = digital_micrograph.get_dm3_metadata(stem_diff_642[0])
        assert meta["nx_meta"]["Data Type"] == "STEM_Diffraction"
        assert meta["nx_meta"]["Imaging Mode"] == "DIFFRACTION"
        assert meta["nx_meta"]["Microscope"] == "MSED Titan"
        assert meta["nx_meta"]["Voltage"] == 300000.0

        meta = digital_micrograph.get_dm3_metadata(opmode_diff_642[0])
        assert meta["nx_meta"]["Data Type"] == "TEM_Diffraction"
        assert meta["nx_meta"]["Imaging Mode"] == "DIFFRACTION"
        assert meta["nx_meta"]["Microscope"] == "MSED Titan"
        assert meta["nx_meta"]["Voltage"] == 300000.0

    @pytest.mark.usefixtures("_titan_tem_db")
    def test_642_dm3_eels(
        self,
        eels_proc_1_642,
        eels_si_drift_642,
        tecnai_mag_642,
    ):
        meta = digital_micrograph.get_dm3_metadata(eels_proc_1_642[0])
        assert meta["nx_meta"]["Data Type"] == "STEM_EELS"
        assert meta["nx_meta"]["Imaging Mode"] == "DIFFRACTION"
        assert meta["nx_meta"]["Microscope"] == "MSED Titan"
        assert meta["nx_meta"]["Voltage"] == 300000.0
        assert (
            meta["nx_meta"]["EELS"]["Processing Steps"]
            == "Aligned parent SI By Peak, Extracted from SI"
        )
        assert meta["nx_meta"]["EELS"]["Spectrometer Aperture label"] == "2mm"

        meta = digital_micrograph.get_dm3_metadata(eels_si_drift_642[0])
        assert meta["nx_meta"]["Data Type"] == "EELS_Spectrum_Imaging"
        assert meta["nx_meta"]["Imaging Mode"] == "DIFFRACTION"
        assert meta["nx_meta"]["Microscope"] == "MSED Titan"
        assert meta["nx_meta"]["Voltage"] == 300000.0
        assert meta["nx_meta"]["EELS"]["Convergence semi-angle (mrad)"] == 10.0
        assert meta["nx_meta"]["EELS"]["Spectrometer Aperture label"] == "2mm"
        assert (
            meta["nx_meta"]["Spectrum Imaging"]["Artefact Correction"]
            == "Spatial drift correction every 100 seconds"
        )
        assert meta["nx_meta"]["Spectrum Imaging"]["Pixel time (s)"] == 0.05

        meta = digital_micrograph.get_dm3_metadata(tecnai_mag_642[0])
        assert meta["nx_meta"]["Data Type"] == "TEM_Imaging"
        assert meta["nx_meta"]["Imaging Mode"] == "IMAGING"
        assert meta["nx_meta"]["Microscope"] == "MSED Titan"
        assert meta["nx_meta"]["Indicated Magnification"] == 8100.0
        assert meta["nx_meta"]["Tecnai User"] == "MBK1"
        assert meta["nx_meta"]["Tecnai Mode"] == "TEM uP SA Zoom Image"

    @pytest.mark.usefixtures("_titan_643_tem_db")
    def test_643_dm3(
        self,
        eftem_diff_643,
        eds_si_643,
        stem_stack_643,
    ):
        meta = digital_micrograph.get_dm3_metadata(eftem_diff_643[0])
        assert meta["nx_meta"]["Data Type"] == "TEM_EFTEM_Diffraction"
        assert meta["nx_meta"]["DatasetType"] == "Diffraction"
        assert meta["nx_meta"]["Imaging Mode"] == "EFTEM DIFFRACTION"
        assert meta["nx_meta"]["Microscope"] == "Titan80-300_D3094"
        assert meta["nx_meta"]["STEM Camera Length"] == 5.0
        assert meta["nx_meta"]["EELS"]["Spectrometer Aperture label"] == "5 mm"

        meta = digital_micrograph.get_dm3_metadata(eds_si_643[0])
        assert meta["nx_meta"]["Data Type"] == "EDS_Spectrum_Imaging"
        assert meta["nx_meta"]["DatasetType"] == "SpectrumImage"
        assert meta["nx_meta"]["Analytic Signal"] == "X-ray"
        assert meta["nx_meta"]["Analytic Format"] == "Spectrum image"
        assert meta["nx_meta"]["STEM Camera Length"] == 77.0
        assert meta["nx_meta"]["EDS"]["Real time (SI Average)"] == pytest.approx(
            0.9696700292825698,
            0.1,
        )
        assert meta["nx_meta"]["EDS"]["Live time (SI Average)"] == pytest.approx(
            0.9696700292825698,
            0.1,
        )
        assert meta["nx_meta"]["Spectrum Imaging"]["Pixel time (s)"] == 1.0
        assert meta["nx_meta"]["Spectrum Imaging"]["Scan Mode"] == "LineScan"
        assert (
            meta["nx_meta"]["Spectrum Imaging"]["Spatial Sampling (Horizontal)"] == 100
        )

        meta = digital_micrograph.get_dm3_metadata(stem_stack_643[0])
        assert meta["nx_meta"]["Data Type"] == "STEM_Imaging"
        assert meta["nx_meta"]["DatasetType"] == "Image"
        assert meta["nx_meta"]["Acquisition Device"] == "DigiScan"
        assert meta["nx_meta"]["Cs(mm)"] == 1.0
        assert meta["nx_meta"]["Data Dimensions"] == "(12, 1024, 1024)"
        assert meta["nx_meta"]["Indicated Magnification"] == 7200000.0
        assert meta["nx_meta"]["STEM Camera Length"] == 100.0

    @pytest.mark.usefixtures("_titan_643_tem_db")
    def test_643_dm3_eels(
        self,
        eels_si_643,
        eels_proc_int_bg_643,
        eels_proc_thick_643,
        eels_si_drift_643,
    ):
        meta = digital_micrograph.get_dm3_metadata(eels_si_643[0])
        assert meta["nx_meta"]["Data Type"] == "EELS_Spectrum_Imaging"
        assert meta["nx_meta"]["DatasetType"] == "SpectrumImage"
        assert meta["nx_meta"]["Imaging Mode"] == "DIFFRACTION"
        assert meta["nx_meta"]["Operation Mode"] == "SCANNING"
        assert meta["nx_meta"]["STEM Camera Length"] == 60.0
        assert meta["nx_meta"]["EELS"]["Convergence semi-angle (mrad)"] == 13.0
        assert meta["nx_meta"]["EELS"]["Exposure (s)"] == 0.5
        assert meta["nx_meta"]["Spectrum Imaging"]["Pixel time (s)"] == 0.5
        assert meta["nx_meta"]["Spectrum Imaging"]["Scan Mode"] == "LineScan"
        assert meta["nx_meta"]["Spectrum Imaging"]["Acquisition Duration (s)"] == 605

        meta = digital_micrograph.get_dm3_metadata(eels_proc_int_bg_643[0])
        assert meta["nx_meta"]["Data Type"] == "STEM_EELS"
        assert meta["nx_meta"]["DatasetType"] == "Spectrum"
        assert meta["nx_meta"]["Analytic Signal"] == "EELS"
        assert meta["nx_meta"]["Analytic Format"] == "Image"
        assert meta["nx_meta"]["STEM Camera Length"] == 48.0
        assert meta["nx_meta"]["EELS"]["Background Removal Model"] == "Power Law"
        assert (
            meta["nx_meta"]["EELS"]["Processing Steps"]
            == "Background Removal, Signal Integration"
        )

        meta = digital_micrograph.get_dm3_metadata(eels_proc_thick_643[0])
        assert meta["nx_meta"]["Data Type"] == "STEM_EELS"
        assert meta["nx_meta"]["DatasetType"] == "Spectrum"
        assert meta["nx_meta"]["Analytic Signal"] == "EELS"
        assert meta["nx_meta"]["Analytic Format"] == "Spectrum"
        assert meta["nx_meta"]["STEM Camera Length"] == 60.0
        assert meta["nx_meta"]["EELS"]["Exposure (s)"] == 0.05
        assert meta["nx_meta"]["EELS"]["Integration time (s)"] == 0.25
        assert (
            meta["nx_meta"]["EELS"]["Processing Steps"]
            == "Calibrated Post-acquisition, Compute Thickness"
        )
        assert meta["nx_meta"]["EELS"]["Thickness (absolute) [nm]"] == pytest.approx(
            85.29884338378906,
            0.1,
        )

        meta = digital_micrograph.get_dm3_metadata(eels_si_drift_643[0])
        assert meta["nx_meta"]["Data Type"] == "EELS_Spectrum_Imaging"
        assert meta["nx_meta"]["DatasetType"] == "SpectrumImage"
        assert meta["nx_meta"]["Analytic Signal"] == "EELS"
        assert meta["nx_meta"]["Analytic Format"] == "Spectrum image"
        assert meta["nx_meta"]["Analytic Acquisition Mode"] == "Parallel dispersive"
        assert meta["nx_meta"]["STEM Camera Length"] == 100.0
        assert meta["nx_meta"]["EELS"]["Exposure (s)"] == 0.5
        assert meta["nx_meta"]["EELS"]["Number of frames"] == 1
        assert meta["nx_meta"]["Spectrum Imaging"]["Acquisition Duration (s)"] == 2173
        assert (
            meta["nx_meta"]["Spectrum Imaging"]["Artefact Correction"]
            == "Spatial drift correction every 1 row"
        )
        assert meta["nx_meta"]["Spectrum Imaging"]["Scan Mode"] == "2D Array"

    def test_jeol3010_dm3(self, monkeypatch, jeol3010_diff):
        # monkeypatch so DM extractor thinks this file came from JEOL 3010
        def mock_instr(_):
            return instruments.instrument_db["JEOL-JEM3010-TEM-565989_n"]

        monkeypatch.setattr(digital_micrograph, "get_instr_from_filepath", mock_instr)

        meta = digital_micrograph.get_dm3_metadata(jeol3010_diff[0])
        assert meta["nx_meta"]["Data Type"] == "TEM_Diffraction"
        assert meta["nx_meta"]["DatasetType"] == "Diffraction"
        assert meta["nx_meta"]["Acquisition Device"] == "Orius "
        assert meta["nx_meta"]["Microscope"] == "JEM3010 UHR"
        assert meta["nx_meta"]["Data Dimensions"] == "(2672, 4008)"
        assert meta["nx_meta"]["Facility"] == "Microscopy Nexus"
        assert meta["nx_meta"]["Camera/Detector Processing"] == "Gain Normalized"

    def test_try_decimal(self):
        # this function should just return the input if it cannot be
        # converted to a decimal
        assert _try_decimal("bogus") == "bogus"

    def test_zero_data(self, stem_image_dm3: Path):
        input_path = stem_image_dm3
        output_path = input_path.parent / (input_path.stem + "_test.dm3")
        fname_1 = _zero_data_in_dm3(input_path, out_filename=None)
        fname_2 = _zero_data_in_dm3(input_path, out_filename=output_path)
        fname_3 = _zero_data_in_dm3(input_path, compress=False)

        # All three files should have been created
        for filename in [fname_1, fname_2, fname_3]:
            assert filename.is_file()

        # The first two files should be compressed so data is smaller
        assert input_path.stat().st_size > fname_1.stat().st_size
        assert input_path.stat().st_size > fname_2.stat().st_size
        # The last should be the same size
        assert input_path.stat().st_size == fname_3.stat().st_size

        meta_in = digital_micrograph.get_dm3_metadata(input_path)
        meta_3 = digital_micrograph.get_dm3_metadata(fname_3)

        # Creation times will be different, so remove that metadata
        del meta_in["nx_meta"]["Creation Time"]
        del meta_3["nx_meta"]["Creation Time"]

        # All other metadata should be equal
        assert meta_in == meta_3

        for filename in [fname_1, fname_2, fname_3]:
            filename.unlink(missing_ok=True)


class TestEDAXSPCExtractor:
    """Tests nexusLIMS.extractors.edax."""

    def test_647_leo_edax_spc(self):
        test_file = Path(__file__).parent / "files" / "647_leo_edax_test.spc"
        meta = get_spc_metadata(test_file)
        assert meta["nx_meta"]["Azimuthal Angle (deg)"] == 0.0
        assert meta["nx_meta"]["Live Time (s)"] == pytest.approx(30.000002)
        assert meta["nx_meta"]["Detector Energy Resolution (eV)"] == pytest.approx(
            125.16211,
        )
        assert meta["nx_meta"]["Elevation Angle (deg)"] == 35.0
        assert meta["nx_meta"]["Channel Size (eV)"] == 5
        assert meta["nx_meta"]["Number of Spectrum Channels"] == 4096
        assert meta["nx_meta"]["Stage Tilt (deg)"] == -1.0
        assert meta["nx_meta"]["Starting Energy (keV)"] == 0.0
        assert meta["nx_meta"]["Ending Energy (keV)"] == pytest.approx(20.475)

    def test_647_leo_edax_msa(self):
        test_file = Path(__file__).parent / "files" / "647_leo_edax_test.msa"
        meta = get_msa_metadata(test_file)
        assert meta["nx_meta"]["Azimuthal Angle (deg)"] == 0.0
        assert meta["nx_meta"]["Amplifier Time (μs)"] == "7.68"
        assert meta["nx_meta"]["Analyzer Type"] == "DPP4"
        assert meta["nx_meta"]["Beam Energy (keV)"] == 10.0
        assert meta["nx_meta"]["Channel Offset"] == 0.0
        assert (
            meta["nx_meta"]["EDAX Comment"]
            == "Converted by EDAX.TeamEDS V4.5.1-RC2.20170623.3 Friday, June 23, 2017"
        )
        assert meta["nx_meta"]["Data Format"] == "XY"
        assert meta["nx_meta"]["EDAX Date"] == "29-Aug-2022"
        assert meta["nx_meta"]["Elevation Angle (deg)"] == 35.0
        assert meta["nx_meta"]["User-Selected Elements"] == "8,27,16"
        assert (
            meta["nx_meta"]["Originating File of MSA Export"]
            == "20220829_CoO220711_withNscan.spc"
        )
        assert meta["nx_meta"]["File Format"] == "EMSA/MAS Spectral Data File"
        assert meta["nx_meta"]["FPGA Version"] == "0"
        assert meta["nx_meta"]["Live Time (s)"] == 30.0
        assert meta["nx_meta"]["Number of Data Columns"] == 1.0
        assert meta["nx_meta"]["Number of Data Points"] == 4096.0
        assert meta["nx_meta"]["Offset"] == 0.0
        assert meta["nx_meta"]["EDAX Owner"] == "EDAX TEAM EDS/block"
        assert meta["nx_meta"]["Real Time (s)"] == 0.0
        assert meta["nx_meta"]["Energy Resolution (eV)"] == "125.2"
        assert meta["nx_meta"]["Signal Type"] == "EDS"
        assert meta["nx_meta"]["Active Layer Thickness (cm)"] == "0.1"
        assert meta["nx_meta"]["Be Window Thickness (cm)"] == 0.0
        assert meta["nx_meta"]["Dead Layer Thickness (cm)"] == 0.03
        assert meta["nx_meta"]["EDAX Time"] == "10:14"
        assert meta["nx_meta"]["EDAX Title"] == ""  # noqa: PLC1901
        assert meta["nx_meta"]["TakeOff Angle (deg)"] == "35.5"
        assert meta["nx_meta"]["Stage Tilt (deg)"] == "-1.0"
        assert meta["nx_meta"]["MSA Format Version"] == "1.0"
        assert meta["nx_meta"]["X Column Label"] == "X-RAY Energy"
        assert meta["nx_meta"]["X Units Per Channel"] == 5.0
        assert meta["nx_meta"]["X Column Units"] == "Energy (EV)"
        assert meta["nx_meta"]["Y Column Label"] == "X-RAY Intensity"
        assert meta["nx_meta"]["Y Column Units"] == "Intensity"


class TestQuantaExtractor:
    """Tests nexusLIMS.extractors.quanta_tif."""

    def test_quanta_extraction(self, quanta_test_file):
        metadata = get_quanta_metadata(quanta_test_file[0])

        # test 'nx_meta' values of interest
        assert metadata["nx_meta"]["Data Type"] == "SEM_Imaging"
        assert metadata["nx_meta"]["DatasetType"] == "Image"
        assert metadata["nx_meta"]["warnings"] == [["Operator"]]

        # test two values from each of the native sections
        assert metadata["User"]["Date"] == "12/18/2017"
        assert metadata["User"]["Time"] == "01:04:14 PM"
        assert metadata["System"]["Type"] == "SEM"
        assert metadata["System"]["Dnumber"] == "D8439"
        assert metadata["Beam"]["HV"] == "30000"
        assert metadata["Beam"]["Spot"] == "3"
        assert metadata["EBeam"]["Source"] == "FEG"
        assert metadata["EBeam"]["FinalLens"] == "S45"
        assert metadata["GIS"]["Number"] == "0"
        assert metadata["EScan"]["InternalScan"]
        assert metadata["EScan"]["Scan"] == "PIA 2.0"
        assert metadata["Stage"]["StageX"] == "0.009654"
        assert metadata["Stage"]["StageY"] == "0.0146008"
        assert metadata["Image"]["ResolutionX"] == "1024"
        assert metadata["Image"]["DigitalContrast"] == "1"
        assert metadata["Vacuum"]["ChPressure"] == "79.8238"
        assert metadata["Vacuum"]["Gas"] == "Wet"
        assert metadata["Specimen"]["Temperature"] == ""  # noqa: PLC1901
        assert metadata["Detectors"]["Number"] == "1"
        assert metadata["Detectors"]["Name"] == "LFD"
        assert metadata["LFD"]["Contrast"] == "62.4088"
        assert metadata["LFD"]["Brightness"] == "45.7511"
        assert metadata["Accessories"]["Number"] == "0"
        assert metadata["PrivateFei"]["BitShift"] == "0"
        assert (
            metadata["PrivateFei"]["DataBarSelected"]
            == "DateTime dwell HV HFW pressure Label MicronBar"
        )
        assert metadata["HiResIllumination"]["BrightFieldIsOn"] == ""  # noqa: PLC1901
        assert metadata["HiResIllumination"]["BrightFieldValue"] == ""  # noqa: PLC1901

    def test_bad_metadata(self, quanta_bad_metadata):
        metadata = get_quanta_metadata(quanta_bad_metadata)
        assert (
            metadata["nx_meta"]["Extractor Warnings"]
            == "Did not find expected FEI tags. Could not read metadata"
        )
        assert metadata["nx_meta"]["Data Type"] == "Unknown"
        assert metadata["nx_meta"]["Data Type"] == "Unknown"

    def test_modded_metadata(self, quanta_just_modded_mdata):
        metadata = get_quanta_metadata(quanta_just_modded_mdata)

        # test 'nx_meta' values of interest
        assert metadata["nx_meta"]["Data Type"] == "SEM_Imaging"
        assert metadata["nx_meta"]["DatasetType"] == "Image"
        assert metadata["nx_meta"]["warnings"] == [["Operator"]]

        assert metadata["nx_meta"]["Scan Rotation (°)"] == 179.9947
        assert metadata["nx_meta"]["Tilt Correction Angle"] == 0.0121551
        assert metadata["nx_meta"]["Specimen Temperature (K)"] == "j"
        assert len(metadata["nx_meta"]["Chamber Pressure (mPa)"]) == 7000

    def test_no_beam_scan_or_system_metadata(self, monkeypatch, quanta_no_beam_meta):
        # monkeypatch so DM extractor thinks this file came from JEOL 3010
        def mock_instr(_):
            return instruments.instrument_db["FEI-Quanta200-ESEM-633137_n"]

        monkeypatch.setattr(
            nexusLIMS.extractors.utils,
            "get_instr_from_filepath",
            mock_instr,
        )

        metadata = get_quanta_metadata(quanta_no_beam_meta[0])
        assert metadata["nx_meta"]["Data Type"] == "SEM_Imaging"
        assert metadata["nx_meta"]["DatasetType"] == "Image"
        assert metadata["nx_meta"]["Creation Time"] == "2023-03-23T18:32:11-04:00"
        assert metadata["nx_meta"]["Instrument ID"] == "FEI-Quanta200-ESEM-633137_n"
        assert metadata["nx_meta"]["Data Dimensions"] == "(1024, 884)"
        assert metadata["nx_meta"]["Frames Integrated"] == 5
        assert metadata["Image"]["ResolutionX"] == "1024"
        assert metadata["Image"]["DigitalContrast"] == "1"


class TestSerEmiExtractor:  # pylint: disable=too-many-public-methods
    """Tests nexusLIMS.extractors.fei_emi."""

    def test_642_stem_image_1(self, fei_ser_files):
        test_file = get_full_file_path(
            "***REMOVED***_14.59.36 Scanning Acquire_dataZeroed_1.ser",
            fei_ser_files,
        )
        meta = fei_emi.get_ser_metadata(test_file)
        assert meta["nx_meta"]["DatasetType"] == "Image"
        assert meta["nx_meta"]["Data Type"] == "STEM_Imaging"
        assert meta["nx_meta"]["Data Dimensions"] == "(1024, 1024)"
        assert (
            meta["nx_meta"]["Creation Time"]
            == dt(2018, 11, 13, 15, 00, 31).isoformat()  # noqa: DTZ001
        )
        assert meta["nx_meta"]["Magnification (x)"] == 28500
        assert meta["nx_meta"]["Mode"] == "STEM nP SA Zoom Diffraction"
        assert meta["nx_meta"]["Stage Position"] == {
            "A (°)": -0.84,
            "B (°)": 0.0,
            "X (μm)": -195.777,
            "Y (μm)": -132.325,
            "Z (μm)": 128.364,
        }
        assert meta["nx_meta"]["User"] == "MBK1"
        assert meta["nx_meta"]["C2 Lens (%)"] == 22.133

    def test_642_stem_image_2(self, fei_ser_files):
        test_file = get_full_file_path(
            "***REMOVED***_14.59.36 Scanning Acquire_dataZeroed_2.ser",
            fei_ser_files,
        )
        meta = fei_emi.get_ser_metadata(test_file)
        assert meta["nx_meta"]["Defocus (μm)"] == 0
        assert meta["nx_meta"]["Data Dimensions"] == "(1024, 1024)"
        assert meta["nx_meta"]["Gun Lens"] == 6
        assert meta["nx_meta"]["Gun Type"] == "FEG"
        assert meta["nx_meta"]["C2 Aperture (μm)"] == 50.0
        assert meta["nx_meta"]["DatasetType"] == "Image"
        assert meta["nx_meta"]["Data Type"] == "STEM_Imaging"
        assert (
            meta["nx_meta"]["Creation Time"]
            == dt(2018, 11, 13, 15, 00, 31).isoformat()  # noqa: DTZ001
        )

    def test_642_single_stem_image(self, fei_ser_files):
        test_file = get_full_file_path(
            "***REMOVED***_HAADF_dataZeroed_1.ser",
            fei_ser_files,
        )
        meta = fei_emi.get_ser_metadata(test_file)
        assert meta["nx_meta"]["DatasetType"] == "Image"
        assert meta["nx_meta"]["Data Type"] == "STEM_Imaging"
        assert meta["nx_meta"]["Data Dimensions"] == "(1024, 1024)"
        assert (
            meta["nx_meta"]["Creation Time"]
            == dt(2019, 6, 28, 15, 53, 31).isoformat()  # noqa: DTZ001
        )
        assert meta["nx_meta"]["C1 Aperture (μm)"] == 2000
        assert meta["nx_meta"]["Mode"] == "STEM nP SA Zoom Image"
        assert meta["nx_meta"]["Stage Position"] == {
            "A (°)": 0.0,
            "B (°)": 0.0,
            "X (μm)": -31.415,
            "Y (μm)": 42.773,
            "Z (μm)": -10.576,
        }
        assert meta["nx_meta"]["SA Aperture"] == "retracted"
        assert meta["ObjectInfo"]["Uuid"] == "cb7d82b8-5405-42fc-aa71-7680721a6e32"

    def test_642_eds_spectrum_image(self, fei_ser_files):
        test_file = get_full_file_path(
            "***REMOVED***_13.50.23 Spectrum image_dataZeroed_1.ser",
            fei_ser_files,
        )
        meta = fei_emi.get_ser_metadata(test_file)
        assert meta["nx_meta"]["DatasetType"] == "SpectrumImage"
        assert meta["nx_meta"]["Data Type"] == "STEM_EDS_Spectrum_Imaging"
        assert meta["nx_meta"]["Data Dimensions"] == "(9, 10, 3993)"
        assert (
            meta["nx_meta"]["Creation Time"]
            == dt(2019, 7, 17, 13, 50, 22).isoformat()  # noqa: DTZ001
        )
        assert meta["nx_meta"]["Microscope Accelerating Voltage (V)"] == 300000
        assert meta["nx_meta"]["Camera Length (m)"] == 0.195
        assert meta["nx_meta"]["Stage Position"] == {
            "A (°)": 9.57,
            "B (°)": 0.0,
            "X (μm)": -505.273,
            "Y (μm)": -317.978,
            "Z (μm)": 15.525,
        }
        assert meta["nx_meta"]["Spot Size"] == 6
        assert meta["nx_meta"]["Magnification (x)"] == 14000.0

    def test_642_eds_line_scan_1(self, fei_ser_files):
        test_file = get_full_file_path(
            "***REMOVED***_15.42.57 Spectrum profile_dataZeroed_1.ser",
            fei_ser_files,
        )
        meta = fei_emi.get_ser_metadata(test_file)
        assert meta["nx_meta"]["DatasetType"] == "SpectrumImage"
        assert meta["nx_meta"]["Data Type"] == "STEM_EDS_Spectrum_Imaging"
        assert meta["nx_meta"]["Data Dimensions"] == "(100, 3993)"
        assert (
            meta["nx_meta"]["Creation Time"]
            == dt(2019, 11, 1, 15, 42, 16).isoformat()  # noqa: DTZ001
        )
        assert meta["nx_meta"]["Dwell Time Path (s)"] == 6e-6
        assert meta["nx_meta"]["Defocus (μm)"] == -1.12
        assert meta["nx_meta"]["Stage Position"] == {
            "A (°)": 7.32,
            "B (°)": -3.57,
            "X (μm)": 20.528,
            "Y (μm)": 243.295,
            "Z (μm)": 45.491,
        }
        assert meta["nx_meta"]["STEM Rotation Correction (°)"] == -12.3
        assert meta["nx_meta"]["Frame Time (s)"] == 1.88744

    def test_642_eds_line_scan_2(self, fei_ser_files):
        test_file = get_full_file_path(
            "***REMOVED***_15.43.21 Spectrum positions_dataZeroed_1.ser",
            fei_ser_files,
        )
        meta = fei_emi.get_ser_metadata(test_file)
        assert meta["nx_meta"]["DatasetType"] == "SpectrumImage"
        assert meta["nx_meta"]["Data Type"] == "STEM_EDS_Spectrum_Imaging"
        assert meta["nx_meta"]["Data Dimensions"] == "(6, 3993)"
        assert (
            meta["nx_meta"]["Creation Time"]
            == dt(2019, 7, 17, 15, 43, 21).isoformat()  # noqa: DTZ001
        )
        assert meta["nx_meta"]["Diffraction Lens (%)"] == 34.922
        assert meta["nx_meta"]["Defocus (μm)"] == -0.145
        assert meta["nx_meta"]["Stage Position"] == {
            "A (°)": 9.57,
            "B (°)": 0,
            "X (μm)": -565.778,
            "Y (μm)": -321.364,
            "Z (μm)": 17.126,
        }
        assert meta["nx_meta"]["Manufacturer"] == "FEI (ISAS)"
        assert (
            meta["nx_meta"]["Microscope"] == "Microscope Titan 300 "
            "kV D3188 SuperTwin"
        )

    def test_642_eds_spectrum(self, fei_ser_files):
        test_file = get_full_file_path(
            "***REMOVED***_16.02.37 EDX Acquire_dataZeroed_1.ser",
            fei_ser_files,
        )
        meta = fei_emi.get_ser_metadata(test_file)
        assert meta["nx_meta"]["DatasetType"] == "Spectrum"
        assert meta["nx_meta"]["Data Type"] == "TEM_EDS_Spectrum"
        assert meta["nx_meta"]["Data Dimensions"] == "(3993,)"
        assert (
            meta["nx_meta"]["Creation Time"]
            == dt(2019, 12, 11, 16, 2, 38).isoformat()  # noqa: DTZ001
        )
        assert meta["nx_meta"]["Energy Resolution (eV)"] == 10
        assert meta["nx_meta"]["Integration Time (s)"] == 25
        assert meta["nx_meta"]["Stage Position"] == {
            "A (°)": 0,
            "B (°)": 0.11,
            "X (μm)": -259.807,
            "Y (μm)": 18.101,
            "Z (μm)": 7.06,
        }
        assert meta["nx_meta"]["Manufacturer"] == "EDAX"
        assert meta["nx_meta"]["Emission (μA)"] == 145.0

    def test_642_diffraction(self, fei_ser_files):
        test_file = get_full_file_path(
            "***REMOVED***_saed2_1a(-28p57_-1p4)_dl300_dataZeroed_1.ser",
            fei_ser_files,
        )
        meta = fei_emi.get_ser_metadata(test_file)
        assert meta["nx_meta"]["DatasetType"] == "Diffraction"
        assert meta["nx_meta"]["Data Type"] == "TEM_Diffraction"
        assert meta["nx_meta"]["Data Dimensions"] == "(2048, 2048)"
        assert (
            meta["nx_meta"]["Creation Time"]
            == dt(2018, 10, 30, 17, 1, 3).isoformat()  # noqa: DTZ001
        )
        assert meta["nx_meta"]["Camera Name Path"] == "BM-UltraScan"
        assert meta["nx_meta"]["Camera Length (m)"] == 0.3
        assert meta["nx_meta"]["Stage Position"] == {
            "A (°)": -28.59,
            "B (°)": 0.0,
            "X (μm)": -91.527,
            "Y (μm)": -100.11,
            "Z (μm)": 210.133,
        }
        assert meta["nx_meta"]["Manufacturer"] == "FEI"
        assert meta["nx_meta"]["Extraction Voltage (V)"] == 4400

    def test_642_image_stack_1(self, fei_ser_files):
        test_file = get_full_file_path(
            "***REMOVED***_haadfseries1_dataZeroed_1.ser",
            fei_ser_files,
        )
        meta = fei_emi.get_ser_metadata(test_file)
        assert meta["nx_meta"]["DatasetType"] == "Image"
        assert meta["nx_meta"]["Data Type"] == "STEM_Imaging"
        assert meta["nx_meta"]["Data Dimensions"] == "(20, 2048, 2048)"
        assert (
            meta["nx_meta"]["Creation Time"]
            == dt(2019, 3, 28, 21, 14, 16).isoformat()  # noqa: DTZ001
        )
        assert meta["nx_meta"]["Dwell Time Path (s)"] == 0.000002
        assert meta["nx_meta"]["C2 Aperture (μm)"] == 50.0
        assert meta["nx_meta"]["Stage Position"] == {
            "A (°)": 2.9,
            "B (°)": 0.0,
            "X (μm)": -207.808,
            "Y (μm)": 111.327,
            "Z (μm)": 74.297,
        }
        assert meta["nx_meta"]["Gun Type"] == "FEG"
        assert meta["nx_meta"]["Diffraction Lens (%)"] == 38.91

    def test_642_image_stack_2(self, fei_ser_files):
        test_file = get_full_file_path(
            "***REMOVED***_haadfseries3_dataZeroed_1.ser",
            fei_ser_files,
        )
        meta = fei_emi.get_ser_metadata(test_file)
        assert meta["nx_meta"]["DatasetType"] == "Image"
        assert meta["nx_meta"]["Data Type"] == "STEM_Imaging"
        assert meta["nx_meta"]["Data Dimensions"] == "(20, 2048, 2048)"
        assert (
            meta["nx_meta"]["Creation Time"]
            == dt(2019, 3, 28, 22, 41, 0).isoformat()  # noqa: DTZ001
        )
        assert meta["nx_meta"]["Frame Time (s)"] == 10
        assert meta["nx_meta"]["C1 Aperture (μm)"] == 2000
        assert meta["nx_meta"]["Stage Position"] == {
            "A (°)": 4.53,
            "B (°)": 0.0,
            "X (μm)": -207.438,
            "Y (μm)": 109.996,
            "Z (μm)": 76.932,
        }
        assert meta["nx_meta"]["Gun Lens"] == 5
        assert meta["nx_meta"]["Tecnai Filter"]["Mode"] is None

    def test_642_diffraction_stack(self, fei_ser_files):
        test_file = get_full_file_path(
            "***REMOVED***_21318 MoTe2 flake2 "
            "D245mm SAED 7b0 fx27k TEM6g 4s_dataZeroed_1.ser",
            fei_ser_files,
        )
        meta = fei_emi.get_ser_metadata(test_file)
        assert meta["nx_meta"]["DatasetType"] == "Diffraction"
        assert meta["nx_meta"]["Data Type"] == "TEM_Diffraction"
        assert meta["nx_meta"]["Data Dimensions"] == "(33, 1024, 1024)"
        assert (
            meta["nx_meta"]["Creation Time"]
            == dt(2018, 12, 13, 13, 33, 47).isoformat()  # noqa: DTZ001
        )
        assert meta["nx_meta"]["C2 Lens (%)"] == 43.465
        assert meta["nx_meta"]["C2 Aperture (μm)"] == 100
        assert meta["nx_meta"]["Stage Position"] == {
            "A (°)": 1.86,
            "B (°)": 0.0,
            "X (μm)": -179.33,
            "Y (μm)": -31.279,
            "Z (μm)": -158.512,
        }
        assert meta["nx_meta"]["OBJ Aperture"] == "retracted"
        assert meta["nx_meta"]["Mode"] == "TEM uP SA Zoom Diffraction"

    def test_642_emi_list_image_spectrum_1(self, fei_ser_files):
        test_file_1 = get_full_file_path(
            "***REMOVED***_eds1_dataZeroed_1.ser",
            fei_ser_files,
        )
        test_file_2 = get_full_file_path(
            "***REMOVED***_eds1_dataZeroed_2.ser",
            fei_ser_files,
        )
        meta_1 = fei_emi.get_ser_metadata(test_file_1)
        meta_2 = fei_emi.get_ser_metadata(test_file_2)

        assert meta_1["nx_meta"]["DatasetType"] == "Image"
        assert meta_1["nx_meta"]["Data Type"] == "STEM_Imaging"
        assert meta_1["nx_meta"]["Data Dimensions"] == "(2048, 2048)"
        assert meta_1["nx_meta"]["High Tension (kV)"] == 300
        assert meta_1["nx_meta"]["Gun Lens"] == 6
        assert meta_1["nx_meta"]["Stage Position"] == {
            "A (°)": 9.21,
            "B (°)": 0.0,
            "X (μm)": -202.298,
            "Y (μm)": -229.609,
            "Z (μm)": 92.45,
        }

        assert meta_2["nx_meta"]["DatasetType"] == "Spectrum"
        assert meta_2["nx_meta"]["Data Type"] == "STEM_EDS_Spectrum"
        assert meta_2["nx_meta"]["Data Dimensions"] == "(3993,)"
        assert meta_2["nx_meta"]["Beam Position (μm)"] == "(-0.99656, 0.74289)"
        assert meta_2["nx_meta"]["Diffraction Lens (%)"] == 37.347
        assert meta_2["nx_meta"]["Objective Lens (%)"] == 87.987
        assert meta_2["nx_meta"]["Stage Position"] == {
            "A (°)": 9.21,
            "B (°)": 0.0,
            "X (μm)": -202.296,
            "Y (μm)": -229.616,
            "Z (μm)": 92.45,
        }

    def test_642_emi_list_image_spectrum_2(self, fei_ser_files):
        test_file_1 = get_full_file_path(
            "***REMOVED***_eds2a_dataZeroed_1.ser",
            fei_ser_files,
        )
        test_file_2 = get_full_file_path(
            "***REMOVED***eds2a_dataZeroed_2.ser",
            fei_ser_files,
        )
        test_file_3 = get_full_file_path(
            "***REMOVED***_eds2a_dataZeroed_3.ser",
            fei_ser_files,
        )
        test_file_4 = get_full_file_path(
            "***REMOVED***_eds2a_dataZeroed_4.ser",
            fei_ser_files,
        )
        test_file_5 = get_full_file_path(
            "***REMOVED***_eds2a_dataZeroed_5.ser",
            fei_ser_files,
        )
        meta_1 = fei_emi.get_ser_metadata(test_file_1)
        meta_2 = fei_emi.get_ser_metadata(test_file_2)
        meta_3 = fei_emi.get_ser_metadata(test_file_3)
        meta_4 = fei_emi.get_ser_metadata(test_file_4)
        meta_5 = fei_emi.get_ser_metadata(test_file_5)

        assert meta_1["nx_meta"]["DatasetType"] == "Image"
        assert meta_1["nx_meta"]["Data Type"] == "STEM_Imaging"
        assert meta_1["nx_meta"]["Data Dimensions"] == "(512, 512)"
        assert (
            meta_1["nx_meta"]["Creation Time"]
            == dt(2019, 6, 13, 19, 52, 6).isoformat()  # noqa: DTZ001
        )
        assert meta_1["nx_meta"]["Diffraction Lens (%)"] == 37.347
        assert meta_1["nx_meta"]["Spot Size"] == 7
        assert meta_1["nx_meta"]["Manufacturer"] == "FEI (ISAS)"
        assert meta_1["nx_meta"]["Stage Position"] == {
            "A (°)": 9.21,
            "B (°)": 0.0,
            "X (μm)": -202.296,
            "Y (μm)": -229.618,
            "Z (μm)": 92.45,
        }

        # the remaining spectra don't have metadata, only a UUID
        for meta, uuid in zip(
            [meta_2, meta_3, meta_4, meta_5],
            [
                "5bb5972e-276a-40c3-87c5-eb9ef3f4cb12",
                "36c60afe-f7e4-4356-b351-f329347fb464",
                "76e6b908-f988-48cb-adab-2c64fd6de24e",
                "9eabdd9d-6cb7-41c3-b234-bb44670a14f6",
            ],
        ):
            assert meta["nx_meta"]["DatasetType"] == "Spectrum"
            # this might be incorrect, but we have no way of determining
            assert meta["nx_meta"]["Data Type"] == "TEM_EDS_Spectrum"
            assert meta["nx_meta"]["Data Dimensions"] == "(3993,)"
            assert meta["ObjectInfo"]["Uuid"] == uuid
            assert "Manufacturer" not in meta["nx_meta"]

    def test_642_emi_list_haadf_diff_stack(self, fei_ser_files):
        test_file_1 = get_full_file_path(
            "***REMOVED***_92118 35nm Si B3 inspection x10k TEM10d2 "
            "large w  f saed10_dataZeroed_1.ser",
            fei_ser_files,
        )
        test_file_2 = get_full_file_path(
            "***REMOVED***_92118 35nm Si B3 inspection x10k TEM10d2 "
            "large w  f saed10_dataZeroed_2.ser",
            fei_ser_files,
        )
        meta_1 = fei_emi.get_ser_metadata(test_file_1)
        meta_2 = fei_emi.get_ser_metadata(test_file_2)

        assert meta_1["nx_meta"]["DatasetType"] == "Diffraction"
        assert meta_1["nx_meta"]["Data Type"] == "TEM_Diffraction"
        assert meta_1["nx_meta"]["Data Dimensions"] == "(77, 1024, 1024)"
        assert (
            meta_1["nx_meta"]["Creation Time"]
            == dt(2018, 9, 21, 14, 17, 25).isoformat()  # noqa: DTZ001
        )
        assert meta_1["nx_meta"]["Binning"] == 2
        assert meta_1["nx_meta"]["Tecnai Filter"]["Mode"] == "Spectroscopy"
        assert meta_1["nx_meta"]["Tecnai Filter"]["Selected Aperture"] == "3mm"
        assert meta_1["nx_meta"]["Image Shift X (μm)"] == 0.003
        assert meta_1["nx_meta"]["Mode"] == "TEM uP SA Zoom Diffraction"
        assert meta_1["nx_meta"]["Stage Position"] == {
            "A (°)": 0,
            "B (°)": 0,
            "X (μm)": -135.782,
            "Y (μm)": 637.285,
            "Z (μm)": 77.505,
        }

        assert meta_2["nx_meta"]["DatasetType"] == "Image"
        assert meta_2["nx_meta"]["Data Type"] == "TEM_Imaging"
        assert meta_2["nx_meta"]["Data Dimensions"] == "(4, 1024, 1024)"
        assert (
            meta_2["nx_meta"]["Creation Time"]
            == dt(2018, 9, 21, 14, 25, 11).isoformat()  # noqa: DTZ001
        )
        assert meta_2["nx_meta"]["Dwell Time Path (s)"] == 0.8
        assert meta_2["nx_meta"]["Emission (μA)"] == 135.0
        assert meta_2["nx_meta"]["Magnification (x)"] == 10000
        assert meta_2["nx_meta"]["Image Shift X (μm)"] == 0.003
        assert meta_2["nx_meta"]["Mode"] == "TEM uP SA Zoom Image"
        assert meta_2["nx_meta"]["Stage Position"] == {
            "A (°)": 0,
            "B (°)": 0,
            "X (μm)": -135.787,
            "Y (μm)": 637.281,
            "Z (μm)": 77.505,
        }

    def test_642_emi_list_four_images(self, fei_ser_files):
        test_file_1 = get_full_file_path(
            "642Titan_10_voleshko_11418 Inspection A1 35nm Si membUS100_C35Q33 "
            "l2266CL130mmx160kSTEM lw15corner_dataZeroed_1.ser",
            fei_ser_files,
        )
        test_file_2 = get_full_file_path(
            "***REMOVED***_11418 Inspection A1 35nm Si membUS100_C35Q33 "
            "l2266CL130mmx160kSTEM lw15corner_dataZeroed_2.ser",
            fei_ser_files,
        )
        test_file_3 = get_full_file_path(
            "***REMOVED***_11418 Inspection A1 35nm Si membUS100_C35Q33 "
            "l2266CL130mmx160kSTEM lw15corner_dataZeroed_3.ser",
            fei_ser_files,
        )
        test_file_4 = get_full_file_path(
            "***REMOVED***_11418 Inspection A1 35nm Si membUS100_C35Q33 "
            "l2266CL130mmx160kSTEM lw15corner_dataZeroed_4.ser",
            fei_ser_files,
        )

        for meta in [
            fei_emi.get_ser_metadata(f)
            for f in [test_file_1, test_file_2, test_file_3, test_file_4]
        ]:
            assert meta["nx_meta"]["DatasetType"] == "Image"
            assert meta["nx_meta"]["Data Type"] == "STEM_Imaging"
            assert meta["nx_meta"]["Data Dimensions"] == "(2048, 2048)"

            assert (
                meta["nx_meta"]["Creation Time"]
                == dt(2018, 11, 14, 17, 9, 55).isoformat()  # noqa: DTZ001
            )
            assert meta["nx_meta"]["Frame Time (s)"] == 30.199
            assert (
                meta["nx_meta"]["Tecnai Filter"]["Selected Dispersion (eV/Channel)"]
                == 0.1
            )
            assert (
                meta["nx_meta"]["Microscope"] == "Microscope Titan 300 kV "
                "D3188 SuperTwin"
            )
            assert meta["nx_meta"]["Mode"] == "STEM nP SA Zoom Diffraction"
            assert meta["nx_meta"]["Spot Size"] == 8
            assert meta["nx_meta"]["Gun Lens"] == 5
            assert meta["nx_meta"]["Gun Type"] == "FEG"
            assert meta["nx_meta"]["Stage Position"] == {
                "A (°)": 0,
                "B (°)": 0,
                "X (μm)": -116.939,
                "Y (μm)": -65.107,
                "Z (μm)": 79.938,
            }

    def test_643_stem_image(self, fei_ser_files):
        test_file = get_full_file_path(
            "***REMOVED***_09.45.36 Scanning Acquire_dataZeroed_1.ser",
            fei_ser_files,
        )
        meta = fei_emi.get_ser_metadata(test_file)
        assert meta["nx_meta"]["DatasetType"] == "Image"
        assert meta["nx_meta"]["Data Type"] == "STEM_Imaging"
        assert meta["nx_meta"]["Data Dimensions"] == "(1024, 1024)"
        assert (
            meta["nx_meta"]["Creation Time"]
            == dt(2011, 11, 16, 9, 46, 13).isoformat()  # noqa: DTZ001
        )
        assert meta["nx_meta"]["C2 Lens (%)"] == 8.967
        assert meta["nx_meta"]["C2 Aperture (μm)"] == 40
        assert meta["nx_meta"]["Stage Position"] == {
            "A (°)": 0,
            "B (°)": 0,
            "X (μm)": 46.293,
            "Y (μm)": -14.017,
            "Z (μm)": -127.155,
        }
        assert meta["nx_meta"]["STEM Rotation Correction (°)"] == 12.4
        assert meta["nx_meta"]["User"] == "SUPERVISOR"
        assert (
            meta["nx_meta"]["Microscope"] == "Microscope Titan 300 kV "
            "D3094 SuperTwin"
        )

    def test_643_eds_and_eels_spectrum_image(self, fei_ser_files):
        test_file_eds = get_full_file_path(
            "***REMOVED***_16.10.32 Spectrum image_dataZeroed_1.ser",
            fei_ser_files,
        )
        test_file_eels = get_full_file_path(
            "***REMOVED***_16.10.32 Spectrum image_dataZeroed_2.ser",
            fei_ser_files,
        )
        meta_1 = fei_emi.get_ser_metadata(test_file_eds)
        meta_2 = fei_emi.get_ser_metadata(test_file_eels)

        assert meta_1["nx_meta"]["DatasetType"] == "SpectrumImage"
        assert meta_1["nx_meta"]["Data Type"] == "STEM_EDS_Spectrum_Imaging"
        assert meta_1["nx_meta"]["Data Dimensions"] == "(40, 70, 4000)"
        assert (
            meta_1["nx_meta"]["Creation Time"]
            == dt(2011, 11, 16, 16, 8, 54).isoformat()  # noqa: DTZ001
        )
        assert meta_1["nx_meta"]["Frame Time (s)"] == 10
        assert meta_1["nx_meta"]["Emission (μA)"] == 237.3
        assert meta_1["nx_meta"]["Tecnai Filter"]["Selected Aperture"] == "2.5 mm"
        assert meta_1["nx_meta"]["Tecnai Filter"]["Slit State"] == "Retracted"

        assert meta_2["nx_meta"]["DatasetType"] == "SpectrumImage"
        assert meta_2["nx_meta"]["Data Type"] == "STEM_EELS_Spectrum_Imaging"
        assert meta_2["nx_meta"]["Data Dimensions"] == "(40, 70, 2048)"
        assert (
            meta_2["nx_meta"]["Creation Time"]
            == dt(2011, 11, 16, 16, 32, 27).isoformat()  # noqa: DTZ001
        )
        assert meta_2["nx_meta"]["Energy Resolution (eV)"] == 10
        assert meta_2["nx_meta"]["Integration Time (s)"] == 0.5
        assert meta_2["nx_meta"]["Extraction Voltage (V)"] == 4500
        assert meta_2["nx_meta"]["Camera Length (m)"] == 0.06
        assert meta_2["nx_meta"]["C2 Lens (%)"] == 8.967
        assert meta_2["nx_meta"]["C3 Aperture (μm)"] == 1000

    def test_643_image_stack(self, fei_ser_files):
        test_file = get_full_file_path(
            "***REMOVED***_17.08.14 Scanning Acquire_Before Full 360 "
            "Dataset_2_dataZeroed_1.ser",
            fei_ser_files,
        )
        meta = fei_emi.get_ser_metadata(test_file)
        assert meta["nx_meta"]["DatasetType"] == "Image"
        assert meta["nx_meta"]["Data Type"] == "STEM_Imaging"
        assert meta["nx_meta"]["Data Dimensions"] == "(5, 1024, 1024)"
        assert (
            meta["nx_meta"]["Creation Time"]
            == dt(2012, 1, 31, 13, 43, 40).isoformat()  # noqa: DTZ001
        )
        assert meta["nx_meta"]["Frame Time (s)"] == 2.0
        assert meta["nx_meta"]["C1 Aperture (μm)"] == 2000
        assert meta["nx_meta"]["C2 Lens (%)"] == 14.99
        assert meta["nx_meta"]["Defocus (μm)"] == -2.593
        assert (
            meta["nx_meta"]["Microscope"] == "Microscope Titan 300 kV "
            "D3094 SuperTwin"
        )
        assert meta["nx_meta"]["Mode"] == "STEM nP SA Zoom Diffraction"
        assert meta["nx_meta"]["Magnification (x)"] == 80000

    def test_643_image_stack_2_newer(self, fei_ser_files):
        test_file = get_full_file_path(
            "***REMOVED***_005_STEM_80kXemi_dataZeroed_1.ser",
            fei_ser_files,
        )
        meta = fei_emi.get_ser_metadata(test_file)
        assert meta["nx_meta"]["DatasetType"] == "Image"
        assert meta["nx_meta"]["Data Type"] == "STEM_Imaging"
        assert meta["nx_meta"]["Data Dimensions"] == "(2, 512, 512)"
        assert (
            meta["nx_meta"]["Creation Time"]
            == dt(2020, 3, 11, 16, 33, 38).isoformat()  # noqa: DTZ001
        )
        assert meta["nx_meta"]["Frame Time (s)"] == 6.34179
        assert meta["nx_meta"]["Dwell Time Path (s)"] == 0.000001
        assert meta["nx_meta"]["C2 Aperture (μm)"] == 10
        assert meta["nx_meta"]["C3 Lens (%)"] == -37.122
        assert meta["nx_meta"]["Defocus (μm)"] == -0.889
        assert (
            meta["nx_meta"]["Microscope"] == "Microscope Titan 300 kV "
            "D3094 SuperTwin"
        )
        assert meta["nx_meta"]["Mode"] == "STEM nP SA Zoom Diffraction"
        assert meta["nx_meta"]["Magnification (x)"] == 80000
        assert meta["nx_meta"]["STEM Rotation (°)"] == -90.0

    def test_no_emi_error(self, caplog, fei_ser_files):
        test_file = get_full_file_path(
            "***REMOVED***_12_no_accompanying_emi_dataZeroed_1.ser",
            fei_ser_files,
        )
        meta = fei_emi.get_ser_metadata(test_file)

        assert "Extractor Warning" in meta["nx_meta"]
        assert (
            "NexusLIMS could not find a corresponding .emi metadata "
            "file for this .ser file" in meta["nx_meta"]["Extractor Warning"]
        )
        assert (
            "NexusLIMS could not find a corresponding .emi metadata "
            "file for this .ser file" in caplog.text
        )
        assert meta["nx_meta"]["emi Filename"] is None

    def test_unreadable_ser(self, caplog, fei_ser_files):
        # if the ser is unreadable, neither the emi or the ser can be read,
        # so we will get the bare minimum of metadata back from the parser
        test_file = get_full_file_path(
            "***REMOVED***_13_unreadable_ser_1.ser",
            fei_ser_files,
        )
        meta = fei_emi.get_ser_metadata(test_file)
        assert "nx_meta" in meta
        assert meta["nx_meta"]["Data Type"] == "Unknown"
        assert meta["nx_meta"]["DatasetType"] == "Misc"
        assert "Creation Time" in meta["nx_meta"]
        assert "***REMOVED***_13_unreadable_ser.emi" in meta["nx_meta"]["emi Filename"]
        assert (
            "The .emi metadata file associated with this .ser file could "
            "not be opened by NexusLIMS." in caplog.text
        )
        assert (
            "The .ser file could not be opened (perhaps file is "
            "corrupted?)" in caplog.text
        )

    @staticmethod
    def _helper_test(caplog, fei_ser_files):
        test_file = get_full_file_path(
            "***REMOVED***_14_unreadable_emi_1.ser",
            fei_ser_files,
        )
        meta = fei_emi.get_ser_metadata(test_file)
        assert "nx_meta" in meta
        assert "ser_header_parameters" in meta
        assert (
            "The .emi metadata file associated with this .ser file could "
            "not be opened by NexusLIMS" in caplog.text
        )
        assert (
            "The .emi metadata file associated with this .ser file could "
            "not be opened by NexusLIMS" in meta["nx_meta"]["Extractor Warning"]
        )
        assert meta["nx_meta"]["Data Dimensions"] == "(1024, 1024)"
        assert meta["nx_meta"]["DatasetType"] == "Image"
        return meta

    def test_unreadable_emi(self, caplog, fei_ser_files):
        # if emi is unreadable, we should still get basic metadata from the ser
        meta = TestSerEmiExtractor._helper_test(caplog, fei_ser_files)  # noqa: SLF001
        assert meta["nx_meta"]["Data Type"] == "TEM_Imaging"

    def test_instr_mode_parsing_with_unreadable_emi_tem(
        self,
        monkeypatch,
        caplog,
        fei_ser_files,
    ):
        # if emi is unreadable, we should get imaging mode based off
        # instrument, but testing directory doesn't allow proper handling of
        # this, so monkeypatch get_instr_from_filepath
        def mock_get_instr(_):
            return instruments.instrument_db["FEI-Titan-TEM-635816_n"]

        monkeypatch.setattr(fei_emi, "get_instr_from_filepath", mock_get_instr)
        meta = TestSerEmiExtractor._helper_test(caplog, fei_ser_files)  # noqa: SLF001
        assert meta["nx_meta"]["Data Type"] == "TEM_Imaging"

    def test_instr_mode_parsing_with_unreadable_emi_stem(
        self,
        monkeypatch,
        caplog,
        fei_ser_files,
    ):
        # if emi is unreadable, we should get imaging mode based off
        # instrument, but testing directory doesn't allow proper handling of
        # this, so monkeypatch get_instr_from_filepath
        def mock_get_instr(_):
            return instruments.instrument_db["FEI-Titan-STEM-630901_n"]

        monkeypatch.setattr(fei_emi, "get_instr_from_filepath", mock_get_instr)
        meta = TestSerEmiExtractor._helper_test(caplog, fei_ser_files)  # noqa: SLF001
        assert meta["nx_meta"]["Data Type"] == "STEM_Imaging"


class TestBasicExtractor:
    """Tests nexusLIMS.extractors.basic_metadata."""

    def test_basic_extraction(self, basic_txt_file):
        metadata = get_basic_metadata(basic_txt_file)

        # test 'nx_meta' values of interest
        assert metadata["nx_meta"]["Data Type"] == "Unknown"
        assert metadata["nx_meta"]["DatasetType"] == "Unknown"
        assert "Creation Time" in metadata["nx_meta"]
        assert dt.fromisoformat(metadata["nx_meta"]["Creation Time"])

    def test_basic_extraction_no_extension(self, basic_txt_file_no_extension):
        metadata = get_basic_metadata(basic_txt_file_no_extension)

        # test 'nx_meta' values of interest
        assert metadata["nx_meta"]["Data Type"] == "Unknown"
        assert metadata["nx_meta"]["DatasetType"] == "Unknown"
        assert "Creation Time" in metadata["nx_meta"]
        assert dt.fromisoformat(metadata["nx_meta"]["Creation Time"])
