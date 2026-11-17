import numpy as np
import pandas as pd
import streamlit as st

st.set_page_config(page_title="SwitchSole | 5-Jahres-Simulation", page_icon="👟", layout="wide")

st.markdown("""<style>
.block-container {padding-top: 1.8rem; max-width: 1450px;}
[data-testid="stMetric"] {background: #f2f5f2; padding: 16px; border-radius: 12px;}
[data-testid="stMetricLabel"] {color: #34443a;}
</style>""", unsafe_allow_html=True)

st.title("👟 SwitchSole | Triathlon Edition")
st.caption("Interaktive 5-Jahres-Marketingsimulation · 2027–2031 · Alle Geldbeträge in EUR")
st.info("Planungsmodell, keine Absatzprognose: Nachfrageparameter, Kosten und Marketingeffekte sind Annahmen. Die Produktpreise aus dem Konzept sind Startwerte.")

with st.sidebar:
    st.header("Marketing-Mix: 4P")
    with st.expander("1 · Product", expanded=True):
        rnd = st.slider("F&E-Budget pro Jahr (€)", 0, 150000, 60000, 5000)
        quality = st.selectbox("Materialqualität", ["Standard", "Premium", "Luxus"], index=0)
        packaging = st.slider("Packaging & Design je Starterset (€)", 0.0, 25.0, 5.0, 0.5)
        st.caption("F&E beeinflusst die Markenstärke mit Verzögerung. Materialqualität verändert Kosten und Nachfrage.")
    with st.expander("2 · Price", expanded=True):
        starter_price = st.slider("Starterset: Schuh + 2 Sohlen (€ brutto)", 150, 400, 210, 5)
        sole_price = st.slider("Ersatzsohle (€ brutto)", 20, 100, 35, 1)
        shoe_price = st.slider("Schuh einzeln (€ brutto)", 100, 350, 170, 5)
        discount = st.slider("Rabatt auf 2 Startersets (%)", 0, 30, 10, 1)
        target_price = st.slider("Starterset-Zielpreis im Jahr 5 (€ brutto)", 150, 500, 340, 5)
        st.caption("Alle Sortimentpreise steigen jährlich mit demselben Faktor bis Jahr 5. Der Mengenrabatt gilt für beide Sets einer Zweierbestellung.")
    with st.expander("3 · Place", expanded=True):
        online = st.checkbox("Onlineshop", value=True)
        retail = st.checkbox("Stationärer Handel / On-Site-Shop", value=True)
        marketplace = st.checkbox("Marktplätze", value=False)
        st.caption("Onlineshop: 3.600 €/Jahr + 3 % Provision; Handel: 12.000 €/Jahr + 25 % Handelsspanne; Marktplätze: 1.200 €/Jahr + 15 % Provision. Annahmen.")
    with st.expander("4 · Promotion", expanded=True):
        content = st.slider("Social Media Content (€/Monat)", 0, 3000, 200, 50)
        ads = st.slider("Social Media Ads (€/Monat)", 0, 10000, 400, 50)
        sponsored_sets = st.slider("Gratis-Startersets für Nachwuchstalente / Jahr", 0, 100, 20, 1)
        event_budget = st.slider("Verbandsaktivierung / Events (€/Jahr)", 0, 15000, 1000, 250)
        st.caption("Produktkosten der gesponserten Sets werden zusätzlich als Promotionkosten erfasst.")
    with st.expander("Modellannahmen (optional)", expanded=False):
        vat = st.number_input("Umsatzsteuer (%)", 0.0, 30.0, 20.0, 0.5)
        market_capacity = st.slider("Erreichbarer Markt (Käufer/Jahr)", 1000, 100000, 15000, 1000)
        organic_base = st.slider("Basisabsatz Jahr 1 ohne Werbung (Sets)", 0, 5000, 650, 50)
        elasticity = st.slider("Preiselastizität (Betrag)", 0.0, 3.0, 1.2, 0.1)
        annual_market_growth = st.slider("Marktwachstum pro Jahr (%)", -10.0, 20.0, 4.0, 1.0)
        cost_inflation = st.slider("Kostenanstieg pro Jahr (%)", 0.0, 15.0, 3.0, 0.5)
        base_overhead = st.slider("Allgemeine Fixkosten (€/Jahr)", 0, 150000, 24000, 1000)
        pair_share = st.slider("Anteil Sets aus Zweierbestellungen (%)", 0, 80, 20, 5)
        extra_sole_rate = st.slider("Ersatzsohlen pro verkauftem Starterset", 0.0, 2.0, 0.25, 0.05)
        extra_shoe_rate = st.slider("Einzelschuhe pro verkauftem Starterset", 0.0, 1.0, 0.05, 0.01)
        returns_reserve = st.slider("Retouren/Garantie-Reserve (% Nettoumsatz)", 0.0, 15.0, 3.0, 0.5)
        st.caption("Der Basisabsatz, Marktumfang und Wirkungskoeffizienten sind illustrative Annahmen. Keine externe Validierung.")

