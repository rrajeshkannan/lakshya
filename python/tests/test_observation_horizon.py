import pytest

from mission.observation_horizon import (
    SUPPORTED_OBSERVATION_HORIZONS,
    nearest_supported_horizon,
)


def test_canonical_observation_horizons_are_shared_ladder():
    assert SUPPORTED_OBSERVATION_HORIZONS == (3, 5, 7, 10)


@pytest.mark.parametrize(
    ("requested", "expected"),
    [
        (3, 3),
        (4, 3),
        (5, 5),
        (6, 5),
        (7, 7),
        (8, 7),
        (9, 7),
        (10, 10),
        (11, 10),
        (12, 10),
    ],
)
def test_nearest_supported_horizon_uses_longest_supported_not_beyond_request(
    requested,
    expected,
):
    assert nearest_supported_horizon(requested) == expected


def test_horizon_below_ladder_has_no_supported_horizon():
    assert nearest_supported_horizon(2) is None


def test_non_positive_horizon_is_rejected():
    with pytest.raises(ValueError, match="positive"):
        nearest_supported_horizon(0)
