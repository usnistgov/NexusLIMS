# Welcome to NexusLIMS!

[![](https://img.shields.io/badge/NexusLIMS-Documentation-brightgreen)](https://pages.nist.gov/NexusLIMS)

The project serves as the development and documentation space for the back-end of the Nexus Microscopy
Facility Laboratory Information Management System (NexusLIMS), developed by the NIST Office of Data
and Informatics and described in the following *Microscopy and Microanalysis* article: 
[https://doi.org/10.1017/S1431927621000222](https://doi.org/10.1017/S1431927621000222).
This manuscript details the processes by which NexusLIMS harvests and combines data from multiple sources to build 
a record of an experiment on a Nexus facility microscope.

This repository holds the "back-end" code that facilitates the building of experimental records from a 
collection of instruments by extracting metadata from data files and harvesting experimental metadata 
from one or more reservation calendar systems (such as [NEMO](https://github.com/usnistgov/NEMO)). This code will 
extract metadata from those reservations and the data files it finds then build that metadata into an XML-formatted
experimental record that conforms to the "Nexus Experiment" schema (available
[here](https://doi.org/10.18434/M32245)) There is additional documentation available at 
http://pages.nist.gov/NexusLIMS/.

The back-end code contained in this repository is the complement of the front-end user interface code available at
the [NexusLIMS CDCS](https://github.com/usnistgov/NexusLIMS-CDCS) repository. For a "full" installation of NexusLIMS,
both the back-end and front-end parts are required.

## Warnings and Limitations

First, see the standard NIST [disclaimer](https://www.nist.gov/disclaimer).

Next, NexusLIMS was written primarily for internal use within NIST. While efforts have been made to try to generalize 
the code to be applicable to other institutions, many design decisions and implementation details are specific to the
infrastructure that was in place at the time of development. As such, it may not work fully (or at all!) in your
environment without substantial changes.

One of the key parts of the NexusLIMS backend is the metadata extraction from various electron microscopy data formats.
Again, the supported formats are specific to the needs of NIST at the time of development, and the code currently only
processes certain file types, including DigitalMicrograph `.dm3/.dm4` files, `.tif` files (from FEI/Thermo Fisher
FIBs and SEMs), and `.ser`/`.emi` transmission electron microscopy files (from the older FEI TIA acquisition 
software)[^1].
If you have substantially different sorts of microscopes in your research facility, some work will be required to write
extractors for these file formats, a process that can range from fairly easy to quite involved. Regardless, the 
NexusLIMS developers would be very interested in any developments in this regard and would likely provide assistance
where possible and integration into the main codebase.

[^1]: Any mention of commercial products within NIST web pages is for information only; it does not imply 
      recommendation or endorsement by NIST.

Additionally, one of the primary data sources for the generation of experimental data records is a reservation calendar
for specific instruments. NexusLIMS was originally developed to connect to a shared SharePoint-based calendar system,
but then migrated to a more fully-featured laboratory facility software named [NEMO](https://github.com/usnistgov/) 
(also open-source and developed at NIST). As such, only these two data sources were ever implemented, and only the NEMO
data harvester is currently supported/recommended. Any "harvester" for another reservation metadata system would need
to be implemented to match with your local facility requirements (or you could adopt NEMO as a laboratory management
system, but that may not be an option for your facility).

If using NEMO, there is an expectation that a set of "reservation questions" will be associated with the instruments
configured in the NexusLIMS database (see the section of the 
[NEMO Feature Manual](https://github.com/usnistgov/NEMO/blob/master/documentation/NEMO_Feature_Manual.pdf) on this topic
for more details -- approximately page 446). The documentation of the 
[`nemo.res_event_from_session()`](https://pages.nist.gov/NexusLIMS/api/nexusLIMS.harvesters.html#nexusLIMS.harvesters.nemo.res_event_from_session)
method has more details about the expected format of these questions.

NexusLIMS has been developed to run on a Linux-based headless server, although it _may_ work under MacOS as well. It
is known to _not_ work under Windows, and would require some minor development effort to get it to do so. The following
basic steps are provided as installation instructions, but it likely that some changes to the code will be required
unless your deployment environment looks exactly like the one at NIST (which it probably doesn't). 

## Basic installation instructions

The expectation is that the NexusLIMS back-end code will run on a server/system with network access to a collection of 
instrumental data that has been saved in one centralized location (see the 
[NexusLIMS manuscript](https://doi.org/10.1017/S1431927621000222) for more details).

### 0. Prerequisites

Prior to installing NexusLIMS, first install at least one of the versions of python specified in the 
[`.python-version`](./.python-version) file. The NexusLIMS developers utilize [pyenv](https://github.com/pyenv/pyenv)
to do so. The [Poetry](https://python-poetry.org/) package manager should be installed as well. Finally, download
or clone this repository to obtain the code required to run the record builder.

### 1. Installation

With the prerequisite pieces installed, installation of the NexusLIMS library should be as simple as running:

```bash
$ poetry install
```

from the directory where the NexusLIMS project was downloaded. This command uses poetry to parse the 
[`pyproject.toml`](./pyproject.toml) and [`poetry.lock`](./poetry.lock) files to download and install all the correct
third-party libraries required by NexusLIMS into an isolated Python environment (run `$ poetry run which python` to 
find the path to the interpreter Poetry created for you as part of the process).

### 2. Database initialization

NexusLIMS expects the presence of an SQLite database in which it stores information about known instruments and the 
session records that need to be/are built. If this database does not exist, the NexusLIMS record builder will not work.
In fact, the library will not even import at all if the database is not set up correctly. You can use the 
[`NexusLIMS_db_creation_script.sql`](./nexusLIMS/db/dev/NexusLIMS_db_creation_script.sql) file to create a database
with the expected schema, although it will not have any instruments defined in it. 

To define instruments, insert one or more rows into the `instruments` table with values appropriate for your 
environment. See the [database documentation](https://pages.nist.gov/NexusLIMS/database.html) for further descriptions
of the database format and expectations of values in each tables' columns.

### 3. Configuration

Currently, the NexusLIMS back-end is configured via the use of environment variables. In practice, the easiest way
to do this is to copy or rename the [`.env.example`](./.env.example) into a file named `.env`, located in the same 
directory as this README, and then changing the values as required for your deployment environment. The `.env.example`
file is (hopefully) well-documented, so check those comments for a description of the values that should be defined.
Alternatively, you can set your environment variables in some other way, and they should still be understood by the
NexusLIMS code.

Primarily, you need to configure three types of settings:

- First, the username/password for a user in the NexusLIMS CDCS front-end system where the built records will be   
  uploaded. While not currently configurable, the upload functionality could be disabled if this feature is not 
  needed. Also, you will need to enter the URL to your NexusLIMS instance in the `cdcs_url` variable.
- Second, various file paths that indicate the read-only path to the centralized datafile store, a writeable path 
  in which to store preview images and extracted metadata, and the path to the SQlite database file that is used to 
  hold information about instruments and sessions
- Third, settings for the NEMO harvester to use to connect to a NEMO instance holding information about reservations  
  and instrument usage. This is optional, but without it there will be no real way to indicate to the system that a 
  record needs to be built (there is a deprecated "session logger" application that can run on the instrument computers
  directly that is no longer supported; contact the developers if interested)

### 4. Building Records

Records are built when a new session is detected, either from being manually inserted into the `session_log` table of 
the NexusLIMS database, or from the result of harvesting data from a configured NEMO harvester. For full details of the
record building process, see the [Record building workflow](https://pages.nist.gov/NexusLIMS/record_building.html)
documentation page. To initiate the building process, run the record building module from the command line:

```bash
$ poetry run python -m nexusLIMS.builder.record_builder
```

Running the code as a module such as this has a couple of options, which can be viewed by appending the `-h` or `--help`
option flag. This command will kick off the record building process via the 
[`process_new_records()`](https://pages.nist.gov/NexusLIMS/api/nexusLIMS.builder.html#nexusLIMS.builder.record_builder.process_new_records)
method, which will check for the existence of new sessions to build, perform the data file finding operation, extract
the metadata, build records as needed, and upload it/them to the front-end NexusLIMS CDCS application

Alternatively, there is a bash script supplied in the root folder of this repository named `process_new_records.sh`.
This script wraps the above `poetry run python -m nexusLIMS.builder.record_builder` command with additional 
functionality, including logging the results of the run to a file, generating a "lock file" so the record builder will
not run if it is already running, and the sending of notification emails if any errors are detected in the log output.
This script can be configured also by settings in the `.env` file, including the `email_sender` and `email_recipients`
values. At NIST, the deployment of NexusLIMS is automated by running this script via the `cron` scheduler. As currently
written, the logs from this script will be saved in a file relative to the `nexusLIMS_path` environment variable and
organized by date, generated as follows: `"${nexusLIMS_path}/../logs/${year}/${month}/${day}/$(date +%Y%m%d-%H%M).log"`.

## Where to get help?

There is extensive [documentation](http://pages.nist.gov/NexusLIMS/) for those who wish to learn more about the nuts 
and bolts of how the back-end operates.

## Developer instructions

For further details, see the [developer documentation](http://pages.nist.gov/NexusLIMS/development) page, but in 
brief... to develop on the NexusLIMS code, the installation process is similar to above. First install `pyenv` and 
`poetry`, then run `poetry install`, then:

```bash
# install required pyenv environments:
$ pyenv local | xargs -L1 pyenv install  # https://github.com/pyenv/pyenv/issues/919

# configure poetry to put the virtual environment in a local .venv folder (if you want)
$ poetry config virtualenvs.in-project true

# make sure to configure your .env settings prior to running the following commands

# to run tests for python 3.7 and 3.8 environments:
$ poetry run tox

# to generate the documentation:
$ poetry run tox -e docs

# to generate pytest-mpl figures:
$ poetry run tox -e gen_mpl_baseline
```

If you would like to contribute code to NexusLIMS, please fork this repository and submit a pull request for your code 
to be included. 

## About the NexusLIMS logo

The logo for the NexusLIMS project is inspired by the Nobel Prize
[winning](https://www.nobelprize.org/prizes/chemistry/2011/shechtman/facts/)
work of [Dan Shechtman](https://www.nist.gov/content/nist-and-nobel/nobel-moment-dan-shechtman)
during his time at NIST in the 1980s. Using transmission electron diffraction, Shechtman measured an unusual 
diffraction pattern that ultimately overturned a fundamental paradigm of crystallography. He had
discovered a new class of crystals known as [quasicrystals](https://en.wikipedia.org/wiki/Quasicrystal), which have a 
regular structure and diffract, but are not periodic.

We chose to use Shechtman’s [first published](https://journals.aps.org/prl/pdf/10.1103/PhysRevLett.53.1951)
diffraction pattern of a quasicrystal as inspiration for the NexusLIMS logo due to its significance in the electron 
microscopy and crystallography communities, together with its storied NIST heritage:

![NexusLIMS Logo Inspiration](docs/_static/logo_inspiration.png)

## About the developers

NexusLIMS has been developed through a great deal of work by a number of people
including: 

- [Joshua Taillon](https://www.nist.gov/people/joshua-taillon) - Office of Data and Informatics
- [June Lau](https://www.nist.gov/people/june-w-lau) - Office of Data and Informatics
- [Ryan White](https://www.nist.gov/people/ryan-white) - Applied Chemicals and Materials Division / Office of Data and Informatics
- [Marcus Newrock](https://www.nist.gov/people/marcus-william-newrock) - Office of Data and Informatics
- [Ray Plante](https://www.nist.gov/people/raymond-plante) - Office of Data and Informatics
- [Gretchen Greene](https://www.nist.gov/people/gretchen-greene) - Office of Data and Informatics

As well as multiple [SURF](https://www.nist.gov/surf) students/undergraduate interns:

- Rachel Devers - Montgomery College/University of Maryland College Park
- Thomas Bina - Pennsylvania State University
- Priya Shah - University of Pennsylvania
- Sarita Upreti - Montgomery College
