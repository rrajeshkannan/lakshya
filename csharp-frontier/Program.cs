// Step 6 (C# port): the efficient frontier.
//
// KEY DESIGN DIFFERENCE FROM PYTHON, read before comparing outputs: Python's
// scipy.optimize.minimize (SLSQP) can directly minimize a nonlinear objective like
// "negative Sharpe ratio". Accord's GoldfarbIdnani can only solve quadratic objectives
// (variance) — it cannot directly maximize a ratio. Rather than hand-roll a general
// nonlinear solver (a much higher-risk piece of untested numerical code), Max Sharpe is
// found here via golden-section search over the ONE free parameter (target return),
// repeatedly calling the same QP solver used for the rest of the frontier. This relies
// on Sharpe-vs-return being unimodal along the efficient frontier, which holds for the
// unconstrained classical frontier and should hold here too, but isn't mathematically
// guaranteed once category/weight caps are added — if the reported Max Sharpe ever looks
// suspicious, cross-check against a few frontier_points.csv rows near it by eye.
//
// Reads:  ../output/covariance_shrunk_annualized.csv
//         ../output/monthly_returns_common_window.csv
//         ../data/funds_universe.csv
// Writes: ../output/frontier_points.csv
//         ../output/frontier_key_portfolios.csv
//         ../output/frontier_bootstrap_stability.csv
//
// Usage: dotnet run
//        dotnet run -- --max-weight 0.25 --max-category-weight 0.40
//        dotnet run -- --n-bootstrap 200 --no-bootstrap

using System.Globalization;
using MfCorrelation; // LinAlg (Ledoit-Wolf), reused from Step 5 for the bootstrap
using MfFrontier;

var projectDir = FindProjectRoot(AppContext.BaseDirectory);
var repoRoot = projectDir.Parent!.FullName;
var covPath = Path.Combine(repoRoot, "output", "covariance_shrunk_annualized.csv");
var returnsPath = Path.Combine(repoRoot, "output", "monthly_returns_common_window.csv");
var universePath = Path.Combine(repoRoot, "data", "funds_universe.csv");
var outputDir = Path.Combine(repoRoot, "output");

double maxWeight = 0.30, maxCategoryWeight = 0.45, riskFreeRate = 0.065;
int nFrontierPoints = 25, nBootstrap = 200;
bool noBootstrap = false;

for (int i = 0; i < args.Length; i++)
{
    switch (args[i])
    {
        case "--max-weight": maxWeight = double.Parse(args[++i], CultureInfo.InvariantCulture); break;
        case "--max-category-weight": maxCategoryWeight = double.Parse(args[++i], CultureInfo.InvariantCulture); break;
        case "--risk-free-rate": riskFreeRate = double.Parse(args[++i], CultureInfo.InvariantCulture); break;
        case "--n-frontier-points": nFrontierPoints = int.Parse(args[++i]); break;
        case "--n-bootstrap": nBootstrap = int.Parse(args[++i]); break;
        case "--no-bootstrap": noBootstrap = true; break;
    }
}

if (!File.Exists(covPath) || !File.Exists(returnsPath))
    throw new FileNotFoundException("Missing covariance_shrunk_annualized.csv or monthly_returns_common_window.csv — run csharp-correlation first.");

var (isins, cov) = LoadCovariance(covPath);
var (returnDates, returnIsins, monthlyReturns) = LoadMonthlyReturns(returnsPath);

// Align monthly_returns_common_window.csv's column order to covariance's — don't assume
// the two files agree on ordering, even though in practice they come from the same run.
var colIndex = returnIsins.Select((isin, idx) => (isin, idx)).ToDictionary(x => x.isin, x => x.idx);
if (!isins.All(colIndex.ContainsKey))
    throw new InvalidOperationException("ISIN mismatch between covariance and returns files — rerun csharp-correlation.");
var reorderedReturns = new double[monthlyReturns.GetLength(0), isins.Count];
for (int i = 0; i < monthlyReturns.GetLength(0); i++)
    for (int j = 0; j < isins.Count; j++)
        reorderedReturns[i, j] = monthlyReturns[i, colIndex[isins[j]]];

var mu = AnnualizedGeometricReturn(reorderedReturns);

var universe = SimpleCsv.ReadWithHeader(universePath).ToDictionary(r => r["isin"].Trim(), r => r);
var categoryGroups = new Dictionary<string, List<int>>();
for (int i = 0; i < isins.Count; i++)
{
    var cat = universe.TryGetValue(isins[i], out var row) ? row["category"].Trim() : "Unknown";
    if (!categoryGroups.ContainsKey(cat)) categoryGroups[cat] = new List<int>();
    categoryGroups[cat].Add(i);
}

