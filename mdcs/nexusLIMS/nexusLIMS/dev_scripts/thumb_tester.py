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
import numpy as np
from nexusLIMS.extractors.thumbnail_generator import sig_to_thumbnail
import hyperspy.api as hs
from nexusLIMS import mmf_nexus_root_path as _mmf_path
import os

extension = '.png'
dpi = 100


def oned_signals():
    s = hs.datasets.example_signals.EDS_TEM_Spectrum()
    s.metadata.General.title = 'Dummy spectrum'
    print('1D: Single spectrum')
    sig_to_thumbnail(s, f'***REMOVED***tmp/1-spectrum{extension}', dpi=dpi)

    oned_s = hs.stack([s * i for i in np.arange(.1, 1, .1)],
                      new_axis_name='x')
    oned_s.metadata.General.title = 'Dummy line scan'
    print('1D: Line scan')
    sig_to_thumbnail(oned_s, f'***REMOVED***tmp/2-linescan{extension}', dpi=dpi)

    s3 = hs.load('***REMOVED***tmp/EELS_SI.hdf5')
    s3.metadata.General.title = 'Example spectrum image'
    print('1D: Spectrum image (2d)')
    sig_to_thumbnail(s3, f'***REMOVED***tmp/3-2dSI{extension}', dpi=dpi)

    s = hs.datasets.example_signals.EDS_SEM_Spectrum()
    oned_s = hs.stack([s * i for i in np.arange(.1, 1, .1)])
    twod_s = hs.stack([oned_s] * 10)
    threed_s = hs.stack([twod_s] * 5)
    threed_s.metadata.General.title = 'Example multi-dimensional EDS spectrum'
    print('1D: Spectrum image (3d)')
    sig_to_thumbnail(threed_s, f'***REMOVED***tmp/4-3dSI{extension}', dpi=dpi)


def twod_signals():
    s = hs.load('***REMOVED***tmp/diffraction.dm3')
    print('2D: Diffraction pattern')
    sig_to_thumbnail(s, f'***REMOVED***tmp/5-diffraction{extension}', dpi=dpi)

    s2 = hs.load('***REMOVED***tmp/darkfield image.dm3')
    print('2D: Image')
    sig_to_thumbnail(s2, f'***REMOVED***tmp/6-DF_image{extension}', dpi=dpi)

    s3 = hs.load('***REMOVED***tmp/through_focal_series_ex.dm3')
    s3.metadata.General.title = "Through Focal Series"
    print('2D: Image stack')
    sig_to_thumbnail(s3, f'***REMOVED***tmp/7-image_series{extension}', dpi=dpi)

    s4 = hs.load('***REMOVED***tmp/4d_stem.hdf5')
    print('2D: Hyperimage')
    sig_to_thumbnail(s4.inav[:, :], f'***REMOVED***tmp/8-hyperimage{extension}',
                     dpi=dpi)


def other_signals():
    dict0 = {'size': 70, 'name': 'nav axis 3', 'units': 'nm',
             'scale': 2, 'offset': 0}
    dict1 = {'size': 50, 'name': 'nav axis 2', 'units': 'pm',
             'scale': 200, 'offset': 0}
    dict2 = {'size': 40, 'name': 'nav axis 1', 'units': 'mm',
             'scale': 0.02, 'offset': 0}
    dict3 = {'size': 30, 'name': 'sig axis 3', 'units': 'eV',
             'scale': 100, 'offset': 0}
    dict4 = {'size': 20, 'name': 'sig axis 2', 'units': 'Hz',
             'scale': 0.2121, 'offset': 0}
    dict5 = {'size': 10, 'name': 'sig axis 1', 'units': 'radians',
             'scale': 0.314, 'offset': 0}
    s = hs.signals.BaseSignal(np.zeros((10, 20, 30, 40, 50, 70)),
                              axes=[dict0, dict1, dict2, dict3, dict4, dict5])
    s = s.transpose(navigation_axes=3)
    s.metadata.General.title = 'Signal with higher-order dimensionality'
    print('Higher dimensional signal')
    sig_to_thumbnail(s, f'***REMOVED***tmp/9-more_dimensions{extension}', dpi=dpi)


def survey_image():
    # test a survey image from 643 Titan
    fname = os.path.join(_mmf_path,
                         '643Titan/***REMOVED***/191113 - Reactor Sample FIB Specimen '
                         '- EELS Maps - 643 Titan/SI 01/'
                         'SI Survey Image (active).dm3')
    out_fname = fname.replace('mmfnexus', 'nexusLIMS/mmfnexus')
    sig_to_thumbnail(hs.load(fname), f'{out_fname}.thumb.png', dpi=dpi)

    # Test a survey image from 642 Titan
    fname = os.path.join(_mmf_path,
                         'Titan/v***REMOVED***/1***REMOVED*** Si membrane '
                         '***REMOVED***/***REMOVED*** Si '
                         '***REMOVED*** SI21 '
                         'lw19corner ADF4 Survey Image.dm3')
    out_fname = fname.replace('mmfnexus', 'nexusLIMS/mmfnexus')
    sig_to_thumbnail(hs.load(fname), f'{out_fname}.thumb.png', dpi=dpi)

    # Test a non-survey image with annotations:
    fname = os.path.join(_mmf_path,
                         'Titan/***REMOVED***/***REMOVED*** 6hr 750C - '
                         'number4 - ***REMOVED*** - Titan/02 - 30um obj - 8100x.dm3')
    out_fname = fname.replace('mmfnexus', 'nexusLIMS/mmfnexus')
    sig_to_thumbnail(hs.load(fname), f'{out_fname}.thumb.png', dpi=dpi)


if __name__ == '__main__':
    # oned_signals()
    # twod_signals()
    # other_signals()

    survey_image()
