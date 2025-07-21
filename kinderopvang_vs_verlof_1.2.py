import streamlit as st
import pandas as pd
 
# ===============================
# Configuratie
# ===============================
st.set_page_config(page_title="Ouderschapsverlof vs Kinderopvang", layout="wide")
st.markdown("## ⚖️ Financiële vergelijking: ouderschapsverlof vs. kinderopvang")
 
# ===============================
# Sidebar instellingen
# ===============================
fiscal_pct = st.sidebar.slider(
    "Fiscale factor (%)", 0, 100, 50,
    help="Gemiddelde belastingdruk (standaard 49.5%)"
) / 100
 
with st.sidebar.expander("ℹ️ Uitleg en Assumpties", expanded=True):
    st.write("""
    - Berekening per maand.
    - Inclusief vakantiegeld en vaste vergoedingen.
    - Ouderschapsverlof: standaard 70% vergoeding voor 9 weken.
    - Kinderopvangtoeslag: toeslag op basis van inkomen, ga voor meer informatie naar www.rijksoverheid.nl .
    """)
 
# ===============================
# Toeslagtabel inladen
# ===============================
def load_toeslag_data(path, sheet):
    df = pd.read_excel(path, sheet_name=sheet)
    df.columns = [c.strip().lower().replace(' ', '_') for c in df.columns]
    def find_col(keywords):
        return next((col for col in df.columns if all(k in col for k in keywords)), None)
    pct_col = find_col(['vergoedingspercentage','eerste'])
    frm_col = find_col(['toetsingsinkomen','vanaf'])
    tot_col = find_col(['tot','met'])
    df = df.rename(columns={pct_col:'pct', frm_col:'vanaf', tot_col:'tot'})
    return df.sort_values('vanaf').reset_index(drop=True)
 
toeslag_df = load_toeslag_data(
    "Geboorte en ouderschapsverlof (1).xlsx",
    "Kinderopvangtoeslagtabel 2026"
)
 
# ===============================
# Berekeningsfuncties
# ===============================
def kot_pct(inkomen):
    for _, r in toeslag_df.iterrows():
        grens, vanaf, pct = r['tot'], r['vanaf'], float(r['pct'])
        if isinstance(grens, str) and grens.strip().lower() == 'en hoger':
            if inkomen >= vanaf:
                return pct
        elif vanaf <= inkomen <= float(grens):
            return pct
    return 0.0
 
def nettoverlies(sv, verlofdagen, doorb_pct):
    dagloon = sv / 261
    betaald = dagloon * doorb_pct
    verlies_dag = dagloon - betaald
    bruto_mnd = verlies_dag * verlofdagen * 4
    netto_mnd = bruto_mnd * fiscal_pct
    return bruto_mnd, netto_mnd
 
def opvangkosten(uurtarief, cap, dpw, upd, wpj, pct):
    uren_per_maand = dpw * upd * wpj / 12
    bruto = uren_per_maand * uurtarief
    toeslag = uren_per_maand * cap * pct
    netto = bruto - toeslag
    return bruto, toeslag, netto
 
# ===============================
# Scenario verwerking met gerichte kolommen
# ===============================
def process_scenario(prefix):
    col1, col2, col3 = st.columns([2, 2, 1])  # kolomverdeling voor compacte inputs
    with col1:
        sv1 = st.number_input(f"{prefix} - SV-jaarloon Ouder 1", 0.0, 300000.0, 66000.0, step=500.0, key=prefix+"_sv1")
        vw1 = st.number_input(f"{prefix} - Verlofdagen/week Ouder 1", 0.0, 5.0, 1.0, step=1.0, key=prefix+"_vw1")
        db1 = st.slider(f"{prefix} - Procent betaald Ouder 1 (%)", 0, 100, 70, key=prefix+"_db1") / 100
        sv2 = st.number_input(f"{prefix} - SV-jaarloon Ouder 2", 0.0, 300000.0, 48000.0, step=500.0, key=prefix+"_sv2")
        vw2 = st.number_input(f"{prefix} - Verlofdagen/week Ouder 2", 0.0, 5.0, 1.0, step=1.0, key=prefix+"_vw2")
        db2 = st.slider(f"{prefix} - Procent betaald Ouder 2 (%)", 0, 100, 70, key=prefix+"_db2") / 100
    with col2:
        urt = st.number_input(f"{prefix} - Uurtarief opvang (€)", 0.0, 100.0, 11.76, step=0.1, key=prefix+"_urt")
        cap = st.number_input(f"{prefix} - Max. uurvergoeding (€)", 0.0, 100.0, 11.23, step=0.1, key=prefix+"_cap")
    with col3:
        dpw = st.number_input(f"{prefix} - Opvangdagen/week", 0, 7, 2, key=prefix+"_dpw")
        upd = st.number_input(f"{prefix} - Opvanguren/dag", 0.0, 24.0, 10.75, step=0.25, key=prefix+"_upd")
        wpj = st.selectbox(f"{prefix} - Opvangweken/jaar", [41, 52], index=1, key=prefix+"_wpj")
 
    tot_inc = sv1 + sv2
    b1, n1 = nettoverlies(sv1, vw1, db1)
    b2, n2 = nettoverlies(sv2, vw2, db2)
    jaarverlies = (b1 + b2) * 12
    adj_inkomen = max(0, tot_inc - jaarverlies)
    pct = kot_pct(adj_inkomen)
    opro, oto, ono = opvangkosten(urt, cap, dpw, upd, wpj, pct)
 
    return {
        'netto1': n1,
        'netto2': n2,
        'bruto_opv': opro,
        'toeslag': oto,
        'netto_opv': ono,
        'totaal': n1 + n2 + ono,
        'vw1': vw1,
        'vw2': vw2,
        'dpw': dpw,
        'adj_inkomen': adj_inkomen
    }
 
