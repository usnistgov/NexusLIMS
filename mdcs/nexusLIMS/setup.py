from setuptools import setup, find_packages
from os import path
import io
import re

here = path.abspath(path.dirname(__file__))

# Get the long description from the relevant file
# with open(path.join(here, 'README.rst'), encoding='utf-8') as f:
#     long_description = f.read()


# next two methods read version from file
def read(*names, **kwargs):
    with io.open(
        path.join(path.dirname(__file__), *names),
        encoding=kwargs.get("encoding", "utf8")
    ) as fp:
        return fp.read()


def find_version(*file_paths):
    version_file = read(*file_paths)
    version_match = re.search(r"^__version__ = ['\"]([^'\"]*)['\"]",
                              version_file, re.M)
    if version_match:
        return version_match.group(1)
    raise RuntimeError("Unable to find version string.")


setup(
    name='nexusLIMS',

    # Versions should comply with PEP440.  For a discussion on single-sourcing
    # the version across setup.py and the project code, see
    # https://packaging.python.org/en/latest/single_source_version.html
    version=find_version('nexusLIMS/version.py'),

    description='The NIST Electron Microscopy Nexus LIMS project',
    long_description='Metadata harvesting and XML record builder for the EM '
                     'Nexus Facility',

    # The project's main homepage.
    url='https://***REMOVED***/sites/staff/mml-lims-pilot/'
        'SitePages/Home.aspx',

    # Author details
    author='NIST MML Office of Data and Informatics',
    author_email='AskODI@nist.gov',

    # Choose your license
    license='custom',

    # See https://pypi.python.org/pypi?%3Aaction=list_classifiers
    classifiers=[
        # How mature is this project? Common values are
        #   3 - Alpha
        #   4 - Beta
        #   5 - Production/Stable
        'Development Status :: 3 - Alpha',

        # Indicate who your project is intended for
        'Intended Audience :: Science/Research',
        'Topic :: Scientific/Engineering',

        # Specify the Python versions you support here. In particular, ensure
        # that you indicate whether you support Python 2, Python 3 or both.
        'Programming Language :: Python :: 3.7'
    ],

    # What does your project relate to?
    keywords='electronmicroscopy datamanagement information metadata schema',

    # You can just specify the packages manually here if your project is
    # simple. Or you can use find_packages().
    packages=['nexusLIMS', 'nexusLIMS.cal_harvesting', 'nexusLIMS.extractors'],

    # List run-time dependencies here.  These will be installed by pip when your
    # project is installed. For an analysis of "install_requires" vs pip's
    # requirements files see:
    # https://packaging.python.org/en/latest/requirements.html
    install_requires=['lxml',
                      'requests',
                      'requests-ntlm',
                      'ntlm-auth',
                      'dateparser',
                      'pynoid @ git+https://github.com/***REMOVED***/pynoid@master',
                      'hyperspy'],

    # List additional groups of dependencies here (e.g. development
    # dependencies). You can install these using the following syntax,
    # for example:
    #    $ pip install -e .[dev,test]
    extras_require={
        'devel': ['coverage',
                  'pytest',
                  'pytest-cov',
                  'sphinx'
                  ]
    },

    # required to include additional resource files in the package
    include_package_data=True,
)