if not (online or retail or marketplace):
    st.warning("Kein Vertriebskanal ausgewählt. Es werden keine Verkäufe berechnet; laufende Kosten fallen dennoch an.")

quality_factors = {
    "Standard": {"cost": 1.00, "demand": 1.00},
    "Premium": {"cost": 1.25, "demand": 1.12},
    "Luxus": {"cost": 1.55, "demand": 1.20},
}
q = quality_factors[quality]
# Basisannahmen für Produktionskosten ohne Packaging; netto gerechnet.
base_starter_production = 100.0
base_sole_production = 14.0
base_shoe_production = 55.0
# Gewichte normalisiert: Absatz verteilt sich auf aktive Kanäle, keine dreifache Zählung.
channel_config = {
    "Onlineshop": {"enabled": online, "weight": 0.55, "fixed": 3600, "fee": 0.03},
    "Handel / On-Site": {"enabled": retail, "weight": 0.30, "fixed": 12000, "fee": 0.25},
    "Marktplätze": {"enabled": marketplace, "weight": 0.15, "fixed": 1200, "fee": 0.15},
}
active = {k: v for k, v in channel_config.items() if v["enabled"]}
weight_sum = sum(v["weight"] for v in active.values())
weighted_fee = sum(v["weight"] / weight_sum * v["fee"] for v in active.values()) if weight_sum else 0.0
channel_fixed = sum(v["fixed"] for v in active.values())
# Sponsoringkosten enthalten Herstellung + Verpackung; keine fiktiven Verkaufserlöse.
first_year_sponsor_unit_cost = base_starter_production * q["cost"] + packaging
promotion_year1 = 12 * (content + ads) + event_budget + sponsored_sets * first_year_sponsor_unit_cost
st.sidebar.metric("Promotion Jahr 1 (live)", f"{promotion_year1:,.0f} €".replace(",", "."))
st.sidebar.caption("Content + Ads + Verbandsaktivierung + Herstellkosten der Gratissets")

