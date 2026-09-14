"""Global Composition frontier stage extracted from the resilient runner."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Iterable


@dataclass(frozen=True)
class GlobalCompositionDeps:
    output_dir: Path
    project_root: Path
    fingerprint_dir: Path
    candidates_path: Path
    global_survivors_path: Path
    fingerprint_schema_version: object
    input_hash: Callable[[Path], str]
    candidate_compositions: Callable[[object], Iterable[object]]
    fingerprint_path: Callable[[Path, object], Path]
    composition_identity: Callable[[object], str]
    load_fingerprint: Callable[[Path, object], object]
    global_composition_frontier: Callable[[Iterable[tuple[object, object]]], list[object]]
    load_csv_checkpoint: Callable[..., object]
    detail: Callable[[str], None]
    as_of_string: Callable[[], str]


class GlobalCompositionStage:
    def __init__(self, deps: GlobalCompositionDeps) -> None:
        self.deps = deps

    def load_pairs_for_frontier(self, teams):
        for composition in self.deps.candidate_compositions(teams):
            path = self.deps.fingerprint_path(self.deps.fingerprint_dir, composition)
            if not path.is_file():
                identity = self.deps.composition_identity(composition)
                self.deps.detail(f"GLOBAL_FINGERPRINT_MISSING composition={identity} path={path}")
                raise FileNotFoundError(f"Missing Composition fingerprint checkpoint: {path}")
            identity = self.deps.composition_identity(composition)
            self.deps.detail(f"GLOBAL_FINGERPRINT_LOADED composition={identity} path={path}")
            yield composition, self.deps.load_fingerprint(path, composition)

    def inputs(self) -> dict[str, str]:
        return {
            "composition_candidates_sha256": self.deps.input_hash(self.deps.candidates_path),
            "fingerprint_schema_version": str(self.deps.fingerprint_schema_version),
        }

    def load_identities(self) -> list[str]:
        path = self.deps.global_survivors_path
        df = self.deps.load_csv_checkpoint(
            path,
            stage="global_frontier",
            as_of=self.deps.as_of_string(),
            inputs=self.inputs(),
        )
        if "composition" not in df.columns:
            raise ValueError(f"Invalid global frontier checkpoint: {path}")
        identities = df["composition"].tolist()
        self.deps.detail(f"GLOBAL_CHECKPOINT_READY path={path} survivors={len(identities)}")
        return identities
