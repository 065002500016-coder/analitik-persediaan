import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

st.set_page_config(page_title="Analitik Persediaan EOQ & EPQ", layout="wide")

# ---------------------------------------------------------------- Sidebar
st.sidebar.header("Parameter Persediaan")
D = st.sidebar.number_input("Permintaan Tahunan D (unit/tahun)", min_value=1.0, value=12000.0, step=100.0)
S = st.sidebar.number_input("Biaya Pesan / Setup S ($)", min_value=0.01, value=100.0, step=5.0)
H = st.sidebar.number_input("Biaya Simpan H ($/unit/tahun)", min_value=0.01, value=4.0, step=0.5)
DAYS = st.sidebar.number_input("Hari Kerja per Tahun", min_value=1, value=300, step=10)
P = st.sidebar.number_input("Laju Produksi p (unit/hari)", min_value=1.0, value=100.0, step=5.0)
L = st.sidebar.number_input("Lead Time L (hari)", min_value=0.0, value=5.0, step=1.0)
Q_CUR = st.sidebar.number_input("Ukuran Lot Kebijakan Saat Ini (unit)", min_value=1.0, value=1000.0, step=50.0)

d = D / DAYS
if P <= d:
    st.error(f"Laju produksi (p = {P:,.0f}) harus lebih besar dari permintaan harian (d = {d:,.2f}).")
    st.stop()


# ---------------------------------------------------------------- Model
def eoq_cost(q):
    order = D / q * S
    hold = q / 2 * H
    return order, hold, order + hold


def epq_cost(q):
    setup = D / q * S
    hold = q * (1 - d / P) / 2 * H
    return setup, hold, setup + hold


q_eoq = np.sqrt(2 * D * S / H)
q_epq = np.sqrt(2 * D * S / (H * (1 - d / P)))
rop = d * L

rows = []
for name, q, fn in [
    ("Model A (EOQ)", q_eoq, eoq_cost),
    ("Model B (EPQ)", q_epq, epq_cost),
    ("Kebijakan Saat Ini", Q_CUR, eoq_cost),
]:
    o, h, t = fn(q)
    rows.append({"Model": name, "Q (unit)": q, "Pesanan/Setup per Tahun": D / q,
                 "Biaya Pemesanan/Setup ($)": o, "Biaya Simpan ($)": h, "Total Biaya ($)": t})
df = pd.DataFrame(rows)

# ---------------------------------------------------------------- Halaman
st.title("Aplikasi Analitik Persediaan: EOQ dan EPQ")
st.caption("Simulasi ukuran lot ekonomis untuk permintaan pasti (Operations Management, Chapter 13)")

c1, c2, c3, c4 = st.columns(4)
c1.metric("EOQ", f"{q_eoq:,.2f} unit")
c2.metric("EPQ", f"{q_epq:,.2f} unit")
c3.metric("Reorder Point (d × L)", f"{rop:,.0f} unit")
c4.metric("Permintaan Harian (d)", f"{d:,.2f} unit")

st.subheader("Ringkasan Perbandingan Biaya")
st.dataframe(
    df.style.format({
        "Q (unit)": "{:,.2f}", "Pesanan/Setup per Tahun": "{:,.2f}",
        "Biaya Pemesanan/Setup ($)": "{:,.2f}", "Biaya Simpan ($)": "{:,.2f}",
        "Total Biaya ($)": "{:,.2f}",
    }),
    hide_index=True, use_container_width=True,
)

left, right = st.columns([3, 2])
with left:
    long = df.melt(id_vars="Model", value_vars=["Biaya Pemesanan/Setup ($)", "Biaya Simpan ($)"],
                   var_name="Komponen", value_name="Biaya ($)")
    fig = px.bar(long, x="Model", y="Biaya ($)", color="Komponen", title="Perbandingan Biaya per Tahun")
    st.plotly_chart(fig, use_container_width=True)
with right:
    best = df.loc[df["Total Biaya ($)"].idxmin()]
    st.success(f"**Rekomendasi:** {best['Model']} memiliki total biaya terendah, "
               f"yaitu ${best['Total Biaya ($)']:,.2f} per tahun.")
    st.info("Model A dan B menggambarkan kondisi pasokan berbeda (beli sekaligus vs produksi bertahap). "
            "Gunakan EOQ jika barang dibeli, EPQ jika diproduksi sendiri.")

st.subheader("Kurva Total Biaya terhadap Ukuran Lot")
q_range = np.linspace(max(1.0, 0.2 * q_eoq), 3 * max(q_eoq, q_epq), 300)
curve = go.Figure()
curve.add_trace(go.Scatter(x=q_range, y=[eoq_cost(q)[0] for q in q_range], name="Biaya Pemesanan"))
curve.add_trace(go.Scatter(x=q_range, y=[eoq_cost(q)[1] for q in q_range], name="Biaya Simpan (EOQ)"))
curve.add_trace(go.Scatter(x=q_range, y=[eoq_cost(q)[2] for q in q_range], name="Total Biaya (EOQ)",
                           line=dict(width=3)))
curve.add_trace(go.Scatter(x=q_range, y=[epq_cost(q)[2] for q in q_range], name="Total Biaya (EPQ)",
                           line=dict(width=3, dash="dash")))
curve.add_vline(x=q_eoq, line_dash="dot", annotation_text="EOQ")
curve.add_vline(x=q_epq, line_dash="dot", annotation_text="EPQ")
curve.update_layout(xaxis_title="Ukuran Lot Q (unit)", yaxis_title="Biaya per Tahun ($)")
st.plotly_chart(curve, use_container_width=True)

# ---------------------------------------------------------------- Rincian
with st.expander("Rincian Perhitungan Model A (EOQ)"):
    st.latex(r"Q^* = \sqrt{\frac{2DS}{H}}")
    st.write(f"Q* = {q_eoq:,.2f} unit; pesanan per tahun = {D / q_eoq:,.2f}; "
             f"siklus = {q_eoq / d:,.2f} hari.")
    o, h, t = eoq_cost(q_eoq)
    st.write(f"Biaya pemesanan = ${o:,.2f}; biaya simpan = ${h:,.2f}; total = ${t:,.2f}.")

with st.expander("Rincian Perhitungan Model B (EPQ)"):
    st.latex(r"Q^* = \sqrt{\frac{2DS}{H\left(1-\frac{d}{p}\right)}}")
    st.write(f"Q* = {q_epq:,.2f} unit; persediaan maksimum = {q_epq * (1 - d / P):,.2f} unit; "
             f"lama produksi = {q_epq / P:,.2f} hari; siklus = {q_epq / d:,.2f} hari.")
    o, h, t = epq_cost(q_epq)
    st.write(f"Biaya setup = ${o:,.2f}; biaya simpan = ${h:,.2f}; total = ${t:,.2f}.")

with st.expander("Rincian Kebijakan Saat Ini"):
    o, h, t = eoq_cost(Q_CUR)
    st.write(f"Lot tetap {Q_CUR:,.0f} unit: biaya pemesanan = ${o:,.2f}; biaya simpan = ${h:,.2f}; "
             f"total = ${t:,.2f}. Selisih terhadap EOQ = ${t - eoq_cost(q_eoq)[2]:,.2f}.")
