using Accord.Math.Optimization;

namespace MfFrontier;

public record QpResult(double[] Weights, double Return, double Volatility);

/// <summary>
/// Wraps GoldfarbIdnani for the one problem shape this pipeline needs: minimize
/// portfolio variance subject to long-only weights, a per-fund cap, optional
/// per-category caps, and an optional target-return constraint.
///
/// Objective convention (verified against Accord's own worked examples before writing
/// this — see the project README/commit notes): GoldfarbIdnani minimizes 0.5*w'Qw + d'w.
/// Portfolio variance is w'*Cov*w, so setting Q = 2*Cov and d = 0 makes 0.5*w'Qw exactly
/// equal to w'*Cov*w. Getting this factor of 2 wrong would silently produce a portfolio
/// with the right relative weight proportions between funds but the wrong absolute risk
/// number — worth remembering if any downstream volatility figure ever looks half or
/// double what's expected.
///
/// GMV = call with targetReturn: null. A specific frontier point = call with a target
/// return. There is deliberately no direct "maximize Sharpe" method here — Sharpe is a
/// ratio, not a quadratic form, so it isn't solvable by a QP solver directly. See
/// Program.cs for how Max Sharpe is approximated instead (best point on a sufficiently
/// dense frontier, not a separate nonlinear solve).
/// </summary>
public static class QpSolver
{
    public static QpResult? SolveMinVariance(
        double[,] cov, double[] mu, Dictionary<string, List<int>> categoryGroups,
        double maxWeight, double? maxCategoryWeight, double? targetReturn)
    {
        int n = mu.Length;

        var Q = new double[n, n];
        for (int i = 0; i < n; i++)
            for (int j = 0; j < n; j++)
                Q[i, j] = 2.0 * cov[i, j];
        var d = new double[n]; // no linear term — pure variance minimization

        var constraints = new List<LinearConstraint>();

        // sum(w) = 1
        constraints.Add(new LinearConstraint(numberOfVariables: n)
        {
            VariablesAtIndices = Enumerable.Range(0, n).ToArray(),
            CombinedAs = Enumerable.Repeat(1.0, n).ToArray(),
            ShouldBe = ConstraintType.EqualTo,
            Value = 1.0
        });

        // mu . w = targetReturn (omitted entirely for GMV, which has no return target)
        if (targetReturn is not null)
        {
            constraints.Add(new LinearConstraint(numberOfVariables: n)
            {
                VariablesAtIndices = Enumerable.Range(0, n).ToArray(),
                CombinedAs = (double[])mu.Clone(),
                ShouldBe = ConstraintType.EqualTo,
                Value = targetReturn.Value
            });
        }

        // w_i >= 0 (long only)
        for (int i = 0; i < n; i++)
        {
            constraints.Add(new LinearConstraint(numberOfVariables: 1)
            {
                VariablesAtIndices = new[] { i },
                CombinedAs = new[] { 1.0 },
                ShouldBe = ConstraintType.GreaterThanOrEqualTo,
                Value = 0.0
            });
        }

        // w_i <= maxWeight
        for (int i = 0; i < n; i++)
        {
            constraints.Add(new LinearConstraint(numberOfVariables: 1)
            {
                VariablesAtIndices = new[] { i },
                CombinedAs = new[] { 1.0 },
                ShouldBe = ConstraintType.LesserThanOrEqualTo,
                Value = maxWeight
            });
        }

        // per-category caps
        if (maxCategoryWeight is not null)
        {
            foreach (var indices in categoryGroups.Values)
            {
                if (indices.Count == 0) continue;
                constraints.Add(new LinearConstraint(numberOfVariables: indices.Count)
                {
                    VariablesAtIndices = indices.ToArray(),
                    CombinedAs = Enumerable.Repeat(1.0, indices.Count).ToArray(),
                    ShouldBe = ConstraintType.LesserThanOrEqualTo,
                    Value = maxCategoryWeight.Value
                });
            }
        }

        var objective = new QuadraticObjectiveFunction(Q, d);
        var solver = new GoldfarbIdnani(objective, constraints);

        bool success;
        try
        {
            success = solver.Minimize();
        }
        catch
        {
            return null; // infeasible / numerically failed — caller treats like scipy's res.success == False
        }
        if (!success) return null;

        var w = solver.Solution;
        double ret = 0.0;
        for (int i = 0; i < n; i++) ret += w[i] * mu[i];
        double variance = 0.0;
        for (int i = 0; i < n; i++)
            for (int j = 0; j < n; j++)
                variance += w[i] * cov[i, j] * w[j];

        return new QpResult(w, ret, Math.Sqrt(Math.Max(variance, 0.0)));
    }
}
