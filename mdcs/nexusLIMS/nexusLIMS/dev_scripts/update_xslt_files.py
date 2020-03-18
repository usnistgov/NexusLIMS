import os as _os
import requests as _requests
from glob import glob as _glob
from urllib.parse import urljoin as _urljoin
import warnings as _warnings
from urllib3.exceptions import InsecureRequestWarning as _InsecReqWarning
from tqdm import tqdm as _tqdm
import logging as _logging
import argparse

logger = _logging.getLogger()
_warnings.filterwarnings("ignore",
                         category=_InsecReqWarning)


def get_current_xslt_ids(names):
    """
    Get the id values of XSLT resources on the server

    Parameters
    ----------
    names : list of str
        The names of the stylesheets to update (i.e. usually `"detail"` and
        `"list"`)

    Returns
    -------
    xslt_ids : dict
        a dictionary of the XSLT id values, with the values in `names` as
        keys and the ID values as values
    """
    headers = {'Content-Type': "application/json",
               'Accept': 'application/json', }
    url = _urljoin(_cdcs_url, f'rest/xslt/')
    xslt_ids = {}
    resp = _requests.request("GET", url, headers=headers,
                             auth=(username, password), verify=False)

    if resp.status_code == 200:
        for xsl in resp.json():
            # xsl is a dictionary with each response
            if xsl['name'] not in names:
                # ignore any XSL documents that don't have one of the
                # specified names
                continue
            else:
                xslt_ids[xsl['name']] = xsl['id']
        return xslt_ids
    else:
        raise ConnectionError(f'Could not parse response from {url}; '
                              f'Response text was: {resp.text}')


def replace_xslt_files():
    list_xsl_file = __file__.replace('mdcs/nexusLIMS/nexusLIMS/'
                                     'dev_scripts/update_xslt_files.py',
                                     'xsl/cdcs_stylesheet_list.xsl')
    detail_xsl_file = __file__.replace('mdcs/nexusLIMS/nexusLIMS/'
                                       'dev_scripts/update_xslt_files.py',
                                       'xsl/cdcs_stylesheet.xsl')
    with open(list_xsl_file) as f:
        list_content = f.read()
    with open(detail_xsl_file) as f:
        detail_content = f.read()

    xslt_ids = get_current_xslt_ids(['list', 'detail'])

    headers = {'Content-Type': "application/json",
               'Accept': 'application/json'}

    list_payload = {"id": xslt_ids['list'],
                    "name": "list",  # name of XSL
                    "filename": "cdcs_stylesheet_list.xsl",  # filename of XSL
                    "content": list_content,  # xml content of XSL
                    "_cls": "XslTransformation"}
    detail_payload = {"id": xslt_ids['detail'],
                      "name": "detail",  # name of XSL
                      "filename": "cdcs_stylesheet.xsl",  # filename of XSL
                      "content": detail_content,  # xml content of XSL
                      "_cls": "XslTransformation"}

    list_xsl_endpoint = _urljoin(_cdcs_url,
                                 f'rest/xslt/{xslt_ids["list"]}/')
    detail_xsl_endpoint = _urljoin(_cdcs_url,
                                   f'rest/xslt/{xslt_ids["detail"]}/')

    list_response = _requests.request("PATCH", list_xsl_endpoint,
                                      json=list_payload, headers=headers,
                                      auth=(username, password), verify=False)
    detail_response = _requests.request("PATCH", detail_xsl_endpoint,
                                        json=detail_payload, headers=headers,
                                        auth=(username, password), verify=False)

    print(f"List XSL: {list_xsl_endpoint}\n", list_response.status_code)
    print(f"\nDetail XSL: {detail_xsl_endpoint}\n", detail_response.status_code)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description='Upload XSLs to a CDCS instance')
    parser.add_argument('--production',
                        help='Upload to production server rather than local '
                             'Docker instance. This option has highest '
                             'priority of all.',
                        action='store_true')
    parser.add_argument('--poole',
                        help='Upload to poole test server rather than local '
                             'Docker instance',
                        action='store_true')

    args = parser.parse_args()

    if args.production:
        username = _os.environ['nexusLIMS_user']
        password = _os.environ['nexusLIMS_pass']
        _cdcs_url = 'https://***REMOVED***'
    elif args.poole:
        username = 'admin'
        password = 'admin'
        _cdcs_url = 'https://***REMOVED***/'
    else:
        username = 'admin'
        password = 'admin'
        _cdcs_url = 'https://***REMOVED***/'

    replace_xslt_files()
