import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt

# --- Updated Dynamic CTR Function ---
def get_ctr_dynamic(rank):
    """Get a better CTR estimate based on broader rank ranges."""
    if rank == 1:
        return 0.31
    elif rank == 2:
        return 0.24
    elif rank == 3:
        return 0.18
    elif rank == 4:
        return 0.13
    elif rank == 5:
        return 0.10
    elif 6 <= rank <= 10:
        return 0.06
    elif 11 <= rank <= 20:
        return 0.03
    elif 21 <= rank <= 30:
        return 0.02
    elif 31 <= rank <= 50:
        return 0.01
    else:
        return 0.005  # Tiny CTR if rank is worse than 50

# --- Updated Rank Estimation ---
def estimate_rank_dynamic(difficulty, month):
    """Estimate ranking improvement more realistically."""
    if difficulty < 20:
        current_rank = 30
    elif difficulty < 40:
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

# --- Project Traffic ---
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
            ctr = get_ctr_dynamic(est_rank)
            est_traffic = volume * ctr
            projections.append({
                "Assigned Page": page,
                "Month": month,
                "Estimated Traffic": est_traffic
            })
    return pd.DataFrame(projections)

# --- Pivot Output ---
def pivot_projection(projections, months):
    """Pivot the data: rows = page, columns = months + cumulative."""
    pivot = projections.pivot_table(
        index="Assigned Page",
        columns="Month",
        values="Estimated Traffic",
        aggfunc="sum",
        fill_value=0,
    )

    pivot.columns = [f"Month {col}" for col in pivot.columns]
    pivot["Cumulative Total"] = pivot.sum(axis=1)

    return pivot.reset_index()

# --- Streamlit App ---
st.title("📈 Keyword Traffic Projection App (Dynamic CTR + Charts)")

uploaded_file = st.file_uploader("Upload your keyword CSV", type=["csv"])

if uploaded_file:
    df = pd.read_csv(uploaded_file)
    df.columns = df.columns.str.strip()

    st.subheader("Your Uploaded Data")
    st.dataframe(df)

    months = st.slider("Project for how many months?", 1, 12, 6)

    projections = project_traffic(df, months)
    pivoted = pivot_projection(projections, months)

    # --- Pretty Styled Table ---
    st.subheader("📊 Projected Traffic by Page (with Heatmap)")
    styled_table = pivoted.style.background_gradient(cmap="YlGnBu", subset=[f"Month {i}" for i in range(1, months + 1)] + ["Cumulative Total"])
    st.dataframe(styled_table, use_container_width=True)

    # --- Download Button ---
    csv = pivoted.to_csv(index=False).encode('utf-8')
    st.download_button(
        label="Download Projected Traffic CSV",
        data=csv,
        file_name="projected_traffic_by_page.csv",
        mime="text/csv"
    )

    # --- Line Chart ---
    st.subheader("📈 Traffic Growth Over Time")
    fig, ax = plt.subplots(figsize=(10, 6))
    month_cols = [f"Month {i}" for i in range(1, months + 1)]

    for idx, row in pivoted.iterrows():
        ax.plot(month_cols, row[month_cols], label=row['Assigned Page'])

    ax.set_xlabel("Month")
    ax.set_ylabel("Estimated Traffic")
    ax.set_title("Traffic Growth by Page")
    ax.legend(bbox_to_anchor=(1.05, 1), loc='upper left', fontsize="small")
    st.pyplot(fig)

    # --- Top Pages ---
    st.subheader("🏆 Top 5 Pages by Total Projected Traffic")
    top_pages = pivoted.sort_values(by="Cumulative Total", ascending=False).head(5)
    st.dataframe(top_pages, use_container_width=True)
