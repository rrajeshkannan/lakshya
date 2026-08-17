from dataclasses import dataclass

import pandas as pd

from .models import ResilienceEvidence


@dataclass(frozen=True)
class DrawdownEpisode:
    peak_date: object
    peak_value: float
    trough_date: object
    trough_value: float
    drawdown_pct: float
    decline_days: int
    recovery_date: object | None
    recovery_days: int | None
    underwater_days: int | None
    status: str
    history_before_peak_days: int


@dataclass(frozen=True)
class DrawdownEpisodeSummary:
    threshold_pct: float

    episode_count: int
    recovered_count: int
    ongoing_count: int

    median_depth_pct: float | None
    worst_depth_pct: float | None

    # Historical demonstrated behaviour
    median_decline_days_recovered: float | None
    median_recovery_days: float | None
    median_underwater_days_recovered: float | None

    # Current observed state
    median_underwater_days_ongoing: float | None


def identify_drawdown_episodes(
    nav: pd.Series,
    threshold_pct: float,
) -> list[DrawdownEpisode]:

    if nav.empty:
        return []

    nav = nav.dropna().sort_index()

    running_peak = nav.cummax()
    drawdown = nav / running_peak - 1.0

    episodes: list[DrawdownEpisode] = []

    in_episode = False
    peak_date = None
    peak_value = None
    trough_date = None
    trough_value = None

    for date, value in nav.items():

        dd = drawdown.loc[date]

        if not in_episode:

            if dd <= -threshold_pct:

                in_episode = True

                peak_idx = nav.loc[:date].idxmax()

                peak_date = peak_idx
                peak_value = float(nav.loc[peak_date])

                trough_date = date
                trough_value = float(value)

        else:

            if value < trough_value:
                trough_date = date
                trough_value = float(value)

            if value >= peak_value:

                recovery_date = date

                decline_days = (
                    trough_date - peak_date
                ).days

                recovery_days = (
                    recovery_date - trough_date
                ).days

                underwater_days = (
                    recovery_date - peak_date
                ).days

                history_before_peak_days = (
                    peak_date - nav.index[0]
                ).days

                episodes.append(
                    DrawdownEpisode(
                        peak_date=peak_date,
                        peak_value=peak_value,
                        trough_date=trough_date,
                        trough_value=trough_value,
                        drawdown_pct=float(
                            trough_value / peak_value - 1.0
                        ),
                        decline_days=decline_days,
                        recovery_date=recovery_date,
                        recovery_days=recovery_days,
                        underwater_days=underwater_days,
                        status="recovered",
                        history_before_peak_days=history_before_peak_days,
                    )
                )

                in_episode = False
                peak_date = None
                peak_value = None
                trough_date = None
                trough_value = None

    # Handle an episode that remains underwater at the end
    # of the available history.
    if in_episode:

        history_before_peak_days = (
            peak_date - nav.index[0]
        ).days

        underwater_days = (
            nav.index[-1] - peak_date
        ).days

        decline_days = (
            trough_date - peak_date
        ).days

        episodes.append(
            DrawdownEpisode(
                peak_date=peak_date,
                peak_value=peak_value,
                trough_date=trough_date,
                trough_value=trough_value,
                drawdown_pct=float(
                    trough_value / peak_value - 1.0
                ),
                decline_days=decline_days,
                recovery_date=None,
                recovery_days=None,
                underwater_days=underwater_days,
                status="ongoing",
                history_before_peak_days=history_before_peak_days,
            )
        )

    return episodes


