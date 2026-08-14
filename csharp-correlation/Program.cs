// Step 5 (C# port): correlation and covariance matrix. Mirrors python/compute_correlation.py
// structurally (same three outputs, same "pairwise diagnostic vs common-window frontier-ready"
// distinction). See LinAlg.cs for the Ledoit-Wolf and eigenvalue implementations and their
// trust-level caveats — read that before trusting exact numbers here.
//
// Reads:  ../output/nav_panel.csv
//         ../data/funds_universe.csv
// Writes: ../output/correlation_pairwise_full_history.csv   (diagnostic only)
//         ../output/correlation_common_window.csv
//         ../output/covariance_shrunk_annualized.csv         (frontier-ready — USE THIS ONE)
//         ../output/monthly_returns_common_window.csv
//
// Usage: dotnet run  (from this directory)
//        dotnet run -- --min-pairwise-months 36

using System.Globalization;
using MfCorrelation;

const int monthsPerYear = 12;

var projectDir = FindProjectRoot(AppContext.BaseDirectory);
var repoRoot = projectDir.Parent!.FullName;
var navPanelPath = Path.Combine(repoRoot, "output", "nav_panel.csv");
var fundsUniversePath = Path.Combine(repoRoot, "data", "funds_universe.csv");
var outputDir = Path.Combine(repoRoot, "output");

int minPairwiseMonths = 36;
for (int i = 0; i < args.Length; i++)
    if (args[i] == "--min-pairwise-months") minPairwiseMonths = int.Parse(args[++i]);

if (!File.Exists(navPanelPath))
    throw new FileNotFoundException($"{navPanelPath} not found — run fetch_data.py first.");

var navPanel = LoadPanel(navPanelPath);
var universe = SimpleCsv.ReadWithHeader(fundsUniversePath);
var labels = universe.ToDictionary(r => r["isin"].Trim(), r => r["name"].Trim());

var isins = navPanel.Keys.ToList();
var monthlyReturns = isins.ToDictionary(isin => isin, isin => navPanel[isin].MonthlyLast().PctChange()
    .ToDictionary(x => x.date, x => x.ret));

Console.WriteLine($"Monthly return series: {isins.Count} funds");
foreach (var isin in isins)
    Console.WriteLine($"  {isin}  {labels.GetValueOrDefault(isin, "?"),-55} {monthlyReturns[isin].Count} months of returns");

// --- Diagnostic: pairwise-history correlation ---
Console.WriteLine($"\n--- Pairwise-history correlation (diagnostic only, min {minPairwiseMonths} months overlap) ---");
var pairwiseCorr = new Dictionary<(string, string), double?>();
int nMissing = 0;
foreach (var a in isins)
{
    foreach (var b in isins)
    {
        var commonDates = monthlyReturns[a].Keys.Intersect(monthlyReturns[b].Keys).ToList();
        if (commonDates.Count < minPairwiseMonths) { pairwiseCorr[(a, b)] = null; nMissing++; continue; }
        var xs = commonDates.Select(d => monthlyReturns[a][d]).ToArray();
        var ys = commonDates.Select(d => monthlyReturns[b][d]).ToArray();
        pairwiseCorr[(a, b)] = Pearson(xs, ys);
    }
}
if (nMissing > 0) Console.WriteLine($"  [note] {nMissing} pairs had insufficient overlap and are blank in the output");
Directory.CreateDirectory(outputDir);
WriteSquareMatrix(Path.Combine(outputDir, "correlation_pairwise_full_history.csv"), isins,
    (a, b) => pairwiseCorr[(a, b)]);

// --- Frontier-ready: common window where ALL funds have data ---
var allMonthlyDates = isins.SelectMany(i => monthlyReturns[i].Keys).Distinct().OrderBy(d => d).ToList();
var commonDatesList = allMonthlyDates.Where(d => isins.All(i => monthlyReturns[i].ContainsKey(d))).ToList();
int nCommon = commonDatesList.Count;

if (nCommon < 24)
    Console.WriteLine($"\n[warn] only {nCommon} months in the common window across all funds — "
        + "shrinkage covariance will be built on thin data.");

Console.WriteLine($"\n--- Common window across all {isins.Count} funds: {nCommon} months, "
    + $"{(nCommon > 0 ? commonDatesList.First().ToString("yyyy-MM-dd") : "-")} to "
    + $"{(nCommon > 0 ? commonDatesList.Last().ToString("yyyy-MM-dd") : "-")} ---");

// dense n x p matrix for the common window
var X = new double[nCommon, isins.Count];
for (int r = 0; r < nCommon; r++)
    for (int c = 0; c < isins.Count; c++)
        X[r, c] = monthlyReturns[isins[c]][commonDatesList[r]];

// monthly_returns_common_window.csv
{
    var headers = new List<string> { "date" }.Concat(isins).ToList();
    var rows = Enumerable.Range(0, nCommon).Select(r =>
        new List<string> { commonDatesList[r].ToString("yyyy-MM-dd") }
            .Concat(Enumerable.Range(0, isins.Count).Select(c => X[r, c].ToString("F6", CultureInfo.InvariantCulture))));
    SimpleCsv.WriteWithHeader(Path.Combine(outputDir, "monthly_returns_common_window.csv"), headers, rows);
    Console.WriteLine($"Wrote {Path.Combine(outputDir, "monthly_returns_common_window.csv")} ({nCommon} x {isins.Count})");
}

