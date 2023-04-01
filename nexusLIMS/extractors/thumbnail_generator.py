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
"""
Generate preview images from various data files.

Data files are represented as either HyperSpy Signals, or as raw data files
(in the case of tiff images)
"""
import logging
import tempfile
import textwrap
from pathlib import Path
from typing import Optional, Tuple

import hyperspy.api as hs_api
import matplotlib as mpl
import matplotlib.pyplot as plt
import numpy as np
from hyperspy.drawing.marker import dict2marker
from matplotlib.offsetbox import AnchoredOffsetbox, OffsetImage
from matplotlib.transforms import Bbox
from PIL import Image
from skimage import transform
from skimage.io import imread
from skimage.transform import resize

try:
    _LANCZOS = Image.Resampling.LANCZOS
except AttributeError:  # pragma: no cover
    # above is deprecated as of Pillow 9.1.0
    _LANCZOS = Image.LANCZOS

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
_dir_path = Path(__file__).parent
mpl.use("Agg")


def _full_extent(axis, items, pad=0.0):
    """
    Get the full extent of items in an axis.

    Adapted from https://stackoverflow.com/a/26432947/1435788.
    """
    # For text objects, we need to draw the figure first, otherwise the extents
    # are undefined.
    axis.figure.canvas.draw()
    bbox = Bbox.union([item.get_window_extent() for item in items])

    return bbox.expanded(1.0 + pad, 1.0 + pad)


def _set_title(axis, title):
    """
    Set an axis title with maximum width.

    Makes sure it is no wider than 60 characters (so it doesn't run over the edges
    of the plot)

    Parameters
    ----------
    ax : :py:mod:`matplotlib.axis`
        A matplotlib axis instance on which to operate
    title : str
        The desired axis title
    """
    new_title = textwrap.fill(title, 60)
    axis.set_title(new_title)


def _get_visible_labels(axis):
    """
    Get labels that are visible for plot.

    Helper method to return only the tick labels that are visible given the
    current extent of the axes. Useful when calculating the extent of the figure
    to save so extra white space from invisible labels is not included.

    Parameters
    ----------
    ax : :py:mod:`matplotlib.axis`
        A matplotlib axis instance on which to operate

    Returns
    -------
    vis_labels_x, vis_labels_y : tuple of lists
        lists of only the label objects that are visible on the current axis
    """
    vis_labels_x = mpl.cbook.silent_list("Text xticklabel")
    vis_labels_y = mpl.cbook.silent_list("Text yticklabel")

    for label in axis.get_xticklabels():
        label_pos = label.get_position()[0]
        x_limits = axis.get_xlim()
        if x_limits[0] < label_pos < x_limits[1]:
            vis_labels_x.append(label)
    for label in axis.get_yticklabels():
        label_pos = label.get_position()[1]
        y_limits = axis.get_ylim()
        if y_limits[0] < label_pos < y_limits[1]:
            vis_labels_y.append(label)

    return vis_labels_x, vis_labels_y


