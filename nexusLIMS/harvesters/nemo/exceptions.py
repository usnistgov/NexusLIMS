"""Contains some exceptions specific to NEMO harvesting."""


class NoDataConsentError(Exception):
    """A user has not given their consent to have data harvested."""


class NoMatchingReservationError(Exception):
    """No matching reservation (we cannot assume consent to harvest data)."""
