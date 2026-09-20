from decimal import Decimal

import pytest

from lts.models import FormationIntentRow, TargetFormation
from lts.purpose_allocation import validate_purpose_target_allocation


def test_validates_each_purpose_as_its_own_pre_tax_allocation():
    formation = TargetFormation(
        rows=(
            FormationIntentRow("Edu_A", "AAA", Decimal("2000"), Decimal("0.60")),
            FormationIntentRow("Edu_A", "BBB", Decimal("2000"), Decimal("0.40")),
            FormationIntentRow("Retirement", "AAA", Decimal("5000"), Decimal("1.00")),
        )
    )

    validate_purpose_target_allocation(formation)


def test_rejects_weights_that_do_not_sum_to_one():
    formation = [
        FormationIntentRow("Edu_A", "AAA", Decimal("2000"), Decimal("0.60")),
        FormationIntentRow("Edu_A", "BBB", Decimal("2000"), Decimal("0.30")),
    ]

    with pytest.raises(ValueError, match="must sum to 1"):
        validate_purpose_target_allocation(formation)


def test_rejects_inconsistent_capital_base_within_purpose():
    formation = [
        FormationIntentRow("Edu_A", "AAA", Decimal("2000"), Decimal("0.60")),
        FormationIntentRow("Edu_A", "BBB", Decimal("1800"), Decimal("0.40")),
    ]

    with pytest.raises(ValueError, match="inconsistent target capital bases"):
        validate_purpose_target_allocation(formation)


def test_rejects_duplicate_purpose_isin_allocation():
    formation = [
        FormationIntentRow("Edu_A", "AAA", Decimal("2000"), Decimal("0.60")),
        FormationIntentRow("Edu_A", "AAA", Decimal("2000"), Decimal("0.40")),
    ]

    with pytest.raises(ValueError, match="Duplicate Purpose-to-ISIN"):
        validate_purpose_target_allocation(formation)
