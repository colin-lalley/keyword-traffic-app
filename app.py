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
        fill_value=0
    )

    # Rename columns to "Month 1", "Month 2", etc.
    pivot.columns = [f"Month {col}" for col in pivot.columns]

    # Add a Cumulative Total column
    pivot["Cumulative Total"] = pivot.sum(axis=1)

    return pivot.reset_index()

# --- Streamlit Interface ---

st.title("📈 Keyword Traffic Projection App (Page-Level)")

uploaded_file = st.file_uploader("Upload your keyword CSV", type=["csv"])

if uploaded_file:
    df = pd.read_csv(uploaded_file)
    df.columns = df.columns.str.strip()  # Clean column names

    st.subheader("Your Uploaded Data")
    st.dataframe(df)

    months = st.slider("Project for how many months?", 1, 12, 6)

    projections = project_traffic(df, months)
    pivoted = pivot_projection(projections, months)

    st.subheader("📊 Projected Traffic by Page")
    st.dataframe(pivoted)

    csv = pivoted.to_csv(index=False).encode('utf-8')
    st.download_button(
        label="Download Projected Traffic CSV",
        data=csv,
        file_name="projected_traffic_by_page.csv",
        mime="text/csv"
    )
