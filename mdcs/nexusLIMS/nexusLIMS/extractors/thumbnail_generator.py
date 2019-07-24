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
#

from PIL import Image
import numpy as np
import matplotlib.image as mpl_image


def _image_thumbnail(indata,
                     thumbfile=None,
                     scale=0.1,
                     interpolation='bilinear'):
    """
    Make a thumbnail of image data in `indata` with output filename `thumbfile`.

    Parameters
    ----------
    indata : :py:class:`numpy.ndarray`
        The 2D data to use for creating the thumbnail
    thumbfile : None or str, optional
        If ``None``, no file will be written to disk. If a string is
        provided, it should be a path to the desired thumbnail filename
    scale : float, optional
        The scale factor for the thumbnail.
    interpolation : str, optional
        The interpolation scheme used in the resampling. See the
        `interpolation` parameter of :py:func:`~matplotlib.pyplot.imshow` for
        possible values.

    Returns
    -------
    figure : :py:class:`~matplotlib.figure.Figure`
        The figure instance containing the thumbnail.

    Notes
    -----
    This method is a reimplementation of :py:func:`matplotlib.image.thumbnail`,
    but adapted to accept a data array input instead of a file input.
    """
    from matplotlib.backend_bases import FigureCanvasBase

    imdata = indata
    rows, cols = imdata.shape

    # This doesn't really matter (it cancels in the end) but the API needs it.
    dpi = 100

    height = rows / dpi * scale
    width = cols / dpi * scale

    from matplotlib.figure import Figure
    fig = Figure(figsize=(width, height), dpi=dpi)
    FigureCanvasBase(fig)

    ax = fig.add_axes([0, 0, 1, 1], aspect='auto',
                      frameon=False, xticks=[], yticks=[])

    imdata /= imdata.max()
    imdata -= imdata.mean()
    imdata /= imdata.std()
    scale = np.max([np.abs(np.percentile(imdata, 1.0)),
                    np.abs(np.percentile(imdata, 99.0))])
    imdata /= scale
    imdata = np.clip(imdata, -1.0, 1.0)
    imdata = (imdata + 1.0) / 2.0

    imdata = (imdata * 255 + 0.5).astype(np.uint8)

    ax.imshow(imdata, aspect='auto', resample=True, interpolation=interpolation)

    if thumbfile:
        fig.savefig(thumbfile, dpi=dpi)

    return fig


def sig_to_thumbnail(s, out_path, scale=0.1, interpolation='bilinear'):
    """
    Generate a thumbnail of from an arbitrary HyperSpy signal. For a 2D
    signal, the signal from the center navigation position is used. For a 1D
    signal (*i.e.* a spectrum or spectrum image), the output depends on the
    number of navigation dimensions:

    - 0: Image of spectrum
    - 1: Image of linescan (*a la* DigitalMicrograph)
    - 2: Sum image of navigation space (like default HyperSpy navigator plot -- see HyperSpy's :std:ref:`"Data Visualization" <visualization-label>` documentation)
    - 2+: As for 2 dimensions, but the navigation space is collapsed to 2D prior to plotting

    Parameters
    ----------
    s : :py:class:`hyperspy.signal.BaseSignal` (or subclass)
        The HyperSpy signal for which a thumbnail should be generated
    out_path : str
        A path to the desired thumbnail filename
    scale : float, optional
        The scale factor for the thumbnail.
    interpolation : str, optional
        The interpolation scheme used in the resampling. See the
        `interpolation` parameter of :py:func:`~matplotlib.pyplot.imshow` for
        possible values.

    Returns
    -------
    figure : :py:class:`~matplotlib.figure.Figure`
        A figure instance containing the thumbnail
    """
    s.plot()

# fname = os.path.splitext(f)[0]
#     print('{}\t\t{}\t{}'.format( fname, s.data.min(), s.data.max()))
# print(fname)
# s = hs.load('{}.dm3'.format(fname))
# data = s.data

# do a normalization for diffraction data and display on a log scale
# try:
#     if s.original_metadata.ImageList.TagGroup0.ImageTags.Microscope_Info.Imaging_Mode == 'DIFFRACTION':
#         s += (np.abs(s.data.min()) + 1)
#         data = np.log(s.data)
# except Exception:
#     pass

# thumbnail(data.astype(float), fname + '.thumb.png', scale=0.1, preview=False)