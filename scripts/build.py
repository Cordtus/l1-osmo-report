#!/usr/bin/env python3
"""Build L1/OSMO analysis artifacts from the raw BigQuery CSVs (local, no BQ spend).

Extends USD valuation across the *entire* available range:
  Numia's pools_volume gives per-minute USD volume from the pool's first trade (2022-06-06).
  Dividing that by the swap token volume recovers USD prices, so USD prices exist for the
  whole trading history - not just from the first liquidity snapshot (2023-11-16).

Outputs:
  analysis/l1_osmo_daily.csv       consolidated daily metrics (USD-denominated)  "full csv"
  analysis/swaps_with_usd.csv      every swap + USD value / prices
  analysis/bridge_with_usd.csv     every L1 ICS-20 leg + USD value
  raw_parquet/*.parquet            typed copies
  viz/l1_osmo_dashboard.html       interactive plotly (daily)
  viz/l1_osmo_overview.png         static overview
"""

import glob
import os

import numpy as np
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

BASE = "/home/cordt/l1-osmo-export"
L1 = "ibc/F16FDC11A7662B86BC0B9CE61871CBACF7C20606F95E86260FD38915184B75B4"
DEC = {"uosmo": 1e6, L1: 1e18}
IS_L1 = lambda s: s == L1


def load(name):
    p = os.path.join(BASE, name)
    if not os.path.exists(p):
        print("  (missing)", name)
        return None
    df = pd.read_csv(p, dtype=str)
    df.columns = [c.strip().lstrip("\ufeff") for c in df.columns]
    return df


def to_dt(s):
    return pd.to_datetime(pd.to_numeric(s, errors="coerce"), unit="s", utc=True)


def num(s):
    return pd.to_numeric(s, errors="coerce")


# ---------------- swaps ----------------
sw = load("swaps_pool732.csv")
if sw is not None:
    sw["ts"] = to_dt(sw["block_timestamp"])
    sw["amount_in"] = num(sw["token_amount_in"])
    sw["amount_out"] = num(sw["token_amount_out"])
    sw["in_h"] = sw.apply(
        lambda r: r.amount_in / DEC.get(r.token_denom_in, np.nan), axis=1
    )
    sw["out_h"] = sw.apply(
        lambda r: r.amount_out / DEC.get(r.token_denom_out, np.nan), axis=1
    )
    sw["sell_l1"] = IS_L1(sw["token_denom_in"])
    sw["price_osmo"] = pd.to_numeric(
        np.where(sw.sell_l1, sw.out_h / sw.in_h, sw.in_h / sw.out_h), errors="coerce"
    )
    sw["vol_osmo"] = np.where(sw.sell_l1, sw.out_h, sw.in_h)
    sw["vol_l1"] = np.where(sw.sell_l1, sw.in_h, sw.out_h)
    sw["day"] = sw["ts"].dt.floor("D")
    print(f"swaps: {len(sw):,} rows  {sw.ts.min()} -> {sw.ts.max()}")

# ---------------- volume ----------------
vo = load("pools_volume_732.csv")
if vo is not None:
    vo["ts"] = to_dt(vo["minute"])
    vo["usd"] = num(vo["usdc_volume"])
    vo["day"] = vo["ts"].dt.floor("D")
    print(f"volume: {len(vo):,} min rows")

# ---------------- liquidity (USD snapshots, 2023-11+) ----------------
lq = load("pools_liquidity_732.csv")
comp = None
if lq is not None:
    lq["ts"] = to_dt(lq["minute"])
    lq["amt"] = num(lq["token_amount"])
    lq["usd"] = num(lq["usdc_amount"])
    lq["is_l1"] = lq["token_denom"].apply(IS_L1)
    piv = lq.pivot_table(
        index="ts", columns="is_l1", values=["amt", "usd"], aggfunc="sum"
    )
    comp = pd.DataFrame(index=piv.index)
    comp["l1_amt"] = piv[("amt", True)]
    comp["osmo_amt"] = piv[("amt", False)]
    comp["l1_usd"] = piv[("usd", True)]
    comp["osmo_usd"] = piv[("usd", False)]
    comp["tvl_usd"] = comp["l1_usd"].fillna(0) + comp["osmo_usd"].fillna(0)
    comp["price_l1_usd"] = comp["l1_usd"] / comp["l1_amt"]
    comp["price_osmo_usd"] = comp["osmo_usd"] / comp["osmo_amt"]
    comp["price_l1_osmo"] = comp["l1_amt"].rdiv(comp["osmo_amt"])
    comp["day"] = comp.index.floor("D")
    print(f"liquidity: {len(lq):,} rows  {lq.ts.min()} -> {lq.ts.max()}")


