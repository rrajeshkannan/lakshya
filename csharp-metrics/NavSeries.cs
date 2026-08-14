namespace MfMetrics;

/// <summary>
/// A sorted date -> value series with a pandas-Series.asof()-equivalent lookup:
/// given any date, returns the value at the latest date <= that date, or null if
/// the date is before the series starts. This is the building block every rolling
/// calculation depends on, so it gets its own small, carefully-tested class rather
/// than being reimplemented inline each time.
/// </summary>
public class NavSeries
{
    public List<DateTime> Dates { get; }
    private readonly Dictionary<DateTime, double> _values;

    public NavSeries(IEnumerable<(DateTime date, double value)> points)
    {
        var sorted = points.OrderBy(p => p.date).ToList();
        Dates = sorted.Select(p => p.date).ToList();
        _values = sorted.ToDictionary(p => p.date, p => p.value);
    }

    public double this[DateTime date] => _values[date];

    public bool Contains(DateTime date) => _values.ContainsKey(date);

    /// <summary>Value at the latest date <= the given date, or null if none exists.</summary>
    public double? AsOf(DateTime date)
    {
        int lo = 0, hi = Dates.Count - 1, ans = -1;
        while (lo <= hi)
        {
            int mid = (lo + hi) / 2;
            if (Dates[mid] <= date) { ans = mid; lo = mid + 1; }
            else hi = mid - 1;
        }
        return ans == -1 ? null : _values[Dates[ans]];
    }

    /// <summary>
    /// Last observation per calendar month, RE-KEYED to the calendar month-end date
    /// (not the actual last trading date observed) — this deliberately mirrors
    /// pandas' `to_period("M")...to_timestamp(how="end")` behavior from
    /// pipeline_utils.py, so two series with different actual trading calendars
    /// still align on the same synthetic month-end labels for comparison.
    /// </summary>
    public NavSeries MonthlyLast()
    {
        var lastInMonth = new Dictionary<(int year, int month), double>();
        foreach (var date in Dates) // ascending order, so later overwrites earlier = "last"
            lastInMonth[(date.Year, date.Month)] = _values[date];

        var points = lastInMonth.Select(kv =>
        {
            var (y, m) = kv.Key;
            var monthEnd = new DateTime(y, m, DateTime.DaysInMonth(y, m));
            return (monthEnd, kv.Value);
        });
        return new NavSeries(points);
    }

    /// <summary>Simple period-over-period returns (value[i]/value[i-1] - 1), in date order.</summary>
    public List<(DateTime date, double ret)> PctChange()
    {
        var result = new List<(DateTime, double)>();
        for (int i = 1; i < Dates.Count; i++)
        {
            var prev = _values[Dates[i - 1]];
            var cur = _values[Dates[i]];
            if (prev > 0)
                result.Add((Dates[i], cur / prev - 1.0));
        }
        return result;
    }
}
