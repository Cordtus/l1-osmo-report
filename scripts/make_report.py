#!/usr/bin/env python3
"""Generate the L1/OSMO PDF report (USD, full range) from analysis/*.csv."""

import os, subprocess
import numpy as np
import pandas as pd
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

BASE = "/home/cordt/l1-osmo-export"
REP = f"{BASE}/report"
CH = f"{REP}/charts"
os.makedirs(CH, exist_ok=True)

d = pd.read_csv(f"{BASE}/analysis/l1_osmo_daily.csv", parse_dates=["date"]).set_index(
    "date"
)
L1 = "ibc/F16FDC11A7662B86BC0B9CE61871CBACF7C20606F95E86260FD38915184B75B4"
BLUE, ORANGE, GREEN, PURPLE, RED, SKY = (
    "#2563eb",
    "#f59e0b",
    "#10b981",
    "#7c3aed",
    "#dc2626",
    "#0ea5e9",
)
plt.rcParams.update(
    {
        "figure.dpi": 130,
        "font.size": 10,
        "axes.grid": True,
        "grid.alpha": 0.25,
        "axes.spines.top": False,
        "axes.spines.right": False,
        "figure.autolayout": True,
    }
)
save = lambda fig, n: (fig.savefig(f"{CH}/{n}", bbox_inches="tight"), plt.close(fig))

# 1 price
fig, ax = plt.subplots(figsize=(10, 4))
ax.plot(d.index, d["price_l1_usd"], color=BLUE, lw=1.2, label="L1 price (USD)")
ax.set_ylabel("USD", color=BLUE)
ax2 = ax.twinx()
ax2.grid(False)
ax2.plot(
    d.index,
    d["price_l1_osmo_close"].where(d["price_l1_osmo_close"] > 0),
    color=ORANGE,
    lw=1.1,
    label="L1 in OSMO",
)
ax2.set_ylabel("OSMO", color=ORANGE)
ax.set_title("L1 price — USD (left) and OSMO (right), full history")
l1, lb1 = ax.get_legend_handles_labels()
l2, lb2 = ax2.get_legend_handles_labels()
ax.legend(l1 + l2, lb1 + lb2, loc="upper left", frameon=False)
save(fig, "01_price.png")

# 2 daily volume USD
fig, ax = plt.subplots(figsize=(10, 3.4))
ax.bar(d.index, d["volume_usdc"], width=1.0, color=GREEN)
ax.set_ylabel("USD")
ax.set_title("Daily trading volume (USD), full history")
save(fig, "02_volume.png")

# 3 monthly volume USD
mv = d["volume_usdc"].resample("MS").sum()
fig, ax = plt.subplots(figsize=(10, 3.4))
ax.bar(mv.index, mv.values, width=20, color="#059669")
ax.set_ylabel("USD")
ax.set_title("Monthly trading volume (USD)")
save(fig, "03_monthly_volume.png")

# 4 cumulative volume USD
fig, ax = plt.subplots(figsize=(10, 3.2))
ax.fill_between(d.index, d["cum_volume_usdc"], color=GREEN, alpha=0.25)
ax.plot(d.index, d["cum_volume_usdc"], color="#059669", lw=1.2)
ax.set_ylabel("USD")
ax.set_title("Cumulative trading volume (USD)")
save(fig, "04_cum_volume.png")

# 5 TVL
fig, ax = plt.subplots(figsize=(10, 3.4))
ax.fill_between(d.index, d["tvl_usd_close"], color=PURPLE, alpha=0.25)
ax.plot(d.index, d["tvl_usd_close"], color=PURPLE, lw=1.2)
ax.set_ylabel("USD")
ax.set_title("Pool TVL (USD) — from 2023-11-16 (first liquidity snapshot)")
save(fig, "05_tvl.png")

# 6 composition
fig, ax = plt.subplots(figsize=(10, 3.5))
ax.stackplot(
    d.index,
    d["l1_usd_close"],
    d["osmo_usd_close"],
    labels=["L1", "OSMO"],
    colors=[BLUE, ORANGE],
    alpha=0.8,
)
ax.set_ylabel("USD")
ax.set_title("Pool composition (USD)")
ax.legend(loc="upper left", frameon=False)
save(fig, "06_composition.png")

