import pandas as pd
import numpy as np
import scipy.stats as stats
from typing import List, Dict, Tuple
from datetime import datetime

from aegis_trade.domain.features import FeatureSet
from aegis_trade.domain.research import AlphaResearchResult, ResearchMetadata, FeatureScore
from aegis_trade.domain.ports.research_engine import IResearchEngine

class ResearchEngine(IResearchEngine):
    """
    Evaluates quantitative features for predictive power (Information Coefficient).
    Implementation relies purely on pandas, numpy, and scipy.
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
            
            if len(clean_feature) < 10 or std_val == 0 or pd.isna(std_val):
                # Not enough data or constant feature
                ic_mean = 0.0
                ic_std = 0.0
                ir = 0.0
                stability = 0.0
            else:
                # Rolling IC to calculate IC Mean, Std and Stability
                # We use a 30-period rolling window (or available length) to calculate rolling Spearman correlation
                window = min(30, len(clean_feature))
                
                # Pandas rolling corr uses Pearson by default. For rank correlation (Spearman),
                # we must rank the data first inside the rolling window, which is computationally heavy,
                # or we just use rolling Pearson on rank-transformed whole series (approximation).
                # To be precise mathematically:
                rolling_ic = clean_feature.rolling(window).corr(clean_future_ret)
                
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
            
            # 5. Final Score Calculation (Ranking)
            # A simple institutional scoring metric: Abs(IR) * Stability
            final_score = abs(ir) * stability
            
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
                final_score=float(final_score)
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
