Schema documentation
====================

    `Last updated: February 25, 2020`


This page contains the documentation automatically generated from the NexusLIMS
Schema (``nexus-experiment.xsd``) that is used to validate experimental records
upon insertion into the NexusLIMS CDCS instance. This documentation was
generated using Oxygen's
`XML Developer <https://www.oxygenxml.com/xml_developer.html>`_. [1]_

.. raw:: html
   :file: schema_doc/nexus-experiment.xsd.html

Building the Schema Documentation
+++++++++++++++++++++++++++++++++

To build the above documentation, the Oxygen XML Developer software is needed.
The standard `XSD -> HTML` translator document has been customized to allow
embedding within a Sphinx documentation page, and is included in the NexusLIMS
repository as ``_schema_doc_gen/xsdDocHtml.xsl``.
Using the XML Developer software's "Generate XML Schema Documentation" feature
(available through the `Tools -> Generate documenation` menu), select the
``nexus-experiment.xsd`` schema file as the `Schema URL`, and select `Custom` in
the Format menu. Under the options for Custom Format, select the
``_schema_doc_gen/xsdDocHtml.xsl`` stylesheet as the `Custom XSL`. Ensure that
both check boxes are checked and the `Resources` field points to
``_schema_doc_gen/img``. After clicking `OK`, ensure that the `Output file` is
set to ``schema_doc/nexus-experiment.xsd.html``, and click `Generate`. See the
following images for details:

.. image:: _static/schema_doc_gen_1.png
   :width: 48%

.. image:: _static/schema_doc_gen_2.png
   :width: 48%


To include the resulting HTML in the main documentation, use a ``.. raw::``
Sphinx directive to include the file directly in an ``.rst`` file, such as:

    .. code-block::

        .. raw:: html
            :file: schema_doc/nexus-experiment.xsd.html

.. [1] Certain commercial software is identified only to foster understanding.
       Such identification does not imply recommendation or endorsement by the
       National Institute of Standards and Technology, nor does it imply that
       the product identified is necessarily the best available for the purpose.