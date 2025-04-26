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

def estimate_rank_dynamic(difficulty, month):
    """Estimate ranking improvement more realistically."""
    # Start worse for higher difficulty
    if difficulty < 30:
        current_rank = 40
    elif difficulty < 60:
        current_rank = 60
    else:
        current_rank = 80

    for _ in range(month):
        if current_rank > 50:
            rank_improvement = 8
        elif current_rank > 20:
            rank_improvement = 4
        elif current_rank > 10:
            rank_improvement = 2
        else:
            rank_improvement = 1

        current_rank = max(1, current_rank - rank_improvement)

    return current_rank

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
            est_rank = estimate_rank_dynamic(difficulty, month)
            ctr = get_ctr(est_rank)
            est_traffic = volume * ctr
            projections.append({
                "Assigned Page": page,
                "Month": month,
                "Estimated Traffic": est_traffic
            })
    return pd.DataFrame(projections)

def pivot_projection(projections, months):
    """Pivot the data: rows = page, columns = months + cumulative."""
    pivot = projections.pivot_table(
        index="Assigned Page",
        columns="Month",
        values="Estimated Traffic",
        aggfunc="sum",
        fill_value=0,
    )

    # Rename columns to "Month 1", "Month 2", etc.
    pivot.columns = [f"Month {col}" for col in pivot.columns]

    # Add a Cumulative Total column
    pivot["Cumulative Total"] = pivot.sum(axis=1)

    return pivot.reset_index()

# --- Streamlit Interface ---

st.title("📈 Keyword Traffic Projection App (Smarter Ranking Model)")

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
