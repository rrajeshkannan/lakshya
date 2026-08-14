namespace MfMetrics;

public record RollingSummary(double? Mean, double? Median, double? Std, double? Min, double? Max,
    double? PctPositive, double? Latest);

public record DrawdownResult(double? Pct, DateTime? PeakDate, DateTime? TroughDate, DateTime? RecoveryDate,
    int? DeclineDays, int? RecoveryDays, bool? Recovered,
    double? BenchDeclinePctSameWindow, bool? BenchRecoveredByFundRecoveryDate);

public record CaptureResult(double? UpsideCapturePct, double? DownsideCapturePct, int CaptureMonthsUsed);

public static class Metrics
{
    public const int TradingDaysPerYear = 252;
    public const int MinCaptureMonths = 12;

    /// <summary>CAGR ending at each date, looking back `years`, wherever that lookback exists in the data.</summary>
    public static NavSeries RollingCagr(NavSeries nav, int years)
    {
        if (nav.Dates.Count == 0) return new NavSeries(Enumerable.Empty<(DateTime, double)>());
        var earliest = nav.Dates[0];
        var points = new List<(DateTime, double)>();

        foreach (var date in nav.Dates)
        {
            var value = nav[date];
            if (value <= 0) continue;
            var startDate = date.AddYears(-years);
            if (startDate < earliest) continue;
            var startValue = nav.AsOf(startDate);
            if (startValue is null || startValue <= 0) continue;
            var cagr = Math.Pow(value / startValue.Value, 1.0 / years) - 1.0;
            points.Add((date, cagr));
        }
        return new NavSeries(points);
    }

    public static RollingSummary Summarize(NavSeries series)
    {
        if (series.Dates.Count == 0)
            return new RollingSummary(null, null, null, null, null, null, null);

        var values = series.Dates.Select(d => series[d]).ToList();
        var sorted = values.OrderBy(v => v).ToList();
        double mean = values.Average();
        double median = sorted.Count % 2 == 1
            ? sorted[sorted.Count / 2]
            : (sorted[sorted.Count / 2 - 1] + sorted[sorted.Count / 2]) / 2.0;
        double std = values.Count > 1
            ? Math.Sqrt(values.Sum(v => Math.Pow(v - mean, 2)) / (values.Count - 1))
            : 0.0;
        double pctPositive = (double)values.Count(v => v > 0) / values.Count;

        return new RollingSummary(mean, median, std, sorted.First(), sorted.Last(), pctPositive, values.Last());
    }

    public static DrawdownResult MaxDrawdownAndRecovery(NavSeries nav, NavSeries? benchNav)
    {
        if (nav.Dates.Count < 2)
            return new DrawdownResult(null, null, null, null, null, null, null, null, null);

        double runningMax = double.MinValue;
        var drawdown = new Dictionary<DateTime, double>();
        foreach (var date in nav.Dates)
        {
            runningMax = Math.Max(runningMax, nav[date]);
            drawdown[date] = nav[date] / runningMax - 1.0;
        }

        var troughDate = drawdown.OrderBy(kv => kv.Value).First().Key;
        var mdd = drawdown[troughDate];

        // peak = the date of the max NAV value at-or-before the trough
        var peakDate = nav.Dates.TakeWhile(d => d <= troughDate).OrderByDescending(d => nav[d]).First();
        var peakValue = nav[peakDate];

        DateTime? recoveryDate = nav.Dates.Where(d => d >= troughDate && nav[d] >= peakValue)
            .Cast<DateTime?>().FirstOrDefault();

        double? benchDeclineSameWindow = null;
        bool? benchRecoveredByFundRecovery = null;

        if (benchNav is not null && benchNav.Dates.Count > 0
            && peakDate >= benchNav.Dates.First() && peakDate <= benchNav.Dates.Last())
        {
            var benchAtPeak = benchNav.AsOf(peakDate);
            var benchAtTrough = benchNav.AsOf(troughDate);
            if (benchAtPeak is > 0 && benchAtTrough is not null)
                benchDeclineSameWindow = (benchAtTrough.Value / benchAtPeak.Value - 1.0) * 100.0;

            if (recoveryDate is not null && recoveryDate <= benchNav.Dates.Last())
            {
                var benchAtFundRecovery = benchNav.AsOf(recoveryDate.Value);
                if (benchAtFundRecovery is not null && benchAtPeak is not null)
                    benchRecoveredByFundRecovery = benchAtFundRecovery.Value >= benchAtPeak.Value;
            }
        }

        return new DrawdownResult(
            Pct: mdd * 100.0,
            PeakDate: peakDate,
            TroughDate: troughDate,
            RecoveryDate: recoveryDate,
            DeclineDays: (troughDate - peakDate).Days,
            RecoveryDays: recoveryDate is not null ? (recoveryDate.Value - troughDate).Days : null,
            Recovered: recoveryDate is not null,
            BenchDeclinePctSameWindow: benchDeclineSameWindow,
            BenchRecoveredByFundRecoveryDate: benchRecoveredByFundRecovery
        );
    }

    public static double? DownsideDeviationAnnual(List<(DateTime date, double ret)> dailyReturns)
    {
        var downside = dailyReturns.Where(r => r.ret < 0).Select(r => r.ret).ToList();
        if (downside.Count == 0) return 0.0;
        double meanSquare = downside.Sum(r => r * r) / downside.Count;
        return Math.Sqrt(meanSquare) * Math.Sqrt(TradingDaysPerYear);
    }

    public static double? FullPeriodCagr(NavSeries nav)
    {
        if (nav.Dates.Count < 2) return null;
        var years = (nav.Dates.Last() - nav.Dates.First()).Days / 365.25;
        if (years <= 0 || nav[nav.Dates.First()] <= 0) return null;
        return Math.Pow(nav[nav.Dates.Last()] / nav[nav.Dates.First()], 1.0 / years) - 1.0;
    }

    public static CaptureResult CaptureRatios(NavSeries fundNav, NavSeries benchNav)
    {
        var fundMonthly = fundNav.MonthlyLast();
        var benchMonthly = benchNav.MonthlyLast();
        var fundRet = fundMonthly.PctChange().ToDictionary(x => x.date, x => x.ret);
        var benchRet = benchMonthly.PctChange().ToDictionary(x => x.date, x => x.ret);

        var common = fundRet.Keys.Intersect(benchRet.Keys).OrderBy(d => d).ToList();
        if (common.Count < MinCaptureMonths)
            return new CaptureResult(null, null, common.Count);

        var upMonths = common.Where(d => benchRet[d] > 0).ToList();
        var downMonths = common.Where(d => benchRet[d] < 0).ToList();

        double? upside = null;
        if (upMonths.Count > 0)
        {
            double fUp = upMonths.Aggregate(1.0, (acc, d) => acc * (1 + fundRet[d])) - 1.0;
            double bUp = upMonths.Aggregate(1.0, (acc, d) => acc * (1 + benchRet[d])) - 1.0;
            if (bUp != 0) upside = fUp / bUp * 100.0;
        }

        double? downside = null;
        if (downMonths.Count > 0)
        {
            double fDown = downMonths.Aggregate(1.0, (acc, d) => acc * (1 + fundRet[d])) - 1.0;
            double bDown = downMonths.Aggregate(1.0, (acc, d) => acc * (1 + benchRet[d])) - 1.0;
            if (bDown != 0) downside = fDown / bDown * 100.0;
        }

        return new CaptureResult(upside, downside, common.Count);
    }
}