// common-window correlation
var commonCorr = new Dictionary<(string, string), double?>();
for (int i = 0; i < isins.Count; i++)
    for (int j = 0; j < isins.Count; j++)
    {
        var xs = Enumerable.Range(0, nCommon).Select(r => X[r, i]).ToArray();
        var ys = Enumerable.Range(0, nCommon).Select(r => X[r, j]).ToArray();
        commonCorr[(isins[i], isins[j])] = Pearson(xs, ys);
    }
WriteSquareMatrix(Path.Combine(outputDir, "correlation_common_window.csv"), isins, (a, b) => commonCorr[(a, b)]);

// raw sample covariance (for the PSD comparison only)
var rawCovMonthly = LinAlg.SampleCovariance(X, out _);

Console.WriteLine("\n--- Positive-definiteness check ---");
var rawEig = LinAlg.EigenvaluesSymmetric(rawCovMonthly);
Console.WriteLine($"  Raw sample covariance   : min eigenvalue = {rawEig.Min():F6} -> "
    + (rawEig.Min() >= -1e-10 ? "OK (positive semi-definite)" : "PROBLEM (has negative eigenvalues)"));

// Ledoit-Wolf shrinkage
var (shrunkCovMonthly, shrinkage) = LinAlg.LedoitWolfShrink(X);
var shrunkEig = LinAlg.EigenvaluesSymmetric(shrunkCovMonthly);
Console.WriteLine($"  Ledoit-Wolf shrunk cov  : min eigenvalue = {shrunkEig.Min():F6} -> "
    + (shrunkEig.Min() >= -1e-10 ? "OK (positive semi-definite)" : "PROBLEM (has negative eigenvalues)"));
Console.WriteLine($"  Shrinkage intensity (0=no shrinkage, 1=fully toward target): {shrinkage:F4}");

var shrunkCovAnnual = new Dictionary<(string, string), double?>();
for (int i = 0; i < isins.Count; i++)
    for (int j = 0; j < isins.Count; j++)
        shrunkCovAnnual[(isins[i], isins[j])] = shrunkCovMonthly[i, j] * monthsPerYear;
WriteSquareMatrix(Path.Combine(outputDir, "covariance_shrunk_annualized.csv"), isins, (a, b) => shrunkCovAnnual[(a, b)]);

Console.WriteLine("\nUse output/covariance_shrunk_annualized.csv as the frontier's covariance input.");

return 0;

// ---------------------------------------------------------------------------

static DirectoryInfo FindProjectRoot(string startDir)
{
    var dir = new DirectoryInfo(startDir);
    while (dir is not null && !dir.GetFiles("*.csproj").Any())
        dir = dir.Parent;
    return dir ?? new DirectoryInfo(startDir);
}

static Dictionary<string, NavSeries> LoadPanel(string path)
{
    using var reader = new StreamReader(path);
    var header = reader.ReadLine()!.Split(',');
    var isins = header.Skip(1).Select(h => h.Trim()).ToList();
    var points = isins.ToDictionary(n => n, _ => new List<(DateTime, double)>());

    string? line;
    while ((line = reader.ReadLine()) is not null)
    {
        if (line.Length == 0) continue;
        var fields = line.Split(',');
        if (!DateTime.TryParse(fields[0], CultureInfo.InvariantCulture, DateTimeStyles.None, out var date)) continue;
        for (int i = 0; i < isins.Count && i + 1 < fields.Length; i++)
            if (double.TryParse(fields[i + 1], NumberStyles.Float, CultureInfo.InvariantCulture, out var val))
                points[isins[i]].Add((date, val));
    }
    return isins.ToDictionary(n => n, n => new NavSeries(points[n]));
}

static double? Pearson(double[] xs, double[] ys)
{
    int n = xs.Length;
    if (n < 2) return null;
    double mx = xs.Average(), my = ys.Average();
    double sxy = 0, sxx = 0, syy = 0;
    for (int i = 0; i < n; i++)
    {
        double dx = xs[i] - mx, dy = ys[i] - my;
        sxy += dx * dy; sxx += dx * dx; syy += dy * dy;
    }
    if (sxx <= 0 || syy <= 0) return null;
    return sxy / Math.Sqrt(sxx * syy);
}

static void WriteSquareMatrix(string path, List<string> isins, Func<string, string, double?> getValue)
{
    var headers = new List<string> { "" }.Concat(isins).ToList();
    var rows = isins.Select(a => new List<string> { a }.Concat(
        isins.Select(b =>
        {
            var v = getValue(a, b);
            return v.HasValue ? v.Value.ToString("F6", CultureInfo.InvariantCulture) : "";
        })));
    SimpleCsv.WriteWithHeader(path, headers, rows);
    Console.WriteLine($"Wrote {path} ({isins.Count} x {isins.Count})");
}
