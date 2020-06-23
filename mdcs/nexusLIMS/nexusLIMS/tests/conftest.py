#  NIST Public License - 2020
#
#  This software was developed by employees of the National Institute of
#  Standards and Technology (NIST), an agency of the Federal Government
#  and is being made available as a public service. Pursuant to title 17
#  United States Code Section 105, works of NIST employees are not subject
#  to copyright protection in the United States.  This software may be
#  subject to foreign copyright.  Permission in the United States and in
#  foreign countries, to the extent that NIST may hold copyright, to use,
#  copy, modify, create derivative works, and distribute this software and
#  its documentation without fee is hereby granted on a non-exclusive basis,
#  provided that this notice and disclaimer of warranty appears in all copies.
#
#  THE SOFTWARE IS PROVIDED 'AS IS' WITHOUT ANY WARRANTY OF ANY KIND,
#  EITHER EXPRESSED, IMPLIED, OR STATUTORY, INCLUDING, BUT NOT LIMITED
#  TO, ANY WARRANTY THAT THE SOFTWARE WILL CONFORM TO SPECIFICATIONS, ANY
#  IMPLIED WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE,
#  AND FREEDOM FROM INFRINGEMENT, AND ANY WARRANTY THAT THE DOCUMENTATION
#  WILL CONFORM TO THE SOFTWARE, OR ANY WARRANTY THAT THE SOFTWARE WILL BE
#  ERROR FREE.  IN NO EVENT SHALL NIST BE LIABLE FOR ANY DAMAGES, INCLUDING,
#  BUT NOT LIMITED TO, DIRECT, INDIRECT, SPECIAL OR CONSEQUENTIAL DAMAGES,
#  ARISING OUT OF, RESULTING FROM, OR IN ANY WAY CONNECTED WITH THIS SOFTWARE,
#  WHETHER OR NOT BASED UPON WARRANTY, CONTRACT, TORT, OR OTHERWISE, WHETHER
#  OR NOT INJURY WAS SUSTAINED BY PERSONS OR PROPERTY OR OTHERWISE, AND
#  WHETHER OR NOT LOSS WAS SUSTAINED FROM, OR AROSE OUT OF THE RESULTS OF,
#  OR USE OF, THE SOFTWARE OR SERVICES PROVIDED HEREUNDER.
#
import tarfile
import os
from nexusLIMS.tests.utils import tars, files
from datetime import datetime as _dt
from datetime import timedelta as _td
from datetime import timezone as _tz
import time
import pytest
import nexusLIMS.utils

# we don't want to mask both directories, because the record builder tests
# need to look at the real files on ***REMOVED***:
# os.environ['nexusLIMS_path'] =os.path.join(os.path.dirname(__file__), 'files')
# os.environ['mmfnexus_path'] = os.path.join(os.path.dirname(__file__), 'files')

# use our test database for all tests (don't want to impact real one)
os.environ['nexusLIMS_db_path'] = files['DB'][0]


def pytest_configure(config):
    """
    Allows plugins and conftest files to perform initial configuration.
    This hook is called for every plugin and initial conftest
    file after command line options have been parsed.

    Unpack the test_db at the very beginning since we need it right away
    when importing the instruments.py module (for instrument_db)
    """
    with tarfile.open(tars['DB'], 'r:gz') as tar:
        tar.extractall(path=os.path.dirname(tars['DB']))


def pytest_sessionstart(session):
    """
    Called after the Session object has been created and
    before performing collection and entering the run test loop.

    Unpack the compressed test files.
    """
    for _, tarf in tars.items():
        with tarfile.open(tarf, 'r:gz') as tar:
            tar.extractall(path=os.path.dirname(tarf))


def pytest_sessionfinish(session, exitstatus):
    """
    Called after whole test run finished, right before
    returning the exit status to the system.

    Remove the unpacked test files.
    """
    for _, fn_list in files.items():
        for fn in fn_list:
            os.remove(fn)


@pytest.fixture(scope='session')
def monkey_session():
    from _pytest.monkeypatch import MonkeyPatch
    mpatch = MonkeyPatch()
    yield mpatch
    mpatch.undo()


@pytest.fixture(scope='session')
def fix_mountain_time(monkey_session):
    """
    Hack to determine if we need to adjust our datetime objects for the time
    difference between Boulder and G'burg
    """
    def currenttz():
        if time.daylight:
            return _tz(_td(seconds=-time.altzone), time.tzname[1])
        else:   # pragma: no cover
            return _tz(_td(seconds=-time.timezone), time.tzname[0])

    tz_string = currenttz().tzname(_dt.now())

    # if timezone is MST or MDT, we're 2 hours behind, so we need to adjust
    # datetime objects to match file store
    if tz_string in ['MST', 'MDT']:
        # get current timezone, and adjust tz_offset as needed
        monkey_session.setattr(nexusLIMS.utils, "tz_offset",
                            _td(hours=-2))
        monkey_session.setenv('ignore_mib', 'True')
        monkey_session.setenv('is_mountain_time', 'True')
