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
import os

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
     '643_SURVEY': '643_Titan_survey_image_dataZeroed.dm3.tar.gz',
     '642_STEM_DIFF': '642_Titan_STEM_DIFFRACTION_dataZeroed.dm3.tar.gz',
     '642_OPMODE_DIFF':
         '642_Titan_opmode_diffraction_dataZeroed.dm3.tar.gz',
     '642_EELS_SI_DRIFT':
         '642_Titan_EELS_SI_driftcorr_dataZeroed.dm3.tar.gz',
     '642_EELS_PROC_1': '642_Titan_EELS_proc_1_dataZeroed.dm3.tar.gz',
     '642_ANNOTATIONS':
         '642_Titan_opmode_diffraction_dataZeroed_annotations.dm3.tar.gz',
     '642_TECNAI_MAG': '642_Titan_Tecnai_mag_dataZeroed.dm3.tar.gz',
     'JEOL3010_DIFF': 'JEOL3010_diffraction_dataZeroed.dm3.tar.gz',
     'FFT': 'FFT.dm3.tar.gz',
     'QUANTA_TIF': 'quad1image_001.tif.tar.gz',
     'QUANTA_32BIT': 'quad1image_001_32bit.tif.tar.gz',
     '4D_STEM': '4d_stem.hdf5.tar.gz',
     'PARSE_META_642_TITAN': '01 - 13k - 30um obj.dm3.tar.gz',
     'DB': 'test_db.sqlite.tar.gz'
     }


for name, f in tars.items():
    tars[name] = os.path.join(os.path.dirname(__file__), 'files', f)

files = {}
for k, v in tars.items():
    files[k] = v.strip('.tar.gz')
