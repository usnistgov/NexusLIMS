API Documentation
=================

This page contains links to the automatically generated documentation
from the specific functions, classes, and methods that are part of the
``nexusLIMS`` package.

At a high level, the project is divided into a number of different sub-packages:
the ``builder`` focuses on the creation of XML records that will be fed into
the metadata repository (CDCS), ``extractors`` contains the functionality used
to parse metadata from the various files encountered in the Electron Microscopy
Nexus facility (as well as preview image generation), ``harvester`` concerns
the collection of information from various metadata sources, such as the
reservation calendar system, the session log database, electronic laboratory
notebooks (to be implemented), etc., ``schemas`` contains code that helps the
record builder convert the metadata that we harvest and extract into a
Python class-based structure that is consisted with the metadata schema
developed for use with CDCS. The top-level ``nexusLIMS`` package contains a
few additional modules (such as ``utils`` and ``instruments``) that are used
more broadly throughout the codebase.

Use the links below or the `Next`/`Previous` links
in the top header bar to browse through the documentation.

.. toctree::
   :caption: Package structure:
   :titlesonly:
   :maxdepth: -1
   :glob:

   api/nexusLIMS.rst