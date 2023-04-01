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
The "Acquisition Activity" module.

Provides a class to represent and operate on an Acquisition Activity (as defined by the
NexusLIMS `Experiment` schema), as well as a helper method to cluster a list of
filenames by the files' modification times.
"""

import logging
import math
import os
from datetime import datetime as dt
from pathlib import Path
from timeit import default_timer
from typing import Any, Dict, List
from urllib.parse import quote, unquote
from xml.sax.saxutils import escape

import numpy as np
from lxml import etree
from scipy.signal import argrelextrema
from sklearn.model_selection import GridSearchCV, LeaveOneOut
from sklearn.neighbors import KernelDensity

from nexusLIMS.extractors import flatten_dict, parse_metadata
from nexusLIMS.utils import current_system_tz

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


def cluster_filelist_mtimes(filelist: List[str]) -> List[float]:
    """
    Cluster a list of files by modification time.

    Perform a statistical clustering of the timestamps (`mtime` values) of a
    list of files to find "relatively" large gaps in acquisition time. The
    definition of `relatively` depends on the context of the entire list of
    files. For example, if many files are simultaneously acquired,
    the "inter-file" time spacing between these will be very small (near zero),
    meaning even fairly short gaps between files may be important.
    Conversely, if files are saved every 30 seconds or so, the tolerance for
    a "large gap" will need to be correspondingly larger.

    The approach this method uses is to detect minima in the
    `Kernel Density Estimation`_ (KDE) of the file modification times. To
    determine the optimal bandwidth parameter to use in KDE, a `grid search`_
    over possible appropriate bandwidths is performed, using `Leave One Out`_
    cross-validation. This approach allows the method to determine the
    important gaps in file acquisition times with sensitivity controlled by
    the distribution of the data itself, rather than a pre-supposed optimum.
    The KDE minima approach was suggested `here`_.

    .. _Kernel Density Estimation: https://scikit-learn.org/stable/modules/density.html#kernel-density
    .. _grid search: https://scikit-learn.org/stable/modules/grid_search.html#grid-search
    .. _Leave One Out: https://scikit-learn.org/stable/modules/cross_validation.html#leave-one-out-loo
    .. _here: https://stackoverflow.com/a/35151947/1435788


    Parameters
    ----------
    filelist : List[str]
        The files (as a list) whose timestamps will be interrogated to find
        "relatively" large gaps in acquisition time (as a means to find the
        breaks between discrete Acquisition Activities)

    Returns
    -------
    aa_boundaries : List[float]
        A list of the `mtime` values that represent boundaries between
        discrete Acquisition Activities
    """  # noqa: E501
    logger.info("Starting clustering of file mtimes")
    start_timer = default_timer()
    mtimes = sorted([os.path.getmtime(f) for f in filelist])

    # remove duplicate file mtimes (since they cause errors below):
    mtimes = sorted(set(mtimes))
    m_array = np.array(mtimes).reshape(-1, 1)

    if len(mtimes) == 1:
        # if there was only one file, don't do any more processing and just
        # return the one mtime as the AA boundary
        return mtimes

    # mtime_diff is a discrete differentiation to find the time gap between
    # sequential files
    mtime_diff = [j - i for i, j in zip(mtimes[:-1], mtimes[1:])]

    # Bandwidth to use is uncertain, so do a grid search over possible values
    # from smallest to largest sequential mtime difference (logarithmically
    # biased towards smaller values). we do cross-validation using the Leave
    # One Out strategy and using the total log-likelihood from the KDE as
    # the score to maximize (goodness of fit)
    bandwidths = np.logspace(
        math.log(min(mtime_diff)),
        math.log(max(mtime_diff)),
        35,
        base=math.e,
    )
    logger.info("KDE bandwidth grid search")
    grid = GridSearchCV(
        KernelDensity(kernel="gaussian"),
        {"bandwidth": bandwidths},
        cv=LeaveOneOut(),
        n_jobs=-1,
    )
    grid.fit(m_array)
    bandwidth = grid.best_params_["bandwidth"]
    logger.info("Using bandwidth of %.3f minutes for KDE", bandwidth)

    # Calculate AcquisitionActivity boundaries by "clustering" the timestamps
    # using KDE using KDTree nearest neighbor estimates, and the previously
    # identified "optimal" bandwidth
    kde = KernelDensity(kernel="gaussian", bandwidth=bandwidth)
    kde: KernelDensity = kde.fit(m_array)
    s = np.linspace(m_array.min(), m_array.max(), num=len(mtimes) * 10)
    scores = kde.score_samples(s.reshape(-1, 1))

    mins = argrelextrema(scores, np.less)[0]  # the minima indices
    aa_boundaries = [s[m] for m in mins]  # the minima mtime values
    end_timer = default_timer()
    logger.info(
        "Detected %i activities in %.2f seconds",
        len(aa_boundaries) + 1,
        end_timer - start_timer,
    )

    return aa_boundaries


def _escape(val: Any) -> Any:
    """
    Check to see if a value needs to be escaped and escape it or just return it as is.

    Parameters
    ----------
    val
        The value to conditionally escape

    Returns
    -------
    Any
        The value either as-is or escaped
    """
    if isinstance(val, str) and any(c in val for c in "<&"):
        return escape(val)
    return val


def _add_dataset_element(
    file: str,
    aq_ac_xml_el: etree.Element,
    meta: Dict,
    unique_meta: Dict,
    warning: List,
):
    # escape any bad characters in the filename
    file = _escape(file)

    # build path to thumbnail
    rel_fname = file.replace(os.environ["mmfnexus_path"], "")
    rel_thumb_name = f"{rel_fname}.thumb.png"

    # encode for safe URLs
    rel_fname = quote(rel_fname)
    rel_thumb_name = quote(rel_thumb_name)

    # f is string; um is a dictionary, w is a list
    dset_el = etree.SubElement(aq_ac_xml_el, "dataset")
    dset_el.set("type", str(meta["DatasetType"]))
    dset_el.set("role", "Experimental")

    dset_name_el = etree.SubElement(dset_el, "name")
    dset_name_el.text = Path(file).name

    dset_loc_el = etree.SubElement(dset_el, "location")
    dset_loc_el.text = rel_fname

    # check if preview image exists before adding it XML structure
    if rel_thumb_name[0] == "/":
        test_path = Path(os.environ["nexusLIMS_path"]) / unquote(rel_thumb_name)[1:]
    else:  # pragma: no cover
        # this shouldn't happen, but just in case...
        test_path = Path(os.environ["nexusLIMS_path"]) / unquote(rel_thumb_name)

    if test_path.exists():
        dset_prev_el = etree.SubElement(dset_el, "preview")
        dset_prev_el.text = rel_thumb_name

    for meta_k, meta_v in sorted(unique_meta.items(), key=lambda i: i[0].lower()):
        if meta_k not in ["warnings", "DatasetType"]:
            meta_v = _escape(meta_v)  # noqa: PLW2901
            meta_el = etree.SubElement(dset_el, "meta")
            meta_el.set("name", str(meta_k))
            if meta_k in warning:
                meta_el.set("warning", "true")
            meta_el.text = str(meta_v)

    return aq_ac_xml_el


class AcquisitionActivity:  # pylint: disable=too-many-instance-attributes
    """
    A collection of files/metadata attributed to a physical acquisition activity.

    Instances of this class correspond to AcquisitionActivity nodes in the
    `NexusLIMS schema <https://data.nist.gov/od/dm/nexus/experiment/v1.0>`_

    Parameters
    ----------
    start : datetime.datetime
        The start point of this AcquisitionActivity
    end : datetime.datetime
        The end point of this AcquisitionActivity
    mode : str
        The microscope mode for this AcquisitionActivity (i.e. 'IMAGING',
        'DIFFRACTION', 'SCANNING', etc.)
    unique_params : set
        A set of dictionary keys that comprises all unique metadata keys
        contained within the files of this AcquisitionActivity
    setup_params : dict
        A dictionary containing metadata about the data that is shared
        amongst all data files in this AcquisitionActivity
    unique_meta : list
        A list of dictionaries (one for each file in this
        AcquisitionActivity) containing metadata key-value pairs that are
        unique to each file in ``files`` (i.e. those that could not be moved
        into ``setup_params``)
    files : list
        A list of filenames belonging to this AcquisitionActivity
    previews : list
        A list of filenames pointing to the previews for each file in
        ``files``
    meta : list
        A list of dictionaries containing the "important" metadata for each
        file in ``files``
    warnings : list
        A list of metadata values that may be untrustworthy because of the
        software
    """

    def __init__(  # pylint: disable=too-many-arguments # noqa: 0913
        self,
        start=None,
        end=None,
        mode="",
        unique_params=None,
        setup_params=None,
        unique_meta=None,
        files=None,
        previews=None,
        meta=None,
        warnings=None,
    ):
        """Create a new AcquisitionActivity."""
        self.start = start if start is not None else dt.now(tz=current_system_tz())
        self.end = end if end is not None else dt.now(tz=current_system_tz())
        self.mode = mode
        self.unique_params = set() if unique_params is None else unique_params
        self.setup_params = setup_params
        self.unique_meta = unique_meta
        self.files = [] if files is None else files
        self.previews = [] if previews is None else previews
        self.meta = [] if meta is None else meta
        self.warnings = [] if warnings is None else warnings

    def __repr__(self):
        """Return custom representation of AcquisitionActivity."""
        return (
            f"{self.mode:<12} AcquisitionActivity; "
            f"start: {self.start.isoformat()}; "
            f"end: {self.end.isoformat()}"
        )

    def __str__(self):
        """Return custom string representation of AcquisitionActivity."""
        return f"{self.start.isoformat()} AcquisitionActivity {self.mode}"

    def add_file(self, fname: Path, *, generate_preview=True):
        """
        Add file to AcquisitionActivity.

        Add a file to this activity's file list, parse its metadata (storing
        a flattened copy of it to this activity), generate a preview
        thumbnail, get the file's type, and a lazy HyperSpy signal.

        Parameters
        ----------
        fname : str
            The file to be added to the file list
        generate_preview : bool
            Whether or not to create the preview thumbnail images
        """
        if fname.exists():
            self.files.append(str(fname))
            gen_prev = generate_preview
            meta, preview_fname = parse_metadata(fname, generate_preview=gen_prev)

            if meta is None:
                # Something bad happened, so we need to alert the user
                logger.warning("Could not parse metadata of %s", fname)
            else:
                self.previews.append(preview_fname)
                self.meta.append(flatten_dict(meta["nx_meta"]))
                if "warnings" in meta["nx_meta"]:
                    self.warnings.append(
                        [" ".join(w) for w in meta["nx_meta"]["warnings"]],
                    )
                else:
                    self.warnings.append([])
        else:
            msg = f"{fname} was not found"
            raise FileNotFoundError(msg)
        logger.debug("appended %s to files", fname)
        logger.debug("self.files is now %s", self.files)

    def store_unique_params(self):
        """
        Store unique metadata keys.

        Analyze the metadata keys contained in this AcquisitionActivity and
        store the unique values in a set (``self.unique_params``).
        """
        # self.meta is a list of dictionaries
        for meta in self.meta:
            self.unique_params.update(meta.keys())

    def store_setup_params(self, values_to_search=None):
        """
        Store common metadata keys as "setup parameters".

        Search the metadata of files in this AcquisitionActivity for those
        containing identical values over all files, which will then be defined
        as parameters attributed to experimental setup, rather than individual
        datasets.

        Stores a dictionary containing the metadata keys and values that are
        consistent across all files in this AcquisitionActivity as an
        attribute (``self.setup_params``).

        Parameters
        ----------
        values_to_search : list
            A list (or tuple, set, or other iterable type) containing values to
            search for in the metadata dictionary list. If None (default), all
            values contained in any file will be searched.
        """
        # Make sure unique params are defined before proceeding:
        if self.unique_params == set():
            logger.info("Storing unique parameters for files in AcquisitionActivity")
            self.store_unique_params()

        if len(self.files) == 1:
            logger.info(
                "Only one file found in this activity, so leaving "
                "metadata associated with the file, rather than "
                "activity",
            )
            self.setup_params = {}
            return

        if values_to_search is None:
            values_to_search = self.unique_params

        # meta will be individual dictionaries, since self.meta is list of dicts
        i = 0
        setup_params = {}
        for meta, _file in zip(self.meta, self.files):
            # loop through the values_to_search
            # using .copy() on the set allows us to remove values during each
            # iteration, as described in:
            # https://stackoverflow.com/a/22847851/1435788
            for vts in values_to_search.copy():
                # for the first iteration through the list of dictionaries,
                # store any value found for a parameter
                # as a "setup parameter". if it is not found, do not store it
                # and remove from values_to_search to prevent it being searched
                # on subsequent iterations.
                if i == 0:
                    if vts in meta:
                        # this value was found in meta, so store it
                        setup_params[vts] = meta[vts]
                        logger.debug(
                            "iter: %i; adding %s = %s to setup_params",
                            i,
                            vts,
                            meta[vts],
                        )
                    else:
                        # this value wasn't present in meta, so it can't be
                        # common to all, so remove it:
                        logger.debug("iter: %i; removing %s", i, vts)
                        values_to_search.remove(vts)
                # On the subsequent iterations test if values are same/different
                # If different, then remove the key from setup_params and
                # values_to_search, so at the end only identical values remain
                # and duplicate value checks are minimized
                else:
                    if vts not in setup_params:
                        # this condition should probably not be reached,
                        # but if it is, it means this value, which should
                        # have already been added to setup_params is somehow
                        # new, so delete vts from values to search
                        logger.debug(
                            "iter: %i; removing %s",
                            i,
                            vts,
                        )  # pragma: no cover
                        values_to_search.remove(vts)  # pragma: no cover
                    if vts in meta and setup_params[vts] != meta[vts]:
                        # value does not match, so this must be a
                        # individual dataset metadata, so remove it from
                        # setup_params, and remove it from values_to_search
                        logger.debug(
                            "iter: %i; vts=%s - "
                            "meta[vts]=%s != setup_params[vts]=%s; "
                            "removing %s from setup_params and values to search",
                            i,
                            vts,
                            meta[vts],
                            setup_params[vts],
                            vts,
                        )
                        del setup_params[vts]
                        values_to_search.remove(vts)
            i += 1

        self.setup_params = setup_params

    def store_unique_metadata(self):
        """
        Store unique metadata keys as unique to each file.

        For each file in this AcquisitionActivity, stores the metadata that
        is unique rather than common to the entire AcquisitionActivity (which
        are kept in ``self.setup_params``.
        """
        if self.setup_params is None:
            logger.warning(
                "%s -- setup_params has not been defined; call store_setup_params() "
                "prior to using this method. Nothing was done.",
                self,
            )
            return

        unique_meta = []
        for meta in self.meta:
            tmp_unique = {}
            # loop through each metadata dict, and if a given key k in meta is
            # not present in self.setup_params, add it to the
            # current dictionary (u_m) of unique_meta
            for k, v in meta.items():
                if k not in self.setup_params:
                    # this means k is unique to this file, so add it to
                    # unique_meta
                    tmp_unique[k] = v
            unique_meta.append(tmp_unique)

        # store what we calculated as unique metadata into the attribute
        self.unique_meta = unique_meta

    def as_xml(self, seqno, sample_id):
        """
        Translate AcquisitionActivity to an XML representation.

        Build an XML (``lxml``) representation of this AcquisitionActivity (for
        use in instances of the NexusLIMS schema).

        Parameters
        ----------
        seqno : int
            An integer number representing what number activity this is in a
            sequence of activities.
        sample_id : str
            A unique identifier pointing to a sample identifier. No checks
            are done on this value; it is merely reproduced in the XML output

        Returns
        -------
        activity_xml : str
            A string representing this AcquisitionActivity (note: is not a
            properly-formed complete XML document since it does not have a
            header or namespace definitions)
        """
        aq_ac_xml_el = etree.Element("acquisitionActivity")
        aq_ac_xml_el.set("seqno", str(seqno))
        start_time_el = etree.SubElement(aq_ac_xml_el, "startTime")
        start_time_el.text = self.start.isoformat()
        sample_id_el = etree.SubElement(aq_ac_xml_el, "sampleID")
        sample_id_el.text = sample_id

        setup_el = etree.SubElement(aq_ac_xml_el, "setup")

        for param_k, param_v in sorted(
            self.setup_params.items(),
            key=lambda i: i[0].lower(),
        ):
            # metadata values to skip in XML output
            if param_k not in ["warnings", "DatasetType"]:
                param_v = _escape(param_v)  # noqa: PLW2901
                # for setup parameters, a key in the first dataset's warning
                # list is the same as in all of them
                pk_warning = param_k in self.warnings[0]
                param_el = etree.SubElement(setup_el, "param")
                param_el.set("name", str(param_k))
                if pk_warning:
                    param_el.set("warning", "true")
                param_el.text = str(param_v)

        for _file, meta, unique_meta, warning in zip(
            self.files,
            self.meta,
            self.unique_meta,
            self.warnings,
        ):
            aq_ac_xml_el = _add_dataset_element(
                _file,
                aq_ac_xml_el,
                meta,
                unique_meta,
                warning,
            )

        return aq_ac_xml_el
