namespace MfToolkit;

public class NavClient
{
    private const string MfapiListUrl = "https://api.mfapi.in/mf";
    private const string MfapiSchemeUrlTemplate = "https://api.mfapi.in/mf/{0}";
    private const string CaptnemoMetaUrlTemplate = "https://mf.captnemo.in/kuvera/{0}";

    private const int MaxRetries = 3;
    private const double RetryBackoffSecs = 2.0;
    private const int RequestTimeoutSecs = 20;
    private const int ListRequestTimeoutSecs = 60; // the bulk /mf list is large

    private readonly HttpClient _http;

    public NavClient()
    {
        _http = new HttpClient { Timeout = TimeSpan.FromSeconds(RequestTimeoutSecs) };
    }

    public async Task<string?> GetSchemeListRawAsync() =>
        await GetWithRetryAsync(MfapiListUrl, TimeSpan.FromSeconds(ListRequestTimeoutSecs));

    public async Task<string?> GetSchemeNavRawAsync(int schemeCode) =>
        await GetWithRetryAsync(string.Format(MfapiSchemeUrlTemplate, schemeCode), TimeSpan.FromSeconds(RequestTimeoutSecs));

    public async Task<string?> GetMetaRawAsync(string isin) =>
        await GetWithRetryAsync(string.Format(CaptnemoMetaUrlTemplate, isin), TimeSpan.FromSeconds(RequestTimeoutSecs));

    private async Task<string?> GetWithRetryAsync(string url, TimeSpan timeout)
    {
        string lastError = "";
        for (int attempt = 1; attempt <= MaxRetries; attempt++)
        {
            try
            {
                using var cts = new CancellationTokenSource(timeout);
                var response = await _http.GetAsync(url, cts.Token);
                if (response.IsSuccessStatusCode)
                    return await response.Content.ReadAsStringAsync();
                if (response.StatusCode == System.Net.HttpStatusCode.NotFound)
                {
                    Console.WriteLine($"  [warn] 404 not found: {url}");
                    return null;
                }
                lastError = $"HTTP {(int)response.StatusCode}";
            }
            catch (Exception ex)
            {
                lastError = ex.Message;
            }
            var wait = TimeSpan.FromSeconds(RetryBackoffSecs * attempt);
            Console.WriteLine($"  [retry {attempt}/{MaxRetries}] {url} -> {lastError}; waiting {wait.TotalSeconds:F1}s");
            await Task.Delay(wait);
        }
        Console.WriteLine($"  [error] giving up on {url}: {lastError}");
        return null;
    }
}
