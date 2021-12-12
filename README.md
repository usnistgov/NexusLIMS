# Welcome to NexusLIMS!

The project serves as the development and documentation space for the back-end
of the Nexus Microscopy Facility Laboratory Information Management System
(NexusLIMS), developed by the NIST Office of Data and Informatics.
This documentation contains a number of pages that detail the processes by
which NexusLIMS harvests and combines data from multiple sources to build
a record of an experiment on a Nexus facility microscope.

## Where to get help?

Most typical users will have little reason to interact directly with the
NexusLIMS back-end code contained in this repository, since it operates
completely automatically and builds experimental records without any need for 
user input. There is extensive 
[documentation](http://***REMOVED***/NexusMicroscopyLIMS/doc/index.html)
however, for those who wish to learn more about the nuts and bolts of how the
back-end operates to create the records that users view at
https://***REMOVED***.

## Developer instructions

To run tests, install `pyenv` and `poetry`, run `poetry install`, then:

```bash
# install required pyenv environments:
$ pyenv local | xargs -L1 pyenv install  # https://github.com/pyenv/pyenv/issues/919

# configure poetry 
$ poetry config virtualenvs.in-project true

# to run tests for python 3.7 and 3.8 environments
$ poetry run tox

# to generate docs:
$ poetry run tox -e docs

# to generate pytest-mpl figures:
$ poetry run tox -e gen_mpl_baseline
```

## How to help

As a Nexus Facility instrument user, the best way to help is to simply use the
system by remembering to start the 
[Session Logger App](http://***REMOVED***/NexusMicroscopyLIMS/doc/session_logger_app.html)
while on a microscope, and then using the NexusLIMS front-end system at
https://***REMOVED*** to search through and browse your experimental data.
Beyond that, suggestions for improvements or additional features are always
appreciated, and can be sent to the developers by submitting a
[new issue](https://***REMOVED***nexuslims/NexusMicroscopyLIMS/issues/new)
in this repository. The current status of development can also be tracked on
the [boards](https://***REMOVED***nexuslims/NexusMicroscopyLIMS/-/boards)
page.

## About the NexusLIMS logo

The logo for the NexusLIMS project is inspired by the Nobel Prize
[winning](https://www.nobelprize.org/prizes/chemistry/2011/shechtman/facts/)
work of 
[Dan Shechtman](https://www.nist.gov/content/nist-and-nobel/nobel-moment-dan-shechtman)
during his time at NIST in the 1980s. Using transmission electron
diffraction, Shechtman measured an unusual diffraction pattern that
ultimately overturned a fundamental paradigm of crystallography. He had
discovered a new class of crystals known as
[quasicrystals](https://en.wikipedia.org/wiki/Quasicrystal), which
have a regular structure and diffract, but are not periodic.

We chose to use Shechtman’s 
[first published](https://journals.aps.org/prl/pdf/10.1103/PhysRevLett.53.1951)
diffraction pattern of a quasicrystal as inspiration for the NexusLIMS
logo due to its significance in the electron microscopy and
crystallography communities, together with its storied NIST heritage:

![NexusLIMS Logo Inspiration](docs/_static/logo_inspiration.png)

## About the developers

NexusLIMS has been developed through a great deal of work by a number of people
including: 

- [Joshua Taillon](https://www.nist.gov/people/joshua-taillon) - Office of Data and Informatics
- [June Lau](https://www.nist.gov/people/june-w-lau) - Office of Data and Informatics
- [Marcus Newrock](https://www.nist.gov/people/marcus-william-newrock) - Office of Data and Informatics
- [Ray Plante](https://www.nist.gov/people/raymond-plante) - Office of Data and Informatics
- [Gretchen Greene](https://www.nist.gov/people/gretchen-greene) - Office of Data and Informatics

As well as multiple SURF students/undergraduate interns:

- Rachel Devers - Montgomery College/University of Maryland College Park
- Thomas Bina - Pennsylvania State University
- Priya Shah - University of Pennsylvania
- Sarita Upreti - Montgomery College
