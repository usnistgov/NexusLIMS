#! /usr/bin/env python
import requests
from requests_ntlm import HttpNtlmAuth
import logging
from lxml import etree, objectify
from dateparser import parse as dp_parse
from datetime import datetime
import re


def get_auth():
    """
    Set up authentication for the Microscopy Nexus using the miclims account

    Returns
    -------
    HttpNtlmAuth authentication handler for requests
    """
    username = 'miclims'
    passwd = '***REMOVED***'

    domain = 'nist'
    path = domain + '\\' + username

    return HttpNtlmAuth(path, passwd)


def get_events(instrument=None, date=None, user=None):
    """
    Get calendar events for a particular instrument on the Microscopy Nexus,
    on some date, or by some user

    Parameters:
    -----------
    instrument : None, str, or list of str
        One or more of ['titan', 'quanta', 'jeol_sem', 'jeol_tem', 'cm30',
        'em400'], or None. If None, all instruments will be returned.

    date : None or str
        Either None or a YYYY-MM-DD date string indicating the date from
        which events should be fetched (note: the start time of each entry
        is what will be compared). If None, no date filtering will be
        performed. Date will be parsed by
        https://dateparser.readthedocs.io/en/latest/#dateparser.parse,
        but providing the date in the ISO standard format is preferred for
        consistent behavior.

    user : None str
        Either None or a valid NIST username (the short format: e.g. "***REMOVED***"
        instead of joshua.taillon). If None, no user filtering will be
        performed.

    Returns:
    --------
    result : list
        A list of XML nodes ("entry" nodes in the document) that match the
        specified criteria
    """

    # Use dateparser to get python datetime input, and return as YYYY-MM-DD
    if date is not None:
        date_datetime = dp_parse(date, settings={'STRICT_PARSING': True})
        if date_datetime:
            date = datetime.strftime(date_datetime, '%Y-%m-%d')
        else:
            logging.warning("Entered date could not be parsed; reverting to "
                            "None")
            date = None

    # Paths for Nexus Instruments that can be booked through sharepoint calendar
    titan_events = "FEITitanEvents"
    quanta_events = "FEIQuanta200Events"
    jeol_jsm_events = "JEOLJSM7100Events"
    hitachi_events = "HitachiS4700Events"
    jeol_jem_events = "JEOLJEM3010Events"
    cm30_events = "PhilipsCM30Events"
    em400_events = "PhilipsEM400Events"

    all_events = [titan_events,
                  quanta_events,
                  jeol_jsm_events,
                  hitachi_events,
                  jeol_jem_events,
                  cm30_events,
                  em400_events]

    instr_dict = {
        'titan': titan_events,
        'quanta': quanta_events,
        'jeol_sem': jeol_jsm_events,
        'jeol_tem': jeol_jem_events,
        'cm30': cm30_events,
        'em400': em400_events
    }

    url = 'https://***REMOVED***/***REMOVED***/_vti_bin/' \
          'ListData.svc/'

    # TODO: parse instrument input and loop through to generate total output
    # TODO: test cases and automated testing
    #       (will require setting up pytest)
    # DONE: parsing of date
    # DONE: parsing of username

    for instr_name in all_events:
        instr_url = url + instr_name + '?$expand=CreatedBy'
        r = requests.get(instr_url, auth=get_auth())
        logging.info("")
        logging.info("  {} -- {} -- response: {}".format(instr_name,
                                                         instr_url,
                                                         r.status_code))
        if r.status_code == 200:
            # XML elements have a default namespace prefix (Atom format),
            # but lxml does not like an empty prefix, so it is easiest to
            # just sanitize the input and remove the namespaces as in
            # https://stackoverflow.com/a/18160164/1435788:
            xml = re.sub(r'\sxmlns="[^"]+"', '', r.text, count=1)
            xml = bytes(xml, encoding='utf-8')

            parser = etree.XMLParser(remove_blank_text=True, encoding='utf-8')

            # API returns utf-8 encoding, so encode correctly, load from
            # string, and then get the root tree of that top-level element:
            root = etree.fromstring(xml, parser)

            # use LXML to load XSLT stylesheet into xsl_transform
            # (note, etree.XSLT needs to be called on a root _Element
            # not an _ElementTree)
            xsl_dom = etree.parse('cal_parser.xsl', parser).getroot()
            xsl_transform = etree.XSLT(xsl_dom)

            # setup parameters for passing to XSLT parser
            date_param = "''" if date is None else "'{}'".format(date)
            user_param = "''" if user is None else "'{}'".format(user)

            # do XSLT transformation
            simplified_dom = xsl_transform(root,
                                           date=date_param,
                                           user=user_param)

            return simplified_dom

            break
        else:
            raise requests.exceptions.ConnectionError("Could not access Nexus "
                                                      "Sharepoint API")

    return text


def dump_all_calendars():
    """
    asdasd asd a sdas as das das das das dasdasdasdasdasda d asd
    asdasdasdasdasda asda sdasd
    Returns
    -------

    """
    with open('cal_events.xml', 'w') as f:
        text = get_events('all')
        f.write(text)


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    logging.info(get_events(date='2018-12-26'))
    logging.info(get_events(user='***REMOVED***'))
    logging.info(get_events(date='2018-12-26', user='***REMOVED***'))
    logging.info(get_events())
