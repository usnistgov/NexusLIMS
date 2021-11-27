# Configuration file for the Sphinx documentation builder.
#
# This file only contains a selection of the most common options. For a full
# list see the documentation:
# http://www.sphinx-doc.org/en/master/config

# -- Path setup --------------------------------------------------------------

# If extensions (or modules to document with autodoc) are in another directory,
# add these directories to sys.path here. If the directory is relative to the
# documentation root, use os.path.abspath to make it absolute, like shown here.
#
import os
import sys
import shutil
sys.path.insert(0, os.path.abspath('../../'))
import nexusLIMS.version
from datetime import datetime
from glob import glob

# -- Project information -----------------------------------------------------

project = 'NexusLIMS'
copyright = f'{datetime.now().year}, NIST Office of Data and Informatics'
author = 'NIST Office of Data and Informatics'
numfig = True

# The full version, including alpha/beta/rc tags
release = nexusLIMS.version.__version__


# -- General configuration ---------------------------------------------------

# Add any Sphinx extension module names here, as strings. They can be
# extensions coming with Sphinx (named 'sphinx.ext.*') or your custom
# ones.
extensions = [
    'sphinx.ext.autodoc',
    'sphinx.ext.napoleon',
    'sphinx.ext.intersphinx',
    'sphinx.ext.coverage',
    'sphinx.ext.viewcode'
]

try:
    import sphinxcontrib.spelling
    extensions.append('sphinxcontrib.spelling')
except BaseException:
    pass

# Add any paths that contain templates here, relative to this directory.
templates_path = ['_templates']

# The suffix of source filenames.
source_suffix = '.rst'
highlight_language = 'python'
today = ""
pygments_style = 'sphinx'
add_function_parentheses = True
# master_doc = 'index'

# # LXML does not use sphinx, so if you want to link to specific page,
# # you have to create a custom objects.inv file for that module
#   To do this, use the
# # example below to add the specific objects and links as needed (this
# # method from https://sphobjinv.readthedocs.io/en/latest/customfile.html)

#     import sphobjinv as soi
#     inv = soi.Inventory()
#     inv.project = 'lxml'
#     inv.version = lxml.__version__
#     o = soi.DataObjStr(name='lxml.etree._XSLTResultTree', domain='py',
#     role='class', priority='1', uri='xpathxslt.html#xslt', dispname='-')
#     inv.objects.append(o)
#     text = inv.data_file(contract=True)
#     ztext = soi.compress(text)
#     soi.writebytes('***REMOVED***NexusMicroscopyLIMS/mdcs/nexusLIMS/'
#                    'doc/source/objects_lxml.inv', ztext)

intersphinx_mapping = {'python': ('https://docs.python.org/3.7/', None),
                       'dateparser': (
                           'https://dateparser.readthedocs.io/en/latest/',
                           None),
                       'hyperspy': (
                           'http://hyperspy.org/hyperspy-doc/current/', None),
                       'numpy': (
                           'https://numpy.org/doc/stable/', None),
                       'matplotlib': ('https://matplotlib.org/', None),
                       'requests': (
                           'https://docs.python-requests.org/en/latest/',
                           None),
                       'PIL': (
                           'https://pillow.readthedocs.io/en/stable/',
                           None),
                       'pytz': ('http://pytz.sourceforge.net/',
                                'pytz_objects.inv'),
                       # use the custom objects.inv file above for LXML:
                       'lxml': ('https://lxml.de/', 'objects_lxml.inv'),
                       }

import sphinx_bootstrap_theme
# Activate the theme.
html_theme = 'bootstrap'
html_theme_path = sphinx_bootstrap_theme.get_html_theme_path()


# List of patterns, relative to source directory, that match files and
# directories to ignore when looking for source files.
# This pattern also affects html_static_path and html_extra_path.
exclude_patterns = [
    '.git',
    '_build',
    'Thumbs.db',
    '.DS_Store',
    'build',
#    'api/nexusLIMS.rst',
    'api/nexusLIMS.version.rst',
    'README.rst',
    'dev_scripts'
]

