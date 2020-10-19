:tocdepth: 3

Tips for customizing CDCS
=========================

    `Originally written by: Joshua Taillon -- ODI`

    `Last updated: November 15, 2019`

The front-end for `NexusLIMS` is powered by the Configurable Data Curation
System -- CDCS_. CDCS is a project originating from the Materials Genome
Initiative (MGI) that provides a fully customizable platform with which to
collect, organize, query, and disseminate scientific data. The data is fed into
the system as individual `records` that must conform with a `template`
(expressed using XML Schema). The records can then be searched and displayed
using a customized `XSLT` stylesheet (eXtensible Stylesheet Language
Transformations). These stylesheets can incorporate any arbitrary HTML and
javascript, giving great control over what content is ultimately displayed to
the end user when he or she opens a record.

.. _CDCS: https://www.nist.gov/itl/ssd/information-systems-group/configurable-data-curation-system-cdcs

Overview
++++++++

On the technical side, CDCS is implemented in Python using the Django framework
and MongoDB for record storage in a NoSQL database. In addition to the actual
record display that can be customized via XSLT, the Django framework allows
any part of the entire CDCS application to be customized by overriding or
changing the default `templates` (see `here <DjangoTemplates_>`_ for more
documentation on Django templates). Through this mechanism, any part of the
application can be modified as needed.

.. _DjangoTemplates: https://docs.djangoproject.com/en/2.2/topics/templates/

The specific implementation of CDCS used for `NexusLIMS` is stored in a
`forked version <NexusLIMSCDCSRepo_>`_ of the `upstream` CDCS
`repository <CDCSRepo_>`_ available on the internal NIST Gitlab. CDCS is
comprised of many individual Django `apps` (or `modules` -- see
`here <CDCSModules_>`_ for a complete list), that each control a different part
or function of the overall application. For example, the
``core_explore_keyword_app`` controls the display of the data "search by
keyword" page.

.. _CDCSModules: https://www.nist.gov/itl/ssd/information-systems-group/cdcs-system-modules
.. _NexusLIMSCDCSRepo: https://gitlab.nist.gov/gitlab/nexuslims/nexuslims-cdcs
.. _CDCSRepo: https://github.com/usnistgov/MDCS

Installation
++++++++++++

General documentation for the installation of CDCS is available from the
`documentation site <CDCSdocs_>`_ of CDCS itself. The easiest way to install
however, is using the Docker method, supplied by the developers of CDCS. The
files for this can be obtained by `contacting <CDCScontact_>`_ the developers
directly, or by going to the `NexusLIMS repository <NexusLIMSdocker_>`_ that
holds instructions for installing the `NexusLIMS`-customized version (follow the
instructions in the ``README.md`` file contained in that repository). If you
proceed with the files from the `NexusLIMS` repository, the resulting product
will contain all the `NexusLIMS` changes, rather than the default look-and-feel
written by the CDCS developers (and as a result, will look just like
`NexusLIMS`).

.. _CDCSdocs: https://www.nist.gov/itl/ssd/information-systems-group/configurable-data-curation-system-cdcs/cdcs-help-and-resources
.. _CDCScontact: https://www.nist.gov/itl/ssd/information-systems-group/configurable-data-curation-system-cdcs/contact-cdcs
.. _NexusLIMSdocker: https://gitlab.nist.gov/gitlab/nexuslims/nexuslims-cdcs-docker-setup/tree/master

After setting up an installation of CDCS (assuming an `MDCS` install rather than
a `registry` install), there will be a few directories within the top-level
folder displayed by the web server that can contain customizations. If the
installation was performed using the `docker method <NexusLIMSdocker_>`_,
then this top-level folder is the ``/srv/curator`` directory in the
``mdcs_cdcs_1`` container. This can be accessed by telling docker to execute
an interactive ``bash`` shell within the container from your host system:

..  code:: bash

    docker exec -it mdcs_cdcs_1 bash

..  admonition:: A development tip...

    Microsoft's [1]_ freely-available `Visual Studio Code <VSCode_>`_
    supports connecting to existing Docker containers and editing the files
    inside that container on-the-fly. This makes rapid prototyping significantly
    easier, as you can edit files within the container using modern IDE tools
    and see the impact of certain changes in realtime. See the
    `documentation <VSCodeContainerDocs_>`_ of the container features in VS Code
    for more detail. `This <VSCodeContainerRemoteDocs_>`_ page also describes
    how to connect to a container that may be on an SSH-accessible remote host.