Console.WriteLine($"{isins.Count} funds, {categoryGroups.Count} categories, max_weight={maxWeight}, max_category_weight={maxCategoryWeight}\n");
Console.WriteLine("Annualized expected return per fund (common-window, geometric):");
for (int i = 0; i < isins.Count; i++)
{
    var name = universe.TryGetValue(isins[i], out var row) ? row["name"] : "?";
    Console.WriteLine($"  {isins[i]}  {name,-55} {mu[i] * 100,6:F2}%");
}

// --- GMV ---
var gmv = QpSolver.SolveMinVariance(cov, mu, categoryGroups, maxWeight, maxCategoryWeight, targetReturn: null);
if (gmv is null)
    throw new InvalidOperationException("GMV optimization failed to converge — try relaxing --max-weight/--max-category-weight");
Console.WriteLine($"\nGlobal Minimum Variance: return={gmv.Return * 100:F2}%  vol={gmv.Volatility * 100:F2}%");

// --- Max Sharpe via golden-section search over target return ---
double maxSingleReturn = mu.Max();
var (maxSharpeTarget, maxSharpe) = GoldenSectionMaxSharpe(
    cov, mu, categoryGroups, maxWeight, maxCategoryWeight, gmv.Return, maxSingleReturn, riskFreeRate, iterations: 60);
double maxSharpeRatio = (maxSharpe.Return - riskFreeRate) / maxSharpe.Volatility;
Console.WriteLine($"Max Sharpe:              return={maxSharpe.Return * 100:F2}%  vol={maxSharpe.Volatility * 100:F2}%  sharpe={maxSharpeRatio:F3}");

// --- frontier curve ---
var frontier = new List<QpResult>();
for (int i = 0; i < nFrontierPoints; i++)
{
    double target = gmv.Return + (maxSingleReturn - gmv.Return) * i / (nFrontierPoints - 1);
    var res = QpSolver.SolveMinVariance(cov, mu, categoryGroups, maxWeight, maxCategoryWeight, target);
    if (res is not null) frontier.Add(res);
}
Console.WriteLine($"\nFrontier: {frontier.Count}/{nFrontierPoints} target points converged");

Directory.CreateDirectory(outputDir);

var frontierHeaders = new List<string> { "target_return_pct", "volatility_pct", "sharpe" }.Concat(isins).ToList();
var frontierRows = frontier.Select(pt =>
{
    double sharpe = pt.Volatility > 0 ? (pt.Return - riskFreeRate) / pt.Volatility : 0;
    var vals = new List<string> {
        (pt.Return * 100).ToString("F6", CultureInfo.InvariantCulture),
        (pt.Volatility * 100).ToString("F6", CultureInfo.InvariantCulture),
        sharpe.ToString("F6", CultureInfo.InvariantCulture)
    };
    vals.AddRange(pt.Weights.Select(w => w.ToString("F6", CultureInfo.InvariantCulture)));
    return vals;
});
SimpleCsv.WriteWithHeader(Path.Combine(outputDir, "frontier_points.csv"), frontierHeaders, frontierRows);
Console.WriteLine($"Wrote {Path.Combine(outputDir, "frontier_points.csv")}");

var keyHeaders = new List<string> { "portfolio", "return_pct", "volatility_pct", "sharpe" }.Concat(isins).ToList();
var keyRows = new List<(string label, QpResult pt, double sharpe)>
{
    ("Global Minimum Variance", gmv, gmv.Volatility > 0 ? (gmv.Return - riskFreeRate) / gmv.Volatility : 0),
    ("Max Sharpe", maxSharpe, maxSharpeRatio),
}.Select(x =>
{
    var vals = new List<string> {
        x.label,
        (x.pt.Return * 100).ToString("F6", CultureInfo.InvariantCulture),
        (x.pt.Volatility * 100).ToString("F6", CultureInfo.InvariantCulture),
        x.sharpe.ToString("F6", CultureInfo.InvariantCulture)
    };
    vals.AddRange(x.pt.Weights.Select(w => w.ToString("F6", CultureInfo.InvariantCulture)));
    return vals;
});
SimpleCsv.WriteWithHeader(Path.Combine(outputDir, "frontier_key_portfolios.csv"), keyHeaders, keyRows);
Console.WriteLine($"Wrote {Path.Combine(outputDir, "frontier_key_portfolios.csv")}");

