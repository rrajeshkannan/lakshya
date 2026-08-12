// Step 0/1/2 of the portfolio pipeline: fund universe metadata + historical NAV acquisition.
//
// Reads:   ../data/funds_universe.csv
// Writes:  ../data/cache/{isin}_nav.json / {isin}_meta.json   (raw API responses, cached)
//          ../output/nav_panel.csv        (dates x funds NAV matrix, forward-filled)
//          ../output/fund_metadata.csv    (flattened metadata)
//
// This mirrors python/fetch_data.py field-for-field and format-for-format, so the two
// outputs can be diffed against each other as a sanity check that both pipelines agree.
//
// Usage:
//   dotnet run                                   -- fetch/refresh everything
//   dotnet run -- --isin INF846K01K35             -- fetch just one fund (testing)
//   dotnet run -- --no-cache                      -- ignore cache, force re-download
//   dotnet run -- --max-age-days 7                -- treat cache older than 7 days as stale
//
// Caveats carried over from the Python version:
//   - mf.captnemo.in is an unofficial free API. Spot-check a few NAVs against the AMC's
//     own factsheet before trusting this for real decisions.
//   - Be a good citizen of a free service: this sleeps between calls and retries with backoff.

using System.Text.Json;
using MfToolkit;

// walk up from bin/Debug/net8.0/ to the csharp/ project dir, then to the repo root
var projectDir = FindProjectRoot(AppContext.BaseDirectory);
var repoRoot = projectDir.Parent!.FullName;
var universeCsv = Path.Combine(repoRoot, "data", "funds_universe.csv");
var cacheDir = Path.Combine(repoRoot, "data", "cache");
var outputDir = Path.Combine(repoRoot, "output");

const int maxForwardFillDays = 5;
const double sleepBetweenCallsSecs = 0.5;

string? isinFilter = null;
bool noCache = false;
int? maxAgeDays = null;

for (int i = 0; i < args.Length; i++)
{
    switch (args[i])
    {
        case "--isin":
            isinFilter = args[++i];
            break;
        case "--no-cache":
            noCache = true;
            break;
        case "--max-age-days":
            maxAgeDays = int.Parse(args[++i]);
            break;
    }
}

var funds = ReadUniverse(universeCsv);
if (isinFilter is not null)
{
    funds = funds.Where(f => f.Isin == isinFilter).ToList();
    if (funds.Count == 0)
    {
        Console.WriteLine($"ISIN {isinFilter} not found in {universeCsv}");
        return 1;
    }
}

Directory.CreateDirectory(cacheDir);
Directory.CreateDirectory(outputDir);

var client = new NavClient();
foreach (var fund in funds)
{
    await FetchFundAsync(fund, client, cacheDir, useCache: !noCache, maxAgeDays: maxAgeDays);
}

var allFunds = ReadUniverse(universeCsv);
BuildMetadataTable(allFunds, cacheDir, outputDir);
BuildNavPanel(allFunds, cacheDir, outputDir, maxForwardFillDays);

return 0;

// ---------------------------------------------------------------------------

static DirectoryInfo FindProjectRoot(string startDir)
{
    var dir = new DirectoryInfo(startDir);
    while (dir is not null && !dir.GetFiles("*.csproj").Any())
        dir = dir.Parent;
    return dir ?? new DirectoryInfo(startDir);
}

static List<FundEntry> ReadUniverse(string path)
{
    if (!File.Exists(path))
        throw new FileNotFoundException(
            $"Fund universe file not found at {path}. " +
            "Create it with columns: isin,name,category,is_current_holding,notes");

    var rows = SimpleCsv.ReadWithHeader(path);
    return rows.Select(r => new FundEntry(
        Isin: r["isin"].Trim(),
        Name: r["name"].Trim(),
        Category: r["category"].Trim(),
        IsCurrentHolding: r.GetValueOrDefault("is_current_holding", "").Trim().ToLowerInvariant() == "true",
        Notes: r.GetValueOrDefault("notes", "").Trim()
    )).ToList();
}

static string CachePath(string cacheDir, string isin, string kind) =>
    Path.Combine(cacheDir, $"{isin}_{kind}.json");

static bool IsCacheFresh(string path, int? maxAgeDays)
{
    if (!File.Exists(path)) return false;
    if (maxAgeDays is null) return true;
    var age = DateTime.Now - File.GetLastWriteTime(path);
    return age < TimeSpan.FromDays(maxAgeDays.Value);
}

static async Task FetchFundAsync(FundEntry fund, NavClient client, string cacheDir, bool useCache, int? maxAgeDays)
{
    var navPath = CachePath(cacheDir, fund.Isin, "nav");
    if (useCache && IsCacheFresh(navPath, maxAgeDays))
    {
        Console.WriteLine($"[cache] {fund.Isin} NAV ({fund.Name})");
    }
    else
    {
        Console.WriteLine($"[fetch] {fund.Isin} NAV ({fund.Name})");
        var raw = await client.GetNavRawAsync(fund.Isin);
        if (raw is not null) await File.WriteAllTextAsync(navPath, raw);
        await Task.Delay(TimeSpan.FromSeconds(sleepBetweenCallsSecs));
    }

    var metaPath = CachePath(cacheDir, fund.Isin, "meta");
    if (useCache && IsCacheFresh(metaPath, maxAgeDays))
    {
        Console.WriteLine($"[cache] {fund.Isin} metadata");
    }
    else
    {
        Console.WriteLine($"[fetch] {fund.Isin} metadata");
        var raw = await client.GetMetaRawAsync(fund.Isin);
        if (raw is not null) await File.WriteAllTextAsync(metaPath, raw);
        await Task.Delay(TimeSpan.FromSeconds(sleepBetweenCallsSecs));
    }
}

