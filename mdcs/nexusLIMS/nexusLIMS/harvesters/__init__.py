"""
This module contains a top-level class to represent calendar reservations and
associated metadata harvest metadata from
various calendar
sources.
"""
from lxml import etree


class ReservationEvent:
    """
    A representation of a single calendar reservation, independent of the type
    of calendar the reservation was made with. ``ReservationEvent``
    is a common interface that is used by the record building code. Sub-modules
    should contain methods return an instance of this class as needed by
    parsing their data as needed. Any attribute can be None to indicate it was
    not present or no value was provided.

    Attributes
    ----------
    experiment_title : str
        The title of the event
    instrument : ~nexusLIMS.instruments.Instrument
        The instrument associated with this reservation
    last_updated : datetime.datetime
        The time this event was last updated
    username : str
        The NIST "short" username of the user indicated in this event
    created_by : str
        The NIST "short" username of the user that created this event
    start_time : datetime.datetime
        The time this event was scheduled to start
    end_time : datetime.datetime
        The time this event was scheduled to end
    reservation_type : str
        The "type" or category of this event (such as User session, service,
        etc.))
    experiment_purpose : str
        The user-entered purpose of this experiment
    sample_details : str
        The user-entered sample details for this experiment
    sample_pid : :obj:`list` of :obj:`str`
        A list of sample names or PIDs provided by the user
    sample_name : str
        A user-friendly sample name (not a PID)
    project_name : str
        The user-entered project identifier for this experiment
    project_id : str or list
        The specific project ID within a research group/division. If a ``str``
        is provided, it will be converted to a list internally
    project_ref : str
        An (optional) link to this project in another database
    internal_id : str
        The identifier assigned to this event (if any) by the calendaring system
    division : str
        An identifier of the division this experiment was performed for (i.e.
        the user's division)
    group : str
        An identifier of the group this experiment was performed for (i.e.
        the user's group)
    """

    def __init__(self, experiment_title=None, instrument=None,
                 last_updated=None, username=None, created_by=None,
                 start_time=None, end_time=None, reservation_type=None,
                 experiment_purpose=None, sample_details=None, sample_pid=None,
                 sample_name=None, project_name=None,
                 project_id=None, project_ref=None, internal_id=None,
                 division=None, group=None):
        self.experiment_title = experiment_title
        self.instrument = instrument
        self.last_updated = last_updated
        self.username = username
        self.created_by = created_by
        self.start_time = start_time
        self.end_time = end_time
        self.reservation_type = reservation_type
        self.experiment_purpose = experiment_purpose
        self.sample_details = sample_details
        if isinstance(sample_pid, (str,)):
            self.sample_pid = [sample_pid]
        else:
            self.sample_pid = sample_pid
        self.sample_name = sample_name
        self.project_name = project_name
        self.project_id = project_id
        self.project_ref = project_ref
        self.internal_id = internal_id
        self.division = division
        self.group = group

    def __repr__(self):
        if self.username and self.start_time and self.end_time:
            return f'Event for {self.username} on {self.instrument.name} ' \
                   f'from {self.start_time.isoformat()} to ' \
                   f'{self.end_time.isoformat()}'
        else:
            return f'No matching calendar event' + \
                   (f' for {self.instrument.name}' if self.instrument else '')

    def as_xml(self):
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
        if self.username:
            experimenter_el = etree.SubElement(summary_el, "experimenter")
            experimenter_el.text = self.username
        if self.instrument:
            instr_el = etree.SubElement(summary_el, "instrument")
            instr_el.text = self.instrument.schema_name
            instr_el.set('pid', self.instrument.name)
        if self.start_time:
            start_el = etree.SubElement(summary_el, "reservationStart")
            start_el.text = self.start_time.isoformat()
        if self.end_time:
            end_el = etree.SubElement(summary_el, "reservationEnd")
            end_el.text = self.end_time.isoformat()
        if self.experiment_purpose:
            motivation_el = etree.SubElement(summary_el, "motivation")
            motivation_el.text = self.experiment_purpose

        # sample node
        sample_el = etree.SubElement(root, "sample")
        if self.sample_pid:
            # just use the first one for now; eventually we should support
            # multiple sample entry on the form, but we need to figure out
            # how to have people input that; this will result in multiple
            # sample nodes
            sample_el.set("id", self.sample_pid[0])
        if self.sample_name:
            sample_name_el = etree.SubElement(sample_el, "name")
            sample_name_el.text = self.sample_name
        if self.sample_details:
            sample_detail_el = etree.SubElement(sample_el, "description")
            sample_detail_el.text = self.sample_details

        # project node
        project_el = etree.SubElement(root, "project")
        if self.project_name:
            project_name_el = etree.SubElement(project_el, "name")
            project_name_el.text = self.project_name
        if self.division:
            division_el = etree.SubElement(project_el, "division")
            division_el.text = self.division
        if self.group:
            group_el = etree.SubElement(project_el, "group")
            group_el.text = self.group
        if self.project_id:
            proj_id_el = etree.SubElement(project_el, "project_id")
            proj_id_el.text = self.project_id
        if self.project_ref:
            proj_ref_el = etree.SubElement(project_el, "ref")
            proj_ref_el.text = self.project_ref

        return root
