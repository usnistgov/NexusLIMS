Welcome to NexusLIMS!
=====================

The project serves as the development and documentation space for the back-end
of the Nexus Microscopy Facility Laboratory Information Management System
(LIMS), developed by the NIST Office of Data and Informatics.
This documentation contains a number of pages that detail the processes by
which NexusLIMS harvests and combines data from multiple sources to build
a record of an experiment on a Nexus facility microscope.

Documentation overview
----------------------

The :doc:`data security <data_security>` page explains the approach to our
highest priority, which is protecting users' research data. Besides this,
there are pages describing how data about individual sessions is
:doc:`collected <session_logger_app>` and  :doc:`stored <database>`, as
well as a detailed description of how a record of a given experiment
:doc:`is built <record_building>`, from beginning to end.
There is also additional documentation about the practices used
in :doc:`developing NexusLIMS <development>`, the
:doc:`schema <schema_documentation>` used to represent Experiment records,
and :doc:`customizations <customizing_cdcs>` that were made to
the `CDCS <https://cdcs.nist.gov>`_ platform to create the NexusLIMS front-end.
Finally, there is detailed :doc:`API documentation <api>` for every method
used in the NexusLIMS back-end.

Most typical users will have no reason to interact with the NexusLIMS back-end
directly, since it operates completely automatically and builds experimental
records without any need for user input. These pages serve mostly as reference
for those with more interest in the nuts and bolts of how it all works together,
and how the system may be able to be changed in the future.

How to help
-----------

As a Nexus Facility instrument user, the best way to help is to simply use the
system by remembering to use the :doc:`Session Logger App <session_logger_app>`
while on a microscope, and then using the NexusLIMS front-end system at
https://***REMOVED*** to search through and browse your experimental data.
Beyond that, suggestions for improvements or additional features are always
welcome by submitting a
`new issue <https://***REMOVED***nexuslims/NexusMicroscopyLIMS/issues/new>`_
at the project's code |repoLink|_.

About the logo
--------------

The logo for the NexusLIMS project is inspired by the Nobel Prize
`winning <https://www.nobelprize.org/prizes/chemistry/2011/shechtman/facts/>`__
work of `Dan
Shechtman <https://www.nist.gov/content/nist-and-nobel/nobel-moment-dan-shechtman>`__
during his time at NIST in the 1980s. Using transmission electron
diffraction, Shechtman measured an unusual diffraction pattern that
ultimately overturned a fundamental paradigm of crystallography. He had
discovered a new class of crystals known as
`quasicrystals <https://en.wikipedia.org/wiki/Quasicrystal>`__, which
have a regular structure and diffract, but are not periodic.

We chose to use Shechtman’s `first
published <https://journals.aps.org/prl/pdf/10.1103/PhysRevLett.53.1951>`__
diffraction pattern of a quasicrystal as inspiration for the NexusLIMS
logo due to its significance in the electron microscopy and
crystallography communities, together with its storied NIST heritage:

.. image:: _static/logo_inspiration.png
   :width: 85%

