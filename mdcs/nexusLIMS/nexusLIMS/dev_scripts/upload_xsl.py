import os as _os
import requests as _requests
from glob import glob as _glob
from urllib.parse import urljoin as _urljoin
import warnings as _warnings
from urllib3.exceptions import InsecureRequestWarning as _InsecReqWarning
from tqdm import tqdm as _tqdm
import logging as _logging

logger = _logging.getLogger()

_warnings.filterwarnings("ignore",
                            category=_InsecReqWarning)

import argparse

parser = argparse.ArgumentParser(description='Upload XSLs to a CDCS instance')
parser.add_argument('--remote', help='Upload to production server rather than local Docker',
    action='store_true')

args = parser.parse_args()

if args.remote:
    username = _os.environ['nexusLIMS_user']
    password = _os.environ['nexusLIMS_pass']
    _cdcs_url = 'https://***REMOVED***'

    list_id = "5da619776621a80b4db103e6"
    list_xsl_endpoint = _urljoin(_cdcs_url, f'rest/xslt/{list_id}/')

    detail_id = "5da619676621a80b4db103e5"
    detail_xsl_endpoint = _urljoin(_cdcs_url, f'rest/xslt/{detail_id}/')
else:
    username = 'admin'
    password = 'admin'
    _cdcs_url = 'https://***REMOVED***/'

    list_id = "5d97c6f2c66d1d15b9f5dc95"
    list_xsl_endpoint = _urljoin(_cdcs_url, f'rest/xslt/{list_id}/')

    detail_id = "5d96629ac66d1d0035765a6a"
    detail_xsl_endpoint = _urljoin(_cdcs_url, f'rest/xslt/{detail_id}/')

with open('***REMOVED***NexusMicroscopyLIMS/xsl/cdcs_stylesheet_list.xsl') as f:
    list_content = f.read()
with open('***REMOVED***NexusMicroscopyLIMS/xsl/cdcs_stylesheet.xsl') as f:
    detail_content = f.read()

payload = {"id": list_id,
           "name": "list",  # name of XSL
           "filename": "cdcs_stylesheet_list.xsl",  # filename of XSL
           "content": list_content,   # xml content of XSL
           "_cls": "XslTransformation"}
headers = {'Content-Type': "application/json"}

list_response = _requests.request("PATCH", list_xsl_endpoint,
                                  json=payload, headers=headers,
                                  auth=(username, password), verify=False)

payload = {"id": detail_id,
           "name": "detail",  # name of XSL
           "filename": "cdcs_stylesheet.xsl",  # filename of XSL
           "content": detail_content,   # xml content of XSL
           "_cls": "XslTransformation"}
detail_response = _requests.request("PATCH", detail_xsl_endpoint,
                                    json=payload, headers=headers,
                                    auth=(username, password), verify=False)

print(f"List XSL: {list_xsl_endpoint}\n", list_response.status_code)
print(f"\nDetail XSL: {detail_xsl_endpoint}\n", detail_response.status_code)
