from dataclasses import dataclass
from typing import Any, Callable

@dataclass(frozen=True)
class FullRunStageDeps:
    log: Callable[[str], None]
    detail: Callable[[str], None]
    manifest_update: Callable[..., None]
    write_rows: Callable[..., None]
    write_manifest: Callable[[], None]
    as_of_string: Callable[[], str]
    global_inputs: Callable[[], Any]
    load_global_pairs_for_frontier: Callable[[Any], Any]
    persist_composition_evidence: Callable[..., None]
    write_composition_candidates: Callable[[Any], int]
    load_admissible_funds: Callable[[], Any]
    run_team_pipeline: Callable[..., Any]
    global_composition_frontier: Callable[[Any], Any]
    load_csv_checkpoint: Callable[..., Any]
    is_valid_csv_checkpoint: Callable[..., bool]
    composition_from_identity: Callable[..., Any]
    composition_identity: Callable[[Any], str]

class FullRunStage:
    def __init__(self, deps: FullRunStageDeps):
        self._deps = deps

    def run(self, *, funds, histories, purposes, funds_by_isin, workers) -> None:
        deps = self._deps
        deps.log("[1/7] Loading admitted funds")
        deps.log(f"  admitted funds: {len(funds)}")
        deps.detail(f"STAGE_1_COMPLETE admitted_funds={len(funds)}")
        deps.manifest_update("admitted_funds", "complete", count=len(funds))
        deps.log("[2/7] Loading persisted NAV evidence")
        deps.log("[3/7] Loading Purpose inputs")
        deps.detail(f"STAGE_2_3_COMPLETE nav_funds={len(histories)} purposes={len(purposes)}")
        deps.manifest_update("inputs", "complete", nav_funds=len(histories), purposes=len(purposes))
        deps.log("[4/7] Running TEAM pipeline")
        stage_started = time.perf_counter()
        deps.detail("TEAM_STAGE_START")
        deps.manifest_update("team", "running")
        teams = deps.run_team_pipeline(funds=funds, fund_histories=histories)
        team_elapsed = time.perf_counter() - stage_started
        deps.log(f"  TEAM survivors: {len(teams)} | elapsed={team_elapsed:.1f}s")
        deps.detail(f"TEAM_STAGE_COMPLETE survivors={len(teams)} elapsed_seconds={team_elapsed:.3f}")
        deps.manifest_update("team", "complete", survivors=len(teams), elapsed_seconds=round(team_elapsed, 3))
        deps.write_rows(OUTPUT_DIR / "team_survivors.csv", [{"team": "|".join(member.isin for member in team.members), "members": len(team.members)} for team in teams])
        
        deps.log("[5/7] Generating and persisting Composition fingerprints")
        expected_total = deps.write_composition_candidates(teams)
        deps.persist_composition_evidence(teams, histories, max_workers=workers)
        
        deps.log("[6/7] Applying existing MISSION gates")
        stage_started = time.perf_counter()
        global_inputs = deps.global_inputs()
        global_path = OUTPUT_DIR / "global_survivors.csv"
        if deps.is_valid_csv_checkpoint(global_path, stage="global_frontier", as_of=deps.as_of_string(), inputs=global_inputs):
            global_df = deps.load_csv_checkpoint(global_path, stage="global_frontier", as_of=deps.as_of_string(), inputs=global_inputs)
            global_survivors = [deps.composition_from_identity(identity, funds_by_isin) for identity in global_df["composition"].tolist()]
            deps.log(f"  global Composition frontier: {len(global_survivors)} | valid checkpoint reused")
            deps.detail(f"GLOBAL_FRONTIER_REUSED survivors={len(global_survivors)}")
            deps.manifest_update("global_frontier", "complete", candidates=expected_total, survivors=len(global_survivors), reused=True)
        else:
            deps.detail("GLOBAL_FRONTIER_STAGE_START")
            deps.manifest_update("global_frontier", "running", candidates=expected_total)
            global_survivors = deps.global_composition_frontier(deps.load_global_pairs_for_frontier(teams))
            global_elapsed = time.perf_counter() - stage_started
            deps.write_rows(
                global_path,
                [{"composition": deps.composition_identity(composition)} for composition in global_survivors],
                stage="global_frontier",
                inputs=global_inputs,
            )
            deps.log(f"  global Composition frontier: {len(global_survivors)} | elapsed={global_elapsed:.1f}s")
            deps.detail(f"GLOBAL_FRONTIER_STAGE_COMPLETE survivors={len(global_survivors)} elapsed_seconds={global_elapsed:.3f}")
            deps.manifest_update("global_frontier", "complete", candidates=expected_total, survivors=len(global_survivors), elapsed_seconds=round(global_elapsed, 3), reused=False)
        
        _run_mission_from_global(purposes, funds_by_isin, max_workers=workers, skip_existing=False)
        deps.log("[7/7] Observing Purpose trajectories")
        _observe_persisted_mission_outputs(purposes, funds_by_isin, max_workers=workers)
        deps.write_rows(
            OUTPUT_DIR / "pipeline_summary.csv",
            [
                {"stage": "admissible_funds", "count": len(funds)},
                {"stage": "team_frontier", "count": len(teams)},
                {"stage": "composition_candidates", "count": expected_total},
                {"stage": "deps.global_composition_frontier", "count": len(global_survivors)},
            ],
        )
        deps.log("DONE")
        deps.detail("RUN_COMPLETE")
        _RUN_MANIFEST["completed_at"] = _wall_timestamp()
        _RUN_MANIFEST["status"] = "complete"
        deps.write_manifest()
        
        
