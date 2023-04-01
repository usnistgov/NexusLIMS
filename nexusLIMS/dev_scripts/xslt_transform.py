"""Tranform an XML document using an XSLT stylesheet."""
# ruff: noqa: INP001, T201
import argparse
import logging
import warnings
from pathlib import Path
from typing import Union

from lxml import etree
from urllib3.exceptions import InsecureRequestWarning

logger = logging.getLogger()
warnings.filterwarnings("ignore", category=InsecureRequestWarning)


class XSLTError(Exception):
    """An error in the XSLT transformation."""


def transform_xml(xml: Union[Path, str], xslt: Union[Path, str]):
    """Perform XSLT transformation."""
    dom = etree.parse(xml)  # noqa: S320
    xslt = etree.parse(xslt)  # noqa: S320
    transform = etree.XSLT(xslt)
    try:
        newdom = transform(dom)
    except Exception as e:
        for error in transform.error_log:
            print("LXML XSLT error: ", error.message, error.line)
        raise XSLTError from e

    return etree.tostring(newdom, pretty_print=True).decode()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Transform an XML document using an XSLT and print it to stdout",
    )
    parser.add_argument("--xslt", help="Path to the XSLT to use", default=None)
    parser.add_argument("--xml", help="Path to the XML file to transform", default=None)

    args = parser.parse_args()

    if args.xml is None:
        msg = "XML file must be provided via --xml argument"
        raise ValueError(msg)
    if args.xslt is None:
        msg = "XSLT file must be provided via --xslt argument"
        raise ValueError(msg)

    print(transform_xml(args.xml, args.xslt))
