from nexusLIMS.version import __version__
from distutils.version import StrictVersion


class TestVersion:
    def test_version_number(self):
        # if distutils can parse the version number, we'll assume it's valid
        StrictVersion(__version__)