// --- bootstrap stability (Max Sharpe only, matching Python's scope) ---
if (!noBootstrap)
{
    Console.WriteLine($"\nRunning {nBootstrap} bootstrap resamples of the Max Sharpe portfolio (re-shrinking covariance each time)...");
    var stability = BootstrapMaxSharpe(reorderedReturns, isins, categoryGroups, maxWeight, maxCategoryWeight, riskFreeRate, nBootstrap);

    var stabHeaders = new List<string> { "isin", "name", "category", "mean_weight", "std_weight", "min_weight", "max_weight", "pct_samples_weight_gt_1pct" };
    var stabRows = isins.Select((isin, i) =>
    {
        var name = universe.TryGetValue(isin, out var row) ? row["name"] : "?";
        var cat = universe.TryGetValue(isin, out var row2) ? row2["category"] : "?";
        return new List<string> {
            isin, name, cat,
            stability.Mean[i].ToString("F4", CultureInfo.InvariantCulture),
            stability.Std[i].ToString("F4", CultureInfo.InvariantCulture),
            stability.Min[i].ToString("F4", CultureInfo.InvariantCulture),
            stability.Max[i].ToString("F4", CultureInfo.InvariantCulture),
            stability.PctGt1Pct[i].ToString("F4", CultureInfo.InvariantCulture),
        };
    }).OrderByDescending(r => double.Parse(r[3], CultureInfo.InvariantCulture));

    SimpleCsv.WriteWithHeader(Path.Combine(outputDir, "frontier_bootstrap_stability.csv"), stabHeaders, stabRows);
    Console.WriteLine($"Wrote {Path.Combine(outputDir, "frontier_bootstrap_stability.csv")}");
}

return 0;

// ---------------------------------------------------------------------------

static DirectoryInfo FindProjectRoot(string startDir)
{
    var dir = new DirectoryInfo(startDir);
    while (dir is not null && !dir.GetFiles("*.csproj").Any())
        dir = dir.Parent;
    return dir ?? new DirectoryInfo(startDir);
}

static (List<string> isins, double[,] cov) LoadCovariance(string path)
{
    using var reader = new StreamReader(path);
    var header = reader.ReadLine()!.Split(',');
    var isins = header.Skip(1).ToList();
    var n = isins.Count;
    var cov = new double[n, n];

    int row = 0;
    string? line;
    while ((line = reader.ReadLine()) is not null)
    {
        if (line.Length == 0) continue;
        var fields = line.Split(',');
        for (int j = 0; j < n; j++)
            cov[row, j] = double.Parse(fields[j + 1], CultureInfo.InvariantCulture);
        row++;
    }
    return (isins, cov);
}

static (List<DateTime> dates, List<string> isins, double[,] returns) LoadMonthlyReturns(string path)
{
    using var reader = new StreamReader(path);
    var header = reader.ReadLine()!.Split(',');
    var isins = header.Skip(1).ToList();
    var dates = new List<DateTime>();
    var rows = new List<double[]>();

    string? line;
    while ((line = reader.ReadLine()) is not null)
    {
        if (line.Length == 0) continue;
        var fields = line.Split(',');
        dates.Add(DateTime.Parse(fields[0], CultureInfo.InvariantCulture));
        rows.Add(fields.Skip(1).Select(f => double.Parse(f, CultureInfo.InvariantCulture)).ToArray());
    }

    var arr = new double[rows.Count, isins.Count];
    for (int i = 0; i < rows.Count; i++)
        for (int j = 0; j < isins.Count; j++)
            arr[i, j] = rows[i][j];
    return (dates, isins, arr);
}

static double[] AnnualizedGeometricReturn(double[,] monthlyReturns)
{
    int nMonths = monthlyReturns.GetLength(0), nFunds = monthlyReturns.GetLength(1);
    var mu = new double[nFunds];
    for (int j = 0; j < nFunds; j++)
    {
        double compounded = 1.0;
        for (int i = 0; i < nMonths; i++) compounded *= 1.0 + monthlyReturns[i, j];
        mu[j] = Math.Pow(compounded, 12.0 / nMonths) - 1.0;
    }
    return mu;
}

