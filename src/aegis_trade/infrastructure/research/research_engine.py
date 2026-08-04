import pandas as pd
import numpy as np
import math
from typing import List, Dict

from aegis_trade.domain.features import FeatureSet
from aegis_trade.domain.research import AlphaResearchResult, ResearchMetadata, FeatureScore
from aegis_trade.domain.ports.research_engine import IResearchEngine

# Rolling window used to trace the IC through time. Only feeds stability and IR;
# the headline IC is measured on the full sample.
ROLLING_WINDOW = 30

# |t| above which a feature stays in the running. Deliberately not a discovery
# threshold: dozens of features are screened at once and no family-wise
# correction is applied here.
SIGNIFICANCE_T = 2.0


def _effective_observations(observations: int, horizon: int) -> int:
    """Sample size corrected for the overlap of forward returns.

    Row t and row t+1 share N-1 bars of their forward window, so consecutive
    observations are strongly correlated and the raw count overstates the
    information available by roughly a factor N. The largest non-overlapping
    subsample has `observations // N` rows: that is what any test of
    significance may spend.

    Conservative on purpose. Ignoring the overlap inflates a t by ~sqrt(N) —
    at N=10 that turns noise into a "discovery".
    """
    if horizon < 1:
        raise ValueError(f"horizon must be >= 1 (got {horizon}).")
    return observations // horizon


def _rank_ic_t_stat(ic: float, effective_observations: int) -> float:
    """Student t of a rank correlation against zero, on the effective sample.

    Under the null of no association, `t = ic * sqrt((n-2) / (1 - ic^2))` follows
    a t distribution with n-2 degrees of freedom. `n` here is the OVERLAP
    -CORRECTED count, never the raw one.
    """
    if effective_observations < 3:
        return 0.0
    if not math.isfinite(ic):
        return 0.0
    # An |IC| of exactly 1 gives an infinite t. It never happens on genuine
    # forward returns and is the signature of a target leak — the 0.9645 of the
    # only report on file being the case in point. Clamp rather than zero: an
    # enormous finite t keeps the leak at the top of the ranking where it gets
    # noticed, whereas zeroing it would bury the very thing worth catching.
    bounded_ic = max(-1.0 + 1e-12, min(1.0 - 1e-12, ic))
    denominator = 1.0 - bounded_ic * bounded_ic
    return float(bounded_ic * math.sqrt((effective_observations - 2) / denominator))


