from __future__ import annotations

from pathlib import Path

from family.staging import initialize_staging, run_turn


def test_staging_log_captures_turn_and_pool_events(tmp_path: Path):
    data = tmp_path / "data"
    purpose = data / "purpose" / "purposes.csv"
    purpose.parent.mkdir(parents=True)
    purpose.write_text(
        "name,due,desired,monthly_plan\n"
        "A,2036-01-01,300,10\n"
        "B,2036-01-01,300,10\n",
        encoding="utf-8",
    )
    positions = data / "lps" / "positions.csv"
    positions.parent.mkdir(parents=True)
    positions.write_text(
        "investor,folio,isin,units,nav,market_value,purpose\n"
        "Amma,F1,PA,1,100,100,A\n"
        "Amma,F2,PB,1,200,200,B\n",
        encoding="utf-8",
    )
    review = data / "reviews" / "2026-09-06"
    review.mkdir(parents=True)
    for name in ("A", "B"):
        (review / f"{name}_summary.csv").write_text(
            "purpose,purpose_horizon_years,primary_winner,contract_version\n"
            f'{name},10,"X|X=1.0000",1\n',
            encoding="utf-8",
        )
    output = tmp_path / "output"
    output.mkdir()
    for name in ("A", "B"):
        (output / f"achievability_{name}.csv").write_text(
            "composition,status,required_annual_return,comparison_horizon_years,observed_upper_return\n"
            "X|X=1.0000,within_observed_terrain,0.05,10,0.10\n",
            encoding="utf-8",
        )

    initialize_staging("2026-09-06", data_dir=data)
    turn = tmp_path / "turn.csv"
    turn.write_text(
        "purpose,value,monthly_plan,desired,due,capital_acquire_pct,sip_acquire_pct\n"
        "A,50,5,,,,\n",
        encoding="utf-8",
    )
    run_turn("2026-09-06", turn, data_dir=data)

    log = (data / "reviews" / "2026-09-06" / "purpose_staging" / "staging.log").read_text(encoding="utf-8")
    assert "TURN_START" in log
    assert "RELEASE_CAPITAL" in log
    assert "RELEASE_SIP" in log
    assert "TURN_COMPLETE" in log
