# GenesisL1 (L1) / OSMO — Osmosis trading activity dataset

**What this is.** A complete, self-contained extract of the trading, liquidity and bridge activity of the
GenesisL1 native token (`el1`, chain `genesis_29-2`) against OSMO on Osmosis — GAMM pool **732**, the only
OSMO/L1 pair — with USD valuation across the full available history.

## Token identity on Osmosis

| field | value |
|---|---|
| Osmosis IBC denom | `ibc/F16FDC11A7662B86BC0B9CE61871CBACF7C20606F95E86260FD38915184B75B4` |
| trace path | `transfer/channel-253/el1` |
| channel pair | genesisl1 `channel-1` / `connection-1` ↔ osmosis `channel-253` / `connection-1539` |
| symbol / exponent | `L1` / 18 |
| prior denom | `ibc/DABCB5B2…7775` (`transfer/channel-235`) — live 2022-05-05→2022-05-31, never in pool 732 |

## Source & method

- **Data:** Numia public BigQuery `numia-data.osmosis` (EU), queried through the BigQuery **sandbox** via the
  REST API. No billing, no Cloud Storage. Filtered to `pool_id='732'` / the L1 denom, then paged to local CSV.
- **Denom/channel:** verified against `https://rpc.archive.osmosis.zone`.
- **USD across the full range:** Numia's `pools_volume` gives per-minute USD volume from the pool's first
  trade (2022-06-06); dividing by swap token volume recovers USD prices. The derived price matches Numia's
  independent liquidity-snapshot price to ~1% (median) where both exist, and extends USD valuation back to
  2022-06-06. TVL/USD liquidity itself only exists from 2023-11-16.

## Deliverables

| path | what |
|---|---|
| `index.html` | self-contained HTML report (charts inlined) |
| `l1-osmo-report.pdf` | 8-page report: context + 11 visualizations + monthly table |
| `data/l1-osmo-full.csv` | consolidated daily metrics, USD-denominated (the report's dataset) |
| `data/raw/` | raw CSVs as pulled (3 largest gzipped, `.csv.gz`) |
| `data/parquet/` | the same raw tables typed as Parquet |
| `data/analysis/` | derived tables (trade-level USD, bridge flows) |
| `viz/l1_osmo_dashboard.html` | interactive Plotly dashboard |
| `scripts/` | `build.py`, `make_report.py` |
| `MANIFEST.md` | this file |

The standalone tarballs (`l1-osmo-raw.tar.gz`, `l1-osmo-package.tar.gz`) are redundant with the tree above
and exceed GitHub's 100 MB per-file limit, so they are not committed.

## Raw tables (`data/raw/`)

`swaps_pool732.csv`, `pools_volume_732.csv` and `pools_liquidity_732.csv` are stored gzipped
(`.csv.gz`); the rest are plain CSV.

| file | rows | coverage | contents |
|---|---:|---|---|
| `swaps_pool732.csv` | 40,856 | 2022-06-06 → 2026-10-06 | every swap (amount in/out, denoms, sender, tx) |
| `pools_volume_732.csv` | 2,303,926 | 2021-09-24 → now (non-zero 2022-06-06 →) | per-minute USD volume |
| `pools_liquidity_732.csv` | 3,040,998 | 2023-11-16 → now | per-minute per-token liquidity (flattened) |
| `lp_gamm_join_pool_732.csv` | 712 | 2022-06-06 → 2026-09-29 | LP deposits |
| `lp_gamm_exit_pool_732.csv` | 662 | 2022-06-06 → 2026-09-29 | LP withdrawals |
| `ics20_transfer_L1.csv` | 2,134 | 2022-06-01 → now | L1 leaving Osmosis |
| `ics20_receive_L1.csv` | 8,660 | 2022-06-01 → now | L1 arriving on Osmosis |
| `asset_denoms.csv` | 3,750 | — | denom↔symbol dictionary |

Derived: `data/l1-osmo-full.csv` (USD daily metrics), `data/analysis/swaps_with_usd.csv`
(trade-level USD value), `data/analysis/bridge_L1_{in,out}_usd.csv`; typed Parquet in `data/parquet/`.

## Headline numbers

- Lifetime volume **$1,052,077**; **40,856** trades by **5,873** wallets
- Current TVL **~$15,906**; L1 ≈ **$0.228 / 6.16 OSMO**
- L1 bridged in/out (USD) **$449,647 / $590,295**
- LP value flow: deposits **$75,600**, withdrawals **$72,094**, net **+$3,506**

## Caveats

- Swap/LP `token_amount*` are `FLOAT`; 18-decimal L1 loses low-order precision. Use `ics20_*`
  (`BIGNUMERIC`) for exact amounts.
- USD prices before 2023-11-16 are derived (7-day-median smoothed) estimates.
- TVL/USD liquidity has no source before 2023-11-16.
- `osmosis_lock_tokens` / `osmosis_superfluid_staking` are broken upstream (backing `lf-data` tables 404).
- Numia is migrating Osmosis data from BigQuery to ObsessionDB; this is a point-in-time snapshot.
- Data © Numia; redistribution subject to Numia's terms.