# 7 LP flows USD
madd = d["lp_add_usd"].resample("MS").sum()
mrm = d["lp_rm_usd"].resample("MS").sum()
fig, ax = plt.subplots(figsize=(10, 3.5))
ax.bar(madd.index, madd.values, width=20, color=GREEN, label="deposits")
ax.bar(mrm.index, -mrm.values, width=20, color=RED, label="withdrawals")
ax.axhline(0, color="#888", lw=0.8)
ax.set_ylabel("USD")
ax.set_title("LP flows (USD) — deposits (+) / withdrawals (−)")
ax.legend(loc="upper left", frameon=False)
save(fig, "07_lp_flows.png")

# 8 bridge USD
bin_ = d["l1_bridged_in_usd"].resample("MS").sum()
bout = d["l1_bridged_out_usd"].resample("MS").sum()
fig, ax = plt.subplots(figsize=(10, 3.5))
ax.bar(bin_.index, bin_.values, width=20, color=SKY, label="bridged in")
ax.bar(bout.index, -bout.values, width=20, color=RED, label="bridged out")
ax.axhline(0, color="#888", lw=0.8)
ax.set_ylabel("USD")
ax.set_title("L1 bridge flows to/from Osmosis (USD)")
ax.legend(loc="upper left", frameon=False)
save(fig, "08_bridge.png")

# 9 trades/traders
fig, ax = plt.subplots(figsize=(10, 3.5))
ax.bar(d.index, d["trades"], width=1.0, color="#94a3b8", label="trades")
ax2 = ax.twinx()
ax2.grid(False)
ax2.plot(d.index, d["unique_traders"], color="#111827", lw=0.9, label="unique traders")
ax.set_ylabel("trades")
ax2.set_ylabel("traders")
ax.set_title("Daily trades and unique traders")
l1, lb1 = ax.get_legend_handles_labels()
l2, lb2 = ax2.get_legend_handles_labels()
ax.legend(l1 + l2, lb1 + lb2, loc="upper right", frameon=False)
save(fig, "09_trades.png")

# 10 L1 share
fig, ax = plt.subplots(figsize=(10, 3.1))
ax.plot(
    d.index,
    (d["l1_share"] * 100).rolling(7, min_periods=1).mean(),
    color=PURPLE,
    lw=1.1,
)
ax.set_ylabel("% of TVL")
ax.set_ylim(0, 100)
ax.set_title("L1 share of pool value (7-day avg)")
save(fig, "10_share.png")

# 11 swap-implied prices full range
sw = pd.read_csv(f"{BASE}/analysis/swaps_with_usd.csv")
sw["ts"] = pd.to_datetime(sw["timestamp"])
sw["day"] = sw["ts"].dt.floor("D")
g = sw.groupby("day")[["price_osmo_per_l1", "price_l1_usd"]].median()
fig, ax = plt.subplots(figsize=(10, 3.4))
ax.plot(g.index, g["price_l1_usd"], color=BLUE, lw=1.0, label="L1 USD")
ax.set_ylabel("USD", color=BLUE)
ax2 = ax.twinx()
ax2.grid(False)
ax2.plot(g.index, g["price_osmo_per_l1"], color=ORANGE, lw=1.0, label="L1 in OSMO")
ax2.set_ylabel("OSMO", color=ORANGE)
ax.set_title("Per-trade implied L1 price (daily median), full history")
l1, lb1 = ax.get_legend_handles_labels()
l2, lb2 = ax2.get_legend_handles_labels()
ax.legend(l1 + l2, lb1 + lb2, loc="upper left", frameon=False)
save(fig, "11_trade_price.png")

# ---------------- monthly table ----------------
mt = pd.DataFrame(
    {
        "trades": d["trades"].resample("MS").sum(),
        "traders": d["unique_traders"].resample("MS").sum(),
        "volume_usd": d["volume_usdc"].resample("MS").sum(),
        "avg_tvl_usd": d["tvl_usd_close"].resample("MS").mean(),
        "l1_price_usd": d["price_l1_usd"].resample("MS").last(),
        "lp_net_usd": d["lp_net_usd"].resample("MS").sum(),
        "bridge_in_usd": d["l1_bridged_in_usd"].resample("MS").sum(),
        "bridge_out_usd": d["l1_bridged_out_usd"].resample("MS").sum(),
    }
)
mt.index = mt.index.strftime("%Y-%m")
mthtml = mt.to_html(border=0, classes="tbl", float_format=lambda x: f"{x:,.2f}")

