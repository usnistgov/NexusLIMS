import os as _os
import requests as _requests
from glob import glob as _glob
from urllib.parse import urljoin as _urljoin
import warnings as _warnings
from pprint import pprint as _pprint
from urllib3.exceptions import InsecureRequestWarning as _InsecReqWarning
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
        Will be empty dict if there are no XSLT documents in instance (such as
        when it is a new instance)
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

def get_template_id_by_name(template_name):
    endpoint = _urljoin(_cdcs_url, f'rest/template-version-manager/global/')
    headers = {'Content-Type': "application/json",
               'Accept': 'application/json'}
    res = _requests.request("GET", endpoint,
                            headers=headers, auth=(username, password), 
                            verify=False)
    if res.status_code == 200:
        for r in res.json():
            if r['title'] == template_name:
                print(r)
                return r['current']
        return None


def replace_xslt_files(detail, list, template_name):
    if detail is None and list is None:
        print('ERROR: One of either "--detail" or "--list" must be specified')
        return

    if template_name is not None:
        template_id = get_template_id_by_name(template_name)
        print(template_id)
    else:
        template_id = None

    # raise ValueError(1)
    list_basename = _os.path.basename(list)
    detail_basename = _os.path.basename(detail)

    print(f'Using {list} and {detail}\n')
    
    names_to_update = []
    
    if list is not None:
        with open(list) as f:
            list_content = f.read()
        names_to_update.append(list_basename)
    if detail is not None:
        with open(detail) as f:
            detail_content = f.read()
        names_to_update.append(detail_basename)

    xslt_ids = get_current_xslt_ids(names_to_update)

    headers = {'Content-Type': "application/json",
               'Accept': 'application/json'}

    if list is not None:
        if xslt_ids == {}:
            print("Did not find file to replace, so POSTing new list XSL")
            list_payload = {"name": list_basename,  # name of XSL
                            "filename": list_basename,  # filename of XSL
                            "content": list_content,  # xml content of XSL
            }
            list_xsl_endpoint = _urljoin(_cdcs_url, f'rest/xslt/')
            list_response = _requests.request("POST", list_xsl_endpoint,
                                            json=list_payload, headers=headers,
                                            auth=(username, password), 
                                            verify=False)
            new_list_id = list_response.json()['id']
            print(f"new_list_id: {new_list_id}")
        else:
            print("Replacing existing list XSL via PATCH")
            list_payload = {"id": xslt_ids[list_basename],
                            "name": list_basename,  # name of XSL
                            "filename": list_basename,  # filename of XSL
                            "content": list_content,  # xml content of XSL
                            "_cls": "XslTransformation"}
            list_xsl_endpoint = _urljoin(_cdcs_url, 
                                        f'rest/xslt/{xslt_ids[list_basename]}/')
            list_response = _requests.request("PATCH", list_xsl_endpoint,
                                            json=list_payload, headers=headers,
                                            auth=(username, password), 
                                            verify=False)

        print(f"List XSL: {list_xsl_endpoint}\n", list_response.status_code)

    if detail is not None:
        if xslt_ids == {}:
            print("Did not find file to replace, so POSTing new detail XSL")
            detail_payload = {"name": detail_basename,  # name of XSL
                              "filename": detail_basename,  # filename of XSL
                              "content": detail_content,  # xml content of XSL
            }
            detail_xsl_endpoint = _urljoin(_cdcs_url, f'rest/xslt/')
            detail_response = _requests.request("POST", detail_xsl_endpoint,
                                                json=detail_payload, headers=headers,
                                                auth=(username, password), 
                                                verify=False)
            new_detail_id = detail_response.json()['id']
            print(f"new_detail_id: {new_detail_id}")
        else:
            print("Replacing existing detail XSL via PATCH")

            detail_payload = {"id": xslt_ids[detail_basename],
                            "name": detail_basename,  # name of XSL
                            "filename": detail_basename,  # filename of XSL
                            "content": detail_content,  # xml content of XSL
                            "_cls": "XslTransformation"}
            detail_xsl_endpoint = _urljoin(_cdcs_url,
                                        f'rest/xslt/{xslt_ids[detail_basename]}/')
            detail_response = _requests.request("PATCH", detail_xsl_endpoint,
                                                json=detail_payload, headers=headers,
                                                auth=(username, password), verify=False)
        print(f"Detail XSL: {detail_xsl_endpoint}\n", detail_response.status_code)

    if xslt_ids == {}:
        # add new xsl_rendering if there were no XSLTs
        data =  {
            "template": template_id,
            "list_detail_xslt": [
                new_list_id
            ],
            "list_xslt": new_list_id,
            "default_detail_xslt": new_detail_id
        }
        endpoint = _urljoin(_cdcs_url, f'rest/template/xsl_rendering/')
        headers = {'Content-Type': "application/json",
                   'Accept': 'application/json'}
        xsl_response = _requests.request("POST", 
                                         endpoint,
                                         json=data, 
                                         headers=headers,
                                         auth=(username, password), 
                                         verify=False)
        print(xsl_response.json())

if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description='Upload XSLs to a CDCS instance')
    parser.add_argument('--url',
                        help='Full URL of the CDCS instance')
    parser.add_argument('--username')
    parser.add_argument('--password')
    parser.add_argument('--detail', 
                        help="Path to the \"detail\" XSLT to be replaced",
                        default=None)
    parser.add_argument('--list',
                        help="Path to the \"list\" XSLT to be replaced",
                        default=None)
    parser.add_argument('--template-name',
                        help="Template name to associate XSLTs with (only used \
                              if XSLTs are uploaded new",
                        default=None)

    args = parser.parse_args()

    username = args.username
    password = args.password
    _cdcs_url = args.url

    replace_xslt_files(args.detail, args.list, args.template_name)