# Keep warnings as “system message” paragraphs in the built documents.
# useful for easily seeing where errors are in the build files
keep_warnings = True


# -- Options for HTML output -------------------------------------------------

# The theme to use for HTML and HTML Help pages.  See the documentation for
# a list of builtin themes.
#

# Add any paths that contain custom static files (such as style sheets) here,
# relative to this directory. They are copied after the builtin static files,
# so a file named "default.css" will overwrite the builtin "default.css".
html_static_path = ['_static']

html_css_files = [
    'custom-styles.css',
]

html_js_files = [
    'custom.js',
]

# html_title = "NexusLIMS documentation"
html_short_title = "NexusLIMS"
html_logo = "_static/logo_horizontal.png"
html_favicon = "_static/nexusLIMS_bare_logo.ico"
html_last_updated_fmt = '%b, %d, %Y'
html_use_smartypants = True
html_show_sourcelink = True
html_show_sphinx = False
html_show_copyright = True

html_extra_path = ['schema_doc']

# html_sidebars = {'**': ['localtoc.html', 'sourcelink.html', 'searchbox.html']}
html_sidebars = {'**': ['custom-sidebar.html',
                        'localtoc.html',
                        'searchbox.html',
                        'sourcelink.html']}


html_theme_options = {
    # Navigation bar title. (Default: ``project`` value)
    'navbar_title': " ",

    # Tab name for entire site. (Default: "Site")
    'navbar_site_name': "Site Map",

    # A list of tuples containing pages or urls to link to.
    # Valid tuples should be in the following forms:
    #    (name, page)                 # a link to a page
    #    (name, "/aa/bb", 1)          # a link to an arbitrary relative url
    #    (name, "http://example.com", True) # arbitrary absolute url
    # Note the "1" or "True" value above as the third argument to indicate
    # an arbitrary url.
    'navbar_links': [
        ("API Docs", 'api'),
        ("Repository",
         "https://***REMOVED***nexuslims/NexusMicroscopyLIMS", True),
        ("NIST ODI", "https://www.nist.gov/mml/odi", True),
    ],

    # Render the next and previous page links in navbar. (Default: true)
    'navbar_sidebarrel': True,

    # Render the current pages TOC in the navbar. (Default: true)
    'navbar_pagenav': False,

    # Tab name for the current pages TOC. (Default: "Page")
    'navbar_pagenav_name': "Page",

    # Global TOC depth for "site" navbar tab. (Default: 1)
    # Switching to -1 shows all levels.
    'globaltoc_depth': -1,

    # Include hidden TOCs in Site navbar?
    #
    # Note: If this is "false", you cannot have mixed ``:hidden:`` and
    # non-hidden ``toctree`` directives in the same page, or else the build
    # will break.
    #
    # Values: "true" (default) or "false"
    'globaltoc_includehidden': "true",

    # HTML navbar class (Default: "navbar") to attach to <div> element.
    # For black navbar, do "navbar navbar-inverse"
    # 'navbar_class': "navbar navbar-inverse",
    'navbar_class': "navbar",

    # Fix navigation bar to top of page?
    # Values: "true" (default) or "false"
    'navbar_fixed_top': "true",

    # Location of link to source.
    # Options are "nav" (default), "footer" or anything else to exclude.
    'source_link_position': "footer",

    # Bootswatch (http://bootswatch.com/) theme.
    #
    # Options are nothing (default) or the name of a valid theme
    # such as "cosmo" or "sandstone".
    #
    # The set of valid themes depend on the version of Bootstrap
    # that's used (the next config option).
    #
    # Currently, the supported themes are:
    # - Bootstrap 2: https://bootswatch.com/2
    # - Bootstrap 3: https://bootswatch.com/3
    'bootswatch_theme': "lumen",

    # Choose Bootstrap version.
    # Values: "3" (default) or "2" (in quotes)
    'bootstrap_version': "3",
}