class ResearchEngine(IResearchEngine):
    """
    Evaluates quantitative features for predictive power (Information Coefficient).
    Implementation relies purely on pandas and numpy.

    The IC reported is a RANK correlation (Spearman), as the term implies. An
    earlier revision computed Pearson while its own comments claimed Spearman:
    Pearson is driven by the tails of a fat-tailed return distribution and can
    read as signal what is a handful of bars.

    Every IC ships with the sample size that produced it and a t computed on
    that sample AFTER correcting for forward-return overlap. An IC without a
    dispersion budget cannot answer "is there a signal" — it is the same mistake
    as reading an in-sample fit metric as a validation.
    """

    def evaluate(self, features: List[FeatureSet], metadata: ResearchMetadata) -> AlphaResearchResult:
        if not features:
            raise ValueError("No features provided for evaluation.")

        # 1. Convert to DataFrame
        df = pd.DataFrame([fs.features for fs in features])

        # 2. Reconstruct price path to calculate future returns.
        # return_1d is (P_t / P_{t-1}) - 1
        # We replace NaNs with 0 to allow cumprod to work from the start.
        if 'return_1d' not in df.columns:
            raise ValueError("return_1d must be present in features to calculate forward returns.")

        returns = df['return_1d'].fillna(0)
        price_index = (1 + returns).cumprod()

        N = metadata.forward_returns_lag
        # Future return: (P_{t+N} - P_t) / P_t
        # Shift -N aligns the future return at t+N with row t
        future_returns = price_index.pct_change(periods=N).shift(-N)

        feature_scores: Dict[str, FeatureScore] = {}

        # 3. Correlation Matrix (Global)
        corr_matrix_df = df.corr(method='pearson')
        correlation_matrix = corr_matrix_df.to_dict()

        # 4. Evaluate each feature
        for col in df.columns:
            # We don't evaluate the base price/return components as predictive alpha signals,
            # but for completeness, we can evaluate everything, or skip returns.
            series = df[col].astype(float)

            # Descriptive stats
            mean_val = series.mean()
            var_val = series.var()
            std_val = series.std()
            skew_val = series.skew()
            kurtosis_val = series.kurtosis()
            missing_rate = series.isna().mean()

            # IC Calculation
            # Align feature at t with future_return at t
            valid_mask = series.notna() & future_returns.notna()
            clean_feature = series[valid_mask]
            clean_future_ret = future_returns[valid_mask]

            observations = int(len(clean_feature))
            effective_observations = _effective_observations(observations, N)

            if observations < 10 or std_val == 0 or pd.isna(std_val):
                # Not enough data or constant feature
                ic_mean = 0.0
                ic_std = 0.0
                ir = 0.0
                stability = 0.0
                ic_spearman = 0.0
            else:
                # Full-sample rank IC: the headline number, and the only one with
                # a sample size attached.
                spearman = clean_feature.corr(clean_future_ret, method='spearman')
                ic_spearman = 0.0 if pd.isna(spearman) else float(spearman)

                # Rolling IC traces the IC through time to yield IR and stability.
                # Ranking the full series once and rolling Pearson over the ranks
                # APPROXIMATES a rolling Spearman: true window-local ranks would
                # cost O(n * w log w). The approximation is monotone-invariant
                # like Spearman and immune to the same outliers; it differs only
                # in that a window's ranks are read on the global scale.
                window = min(ROLLING_WINDOW, observations)
                feature_ranks = clean_feature.rank()
                future_ranks = clean_future_ret.rank()
                rolling_ic = feature_ranks.rolling(window).corr(future_ranks)

                # Mean IC and IC Std (using the point-wise rolling IC)
                ic_mean = rolling_ic.mean()
                ic_std = rolling_ic.std()

                if pd.isna(ic_mean):
                    ic_mean = 0.0
                if pd.isna(ic_std) or ic_std == 0:
                    ic_std = 0.0

                ir = ic_mean / ic_std if ic_std != 0 else 0.0

                # Stability = proportion of periods where IC has the same sign as the Mean IC
                if ic_mean != 0:
                    sign_matches = (np.sign(rolling_ic.dropna()) == np.sign(ic_mean)).mean()
                    stability = sign_matches
                else:
                    stability = 0.0

            t_stat = _rank_ic_t_stat(ic_spearman, effective_observations)
            is_significant = abs(t_stat) > SIGNIFICANCE_T

            # 5. Final Score Calculation (Ranking)
            # abs(IR) * stability, but ZEROED when the IC does not clear its own
            # error bar. Without that gate the ranking is a leaderboard of noise:
            # a feature whose rolling IC is small and merely consistent scores
            # above one that is larger but measured on too few effective
            # observations. abs() is intended — a stable NEGATIVE IC is tradable
            # inverted — which is also why `bottom_features` means "no measurable
            # relation", not "anti-predictive".
            final_score = abs(ir) * stability if is_significant else 0.0

            score = FeatureScore(
                feature_name=col,
                mean=float(mean_val) if not pd.isna(mean_val) else 0.0,
                variance=float(var_val) if not pd.isna(var_val) else 0.0,
                std_dev=float(std_val) if not pd.isna(std_val) else 0.0,
                skewness=float(skew_val) if not pd.isna(skew_val) else 0.0,
                kurtosis=float(kurtosis_val) if not pd.isna(kurtosis_val) else 0.0,
                missing_rate=float(missing_rate),
                ic_mean=float(ic_mean),
                ic_std=float(ic_std),
                ic_information_ratio=float(ir),
                stability=float(stability),
                final_score=float(final_score),
                ic_spearman=float(ic_spearman),
                observations=observations,
                effective_observations=effective_observations,
                ic_t_stat=float(t_stat),
                is_significant=bool(is_significant),
            )
            feature_scores[col] = score

        # 6. Rank Features
        # Sort features by final_score descending
        ranked_features = sorted(feature_scores.values(), key=lambda x: x.final_score, reverse=True)
        ranked_names = [x.feature_name for x in ranked_features]
        
        top_features = ranked_names[:max(1, len(ranked_names) // 3)]
        bottom_features = ranked_names[-max(1, len(ranked_names) // 3):]
        
        return AlphaResearchResult(
            metadata=metadata,
            feature_scores=feature_scores,
            correlation_matrix=correlation_matrix,
            top_features=top_features,
            bottom_features=bottom_features
        )
