Developer documentation
=======================

If you are interested in learning about how the NexusLIMS back-end works or
adding new features, these instructions should get you up and running with a
development environment that will allow you to modify how the code operates.

Installation
------------

NexusLIMS uses the `pipenv <https://docs.pipenv.org/en/latest/>`_ framework
to manage dependencies and create reproducible deployments. This means that
installing the ``nexusLIMS`` package will require
`installing <https://docs.pipenv.org/en/latest/install/#installing-pipenv>`_
``pipenv``. Once you have a Python distribution of some sort
(NexusLIMS is developed and tested using v3.7.5), installing ``pipenv`` is
usually as simple as:

.. code:: bash

   pip install --user pipenv

Once ``pipenv`` is installed, clone the |RepoLink|_ using ``git``, and
then change to the root folder of the repository. Running the following
``install``  command will cause the ``Pipfile`` to be examined and
dependencies automatically resolved and installed into a local python
virtual environment:

.. code:: bash

   pipenv install --dev

Make sure to specify the ``--dev`` flag to ensure that the packages needed for
development are installed alongside the regular NexusLIMS code.

Setting up the environment
--------------------------

To interact with the remote systems from which NexusLIMS harvests information,
it is necessary to provide credentials for authentication and the paths in which
to search for new data files and where to write dataset previews, as well as
the path to the :doc:`NexusLIMS database <database>`.
These values should be set by copying the ``.env.example`` file from the git
repository into a file named ``.env`` in the base directory (in the same folder
as the ``Pipfile`` file). ``pipenv`` will source variables from this file when
entering the environment (through the ``pipenv shell`` or ``pipenv run``
commands) prior to running any other code. As an example, the  ``.env`` file
content should look the following (substituting real credentials, of course)::

    nexusLIMS_user='username'
    nexusLIMS_pass='password'
    mmfnexus_path='/path/to/mmfnexus/mount'
    nexusLIMS_path='/path/to/nexusLIMS/mount/mmfnexus'
    nexusLIMS_db_path='/path/to/nexusLIMS/nexuslims_db.sqlite'


Getting into the environment
----------------------------

Once the package is installed using ``pipenv``, the code can be used
like any other Python library within the resulting virtual environment.

``pipenv`` allows you to run a single command inside that environment by
using the ``pipenv run`` command from the repository:

.. code:: bash

   $ pipenv run python

To use other commands in the NexusLIMS environment, you can also “activate”
the environment using the ``$ pipenv shell`` command from within the cloned
repository. This will spawn a new shell that ensures all commands will have
access to the installed packages and environment variables set appropriately.

Building new records
--------------------

The most basic feature of the NexusLIMS back-end is to check the
:doc:`database <database>` for any logs (inserted by the
:doc:`Session Logger App <session_logger_app>`) with a status of
``'TO_BE_BUILT'``. This can be accomplished simply by running the
:py:mod:`~nexusLIMS.builder.record_builder` module directly via:

..  code-block:: bash

    $ pipenv run python -m nexusLIMS.builder.record_builder

This command will find any records that need to be built, build the .xml file,
and then upload it to the front-end CDCS instance.

Using other features of the library
-----------------------------------

Once you are in a python interpreter (such as ``python``, ``ipython``,
``jupyter``, etc.) from the ``pipenv`` environment, you can access the
code of this library through the ``nexusLIMS`` package if you want to do other
tasks, such as extracting metadata or building previews images, etc.

For example, to extract the metadata from a ``.tif`` file saved on the
FEI Quanta, run the following code using the
:py:func:`~nexusLIMS.extractors.quanta_tif.get_quanta_metadata` function:

.. code:: python

   from nexusLIMS.extractors.quanta_tif import get_quanta_metadata
   meta = get_quanta_metadata("path_to_file.tif")

The ``meta`` variable will then contain a dictionary with the extracted
metadata from the file.


Contributing
------------

To contribute, please
`fork <https://gitlab.nist.gov/gitlab/nexuslims/NexusMicroscopyLIMS/forks/new>`_
the repository, develop your addition on a
`feature branch <https://www.atlassian.com/git/tutorials/comparing-workflows/feature-branch-workflow>`_
within your forked repo, and submit a
`merge request <https://gitlab.nist.gov/gitlab/nexuslims/NexusMicroscopyLIMS/merge_requests>`_
to the
`master <https://gitlab.nist.gov/gitlab/nexuslims/NexusMicroscopyLIMS/tree/master>`_
branch to have it included in the project. Contributing to the package
requires that every line of code is covered by a test case. This project uses
testing through the `pytest <https://docs.pytest.org/en/latest/>`_ library,
and features that do not pass the test cases or decrease coverage will not be
accepted until suitable tests are included (see the |testsLink|_ directory
for examples) and that the coverage of any new features is 100%.
To get this information, you can use an IDE that includes coverage tracking
(such as `PyCharm <https://www.jetbrains.com/pycharm/>`_) or include the
``--cov`` flag when running the tests. To test the preview image generation,
the ``--mpl`` option should also be provided, together with the path to
the `"reference"` images that are tested against. For example:

