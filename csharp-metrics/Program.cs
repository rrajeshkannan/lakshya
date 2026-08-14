// Step 4 (C# port): the metrics engine. Mirrors python/compute_metrics.py function-by-
// function (see Metrics.cs) so the two can be diffed directly. Column order and the
// *100 percentage convention (including pct_positive, which Python also multiplies by
// 100 despite the name) are matched deliberately for cross-validation.
//
// Reads:  ../output/nav_panel.csv
//         ../data/benchmarks_consolidated.csv
//         ../data/funds_universe.csv
//         ../data/benchmark_universe.csv
// Writes: ../output/fund_metrics.csv
//
// Usage: dotnet run  (from this directory)
//        dotnet run -- --risk-free-rate 0.065

using System.Globalization;
using MfMetrics;

var projectDir = FindProjectRoot(AppContext.BaseDirectory);
var repoRoot = projectDir.Parent!.FullName;
var navPanelPath = Path.Combine(repoRoot, "output", "nav_panel.csv");
var benchmarksPath = Path.Combine(repoRoot, "data", "benchmarks_consolidated.csv");
var fundsUniversePath = Path.Combine(repoRoot, "data", "funds_universe.csv");
var benchmarkUniversePath = Path.Combine(repoRoot, "data", "benchmark_universe.csv");
var outputPath = Path.Combine(repoRoot, "output", "fund_metrics.csv");

double riskFreeRate = 0.065;
for (int i = 0; i < args.Length; i++)
{
    if (args[i] == "--risk-free-rate") riskFreeRate = double.Parse(args[++i], CultureInfo.InvariantCulture);
}

int[] rollingWindowsYears = { 3, 5, 7, 10 };

if (!File.Exists(navPanelPath))
    throw new FileNotFoundException($"{navPanelPath} not found — run fetch_data.py/dotnet run in csharp/ first.");
if (!File.Exists(benchmarksPath))
    throw new FileNotFoundException($"{benchmarksPath} not found.");

var navPanel = LoadPanel(navPanelPath);
var benchmarks = LoadPanel(benchmarksPath, normalizeColumnNames: true);
var universe = SimpleCsv.ReadWithHeader(fundsUniversePath);
var benchmarkMap = SimpleCsv.ReadWithHeader(benchmarkUniversePath)
    .ToDictionary(r => r["category"].Trim(), r => r["benchmark_index_name"].Trim());

var rows = new List<Dictionary<string, string>>();
var fieldOrder = new List<string>();

foreach (var fund in universe)
{
    var isin = fund["isin"].Trim();
    var name = fund["name"].Trim();
    var category = fund["category"].Trim();

    if (!navPanel.ContainsKey(isin))
    {
        Console.WriteLine($"  [warn] {isin} ({name}): not present in nav_panel.csv, skipping");
        continue;
    }

    var navSeries = navPanel[isin];
    string? benchIndexName = benchmarkMap.GetValueOrDefault(category);
    NavSeries? benchSeries = null;
    if (benchIndexName is not null)
    {
        var key = NormalizeIndexName(benchIndexName);
        if (benchmarks.TryGetValue(key, out var bs)) benchSeries = bs;
        else Console.WriteLine($"  [warn] {isin} ({name}): benchmark '{benchIndexName}' not found in "
            + $"{Path.GetFileName(benchmarksPath)}, capture ratios will be blank");
    }

    var row = ComputeFundMetrics(isin, name, category, navSeries, benchSeries, benchIndexName, riskFreeRate,
        rollingWindowsYears, fieldOrder);
    rows.Add(row);
    Console.WriteLine($"[done] {isin} ({name}): {row.GetValueOrDefault("track_record_years")}y track record, "
        + $"MDD {row.GetValueOrDefault("mdd_pct")}");
}

if (rows.Count == 0)
{
    Console.WriteLine("No funds processed — nothing to write.");
    return 0;
}

var headers = fieldOrder; // insertion order, matches Python's dict-order-derived fieldnames
var csvRows = rows.Select(r => headers.Select(h => r.GetValueOrDefault(h, "")));
SimpleCsv.WriteWithHeader(outputPath, headers, csvRows);
Console.WriteLine($"\nWrote {outputPath} ({rows.Count} funds)");

return 0;

// ---------------------------------------------------------------------------

static DirectoryInfo FindProjectRoot(string startDir)
{
    var dir = new DirectoryInfo(startDir);
    while (dir is not null && !dir.GetFiles("*.csproj").Any())
        dir = dir.Parent;
    return dir ?? new DirectoryInfo(startDir);
}

static string NormalizeIndexName(string name) =>
    System.Text.RegularExpressions.Regex.Replace(name.Trim().ToUpperInvariant(), @"\s+", " ");

