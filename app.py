import streamlit as st
import pandas as pd

# CTR assumptions based on ranking position
CTR_LOOKUP = {
    1: 0.31,
    2: 0.24,
    3: 0.18,
    4: 0.13,
    5: 0.10,
    6: 0.08,
    7: 0.06,
    8: 0.05,
    9: 0.04,
    10: 0.03
}

def estimate_rank(difficulty, month):
    """Estimate keyword ranking improvement over time."""
    base_rank = 50
    improvement_rate = max(1, (100 - difficulty) / 10)
    rank = base_rank - (improvement_rate * month)
    return max(1, min(100, int(rank)))

def get_ctr(rank):
    """Get CTR based on estimated ranking position."""
    return CTR_LOOKUP.get(rank, 0.01)

def project_traffic(df, months=6):
    """Create a monthly projection DataFrame."""
    projections = []
    for idx, row in df.iterrows():
        keyword = row['Keyword']
        volume = row['Monthly Search Volume']
        difficulty = row['Difficulty']
        page = row['Assigned Page']

        for month in range(1, months + 1):
            est_rank = estimate_rank(difficulty, month)
            ctr = get_ctr(est_rank)
            est_traffic = volume * ctr
            projections.append({
                "Assigned Page": page,
                "Month": month,
                "Estimated Traffic": est_traffic
            })
    return pd.DataFrame(projections)

def pivot_projection(projections, months):
    """Pivot the data: rows = page, columns = months + cumulative"""
    pivot = projections.pivot_table(
    index="Assigned Page",
    columns="Month",
    values="Estimated Traffic",
    aggfunc="sum",
    fill_value=0,
)
