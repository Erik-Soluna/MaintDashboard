"""
Canonical date-stepping for maintenance schedules.

All "add one frequency period to a date" math lives here so every call site
(schedule due-date calculation, recurrence generation, category/global/override
schedules) steps dates the same way. Uses ``dateutil.relativedelta`` so calendar
months and years are handled correctly (leap years, month-end clamping) instead
of 30/90/180/365-day approximations that drift over time.

These functions operate on ``date`` objects only and are timezone-agnostic; the
timezone of the resulting datetime is handled separately at the storage layer.
"""

from dateutil.relativedelta import relativedelta

# Frequency key -> relativedelta step for one period.
_FREQUENCY_STEP = {
    'daily': relativedelta(days=1),
    'weekly': relativedelta(weeks=1),
    'monthly': relativedelta(months=1),
    'quarterly': relativedelta(months=3),
    'semi_annual': relativedelta(months=6),
    'annual': relativedelta(years=1),
}


def _step(frequency, frequency_days):
    """Return the relativedelta for one period of the given frequency."""
    if frequency == 'custom' or frequency not in _FREQUENCY_STEP:
        # Custom or unknown frequency: fall back to an explicit day count.
        return relativedelta(days=(frequency_days or 365))
    return _FREQUENCY_STEP[frequency]


def add_one_period(base_date, frequency, frequency_days=None):
    """Return ``base_date`` advanced by one period of ``frequency``.

    ``frequency`` is one of the MaintenanceSchedule FREQUENCY_CHOICES keys
    (daily/weekly/monthly/quarterly/semi_annual/annual/custom). For ``custom``
    (or an unrecognized value) ``frequency_days`` is used as a day count.
    """
    return base_date + _step(frequency, frequency_days)


def add_n_periods(base_date, frequency, n, frequency_days=None):
    """Return ``base_date`` advanced by ``n`` periods of ``frequency``."""
    if n <= 0:
        return base_date
    return base_date + (_step(frequency, frequency_days) * n)
