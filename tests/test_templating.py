from datetime import datetime, timedelta, timezone

from roost_web.templating import _relative_dt


def test_relative_dt_uses_the_same_units_both_ways() -> None:
    now = datetime.now(tz=timezone.utc)
    assert _relative_dt(None) == "—"
    assert _relative_dt(now - timedelta(minutes=3, seconds=5)) == "3m ago"
    assert _relative_dt(now + timedelta(days=3, hours=1)) == "in 3d"
    assert _relative_dt(now + timedelta(hours=5, minutes=1)) == "in 5h"
