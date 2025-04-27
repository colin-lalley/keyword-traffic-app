import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt

# --- Detailed CTR Curve Function ---
def get_ctr_dynamic(rank):
    if rank == 1:
        return 0.285
    elif rank == 2:
        return 0.157
    elif rank == 3:
        return 0.11
    elif rank == 4:
        return 0.08
    elif rank == 5:
        return 0.063
    elif rank == 6:
        return 0.047
    elif rank == 7:
        return 0.038
    elif rank == 8:
        return 0.031
    elif rank == 9:
        return 0.026
    elif rank == 10:
        return 0.024
    elif 11 <= rank <= 20:
        return 0.02
    elif 21 <= rank <= 30:
        return 0.01
    elif 31 <= rank <= 50:
        return 0.005
    else:
        return 0.0025

# --- Max Rank Based on Difficulty ---
def determine_max_rank(difficulty):
    if difficulty <= 20:
        return 3
    elif difficulty <= 40:
        return 5
    elif difficulty <= 60:
        return 10
    elif difficulty <= 80:
        return 20
    else:
        return 30

# --- Intent Scoring ---
def map_intent_score(intent):
    priority = {
        "Transactional": 100,
        "Commercial": 80,
        "Informational": 50,
        "Navigational": 20
    }

    if pd.isna(intent) or not intent.strip():
        return None

    intents = [i.strip() for i in intent.split(",")]

    best_score = 0
    for i in intents:
        score = priority.get(i, 0)
        if score > best_score:
            best_score = score

    return best_score if best_score > 0 else None

# --- Estimate Rank with Cluster Boost ---
def estimate_rank_with_cluster(difficulty, months=6, mode="Average", is_cluster=False):
    if difficulty < 20:
        current_rank = 30
    elif difficulty < 40:
        current_rank = 40
    elif difficulty < 60:
        current_rank = 60
    else:
        current_rank = 80

    max_rank = determine_max_rank(difficulty)
    rank_progression = []

    if mode == "Conservative":
        fast_improvement = 4
        medium_improvement = 2
        slow_improvement = 1
        very_slow_improvement = 1
    elif mode == "Aggressive":
        fast_improvement = 12
        medium_improvement = 6
        slow_improvement = 3
        very_slow_improvement = 2
    else:
        fast_improvement = 8
        medium_improvement = 4
        slow_improvement = 2
        very_slow_improvement = 1

    if is_cluster:
        fast_improvement += 1
        medium_improvement += 1
        slow_improvement += 1
        very_slow_improvement += 1

    for month in range(1, months + 1):
        if current_rank > 50:
            rank_improvement = fast_improvement
        elif current_rank > 20:
            rank_improvement = medium_improvement
        elif current_rank > 10:
            rank_improvement = slow_improvement
        else:
            rank_improvement = very_slow_improvement

        current_rank = max(1, current_rank - rank_improvement)
        current_rank = max(current_rank, max_rank)

        rank_progression.append(current_rank)

    return rank_progression

# --- Project Traffic ---
def project_traffic(df, months=6, mode="Average"):
    projections = []

    # Count unique pages per Cluster Group
    cluster_page_counts = df.groupby('Cluster Group')['Assigned Page'].nunique().to_dict()

    for idx, row in df.iterrows():
        page = row['Assigned Page']
        volume = row['Monthly Search Volume']
        difficulty = row['Difficulty']
        intent = row['Intent']
        cluster = row['Cluster Group']

        is_cluster = cluster and cluster_page_counts.get(cluster, 0) >= 3

        ranks = estimate_rank_with_cluster(difficulty, months, mode=mode, is_cluster=is_cluster)

        prev_traffic = None
        plateau_hit = False
        max_rank = determine_max_rank(difficulty)

        for month_idx, est_rank in enumerate(ranks, start=1):
            ctr = get_ctr_dynamic(est_rank)
            est_traffic = round(volume * ctr, 1)

            if plateau_hit:
                est_traffic = prev_traffic
            else:
                prev_traffic = est_traffic

            if est_rank == max_rank:
                plateau_hit = True

            projections.append({
                "Assigned Page": page,
                "Month": month_idx,
                "Estimated Traffic": est_traffic,
                "Difficulty": difficulty,
                "Intent": intent,
                "Cluster Group": cluster
            })

    return pd.DataFrame(projections)

# --- Pivot Output + Scoring ---
def pivot_projection(projections, months):
    pivot = projections.pivot_table(
        index="Assigned Page",
        columns="Month",
        values="Estimated Traffic",
        aggfunc="sum",
        fill_value=0,
    )

    pivot.columns = [f"Month {col}" for col in pivot.columns]
    pivot["Cumulative Total"] = pivot.sum(axis=1)

    avg_difficulty = projections.groupby("Assigned Page")["Difficulty"].mean()
    avg_intent_score = projections.groupby("Assigned Page")["Intent"].apply(
        lambda intents: sum([x for x in map(map_intent_score, intents) if x is not None]) / max(len([x for x in map(map_intent_score, intents) if x is not None]), 1)
    )

    pivot = pivot.merge(avg_difficulty, left_on="Assigned Page", right_on="Assigned Page")
    pivot = pivot.merge(avg_intent_score.rename("Avg Intent Score"), left_on="Assigned Page", right_on="Assigned Page")

    pivot["Traffic Score"] = (pivot["Cumulative Total"] / pivot["Cumulative Total"].max()) * 100
    pivot["Ease Score"] = (100 - pivot["Difficulty"])
    pivot["Intent Score"] = pivot["Avg Intent Score"]

    pivot["Final Page Score"] = (
        (pivot["Traffic Score"] * 0.5) +
        (pivot["Ease Score"] * 0.25) +
        (pivot["Intent Score"] * 0.25)
    )

    pivot = pivot.round(1)

    month_cols = [f"Month {i}" for i in range(1, months + 1)]
    keep_cols = ["Assigned Page"] + month_cols + ["Cumulative Total", "Final Page Score"]

    pivot = pivot.reset_index().loc[:, keep_cols]

    return pivot

