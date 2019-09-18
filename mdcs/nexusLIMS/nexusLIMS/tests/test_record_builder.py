import os as _os
from nexusLIMS import mmf_nexus_root_path as _mmf_nexus_root_path
from nexusLIMS.builder import record_builder as _rb
from lxml import etree as et
from uuid import UUID as _UUID

# TODO: Figure out a way to include test files without a large compressed file


class TestRecordBuilder:
    def test_record_builder(self):
        path_to_search = _os.path.join(_mmf_nexus_root_path, 'Titan/***REMOVED***/',
                                       '181113 - ***REMOVED*** - '
                                       '***REMOVED*** - Titan')

        # Build the XML record and write it to a file
        filename = _rb.dump_record(path_to_search,
                                   filename=None,
                                   instrument='FEI-Titan-TEM-635816',
                                   date='2018-11-13',
                                   user='***REMOVED***')
        # Read the generated XML file using ElementTree
        assert _os.path.isfile(filename)
        record = et.parse(filename).getroot()
        acq_acts = record.findall('acquisitionActivity')

        # Test some generated parts taken from the SharePoint calendar as well
        # as from the microscope metadata
        assert record.tag == f'{{{record.nsmap["nx"]}}}Experiment'
        assert record[0].tag == 'title'
        assert record.find('summary/experimenter').text == \
            '***REMOVED*** (Fed)'
        assert record.find('summary/instrument').attrib['pid'] == \
            'FEI-Titan-TEM-635816'
        assert record.find('summary/reservationEnd').text == \
            '2018-11-13T16:00:00'
        assert record.find('sample/name').text == 'AM 17-4'
        assert record.find('id').text == '470'
        assert len(acq_acts) == 9
        for aa in acq_acts:
            ids = aa.findall('sampleID')
            for id in ids:
                # If this raises an error, it's not a valid UUID
                val = _UUID(id.text, version=4)

        # os.remove(filename)

    # TODO: Test acquisition activity contents
    def test_acq_builder(self):
        path_to_search = _os.path.join(_mmf_nexus_root_path, 'Titan/***REMOVED***/',
                                       '181113 - ***REMOVED*** - '
                                       '***REMOVED*** - Titan')
        _rb.build_acq_activities(path_to_search)