.. _VSCode: https://code.visualstudio.com/
.. _VSCodeContainerDocs: https://code.visualstudio.com/docs/remote/containers
.. _VSCodeContainerRemoteDocs: https://code.visualstudio.com/docs/remote/containers-advanced#_developing-inside-a-container-on-a-remote-docker-host

Since CDCS is a Django application, the structure will be familiar to anyone
that has done Django development previously. The ``templates`` folder contains
the HTML-format Django templates that are used to construct the pages, the
``static`` folder contains various `static` resources (such as images, CSS
files, javascript files, etc.) that can be accessed from anywhere on the site,
and ``mdcs_home`` is the "homepage" app that is designed to allow easy
customization of a few high-level CDCS elements. The following sections go into
each of these in more detail. To view the specific changes that were made,
the `NexusLIMS` CDCS `git commit history <nexuslimsCDCSGitCommits_>`_ will show
every change in detail from what is provided in the default CDCS installation.

.. _nexuslimsCDCSGitCommits: https://gitlab.nist.gov/gitlab/nexuslims/nexuslims-cdcs/commits/NexusLIMS_master

General tips
++++++++++++

A couple general strategies help when trying to customize various pieces of the
CDCS installation. It is common not to know where to look when trying to change
a piece of text or the structure of a section, since the application is split
into many different Django `apps` (Python modules) that are all included as part
of the default installation. The only `app` immediately visible from the
root directory of ``/srv/curator`` is the ``mdcs_home`` app. The others (at
least in the docker-installed version -- listed `here <CDCSModules_>`_) are
located in the ``/usr/local/lib/python3.6/site-packages`` folder holding the
libraries for the system-level Python installation.

The easiest way to determine what needs to be changed is to use the
`find in files` feature supplied by most modern code editors/IDEs. After making
sure both the ``/srv/curator`` and ``site-packages`` directories are included
in the search, enter the text (from the website) that you wish to change, and
you should be able to narrow down what specific file is controlling that
display. For non-text or other elements, you can use your web browser's
`inspect` feature (usually found by right-clicking on a certain item) to find
an element's HTML `id`, `name`, or `class`, which can be used as above to find
the file providing that element. If the file you find is within the
``site-packages`` folder, you will need to
`override <DjangoOverridingTemplates_>`_ that template, rather than making
changes directly to the file (see the templates_ section for more detail).

Once you make any changes to the files inside ``/srv/curator``, you will need
to reload Django in order to show any of those changes. This can be done by
restarting the Docker container, or you can get Django to restart itself
automatically by "touching" a special file in the ``mdcs`` directory:

..  code:: bash

    # run from within the mdcs_cdcs_1 docker container:
    touch /srv/curator/mdcs/wsgi.py

.. _DjangoOverridingTemplates: https://docs.djangoproject.com/en/2.2/howto/overriding-templates/#overriding-templates

The ``static`` folder
+++++++++++++++++++++

.. _static:

The ``static`` folder contains resources that can be used on any page within
the Django application, such as images, javascript, CSS style definitions,
individual files to serve, etc.
(see documentation about the concept of static files in Django
`here <DjangoStatic_>`_). For quick customizations, a few files in
particular are good to know about. ``./static/css/extra.css`` is sourced on
every page within the application, and this is a good place to put any custom
style definitions. Some example changes that we made to this file were
modifying the spacing between items, changing item colors, etc. Changes can
also be made to ``./static/css/main.css``, but keeping all modifications in one
file will help make maintenance on these settings easier.

Simply changing or placing files into the ``static`` directory will not
immediately make them visible, since we have to instruct Django to "collect"
these files. This is because Django serves the static files out of a different
directory (at least in the Docker-installed version) named ``static.prod``.
You can either manually copy any changed files into the ``static.prod``
directory (after logging into the docker container with
``docker exec -it mdcs_cdcs_1 bash``) with a command like:

