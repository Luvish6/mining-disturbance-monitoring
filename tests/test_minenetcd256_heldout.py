import pyarrow as pa
import pytest

from scripts.minenetcd256_heldout import test_rows as choose_rows


class MetadataOnly:
    num_row_groups = 2

    def read_row_group(self, group, *, columns, use_threads):
        assert columns == ["domain"]
        return pa.table({"domain": [["old"]*6 + ["a"]*5 + ["b"]*2,
                                    ["b"]*3 + ["c"]*5 + ["d"]*5][group]})


def test_selection_is_site_disjoint_and_label_blind():
    result = choose_rows(MetadataOnly(), set("abcd") | {"old"}, {"old"})
    assert list(result) == ["a", "b", "c"]
    assert [len(v) for v in result.values()] == [5, 5, 5]
    assert result["b"] == [(0, 11), (0, 12), (1, 0), (1, 1), (1, 2)]
    with pytest.raises(ValueError, match="unofficial"):
        choose_rows(MetadataOnly(), set("abcd"), {"old"})
