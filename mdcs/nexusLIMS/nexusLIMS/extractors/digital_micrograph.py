# limit our imports to hopefully reduce loading time
import logging as _logging
from hyperspy.io import load as _hs_load

# from hyperspy.misc.utils import DictionaryTreeBrowser as _DTB
_logger = _logging.getLogger(__name__)


def get_dm3_metadata(filename):
    """
    Returns the metadata (as a dict) from a .dm3 file saved by the Gatan's
    Digital Micrograph in the Nexus Microscopy Facility, with some
    non-relevant information stripped out

    Parameters
    ----------
    filename : str
        path to a .dm3 file saved by Gatan's Digital Micrograph

    Returns
    -------
    metadata : dict
        The metadata of interest extracted from the file
    """
    # We do lazy loading so we don't actually read the data from the disk to
    # save time and memory.
    #

    s = _hs_load(filename, lazy=True)
    m_tree = s.original_metadata

    # Important trees:
    #   DocumentObjectList
    #     Contains information about the display of the information,
    #     including bits about annotations that are included on top of the
    #     image data, the CLUT (color look-up table), data min/max.
    #
    #   ImageList
    #     Contains the actual image information

    # Remove the trees that are not of interest:
    for t in ['ApplicationBounds', 'DocumentTags', 'HasWindowPosition',
              'ImageSourceList',  'Image_Behavior', 'InImageMode',
              'MinVersionList', 'NextDocumentObjectID', 'PageSetup',
              'Page_Behavior', 'SentinelList', 'Thumbnails',
              'WindowPosition', 'root']:
        m_tree = _remove_dtb_element(m_tree, t)

    # Within the DocumentObjectList tree, we really only care about the
    # AnnotationGroupList for each TagGroup, so go into each TagGroup and
    # delete everything but that...
    # NB: the hyperspy DictionaryTreeBrowser __iter__ function returns each
    #   tree element as a tuple containing the tree name and the actual tree, so
    #   we loop through the tag names by taking the first part of the tuple:
    for tg_name, tg in m_tree.DocumentObjectList:
        # tg_name should be 'TagGroup0', 'TagGroup1', etc.
        keys = tg.keys()
        keys.remove('AnnotationGroupList')
        for k in keys:
            # k should be in ['AnnotationType', 'BackgroundColor',
            # 'BackgroundMode', 'FillMode', etc.]
            m_tree = _remove_dtb_element(m_tree, 'DocumentObjectList.'
                                                 '{}.{}'.format(tg_name, k))

    return m_tree


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
        # Log the failure and continue
        _logger.info('_remove_dtb_element: Could not find {}'.format(to_del))

    return tree
