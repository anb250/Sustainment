
import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt

st.set_page_config(page_title="Aviation Fuel LCA Dashboard", layout="wide")

DEFAULT_DATA = pd.DataFrame({
    "Fuel pathway": [
        "Kerosene",
        "Ethanol",
        "Biogas",
        "Biomethane (membrane)",
        "Biomethane (PSA)"
    ],
    "Production process": [
        "Conventional aviation kerosene baseline",
        "Sugar-beet fermentation",
        "Anaerobic digestion of manure",
        "Membrane CO2 separation",
        "Pressure swing adsorption upgrading"
    ],
    "Energy content value": [43.0, 28.1, 22.7, 34.97, 34.97],
    "Energy unit": ["MJ/kg", "MJ/kg", "MJ/m3", "MJ/m3", "MJ/m3"]
})

DEFAULT_SCENARIOS = pd.DataFrame({
    "Distance class": ["Very short-haul", "Short-haul", "Medium-haul"],
    "Kerosene": [1, 1, 1],
    "Ethanol": [1, 1, 1],
    "Biogas": [1, 1, 1],
    "Biomethane (membrane)": [1, 1, 1],
    "Biomethane (PSA)": [1, 1, 1],
})

DEFAULT_RESULTS = pd.DataFrame({
    "Scenario": [
        "Biomethane (PSA) very short-haul",
        "Biomethane (PSA) medium-haul",
        "Biomethane (PSA) short-haul",
        "Biogas very short-haul",
        "Biogas short-haul",
        "Biogas medium-haul",
        "Ethanol very short-haul",
        "Ethanol short-haul",
        "Ethanol medium-haul",
        "Biomethane (membrane) short-haul",
        "Biomethane (membrane) very short-haul",
        "Biomethane (membrane) medium-haul",
        "Kerosene medium-haul",
        "Kerosene short-haul",
        "Kerosene very short-haul",
    ],
    "Fuel pathway": [
        "Biomethane (PSA)", "Biomethane (PSA)", "Biomethane (PSA)",
        "Biogas", "Biogas", "Biogas",
        "Ethanol", "Ethanol", "Ethanol",
        "Biomethane (membrane)", "Biomethane (membrane)", "Biomethane (membrane)",
        "Kerosene", "Kerosene", "Kerosene"
    ],
    "Distance class": [
        "Very short-haul", "Medium-haul", "Short-haul",
        "Very short-haul", "Short-haul", "Medium-haul",
        "Very short-haul", "Short-haul", "Medium-haul",
        "Short-haul", "Very short-haul", "Medium-haul",
        "Medium-haul", "Short-haul", "Very short-haul"
    ],
    # Example values based on your extracted process-contribution range.
    "GWP100 kg CO2-eq/pkm": [
        0.1211564, 0.083628116, 0.097215457,
        0.12123401, 0.0975, 0.0842,
        0.1208, 0.0969, 0.0839,
        0.0971, 0.1210, 0.0837,
        0.0845, 0.0978, 0.1213
    ]
})

st.title("Aviation Fuel LCA Dashboard")
st.caption("Streamlit dashboard for comparing alternative aviation fuel pathways within a passenger aircraft lifecycle assessment model.")

with st.sidebar:
    st.header("Controls")
    show_notes = st.checkbox("Show methodology notes", value=True)
    distance_filter = st.multiselect(
        "Distance class",
        options=sorted(DEFAULT_RESULTS["Distance class"].unique()),
        default=sorted(DEFAULT_RESULTS["Distance class"].unique())
    )
    fuel_filter = st.multiselect(
        "Fuel pathway",
        options=DEFAULT_DATA["Fuel pathway"].tolist(),
        default=DEFAULT_DATA["Fuel pathway"].tolist()
    )

tab1, tab2, tab3, tab4 = st.tabs([
    "Overview",
    "Fuel pathways",
    "Scenario results",
    "Scenario matrix"
])

