#  NIST Public License - 2019
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
from hyperspy.io import load as _hs_load


def get_emi_metadata(filename):
    """
    Returns metadata (as a dict) from an FEI .emi file + its associated .ser files, with some non-relevant information
    stripped.

    Parameters
    ----------
    filename : str
        Path to FEI .emi file, HyperSpy automatically parses the .ser files associated with each .emi file.

    Returns
    -------
    metadata : dict
        Metadata of interest which is extracted from the passed files.
    """
    # Trees:
    # ObjectInfo & ser_header_parameters
    s = _hs_load(filename, lazy=True)   # Loads in each .ser file associated with the passed .emi file into a list
                                        # Each .ser file contain the same information(?), so only need to work with
                                        # the first list element, s[0]
    # Remove parts of the tree that are not of interest
    for leaf in ['ser_header_parameters', 'ObjectInfo.TrueImageHeaderInfo', 'ObjectInfo.Manufacturer',
                 'ObjectInfo.Uuid', 'ObjectInfo.DetectorRange']:
        dtb_metadata = _remove_dtb_element(s[0].original_metadata, leaf)

    metadata = dtb_metadata.as_dictionary()
    root_metadata = _find_dict_root(metadata)

    return root_metadata


def _remove_dtb_element(tree, path):

    """
    Helper method that uses exec to delete a specific leaf of a
    DictionaryTreeBrowser using a string

    Parameters
    ----------
    tree : :py:class:`~hyperspy.misc.utils.DictionaryTreeBrowser`
        the ``DictionaryTreeBrowser`` object to remove the object from
    path : str
        period-delimited path to a DTB element

    Returns
    -------
    tree : :py:class:`~hyperspy.misc.utils.DictionaryTreeBrowser`
    """
    to_del = 'tree.{}'.format(path)
    try:
        exec('del {}'.format(to_del))
    except AttributeError as _:
        raise Exception('Raised AttributeError')
        # Log the failure and continue
        # _logger.info('_remove_dtb_element: Could not find {}'.format(to_del))

    return tree


def _find_dict_root(nested_dict):
    """
    Helper function to recursively parse through nested dictionaries such that only the most
    central entries are isolated and returned.

    Parameters
    ----------
    nested_dict : dict
        Dictionary object which has other dictionaries nested within it.

    Returns
    -------
    root_dict : dict
        Dictionary which has been parsed such that only the lowest level elements are still present.
    """
    root_dict = {}
    for key in nested_dict:
        if not isinstance(nested_dict[key], dict):
            root_dict[key] = nested_dict[key]
        else:
            nested_dict[key].update(root_dict)  # merge the dictionary to be passed with lowest elements already
                                                # isolated so that no information is lost during recursive loops
            root_dict = _find_dict_root(nested_dict[key])

    return root_dict


# if __name__ == '__main__':
#     file_loc = '***REMOVED***/mmfnexus/Titan/***REMOVED***/181113 - ' \
#         '***REMOVED*** - ***REMOVED*** - Titan/14.59.36 Scanning Acquire.emi'
#     # file_loc = '***REMOVED***/mmfnexus/Titan/***REMOVED***/181113 - ' \
#     #     '***REMOVED*** - ***REMOVED*** - Titan/15.10.59 Scanning Acquire.emi'
#
#     result = get_emi_metadata(file_loc)
#     for _ in result:
#         print(_, result[_])