def lp(fn):
    d = load(fn)
    if d is None:
        return None
    d["ts"] = to_dt(d["block_timestamp"])
    d["amt_h"] = pd.to_numeric(d["token_amount"], errors="coerce") / d[
        "token_denom"
    ].map(DEC)
    d["is_l1"] = d["token_denom"].apply(IS_L1)
    d["day"] = d["ts"].dt.floor("D")
    return d


jn, ex = lp("lp_gamm_join_pool_732.csv"), lp("lp_gamm_exit_pool_732.csv")


def ibc(fn):
    d = load(fn)
    if d is None:
        return None
    d["ts"] = to_dt(d["block_timestamp"])
    d["amt_h"] = pd.to_numeric(d["token_amount"], errors="coerce") / 1e18
    d["day"] = d["ts"].dt.floor("D")
    return d


ib_in, ib_out = ibc("ics20_receive_L1.csv"), ibc("ics20_transfer_L1.csv")

# ---------------- consolidated daily ----------------
days = pd.date_range(
    min(d["day"].min() for d in (sw, vo) if d is not None),
    max(d["day"].max() for d in (sw, vo) if d is not None),
    freq="D",
    tz="UTC",
)
out = pd.DataFrame(index=days)
if sw is not None:
    g = sw.groupby("day")
    out["trades"] = g.size()
    out["unique_traders"] = g["sender"].nunique()
    out["vol_osmo"] = g["vol_osmo"].sum()
    out["vol_l1"] = g["vol_l1"].sum()
    out["buys_l1"] = sw[~sw.sell_l1].groupby("day").size()
    out["sells_l1"] = sw[sw.sell_l1].groupby("day").size()
    out["price_l1_osmo_close"] = (
        sw.sort_values("ts").groupby("day")["price_osmo"].last()
    )
if vo is not None:
    out["volume_usdc"] = vo.groupby("day")["usd"].sum()
if comp is not None:
    cg = comp.groupby("day")
    out["tvl_usd_close"] = cg["tvl_usd"].last()
    out["l1_in_pool"] = cg["l1_amt"].last()
    out["osmo_in_pool"] = cg["osmo_amt"].last()
    out["l1_usd_close"] = cg["l1_usd"].last()
    out["osmo_usd_close"] = cg["osmo_usd"].last()
    out["price_l1_usd_close"] = cg["price_l1_usd"].last()
    out["price_osmo_usd_close"] = cg["price_osmo_usd"].last()
if jn is not None:
    out["lp_add_l1"] = jn[jn.is_l1].groupby("day")["amt_h"].sum()
    out["lp_add_osmo"] = jn[~jn.is_l1].groupby("day")["amt_h"].sum()
if ex is not None:
    out["lp_rm_l1"] = ex[ex.is_l1].groupby("day")["amt_h"].sum()
    out["lp_rm_osmo"] = ex[~ex.is_l1].groupby("day")["amt_h"].sum()
if ib_in is not None:
    out["l1_bridged_in"] = ib_in.groupby("day")["amt_h"].sum()
if ib_out is not None:
    out["l1_bridged_out"] = ib_out.groupby("day")["amt_h"].sum()

# ---- full-range USD prices: derived from USD volume / token volume, snapshots preferred ----
osmo_leg = sw.groupby("day")["vol_osmo"].sum().reindex(days, fill_value=0)
l1_leg = sw.groupby("day")["vol_l1"].sum().reindex(days, fill_value=0)
vol = out.get("volume_usdc", pd.Series(0.0, index=days)).reindex(days).fillna(0)
der_osmo = (vol / osmo_leg.replace(0, np.nan)).rolling(7, min_periods=1).median()
der_l1 = (vol / l1_leg.replace(0, np.nan)).rolling(7, min_periods=1).median()
snap_osmo = out.get("price_osmo_usd_close", pd.Series(np.nan, index=days)).reindex(days)
snap_l1 = out.get("price_l1_usd_close", pd.Series(np.nan, index=days)).reindex(days)
out["price_osmo_usd"] = snap_osmo.combine_first(der_osmo).ffill().bfill()
out["price_l1_usd"] = snap_l1.combine_first(der_l1).ffill().bfill()