# ---------------- headline ----------------
lifetime = d["volume_usdc"].sum()
trades = int(d["trades"].sum())
traders = int(pd.read_csv(f"{BASE}/swaps_pool732.csv", dtype=str)["sender"].nunique())
cur = d.iloc[-2] if d["volume_usdc"].iloc[-1] == 0 else d.iloc[-1]
tvl_series = d["tvl_usd_close"][d["tvl_usd_close"] > 0]
cur_tvl = tvl_series.iloc[-1]
cur_l1 = d["price_l1_usd"][d["price_l1_usd"] > 0].iloc[-1]
cur_l1o = d["price_l1_osmo_close"][d["price_l1_osmo_close"] > 0].iloc[-1]
brin, brout = d["l1_bridged_in_usd"].sum(), d["l1_bridged_out_usd"].sum()
lpnet = d["lp_add_usd"].sum() - d["lp_rm_usd"].sum()
first_sw, last = d.index.min().date(), d.index.max().date()
liq_first = tvl_series.index.min().date()

CHARTS = [
    (
        "01_price.png",
        "L1 price in USD (derived, full range) and in OSMO. USD pricing is derived from Numia's per-minute USD volume; it matches the independent liquidity-snapshot price to within ~1% where both exist.",
    ),
    (
        "02_volume.png",
        "Daily trading volume in USD across the entire history (2022-06-06 onward).",
    ),
    ("03_monthly_volume.png", "Monthly volume, showing the 2026 revival."),
    ("04_cum_volume.png", f"Cumulative volume: ${lifetime:,.0f} lifetime."),
    (
        "05_tvl.png",
        "Total value locked in USD. Liquidity snapshots begin 2023-11-16, so TVL has no earlier source.",
    ),
    ("06_composition.png", "Pool composition by value: L1 vs OSMO (USD)."),
    (
        "07_lp_flows.png",
        "LP deposits and withdrawals in USD, priced from the full-range USD series.",
    ),
    (
        "08_bridge.png",
        "L1 bridged onto (+) and off (−) Osmosis in USD via the channel-253 ICS-20 path.",
    ),
    ("09_trades.png", "Daily trade count and unique traders."),
    ("10_share.png", "L1's share of pool value (7-day average)."),
    (
        "11_trade_price.png",
        "Per-trade implied L1 price (daily median) in USD and OSMO.",
    ),
]
imgs = "\n".join(
    f'<figure><img src="charts/{f}"/><figcaption>{c}</figcaption></figure>'
    for f, c in CHARTS
)