# --- Streamlit App ---
st.title("📈 Keyword Traffic Projection App (Cluster Opportunity Edition)")

uploaded_file = st.file_uploader("Upload your keyword CSV", type=["csv"])

if uploaded_file:
    df = pd.read_csv(uploaded_file)
    df.columns = df.columns.str.strip()

    st.success("✅ File uploaded successfully — now select mode and months below.")
    st.subheader("Your Uploaded Data")
    st.dataframe(df)

    if df['Intent'].isna().sum() > 0 or (df['Intent'].str.strip() == "").sum() > 0:
        st.warning("⚠️ Some keywords have missing Intent. These will not receive an Intent Score boost.")

    mode = st.selectbox(
        "Select Improvement Mode:",
        options=["Conservative", "Average", "Aggressive"],
        index=1
    )

    months = st.selectbox(
        "Select Projection Duration (Months):",
        options=[3, 6, 12],
        index=1
    )

    projections = project_traffic(df, months, mode=mode)
    pivoted = pivot_projection(projections, months)

    filter_option = st.radio(
        "Filter Pages By:",
        options=["Show All Pages", "Show Pages with Final Page Score >40", "Show Top 10 Pages"]
    )

    if filter_option == "Show Pages with Final Page Score >40":
        pivoted = pivoted[pivoted["Final Page Score"] > 40]
    elif filter_option == "Show Top 10 Pages":
        pivoted = pivoted.head(10)

    st.subheader("📋 Executive Summary")
    avg_score = pivoted["Final Page Score"].mean().round(1) if not pivoted.empty else 0
    high_priority_count = (pivoted["Final Page Score"] >= 80).sum()
    st.markdown(f"You have **{high_priority_count} high-priority pages** scoring above 80.")
    st.markdown(f"The average Final Page Score across the filtered pages is **{avg_score}**.")

    st.subheader("📊 Projected Traffic by Page (with Heatmap)")
    styled_table = pivoted.style.background_gradient(
        cmap="YlGnBu",
        subset=[col for col in pivoted.columns if col.startswith("Month")] + ["Cumulative Total", "Final Page Score"]
    )
    st.dataframe(styled_table, use_container_width=True, hide_index=True)

    csv = pivoted.to_csv(index=False).encode('utf-8')
    st.download_button(
        label="Download Projected Traffic CSV",
        data=csv,
        file_name="projected_traffic_with_scores.csv",
        mime="text/csv"
    )

    st.subheader("📈 Traffic Growth Over Time")
    fig, ax = plt.subplots(figsize=(10, 6))
    month_cols = [col for col in pivoted.columns if col.startswith("Month")]

    for idx, row in pivoted.iterrows():
        ax.plot(month_cols, row[month_cols], label=row['Assigned Page'])

    ax.set_xlabel("Month")
    ax.set_ylabel("Estimated Traffic")
    ax.set_title("Traffic Growth by Page")
    ax.legend(bbox_to_anchor=(1.05, 1), loc='upper left', fontsize="small")
    st.pyplot(fig)

    # --- Top Pages Table (Opportunity View) ---
    def label_opportunity(row):
        if row['Final Page Score'] >= 80 and row['Difficulty'] < 50:
            return "Easy Win"
        elif row['Final Page Score'] >= 70:
            return "Moderate Win"
        else:
            return "Harder Bet"

    top_pages = pivoted.head(10).copy()
    top_pages["Opportunity Label"] = top_pages.apply(label_opportunity, axis=1)

    st.subheader("🏆 Top Opportunity Pages")
    st.dataframe(top_pages[["Assigned Page", "Opportunity Label"]], use_container_width=True, hide_index=True)

    # --- Cluster Opportunity Rankings ---
    st.subheader("🏢 Cluster Opportunity Rankings")
    cluster_summary = projections.groupby("Cluster Group").agg(
        Avg_Final_Page_Score=("Assigned Page", lambda x: pivoted[pivoted["Assigned Page"].isin(x)].mean()["Final Page Score"]),
        Page_Count=("Assigned Page", lambda x: x.nunique())
    ).reset_index()

    cluster_summary = cluster_summary.dropna(subset=["Cluster Group"])

    def cluster_label(row):
        if row['Avg_Final_Page_Score'] >= 80:
            return "Huge Opportunity"
        elif row['Avg_Final_Page_Score'] >= 70:
            return "Strong Opportunity"
        elif row['Avg_Final_Page_Score'] >= 60:
            return "Moderate Opportunity"
        else:
            return "Lower Priority"

    cluster_summary["Opportunity Label"] = cluster_summary.apply(cluster_label, axis=1)

    st.dataframe(
        cluster_summary[["Cluster Group", "Page_Count", "Avg_Final_Page_Score", "Opportunity Label"]],
        use_container_width=True,
        hide_index=True
    )
