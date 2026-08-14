namespace MfCorrelation;

/// <summary>
/// Minimal matrix math for exactly what Step 5 needs — not a general linear algebra
/// library. Two pieces worth flagging on trust level:
///
/// 1. LedoitWolfShrink implements the published Ledoit &amp; Wolf (2004) formula for
///    shrinkage toward a scaled-identity target, worked out from the paper's math
///    rather than transcribed from scikit-learn's source. The shrinkage intensity and
///    resulting covariance should be very close to sklearn's LedoitWolf — same
///    underlying method — but don't expect bit-for-bit identical output the way
///    Step 1's raw NAV data was. Compare shrinkage intensity and eigenvalues between
///    the Python and C# runs, not exact equality.
///
/// 2. EigenvaluesSymmetric is a classic cyclic Jacobi eigenvalue solver — a
///    well-established textbook algorithm for symmetric matrices, reliable for a
///    17x17 matrix, but hand-implemented rather than from a tested library. Used only
///    for the diagnostic positive-semi-definite check (min eigenvalue >= ~0), not for
///    anything that flows into another calculation.
/// </summary>
public static class LinAlg
{
    public static double[,] SampleCovariance(double[,] X, out double[,] demeanedX)
    {
        int n = X.GetLength(0), p = X.GetLength(1);
        var means = new double[p];
        for (int j = 0; j < p; j++)
        {
            double sum = 0;
            for (int i = 0; i < n; i++) sum += X[i, j];
            means[j] = sum / n;
        }

        var Xc = new double[n, p];
        for (int i = 0; i < n; i++)
            for (int j = 0; j < p; j++)
                Xc[i, j] = X[i, j] - means[j];
        demeanedX = Xc;

        // Biased (divide by n, not n-1) normalization — matches sklearn's default
        // empirical_covariance convention, which LedoitWolf builds on.
        var S = new double[p, p];
        for (int a = 0; a < p; a++)
            for (int b = 0; b < p; b++)
            {
                double sum = 0;
                for (int i = 0; i < n; i++) sum += Xc[i, a] * Xc[i, b];
                S[a, b] = sum / n;
            }
        return S;
    }

    public static (double[,] ShrunkCov, double Shrinkage) LedoitWolfShrink(double[,] X)
    {
        int n = X.GetLength(0), p = X.GetLength(1);
        var S = SampleCovariance(X, out var Xc);

        double mu = 0;
        for (int a = 0; a < p; a++) mu += S[a, a];
        mu /= p;

        // d2 = ||S - F||_F^2 where F = mu*I (scaled identity target).
        // Deliberately NOT divided by p here — what matters is that this uses the
        // SAME normalization convention as b2 below, since shrinkage = b2/d2 is a
        // ratio and any consistent scaling cancels out.
        double d2 = 0;
        for (int a = 0; a < p; a++)
            for (int b = 0; b < p; b++)
            {
                double target = a == b ? mu : 0.0;
                double diff = S[a, b] - target;
                d2 += diff * diff;
            }

        // b2_bar = (1/n^2) * sum_k || x_k x_k^T - S ||_F^2 — estimates how much the
        // sample covariance itself varies from observation to observation.
        double bBarSum = 0;
        for (int k = 0; k < n; k++)
        {
            double sumSq = 0;
            for (int a = 0; a < p; a++)
                for (int b = 0; b < p; b++)
                {
                    double outerAB = Xc[k, a] * Xc[k, b];
                    double diff = outerAB - S[a, b];
                    sumSq += diff * diff;
                }
            bBarSum += sumSq;
        }
        double b2Bar = bBarSum / ((double)n * n);
        double b2 = Math.Min(b2Bar, d2);
        double shrinkage = d2 > 0 ? b2 / d2 : 0.0;
        shrinkage = Math.Clamp(shrinkage, 0.0, 1.0);

        var shrunk = new double[p, p];
        for (int a = 0; a < p; a++)
            for (int b = 0; b < p; b++)
            {
                double target = a == b ? mu : 0.0;
                shrunk[a, b] = shrinkage * target + (1 - shrinkage) * S[a, b];
            }

        return (shrunk, shrinkage);
    }

    /// <summary>Classic cyclic Jacobi eigenvalue algorithm for a symmetric matrix. Returns eigenvalues sorted ascending.</summary>
    public static double[] EigenvaluesSymmetric(double[,] A, int maxSweeps = 100, double tol = 1e-12)
    {
        int n = A.GetLength(0);
        var a = (double[,])A.Clone();

        for (int sweep = 0; sweep < maxSweeps; sweep++)
        {
            double off = 0;
            for (int i = 0; i < n; i++)
                for (int j = 0; j < n; j++)
                    if (i != j) off += a[i, j] * a[i, j];
            if (Math.Sqrt(off) < tol) break;

            for (int p = 0; p < n - 1; p++)
            {
                for (int q = p + 1; q < n; q++)
                {
                    if (Math.Abs(a[p, q]) < 1e-300) continue;

                    double theta = (a[q, q] - a[p, p]) / (2 * a[p, q]);
                    double t = theta >= 0
                        ? 1.0 / (theta + Math.Sqrt(theta * theta + 1))
                        : -1.0 / (-theta + Math.Sqrt(theta * theta + 1));
                    double c = 1.0 / Math.Sqrt(t * t + 1);
                    double s = t * c;

                    double app = a[p, p], aqq = a[q, q], apq = a[p, q];
                    a[p, p] = c * c * app - 2 * s * c * apq + s * s * aqq;
                    a[q, q] = s * s * app + 2 * s * c * apq + c * c * aqq;
                    a[p, q] = 0; a[q, p] = 0;

                    for (int i = 0; i < n; i++)
                    {
                        if (i == p || i == q) continue;
                        double aip = a[i, p], aiq = a[i, q];
                        a[i, p] = c * aip - s * aiq; a[p, i] = a[i, p];
                        a[i, q] = s * aip + c * aiq; a[q, i] = a[i, q];
                    }
                }
            }
        }

        var eigenvalues = new double[n];
        for (int i = 0; i < n; i++) eigenvalues[i] = a[i, i];
        Array.Sort(eigenvalues);
        return eigenvalues;
    }
}
