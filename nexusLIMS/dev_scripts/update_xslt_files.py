"""
Update NexusLIMS CDCS XLST files.

Updates in place or uploads new copy of XSLT files to a NexusLIMS CDCS front end
instance (useful when debugging changes to the XSLT since it saves a lot of time
compared to doing this manually through the Web UI).
"""
# ruff: noqa: T201, INP001, PLR0915
import argparse
import logging
import warnings
from http import HTTPStatus
from pathlib import Path
from typing import Optional
from urllib.parse import urljoin

import requests
from urllib3.exceptions import InsecureRequestWarning

logger = logging.getLogger()
warnings.filterwarnings("ignore", category=InsecureRequestWarning)


def get_current_xslt_ids(names):
    """
    Get the id values of XSLT resources on the server.

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
    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json",
    }
    url = urljoin(_cdcs_url, "rest/xslt/")
    xslt_ids = {}
    resp = requests.request(
        "GET",
        url,
        headers=headers,
        auth=(username, password),
        verify=False,
        timeout=90,
    )

    if resp.status_code == HTTPStatus.OK:
        for xsl in resp.json():
            # xsl is a dictionary with each response
            if xsl["name"] not in names:
                # ignore any XSL documents that don't have one of the
                # specified names
                continue
            xslt_ids[xsl["name"]] = xsl["id"]
        return xslt_ids

    msg = f"Could not parse response from {url}; Response text was: {resp.text}"
    raise ConnectionError(msg)


def get_template_id_by_name(template_name):
    """Get the ID of a template (schema) byt its configured name."""
    endpoint = urljoin(_cdcs_url, "rest/template-version-manager/global/")
    headers = {"Content-Type": "application/json", "Accept": "application/json"}
    res = requests.request(
        "GET",
        endpoint,
        headers=headers,
        auth=(username, password),
        verify=False,
        timeout=90,
    )
    if res.status_code == HTTPStatus.OK:
        for data in res.json():
            if data["title"] == template_name:
                print(data)
                return data["current"]
        return None
    return None


def replace_xslt_files(
    detail_xsl: Optional[Path],
    list_xsl: Optional[Path],
    template_name: Optional[str],
):
    """Replace one or more XSLT files for a given template on a CDCS server."""
    if detail_xsl is None and list_xsl is None:
        print('ERROR: One of either "--detail" or "--list" must be specified')
        return

    if template_name is not None:
        template_id = get_template_id_by_name(template_name)
        print(template_id)
    else:
        template_id = None

    list_basename = list_xsl.name
    detail_basename = detail_xsl.name

    print(f"Using {list_xsl} and {detail_xsl}\n")

    names_to_update = []

    if list_xsl is not None:
        with list_xsl.open(encoding="utf-8") as f:
            list_content = f.read()
        names_to_update.append(list_basename)
    if detail_xsl is not None:
        with detail_xsl.open(encoding="utf-8") as f:
            detail_content = f.read()
        names_to_update.append(detail_basename)

    xslt_ids = get_current_xslt_ids(names_to_update)

    headers = {"Content-Type": "application/json", "Accept": "application/json"}

    if list_xsl is not None:
        if not xslt_ids:
            print("Did not find file to replace, so POSTing new list XSL")
            list_payload = {
                "name": list_basename,  # name of XSL
                "filename": list_basename,  # filename of XSL
                "content": list_content,  # xml content of XSL
            }
            list_xsl_endpoint = urljoin(_cdcs_url, "rest/xslt/")
            list_response = requests.request(
                "POST",
                list_xsl_endpoint,
                json=list_payload,
                headers=headers,
                auth=(username, password),
                verify=False,
                timeout=90,
            )
            new_list_id = list_response.json()["id"]
            print(f"new_list_id: {new_list_id}")
        else:
            print("Replacing existing list XSL via PATCH")
            list_payload = {
                "id": xslt_ids[list_basename],
                "name": list_basename,  # name of XSL
                "filename": list_basename,  # filename of XSL
                "content": list_content,  # xml content of XSL
                "_cls": "XslTransformation",
            }
            list_xsl_endpoint = urljoin(
                _cdcs_url,
                f"rest/xslt/{xslt_ids[list_basename]}/",
            )
            list_response = requests.request(
                "PATCH",
                list_xsl_endpoint,
                json=list_payload,
                headers=headers,
                auth=(username, password),
                verify=False,
                timeout=90,
            )

        print(f"List XSL: {list_xsl_endpoint}\n", list_response.status_code)

    if detail_xsl is not None:
        if not xslt_ids:
            print("Did not find file to replace, so POSTing new detail XSL")
            detail_payload = {
                "name": detail_basename,  # name of XSL
                "filename": detail_basename,  # filename of XSL
                "content": detail_content,  # xml content of XSL
            }
            detail_xsl_endpoint = urljoin(_cdcs_url, "rest/xslt/")
            detail_response = requests.request(
                "POST",
                detail_xsl_endpoint,
                json=detail_payload,
                headers=headers,
                auth=(username, password),
                verify=False,
                timeout=90,
            )
            new_detail_id = detail_response.json()["id"]
            print(f"new_detail_id: {new_detail_id}")
        else:
            print("Replacing existing detail XSL via PATCH")

            detail_payload = {
                "id": xslt_ids[detail_basename],
                "name": detail_basename,  # name of XSL
                "filename": detail_basename,  # filename of XSL
                "content": detail_content,  # xml content of XSL
                "_cls": "XslTransformation",
            }
            detail_xsl_endpoint = urljoin(
                _cdcs_url,
                f"rest/xslt/{xslt_ids[detail_basename]}/",
            )
            detail_response = requests.request(
                "PATCH",
                detail_xsl_endpoint,
                json=detail_payload,
                headers=headers,
                auth=(username, password),
                verify=False,
                timeout=90,
            )
        print(f"Detail XSL: {detail_xsl_endpoint}\n", detail_response.status_code)

    if not xslt_ids:
        # add new xsl_rendering if there were no XSLTs
        data = {
            "template": template_id,
            "list_detail_xslt": [new_list_id],
            "list_xslt": new_list_id,
            "default_detail_xslt": new_detail_id,
        }
        endpoint = urljoin(_cdcs_url, "rest/template/xsl_rendering/")
        headers = {"Content-Type": "application/json", "Accept": "application/json"}
        xsl_response = requests.request(
            "POST",
            endpoint,
            json=data,
            headers=headers,
            auth=(username, password),
            verify=False,
            timeout=90,
        )
        print(xsl_response.json())


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Upload XSLs to a CDCS instance")
    parser.add_argument("--url", help="Full URL of the CDCS instance")
    parser.add_argument("--username")
    parser.add_argument("--password")
    parser.add_argument(
        "--detail",
        help='Path to the "detail" XSLT to be replaced',
        default=None,
    )
    parser.add_argument(
        "--list",
        help='Path to the "list" XSLT to be replaced',
        default=None,
    )
    parser.add_argument(
        "--template-name",
        help="Template name to associate XSLTs with (only used \
                              if XSLTs are uploaded new",
        default=None,
    )

    args = parser.parse_args()

    username = args.username
    password = args.password
    _cdcs_url = args.url

    replace_xslt_files(Path(args.detail), Path(args.list), args.template_name)
