# limit our imports to hopefully reduce loading time
import os as _os
import logging as _logging
import shutil as _shutil
import tarfile as _tarfile

from hyperspy.io import load as _hs_load
from hyperspy.io_plugins.digital_micrograph import \
    DigitalMicrographReader as _dm_reader
from hyperspy.io_plugins.digital_micrograph import ImageObject as _ImageObject

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


def _zero_data_in_dm3(filename, out_filename=None, compress=True):
    """
    Helper method that will overwrite the data in a dm3 image file  with
    zeros and save it as either another dm3, or as a compressed archive (used
    for creating files for the test suite that don't take up tons of space).
    Since the resulting file is just some text metadata and zeros, it should
    be highly compressible (initial tests allowed for a 16MB file to be
    compressed to ~100KB).

    Parameters
    ----------
    filename : str
        Path to file to be modified
    out_filename : None or str
        Name with which to save the output file. If None, it will be
        automatically generated from the ``filename``.
    compress : bool
        Whether or not to compress the files into a tar.gz file

    Returns
    -------
    out_fname : str
        The path of the compressed (or zeroed) file
    """
    # zero out extent of data in DM3 file and compress to tar.gz:
    splitext = _os.path.splitext(filename)
    if not out_filename:
        mod_fname = splitext[0] + '_dataZeroed' + splitext[1]
    else:
        mod_fname = out_filename

    _shutil.copyfile(filename, mod_fname)

    # Do some lower-level reading on the .dm3 file to get the ImageObject refs
    with open(filename, 'rb') as f:
        dm = _dm_reader(f)
        dm.parse_file()
        images = [_ImageObject(imdict, f) for imdict in
                  dm.get_image_dictionaries()]

    # write zeros to the file in the data block (offset + size in bytes
    # information is obtained from the ImageObject ref)
    # NB: currently this is just tested for single-image .dm3 files. Spectra
    # and image stacks will probably work differently.
    with open(mod_fname, 'r+b') as f:
        f.seek(images[0].imdict.ImageData.Data.offset)
        f.write(b'\x00' * images[0].imdict.ImageData.Data.size_bytes)

    # compress the output, if requested
    if compress:
        with _tarfile.open('{}.tar.gz'.format(mod_fname), 'w:gz') as tar:
            tar.add(mod_fname)
        out_fname = '{}.tar.gz'.format(mod_fname)
        _os.remove(mod_fname)
    else:
        out_fname = mod_fname

    return out_fname
