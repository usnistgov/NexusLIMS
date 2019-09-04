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

import numpy as _np
import tempfile as _tmp
import hyperspy.api as _hsapi
import os as _os
from skimage.io import imread as _imread
import skimage.transform as _tform
from skimage.transform import resize as _resize
import matplotlib.pyplot as _plt
from matplotlib.offsetbox import AnchoredOffsetbox as _AOb
from matplotlib.offsetbox import OffsetImage as _OIm
from matplotlib.transforms import Bbox as _Bbox

_dir_path = _os.path.dirname(_os.path.realpath(__file__))


def _full_extent(ax, items, pad=0.0):
    """Get the full extent of items in an axis.
    Adapted from https://stackoverflow.com/a/26432947/1435788
    """
    # For text objects, we need to draw the figure first, otherwise the extents
    # are undefined.
    ax.figure.canvas.draw()
    bbox = _Bbox.union([item.get_window_extent() for item in items])

    return bbox.expanded(1.0 + pad, 1.0 + pad)


def _project_image_stack(s, num=5, dpi=92, v_shear=0.3, h_scale=0.3):
    """
    Create a preview of an image stack by selecting a number of example frames
    and projecting them into a pseudo-3D display.

    Parameters
    ----------
    s : :py:class:`hyperspy.signal.BaseSignal` (or subclass)
        The HyperSpy signal for which an image stack preview should be
        generated. Should have a signal dimension of 2 and a navigation
        dimension of 1.
    num : int
        The number of frames in the image stack to use to make the preview
    dpi : int
        The "dots per inch" of the individual frames within the preview
    v_shear : float
        The factor by which to vertically shear (0.5 means shear the top border
        down by half of the original image's height)
    h_scale : float
        The factor by which to scale in the horizontal direction (0.3 means
        each projected frame will be 30% the width of the original image)

    Returns
    -------
    output : :py:class:`numpy.ndarray`
        The `num` frames loaded into a single NumPy array for plotting
    """
    shear = _np.array([[ 1,           0, 0],
                       [-1 * v_shear, 1, 0],
                       [ 0,           0, 1]])
    scale = _np.array([[h_scale, 0, 0],
                       [      0, 1, 0],
                       [      0, 0, 1]])
    trans_mat = _np.dot(shear, _np.linalg.inv(scale))

    tmps = [''] * num
    for idx, i in enumerate(
            _np.linspace(0, s.axes_manager.navigation_size - 1, num=num,
                         dtype=int)):
        _hsapi.plot.plot_images([s.inav[i].as_signal2D((0, 1))],
                                axes_decor='off', colorbar=False,
                                scalebar='all', label=None)
        tmp = _tmp.NamedTemporaryFile()
        ax = _plt.gca()
        ax.set_position([0, 0, 1, 1])
        ax.set_axis_on()
        for axis in ['top', 'bottom', 'left', 'right']:
            ax.spines[axis].set_linewidth(5)
        ax.figure.canvas.draw()
        ax.figure.savefig(tmp.name + '.png', dpi=dpi)
        tmps[idx] = tmp
        _plt.close(ax.figure)

    im_data = [None] * num
    for idx, tmp in enumerate(tmps):
        img = _plt.imread(tmp.name + '.png')
        img_trans = _tform.warp(img, trans_mat, order=1, preserve_range=True,
                                   mode='constant', cval=_np.nan,
                                output_shape=(int(img.shape[1] * (1 + v_shear)),
                                              int(img.shape[0] * h_scale)))
        im_data[idx] = img_trans

    for t in tmps:
        t.close()
        _os.remove(t.name + '.png')

    output = _np.hstack(im_data)

    return output