# ---- USD-denominated flows across the full range ----
out["lp_add_usd"] = (
    out["lp_add_l1"].fillna(0) * out["price_l1_usd"]
    + out["lp_add_osmo"].fillna(0) * out["price_osmo_usd"]
)
out["lp_rm_usd"] = (
    out["lp_rm_l1"].fillna(0) * out["price_l1_usd"]
    + out["lp_rm_osmo"].fillna(0) * out["price_osmo_usd"]
)
out["lp_net_usd"] = out["lp_add_usd"] - out["lp_rm_usd"]
out["l1_bridged_in_usd"] = out["l1_bridged_in"] * out["price_l1_usd"]
out["l1_bridged_out_usd"] = out["l1_bridged_out"] * out["price_l1_usd"]
out["cum_volume_usdc"] = out["volume_usdc"].fillna(0).cumsum()

num_cols = out.select_dtypes("number").columns
out[num_cols] = out[num_cols].fillna(0)
if comp is not None:
    out["l1_share"] = (
        out["l1_usd_close"] / out["tvl_usd_close"].replace(0, np.nan)
    ).fillna(0)
os.makedirs(f"{BASE}/analysis", exist_ok=True)
out.index.name = "date"
out.to_csv(f"{BASE}/analysis/l1_osmo_daily.csv")
print(f"daily -> analysis/l1_osmo_daily.csv  ({len(out)} days)")

# ---------------- per-event USD exports ----------------
if sw is not None:
    sw["price_l1_usd"] = sw["day"].map(out["price_l1_usd"])
    sw["price_osmo_usd"] = sw["day"].map(out["price_osmo_usd"])
    sw["usd_value"] = sw["vol_l1"] * sw["price_l1_usd"]
    cols = [
        "ts",
        "block_height",
        "tx_hash",
        "sender",
        "sell_l1",
        "vol_l1",
        "vol_osmo",
        "price_l1_osmo" if "price_l1_osmo" in sw else "price_osmo",
        "price_l1_usd",
        "price_osmo_usd",
        "usd_value",
    ]
    ex_out = pd.DataFrame(
        {
            "timestamp": sw["ts"].dt.strftime("%Y-%m-%dT%H:%M:%SZ"),
            "block_height": sw["block_height"],
            "tx_hash": sw["tx_hash"],
            "sender": sw["sender"],
            "side": np.where(sw.sell_l1, "SELL_L1", "BUY_L1"),
            "amount_l1": sw["vol_l1"],
            "amount_osmo": sw["vol_osmo"],
            "price_osmo_per_l1": sw["price_osmo"],
            "price_l1_usd": sw["price_l1_usd"],
            "price_osmo_usd": sw["price_osmo_usd"],
            "usd_value": sw["usd_value"],
        }
    )
    ex_out.to_csv(f"{BASE}/analysis/swaps_with_usd.csv", index=False)
    print("-> analysis/swaps_with_usd.csv")

for nm, dd, col in (("in", ib_in, "l1_bridged_in"), ("out", ib_out, "l1_bridged_out")):
    if dd is not None:
        dd["price_l1_usd"] = dd["day"].map(out["price_l1_usd"])
        dd["usd_value"] = dd["amt_h"] * dd["price_l1_usd"]
        dd.rename(
            columns={
                "ts": "timestamp",
                "amt_h": "amount_l1",
                "src_channel": "src_channel",
                "dst_channel": "dst_channel",
                "sender": "sender",
                "receiver": "receiver",
                "tx_hash": "tx_hash",
            }
        ).loc[
            :,
            [
                c
                for c in [
                    "timestamp",
                    "tx_hash",
                    "sender",
                    "receiver",
                    "src_channel",
                    "dst_channel",
                    "amount_l1",
                    "price_l1_usd",
                    "usd_value",
                ]
                if c in dd.columns
            ],
        ].to_csv(f"{BASE}/analysis/bridge_L1_{nm}_usd.csv", index=False)
print("-> analysis/bridge_L1_*_usd.csv")

# ---------------- parquet ----------------
os.makedirs(f"{BASE}/raw_parquet", exist_ok=True)
for p in glob.glob(f"{BASE}/*.csv"):
    n = os.path.splitext(os.path.basename(p))[0]
    pd.read_csv(p, dtype=str).to_parquet(f"{BASE}/raw_parquet/{n}.parquet", index=False)
print("parquet -> raw_parquet/")