static Dictionary<string, NavSeries> LoadPanel(string path, bool normalizeColumnNames = false)
{
    using var reader = new StreamReader(path);
    var header = reader.ReadLine()!.Split(',');
    var seriesNames = header.Skip(1).Select(h => normalizeColumnNames ? NormalizeIndexName(h) : h.Trim()).ToList();
    var points = seriesNames.ToDictionary(n => n, _ => new List<(DateTime, double)>());

    string? line;
    while ((line = reader.ReadLine()) is not null)
    {
        if (line.Length == 0) continue;
        var fields = line.Split(',');
        if (!DateTime.TryParse(fields[0], CultureInfo.InvariantCulture, DateTimeStyles.None, out var date))
            continue;
        for (int i = 0; i < seriesNames.Count && i + 1 < fields.Length; i++)
        {
            if (double.TryParse(fields[i + 1], NumberStyles.Float, CultureInfo.InvariantCulture, out var val))
                points[seriesNames[i]].Add((date, val));
        }
    }
    return seriesNames.ToDictionary(n => n, n => new NavSeries(points[n]));
}

static string FormatDouble(double? v) => v.HasValue ? v.Value.ToString("G6", CultureInfo.InvariantCulture) : "";
static string FormatDate(DateTime? d) => d.HasValue ? d.Value.ToString("yyyy-MM-dd") : "";
static string FormatBool(bool? b) => b.HasValue ? (b.Value ? "true" : "false") : "";
static string FormatInt(int? i) => i.HasValue ? i.Value.ToString() : "";

static Dictionary<string, string> ComputeFundMetrics(
    string isin, string name, string category, NavSeries nav, NavSeries? benchNav, string? benchName,
    double riskFreeRate, int[] rollingWindowsYears, List<string> fieldOrder)
{
    var row = new Dictionary<string, string>();
    void Set(string key, string value)
    {
        if (!fieldOrder.Contains(key)) fieldOrder.Add(key);
        row[key] = value;
    }

    Set("isin", isin);
    Set("name", name);
    Set("category", category);
    Set("benchmark_index", benchName ?? "");

    if (nav.Dates.Count == 0)
    {
        Set("track_record_years", "0");
        return row;
    }

    double trackYears = (nav.Dates.Last() - nav.Dates.First()).Days / 365.25;
    Set("track_record_years", Math.Round(trackYears, 2).ToString(CultureInfo.InvariantCulture));

    foreach (var years in rollingWindowsYears)
    {
        var prefix = $"roll_{years}y_";
        if (trackYears < years)
        {
            foreach (var stat in new[] { "mean", "median", "std", "min", "max", "pct_positive", "latest" })
                Set(prefix + stat, "");
            continue;
        }
        var series = Metrics.RollingCagr(nav, years);
        var summary = Metrics.Summarize(series);
        // NOTE: Python multiplies ALL stats by 100, including pct_positive (a quirk
        // preserved here deliberately for exact cross-validation — see module comment).
        Set(prefix + "mean", FormatDouble(summary.Mean * 100));
        Set(prefix + "median", FormatDouble(summary.Median * 100));
        Set(prefix + "std", FormatDouble(summary.Std * 100));
        Set(prefix + "min", FormatDouble(summary.Min * 100));
        Set(prefix + "max", FormatDouble(summary.Max * 100));
        Set(prefix + "pct_positive", FormatDouble(summary.PctPositive * 100));
        Set(prefix + "latest", FormatDouble(summary.Latest * 100));
    }

    var dd = Metrics.MaxDrawdownAndRecovery(nav, benchNav);
    Set("mdd_pct", FormatDouble(dd.Pct));
    Set("mdd_peak_date", FormatDate(dd.PeakDate));
    Set("mdd_trough_date", FormatDate(dd.TroughDate));
    Set("mdd_recovery_date", FormatDate(dd.RecoveryDate));
    Set("mdd_decline_days", FormatInt(dd.DeclineDays));
    Set("mdd_recovery_days", FormatInt(dd.RecoveryDays));
    Set("mdd_recovered", FormatBool(dd.Recovered));
    Set("mdd_bench_decline_pct_same_window", FormatDouble(dd.BenchDeclinePctSameWindow));
    Set("mdd_bench_recovered_by_fund_recovery_date", FormatBool(dd.BenchRecoveredByFundRecoveryDate));

    var dailyReturns = nav.PctChange();
    var ddev = Metrics.DownsideDeviationAnnual(dailyReturns);
    Set("downside_deviation_annual_pct", FormatDouble(ddev * 100));

    var cagrFull = Metrics.FullPeriodCagr(nav);
    Set("full_period_cagr_pct", FormatDouble(cagrFull * 100));

    if (cagrFull is not null && ddev is > 0)
        Set("sortino_ratio", FormatDouble((cagrFull.Value - riskFreeRate) / ddev.Value));
    else
        Set("sortino_ratio", "");

    if (cagrFull is not null && dd.Pct is not null && dd.Pct != 0)
        Set("calmar_ratio", FormatDouble(cagrFull.Value / (Math.Abs(dd.Pct.Value) / 100.0)));
    else
        Set("calmar_ratio", "");

    if (benchNav is not null)
    {
        var cap = Metrics.CaptureRatios(nav, benchNav);
        Set("upside_capture_pct", FormatDouble(cap.UpsideCapturePct));
        Set("downside_capture_pct", FormatDouble(cap.DownsideCapturePct));
        Set("capture_months_used", FormatInt(cap.CaptureMonthsUsed));
    }
    else
    {
        Set("upside_capture_pct", "");
        Set("downside_capture_pct", "");
        Set("capture_months_used", "");
    }

    return row;
}
