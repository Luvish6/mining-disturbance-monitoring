from datetime import datetime, timezone

import pytest

from config.phase2_settings import Phase2Config
from config.settings import BEFORE, AFTER
from scripts.indian_ssl_cache import divide, replicas


def ms(day):
    return int(datetime.fromisoformat(day).replace(tzinfo=timezone.utc).timestamp()*1000)


def sources(season, prefix):
    days = [season.start[:8]+f"{i:02}" for i in range(1,5)]
    return [(f"{prefix}-{i}",ms(day)) for i,day in enumerate(days)]


def test_replicas_are_date_disjoint_and_keep_same_day_products_together():
    rows = sources(BEFORE,"s1")
    rows += [("another-slice",rows[0][1])]
    a,b = divide(rows[::-1],BEFORE,2)
    assert {t for _,t in a}.isdisjoint(t for _,t in b)
    assert {key for key,_ in a} == {"s1-0","s1-2","another-slice"}


def test_replicas_refuse_bad_dates_duplicate_products_and_cross_season_reuse():
    rows = sources(BEFORE,"s")
    with pytest.raises(ValueError, match="Duplicate"):
        divide(rows+[rows[0]],BEFORE,2)
    with pytest.raises(ValueError, match="Invalid scene"):
        divide(rows,AFTER,2)
    with pytest.raises(ValueError, match="Insufficient"):
        divide(rows[:3],BEFORE,2)
    first = dict(s1=rows,s2=sources(BEFORE,"o"))
    second = dict(s1=sources(AFTER,"other"),s2=sources(AFTER,"p"))
    second["s1"][1]=(rows[0][0],second["s1"][1][1])
    with pytest.raises(ValueError, match="Shared"):
        replicas([first,second],Phase2Config())