html = f"""<!doctype html><html><head><meta charset="utf-8"><style>
@page {{ size: A4; margin: 16mm 14mm; }}
body {{ font-family: -apple-system,"Segoe UI",Roboto,Helvetica,Arial,sans-serif; color:#1f2937; font-size:11px; line-height:1.5; }}
h1 {{ font-size:25px; margin:0 0 4px; color:#111827; }}
h2 {{ font-size:15.5px; margin:24px 0 8px; padding-bottom:4px; border-bottom:2px solid #e5e7eb; }}
.sub {{ color:#6b7280; font-size:12px; margin-bottom:16px; }}
.cover {{ border:1px solid #e5e7eb; border-radius:10px; padding:20px; background:#f9fafb; margin-bottom:8px; }}
.kpis {{ display:flex; flex-wrap:wrap; gap:9px; margin:10px 0 4px; }}
.kpi {{ border:1px solid #e5e7eb; border-radius:8px; padding:9px 13px; min-width:140px; background:#fff; }}
.kpi .v {{ font-size:17px; font-weight:700; color:#111827; }}
.kpi .l {{ font-size:9.5px; color:#6b7280; text-transform:uppercase; letter-spacing:.04em; }}
table.tbl {{ border-collapse:collapse; width:100%; font-size:9px; }}
table.tbl th, table.tbl td {{ border-bottom:1px solid #eee; padding:2.5px 5px; text-align:right; }}
table.tbl th:first-child, table.tbl td:first-child {{ text-align:left; }}
table.tbl th {{ background:#f3f4f6; position:sticky; top:0; }}
figure {{ margin:8px 0 15px; page-break-inside:avoid; }}
figure img {{ width:100%; border:1px solid #eee; border-radius:6px; }}
figcaption {{ color:#6b7280; font-size:9.5px; margin-top:3px; }}
code {{ background:#f3f4f6; padding:1px 4px; border-radius:4px; font-size:10px; }}
.pagebreak {{ page-break-before:always; }}
.note {{ background:#fffbeb; border:1px solid #fde68a; border-radius:8px; padding:10px 14px; }}
.info {{ background:#eff6ff; border:1px solid #bfdbfe; border-radius:8px; padding:10px 14px; }}
.files td:first-child {{ font-family:ui-monospace,Menlo,monospace; font-size:9.5px; }}
</style></head><body>

<div class="cover">
  <h1>GenesisL1 (L1) / OSMO on Osmosis</h1>
  <div class="sub">Full historical trading &amp; liquidity report · pool&nbsp;732 · USD-denominated · generated {pd.Timestamp.utcnow():%Y-%m-%d %H:%M UTC}</div>
  <div class="kpis">
    <div class="kpi"><div class="v">${lifetime:,.0f}</div><div class="l">lifetime volume</div></div>
    <div class="kpi"><div class="v">{trades:,}</div><div class="l">trades</div></div>
    <div class="kpi"><div class="v">{traders:,}</div><div class="l">unique traders</div></div>
    <div class="kpi"><div class="v">${cur_tvl:,.0f}</div><div class="l">current TVL</div></div>
    <div class="kpi"><div class="v">${cur_l1:,.4f}</div><div class="l">L1 price (USD)</div></div>
    <div class="kpi"><div class="v">{cur_l1o:,.2f}</div><div class="l">L1 price (OSMO)</div></div>
    <div class="kpi"><div class="v">${brin:,.0f}</div><div class="l">bridged in (USD)</div></div>
    <div class="kpi"><div class="v">${brout:,.0f}</div><div class="l">bridged out (USD)</div></div>
  </div>
  <p style="margin:10px 0 0;color:#4b5563">Data window <b>{first_sw} → {last}</b>; every figure uses USD where
  it can be computed. Source: Numia public BigQuery <code>numia-data.osmosis</code>; denom/channel verified
  against the Osmosis archive RPC.</p>
</div>

<h2>1 · Executive summary</h2>
<p>The GenesisL1 native token (<code>el1</code>) trades on Osmosis exclusively against OSMO in GAMM pool
<b>732</b>, the only OSMO/L1 pair. Across the full history the pool has turned over
<b>${lifetime:,.0f}</b> over <b>{trades:,}</b> trades by <b>{traders:,}</b> wallets. Activity is thin and
episodic with a strong 2026 revival; current TVL is <b>${cur_tvl:,.0f}</b>, L1 trades at
<b>${cur_l1:,.4f}</b> (<b>{cur_l1o:,.2f} OSMO</b>). All-time bridged value is
<b>${brin:,.0f}</b> in / <b>${brout:,.0f}</b> out, and net LP value flow is
<b>${lpnet:,.0f}</b>.</p>
<div class="info"><b>USD across the whole range.</b> Numia's <code>pools_volume</code> gives USD volume from
the pool's first trade (2022-06-06). Dividing that per-minute USD by the swap token volume recovers
USD prices, so USD prices, LP flows and bridge flows are valued for the <i>entire</i> trading history —
not only from 2023-11-16 when liquidity snapshots begin. Where both exist the derived USD price matches
Numia's snapshot price to within ~1% (median).</div>

<h2>2 · Token &amp; channel identity</h2>
<table class="tbl files">
<tr><td>Native token</td><td><code>el1</code> · chain <code>genesis_29-2</code> · symbol L1 · 18 decimals</td></tr>
<tr><td>Osmosis IBC denom</td><td><code>{L1}</code></td></tr>
<tr><td>Denom trace</td><td><code>transfer/channel-253/el1</code></td></tr>
<tr><td>Channel pair</td><td>genesisl1 <code>channel-1</code>/<code>connection-1</code> ↔ osmosis <code>channel-253</code>/<code>connection-1539</code></td></tr>
<tr><td>Prior denom</td><td><code>ibc/DABCB5B2…7775</code> (channel-235) — live 2022-05-05→2022-05-31, never used in pool 732</td></tr>
<tr><td>Pool</td><td>GAMM <code>pool 732</code> (uosmo + L1) — only OSMO/L1 pair</td></tr>
</table>

<h2>3 · Visualizations</h2>
{imgs}

<div class="pagebreak"></div>
<h2>4 · Monthly activity (USD)</h2>
{mthtml}

<div class="pagebreak"></div>
<h2>5 · Data, methodology &amp; scope</h2>
<p>Data is Numia's public Osmosis BigQuery dataset (<code>numia-data.osmosis</code>, EU), queried through the
BigQuery sandbox via the REST API, filtered to pool 732 or the L1 denom and exported to local CSV (no Cloud
Storage, no billing). Denom/channel were confirmed against <code>https://rpc.archive.osmosis.zone</code>.</p>
<table class="tbl files">
<tr><th>Table</th><th>Rows</th><th>Coverage</th></tr>
<tr><td>osmosis_swaps (732)</td><td>40,856</td><td>2022-06-06 → {last}</td></tr>
<tr><td>osmosis_pools_volume (732)</td><td>2,303,926</td><td>2021-09-24 → {last} (non-zero 2022-06-06 →)</td></tr>
<tr><td>osmosis_pools_liquidity (732)</td><td>3,040,998</td><td>{liq_first} → {last}</td></tr>
<tr><td>osmosis_lp_gamm_join_pool (732)</td><td>712</td><td>2022-06-06 → 2026-09-29</td></tr>
<tr><td>osmosis_lp_gamm_exit_pool (732)</td><td>662</td><td>2022-06-06 → 2026-09-29</td></tr>
<tr><td>osmosis_ics20_receive (L1)</td><td>8,660</td><td>2022-06-01 → {last}</td></tr>
<tr><td>osmosis_ics20_transfer (L1)</td><td>2,134</td><td>2022-06-01 → {last}</td></tr>
<tr><td>osmosis_asset_denoms</td><td>3,750</td><td>reference</td></tr>
</table>

<h2>6 · Caveats</h2>
<ul>
<li>Swap/LP <code>token_amount</code> columns are <code>FLOAT</code>; at 18 decimals L1 amounts lose low-order
precision. Use the <code>ics20_*</code> tables (<code>BIGNUMERIC</code>) for exact amounts.</li>
<li>USD prices before 2023-11-16 are <b>derived</b> (USD volume ÷ token volume) and are smoothed with a
7-day median; treat them as estimates. From 2023-11-16 the USD price comes directly from liquidity snapshots.</li>
<li>TVL/USD liquidity has no source before 2023-11-16 — the pool balances are not reconstructable from the
available tables.</li>
<li><code>osmosis_lock_tokens</code> and <code>osmosis_superfluid_staking</code> are broken upstream (backing
<code>lf-data</code> tables 404) and are excluded.</li>
<li>Numia is migrating Osmosis data from BigQuery to ObsessionDB (ClickHouse); this is a point-in-time snapshot.</li>
</ul>

<h2>7 · Deliverables</h2>
<table class="tbl files">
<tr><td>l1-osmo-raw.tar.gz</td><td>all raw CSVs + Parquet + build scripts</td></tr>
<tr><td>l1-osmo-full.csv</td><td>consolidated daily metrics, USD-denominated (this report's dataset)</td></tr>
<tr><td>l1-osmo-report.pdf</td><td>this report</td></tr>
<tr><td>viz/l1_osmo_dashboard.html</td><td>interactive Plotly dashboard</td></tr>
<tr><td>MANIFEST.md</td><td>provenance &amp; file inventory</td></tr>
</table>
<p class="note">Data © Numia. Redistribution subject to Numia's terms. Figures are derived from on-chain
indexed data and provided as-is.</p>
</body></html>"""

open(f"{REP}/l1-osmo-report.html", "w").write(html)
print("html written")
subprocess.run(
    [
        "google-chrome-stable",
        "--headless=new",
        "--no-sandbox",
        "--disable-gpu",
        "--no-pdf-header-footer",
        f"--print-to-pdf={REP}/l1-osmo-report.pdf",
        f"file://{REP}/l1-osmo-report.html",
    ],
    check=True,
    timeout=300,
    capture_output=True,
)
print(
    "pdf ->",
    f"{REP}/l1-osmo-report.pdf",
    os.path.getsize(f"{REP}/l1-osmo-report.pdf"),
    "bytes",
)