# ---------------------------------------------------------------------------
# Historical exploratory helper
# ---------------------------------------------------------------------------
# This function supported the empirical investigation that led to the
# current Fund-stage Resilience model.
#
# It is retained temporarily as historical analytical machinery.
# The active Fund-stage path uses:
#
#     identify_drawdown_episodes()
#             ↓
#     calculate_resilience()
#
# Once the Fund-stage implementation is fully validated, this helper can
# either be moved into an experiment/archive module or removed if its
# historical outputs are no longer needed.
# ---------------------------------------------------------------------------
def summarize_drawdown_episodes(
    episodes: list[DrawdownEpisode],
    threshold_pct: float,
) -> DrawdownEpisodeSummary:

    if not episodes:
        return DrawdownEpisodeSummary(
            threshold_pct=threshold_pct,
            episode_count=0,
            recovered_count=0,
            ongoing_count=0,
            median_depth_pct=None,
            worst_depth_pct=None,
            median_decline_days_recovered=None,
            median_recovery_days=None,
            median_underwater_days_recovered=None,
            median_underwater_days_ongoing=None,
        )

    depths = [
        abs(episode.drawdown_pct) * 100
        for episode in episodes
    ]

    recovered = [
        episode
        for episode in episodes
        if episode.status == "recovered"
    ]

    ongoing = [
        episode
        for episode in episodes
        if episode.status == "ongoing"
    ]

    recovered_decline_days = [
        episode.decline_days
        for episode in recovered
    ]

    recovered_recovery_days = [
        episode.recovery_days
        for episode in recovered
        if episode.recovery_days is not None
    ]

    recovered_underwater_days = [
        episode.underwater_days
        for episode in recovered
        if episode.underwater_days is not None
    ]

    ongoing_underwater_days = [
        episode.underwater_days
        for episode in ongoing
        if episode.underwater_days is not None
    ]

    return DrawdownEpisodeSummary(
        threshold_pct=threshold_pct,

        episode_count=len(episodes),
        recovered_count=len(recovered),
        ongoing_count=len(ongoing),

        # Depth is valid for both completed and ongoing episodes.
        median_depth_pct=float(
            pd.Series(depths).median()
        ),
        worst_depth_pct=float(
            max(depths)
        ),

        # Historical demonstrated behaviour only.
        median_decline_days_recovered=(
            float(pd.Series(recovered_decline_days).median())
            if recovered_decline_days
            else None
        ),
        median_recovery_days=(
            float(pd.Series(recovered_recovery_days).median())
            if recovered_recovery_days
            else None
        ),
        median_underwater_days_recovered=(
            float(pd.Series(recovered_underwater_days).median())
            if recovered_underwater_days
            else None
        ),

        # Current observed state only.
        median_underwater_days_ongoing=(
            float(pd.Series(ongoing_underwater_days).median())
            if ongoing_underwater_days
            else None
        ),
    )


def calculate_resilience(
    episodes: list[DrawdownEpisode],
) -> ResilienceEvidence:
    """
    Compose drawdown episodes into Fund-stage Resilience evidence.

    Resilience describes what happens after adversity begins.

    The individual DrawdownEpisode objects are deliberately retained.
    Summary statistics are derived from them, but never replace them.

    Recovered and ongoing episodes are treated separately:

        recovered:
            recovery behaviour is known and may contribute to recovery
            statistics.

        ongoing:
            the recovery story is not yet known. The episode remains
            evidence, but cannot contribute to recovery-duration statistics.

    This distinction is fundamental:
        unknown recovery != zero recovery
        unknown recovery != failed recovery
    """

    recovered = [
        episode
        for episode in episodes
        if episode.status == "recovered"
    ]

    ongoing = [
        episode
        for episode in episodes
        if episode.status == "ongoing"
    ]

    return ResilienceEvidence(
        episodes=list(episodes),

        episode_count=len(episodes),
        recovered_count=len(recovered),
        ongoing_count=len(ongoing),

        median_depth_pct=(
            float(
                pd.Series(
                    abs(episode.drawdown_pct) * 100
                    for episode in episodes
                ).median()
            )
            if episodes
            else None
        ),

        worst_depth_pct=(
            float(
                pd.Series(
                    abs(episode.drawdown_pct) * 100
                    for episode in episodes
                ).max()
            )
            if episodes
            else None
        ),

        median_decline_days_recovered=(
            float(
                pd.Series(
                    episode.decline_days
                    for episode in recovered
                ).median()
            )
            if recovered
            else None
        ),

        median_recovery_days=(
            float(
                pd.Series(
                    episode.recovery_days
                    for episode in recovered
                    if episode.recovery_days is not None
                ).median()
            )
            if recovered
            else None
        ),

        median_underwater_days_recovered=(
            float(
                pd.Series(
                    episode.underwater_days
                    for episode in recovered
                ).median()
            )
            if recovered
            else None
        ),

        median_underwater_days_ongoing=(
            float(
                pd.Series(
                    episode.underwater_days
                    for episode in ongoing
                ).median()
            )
            if ongoing
            else None
        ),
    )
