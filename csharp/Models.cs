using System.Text.Json.Serialization;

namespace MfToolkit;

public record FundEntry(string Isin, string Name, string Category, bool IsCurrentHolding, string Notes);

// Shape of GET https://mf.captnemo.in/nav/{isin}
public class NavResponse
{
    [JsonPropertyName("ISIN")]
    public string? Isin { get; set; }

    [JsonPropertyName("name")]
    public string? Name { get; set; }

    [JsonPropertyName("nav")]
    public double? Nav { get; set; }

    [JsonPropertyName("date")]
    public string? Date { get; set; }

    // Each element is [dateString, navNumber] — deserialized as raw JSON elements
    // because it's a heterogeneous tuple, not a fixed object shape.
    [JsonPropertyName("historical_nav")]
    public List<List<System.Text.Json.JsonElement>>? HistoricalNav { get; set; }
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