.. code:: bash

   $ cd <path_to_repo>
   $ pipenv run pytest mdcs/nexusLIMS/nexusLIMS/tests --cov=mdcs/nexusLIMS/nexusLIMS \
        --cov-report term --mpl --mpl-baseline-path=mdcs/nexusLIMS/nexusLIMS/tests/files/figs

   # ============================= test session starts ==============================
   # platform linux -- Python 3.7.5, pytest-5.3.5, py-1.8.1, pluggy-0.13.1
   # Matplotlib: 3.1.3
   # Freetype: 2.6.1
   # rootdir: mdcs/nexusLIMS/nexusLIMS/tests, inifile: pytest.ini
   # plugins: mpl-0.11, cov-2.8.1, sugar-0.9.2
   # collected 104 items
   #
   # mdcs/nexusLIMS/nexusLIMS/tests/test_calendar_handling.py .............................. [ 28%]
   # mdcs/nexusLIMS/nexusLIMS/tests/test_extractors.py ..................................... [ 64%]
   # mdcs/nexusLIMS/nexusLIMS/tests/test_instruments.py .....                                [ 69%]
   # mdcs/nexusLIMS/nexusLIMS/tests/test_records.py ......................                   [ 90%]
   # mdcs/nexusLIMS/nexusLIMS/tests/test_utils.py .........                                  [ 99%]
   # mdcs/nexusLIMS/nexusLIMS/tests/test_version.py .                                        [100%]
   #
   # ----------- coverage: platform linux, python 3.7.5-final-0 ---------------------
   # Name                                                         Stmts   Miss  Cover
   # --------------------------------------------------------------------------------
   # mdcs/nexusLIMS/nexusLIMS/__init__.py                             8      0   100%
   # mdcs/nexusLIMS/nexusLIMS/_urls.py                                3      0   100%
   # mdcs/nexusLIMS/nexusLIMS/builder/__init__.py                     0      0   100%
   # mdcs/nexusLIMS/nexusLIMS/builder/record_builder.py             149      0   100%
   # mdcs/nexusLIMS/nexusLIMS/cdcs.py                                69      0   100%
   # mdcs/nexusLIMS/nexusLIMS/db/__init__.py                         10      0   100%
   # mdcs/nexusLIMS/nexusLIMS/db/session_handler.py                  72      0   100%
   # mdcs/nexusLIMS/nexusLIMS/extractors/__init__.py                 65      0   100%
   # mdcs/nexusLIMS/nexusLIMS/extractors/digital_micrograph.py      421      0   100%
   # mdcs/nexusLIMS/nexusLIMS/extractors/fei_emi.py                   0      0   100%
   # mdcs/nexusLIMS/nexusLIMS/extractors/quanta_tif.py              197      0   100%
   # mdcs/nexusLIMS/nexusLIMS/extractors/thumbnail_generator.py     329      0   100%
   # mdcs/nexusLIMS/nexusLIMS/harvester/__init__.py                   0      0   100%
   # mdcs/nexusLIMS/nexusLIMS/harvester/sharepoint_calendar.py      108      0   100%
   # mdcs/nexusLIMS/nexusLIMS/instruments.py                         44      0   100%
   # mdcs/nexusLIMS/nexusLIMS/schemas/__init__.py                     0      0   100%
   # mdcs/nexusLIMS/nexusLIMS/schemas/activity.py                   151      0   100%
   # test_calendar_handling.py                                      154      0   100%
   # test_extractors.py                                             379      0   100%
   # test_instruments.py                                             27      0   100%
   # test_records.py                                                181      0   100%
   # test_utils.py                                                   61      0   100%
   # test_version.py                                                  5      0   100%
   # utils.py                                                         7      0   100%
   # mdcs/nexusLIMS/nexusLIMS/utils.py                              135      0   100%
   # mdcs/nexusLIMS/nexusLIMS/version.py                              2      0   100%
   # --------------------------------------------------------------------------------
   # TOTAL                                                         2577      0   100%
