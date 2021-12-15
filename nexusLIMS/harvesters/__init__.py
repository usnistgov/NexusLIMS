"""
This module contains a top-level class to represent calendar reservations and
associated metadata harvest metadata from various calendar sources.
The expectation is that submodules of this module will have a method named
``res_event_from_session`` implemented to handle fetching a ReservationEvent
object from a :py:class:`nexusLIMS.db.session_handler.Session` object.
"""
from typing import Union, List
from nexusLIMS.instruments import Instrument
from datetime import datetime
from lxml import etree
import os as _os

CA_BUNDLE_PATH = _os.path.join(_os.path.dirname(__file__),
                               "cert_bundle.pem")


class ReservationEvent:
    """
    A representation of a single calendar reservation, independent of the type
    of calendar the reservation was made with. ``ReservationEvent``
    is a common interface that is used by the record building code.
    Any attribute can be None to indicate it was not present or no value was
    provided. The :py:meth:`as_xml` method is used to serialize the information
    contained within a ``ReservationEvent`` into an XML representation that is
    compatible with the Nexus Facility ``Experiment`` schema.

    Attributes
    ----------
    experiment_title
        The title of the event
    instrument
        The instrument associated with this reservation
    last_updated : datetime.datetime
        The time this event was last updated
    username
        The NIST "short" username of the user indicated in this event
    user_full_name
        The full name of the user for this event
    created_by
        The NIST "short" username of the user that created this event
    created_by_full_name
        The full name of the user that created this event
    start_time
        The time this event was scheduled to start
    end_time
        The time this event was scheduled to end
    reservation_type
        The "type" or category of this event (such as User session, service,
        etc.))
    experiment_purpose
        The user-entered purpose of this experiment
    sample_details
        A list of the user-entered sample details for this experiment. The
        length of the list must match that given in ``sample_pid`` and
        ``sample_name``.
    sample_pid
        A list of sample PIDs provided by the user. The
        length of the list must match that given in ``sample_details`` and
        ``sample_name``.
    sample_name
        A list of user-friendly sample names (not a PID). The
        length of the list must match that given in ``sample_details`` and
        ``sample_pid``.
    project_name
        A list of the user-entered project names for this experiment. The
        length of the list must match that given in ``project_id`` and
        ``project_ref``.
    project_id
        A list of the specific project IDs within a research group/division. The
        length of the list must match that given in ``project_name`` and
        ``project_ref``.
    project_ref
        A list of (optional) links to this project in another database. The
        length of the list must match that given in ``project_name`` and
        ``project_id``.
    internal_id
        The identifier assigned to this event (if any) by the calendaring system
    division
        An identifier of the division this experiment was performed for (i.e.
        the user's division)
    group
        An identifier of the group this experiment was performed for (i.e.
        the user's group)
    """

    def __init__(self,
                 experiment_title: Union[str, None] = None,
                 instrument: Union[Instrument, None] = None,
                 last_updated: Union[datetime, None] = None,
                 username: Union[str, None] = None,
                 user_full_name: Union[str, None] = None,
                 created_by: Union[str, None] = None,
                 created_by_full_name: Union[str, None] = None,
                 start_time: Union[datetime, None] = None,
                 end_time: Union[datetime, None] = None, 
                 reservation_type: Union[str, None] = None,
                 experiment_purpose: Union[str, None] = None,
                 sample_details: Union[List[Union[str, None]], None] = None,
                 sample_pid: Union[List[Union[str, None]], None] = None,
                 sample_name: Union[List[Union[str, None]], None] = None,
                 project_name: Union[List[Union[str, None]], None] = None,
                 project_id: Union[List[Union[str, None]], None] = None,
                 project_ref: Union[List[Union[str, None]], None] = None,
                 internal_id: Union[str, None] = None,
                 division: Union[str, None] = None,
                 group: Union[str, None] = None):
        self.experiment_title = experiment_title
        self.instrument = instrument
        self.last_updated = last_updated
        self.username = username
        self.user_full_name = user_full_name
        self.created_by = created_by
        self.created_by_full_name = created_by_full_name
        self.start_time = start_time
        self.end_time = end_time
        self.reservation_type = reservation_type
        self.experiment_purpose = experiment_purpose

        # coerce sample arguments into lists
        self.sample_details = \
            sample_details if isinstance(sample_details, list) else \
            [sample_details]
        self.sample_pid = \
            sample_pid if isinstance(sample_pid, list) else [sample_pid]
        self.sample_name = \
            sample_name if isinstance(sample_name, list) else  [sample_name]

        # coerce project arguments into lists
        self.project_name = \
            project_name if isinstance(project_name, list) else [project_name]
        self.project_id = \
            project_id if isinstance(project_id, list) else [project_id]
        self.project_ref = \
            project_ref if isinstance(project_ref, list) else [project_ref]

        self.internal_id = internal_id
        self.division = division
        self.group = group

        # raise error if all sample values are not none and have different
        # lengths (this shouldn't happen):
        self._check_arg_lists()

    def _check_arg_lists(self):
        for check_name, arg_names, lists in zip(
                ['sample', 'project'],
                ['[sample_details, sample_pid, sample_name]',
                 '[project_name, project_id, project_ref]'],
                [[self.sample_details, self.sample_pid, self.sample_name],
                 [self.project_name, self.project_id, self.project_ref]]):
            if all(x is not None for x in lists):
                length = len(lists[0])
                if not all(len(lst) == length for lst in lists[1:]):
                    raise ValueError(f"Length of {check_name} arguments must "
                                     f"be the same. The lengths of the "
                                     f"following arguments were "
                                     f"{arg_names} : "
                                     f"{[len(l) for l in lists]}")

    def __repr__(self):
        if self.username and self.start_time and self.end_time:
            return f'Event for {self.username} on {self.instrument.name} ' \
                   f'from ' \
                   f'{self.instrument.localize_datetime(self.start_time).isoformat()} ' \
                   f'to {self.instrument.localize_datetime(self.end_time).isoformat()}'
        else:
            return f'No matching calendar event' + \
                   (f' for {self.instrument.name}' if self.instrument else '')

    def as_xml(self) -> etree.Element:
        """
        Get an XML representation of this ReservationEvent

        Returns
        -------
        root : lxml.etree.Element
            The reservation event serialized as XML that matches the
            Nexus Experiment schema
        """
        root = etree.Element("root")

        # top-level nodes
        title_el = etree.SubElement(root, "title")
        if self.experiment_title:
            title_el.text = self.experiment_title
        else:
            title_el.text = f"Experiment on the " \
                            f"{self.instrument.schema_name}"
            if self.start_time:
                title_el.text += \
                    f" on {self.start_time.strftime('%A %b. %d, %Y')}"
        if self.internal_id:
            id_el = etree.SubElement(root, "id")
            id_el.text = self.internal_id

        # summary node
        summary_el = etree.SubElement(root, "summary")
        if self.user_full_name:
            experimenter_el = etree.SubElement(summary_el, "experimenter")
            experimenter_el.text = self.user_full_name
        elif self.username:
            experimenter_el = etree.SubElement(summary_el, "experimenter")
            experimenter_el.text = self.username
        if self.instrument:
            instr_el = etree.SubElement(summary_el, "instrument")
            instr_el.text = self.instrument.schema_name
            # temporary workaround for duplicate harvesters for some instruments
            if self.instrument.harvester == 'nemo' and \
                    self.instrument.name.endswith('_n'):  # pragma: no cover
                pid = self.instrument.name.strip('_n')
            else:
                pid = self.instrument.name
            instr_el.set('pid', pid)
        if self.start_time:
            start_el = etree.SubElement(summary_el, "reservationStart")
            if self.instrument is not None:
                start_el.text = self.instrument.localize_datetime(
                    self.start_time).isoformat()
            else:
                start_el.text = self.start_time.isoformat()
        if self.end_time:
            end_el = etree.SubElement(summary_el, "reservationEnd")
            if self.instrument is not None:
                end_el.text = self.instrument.localize_datetime(
                    self.end_time).isoformat()
            else:
                end_el.text = self.end_time.isoformat()
        if self.experiment_purpose:
            motivation_el = etree.SubElement(summary_el, "motivation")
            motivation_el.text = self.experiment_purpose

        # sample nodes
        if self.sample_pid is not None:
            # if any of the sample arguments are not none, they should be
            # lists, so we should create a sample element for each one
            for pid, name, details in zip(self.sample_pid, self.sample_name,
                                          self.sample_details):
                # create one sample subelement for each sample in our lists
                sample_el = etree.SubElement(root, "sample")
                if pid is not None:
                    sample_el.set("ref", pid)
                if name is not None:
                    sample_name_el = etree.SubElement(sample_el, "name")
                    sample_name_el.text = name
                if details is not None:
                    sample_detail_el = etree.SubElement(sample_el,
                                                        "description")
                    sample_detail_el.text = details

        # project nodes
        if self.project_name is not None:
            for name, pid, ref in zip(self.project_name, self.project_id,
                                     self.project_ref):
                project_el = etree.SubElement(root, "project")
                if name is not None:
                    project_name_el = etree.SubElement(project_el, "name")
                    project_name_el.text = name
                if self.division is not None:
                    division_el = etree.SubElement(project_el, "division")
                    division_el.text = self.division
                if self.group is not None:
                    group_el = etree.SubElement(project_el, "group")
                    group_el.text = self.group
                if pid is not None:
                    proj_id_el = etree.SubElement(project_el, "project_id")
                    proj_id_el.text = pid
                if ref is not None:
                    proj_ref_el = etree.SubElement(project_el, "ref")
                    proj_ref_el.text = ref

        return root
