using System.Text.Json.Serialization;

namespace MfToolkit;

public record FundEntry(string Isin, string Name, string Category, bool IsCurrentHolding, string Notes);

// One entry in the bulk GET https://api.mfapi.in/mf list (~37k schemes).
// isinGrowth/isinDivReinvestment are what let us resolve ISIN -> scheme code,
// since mfapi.in doesn't support looking up by ISIN directly.
public class MfapiSchemeListEntry
{
    [JsonPropertyName("schemeCode")] public int SchemeCode { get; set; }
    [JsonPropertyName("schemeName")] public string? SchemeName { get; set; }
    [JsonPropertyName("isinGrowth")] public string? IsinGrowth { get; set; }
    [JsonPropertyName("isinDivReinvestment")] public string? IsinDivReinvestment { get; set; }
}

// Shape of GET https://api.mfapi.in/mf/{scheme_code} — full NAV history, newest-first.
public class MfapiSchemeResponse
{
    [JsonPropertyName("meta")] public MfapiSchemeMeta? Meta { get; set; }
    [JsonPropertyName("data")] public List<MfapiNavEntry>? Data { get; set; }
    [JsonPropertyName("status")] public string? Status { get; set; }
}

public class MfapiSchemeMeta
{
    [JsonPropertyName("fund_house")] public string? FundHouse { get; set; }
    [JsonPropertyName("scheme_type")] public string? SchemeType { get; set; }
    [JsonPropertyName("scheme_category")] public string? SchemeCategory { get; set; }
    [JsonPropertyName("scheme_code")] public int SchemeCode { get; set; }
    [JsonPropertyName("scheme_name")] public string? SchemeName { get; set; }
}

public class MfapiNavEntry
{
    // Format "DD-MM-YYYY", e.g. "26-10-2024" — mfapi.in's convention, not ISO.
    [JsonPropertyName("date")] public string? Date { get; set; }
    [JsonPropertyName("nav")] public string? Nav { get; set; }
}

// Shape of GET https://mf.captnemo.in/kuvera/{isin} (a JSON array with one entry)
public class KuveraReturns
{
    [JsonPropertyName("year_1")] public double? Year1 { get; set; }
    [JsonPropertyName("year_3")] public double? Year3 { get; set; }
    [JsonPropertyName("year_5")] public double? Year5 { get; set; }
}

public class KuveraMetaEntry
{
    [JsonPropertyName("ISIN")] public string? Isin { get; set; }
    [JsonPropertyName("fund_house")] public string? FundHouse { get; set; }
    [JsonPropertyName("fund_category")] public string? FundCategory { get; set; }
    [JsonPropertyName("aum")] public double? Aum { get; set; }
    [JsonPropertyName("expense_ratio")] public string? ExpenseRatio { get; set; }
    [JsonPropertyName("start_date")] public string? StartDate { get; set; }
    [JsonPropertyName("lock_in_period")] public double? LockInPeriod { get; set; }
    [JsonPropertyName("volatility")] public double? Volatility { get; set; }
    [JsonPropertyName("fund_manager")] public string? FundManager { get; set; }
    [JsonPropertyName("returns")] public KuveraReturns? Returns { get; set; }
}
