"""[lakshya] Tests for the current directional comparator surface."""

from team_analysis.comparator_surface import (
    ROLLING_HORIZONS,
    ROLLING_METRICS,
    PROTECTION_METRICS,
    fund_team_dimensions,
)


def test_surface_has_28_elevation_and_12_protection_dimensions():
    dimensions = fund_team_dimensions()

    assert len(ROLLING_HORIZONS) == 4
    assert len(ROLLING_METRICS) == 7
    assert len(PROTECTION_METRICS) == 12
    assert len(dimensions) == 40


def test_all_elevation_dimensions_are_up():
    dimensions = fund_team_dimensions()[:28]

    assert all(d.direction == "up" for d in dimensions)


def test_all_protection_dimensions_are_down():
    dimensions = fund_team_dimensions()[28:]

    assert all(d.direction == "down" for d in dimensions)


def test_surface_contains_no_folded_or_scale_dependent_metrics():
    names = {dimension.name for dimension in fund_team_dimensions()}

    assert not any("standard_deviation" in name for name in names)
    assert not any(name.endswith("_mean_nav") for name in names)
    assert not any(name.endswith("_latest") for name in names)
    assert not any("positive_periods" in name for name in names)
    assert not any("negative_periods" in name for name in names)
