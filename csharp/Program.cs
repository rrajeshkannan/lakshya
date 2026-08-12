// Step 0/1/2 of the portfolio pipeline: fund universe metadata + historical NAV acquisition.
//
// Reads:   ../data/funds_universe.csv
// Writes:  ../data/cache/mfapi_scheme_list.json         (bulk scheme list, cached)
//          ../data/cache/{isin}_nav.json / {isin}_meta.json   (raw API responses, cached)
//          ../output/nav_panel.csv        (dates x funds NAV matrix, forward-filled)
//          ../output/fund_metadata.csv    (flattened metadata)
//
// Data sources (hybrid, mirrors python/fetch_data.py):
//   - NAV history: api.mfapi.in. No ISIN lookup endpoint, so we resolve ISIN -> scheme
//     code via one cached bulk fetch of GET /mf (isinGrowth/isinDivReinvestment fields),
//     then pull full history via GET /mf/{scheme_code}.
//   - Metadata (AUM, expense ratio, fund manager): mf.captnemo.in /kuvera/{isin} —
//     mfapi.in's own metadata doesn't include these fields.
//
// Usage:
//   dotnet run                                   -- fetch/refresh everything
//   dotnet run -- --isin INF846K01K35             -- fetch just one fund (testing)
//   dotnet run -- --no-cache                      -- ignore cache, force re-download
//   dotnet run -- --max-age-days 7                -- treat cache older than 7 days as stale

using System.Text.Json;
using MfToolkit;

// walk up from bin/Debug/net8.0/ to the csharp/ project dir, then to the repo root
var projectDir = FindProjectRoot(AppContext.BaseDirectory);
var repoRoot = projectDir.Parent!.FullName;
var universeCsv = Path.Combine(repoRoot, "data", "funds_universe.csv");
var cacheDir = Path.Combine(repoRoot, "data", "cache");
var outputDir = Path.Combine(repoRoot, "output");
var schemeListCachePath = Path.Combine(cacheDir, "mfapi_scheme_list.json");

const int maxForwardFillDays = 5;
const double sleepBetweenCallsSecs = 0.5;
const int schemeListMaxAgeDaysDefault = 1; // the bulk list changes rarely; refresh daily at most

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
bool useCache = !noCache;

var schemeList = await EnsureSchemeListAsync(client, schemeListCachePath, useCache,
    maxAgeDays ?? schemeListMaxAgeDaysDefault);
var isinIndex = BuildIsinIndex(schemeList);
Console.WriteLine($"Resolved scheme-code index: {isinIndex.Count} ISINs known to mfapi.in\n");

var unresolved = funds.Where(f => !isinIndex.ContainsKey(f.Isin.Trim().ToUpperInvariant())).ToList();
if (unresolved.Count > 0)
{
    Console.WriteLine("[warn] ISINs not found in mfapi.in scheme list (NAV fetch will be skipped for these):");
    foreach (var f in unresolved)
        Console.WriteLine($"    {f.Isin}  {f.Name}");
    Console.WriteLine();
}

foreach (var fund in funds)
{
    await FetchFundAsync(fund, client, isinIndex, cacheDir, useCache: useCache, maxAgeDays: maxAgeDays);
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

static async Task<List<MfapiSchemeListEntry>> EnsureSchemeListAsync(
    NavClient client, string cachePath, bool useCache, int maxAgeDays)
{
    if (useCache && IsCacheFresh(cachePath, maxAgeDays))
    {
        Console.WriteLine("[cache] mfapi scheme list");
        var cached = await File.ReadAllTextAsync(cachePath);
        return JsonSerializer.Deserialize<List<MfapiSchemeListEntry>>(cached) ?? new();
    }

    Console.WriteLine("[fetch] mfapi scheme list (~37k schemes, one-time/occasional download)");
    var raw = await client.GetSchemeListRawAsync();
    if (raw is null)
    {
        if (File.Exists(cachePath))
        {
            Console.WriteLine("  [warn] using stale cached scheme list since fresh fetch failed");
            var stale = await File.ReadAllTextAsync(cachePath);
            return JsonSerializer.Deserialize<List<MfapiSchemeListEntry>>(stale) ?? new();
        }
        throw new InvalidOperationException("Could not fetch mfapi scheme list and no cache available.");
    }
    await File.WriteAllTextAsync(cachePath, raw);
    return JsonSerializer.Deserialize<List<MfapiSchemeListEntry>>(raw) ?? new();
}

static Dictionary<string, int> BuildIsinIndex(List<MfapiSchemeListEntry> schemeList)
{
    var index = new Dictionary<string, int>();
    foreach (var entry in schemeList)
    {
        if (!string.IsNullOrWhiteSpace(entry.IsinGrowth))
            index[entry.IsinGrowth.Trim().ToUpperInvariant()] = entry.SchemeCode;
        if (!string.IsNullOrWhiteSpace(entry.IsinDivReinvestment))
            index[entry.IsinDivReinvestment.Trim().ToUpperInvariant()] = entry.SchemeCode;
    }
    return index;
}

static async Task FetchFundAsync(FundEntry fund, NavClient client, Dictionary<string, int> isinIndex,
    string cacheDir, bool useCache, int? maxAgeDays)
{
    var navPath = CachePath(cacheDir, fund.Isin, "nav");
    if (useCache && IsCacheFresh(navPath, maxAgeDays))
    {
        Console.WriteLine($"[cache] {fund.Isin} NAV ({fund.Name})");
    }
    else if (isinIndex.TryGetValue(fund.Isin.Trim().ToUpperInvariant(), out var schemeCode))
    {
        Console.WriteLine($"[fetch] {fund.Isin} NAV via mfapi scheme {schemeCode} ({fund.Name})");
        var raw = await client.GetSchemeNavRawAsync(schemeCode);
        if (raw is not null) await File.WriteAllTextAsync(navPath, raw);
        await Task.Delay(TimeSpan.FromSeconds(sleepBetweenCallsSecs));
    }
    else
    {
        Console.WriteLine($"  [warn] {fund.Isin} ({fund.Name}): not found in mfapi scheme list, skipping NAV fetch");
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
        var payload = JsonSerializer.Deserialize<MfapiSchemeResponse>(json);
        var series = new Dictionary<string, double>();

        if (payload?.Data is not null)
        {
            foreach (var entry in payload.Data)
            {
                if (string.IsNullOrWhiteSpace(entry.Date) || string.IsNullOrWhiteSpace(entry.Nav))
                    continue;
                // mfapi.in dates are "DD-MM-YYYY", not ISO
                if (!DateTime.TryParseExact(entry.Date.Trim(), "dd-MM-yyyy",
                        System.Globalization.CultureInfo.InvariantCulture,
                        System.Globalization.DateTimeStyles.None, out var d))
                    continue; // skip anything we can't parse rather than guess
                if (!double.TryParse(entry.Nav, System.Globalization.NumberStyles.Float,
                        System.Globalization.CultureInfo.InvariantCulture, out var nav))
                    continue;
                var iso = d.ToString("yyyy-MM-dd");
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
