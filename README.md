# GenesisL1 (L1) / OSMO on Osmosis — pool 732

Full historical trading & liquidity report for the only OSMO/L1 pair on Osmosis, USD-denominated,
over the whole data window (2021-09-24 → 2026-10-06).

**Read the report:** <https://cordtus.github.io/l1-osmo-report/> (also [`index.html`](index.html) · [`PDF`](l1-osmo-report.pdf))

Headline: **$1,052,077** lifetime volume · **40,856** trades by **5,873** wallets · current TVL
**~$15,906** · **$449,647** bridged in / **$590,295** out. See [`MANIFEST.md`](MANIFEST.md) for
provenance, method, table inventory and caveats.

## Repository layout

| path | what |
|---|---|
| `index.html` | self-contained report (charts inlined; opens offline) |
| `l1-osmo-report.pdf` | 8-page PDF of the same report |
| `data/l1-osmo-full.csv` | consolidated daily metrics — the report's dataset |
| `data/raw/` | raw tables as pulled from Numia BigQuery (3 largest gzipped) |
| `data/parquet/` | the same raw tables, typed Parquet |
| `data/analysis/` | derived tables (trade-level USD, bridge in/out flows) |
| `viz/l1_osmo_dashboard.html` | interactive Plotly dashboard |
| `scripts/` | `build.py` (aggregation), `make_report.py` (report/figures) |

## Rebuild

`scripts/` holds the exact generators used, in run order:

```bash
python3 scripts/build.py       # raw CSVs + Parquet -> data/l1-osmo-full.csv, analysis/*, viz dashboard
python3 scripts/make_report.py # analysis/* -> index.html, l1-osmo-report.pdf, charts/
```

Both have `BASE` hard-coded to the original flat working directory; point it at a checkout of
`data/raw/` laid out flat (`.gz` files ungzipped) before running.

## License / attribution

Data © [Numia](https://numia.xyz); redistribution subject to their terms. Figures are derived from
on-chain indexed data and provided as-is.
