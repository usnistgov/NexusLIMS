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

if __name__ == '__main__':
    import os as _os
    import time as _time
    import logging as _logging
    from nexusLIMS import mmf_nexus_root_path as _mmf_nexus_root_path
    from nexusLIMS import nexuslims_root_path as _nexuslims_root_path
    from nexusLIMS.builder import record_builder as _rb

    d = _os.path.join(_mmf_nexus_root_path, 'Titan/***REMOVED***')
    dirs = [_os.path.join(d, o) for o in _os.listdir(d)
                if _os.path.isdir(_os.path.join(d, o))]

    dates = [_time.strftime('%Y-%m-%d', _time.localtime(_os.path.getmtime(p)))
             for p in dirs]

    aa_logger = _logging.getLogger('nexusLIMS.schemas.activity')
    aa_logger.setLevel(_logging.INFO)

    for d, pth in zip(dates, dirs):
        print(f'{d} : {pth}')
        outpath = pth.replace(_mmf_nexus_root_path, _nexuslims_root_path)
        instrument = 'FEI-Titan-TEM-635816'
        user = '***REMOVED***'
        outfilename = f'compiled_record_{instrument}_{d}_{user}.xml'
        _rb.dump_record(pth,
                        filename=_os.path.join(outpath, outfilename),
                        instrument=instrument,
                        date=d,
                        user=user)

    # path_to_search = os.path.join(_mmf_nexus_root_path, 'Titan/***REMOVED***/',
    #                               '181113 - ***REMOVED*** - '
    #                               '***REMOVED*** - Titan')

    # Build the XML record and write it to a file
    # filename = _rb.dump_record(path_to_search,
    #                            filename=None,
    #                            instrument='FEI-Titan-TEM-635816',
    #                            date='2018-11-13',
    #                            user='***REMOVED***')