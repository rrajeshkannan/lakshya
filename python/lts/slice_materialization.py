"""Materialize conservation-balanced virtual slices from an LTS plan."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from .position_bridge import LtsPosition, LtsPositionId, validate_slice_percentages
from .purpose_transition import PurposeTransitionPlan, TransitionDisposition, TransitionMapping

ZERO = Decimal("0")
ONE_HUNDRED = Decimal("100")
TOLERANCE = Decimal("0.00000001")


@dataclass(frozen=True)
class MaterializedSlice:
    """One virtual slice representing one source-to-destination outcome."""

    id: LtsPositionId
    source_position_id: LtsPositionId
    source_isin: str
    destination_isin: str
    purpose: str
    disposition: TransitionDisposition
    locked: bool
    percentage: Decimal
    units: Decimal
    nav: Decimal | None
    market_value: Decimal
    source_amount: Decimal
    ownership_source: str

    @property
    def physical_key(self) -> tuple[str, str, str]:
        return self.id.investor, self.id.folio, self.id.isin


def _source_value(position: LtsPosition) -> Decimal:
    if position.market_value is None:
        raise ValueError(f"Cannot materialize an unvalued Position: {position.id}")
    if position.market_value < ZERO:
        raise ValueError(f"Position market value cannot be negative: {position.id}")
    return position.market_value * position.percentage / ONE_HUNDRED


def _mapping_disposition(mapping: TransitionMapping) -> TransitionDisposition:
    if mapping.source_kind.value == "RETAINED_POSITION":
        return TransitionDisposition.RETAIN
    if mapping.destination_isin != mapping.source_isin:
        return TransitionDisposition.INVEST
    if mapping.locked:
        return TransitionDisposition.REDEEM_LOCKED
    return TransitionDisposition.REDEEM


def materialize_transition_slices(
    positions: list[LtsPosition],
    plan: PurposeTransitionPlan,
) -> tuple[MaterializedSlice, ...]:
    """Split source positions into outcome-specific virtual slices.

    A source position can produce multiple slices when its mapped capital is
    retained, redeemed, or directed to different destination ISINs. Slice
    percentages are percentages of the source physical holding. Units and
    market value are allocated pro-rata by attributed source value.
    """
    validate_slice_percentages(positions)
    by_id = {position.id: position for position in positions}
    if len(by_id) != len(positions):
        raise ValueError("Source LTS Position identities must be unique.")

    grouped: dict[LtsPositionId, list[TransitionMapping]] = {}
    for mapping in plan.mappings:
        if mapping.source_position_id not in by_id:
            raise ValueError(
                "Transition mapping references unknown source Position: "
                f"{mapping.source_position_id}"
            )
        grouped.setdefault(mapping.source_position_id, []).append(mapping)

    output: list[MaterializedSlice] = []
    counters: dict[tuple[str, str, str], int] = {}

    for position in sorted(
        positions,
        key=lambda item: (
            item.id.investor,
            item.id.folio,
            item.id.isin,
            item.id.slice,
        ),
    ):
        source_value = _source_value(position)
        mappings = grouped.get(position.id, [])
        mapped_total = sum((mapping.amount for mapping in mappings), ZERO)
        if abs(mapped_total - source_value) > TOLERANCE:
            raise ValueError(
                "Source mapping total does not reconcile to source value: "
                f"{position.id}: mapped={mapped_total}, source={source_value}"
            )
        if source_value <= ZERO:
            if mappings:
                raise ValueError(f"Positive mapping exists for zero-value Position: {position.id}")
            continue

        physical_key = (position.id.investor, position.id.folio, position.id.isin)
        for mapping in mappings:
            if mapping.amount < ZERO:
                raise ValueError(f"Mapping amount cannot be negative: {mapping}")
            counters[physical_key] = counters.get(physical_key, 0) + 1
            ratio = mapping.amount / source_value
            output.append(
                MaterializedSlice(
                    id=LtsPositionId(
                        investor=position.id.investor,
                        folio=position.id.folio,
                        isin=position.id.isin,
                        slice=f"Slice-{counters[physical_key]}",
                    ),
                    source_position_id=position.id,
                    source_isin=mapping.source_isin,
                    destination_isin=mapping.destination_isin,
                    purpose=mapping.purpose,
                    disposition=_mapping_disposition(mapping),
                    locked=mapping.locked,
                    percentage=position.percentage * ratio,
                    units=position.units * position.percentage / ONE_HUNDRED * ratio,
                    nav=position.nav,
                    market_value=source_value * ratio,
                    source_amount=mapping.amount,
                    ownership_source=position.ownership_source,
                )
            )

    if len(output) == 0 and positions:
        raise ValueError("No materialized slices were produced for non-empty positions.")

    source_by_physical: dict[tuple[str, str, str], tuple[Decimal, Decimal, Decimal]] = {}
    for position in positions:
        key = (position.id.investor, position.id.folio, position.id.isin)
        units, value, percentage = source_by_physical.get(key, (ZERO, ZERO, ZERO))
        source_by_physical[key] = (
            units + position.units * position.percentage / ONE_HUNDRED,
            value + _source_value(position),
            percentage + position.percentage,
        )

    output_by_physical: dict[tuple[str, str, str], tuple[Decimal, Decimal, Decimal]] = {}
    for item in output:
        key = item.physical_key
        units, value, percentage = output_by_physical.get(key, (ZERO, ZERO, ZERO))
        output_by_physical[key] = (
            units + item.units,
            value + item.market_value,
            percentage + item.percentage,
        )

    if set(source_by_physical) != set(output_by_physical):
        raise ValueError("Materialized slices changed the set of physical holdings.")

    for key, (source_units, source_value, source_percentage) in source_by_physical.items():
        output_units, output_value, output_percentage = output_by_physical[key]
        if abs(source_units - output_units) > TOLERANCE:
            raise ValueError(f"Slice units do not reconcile for {key}: {source_units} != {output_units}")
        if abs(source_value - output_value) > TOLERANCE:
            raise ValueError(f"Slice value does not reconcile for {key}: {source_value} != {output_value}")
        if abs(source_percentage - output_percentage) > TOLERANCE:
            raise ValueError(
                f"Slice percentage does not reconcile for {key}: {source_percentage} != {output_percentage}"
            )

    return tuple(output)


__all__ = ["MaterializedSlice", "materialize_transition_slices"]
