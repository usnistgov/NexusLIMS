#  NIST Public License - 2020
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
"""Provides some utilities to use during the testing of NexusLIMS."""
import tarfile
from pathlib import Path

import numpy as np
from PIL import Image

tars = {
    "CORRUPTED": "test_corrupted.dm3.tar.gz",
    "LIST_SIGNAL": "list_signal_dataZeroed.dm3.tar.gz",
    "643_EFTEM_DIFF": "643_EFTEM_DIFFRACTION_dataZeroed.dm3.tar.gz",
    "643_EELS_SI": "643_Titan_EELS_SI_dataZeroed.dm3.tar.gz",
    "643_EELS_PROC_THICK": "643_Titan_EELS_proc_thickness_dataZeroed.dm3.tar.gz",
    "643_EELS_PROC_INT_BG": "643_Titan_EELS_proc_intgrate_and_bg_dataZeroed.dm3.tar.gz",
    "643_EELS_SI_DRIFT": "643_Titan_EELS_SI_driftcorr_dataZeroed.dm3.tar.gz",
    "643_EDS_SI": "643_Titan_EDS_SI_dataZeroed.dm4.tar.gz",
    "643_STEM_STACK": "643_Titan_STEM_stack_dataZeroed.dm3.tar.gz",
    "643_SURVEY": "643_Titan_survey_image_dataZeroed.dm3.tar.gz",
    "642_STEM_DIFF": "642_Titan_STEM_DIFFRACTION_dataZeroed.dm3.tar.gz",
    "642_OPMODE_DIFF": "642_Titan_opmode_diffraction_dataZeroed.dm3.tar.gz",
    "642_EELS_SI_DRIFT": "642_Titan_EELS_SI_driftcorr_dataZeroed.dm3.tar.gz",
    "642_EELS_PROC_1": "642_Titan_EELS_proc_1_dataZeroed.dm3.tar.gz",
    "642_ANNOTATIONS": "642_Titan_opmode_diffraction_dataZeroed_annotations.dm3.tar.gz",
    "642_TECNAI_MAG": "642_Titan_Tecnai_mag_dataZeroed.dm3.tar.gz",
    "JEOL3010_DIFF": "JEOL3010_diffraction_dataZeroed.dm3.tar.gz",
    "FFT": "FFT.dm3.tar.gz",
    "QUANTA_TIF": "quad1image_001.tif.tar.gz",
    "QUANTA_32BIT": "quad1image_001_32bit.tif.tar.gz",
    "QUANTA_NO_BEAM": "quad1image_001_no_beam_scan_or_system_meta.tar.gz",
    "4D_STEM": "4d_stem.hdf5.tar.gz",
    "PARSE_META_642_TITAN": "01 - 13k - 30um obj.dm3.tar.gz",
    "FEI_SER": "fei_emi_ser_test_files.tar.gz",
    "DB": "test_db.sqlite.tar.gz",
    "RECORD": "2018-11-13_FEI-Titan-TEM-635816_7de34313.xml.tar.gz",
    "IMAGE_FILES": "test_image_thumb_sources.tar.gz",
}


for name, f in tars.items():
    tars[name] = Path(__file__).parent / "files" / f


def extract_files(tar_key):
    """
    Extract files from a tar archive.

    Will extract files from a tar specified by ``tar_key``; returns a list
    of files that were present in the tar archive
    """
    with tarfile.open(tars[tar_key], "r:gz") as tar:
        tar.extractall(path=Path(tars[tar_key]).parent)
        return [Path(__file__).parent / "files" / i for i in tar.getnames()]


def delete_files(tar_key):
    """
    Delete files previously extracted from a tar.

    Will delete any files that have been extracted from one of the above tars,
    specified by ``tar_key``
    """
    with tarfile.open(tars[tar_key], "r:gz") as tar:
        files = [Path(__file__).parent / "files" / i for i in tar.getnames()]
    for _f in files:
        Path(_f).unlink(missing_ok=True)


def get_full_file_path(filename, fei_ser_files):
    """
    Get full file path for a file.

    Get the full file path on disk for a file that is part of the ``fei_ser_files``
    fixture/dictionary
    """
    return [i for i in fei_ser_files if filename in str(i)][0]


def assert_images_equal(image_1: Path, image_2: Path):
    """
    Test that images are similar using Pillow.

    Parameters
    ----------
    image_1
        The first image to compare
    image_2
        The second image to compare

    Raises
    ------
    AssertionError
        If normalized sum of image content square difference is
        greater than 0.1%

    Notes
    -----
    This method has been adapted from one proposed by Jennifer Helsby
    (redshiftzero) at https://www.redshiftzero.com/pytest-image/,
    and is used here under that code's CC BY-NC-SA 4.0 license.
    """
    img1 = Image.open(image_1)
    img2 = Image.open(image_2)

    # Convert to same mode and size for comparison
    img2 = img2.convert(img1.mode)
    img2 = img2.resize(img1.size)

    sum_sq_diff = np.sum(
        (np.asarray(img1).astype("float") - np.asarray(img2).astype("float")) ** 2,
    )

    if sum_sq_diff == 0:
        # Images are exactly the same
        pass
    else:
        thresh = 0.001
        normalized_sum_sq_diff = sum_sq_diff / np.sqrt(sum_sq_diff)
        assert normalized_sum_sq_diff < thresh, (
            f"Images differed; normalized diff: {normalized_sum_sq_diff}; "
            f"Image 1: {image_1}; Image 2: {image_2}"
        )
