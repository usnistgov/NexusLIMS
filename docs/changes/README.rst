This directory contains "news fragments" which are short files that contain a
small **ReST**-formatted text that will be added to the next change log.

The changelog will be read by **users**, so this description should be aimed to
users instead of describing internal changes which are only relevant to the developers.

Each file should be named like ``<ISSUE>.<TYPE>.rst``, where
``<ISSUE>`` is an issue or merge/pull request number, and ``<TYPE>`` is one of:

* ``feature``: new user facing features, like new command-line options and new behavior.
* ``bugfix``: fixes a bug.
* ``doc``: documentation improvement, like rewording an entire session or adding
           missing docs.
* ``removal``: feature deprecation or removal.
* ``misc``: a change related to the test suite, packaging, etc. probably not of
            interest to regular users

So for example ``1412.feature.rst`` or ``2773.bugfix.rst``.

If your pull/merge request fixes an issue, use the number of the issue here. If there
is no issue, then after you submit the PR and get the PR number you can add a changelog
using that instead.

If you are not sure what issue type to use, don't hesitate to ask in your PR.

``towncrier`` preserves multiple paragraphs and formatting (code blocks, lists, and
so on), but for entries other than ``new`` it is usually better to stick to a single
paragraph to keep it concise.

Multiple

To see what would be written, make a draft of the changelog by running from the
command line:

   .. code-block:: bash

       $ towncrier build --draft

See https://towncrier.readthedocs.io/ for more details.

.. note: 

    This file was mostly copied from 
    https://github.com/hyperspy/hyperspy/blob/RELEASE_next_minor/upcoming_changes/README.rst)