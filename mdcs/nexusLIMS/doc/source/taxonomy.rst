NexusLIMS taxonomy
==================

Oftentimes, it can be a bit confusing when speaking about the different portions
of the back-end codebase, so this short page defines the terms frequently
used by the NexusLIMS development team and what is meant by them:

- **Harvester:**

  - The harvesters (implemented in the :py:mod:`nexusLIMS.harvester` package)
    are the portions of the code that connect to external data sources, such
    as the SharePoint calendar. Currently, the calendar harvester is the only
    one implemented, but eventually there will likely be at least an electronic
    laboratory notebook (ELN) harvester as well.

.. Padding. See https://github.com/sphinx-doc/sphinx/issues/2258

- **Extractor:**

  - The extractors (implemented in the :py:mod:`nexusLIMS.extractors` package)
    are the modules that inspect the data files collected during an Experiment
    and pull out the relevant metadata contained within for inclusion in the
    record. The preview image generation is also considered an extractor.

.. Padding. See https://github.com/sphinx-doc/sphinx/issues/2258

- **Record Builder:**

  - The record builder (implemented in the
    :py:mod:`nexusLIMS.builder.record_builder` module) is the heart of the
    NexusLIMS back-end, and is the portion of the library that orchestrates
    the creation of a new record and its insertion into the NexusLIMS CDCS
    instance. Further details are provided on the
    :doc:`record building <record_building>` documentation page.

.. Padding. See https://github.com/sphinx-doc/sphinx/issues/2258

- **Session Logger:**

  - The session logger is the portable Windows application that runs on the
    individual microscope PCs, which logs simple information to the NexusLIMS
    database about when an Experiment has occurred. See the associated
    :doc:`documentation <session_logger_app>` page for more details.