rst_epilog = """
.. |SQLSchemaLink| replace:: SQL Schema Definition
.. _SQLSchemaLink: https://***REMOVED***nexuslims/NexusMicroscopyLIMS/blob/master/mdcs/nexusLIMS/nexusLIMS/db/NexusLIMS_db_creation_script.sql
.. |RepoLink| replace:: repository
.. _RepoLink: https://***REMOVED***nexuslims/NexusMicroscopyLIMS
.. |dbloggerLink| replace:: ``db_logger_gui.py``
.. _dbloggerLink: https://***REMOVED***nexuslims/NexusMicroscopyLIMS/-/blob/master/mdcs/nexusLIMS/nexusLIMS/db/db_logger_gui/db_logger_gui.py
.. |makedbentryLink| replace:: ``make_db_entry.py``
.. _makedbentryLink: https://***REMOVED***nexuslims/NexusMicroscopyLIMS/-/blob/master/mdcs/nexusLIMS/nexusLIMS/db/db_logger_gui/make_db_entry.py
.. |specfileLink| replace:: ``db_logger_gui.spec``
.. _specfileLink: https://***REMOVED***nexuslims/NexusMicroscopyLIMS/-/blob/master/mdcs/nexusLIMS/nexusLIMS/db/db_logger_gui/db_logger_gui.spec
.. |testsLink| replace:: ``tests``
.. _testsLink: https://***REMOVED***nexuslims/NexusMicroscopyLIMS/-/tree/master/mdcs/nexusLIMS/nexusLIMS/tests
"""


# api-doc autogeneration adapted from
# https://github.com/isogeo/isogeo-api-py-minsdk/blob/master/docs/conf.py
def run_apidoc(_):
    from sphinx.ext.apidoc import main

    cur_dir = os.path.normpath(os.path.dirname(__file__))
    output_path = os.path.join(cur_dir, 'api')
    shutil.rmtree(output_path, ignore_errors=True)
    modules = os.path.normpath(os.path.join(cur_dir, "../../nexusLIMS"))
    to_exclude = list(glob(os.path.join(modules, 'dev_scripts') + '/**/*',
                           recursive=True))
    # exclude db_logger_gui files from autodoc
    to_exclude += list(glob(os.path.join(modules, 'db', 'db_logger_gui', '*')))
    # to_exclude += list(glob(os.path.join(modules, 'db', 'migrate_db.py')))
    # to_exclude += [os.path.join(modules, 'builder')]
    main(['-f', '-M', '-T', '-d', '-1', '-o', output_path, modules] +
         to_exclude)


# def build_plantuml(_):
#     from glob import glob
#     from plantuml import PlantUML
#     pl = PlantUML('http://www.plantuml.com/plantuml/img/')
#     cur_dir = os.path.normpath(os.path.dirname(__file__))
#     diagrams = os.path.join(cur_dir, 'diagrams')
#     output_path = os.path.join(cur_dir, '_static')
#     for f in glob(os.path.join(diagrams, '*uml')):
#         print(f)
#         out_name = os.path.splitext(os.path.basename(f))[0] + '.png'
#         out_f_path = os.path.join(output_path, out_name)
#         pl.processes_file(f, outfile=out_f_path)


# lines from intersphinx to ignore during api-doc autogeneration (so we don't
# get useless warning messages while the docs are being built
nitpick_ignore = [('py:class', 'function'),
                  ('py:class', 'optional'),
                  ('py:class', 'json.encoder.JSONEncoder')]


def skip(app, what, name, obj, would_skip, options):
    if name == "__init__":
        return False
    return would_skip


def setup(app):
    # app.connect("autodoc-skip-member", skip)
    app.connect('builder-inited', run_apidoc)
    # app.connect('builder-inited', build_plantuml)
    print('If you need to update the PlantUML diagrams, run\n'
          'build_plantuml.sh in this directory')
    # app.add_stylesheet("custom-styles.css")
