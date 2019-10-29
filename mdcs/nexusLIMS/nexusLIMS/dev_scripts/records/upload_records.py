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
    import requests as _requests
    from glob import glob as _glob
    from urllib.parse import urljoin as _urljoin
    from nexusLIMS._urls import cdcs_url as _cdcs_url
    import warnings as _warnings
    from urllib3.exceptions import InsecureRequestWarning as _InsecReqWarning
    from tqdm import tqdm as _tqdm
    import logging as _logging

    logger = _logging.getLogger()

    _warnings.filterwarnings("ignore",
                             category=_InsecReqWarning)

    file_list = _glob('*.xml')

    username = _os.environ['nexusLIMS_user']
    password = _os.environ['nexusLIMS_pass']

    endpoint = _urljoin(_cdcs_url, 'rest/workspace/read_access')
    r = _requests.request("GET", endpoint, auth=(username, password),
                          verify=False)
    workspace_id = r.json()[0]['id']

    endpoint = _urljoin(_cdcs_url, 'rest/template-version-manager/global')
    r = _requests.request("GET", endpoint, auth=(username, password), 
                          verify=False)
    template_id = r.json()[0]['current']

    endpoint = _urljoin(_cdcs_url, 'rest/data/')

    for f in _tqdm(file_list):
        with open(f, 'r') as xml_file:
            xml_content = xml_file.read()

        payload = {
            'template': template_id,
            'title': _os.path.basename(f),
            'xml_content': xml_content
        }

        r = _requests.request("POST", endpoint, auth=(username, password),
                              json=payload, verify=False)

        if r.status_code == 500:
            logger.warning('Got error on ' + _os.path.basename(f))

        record_id = r.json()['id']
        wrk_endpoint = _urljoin(_cdcs_url,
                                f'rest/data/{record_id}/assign/{workspace_id}')

        r = _requests.request("PATCH", wrk_endpoint, auth=(username, password),
                              verify=False)

        # print(r.text)
