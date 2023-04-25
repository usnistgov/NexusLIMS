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
"""
A module to handle the uploading of previously-built XML records to a CDCS instance.

See https://github.com/usnistgov/NexusLIMS-CDCS for more details on the NexusLIMS
customizations to the CDCS application.

This module can also be run directly to upload records to a CDCS instance without
invoking the record builder.
"""

import argparse
import logging
import os
import sys
from glob import glob
from http import HTTPStatus
from pathlib import Path
from typing import List, Optional
from urllib.parse import urljoin

from tqdm import tqdm

from nexusLIMS.utils import AuthenticationError, nexus_req

logging.basicConfig()
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


def cdcs_url() -> str:
    """
    Return the url to the NexusLIMS CDCS instance by fetching it from the environment.

    Returns
    -------
    url : str
        The URL of the NexusLIMS CDCS instance to use

    Raises
    ------
    ValueError
        If the ``cdcs_url`` environment variable is not defined, raise a ``ValueError``
    """
    url = os.environ.get("cdcs_url", None)
    if url is None:
        msg = "'cdcs_url' environment variable is not defined"
        raise ValueError(msg)

    return url


def get_workspace_id():
    """
    Get the workspace ID that the user has access to.

    This should be the Global Public Workspace in the current NexusLIMS CDCS
    implementation.

    Returns
    -------
    workspace_id : str
        The workspace ID
    """
    # assuming there's only one workspace for this user (that is the public
    # workspace)
    _endpoint = urljoin(cdcs_url(), "rest/workspace/read_access")
    _r = nexus_req(_endpoint, "GET", basic_auth=True)
    if _r.status_code == HTTPStatus.UNAUTHORIZED:
        msg = (
            "Could not authenticate to CDCS. Are the nexusLIMS_user and "
            "nexusLIMS_pass environment variables set correctly?"
        )
        raise AuthenticationError(msg)

    return _r.json()[0]["id"]  # return workspace id


def get_template_id():
    """
    Get the template ID for the schema (so the record can be associated with it).

    Returns
    -------
    template_id : str
        The template ID
    """
    # get the current template (XSD) id value:
    _endpoint = urljoin(cdcs_url(), "rest/template-version-manager/global")
    _r = nexus_req(_endpoint, "GET", basic_auth=True)
    if _r.status_code == HTTPStatus.UNAUTHORIZED:
        msg = (
            "Could not authenticate to CDCS. Are the nexusLIMS_user and nexusLIMS_pass "
            "environment variables set correctly?",
        )
        raise AuthenticationError(msg)

    return _r.json()[0]["current"]  # return template id


def upload_record_content(xml_content, title):
    """
    Upload a single XML record to the NexusLIMS CDCS instance.

    Parameters
    ----------
    xml_content : str
        The actual content of an XML record (rather than a file)
    title : str
        The title to give to the record in CDCS

    Returns
    -------
    post_r : :py:class:`~requests.Response`
        The REST response returned from the CDCS instance after attempting
        the upload
    record_id : str
        The id (on the server) of the record that was uploaded
    """
    endpoint = urljoin(cdcs_url(), "rest/data/")

    payload = {
        "template": get_template_id(),
        "title": title,
        "xml_content": xml_content,
    }

    post_r = nexus_req(endpoint, "POST", json=payload, basic_auth=True)

    if post_r.status_code != HTTPStatus.CREATED:
        # anything other than 201 status means something went wrong
        logger.error("Got error while uploading %s:\n%s", title, post_r.text)
        return post_r

    # assign this record to the public workspace
    record_id = post_r.json()["id"]
    record_url = urljoin(cdcs_url(), f"data?id={record_id}")
    wrk_endpoint = urljoin(
        cdcs_url(),
        f"rest/data/{record_id}/assign/{get_workspace_id()}",
    )

    _ = nexus_req(wrk_endpoint, "PATCH", basic_auth=True)

    logger.info('Record "%s" available at %s', title, record_url)
    return post_r, record_id


def delete_record(record_id):
    """
    Delete a Data record from the NexusLIMS CDCS instance via REST API.

    Parameters
    ----------
    record_id : str
        The id value (on the CDCS server) of the record to be deleted

    Returns
    -------
    response : :py:class:`~requests.Response`
        The REST response returned from the CDCS instance after attempting
        the delete operation
    """
    endpoint = urljoin(cdcs_url(), f"rest/data/{record_id}")
    response = nexus_req(endpoint, "DELETE", basic_auth=True)
    if response.status_code != HTTPStatus.NO_CONTENT:
        # anything other than 204 status means something went wrong
        logger.error("Received error while deleting %s:\n%s", record_id, response.text)
    return response


def upload_record_files(
    files_to_upload: Optional[List[Path]],
    *,
    progress: bool = False,
) -> List[Path]:
    """
    Upload record files to CDCS.

    Upload a list of .xml files (or all .xml files in the current directory)
    to the NexusLIMS CDCS instance using :py:meth:`upload_record_content`.

    Parameters
    ----------
    files_to_upload : typing.Optional[typing.List[pathlib.Path]]
        The list of .xml files to upload. If ``None``, all .xml files in the
        current directory will be used instead.
    progress : bool
        Whether to show a progress bar for uploading

    Returns
    -------
    files_uploaded : list of pathlib.Path
        A list of the files that were successfully uploaded
    record_ids : list of str
        A list of the record id values (on the server) that were uploaded
    """
    if files_to_upload is None:
        logger.info("Using all .xml files in this directory")
        files_to_upload = glob("*.xml")
    else:
        logger.info("Using .xml files from command line")

    logger.info("Found %s files to upload\n", len(files_to_upload))
    if len(files_to_upload) == 0:
        msg = (
            "No .xml files were found (please specify on the "
            "command line, or run this script from a directory "
            "containing one or more .xml files"
        )
        logger.error(msg)
        raise ValueError(msg)

    files_uploaded = []
    record_ids = []

    for f in tqdm(files_to_upload) if progress else files_to_upload:
        f_path = Path(f)
        with f_path.open(encoding="utf-8") as xml_file:
            xml_content = xml_file.read()

        title = f_path.stem
        response, record_id = upload_record_content(xml_content, title)

        if response.status_code != HTTPStatus.CREATED:
            logger.warning("Could not upload %s", f_path.name)
            continue

        files_uploaded.append(f_path)
        record_ids.append(record_id)

    logger.info(
        "Successfully uploaded %i of %i files",
        len(files_uploaded),
        len(files_to_upload),
    )

    return files_uploaded, record_ids


if __name__ == "__main__":  # pragma: no cover
    parser = argparse.ArgumentParser(
        description="Communicate with the Nexus CDCS instance",
    )
    parser.add_argument(
        "--upload-records",
        help="Upload .xml records to the the Nexus CDCS",
        action="store_true",
    )
    parser.add_argument(
        "xml",
        nargs="*",
        help="(used with --upload-records) "
        "Files to upload (separated by space and "
        "surrounded by quotes, if needed). If no files "
        "are specified, all .xml files in the current "
        "directory will be used instead.",
    )

    args = parser.parse_args()

    if len(sys.argv) == 1:
        parser.print_help()

    if args.upload_records:
        if len(sys.argv) == 2:  # noqa: PLR2004
            # no files were provided, so assume the user wanted to glob all
            # .xml files in the current directory
            upload_record_files(None)
        elif len(sys.argv) > 2:  # noqa: PLR2004
            upload_record_files(args.xml)
