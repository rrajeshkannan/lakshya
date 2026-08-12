using System.Text.Json;

namespace MfToolkit;

public class NavClient
{
    private const string NavUrlTemplate = "https://mf.captnemo.in/nav/{0}";
    private const string MetaUrlTemplate = "https://mf.captnemo.in/kuvera/{0}";
    private const int MaxRetries = 3;
    private const double RetryBackoffSecs = 2.0;
    private const int RequestTimeoutSecs = 20;

    private readonly HttpClient _http;

    public NavClient()
    {
        _http = new HttpClient { Timeout = TimeSpan.FromSeconds(RequestTimeoutSecs) };
    }

    public async Task<string?> GetNavRawAsync(string isin) =>
        await GetWithRetryAsync(string.Format(NavUrlTemplate, isin));

    public async Task<string?> GetMetaRawAsync(string isin) =>
        await GetWithRetryAsync(string.Format(MetaUrlTemplate, isin));

    private async Task<string?> GetWithRetryAsync(string url)
    {
        string lastError = "";
        for (int attempt = 1; attempt <= MaxRetries; attempt++)
        {
            try
            {
                var response = await _http.GetAsync(url);
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
