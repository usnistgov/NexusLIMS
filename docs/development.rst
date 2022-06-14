Developer documentation
=======================

    `Last updated: December 11, 2021`

If you are interested in learning about how the NexusLIMS back-end works or
adding new features, these instructions should get you up and running with a
development environment that will allow you to modify how the code operates.

Currently, running the NexusLIMS record building back-end code is only
supported and tested on Linux. It may run on MacOS or other UNIX environments,
but is known for sure not to work on Windows due to some specific 
implementation choices.

Installation
------------

NexusLIMS uses the `poetry <https://python-poetry.org/>`_ framework
to manage dependencies and create reproducible deployments. This means that
installing the ``nexusLIMS`` package will require
`installing <https://python-poetry.org/docs/#installation>`_
``poetry``. Once you have a Python distribution of some sort
(NexusLIMS is developed and tested using v3.7.12 and v3.8.12), 
installing ``poetry`` is usually as simple as:

.. code:: bash

   curl -sSL https://raw.githubusercontent.com/python-poetry/poetry/master/get-poetry.py | python -

.. danger::
   Never run code downloaded straight from the internet just because someone
   tells you to! Make sure to download and inspect the script to ensure it 
   doesn't do anything nasty before you run it.

Once ``poetry`` is installed, clone the NexusLIMS |RepoLink|_ using ``git``, 
and then change to the root folder of the repository. Running the following
``install``  command will make ``poetry`` install the dependencies specified
in the ``poetry.lock`` file into a local python virtual environment (so they
don't interfere with other Python installations on your system). It will also
install the ``nexusLIMS`` Python package in "editable" mode so you can make
changes locally for development purposes and still run things.

.. code:: bash

   poetry install

.. note::
   Depending on your preferences, there are a few ``poetry``
   `configuration options <https://python-poetry.org/docs/configuration/>`_
   that you may wish to tweak. For example, running 
   ``$ poetry config virtualenvs.in-project true`` will configure ``poetry``
   to create its virtual environment in a folder local to the project itself
   (by default, the ``./.venv`` folder). This can be useful to keep the project
   files all in one directory, rather than having the Python virtualenv in your
   user folder somewhere else on the system. To see all currently configured
   settings, run ``$ poetry config --list``.

Setting up the environment
--------------------------

To interact with the remote systems from which NexusLIMS harvests information,
it is necessary to provide credentials for authentication and the paths in which
to search for new data files and where to write dataset previews, as well as
the path to the :doc:`NexusLIMS database <database>`.
These values should be set by copying the ``.env.example`` file from the git
repository into a file named ``.env`` in the base directory (in the same folder
as the ``README.md`` and ``pyproject.toml`` files). 
``nexusLIMS`` makes use of the 
`dotenv <https://pypi.org/project/python-dotenv/>`_ library to dynamically 
load variables from this file when running any ``nexusLIMS`` code. 
As an example, the  ``.env`` file content should look something like the 
following (substituting real credentials, of course). See the 
environment variables :ref:`documentation <nexusLIMS-user>` for more
details.

.. code:: bash

    nexusLIMS_user='username'
    nexusLIMS_pass='password'
    mmfnexus_path='/path/to/mmfnexus/mount'
    nexusLIMS_path='/path/to/nexusLIMS/mount/mmfnexus'
    nexusLIMS_db_path='/path/to/nexusLIMS/nexuslims_db.sqlite'
    NEMO_address_1='https://path.to.nemo.com/api/'
    NEMO_token_1='authentication_token'
    NEMO_strftime_fmt_1="%Y-%m-%dT%H:%M:%S%z"
    NEMO_strptime_fmt_1="%Y-%m-%dT%H:%M:%S%z"
    NEMO_tz_1="America/New_York"

Rather than using the ``.env`` file, each of these variables could also be set 
in the environment some other way if you desire. For example, to use Gitlab
CI/CD tools, you would set these variables in your project's CI/CD settings
(see `their documentation <https://docs.gitlab.com/ee/ci/variables/>`_),
since you would not want to commit a ``.env`` file into a remote repository
that contains authorization secrets.

Getting into the environment
----------------------------

Once the package is installed using ``poetry``, the code can be used
like any other Python library within the resulting virtual environment.

``poetry`` allows you to run a single command inside that environment by
using the ``poetry run`` command from the repository:

.. code:: bash

   $ poetry run python

To use other commands in the NexusLIMS environment, you can also “activate”
the environment using the ``$ poetry shell`` command from within the cloned
repository. This will spawn a new shell that ensures all commands will have
access to the installed packages and environment variables set appropriately.

Using ``tox`` for testing
-------------------------

The ``tox`` library is installed as a NexusLIMS dependency via ``poetry``, and
is used to coordinate running the code tests and building documentation. 
``tox`` is configured in the ``[tool.tox]`` section of the ``pyproject.toml``
file. To run the complete test suite in isolated environments through 
``tox``, simply run:

..  code-block:: bash
   
   $ poetry run tox

One caveat is that (at the time of writing), ``tox`` is configured to run the
tests in both a Python 3.7 and Python 3.8 environment, meaning both of these
Python versions must be installed on your system. The recommended way to do
this is to install `pyenv <https://github.com/pyenv/pyenv>`_, which can manage
multiple versions of Python on one system (without resorting to a heavier 
system such as Anaconda). If you have ``pyenv`` installed, the required
versions of Python can be installed by running:

..  code-block:: bash

    $ pyenv local | xargs -L1 pyenv install -s

This will read the versions specified in the ``.python-version`` file, and tell
``pyenv`` to install each one that is found (at the time of writing, this is
3.7.12 and 3.8.12). This command only needs to be run once to do the initial
Python installation. Assuming ``pyenv`` is installed correctly, ``tox`` will
recognize the different Python versions and use them for its tests as defined
in ``pyproject.toml``. 

To build the documentation for the project, run:

..  code-block:: bash

   $ poetry run tox -e docs

The documentation should then be present in the ``./_build/`` directory.

Finally, to generate the baseline test images (for the thumbnail generator
code), run:

..  code-block:: bash

   $ poetry run tox -e gen_mpl_baseline

Other commands can be added to the ``tox`` configuration in ``pyproject.toml``
following the example of the existing tasks. Consult the 
`tox documentation <https://tox.wiki/en/latest/index.html>`_ for more
information.

Building new records
--------------------

The most basic feature of the NexusLIMS back-end is to check the
:doc:`database <database>` for any logs (inserted by the
:doc:`Session Logger App <session_logger_app>`) with a status of
``'TO_BE_BUILT'``. This can be accomplished simply by running the
:py:mod:`~nexusLIMS.builder.record_builder` module directly via:

..  code-block:: bash

    $ poetry run python -m nexusLIMS.builder.record_builder

This command will find any records that need to be built, build their .xml 
files, and then upload them to the front-end CDCS instance. Consult the
record building :doc:`documentation <record_building>` for more details.

Using other features of the library
-----------------------------------

Once you are in a python interpreter (such as ``python``, ``ipython``,
``jupyter``, etc.) from the ``poetry`` environment, you can access the
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
`fork <https://***REMOVED***nexuslims/NexusMicroscopyLIMS/forks/new>`_
the repository, develop your addition on a
`feature branch <https://www.atlassian.com/git/tutorials/comparing-workflows/feature-branch-workflow>`_
within your forked repo, and submit a
`merge request <https://***REMOVED***nexuslims/NexusMicroscopyLIMS/merge_requests>`_
to the
`master <https://***REMOVED***nexuslims/NexusMicroscopyLIMS/tree/master>`_
branch to have it included in the project. Contributing to the package
requires that every line of code is covered by a test case. This project uses
testing through the `pytest <https://docs.pytest.org/en/latest/>`_ library,
and features that do not pass the test cases or decrease coverage will not be
accepted until suitable tests are included (see the ``tests`` directory
for examples) and that the coverage of any new features is 100%.
To get this information, you can use an IDE that includes coverage tracking
(such as `PyCharm <https://www.jetbrains.com/pycharm/>`_) or include the
``--cov`` flag when running the tests. To test the preview image generation,
the ``--mpl`` option should also be provided, together with the path to
the `"reference"` images that are tested against. For example:

.. code:: bash

   $ cd <path_to_repo>
   $ poetry run pytest tests/ --cov=nexusLIMS --cov=tests --cov-config=tests/.coveragerc \
        --cov-report term --mpl --mpl-baseline-path=tests/files/figs

   # ================================= test session starts ==============================================================
   # platform linux -- Python 3.8.12, pytest-5.4.3, py-1.11.0, pluggy-0.13.1                                              
   # cachedir: ***REMOVED***tmp/nexuslims/.tox/py38/.pytest_cache                                                            
   # Matplotlib: 3.4.3                                                                                                          
   # Freetype: 2.6.1                                                                                                      
   # rootdir: ***REMOVED***tmp/nexuslims/tests, inifile: pytest.ini                                                          
   # plugins: cov-3.0.0, mpl-0.13                                                                                      
   # collected 204 items                                                                                               
   #                                                                                                                               
   # tests/test_extractors.py ...............................................................                      [ 30%]
   # tests/test_harvesters.py .................................................................................... [ 72%]
   # tests/test_instruments.py ..........                                                                          [ 76%]
   # tests/test_records.py .................................                                                       [ 93%]
   # tests/test_utils.py .............                                                                             [ 99%]
   # tests/test_version.py .                                                                                       [100%]
   # 
   # ---------- coverage: platform linux, python 3.8.12-final-0 -----------
   # Name                                          Stmts   Miss  Cover   Missing
   # ---------------------------------------------------------------------------
   # nexusLIMS/__init__.py                             8      0   100%
   # nexusLIMS/_urls.py                                3      0   100%
   # nexusLIMS/builder/__init__.py                     0      0   100%
   # nexusLIMS/builder/record_builder.py             201      0   100%
   # nexusLIMS/cdcs.py                                70      0   100%
   # nexusLIMS/db/__init__.py                         10      0   100%
   # nexusLIMS/db/session_handler.py                  96      0   100%
   # nexusLIMS/extractors/__init__.py                 80      0   100%
   # nexusLIMS/extractors/digital_micrograph.py      415      0   100%
   # nexusLIMS/extractors/fei_emi.py                 198      0   100%
   # nexusLIMS/extractors/quanta_tif.py              203      0   100%
   # nexusLIMS/extractors/thumbnail_generator.py     328      0   100%
   # nexusLIMS/harvesters/__init__.py                107      0   100%
   # nexusLIMS/harvesters/nemo.py                    275      0   100%
   # nexusLIMS/harvesters/sharepoint_calendar.py     149      0   100%
   # nexusLIMS/instruments.py                         76      0   100%
   # nexusLIMS/schemas/__init__.py                     0      0   100%
   # nexusLIMS/schemas/activity.py                   166      0   100%
   # nexusLIMS/utils.py                              199      0   100%
   # nexusLIMS/version.py                              2      0   100%
   # tests/__init__.py                                 0      0   100%
   # tests/test_extractors.py                        747      0   100%
   # tests/test_harvesters.py                        477      0   100%
   # tests/test_instruments.py                        56      0   100%
   # tests/test_records.py                           254      0   100%
   # tests/test_utils.py                             101      0   100%
   # tests/test_version.py                             5      0   100%
   # tests/utils.py                                    9      0   100%
   # ---------------------------------------------------------------------------
   # TOTAL                                          4235      0   100%
   # Coverage HTML written to dir tests/coverage

