from pathlib import Path

import pandas as pd
import pytest

from fund_analysis.admissible_funds import load_admissible_funds


def test_load_admissible_funds(tmp_path: Path):
    path = tmp_path / "funds_admissible.csv"

    pd.DataFrame(
        [
            {
                "scheme_name": "Axis Small Cap Fund",
                "isin": "INF846K01K35",
                "category": "Small Cap Fund",
            },
            {
                "scheme_name": "Parag Parikh Flexi Cap Fund",
                "isin": "INF879O01027",
                "category": "Flexi Cap Fund",
            },
        ]
    ).to_csv(path, index=False)

    funds = load_admissible_funds(path)

    assert len(funds) == 2

    assert funds[0].name == "Axis Small Cap Fund"
    assert funds[0].isin == "INF846K01K35"
    assert funds[0].category == "Small Cap Fund"

    assert funds[1].name == "Parag Parikh Flexi Cap Fund"
    assert funds[1].isin == "INF879O01027"
    assert funds[1].category == "Flexi Cap Fund"


def test_missing_required_column(tmp_path: Path):
    path = tmp_path / "funds_admissible.csv"

    pd.DataFrame(
        [
            {
                "scheme_name": "Axis Small Cap Fund",
                "isin": "INF846K01K35",
            }
        ]
    ).to_csv(path, index=False)

    with pytest.raises(ValueError, match="missing required columns"):
        load_admissible_funds(path)