with tab1:
    st.subheader("Project overview")
    st.markdown(
        """
        This dashboard summarises a lifecycle assessment model in which alternative fuel pathways
        are linked to modified passenger aircraft transport datasets. The aim is to compare
        aviation kerosene, ethanol, biogas, and two biomethane upgrading pathways under a
        consistent passenger-kilometre functional unit.
        """
    )

    c1, c2, c3 = st.columns(3)
    c1.metric("Fuel pathways", len(DEFAULT_DATA))
    c2.metric("Distance classes", DEFAULT_SCENARIOS.shape[0])
    c3.metric("Scenarios compared", len(DEFAULT_RESULTS))

    st.subheader("Fuel pathway summary")
    st.dataframe(DEFAULT_DATA, use_container_width=True, hide_index=True)

    if show_notes:
        st.info(
            "Airport infrastructure was removed from the copied aircraft datasets so the comparison "
            "focuses on operational fuel effects and upstream fuel production pathways."
        )

with tab2:
    st.subheader("Fuel pathway properties")
    edited_data = st.data_editor(DEFAULT_DATA, use_container_width=True, num_rows="dynamic", hide_index=True)

    fig, ax = plt.subplots(figsize=(8, 4.8))
    bars = ax.bar(edited_data["Fuel pathway"], edited_data["Energy content value"])
    ax.set_ylabel("Energy content")
    ax.set_xlabel("Fuel pathway")
    ax.set_title("Energy content by fuel pathway")
    ax.tick_params(axis="x", rotation=30)
    for bar, value, unit in zip(bars, edited_data["Energy content value"], edited_data["Energy unit"]):
        ax.text(bar.get_x() + bar.get_width()/2, bar.get_height(), f"{value:.2f}\n{unit}",
                ha="center", va="bottom", fontsize=8)
    st.pyplot(fig, use_container_width=True)

with tab3:
    st.subheader("Scenario results")
    results = DEFAULT_RESULTS.copy()
    results = results[
        results["Distance class"].isin(distance_filter) &
        results["Fuel pathway"].isin(fuel_filter)
    ]

    st.dataframe(results, use_container_width=True, hide_index=True)

    if not results.empty:
        pivot = results.pivot_table(
            index="Distance class",
            columns="Fuel pathway",
            values="GWP100 kg CO2-eq/pkm",
            aggfunc="mean"
        ).reindex(index=["Very short-haul", "Short-haul", "Medium-haul"])

        st.markdown("**Grouped comparison by distance class**")
        st.bar_chart(pivot, height=380, use_container_width=True)

        st.markdown("**Scenario ranking**")
        ranked = results.sort_values("GWP100 kg CO2-eq/pkm", ascending=True).reset_index(drop=True)
        st.dataframe(ranked, use_container_width=True, hide_index=True)

        st.markdown("**Interpretation**")
        best = ranked.iloc[0]
        worst = ranked.iloc[-1]
        st.write(
            f"Within the current inputs, the lowest reported scenario is **{best['Scenario']}** "
            f"at **{best['GWP100 kg CO2-eq/pkm']:.4f} kg CO2-eq/pkm**, while the highest reported "
            f"scenario is **{worst['Scenario']}** at **{worst['GWP100 kg CO2-eq/pkm']:.4f} kg CO2-eq/pkm**."
        )
    else:
        st.warning("No scenarios match the current filters.")

with tab4:
    st.subheader("Scenario matrix")
    st.dataframe(DEFAULT_SCENARIOS, use_container_width=True, hide_index=True)

    st.markdown("### System boundary")
    st.markdown(
        """
        **Fuel production pathway**  
        ↓  
        **Fuel processing / upgrading**  
        ↓  
        **Aircraft fuel input (modified dataset)**  
        ↓  
        **Aircraft operational emissions**  
        ↓  
        **Lifecycle impact assessment per passenger-km**
        """
    )

    if show_notes:
        st.markdown("### Methodological note")
        st.write(
            "These results should be interpreted as relative comparisons within an attributional "
            "LCA framework. They represent average supply-chain conditions rather than marginal "
            "future market responses."
        )