def sig_to_thumbnail(s, out_path, dpi=92):
    """
    Generate a thumbnail of from an arbitrary HyperSpy signal. For a 2D
    signal, the signal from the first navigation position is used (most
    likely the top- and left-most position. For a 1D signal (*i.e.* a
    spectrum or spectrum image), the output depends on the
    number of navigation dimensions:

    - 0: Image of spectrum
    - 1: Image of linescan (*a la* DigitalMicrograph)
    - 2: Image of spectra sampled from navigation space
    - 2+: As for 2 dimensions

    Parameters
    ----------
    s : :py:class:`hyperspy.signal.BaseSignal` (or subclass)
        The HyperSpy signal for which a thumbnail should be generated
    out_path : str
        A path to the desired thumbnail filename. All formats supported by
        :py:meth:`~matplotlib.figure.Figure.savefig` can be used.
    dpi : int
        The "dots per inch" resolution for the outputted figure

    Notes
    -----
    This method heavily utilizes HyperSpy's existing plotting functions to
    figure out how to best display the image
    """
    # Processing 1D signals (spectra, spectrum images, etc)
    if isinstance(s, _hsapi.signals.Signal1D):
        # signal is single spectrum
        if s.axes_manager.navigation_dimension == 0:
            s.plot()
            # get signal plot figure
            f = s._plot.signal_plot.figure
            ax = f.get_axes()[0]
            # Change line color to matplotlib default
            ax.get_lines()[0].set_color(_plt.get_cmap('tab10')(0))
            ax.set_title(s.metadata.General.title)
            f.savefig(out_path, dpi=dpi)
            _plt.close(f)
        # signal is 1D linescan
        elif s.axes_manager.navigation_dimension == 1:
            s.plot()
            s._plot.pointer.set_on(False)       # remove pointer
            f = s._plot.navigator_plot.figure
            f.get_axes()[1].remove()            # remove colorbar scale
            f.get_axes()[0].set_title(s.metadata.General.title)
            f.savefig(out_path, bbox_inches='tight', dpi=dpi)
            _plt.close(f)
        elif s.axes_manager.navigation_dimension > 1:
            nav_size = s.axes_manager.navigation_size
            if nav_size >= 9:
                n_to_plot = 9
            else:
                n_to_plot = nav_size

            # temporarily unfold the signal so we can get spectra from all
            # over the navigation space easily:
            with s.unfolded():
                idx_to_plot = _np.linspace(0, nav_size-1, n_to_plot, dtype=int)
                s_to_plot = [s.inav[i] for i in idx_to_plot]

            f = _plt.figure()
            _hsapi.plot.plot_spectra(s_to_plot, style='cascade',
                                     padding=0.1, fig=f)
            ax = _plt.gca()

            desc = r'\ x\ '.join([str(x) for x in
                                  s.axes_manager.navigation_shape])

            ax.set_title(s.metadata.General.title + '\n' + r"$\bf{" +
                         desc + r'\ Spectrum\ Image}$')

            # Load "watermark" stamp and rescale to be appropriately sized
            stamp = _imread(_os.path.join(_dir_path,
                                          'spectrum_image_logo.svg.png'))
            width, height = ax.figure.get_size_inches() * f.dpi
            stamp_width = int(width / 2.5)
            scaling = (stamp_width / float(stamp.shape[0]))
            stamp_height = int(float(stamp.shape[1]) * float(scaling))
            stamp = _resize(stamp, (stamp_width, stamp_height),
                            mode='wrap', anti_aliasing=True)

            # Create matplotlib annotation with image in center
            imagebox = _OIm(stamp, zoom=1, alpha=.15)
            imagebox.image.axes = ax
            ao = _AOb('center', pad=1, borderpad=0, child=imagebox)
            ao.patch.set_alpha(0)
            ax.add_artist(ao)

            # Pack figure and save
            f.tight_layout()
            f.savefig(out_path, dpi=dpi)
            _plt.close(f)

    # Signal is an image of some sort, so we'll use hs.plot.plot_images
    elif isinstance(s, _hsapi.signals.Signal2D):
        # signal is single image
        if s.axes_manager.navigation_dimension == 0:
            _hsapi.plot.plot_images([s], axes_decor='off',
                                    colorbar=False, scalebar='all', label=None)
            f = _plt.gcf()
            ax = _plt.gca()
            ax.set_title(s.metadata.General.title)
            f.tight_layout()
            f.savefig(out_path, dpi=dpi)
            _plt.close(f)
        # we're looking at an image stack
        elif s.axes_manager.navigation_dimension == 1:
            _plt.figure()
            _plt.imshow(_project_image_stack(s, dpi=dpi))
            ax = _plt.gca()
            ax.set_position([0, 0, 1, .8])
            ax.set_axis_off()
            ax.set_title(s.metadata.General.title + '\n' +
                         r"$\bf{" + str(s.axes_manager.navigation_size)
                         +'-member' + r'\ Image\ Series}$')
            _plt.show()
            # use _full_extent to determine the bounding box needed to pick
            # out just the items we're interested in
            extent = _full_extent(ax, [ax, ax.title], pad=0.1).transformed(
                ax.figure.dpi_scale_trans.inverted())
            ax.figure.savefig(out_path, bbox_inches=extent, dpi=300)
            _plt.close(ax.figure)
        # This is a 4D-STEM type image, so display as tableau
        elif s.axes_manager.navigation_dimension == 2:
            asp_ratio = s.axes_manager.signal_shape[
                            1]/s.axes_manager.signal_shape[0]
            width = 6
            f = _plt.figure(figsize=(width, width * asp_ratio))
            if s.axes_manager.navigation_size >= 9:
                square_n = 3
            elif s.axes_manager.navigation_size >= 4:
                square_n = 2
            else:
                square_n = 1
            num_to_plot = square_n**2
            im_list = [None] * num_to_plot
            desc = r'\ x\ '.join([str(x) for x in
                                  s.axes_manager.navigation_shape])
            s.unfold_navigation_space()
            chunk_size = s.axes_manager.navigation_size // num_to_plot
            for i in range(num_to_plot):
                im_list[i] = s.inav[i * chunk_size:
                                    (i+1) * chunk_size].inav[chunk_size//2]
            axlist = _hsapi.plot.plot_images(im_list, colorbar=None,
                                             axes_decor='off',
                                             tight_layout=True, scalebar=[0],
                                             per_row=square_n, fig=f)

            # Make sure scalebar is fully on plot:
            _plt.show()
            txt = axlist[0].texts[0]
            left_extent = txt.get_window_extent().transformed(
                          axlist[0].transData.inverted()).bounds[0]
            if left_extent < 0:
                # Move scalebar text over if it overlaps outside of axis
                txt.set_x(txt.get_position()[0] + left_extent * -1)
            # txt.set_y(txt.get_position()[1]*1.1)
            f.suptitle(s.metadata.General.title + '\n' +
                       r"$\bf{" + desc + r'\ Hyperimage}$')
            f.tight_layout(rect=(0, 0, 1,
                                 f.texts[0].get_window_extent().transformed(
                                     f.transFigure.inverted()).bounds[1]))
            f.savefig(out_path, dpi=dpi)
            _plt.close(f)

    # if we have a different type of signal, just output a graphical
    # representation of the axis manager
    else:
        f, ax = _plt.subplots()
        ax.set_position([0, 0, 1, 1])
        ax.set_axis_off()

        # Remove axes_manager text
        ax_m = s.axes_manager.__repr__()
        ax_m = ax_m.split('\n')
        ax_m = ax_m[1:]
        ax_m = '\n'.join(ax_m)

        ax.text(0.03, .9, s.metadata.General.title,
                fontweight='bold', va='top')
        ax.text(0.03, 0.85, 'Could not generate preview image',
                va='top', color='r')
        ax.text(0.03, 0.8, 'Axes information:',
                va='top', fontstyle='italic')
        ax.text(0.03, .75, ax_m,
                fontfamily='monospace', va='top')

        extent = _full_extent(ax, ax.texts, pad=0.1).transformed(
            ax.figure.dpi_scale_trans.inverted())

        f.savefig(out_path, bbox_inches=extent, dpi=300)