static void BuildMetadataTable(List<FundEntry> funds, string cacheDir, string outputDir)
{
    var outPath = Path.Combine(outputDir, "fund_metadata.csv");
    var headers = new[]
    {
        "isin", "name", "category", "is_current_holding",
        "fund_house", "kuvera_category", "aum_cr", "expense_ratio_pct",
        "start_date", "lock_in_days", "return_1y", "return_3y", "return_5y",
        "volatility", "fund_manager",
    };

    var rows = new List<List<string>>();
    foreach (var fund in funds)
    {
        var row = new Dictionary<string, string>
        {
            ["isin"] = fund.Isin, ["name"] = fund.Name, ["category"] = fund.Category,
            ["is_current_holding"] = fund.IsCurrentHolding.ToString().ToLowerInvariant(),
            ["fund_house"] = "", ["kuvera_category"] = "", ["aum_cr"] = "", ["expense_ratio_pct"] = "",
            ["start_date"] = "", ["lock_in_days"] = "", ["return_1y"] = "", ["return_3y"] = "",
            ["return_5y"] = "", ["volatility"] = "", ["fund_manager"] = "",
        };

        var metaPath = CachePath(cacheDir, fund.Isin, "meta");
        if (File.Exists(metaPath))
        {
            try
            {
                var json = File.ReadAllText(metaPath);
                var entries = JsonSerializer.Deserialize<List<KuveraMetaEntry>>(json);
                var entry = entries?.FirstOrDefault();
                if (entry is not null)
                {
                    row["fund_house"] = entry.FundHouse ?? "";
                    row["kuvera_category"] = entry.FundCategory ?? "";
                    row["aum_cr"] = entry.Aum?.ToString() ?? "";
                    row["expense_ratio_pct"] = entry.ExpenseRatio ?? "";
                    row["start_date"] = entry.StartDate ?? "";
                    row["lock_in_days"] = entry.LockInPeriod?.ToString() ?? "";
                    row["return_1y"] = entry.Returns?.Year1?.ToString() ?? "";
                    row["return_3y"] = entry.Returns?.Year3?.ToString() ?? "";
                    row["return_5y"] = entry.Returns?.Year5?.ToString() ?? "";
                    row["volatility"] = entry.Volatility?.ToString() ?? "";
                    row["fund_manager"] = entry.FundManager ?? "";
                }
            }
            catch (JsonException ex)
            {
                Console.WriteLine($"  [warn] could not parse metadata for {fund.Isin}: {ex.Message}");
            }
        }
        rows.Add(headers.Select(h => row[h]).ToList());
    }

    SimpleCsv.WriteWithHeader(outPath, headers, rows);
    Console.WriteLine($"Wrote {outPath} ({rows.Count} funds)");
}

static void BuildNavPanel(List<FundEntry> funds, string cacheDir, string outputDir, int maxForwardFillDays)
{
    var seriesByIsin = new Dictionary<string, Dictionary<string, double>>();
    var allDates = new SortedSet<string>(StringComparer.Ordinal);

    foreach (var fund in funds)
    {
        var navPath = CachePath(cacheDir, fund.Isin, "nav");
        if (!File.Exists(navPath))
        {
            Console.WriteLine($"  [warn] no cached NAV data for {fund.Isin}, skipping in panel");
            continue;
        }

        var json = File.ReadAllText(navPath);
        var payload = JsonSerializer.Deserialize<NavResponse>(json);
        var series = new Dictionary<string, double>();

        if (payload?.HistoricalNav is not null)
        {
            foreach (var pair in payload.HistoricalNav)
            {
                if (pair.Count < 2) continue;
                var dateStr = pair[0].GetString();
                if (dateStr is null) continue;
                if (!DateTime.TryParse(dateStr, out var d))
                    continue; // skip anything we can't parse rather than guess
                var iso = d.ToString("yyyy-MM-dd");
                var nav = pair[1].GetDouble();
                series[iso] = nav;
                allDates.Add(iso);
            }
        }
        seriesByIsin[fund.Isin] = series;
    }

    var sortedDates = allDates.ToList();
    var isins = seriesByIsin.Keys.ToList();

    var lastValue = new Dictionary<string, double>();
    var gapLen = new Dictionary<string, int>();
    foreach (var isin in isins) gapLen[isin] = 0;

    var filled = new Dictionary<string, Dictionary<string, string>>();
    foreach (var isin in isins) filled[isin] = new Dictionary<string, string>();

    foreach (var date in sortedDates)
    {
        foreach (var isin in isins)
        {
            var series = seriesByIsin[isin];
            if (series.TryGetValue(date, out var nav))
            {
                lastValue[isin] = nav;
                gapLen[isin] = 0;
                filled[isin][date] = nav.ToString("F4");
            }
            else if (lastValue.ContainsKey(isin) && gapLen[isin] < maxForwardFillDays)
            {
                gapLen[isin]++;
                filled[isin][date] = lastValue[isin].ToString("F4");
            }
            else
            {
                filled[isin][date] = "";
            }
        }
    }

    var outPath = Path.Combine(outputDir, "nav_panel.csv");
    var headers = new List<string> { "date" }.Concat(isins).ToList();
    var rows = sortedDates.Select(date =>
        new List<string> { date }.Concat(isins.Select(isin => filled[isin].GetValueOrDefault(date, ""))).ToList()
    );

    SimpleCsv.WriteWithHeader(outPath, headers, rows);
    Console.WriteLine($"Wrote {outPath} ({sortedDates.Count} dates x {isins.Count} funds)");
}