# ===============================
# Scenario input & berekening in tabs
# ===============================
tabs = st.tabs(["Scenario 1", "Scenario 2"])
with tabs[0]:
    with st.expander("Instellingen Scenario 1", expanded=True):
        data1 = process_scenario("S1")
with tabs[1]:
    with st.expander("Instellingen Scenario 2", expanded=True):
        data2 = process_scenario("S2")
 
# ===============================
# KPI Metrics per scenario
# ===============================
st.markdown("---")
# Scenario 1 metrics
st.markdown("#### Overzicht Scenario 1 (€/mnd)")
cols1 = st.columns(6)
cols1[0].metric("Inkomstenverlies ouder 1 (netto)", f"€{data1['netto1']:.0f}")
cols1[1].metric("Inkomstenverlies ouder 2 (netto)", f"€{data1['netto2']:.0f}")
cols1[2].metric("Bruto opvangkosten", f"€{data1['bruto_opv']:.0f}")
cols1[3].metric("Toeslag", f"€{data1['toeslag']:.0f}")
cols1[4].metric("Netto opvangkosten", f"€{data1['netto_opv']:.0f}")
cols1[5].metric("Totaal kosten", f"€{data1['totaal']:.0f}")
# Verlofdagen en opvangdagen
st.markdown(f"**Verlofdagen/week:** Ouder 1={data1['vw1']}, Ouder 2={data1['vw2']}  |  **Opvangdagen/week:** {data1['dpw']}")
 
st.markdown("---")
# Scenario 2 metrics
st.markdown("#### Overzicht Scenario 2 (€/mnd)")
cols2 = st.columns(6)
cols2[0].metric("Inkomstenverlies ouder 1 (netto)", f"€{data2['netto1']:.0f}")
cols2[1].metric("Inkomstenverlies ouder 2 (netto)", f"€{data2['netto2']:.0f}")
cols2[2].metric("Bruto opvangkosten", f"€{data2['bruto_opv']:.0f}")
cols2[3].metric("Toeslag", f"€{data2['toeslag']:.0f}")
cols2[4].metric("Netto opvangkosten", f"€{data2['netto_opv']:.0f}")
cols2[5].metric("Totaal kosten", f"€{data2['totaal']:.0f}")
# Verlofdagen en opvangdagen
st.markdown(f"**Verlofdagen/week:** Ouder 1={data2['vw1']}, Ouder 2={data2['vw2']}  |  **Opvangdagen/week:** {data2['dpw']}")
 
# ===============================
# Toeslagtrede informatie in sidebar (gebaseerd op Scenario 1)
# ===============================
adj = data1['adj_inkomen']
df_trede = toeslag_df.copy()
df_trede['tot_num'] = df_trede['tot'].apply(lambda x: float('inf') if isinstance(x, str) and x.strip().lower()=='en hoger' else float(x))
mask = (df_trede['vanaf'] <= adj) & (adj <= df_trede['tot_num'])
if mask.any():
    idx = mask.idxmax()
    prev_row = df_trede.iloc[idx-1] if idx > 0 else None
    curr_row = df_trede.iloc[idx]
    next_row = df_trede.iloc[idx+1] if idx < len(df_trede)-1 else None
 
    with st.sidebar.expander("🗂️ Toeslagtrede info", expanded=False):
        if prev_row is not None:
            st.write(f"Vorige trede (< €{int(prev_row['vanaf']):,} - €{prev_row['tot']}): {prev_row['pct']*100:.1f}%")
        st.write(f"Huidige trede (inkomen €{int(adj):,}): tot €{curr_row['tot']} met {curr_row['pct']*100:.1f}%")
        if next_row is not None:
            st.write(f"Volgende trede (≥ €{int(next_row['vanaf']):,}): tot €{next_row['tot']} met {next_row['pct']*100:.1f}%")
else:
    with st.sidebar.expander("🗂️ Toeslagtrede info", expanded=False):
        st.write("Geen toeslagtrede gevonden voor dit inkomen.")
 
# ===============================
# Conclusie
# ===============================
diff = data2['totaal'] - data1['totaal']
if diff > 0:
    st.success(f"Scenario 1 is voordeliger met €{abs(diff):,.0f}")
elif diff < 0:
    st.info(f"Scenario 2 is voordeliger met €{abs(diff):,.0f}")
else:
    st.warning("Beide scenario’s zijn financieel gelijk.")
 
# ===============================
# Gedetailleerde KPI Tabel
# ===============================
df_kpi = pd.DataFrame({
    'Parameter': [
        'Inkomstenverlies ouder 1 netto/mnd',
        'Inkomstenverlies ouder 2 netto/mnd',
        'Opvangkosten bruto/mnd',
        'Toeslag',
        'Opvangkosten netto/mnd',
        'Totale kosten netto/mnd'
    ],
    'Scenario 1': [
        f"€{data1['netto1']:.0f}",
        f"€{data1['netto2']:.0f}",
        f"€{data1['bruto_opv']:.0f}",
        f"€{data1['toeslag']:.0f}",
        f"€{data1['netto_opv']:.0f}",
        f"€{data1['totaal']:.0f}"
    ],
    'Scenario 2': [
        f"€{data2['netto1']:.0f}",
        f"€{data2['netto2']:.0f}",
        f"€{data2['bruto_opv']:.0f}",
        f"€{data2['toeslag']:.0f}",
        f"€{data2['netto_opv']:.0f}",
        f"€{data2['totaal']:.0f}"
    ]
})
st.markdown("## Gedetailleerde KPI-tabel")
st.table(df_kpi)