def _project_image_stack(s, num=5, dpi=92, v_shear=0.3, h_scale=0.3):
    """
    Project an image stack.

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
    tmps = []
    for i in np.linspace(0, s.axes_manager.navigation_size - 1, num=num, dtype=int):
        hs_api.plot.plot_images(
            [s.inav[i].as_signal2D((0, 1))],
            axes_decor="off",
            colorbar=False,
            scalebar="all",
            label=None,
        )
        tmp = tempfile.NamedTemporaryFile()  # pylint: disable=consider-using-with
        axis = plt.gca()
        axis.set_position([0, 0, 1, 1])
        axis.set_axis_on()
        for axis_side in ["top", "bottom", "left", "right"]:
            axis.spines[axis_side].set_linewidth(5)
        axis.figure.canvas.draw()
        axis.figure.savefig(tmp.name + ".png", dpi=dpi)
        tmps.append(tmp)
        plt.close(axis.figure)

    im_data = []
    for tmp in tmps:
        img = plt.imread(tmp.name + ".png")
        img_trans = transform.warp(
            image=img,
            inverse_map=np.dot(
                np.array([[1, 0, 0], [-1 * v_shear, 1, 0], [0, 0, 1]]),  # shear
                np.linalg.inv(
                    np.array([[h_scale, 0, 0], [0, 1, 0], [0, 0, 1]]),
                ),  # scale
            ),
            order=1,
            preserve_range=True,
            mode="constant",
            cval=np.nan,
            output_shape=(
                int(img.shape[1] * (1 + v_shear)),
                int(img.shape[0] * h_scale),
            ),
        )
        im_data.append(img_trans)

    for temp_file in tmps:
        temp_file.close()
        Path(temp_file.name + ".png").unlink()

    return np.hstack(im_data)


def _pad_to_square(im_path: Path, new_width: int = 500):
    """
    Pad an image to square.

    Helper method to pad an image saved on disk to a square with size
    ``width x width``. This ensures consistent display on the front-end web
    page. Increasing the size of a dimension is done by padding with empty
    space. The original image is overwritten.

    Method adapted from:
    https://jdhao.github.io/2017/11/06/resize-image-to-square-with-padding/

    Parameters
    ----------
    im_path
        The path to the image that should be resized/padded
    new_width
        Desired output width/height of the image (in pixels)
    """
    image = Image.open(im_path)
    old_size = image.size  # old_size[0] is in (width, height) format
    ratio = float(new_width) / max(old_size)
    new_size = tuple(int(x * ratio) for x in old_size)
    image = image.resize(new_size, _LANCZOS)

    new_im = Image.new("RGBA", (new_width, new_width))
    new_im.paste(
        image,
        ((new_width - new_size[0]) // 2, (new_width - new_size[1]) // 2),
    )
    new_im.save(im_path)


def _get_marker_color(annotation):
    """
    Get the color of a DigitalMicrograph annotation.

    Parameters
    ----------
    annotation : dict
        The tag dictionary for a given annotation from a DigitalMicrograph
        tag structure

    Returns
    -------
    color : str or tuple
        Either an RGB tuple, or string containing a color name
    """
    if ("ForegroundColor" in annotation) or ("Color" in annotation):
        # There seems to be 3 different colors in annotations in
        # dm3-files: Color, ForegroundColor and BackgroundColor.
        # ForegroundColor and BackgroundColor seems to be present
        # for all annotations. Color is present in some of them.
        # If Color is present, it seems to override the others.
        # Currently, BackgroundColor is not utilized, due to
        # HyperSpy markers only supporting a single color.
        if "Color" in annotation:
            color_raw = annotation["Color"]
        else:
            color_raw = annotation["ForegroundColor"]
        # Colors in DM are saved as negative values
        # Some values are also in 16-bit
        color = []
        for raw_value in color_raw:
            raw_value_ = abs(raw_value)
            if raw_value_ > 1:
                raw_value_ /= 2**16
            color.append(raw_value_)
        color = tuple(color)
    else:
        color = "red"

    return color


def _get_marker_props(annotation):
    """
    Get the properties of a DigitalMicrograph annotation.

    Parameters
    ----------
    annotation : dict
        The tag dictionary for a given annotation from a DigitalMicrograph
        tag structure

    Returns
    -------
    marker_properties : dict
        A dictionary containing various properties for this
        annotation/marker, such as line width, style, etc.
    temp_dict : dict
        A dictionary that contains the marker type
    marker_text : None or str
        If present, the text of a textual annotation
    """
    marker_properties = {}
    temp_dict = {}
    marker_text = None
    log_msg_map = {
        3: "Arrow marker not loaded: not implemented",
        4: "Double arrow marker not loaded: not implemented",
        6: "Ellipse marker not loaded: not implemented",
        8: "Mask spot marker not loaded: not implemented",
        9: "Mask array marker not loaded: not implemented",
        15: "Mask band pass marker not loaded: not implemented",
        19: "Mask wedge marker not loaded: not implemented",
        29: "ROI curve marker not loaded: not implemented",
        31: "Scalebar marker not loaded: not implemented",
    }
    line_segment_type = 2
    rectangle_type = 5
    text_type = 13
    roi_rectangle_type = 23
    roi_line_type = 25
    point_type = 27
    if "AnnotationType" in annotation:
        annotation_type = annotation["AnnotationType"]
        if annotation_type == line_segment_type:
            temp_dict["marker_type"] = "LineSegment"
            marker_properties["linewidth"] = 2
        elif annotation_type == rectangle_type:
            temp_dict["marker_type"] = "Rectangle"
            marker_properties["linewidth"] = 2
        elif annotation_type == text_type:
            temp_dict["marker_type"] = "Text"
            marker_text = annotation["Text"]
        elif annotation_type == roi_rectangle_type:  # roirectangle
            temp_dict["marker_type"] = "Rectangle"
            marker_properties["linestyle"] = "--"
            marker_properties["linewidth"] = 2
        elif annotation_type == roi_line_type:  # roiline
            temp_dict["marker_type"] = "LineSegment"
            marker_properties["linestyle"] = "--"
            marker_properties["linewidth"] = 2
        elif annotation_type == point_type:
            temp_dict["marker_type"] = "Point"
        elif annotation_type in log_msg_map:
            logger.debug(log_msg_map[annotation_type])

    return marker_properties, temp_dict, marker_text


def _get_markers_dict(s, tags_dict):
    """
    Get dictionary of markers from a HyperSpy signal.

    Parameters
    ----------
    s : :py:class:`hyperspy.signal.BaseSignal`
        The HyperSpy signal from which annotations should be read
    tags_dict : dict
        The dictionary of DigitalMicrograph tags (saved as
        ``s.original_metadata``)

    Returns
    -------
    markers_dict : dict
        The Markers that correspond to the annotations found in `s`
    """
    scale = {"x": s.axes_manager["x"].scale, "y": s.axes_manager["y"].scale}
    offset = {"x": s.axes_manager["x"].offset, "y": s.axes_manager["y"].offset}

    markers_dict = {}
    annotations_dict = tags_dict["DocumentObjectList"]["TagGroup0"][
        "AnnotationGroupList"
    ]
    for annotation in annotations_dict.values():
        if "Rectangle" in annotation:
            position = annotation["Rectangle"]
        marker_properties, temp_dict, marker_text = _get_marker_props(annotation)
        if "marker_type" in temp_dict:
            color = _get_marker_color(annotation)
            if "Label" in annotation and annotation["Label"] != []:
                # Some annotations contains an empty label, which are
                # represented in the input dict as an empty list: []
                marker_label = annotation["Label"]
                label_marker_dict = {
                    "marker_type": "Text",
                    "plot_marker": True,
                    "plot_on_signal": True,
                    "axes_manager": s.axes_manager,
                    "data": {
                        "y1": position[0] * scale["y"] + offset["y"],
                        "x1": position[1] * scale["x"] + offset["x"],
                        "size": 20,
                        "text": marker_label,
                    },
                    "marker_properties": {
                        "color": color,
                        "va": "bottom",
                    },
                }
                marker_name = "Text" + str(annotation["UniqueID"])
                markers_dict[marker_name] = label_marker_dict

            marker_properties["color"] = color
            temp_dict["plot_on_signal"] = (True,)
            temp_dict["plot_marker"] = (True,)
            temp_dict["axes_manager"] = (s.axes_manager,)
            temp_dict["data"] = {
                "y1": position[0] * scale["y"] + offset["y"],
                "x1": position[1] * scale["x"] + offset["x"],
                "y2": position[2] * scale["y"] + offset["y"],
                "x2": position[3] * scale["x"] + offset["x"],
                "size": 20,
                "text": marker_text,
            }
            temp_dict["marker_properties"] = marker_properties
            markers_dict[
                temp_dict["marker_type"] + str(annotation["UniqueID"])
            ] = temp_dict

    return markers_dict


def add_annotation_markers(s):
    """
    Add annotation markers from a DM3/DM4 file to a HyperSpy signal.

    Read annotations from a signal originating from DigitalMicrograph and
    convert the ones (that we can) into Hyperspy markers for plotting.
    Adapted from a currently (at the time of writing) open `pull request`_ in
    HyperSpy.

    .. _pull request: https://github.com/hyperspy/hyperspy/pull/1491

    Parameters
    ----------
    s : :py:class:`hyperspy.signal.BaseSignal` (or subclass)
        The HyperSpy signal for which a thumbnail should be generated
    """
    # pylint: disable=broad-exception-caught
    # Parsing markers can potentially lead to errors, so to avoid
    # this any Exceptions are caught and logged instead of the files
    # not being loaded at all.
    try:
        markers_dict = _get_markers_dict(s, s.original_metadata.as_dictionary())
    except Exception as err:
        logger.warning("Markers could not be loaded from the file due to: %s", err)
        markers_dict = {}
    if markers_dict:
        markers_list = []
        for k, v in markers_dict.items():
            # convert each marker dictionary item into a Marker object
            markers_list.append(dict2marker(v, k))
        if len(markers_list) > 0:
            # add the Marker objects (in a list) to the signal
            s.add_marker(markers_list, permanent=True)


def sig_to_thumbnail(s, out_path: Path, dpi: int = 92):
    """
    Generate a preview thumbnail from an arbitrary HyperSpy signal.

    For a 2D signal, the signal from the first navigation position is used (most
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
    out_path
        A path to the desired thumbnail filename. All formats supported by
        :py:meth:`~matplotlib.figure.Figure.savefig` can be used.
    dpi : int
        The "dots per inch" resolution for the outputted figure

    Returns
    -------
    f : :py:class:`matplotlib.figure.Figure`
        Handle to a matplotlib Figure

    Notes
    -----
    This method heavily utilizes HyperSpy's existing plotting functions to
    figure out how to best display the image
    """
    # close all currently open plots to ensure we don't leave a mess behind
    # in memory
    plt.close("all")
    plt.rcParams["image.cmap"] = "gray"

    # Processing 1D signals (spectra, spectrum images, etc)
    if isinstance(s, hs_api.signals.Signal1D):
        return _plot_1d_signal(s, out_path, dpi)

    # Signal is an image of some sort, so we'll use hs.plot.plot_images
    if isinstance(s, hs_api.signals.Signal2D):
        return _plot_2d_signal(s, out_path, dpi)

    # Complex image, so plot power spectrum (like an FFT)
    if isinstance(s, hs_api.signals.ComplexSignal2D):
        return _plot_complex_signal(s, out_path, dpi)

    # if we have a different type of signal, just output a graphical
    # representation of the axis manager
    return _plot_axes_manager(s, out_path, dpi)


def _set_extent_and_save(mpl_axis, s, f, out_path, dpi):
    _set_title(mpl_axis, s.metadata.General.title)
    items = [mpl_axis, mpl_axis.title, mpl_axis.xaxis.label, mpl_axis.yaxis.label]
    for labels in _get_visible_labels(mpl_axis):
        items += labels
    extent = _full_extent(mpl_axis, items, pad=0.05).transformed(
        mpl_axis.figure.dpi_scale_trans.inverted(),
    )
    f.savefig(out_path, bbox_inches=extent, dpi=dpi)
    _pad_to_square(out_path, 500)


def _plot_1d_signal(s, out_path, dpi):
    # signal is single spectrum
    if s.axes_manager.navigation_dimension == 0:
        return _plot_spectrum(s, out_path, dpi)

    # signal is 1D linescan
    if s.axes_manager.navigation_dimension == 1:
        return _plot_linescan(s, out_path, dpi)

    # otherwise we have spectrum image:
    return _plot_si(s, out_path, dpi)


def _plot_2d_signal(s, out_path, dpi):
    # signal is single image
    if s.axes_manager.navigation_dimension == 0:
        return _plot_single_image(s, out_path, dpi)

    # we're looking at an image stack
    if s.axes_manager.navigation_dimension == 1:
        return _plot_image_stack(s, out_path, dpi)

    # This is a 4D-STEM type image, so display as tableau
    return _plot_tableau(s, out_path, dpi)


def _plot_spectrum(s, out_path, dpi):
    # pylint: disable=protected-access
    s.plot()
    # get signal plot figure
    f = s._plot.signal_plot.figure  # noqa: SLF001
    mpl_axis = f.get_axes()[0]
    # Change line color to matplotlib default
    mpl_axis.get_lines()[0].set_color(plt.get_cmap("tab10")(0))
    _set_extent_and_save(mpl_axis, s, f, out_path, dpi)
    return f


def _plot_linescan(s, out_path, dpi):
    # pylint: disable=protected-access
    s.plot()

    f = s._plot.navigator_plot.figure  # noqa: SLF001
    f.get_axes()[1].remove()  # remove colorbar scale
    mpl_axis = f.get_axes()[0]

    # workaround for above issue to remove pointer
    for line in list(mpl_axis.lines):
        line.remove()

    _set_extent_and_save(mpl_axis, s, f, out_path, dpi)
    return f


def _plot_si(s, out_path, dpi):
    nav_size = s.axes_manager.navigation_size
    max_nav_size = 9

    # temporarily unfold the signal so we can get spectra from all
    # over the navigation space easily:
    with s.unfolded():
        idx_to_plot = np.linspace(
            0,
            nav_size - 1,
            9 if nav_size >= max_nav_size else nav_size,
            dtype=int,
        )
        s_to_plot = [s.inav[i] for i in idx_to_plot]

    f = plt.figure()
    hs_api.plot.plot_spectra(s_to_plot, style="cascade", padding=0.1, fig=f)
    mpl_axis = plt.gca()

    _set_title(mpl_axis, s.metadata.General.title)
    mpl_axis.set_title(
        mpl_axis.get_title()
        + "\n"
        + r"$\bf{"
        + r"\ x\ ".join([str(x) for x in s.axes_manager.navigation_shape])
        + r"\ Spectrum\ Image}$",
    )

    # Load "watermark" stamp and rescale to be appropriately sized
    stamp = imread(_dir_path / "spectrum_image_logo.svg.png")
    stamp_width = int((mpl_axis.figure.get_size_inches() * f.dpi)[0] / 2.5)
    scaling = stamp_width / float(stamp.shape[0])
    stamp_height = int(float(stamp.shape[1]) * float(scaling))
    stamp = resize(stamp, (stamp_width, stamp_height), mode="wrap", anti_aliasing=True)

    # Create matplotlib annotation with image in center
    imagebox = OffsetImage(stamp, zoom=1, alpha=0.15)
    imagebox.image.axes = mpl_axis
    anchored_offset = AnchoredOffsetbox("center", pad=1, borderpad=0, child=imagebox)
    anchored_offset.patch.set_alpha(0)
    mpl_axis.add_artist(anchored_offset)

    # Pack figure and save
    f.tight_layout()
    f.savefig(out_path, dpi=dpi)
    _pad_to_square(out_path, 500)
    return f


def _plot_single_image(s, out_path, dpi):
    # check to see if this is a dm3/dm4; if so try to plot with
    # annotations
    orig_fname = s.metadata.General.original_filename
    if ".dm3" in orig_fname or ".dm4" in orig_fname:
        add_annotation_markers(s)
        s.plot(colorbar=False)
        plt.gca().axis("off")
    else:
        hs_api.plot.plot_images(
            [s],
            axes_decor="off",
            colorbar=False,
            scalebar="all",
            label=None,
        )

    f = plt.gcf()
    mpl_axis = plt.gca()
    _set_title(mpl_axis, s.metadata.General.title)
    f.tight_layout()
    f.savefig(out_path, dpi=dpi)
    _pad_to_square(out_path, 500)
    return f


def _plot_image_stack(s, out_path, dpi):
    plt.figure()
    plt.imshow(
        _project_image_stack(s, num=min(5, s.axes_manager.navigation_size), dpi=dpi),
    )
    mpl_axis = plt.gca()
    mpl_axis.set_position([0, 0, 1, 0.8])
    mpl_axis.set_axis_off()
    _set_title(mpl_axis, s.metadata.General.title)
    mpl_axis.set_title(
        mpl_axis.get_title()
        + "\n"
        + r"$\bf{"
        + str(s.axes_manager.navigation_size)
        + r"-member"
        + r"\ Image\ Series}$",
    )
    # use _full_extent to determine the bounding box needed to pick
    # out just the items we're interested in
    extent = _full_extent(mpl_axis, [mpl_axis, mpl_axis.title], pad=0.1).transformed(
        mpl_axis.figure.dpi_scale_trans.inverted(),
    )
    mpl_axis.figure.savefig(out_path, bbox_inches=extent, dpi=dpi)
    _pad_to_square(out_path, 500)
    return mpl_axis.figure


def _plot_tableau(s, out_path, dpi):
    asp_ratio = s.axes_manager.signal_shape[1] / s.axes_manager.signal_shape[0]
    f = plt.figure(figsize=(6, 6 * asp_ratio))
    if s.axes_manager.navigation_size >= 9:  # noqa: PLR2004
        square_n = 3
    elif s.axes_manager.navigation_size >= 4:  # noqa: PLR2004
        square_n = 2
    else:
        square_n = 1
    num_to_plot = square_n**2
    im_list = [None] * num_to_plot
    desc = r"\ x\ ".join([str(x) for x in s.axes_manager.navigation_shape])
    s.unfold_navigation_space()
    chunk_size = s.axes_manager.navigation_size // num_to_plot
    for i in range(num_to_plot):
        if square_n == 1:
            im_list = [s]
        else:
            im_list[i] = s.inav[i * chunk_size : (i + 1) * chunk_size].inav[
                chunk_size // 2
            ]
    axlist = hs_api.plot.plot_images(
        im_list,
        colorbar=None,
        axes_decor="off",
        tight_layout=True,
        scalebar=[0],
        per_row=square_n,
        fig=f,
    )

    # Make sure scalebar is fully on plot:
    txt = axlist[0].texts[0]
    left_extent = (
        txt.get_window_extent().transformed(axlist[0].transData.inverted()).bounds[0]
    )
    if left_extent < 0:
        # Move scalebar text over if it overlaps outside of axis
        txt.set_x(txt.get_position()[0] + left_extent * -1)

    f.suptitle(
        textwrap.fill(s.metadata.General.title, 60)
        + "\n"
        + r"$\bf{"
        + desc
        + r"\ Hyperimage}$",
    )
    f.tight_layout(
        rect=(
            0,
            0,
            1,
            f.texts[0]
            .get_window_extent()
            .transformed(f.transFigure.inverted())
            .bounds[1],
        ),
    )
    f.savefig(out_path, dpi=dpi)
    _pad_to_square(out_path, 500)
    return f


def _plot_complex_signal(s, out_path, dpi):
    # in tests, setting minimum to a percentile around 66% looks good
    s.amplitude.plot(
        interpolation="bilinear",
        norm="log",
        vmin=np.nanpercentile(s.amplitude.data, 66),
        colorbar=None,
        axes_off=True,
    )
    f = plt.gcf()
    mpl_axis = plt.gca()
    _set_title(mpl_axis, s.metadata.General.title)
    extent = _full_extent(mpl_axis, [mpl_axis, mpl_axis.title], pad=0.1).transformed(
        mpl_axis.figure.dpi_scale_trans.inverted(),
    )
    f.savefig(out_path, dpi=dpi, bbox_inches=extent)
    _pad_to_square(out_path, 500)
    return f


def _plot_axes_manager(s, out_path, dpi):
    f, mpl_axis = plt.subplots()
    mpl_axis.set_position([0, 0, 1, 1])
    mpl_axis.set_axis_off()

    # Remove axes_manager text
    ax_m = repr(s.axes_manager)
    ax_m = ax_m.split("\n")
    ax_m = ax_m[1:]
    ax_m = "\n".join(ax_m)

    mpl_axis.text(0.03, 0.9, s.metadata.General.title, fontweight="bold", va="top")
    mpl_axis.text(0.03, 0.85, "Could not generate preview image", va="top", color="r")
    mpl_axis.text(0.03, 0.8, "Axes information:", va="top", fontstyle="italic")
    mpl_axis.text(0.03, 0.75, ax_m, fontfamily="monospace", va="top")

    extent = _full_extent(mpl_axis, mpl_axis.texts, pad=0.1).transformed(
        mpl_axis.figure.dpi_scale_trans.inverted(),
    )

    f.savefig(out_path, bbox_inches=extent, dpi=dpi)
    _pad_to_square(out_path, 500)
    return f


def down_sample_image(
    fname: Path,
    out_path: Path,
    output_size: Optional[Tuple[int, int]] = None,
    factor: Optional[int] = None,
):
    """
    Load an image file from disk, down-sample it to the requested dpi, and save.

    Sometimes the data doesn't need to be loaded as a HyperSpy signal,
    and it's better just to down-sample existing image data (such as for .tif
    files created by the Quanta SEM).

    Parameters
    ----------
    fname
        The filepath that will be resized. All formats supported by
        :py:func:`PIL.Image.open` can be used
    out_path
        A path to the desired thumbnail filename. All formats supported by
        :py:meth:`PIL.Image.Image.save` can be used.
    output_size
        A tuple of ints specifying the width and height of the output image.
        Either this argument or ``factor`` should be provided (not both).
    factor
        The multiple of the image size to reduce by (i.e. a value of 2
        results in an image that is 50% of each original dimension). Either
        this argument or ``output_size`` should be provided (not both).
    """
    if output_size is None and factor is None:
        msg = "One of output_size or factor must be provided"
        raise ValueError(msg)
    if output_size is not None and factor is not None:
        msg = "Only one of output_size or factor should be provided"
        raise ValueError(msg)

    image = Image.open(fname)
    size = image.size

    if output_size is not None:
        resized = output_size
    else:
        resized = tuple(s // factor for s in size)

    if "I" in image.mode:
        image = image.point(lambda i: i * (1.0 / 256)).convert("L")

    image.thumbnail(resized, resample=_LANCZOS)
    image.save(out_path)
    _pad_to_square(out_path, new_width=500)

    plt.rcParams["image.cmap"] = "gray"
    f = plt.figure()
    f.gca().imshow(image)

    return f
