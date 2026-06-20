"""Ranking and AHP helper functions."""

import pandas as pd


def normalize_custom_ranking(
    ranking_data, max_rank, min_new_scale=1, max_new_scale=9
):
    """Normalize integer ranks into a new integer scoring scale."""
    if max_rank <= 1:
        raise ValueError("max_rank must be greater than 1")

    return {
        key: min_new_scale
        + int((value - 1) / (max_rank - 1) * (max_new_scale - min_new_scale))
        for key, value in ranking_data.items()
    }


def create_ahp_matrix(normalized_ranks):
    """Create an AHP pairwise-comparison matrix from normalized ranks."""
    factors = list(normalized_ranks.keys())
    ahp_matrix = pd.DataFrame(index=factors, columns=factors, dtype=float)

    for row_factor in factors:
        for col_factor in factors:
            if row_factor == col_factor:
                ahp_matrix.loc[row_factor, col_factor] = 1.0
            else:
                ahp_matrix.loc[row_factor, col_factor] = (
                    normalized_ranks[row_factor] / normalized_ranks[col_factor]
                )

    return ahp_matrix


def calculate_ahp_weights(ahp_matrix):
    """Calculate percentage weights from an AHP pairwise-comparison matrix."""
    column_sums = ahp_matrix.sum()
    normalized_matrix = ahp_matrix.divide(column_sums, axis=1)
    weights = normalized_matrix.mean(axis=1)
    return (weights / weights.sum()) * 100