static (double target, QpResult result) GoldenSectionMaxSharpe(
    double[,] cov, double[] mu, Dictionary<string, List<int>> categoryGroups,
    double maxWeight, double maxCategoryWeight, double gmvReturn, double maxReturn,
    double riskFreeRate, int iterations)
{
    double gr = (Math.Sqrt(5.0) - 1.0) / 2.0;
    double lo = gmvReturn, hi = maxReturn;

    double SharpeAt(double targetReturn)
    {
        var res = QpSolver.SolveMinVariance(cov, mu, categoryGroups, maxWeight, maxCategoryWeight, targetReturn);
        if (res is null || res.Volatility <= 1e-12) return double.NegativeInfinity;
        return (res.Return - riskFreeRate) / res.Volatility;
    }

    double x1 = hi - gr * (hi - lo), x2 = lo + gr * (hi - lo);
    double f1 = SharpeAt(x1), f2 = SharpeAt(x2);

    for (int i = 0; i < iterations; i++)
    {
        if (f1 < f2)
        {
            lo = x1; x1 = x2; f1 = f2;
            x2 = lo + gr * (hi - lo);
            f2 = SharpeAt(x2);
        }
        else
        {
            hi = x2; x2 = x1; f2 = f1;
            x1 = hi - gr * (hi - lo);
            f1 = SharpeAt(x1);
        }
    }

    double bestTarget = (lo + hi) / 2.0;
    var bestResult = QpSolver.SolveMinVariance(cov, mu, categoryGroups, maxWeight, maxCategoryWeight, bestTarget);
    // Fall back to whichever bracket endpoint was best if the exact midpoint somehow fails
    // (can happen right at a constraint boundary) — never return null from this function.
    bestResult ??= (f1 >= f2
        ? QpSolver.SolveMinVariance(cov, mu, categoryGroups, maxWeight, maxCategoryWeight, x1)
        : QpSolver.SolveMinVariance(cov, mu, categoryGroups, maxWeight, maxCategoryWeight, x2))
        ?? throw new InvalidOperationException("Max Sharpe search failed to find any feasible point.");

    return (bestTarget, bestResult);
}

static (double[] Mean, double[] Std, double[] Min, double[] Max, double[] PctGt1Pct) BootstrapMaxSharpe(
    double[,] monthlyReturns, List<string> isins, Dictionary<string, List<int>> categoryGroups,
    double maxWeight, double maxCategoryWeight, double riskFreeRate, int nBootstrap, int seed = 42)
{
    int nMonths = monthlyReturns.GetLength(0), nFunds = monthlyReturns.GetLength(1);
    var rng = new Random(seed);
    var samples = new List<double[]>();

    for (int b = 0; b < nBootstrap; b++)
    {
        var resample = new double[nMonths, nFunds];
        for (int i = 0; i < nMonths; i++)
        {
            int src = rng.Next(nMonths);
            for (int j = 0; j < nFunds; j++)
                resample[i, j] = monthlyReturns[src, j];
        }

        var muBoot = AnnualizedGeometricReturn(resample);
        var (shrunkMonthly, _) = LinAlg.LedoitWolfShrink(resample);
        var covBoot = new double[nFunds, nFunds];
        for (int i = 0; i < nFunds; i++)
            for (int j = 0; j < nFunds; j++)
                covBoot[i, j] = shrunkMonthly[i, j] * 12.0; // annualize, matching Step 5's convention

        double maxSingle = muBoot.Max();
        var gmvBoot = QpSolver.SolveMinVariance(covBoot, muBoot, categoryGroups, maxWeight, maxCategoryWeight, null);
        if (gmvBoot is null) continue;

        var (_, resultBoot) = GoldenSectionMaxSharpe(
            covBoot, muBoot, categoryGroups, maxWeight, maxCategoryWeight, gmvBoot.Return, maxSingle, riskFreeRate, iterations: 30);
        samples.Add(resultBoot.Weights);
    }

    if (samples.Count < nBootstrap)
        Console.WriteLine($"  [note] {nBootstrap - samples.Count}/{nBootstrap} bootstrap resamples failed to converge, excluded");

    var mean = new double[nFunds]; var std = new double[nFunds];
    var min = new double[nFunds]; var max = new double[nFunds]; var pctGt1 = new double[nFunds];

    for (int j = 0; j < nFunds; j++)
    {
        var vals = samples.Select(s => s[j]).ToList();
        mean[j] = vals.Average();
        std[j] = vals.Count > 1 ? Math.Sqrt(vals.Sum(v => Math.Pow(v - mean[j], 2)) / vals.Count) : 0;
        min[j] = vals.Min();
        max[j] = vals.Max();
        pctGt1[j] = (double)vals.Count(v => v > 0.01) / vals.Count;
    }
    return (mean, std, min, max, pctGt1);
}