..  code:: bash

    cp -R /srv/curator/static/* /srv/curator/static.prod/

Or you can instruct Django to do this for you (the recommended method) using
the |DjangoCollectStatic|_. From the ``/srv/curator`` directory inside
the ``mdcs_cdcs_1`` container, run the following:

.. |DjangoCollectStatic| replace:: ``collectstatic`` command
.. _DjangoCollectStatic: https://docs.djangoproject.com/en/2.2/ref/contrib/staticfiles/
.. _DjangoStatic: https://docs.djangoproject.com/en/2.2/howto/static-files/

..  _collectStatic:

..  code:: bash

    python manage.py collectstatic -c --noinput

This may take a little bit of time depending on how many files you have, but the
command will completely clear the ``static.prod`` folder, and copy all the files
you placed in the ``static`` folder into the right place.

To actually use the files that are in the ``static`` folder, you will need
to use the ``static`` `template tag` (documented
`here <DjangoStaticTemplateTag_>`_) within your templates. `Template tags` are
specially-formatted bits of code that Django parses within the HTML templates
that allow for dynamic content (see the next section). Template tags in Django
are signified using curly braces and percent symbols ``{% ... %}`` followed by
whichever tag you want to use. As an example, you would use the following
syntax to include an image stored at ``/srv/curator/static/img/example.jpg``
from within a Django template:

..  code:: django

    <img src="{% static "img/example.jpg" %}" alt="My image">

If you peruse around the included templates in the ``templates`` folder, you
will see this syntax all over, for example in  ``<script>`` elements
(for including javascript), ``<style>`` elements (to include ``.css`` files),
images, etc.

..  _DjangoStaticTemplateTag: https://docs.djangoproject.com/en/2.2/ref/templates/builtins/#std:templatetag-static

The ``templates`` folder
++++++++++++++++++++++++

.. _templates:

Intro to Django templates
_________________________

While this section will not be a definitive introduction to Django's templating
system (see the `official docs <DjangoTemplatesDocs_>`_ for more detail), it
should provide enough instruction that you understand how the pieces of the
different pieces come together to make your own customizations. Django templates
(a different concept than the CDCS/XML Schema templates mentioned at the
beginning of this document) are text files that Django uses to dynamically
generate another file (such as html) using content controlled by `variables`,
`tags`, and `filters` (the ``static`` template tag was introduced above).
You can also define `blocks` in a template, which can then be re-used throughout
the application.

A simple example of this in practice is the ``if`` tag. Together with tags such
as ``for``, you can control the logic within a template as you would in any
other programming language, to dynamically generate the content that is
ultimately displayed to the user. Consider the following example (copied from
the Django documentation):

..  code:: django

    {% if athlete_list %}
        Number of athletes: {{ athlete_list|length }}
    {% elif athlete_in_locker_room_list %}
        Athletes should be out of the locker room soon!
    {% else %}
        No athletes.
    {% endif %}

In this example, the ``{% if ... %}`` tag checks a variable (``athlete_list``),
and if it evaluates to true, displays a certain content, and displays
something else if not. This branching and flow-control capability allows
templates to be much more flexible than a regular HTML page.

The other tag that you will see used frequently is the ``{% extends ... %}``
tag (docs `here <DjangoTemplateInheritanceDocs_>`_). This tag allows templates
to inherit from each other by including "child" templates (defined in a separate
file) within a "parent" template. Whenever you see an ``extend`` tag, you know
that you are viewing a template that is a child of another template, and using
that knowledge, you can work "up the chain" to see how all the templates
are used together to generate the entire document that is finally displayed to
the user.

These basic tools are good to understand when working with the CDCS templates,
as they provide the building blocks required to start making your own
customizations.

..  _DjangoTemplatesDocs: https://docs.djangoproject.com/en/2.2/ref/templates/language/
..  _DjangoTemplateInheritanceDocs: https://docs.djangoproject.com/en/2.2/ref/templates/language/#template-inheritance

Working with the CDCS templates
_______________________________

Changing the default files
**************************

**theme.html:**

Within the ``/srv/curator`` directory, the ``templates`` folder by default
contains a few files that can be modified to make some basic customizations.
For example, the ``templates/theme.html`` file contains block definitions that
are placed into the header of the HTML pages, and thus is where you can update
values such as the page metadata (with ``<meta>`` elements), the page title,
and including any additional CSS style or javascript files. If you have a new
file that you want to include, simply place the file into the ``static``
directory and follow the pattern used in this file to make sure it is linked on
all the pages of your CDCS instance (remembering that you will need to run the
|collectstatic|_ command from above.

.. |collectstatic| replace:: ``collectstatic``

**menu.html and footer/default.html:**

Within the ``templates/theme.html`` file, you will also see a few other files
referenced that you can edit to make changes as well. These include the top
menu template (``templates/theme/menu.html``) and the footer template
(``templates/theme/footer/default.html``). As you might expect, these files can
similarly be modified as needed. For example, on the `NexusLIMS` page, the block

..  code:: django

    <div id="cdcs-menu-title">
        <a href="https://cdcs.nist.gov/" title="Configurable Data Curation System (CDCS)">
            Materials Data Curation System
        </a>
    </div>

in ``templates/theme/menu.html`` was replaced by

..  code:: django

    <div id="cdcs-menu-title">
        <a href="/" title="NexusLIMS">
            <img src="{% static 'img/logo_horizontal.png' %}"/>
        </a>
    </div>

This small modification changed the left link in the top menu bar from text
saying "Materials Data Curation System" (linking to the CDCS homepage) to an
image of the project's logo (placed in the ``static`` folder) that will always
bring the user back to the homepage of the `NexusLIMS` CDCS instance. Likewise,
the `NexusLIMS` project did not require the drop-down menus for data exploration
and data composition that are included by default, so they were simply commented
out of the ``templates/theme/menu.html`` template. Similarly, some small changes
were made to ``templates/theme/footer/default.html`` to meet the project's
design needs.

**core_main_app/user/homepage.html:**

The "homepage" template located at
``templates/core_main_app/user/homepage.html`` is an example of a template
override (explained in the next section), but is provided by default by CDCS
since it is a commonly changed feature. This template controls the content
(but not the header or footer, since those are defined elsewhere) of the very
first page that is displayed to users when they visit the site's root. By
default, this shows some text about CDCS and a figure describing the MGI.
It also defines two columns for `tiles` and `templates`, which are then filled
out later on in the page loading by javascript defined in the
``static/core_main_app/js/homepage.js`` file. In the `NexusLIMS`
CDCS instance, the template list was commented out, and the text/logo were
modified to be more appropriate. `Note:` you do not have to keep this structure,
and the homepage can be defined in any way you choose.

..  admonition:: A note on page layouts...

    The page content throughout CDCS is laid out using (currently) version
    3.3.7 of the `Bootstrap <BootstrapDocs_>`_ web framework. This is a very
    commonly used framework that provides tools to generate mobile-responsive
    pages using a set of standard rows and columns (along with other
    components). Thus, throughout the templates, you will see content wrapped
    in ``<div>`` elements that have either the ``row`` or ``col-**-#`` classes.
    These are classes that are part of Bootstrap that control how the content
    is laid out on different-sized devices (see the `docs <BootstrapCSSDocs_>`_
    for more detail).

.. _BootstrapDocs: https://getbootstrap.com/docs/3.3/
.. _BootstrapCSSDocs: https://getbootstrap.com/docs/3.3/css/

**mdcs_home/tiles.html:**

..  _tiles_template:

This file (together with the ``templates.html`` file below) control what is
shown on the bottom portion of the CDCS homepage. The `tiles` are the links
that are shown on the left side with content such as
"`Curate your Materials Data`", "`Build your own queries`", etc. ``tiles.html``
controls the overall display of these links, but the actual content of the tiles
is controlled by the ``/srv/curator/mdcs_home/views.py`` file (see the
|mdcs_home|_ section for more details).

.. |mdcs_home| replace:: ``mdcs_home``

..  admonition:: A note on those icons...

    Throughout CDCS you will notice icons on most buttons (`e.g.` the tiles,
    the `Log In/Sign Up` button, etc.) that are not included in the ``static``
    folder as you might expect. These icons are provided by the
    `Font Awesome <FontAwesome_>`_ framework (v. 4.7), which (like Bootstrap) is
    very commonly used throughout the web. The previous link will show all the
    icons that are available to use, which can be included at any point in your
    HTML templates by using an ``<i>`` element with the appropriate classes
    attached. For example, to display a camera icon, you would use the syntax
    ``<i class="fa fa-camera-retro"></i>``. The ``fa`` "activates" the Font
    Awesome framework, and then the ``fa-camera-retro`` indicates which specific
    icon to use. There are many more options that can be provided, but know that
    when you see ``fa-*`` in the CDCS sources, this indicates some sort of icon
    from the Font Awesome library (see the `documentation <FontAwesomeDocs_>`_
    for more detail).

..  _FontAwesome: https://fontawesome.com/v4.7.0/icons/
..  _FontAwesomeDocs: https://fontawesome.com/v4.7.0/examples/

**mdcs_home/templates.html:**

Like the ``tiles.html`` file, this template controls what is shown underneath
the welcome message on the CDCS homepage. By default, it loops through the
installed `XML Schema` templates that have been loaded into CDCS and displays
them to the user. This was not needed for the `NexusLIMS` project, and so was
commented out entirely.

Overriding other CDCS templates
*******************************

Inspecting the directory structure of the ``templates`` folder in the
`NexusLIMS` CDCS `repository <NexusLIMSCDCSRepo>`_, you will notice a few more
folders in the customized version than the default. All the added templates in
`NexusLIMS` are overrides of the ones included in the default CDCS modules
(such as ``core_explore_common_app`` and ``core_explore_keyword_app``). As
mentioned previously, these are included because there were files contained
within the ``site-packages`` folder that needed to be changed. By copying those
files into the root structure (making sure to maintain relative paths), it is
possible to override the default versions. An example is probably most
helpful:

The "root" template that is used to load most of the high-level page structure
is present by default at:

..  raw:: html

    <div class="highlight-bash notranslate">
        <div class="highlight">
            <pre>/usr/local/lib/python3.6/site-packages/core_main_app/<span style='color:#158cba;'>templates/core_main_app/_render/user/theme_base.html</span></pre>
        </div>
    </div>


For `NexusLIMS`, a few changes were required to this file, so it was copied
into:

..  raw:: html

    <div class="highlight-bash notranslate">
        <div class="highlight">
            <pre>/srv/curator/<span style='color:#158cba;'>templates/core_main_app/_render/user/theme_base.html</span></pre>
        </div>
    </div>

(note that the ``templates/core_main_app/_render/user/`` relative path is
maintained; this is how Django knows that this file is supposed to override
the default one from the ``site-packages`` folder). Once this file was copied
to the local directory, some slight changes were made to enable additional
functionality on the record display pages. For example, an additional javascript
library was needed for interactive table displays
(`DataTables.js <DataTables_>`_), so to make sure this was loaded properly, it
was necessary to make changes to the page headers to include both the library's
CSS and JS files (which had been copied into the ``static`` folder). Note, these
inclusions likely could have also been included in the ``templates/theme.html``
file under the blocks ``theme_css`` and ``theme_js``, in retrospect. The other
change made to this file was moving the jQuery and Bootstrap library loading
to before the ``body`` block (`lines 40-42 <jqueryLines_>`_ of the default
installation was moved to immediately after the ``<body>`` html tag). The
``{% block body %}{% endblock %}`` line is the one that includes the
XSLT-processed record display, so in order to allow jQuery to be used in the
XSLT translators, this modification was necessary.

..  _DataTables: https://datatables.net/
..  _jqueryLines: https://github.com/usnistgov/core_main_app/blob/master/core_main_app/templates/core_main_app/_render/user/theme_base.html#L40-L42

A few other templates from the ``core_explore_keyword_app`` and
``core_explore_common_app`` were overridden for `NexusLIMS`, primarily to modify
how the search page lists the records. Check the NexusLIMS repository for more
specific information about the changes.

More advanced Django tweaks
***************************

..  _more_advanced:

Instead of (or in addition to) overriding templates from CDCS, there are other
pieces of the Django application that can be modified to change how the user
interface is presented. In the case of `NexusLIMS`, this has involved changing
some of the XML utilities (written in Python) to allow parameters to be passed
to the the XSLT translator stylesheets. For example, in the file
``mdcs_home/utils/xml.py``, the ``xsl_transform()`` method from
``site-packages/core_main_app/utils/xml.py`` is overridden to allow for keyword
arguments (see `line 45 <xmlUtilsLink_>`_ of ``xml.py``), which are passed as
parameters to the XSLT stylesheet. This also required modifying the
``mdcs_home/templatetags/xsl_transform_tag.py`` file, which is where the
``xsl_transform_detail`` and ``xsl_transform_list`` tags (to be used in the
Django template files) are defined. Small modifications were made to the methods
as well to allow the passing of parameters to directly to the XSLT stylesheets
on the list and detail view pages.

.. _xmlUtilsLink: https://gitlab.nist.gov/gitlab/nexuslims/nexuslims-cdcs/blob/8511bd12a354ef4809489369ab0960af27c512aa/mdcs_home/utils/xml.py#L45

The ``mdcs_home`` folder
++++++++++++++++++++++++

.. _mdcs_home:

While it has been mentioned a few times previously in this document, the
``mdcs_home`` folder contains a place to store customizations, overrides, and
other additions on the Python side of the Django application. The ``mdcs_home``
folder represents a distinct Django `app` (like ``core_main_app`` and the
others) that the user has full control over. Thus, this folder does not contain
any HTML Django templates, but rather Python code that can be used to feed
the desired information into those templates. This is also a place where new
tags to be used in the templates (in the ``mdcs_home/templatetags`` folder)
can be defined. Other utilities can be defined (such as
``mdcs_home/utils/xml.py``) and imported as needed in the other Python files.

A few of the files provided by default in this folder were edited for the
`NexusLIMS` CDCS instance. In ``views.py`` (the file that handles web requests
and returns web responses -- see the `Django docs <DjangoViews_>`_ for more
detail), you can see the ``tiles()`` and ``template_list()`` methods defined,
which control what is ultimately displayed by the
`default templates <tiles_template_>`_ discussed above. Since the template
list display was removed entirely from the `NexusLIMS` CDCS, the only
modifications made to this file were to the ``tiles()`` method. In particular,
since the project did not require the "`Search using flexible queries`" or
"`Compose your own template`" tools, the lines that added these tiles to
the Django context (see `more info <DjangoContext_>`_ about Django context) were
commented out, leaving only the "`Explore`" and "`Create new record`" options.
This file (in particular the "`title`" and "`text`" values in each dictionary)
also controls what text is displayed on the tiles and showed to the user. Note,
it would also be possible to remove the apps mentioned in these files from the
``INSTALLED_APPS`` value in ``/srv/curator/mdcs/settings.py`` to remove the
functionality entirely and hide them from the tile list on the homepage.

..  _DjangoViews: https://docs.djangoproject.com/en/2.2/topics/http/views/
..  _DjangoContext: https://stackoverflow.com/questions/20957388/what-is-a-context-in-django

Likewise, the ``mdcs_home/menus.py`` file was modified by commenting out menu
items in the top bar that were not needed for `NexusLIMS`. This is also the
place to modify the text that is shown for each value along the top bar.

Debugging
+++++++++

When making changes to the application within a Docker container, it can be
difficult to use standard IDE tools for debugging. A useful tool for this is a
Python module called |web_pdb|_, which allows you to define breakpoints in the
Python sources, and open up a web-accessible Python debugger session. To use
it, you will need to install it in the ``mdcs_cdcs_1`` container with:

..  code:: bash

    pip install web-pdb

And then to use it, insert the following line at the place you want to stop
execution and debug:

..  code:: python

    import web_pdb; web_pdb.set_trace(port=3000)

When the Python interpreter reaches this line, it will pause execution, and then
you should be able to access the debugger in your web browser at whatever host
IP is running your instance over port 3000 (something like
http://localhost:3000). Note, this port is already forwarded from the CDCS
container to ``localhost`` by default if you use the ``NexusLIMS``-customized
Docker installation. See `line 84 <NexusLIMSDockerCompose3000_>`_ of the
``docker-compose.yml`` file used during installation.

..  |web_pdb| replace:: ``web-pdb``
..  _web_pdb: https://github.com/romanvm/python-web-pdb
..  _NexusLIMSDockerCompose3000: https://gitlab.nist.gov/gitlab/nexuslims/nexuslims-cdcs-docker-setup/blob/90bdc073163633b5e6c2de94efad823edfcc3982/docker-compose.yml#L84

------------

.. [1] Certain commercial software is identified only to foster understanding.
       Such identification does not imply recommendation or endorsement by the
       National Institute of Standards and Technology, nor does it imply that
       the product identified is necessarily the best available for the purpose.