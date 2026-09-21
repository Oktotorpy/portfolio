"""CineVote scheduling: the picking/voting windows are derived from the event date.

The movie night is at date D. Working backwards in **Europe/Prague** local time:

    D-6 00:00  picking opens
    D-2 00:00  picking closes, voting opens   (pick_deadline)
    D   00:00  voting closes, event concludes (vote_deadline)

i.e. 4 days to pick, then 2 days to vote, and the premiere day itself starts with
the winner already decided. All boundaries are Prague midnights; deadlines are
stored in the DB as UTC ISO strings.

If an event is created later than D-6 the window is compressed: voting keeps its
full last 2 days whenever it can, and if there is less than that left the
remaining time splits 2:1 (picking:voting), mirroring the 4:2 ratio.
"""

from datetime import datetime, date, timedelta, timezone

try:
    from zoneinfo import ZoneInfo
    TZ = ZoneInfo("Europe/Prague")
except Exception:  # pragma: no cover - no tzdata (e.g. a bare Windows dev box)
    TZ = None


def _last_sunday(year, month):
    d = date(year, month, 31)
    return d - timedelta(days=(d.weekday() + 1) % 7)


def _prague_offset(y, m, d, hour=0):
    """CET/CEST offset without tzdata: EU summer time runs from the last Sunday
    in March (01:00 UTC) to the last Sunday in October (01:00 UTC)."""
    naive = datetime(y, m, d, hour)
    start = datetime.combine(_last_sunday(y, 3), datetime.min.time()) + timedelta(hours=2)
    end = datetime.combine(_last_sunday(y, 10), datetime.min.time()) + timedelta(hours=3)
    return timezone(timedelta(hours=2 if start <= naive < end else 1))

PICK_DAYS = 4
VOTE_DAYS = 2


def now_utc():
    return datetime.now(timezone.utc)


def parse_iso(s):
    """Parse an ISO timestamp (naive ones are treated as UTC). None-safe."""
    if not s:
        return None
    try:
        dt = datetime.fromisoformat(str(s).replace("Z", "+00:00"))
    except ValueError:
        return None
    return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)


def to_utc_iso(dt):
    return dt.astimezone(timezone.utc).isoformat()


def prague_midnight(d):
    """00:00 Europe/Prague on the given date, as an aware datetime."""
    tz = TZ or _prague_offset(d.year, d.month, d.day)
    return datetime(d.year, d.month, d.day, tzinfo=tz)


def compute_deadlines(event_date, created_at=None):
    """-> (pick_deadline_utc_iso, vote_deadline_utc_iso) for an event date."""
    try:
        d = date.fromisoformat(str(event_date)[:10])
    except ValueError:
        return None, None

    vote_end = prague_midnight(d)                                  # D 00:00
    vote_start = vote_end - timedelta(days=VOTE_DAYS)              # D-2 00:00
    window_open = vote_end - timedelta(days=PICK_DAYS + VOTE_DAYS)  # D-6 00:00

    start = parse_iso(created_at) or now_utc()
    if start <= window_open:
        return to_utc_iso(vote_start), to_utc_iso(vote_end)

    if start < vote_start:
        # created inside the picking window: voting still gets its last 2 days
        return to_utc_iso(vote_start), to_utc_iso(vote_end)

    # less than 2 days left — compress what remains 2:1 (picking:voting)
    remaining = vote_end - start
    if remaining <= timedelta(0):
        return to_utc_iso(vote_end), to_utc_iso(vote_end)
    return to_utc_iso(start + remaining / 3), to_utc_iso(vote_end)
