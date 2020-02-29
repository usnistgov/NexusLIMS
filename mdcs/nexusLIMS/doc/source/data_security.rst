Data security in NexusLIMS
==========================

    `Last updated: February 27, 2020`

Realizing that the data produced by users on the Nexus instruments is expensive
to collect and precious to those that collected it, enormous care has been
taken in the development and implementation of NexusLIMS to ensure data
security and integrity at all stages of the LIMS pipeline. Three features of
the design guarantee redundant safeguards for users' data: (1) the credentials
used to access NIST resources, (2) the separation of all `write` operations from
the area where research data is stored (on backed-up centralized data storage),
(3) the best practices used in developing the codebase.
The following sections go into further detail about these points.

It is the developers' hope that this document will assuage some fears about
"leaving your data in someone else's hands". It explains that NexusLIMS in fact
never "takes control" of any data, and operates on a purely "read-only" basis,
so control of the researchers' data stays with the researchers.

The ``miclims`` user
++++++++++++++++++++

The first "firewall" with respect to protecting raw research data is the access
control enforced by the design of the system.
For the purposes of the NexusLIMS system, all operations that require
authentication to NIST resources (such as the calendar resource and
the centralized file system where the important data is stored), occur using
a NIST functional account named ``miclims`` (short for `Microscopy LIMS`). With
respect to the data storage on ***REMOVED***, the ``miclims`` account has the
same access rights as a regular Nexus user does from their desktop computer.
More specifically, that means that the entire NexusLIMS codebase has just
`read-only` access to the path where research data is stored (in the current
implementation: ``\\***REMOVED***\***REMOVED***\mmfnexus\``). In the unlikely
event that a mistake in the code attempted to move or delete a raw data file
from this folder, it would fail with a `Permission Error`, just as such an
operation would from a user's workstation in their office (only the microscope
computers are allowed to write to this folder).

How NexusLIMS stores data
+++++++++++++++++++++++++

Aside from the ``miclims`` user access rights, the NexusLIMS codebase never
even attempts write or move files from the MMF Nexus root folder. Instead,
any additional data that needs to be written (such as the dataset preview images
or dumps of the file metadata) is written to a
completely different directory, with a folder structure that mirrors that of
the MMF Nexus root folder. Internally, these two folders are distinguished by
two environment variables that must be set prior to running the NexusLIMS code:
``mmfnexus_path`` and ``nexusLIMS_path``, ensuring that there are no
"hard-coded" paths in the codebase that could be forgotten about if there is a
configuration change, for instance.

In the current implementation, ``mmfnexus_path`` is the path on ***REMOVED*** from above
(``./***REMOVED***/mmfnexus``). ``nexusLIMS_path`` is a parallel
folder (``./***REMOVED***/nexusLIMS/mmfnexus``) that anyone in
MML can read (so users can access JSON-formatted metadata from their raw files
and the preview images that are generated when a record is built).
Only the NexusLIMS team (and ``miclims``) has write access to this folder,
however. All session information is maintained in an SQLite database
that is contained within the ``nexusLIMS`` folder as well (currently:
``./***REMOVED***/nexusLIMS/nexuslims_db.sqlite``) -- see the
:doc:`NexusLIMS database <database>` page for more details.

Finally, because all of this data is stored on OISM-managed centralized file
storage, the data is backed up according to the standard OISM policies, and in
the event of disaster, file recovery is possible. The simple database structure
is likewise backed-up as a single file, so session information is kept secure,
as well.

With respect to the CDCS front-end instance, all XML records are backed up
after they are created, and the services powering the CDCS instance are also
backed up at least daily, meaning recovery should be possible from any
unforeseen errors. In the event of complete disaster, because the session logs
are backed up, the entire contents of the CDCS instance could be recreated from
scratch, if needed.

Development practices
+++++++++++++++++++++

The final piece of the data security ecosystem is the methodology used to
develop the backend code that handles record building and communication with
CDCS. Where possible, best-practices from the open source software development
community are enacted, so the entire codebase can be inspected at the
Gitlab |RepoLink|_, where issue tracking, feature development, and deployment
happen "out in the open." When adding features, the developers make use of a
`Test-driven Development <tdd_>`_ framework, meaning that features are fully
tested by defined test-cases prior to release. The codebase also maintains a
`"coverage"` of 100%, meaning that every line of code (with a few exceptions) is
evaluated and tested as a part of the development process, every single time
a change is made. This happens automatically using the continuous integration
features of Gitlab, ensuring that any regressions should be identified prior
to deployment. Changes to the code are not merged if they cause the coverage
percentage to decrease or any tests to fail. The current
`test coverage <../../coverage>`_ of the codebase is published as part of the
integration process, and can be viewed from anywhere on the NIST network.
Similarly, every function used in the project is documented fully, which
enables the automatic creation of detailed :doc:`API Documentation <api>`
that is ensured to be up to date every time a change is made to the code.

.. _tdd: https://en.wikipedia.org/wiki/Test-driven_development

