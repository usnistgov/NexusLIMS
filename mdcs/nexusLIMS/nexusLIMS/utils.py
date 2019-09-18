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

from lxml import etree as _etree
import certifi as _certifi
import tempfile as _tempfile


def parse_xml(xml, xslt_file, **kwargs):
    """
    Parse and translate an XML string from the API into a nicer format

    Parameters
    ----------
    xml : str or bytes
        A string containing XML, such as that returned by :py:func:`~.fetch_xml`
    xslt_file : str
        Path to the XSLT file to use for transformation
    **kwargs : dict (optional)
        Other keyword arguments are passed as parameters to the XSLT
        transformer. ``None`` values are converted to an empty string.
    Returns
    -------
    simplified_dom : ``lxml.XSLT`` transformation result
    """

    for key, value in kwargs.items():
        kwargs[key] = "''" if value is None else f"'{value}'"

    parser = _etree.XMLParser(remove_blank_text=True, encoding='utf-8')

    # load XML structure from  string
    root = _etree.fromstring(xml, parser)

    # use LXML to load XSLT stylesheet into xsl_transform
    # (note, etree.XSLT needs to be called on a root _Element
    # not an _ElementTree)
    xsl_dom = _etree.parse(xslt_file, parser).getroot()
    xsl_transform = _etree.XSLT(xsl_dom)

    # do XSLT transformation
    try:
        simplified_dom = xsl_transform(root, **kwargs)
    except _etree.XSLTApplyError:
        for error in xsl_transform.error_log:
            print(error.message, error.line)
        raise _etree.XSLTApplyError
    return simplified_dom


def nexus_req(url, func, **kwargs):
    """
    A helper method that wraps a function from :py:mod:`requests`, but adds a
    local certificate authority chain to validate the SharePoint server's
    certificates and authenticates using NTLM.

    Parameters
    ----------
    url : str
        The URL to fetch
    func : func
        The function from the ``requests`` library to use (e.g.
        :py:func:`~requests.get`, :py:func:`~requests.put`,
        :py:func:`~requests.post`, etc.)
    **kwargs : dict (optional)
        Other keyword arguments are passed along to the ``func``

    Returns
    -------
    r : :py:class:`requests.Response`
        A requests response object
    """
    from .harvester.sharepoint_calendar import CA_BUNDLE_PATH, get_auth
    with _tempfile.NamedTemporaryFile() as tmp:
        with open(_certifi.where(), 'rb') as sys_cert:
            lines = sys_cert.readlines()
        tmp.writelines(lines)
        with open(CA_BUNDLE_PATH, 'rb') as our_cert:
            lines = our_cert.readlines()
        tmp.writelines(lines)
        tmp.seek(0)
        r = func(url, auth=get_auth(), verify=tmp.name, **kwargs)

    return r


