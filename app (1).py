
import io
import re
from pathlib import Path

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
from pypdf import PdfReader

st.set_page_config(
    page_title="Aviation Fuel LCA Dashboard",
    page_icon="✈️",
    layout="wide",
    initial_sidebar_state="expanded",
)

APP_DIR = Path(__file__).resolve().parent

DEFAULT_FILES = {
    "damage": "Compare All Impact Assessment Damage Assessment.pdf",
    "characterization": "Compare All Impact Assessment Characterization.pdf",
    "process_damage": "Process Contribution Damage Assessment.pdf",
    "process_characterization": "Process Contribution Characterization.pdf",
    "process_inventory": "Process Contribution.pdf",
    "single_damage": "Damage Assessment.pdf",
    "single_characterization": "Characterization.pdf",
}

DISTANCE_ORDER = ["very short haul", "short haul", "medium haul"]
FUEL_ORDER = ["KEROSENE1", "ETHANOL", "BIOGAS", "BIOMETHANE", "BIOMETHANE2"]

def clean_text(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()

@st.cache_data(show_spinner=False)
def extract_pdf_text(path: Path) -> str:
    reader = PdfReader(str(path))
    pages = []
    for page in reader.pages:
        pages.append(page.extract_text() or "")
    return "\n".join(pages)

def find_existing_files() -> dict:
    found = {}
    for key, name in DEFAULT_FILES.items():
        candidate = APP_DIR / name
        if candidate.exists():
            found[key] = candidate
    return found

def parse_products(text: str) -> pd.DataFrame:
    pattern = re.compile(
        r"Product\s+\d+:\s+1 personkm\s+(.+?)\s+Transport,\s+passenger,\s+aircraft,\s+(.+?)\s+\{GLO\}",
        re.IGNORECASE
    )
    rows = []
    for m in pattern.finditer(text):
        fuel = clean_text(m.group(1)).replace(",", "")
        distance = clean_text(m.group(2))
        rows.append({"fuel": fuel.upper(), "distance": distance.lower()})
    df = pd.DataFrame(rows).drop_duplicates()
    return df

def parse_compare_values(text: str) -> pd.DataFrame:
    products = parse_products(text)
    value_match = re.search(r"GWP100\s+kg CO2-eq\s+([0-9E\.\-\s]+)", text)
    if not value_match:
        return pd.DataFrame()
    nums = [float(x) for x in re.findall(r"-?\d+\.\d+(?:E[+-]?\d+)?|-?\d+", value_match.group(1))]
    n = min(len(products), len(nums))
    if n == 0:
        return pd.DataFrame()
    out = products.iloc[:n].copy()
    out["gwp100_kgco2eq_pkm"] = nums[:n]
    return out

def parse_characterization_categories(text: str) -> pd.DataFrame:
    products = parse_products(text)
    rows = []
    for category in ["GWP100 - fossil", "GWP100 - biogenic", "GWP100 - land transformation"]:
        m = re.search(re.escape(category) + r"\s+kg CO2-eq\s+([0-9E\.\-\s]+)", text)
        if not m:
            continue
        nums = [float(x) for x in re.findall(r"-?\d+\.\d+(?:E[+-]?\d+)?|-?\d+", m.group(1))]
        n = min(len(products), len(nums))
        temp = products.iloc[:n].copy()
        temp["category"] = category
        temp["value"] = nums[:n]
        rows.append(temp)
    if not rows:
        return pd.DataFrame()
    return pd.concat(rows, ignore_index=True)

def make_pretty_labels(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return df
    mapping = {
        "KEROSENE1": "Kerosene",
        "ETHANOL": "Ethanol",
        "BIOGAS": "Biogas",
        "BIOMETHANE": "Biomethane (membrane)",
        "BIOMETHANE2": "Biomethane (PSA)",
    }
    dmap = {
        "very short haul": "Very short-haul",
        "short haul": "Short-haul",
        "medium haul": "Medium-haul",
    }
    out = df.copy()
    out["Fuel pathway"] = out["fuel"].map(mapping).fillna(out["fuel"])
    out["Distance class"] = out["distance"].map(dmap).fillna(out["distance"])
    return out

def default_fuel_properties() -> pd.DataFrame:
    return pd.DataFrame({
        "Fuel pathway": ["Kerosene", "Ethanol", "Biogas", "Biomethane (membrane)", "Biomethane (PSA)"],
        "Production process": [
            "Baseline aviation kerosene",
            "Sugar-beet fermentation",
            "Anaerobic digestion of manure",
            "Membrane upgrading of biogas",
            "Pressure swing adsorption upgrading of biogas",
        ],
        "Energy content": [43.0, 28.1, 22.73, 34.97, 34.97],
        "Unit": ["MJ/kg", "MJ/kg", "MJ/m³", "MJ/m³", "MJ/m³"],
    })

files = find_existing_files()
damage_df = pd.DataFrame()
char_df = pd.DataFrame()

if "damage" in files:
    damage_df = parse_compare_values(extract_pdf_text(files["damage"]))
    damage_df = make_pretty_labels(damage_df)

if "characterization" in files:
    char_df = parse_characterization_categories(extract_pdf_text(files["characterization"]))
    char_df = make_pretty_labels(char_df)

st.markdown(
    """
    <style>
    .block-container {padding-top: 1.2rem; padding-bottom: 1rem; max-width: 1450px;}
    .metric-card {background: #f7f9fc; padding: 0.8rem 1rem; border-radius: 0.8rem; border: 1px solid #e8edf5;}
    h1, h2, h3 {letter-spacing: -0.02em;}
    </style>
    """,
    unsafe_allow_html=True,
)

st.title("Aviation Fuel Lifecycle Assessment Dashboard")
st.caption("Professional analysis dashboard for passenger aircraft biofuel comparisons using SimaPro exports and ecoinvent-based transport inventories.")

with st.sidebar:
    st.header("Study settings")
    st.markdown("**Functional unit**  \n1 passenger-km")
    st.markdown("**Impact method**  \nIPCC 2021 GWP100")
    st.markdown("**System model**  \necoinvent allocation, cut-off")
    st.divider()
    available_distances = sorted(damage_df["Distance class"].unique().tolist()) if not damage_df.empty else ["Very short-haul", "Short-haul", "Medium-haul"]
    available_fuels = default_fuel_properties()["Fuel pathway"].tolist()
    selected_distances = st.multiselect("Distance class", available_distances, default=available_distances)
    selected_fuels = st.multiselect("Fuel pathway", available_fuels, default=available_fuels)
    st.divider()
    st.markdown("**Detected export files**")
    if files:
        for k, v in files.items():
            st.write(f"• {v.name}")
    else:
        st.warning("No SimaPro PDF exports detected in the app folder.")

overview, boundary, results, contributions, comparison = st.tabs(
    ["Overview", "System Boundary", "Impact Results", "Characterization", "Fuel Comparison"]
)

with overview:
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Fuel pathways", "5")
    c2.metric("Distance classes", "3")
    c3.metric("Scenarios", str(len(damage_df)) if not damage_df.empty else "15")
    c4.metric("Method", "IPCC 2021 GWP100")
    st.markdown("### Study design")
    st.write(
        "This dashboard summarises a cradle-to-grave aviation fuel lifecycle assessment in which "
        "ethanol, biogas, and two biomethane pathways are substituted into modified passenger aircraft "
        "transport datasets. Airport infrastructure was removed from the copied aircraft processes so "
        "the comparison isolates operational fuel effects and upstream fuel production burdens."
    )
    st.markdown("### Fuel pathway properties")
    st.dataframe(default_fuel_properties(), use_container_width=True, hide_index=True)

with boundary:
    st.markdown("### Journal-style LCA system boundary")
    img_file = APP_DIR / "lca_system_boundary_journal.png"
    if img_file.exists():
        st.image(str(img_file), use_container_width=True)
    else:
        st.error("System boundary image not found. Upload lca_system_boundary_journal.png into the repository.")
    st.markdown(
        """
        The boundary includes feedstock generation, transport, conversion or upgrading, distribution,
        aircraft operation, and climate impact assessment per passenger-km. It also shows the biogenic
        carbon loop and upstream energy inputs used in biofuel processing.
        """
    )

with results:
    st.markdown("### GWP100 results from SimaPro exports")
    if damage_df.empty:
        st.warning("No damage assessment data could be parsed automatically.")
    else:
        filtered = damage_df[
            damage_df["Distance class"].isin(selected_distances) &
            damage_df["Fuel pathway"].isin(selected_fuels)
        ].copy()
        st.dataframe(
            filtered[["Fuel pathway", "Distance class", "gwp100_kgco2eq_pkm"]]
            .rename(columns={"gwp100_kgco2eq_pkm": "GWP100 (kg CO₂-eq/pkm)"}),
            use_container_width=True,
            hide_index=True
        )
        fig = px.bar(
            filtered,
            x="Distance class",
            y="gwp100_kgco2eq_pkm",
            color="Fuel pathway",
            barmode="group",
            labels={"gwp100_kgco2eq_pkm": "kg CO₂-eq per passenger-km"},
        )
        fig.update_layout(height=520, legend_title_text="")
        st.plotly_chart(fig, use_container_width=True)

with contributions:
    st.markdown("### Characterization breakdown")
    if char_df.empty:
        st.warning("No characterization category data could be parsed automatically.")
    else:
        filtered = char_df[
            char_df["Distance class"].isin(selected_distances) &
            char_df["Fuel pathway"].isin(selected_fuels)
        ].copy()
        st.dataframe(
            filtered.rename(columns={"value": "Value (kg CO₂-eq)"}),
            use_container_width=True,
            hide_index=True
        )
        scenario_pick = st.selectbox(
            "Select distance class for category comparison",
            selected_distances if selected_distances else sorted(filtered["Distance class"].unique())
        )
        pivot = (
            filtered[filtered["Distance class"] == scenario_pick]
            .pivot(index="Fuel pathway", columns="category", values="value")
            .reset_index()
        )
        if not pivot.empty:
            fig = go.Figure()
            for col in [c for c in pivot.columns if c != "Fuel pathway"]:
                fig.add_bar(name=col, x=pivot["Fuel pathway"], y=pivot[col])
            fig.update_layout(
                barmode="stack",
                height=520,
                xaxis_title="Fuel pathway",
                yaxis_title="kg CO₂-eq per passenger-km",
                legend_title_text=""
            )
            st.plotly_chart(fig, use_container_width=True)

with comparison:
    st.markdown("### Comparative fuel ranking")
    if damage_df.empty:
        st.warning("No parsed comparison data available.")
    else:
        filtered = damage_df[
            damage_df["Distance class"].isin(selected_distances) &
            damage_df["Fuel pathway"].isin(selected_fuels)
        ].copy()
        rank = (
            filtered.groupby("Fuel pathway", as_index=False)["gwp100_kgco2eq_pkm"]
            .mean()
            .sort_values("gwp100_kgco2eq_pkm")
        )
        fig = px.bar(
            rank,
            x="Fuel pathway",
            y="gwp100_kgco2eq_pkm",
            color="Fuel pathway",
            labels={"gwp100_kgco2eq_pkm": "Average GWP100 (kg CO₂-eq/pkm)"}
        )
        fig.update_layout(height=500, showlegend=False)
        st.plotly_chart(fig, use_container_width=True)
        best = rank.iloc[0]
        worst = rank.iloc[-1]
        st.info(
            f"Lowest average reported scenario in the current parsed exports: {best['Fuel pathway']} "
            f"at {best['gwp100_kgco2eq_pkm']:.4f} kg CO₂-eq/pkm. Highest average: {worst['Fuel pathway']} "
            f"at {worst['gwp100_kgco2eq_pkm']:.4f} kg CO₂-eq/pkm."
        )