# Preisentwicklung mit exakt erreichtem Zielpreis in Jahr 5.
price_growth = (target_price / starter_price) ** (1.0 / 4.0)
base_price_net = starter_price / (1 + vat / 100)
# Langfristiger Markenstock: Vorjahres-Content, F&E und Sponsoring wirken nach.
brand_stock = 0.0
rows = []
for year_index in range(5):
    year = 2027 + year_index
    inflation_factor = (1 + cost_inflation / 100) ** year_index
    price_factor = price_growth ** year_index
    gross_starter = starter_price * price_factor
    gross_sole = sole_price * price_factor
    gross_shoe = shoe_price * price_factor
    net_starter = gross_starter / (1 + vat / 100)
    net_sole = gross_sole / (1 + vat / 100)
    net_shoe = gross_shoe / (1 + vat / 100)
    starter_unit_cost = (base_starter_production * q["cost"] + packaging) * inflation_factor
    sole_unit_cost = base_sole_production * q["cost"] * inflation_factor
    shoe_unit_cost = base_shoe_production * q["cost"] * inflation_factor

    # Ads: sofortige, abnehmende Wirkung; Content/F&E/Sponsoring: zeitversetzter Markenstock.
    ads_effect = 240.0 * np.log1p(ads / 400.0) if ads > 0 else 0.0
    brand_effect = 0.25 * brand_stock
    price_effect = (net_starter / base_price_net) ** (-elasticity)
    quality_effect = q["demand"]
    discount_effect = 1 + 0.004 * discount  # begrenzter Conversion-Effekt (Annahme)
    available_market = market_capacity * (1 + annual_market_growth / 100) ** year_index
    # Sättigung: Nachfrage nähert sich einer Kapazitätsgrenze an, statt unbegrenzt zu wachsen.
    raw_demand = max(0.0, (organic_base + ads_effect + brand_effect) * price_effect * quality_effect * discount_effect)
    saturation_demand = available_market * (1 - np.exp(-raw_demand / max(available_market, 1)))
    starter_units = int(np.rint(saturation_demand)) if active else 0
    sole_units = int(np.rint(starter_units * extra_sole_rate))
    shoe_units = int(np.rint(starter_units * extra_shoe_rate))

    # Rabatt nur auf den Anteil der Startersets, die in Zweierbestellungen verkauft werden.
    starter_revenue = starter_units * net_starter * (1 - pair_share / 100 * discount / 100)
    sole_revenue = sole_units * net_sole
    shoe_revenue = shoe_units * net_shoe
    revenue = starter_revenue + sole_revenue + shoe_revenue
    production = starter_units * starter_unit_cost + sole_units * sole_unit_cost + shoe_units * shoe_unit_cost
    sponsor_production = sponsored_sets * starter_unit_cost
    promotion = 12 * (content + ads) * inflation_factor + event_budget * inflation_factor + sponsor_production
    distribution = channel_fixed * inflation_factor + weighted_fee * revenue
    overhead = base_overhead * inflation_factor
    warranty = revenue * returns_reserve / 100
    research = float(rnd)  # jährliche Auszahlung als Aufwand im vereinfachten EBIT-Modell
    total_cost = production + promotion + distribution + overhead + warranty + research
    ebit = revenue - total_cost
    rows.append({
        "Jahr": year, "Startersets verkauft": starter_units, "Ersatzsohlen verkauft": sole_units,
        "Einzelschuhe verkauft": shoe_units, "Gratissets": sponsored_sets,
        "Starterset brutto (€)": gross_starter, "Sohle brutto (€)": gross_sole,
        "Schuh brutto (€)": gross_shoe, "Umsatz netto (€)": revenue,
        "Produktion (€)": production, "Vertrieb (€)": distribution,
        "Promotion (€)": promotion, "F&E (€)": research,
        "Allgemeine Fixkosten (€)": overhead, "Retouren/Garantie (€)": warranty,
        "Gesamtkosten (€)": total_cost, "EBIT (€)": ebit,
        "Umsatzrendite (%)": 100 * ebit / revenue if revenue > 0 else np.nan,
        "Markenkapital (Index)": brand_stock,
    })
    # Erst NACH dem Jahr wirksame Markeninvestitionen; bewusst gedämpfte Effekte.
    content_contribution = 70.0 * np.log1p(content / 200.0) if content > 0 else 0.0
    rnd_contribution = 85.0 * np.log1p(rnd / 60000.0) if rnd > 0 else 0.0
    sponsor_contribution = 5.0 * sponsored_sets
    brand_stock = 0.70 * brand_stock + content_contribution + rnd_contribution + sponsor_contribution

df = pd.DataFrame(rows)
fmt_eur = lambda x: f"{x:,.0f} €".replace(",", ".")
revenue_5y = float(df["Umsatz netto (€)"].sum())
ebit_5y = float(df["EBIT (€)"].sum())
units_5y = int(df["Startersets verkauft"].sum())
margin_5y = 100 * ebit_5y / revenue_5y if revenue_5y > 0 else np.nan