# ---------------- dashboard ----------------
os.makedirs(f"{BASE}/viz", exist_ok=True)
d = out
fig = make_subplots(
    rows=4,
    cols=2,
    vertical_spacing=0.07,
    horizontal_spacing=0.08,
    specs=[[{"secondary_y": True}, {}], [{}, {}], [{}, {}], [{}, {}]],
    subplot_titles=(
        "L1 price (USD &amp; OSMO)",
        "Daily volume (USDC)",
        "Pool TVL (USD)",
        "Pool composition (USD)",
        "Cumulative LP flow (USD)",
        "Bridge flow (USD, L1)",
        "Trades &amp; unique traders",
        "L1 share of pool USD",
    ),
)
fig.add_trace(
    go.Scatter(
        x=d.index, y=d["price_l1_usd"], name="L1 USD", line=dict(color="#2563eb")
    ),
    1,
    1,
)
fig.add_trace(
    go.Scatter(
        x=d.index,
        y=d["price_l1_osmo_close"],
        name="L1 in OSMO",
        line=dict(color="#f59e0b"),
    ),
    1,
    1,
    secondary_y=True,
)
fig.add_trace(
    go.Bar(x=d.index, y=d["volume_usdc"], name="volume USD", marker_color="#10b981"),
    1,
    2,
)
fig.add_trace(
    go.Scatter(
        x=d.index,
        y=d["tvl_usd_close"],
        name="TVL",
        fill="tozeroy",
        line=dict(color="#6366f1"),
    ),
    2,
    1,
)
fig.add_trace(
    go.Scatter(
        x=d.index,
        y=d["l1_usd_close"],
        name="L1",
        stackgroup="c",
        line=dict(color="#2563eb"),
    ),
    2,
    2,
)
fig.add_trace(
    go.Scatter(
        x=d.index,
        y=d["osmo_usd_close"],
        name="OSMO",
        stackgroup="c",
        line=dict(color="#f59e0b"),
    ),
    2,
    2,
)
fig.add_trace(
    go.Scatter(
        x=d.index,
        y=d["lp_net_usd"].cumsum(),
        name="cum net LP USD",
        line=dict(color="#ef4444"),
    ),
    3,
    1,
)
fig.add_trace(
    go.Scatter(
        x=d.index,
        y=d["l1_bridged_in_usd"],
        name="L1 in USD",
        line=dict(color="#0ea5e9"),
    ),
    3,
    2,
)
fig.add_trace(
    go.Scatter(
        x=d.index,
        y=-d["l1_bridged_out_usd"],
        name="L1 out USD",
        line=dict(color="#dc2626"),
    ),
    3,
    2,
)
fig.add_trace(
    go.Bar(x=d.index, y=d["trades"], name="trades", marker_color="#94a3b8"), 4, 1
)
fig.add_trace(
    go.Scatter(
        x=d.index, y=d["unique_traders"], name="traders", line=dict(color="#111827")
    ),
    4,
    1,
)
fig.add_trace(
    go.Scatter(x=d.index, y=d["l1_share"], name="L1 share", line=dict(color="#7c3aed")),
    4,
    2,
)
fig.update_layout(
    height=1500,
    template="plotly_white",
    barmode="overlay",
    title="GenesisL1 (L1) / OSMO — pool 732 on Osmosis (USD, full history)",
    legend=dict(orientation="h", y=-0.03),
)
fig.update_xaxes(rangeslider_visible=False)
fig.write_html(f"{BASE}/viz/l1_osmo_dashboard.html", include_plotlyjs="cdn")
print(
    f"dashboard -> viz/l1_osmo_dashboard.html ({os.path.getsize(BASE + '/viz/l1_osmo_dashboard.html') / 1e3:.0f} KB)"
)

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

fig2, ax = plt.subplots(3, 1, figsize=(13, 11), sharex=True)
ax[0].bar(d.index, d["volume_usdc"], color="#10b981", width=1.0)
ax[0].set_ylabel("daily volume (USDC)")
ax[1].plot(d.index, d["tvl_usd_close"], color="#6366f1")
ax[1].set_ylabel("TVL (USDC)")
ax[2].plot(d.index, d["price_l1_usd"], color="#2563eb", label="L1 USD")
ax[2].set_ylabel("L1 price (USD)")
ax[2].legend()
ax[0].set_title("GenesisL1 (L1)/OSMO pool 732 — Osmosis")
plt.tight_layout()
plt.savefig(f"{BASE}/viz/l1_osmo_overview.png", dpi=120)
print("png -> viz/l1_osmo_overview.png")
print("BUILD OK")