st.subheader("Ergebnisübersicht | 2027–2031")
c1, c2, c3, c4 = st.columns(4)
c1.metric("5J-Umsatz (netto)", fmt_eur(revenue_5y))
c2.metric("5J-Gewinn (EBIT)", fmt_eur(ebit_5y))
c3.metric("Startersets verkauft", f"{units_5y:,}".replace(",", "."))
c4.metric("Umsatzrendite", f"{margin_5y:.1f} %" if np.isfinite(margin_5y) else "–")

st.subheader("Umsatz, Gesamtkosten und EBIT")
line_df = df.set_index("Jahr")[["Umsatz netto (€)", "Gesamtkosten (€)", "EBIT (€)"]]
st.line_chart(line_df)

st.subheader("Kostenstruktur nach Teilsummen")
cost_cols = ["Produktion (€)", "Vertrieb (€)", "Promotion (€)", "F&E (€)", "Allgemeine Fixkosten (€)", "Retouren/Garantie (€)"]
st.bar_chart(df.set_index("Jahr")[cost_cols], stack=True)

st.subheader("Jahrestabelle")
display = df.drop(columns=["Markenkapital (Index)"]).copy()
formats = {c: "{:,.2f} €" for c in display.columns if c.endswith("(€)")}
formats["Umsatzrendite (%)"] = "{:.1f} %"
st.dataframe(display.style.format(formats, thousands=".", decimal=","), use_container_width=True, hide_index=True)

st.subheader("Preisentwicklung des Sortiments (brutto)")
st.dataframe(df[["Jahr", "Starterset brutto (€)", "Sohle brutto (€)", "Schuh brutto (€)"]].style.format({
    "Starterset brutto (€)": "{:,.2f} €", "Sohle brutto (€)": "{:,.2f} €", "Schuh brutto (€)": "{:,.2f} €"
}, thousands=".", decimal=","), hide_index=True, use_container_width=True)

st.download_button("📥 Jahresdaten als CSV herunterladen", data=df.to_csv(index=False, sep=";", decimal=",").encode("utf-8-sig"), file_name="switchsole_5_jahre.csv", mime="text/csv")

with st.expander("Methodik, Grenzen und Annahmen", expanded=False):
    st.markdown("""
**Finanzielle Abgrenzung:** Die Preise werden als Bruttopreise eingegeben; Umsätze und Provisionen basieren auf Nettoumsätzen. Der vereinfachte EBIT zieht Produktionskosten, Kanalgebühren, Marketing, F&E, Fixkosten und eine Garantie-/Retourenreserve ab. Es gibt keine Finanzierungskosten oder Ertragsteuern. F&E wird vollständig als Aufwand behandelt; eine mögliche Aktivierung oder Abschreibung wird nicht modelliert.

**Produktmix:** Startersets bilden das Kernprodukt. Ersatzsohlen und Einzelschuhe werden proportional zum Startersetabsatz geschätzt. Gratissets erzeugen Kosten, aber keinen Umsatz.

**Nachfrage:** Anzeigen wirken sofort mit abnehmendem Grenznutzen (Logarithmus). Content, Sponsoring und F&E erhöhen einen Markenstock, der erst in Folgejahren wirkt und jährlich teilweise verfällt. Die Preiselastizität reduziert bei höheren Preisen die Nachfrage. Eine exponentielle Sättigungsfunktion begrenzt den Absatz relativ zum erreichbaren Markt.

**Kanäle:** Der Absatz wird einmal berechnet und auf die aktivierten Kanäle nach normalisierten Gewichten verteilt. Gebühren werden als gewichteter Prozentsatz berechnet; Kanal-Fixkosten fallen separat an. Kanalgewichte sind Annahmen und keine Marktstudie.

**Grenzen:** Die Zahlen sind didaktische Szenariowerte, keine belastbare Marktprognose. Vor einer Investitionsentscheidung sind Lieferantenangebote, Testverkäufe, Kundenbefragungen und technische Produktvalidierung erforderlich. Die Annahmen zu Wechselmechanismus, Pedalkompatibilität und Produktsicherheit sind nicht validiert.
""")
