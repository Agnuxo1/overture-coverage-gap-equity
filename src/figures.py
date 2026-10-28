"""Figures and animated GIFs for the README (assets/)."""
import sys
from pathlib import Path

import geopandas as gpd
import imageio.v2 as imageio
import matplotlib
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

matplotlib.use("Agg")
sys.path.insert(0, str(Path(__file__).parent))
from model import PARAMS, REGIONS, ROOT, load_features, predict  # noqa: E402

ASSETS = ROOT / "assets"
BG, FG, MUTED = "#0d1117", "#e6edf3", "#8b949e"
CMAP = "magma_r"
NAMES = {"eastern-ok": "Eastern Oklahoma", "maricopa-az": "Maricopa County, AZ",
         "northern-ca": "Northern California", "south-central-tx": "South-Central Texas"}
plt.rcParams.update({"font.family": "DejaVu Sans", "text.color": FG, "axes.labelcolor": FG,
                     "xtick.color": MUTED, "ytick.color": MUTED, "axes.edgecolor": MUTED})


def frame(fig):
    fig.canvas.draw()
    img = np.asarray(fig.canvas.buffer_rgba())[..., :3].copy()
    plt.close(fig)
    return img


def save_gif(frames, name, fps=1.0):
    ASSETS.mkdir(exist_ok=True)
    h = min(f.shape[0] for f in frames); w = min(f.shape[1] for f in frames)
    imageio.mimsave(ASSETS / name, [f[:h, :w] for f in frames], duration=1000 / fps, loop=0)


def geo(region, values, col):
    g = gpd.read_parquet(ROOT / "data" / "geo" / f"{region}.parquet")
    return g.merge(values[["GEOID", col]], on="GEOID", how="inner")


def map_frame(region, df, col, title, vmax=0.6, cmap=CMAP, label="coverage gap score"):
    fig, ax = plt.subplots(figsize=(8, 6.4), dpi=90, facecolor=BG)
    ax.set_facecolor(BG); ax.set_axis_off()
    g = geo(region, df, col)
    g.plot(column=col, ax=ax, cmap=cmap, vmin=0, vmax=vmax, linewidth=0.05, edgecolor=BG)
    sm = plt.cm.ScalarMappable(cmap=cmap, norm=plt.Normalize(0, vmax))
    cb = fig.colorbar(sm, ax=ax, fraction=0.035, pad=0.01); cb.set_label(label, color=FG)
    cb.ax.yaxis.set_tick_params(color=MUTED)
    fig.suptitle(title, color=FG, fontsize=15, fontweight="bold", y=0.97)
    ax.set_title(f"{NAMES[region]} · {len(g):,} tracts", color=MUTED, fontsize=11)
    return frame(fig)


def gif_regions(pred):
    frames = [map_frame(r, pred, "coverage_gap_score", "Predicted Overture coverage gap") for r in REGIONS]
    save_gif(frames, "regions_coverage_gap.gif", fps=0.7)


def gif_components(pred):
    frames = []
    for r in ("eastern-ok", "northern-ca"):
        for col, lab in (("transport_gap", "Road-network gap"), ("building_gap", "Building gap"),
                         ("poi_gap", "POI gap"), ("coverage_gap_score", "Composite score")):
            frames.append(map_frame(r, pred, col, lab, vmax=0.8 if col != "building_gap" else 0.15))
    save_gif(frames, "components_build_up.gif", fps=0.8)


def gif_provenance(f):
    d = f.assign(osm_share=f.ov_bld_osm / f.ov_bld.clip(lower=1))
    frames = [map_frame(r, d, "osm_share", "Share of Overture buildings sourced from OpenStreetMap",
                        vmax=1.0, cmap="viridis", label="OSM share (rest = ML footprints)") for r in REGIONS]
    save_gif(frames, "building_provenance.gif", fps=0.7)


def gif_strata_bars():
    t = pd.read_csv(ROOT / "results" / "discovery_provenance_by_tribal.csv")
    frames = []
    metrics = [("osm_share", "Buildings from OSM"), ("height_share", "Buildings with height"),
               ("places_per_1k_pop", "Places per 1k residents"), ("fire_per_1k_km2", "Fire stations per 1,000 km²")]
    for m, lab in metrics:
        fig, ax = plt.subplots(figsize=(8, 5), dpi=90, facecolor=BG); ax.set_facecolor(BG)
        piv = t.pivot(index="region", columns="tribal", values=m).reindex(list(REGIONS))
        x = np.arange(len(piv)); w = 0.38
        ax.bar(x - w / 2, piv.get("non-tribal", 0), w, color="#58a6ff", label="non-tribal")
        ax.bar(x + w / 2, piv.get("tribal", 0), w, color="#f78166", label="tribal")
        ax.set_xticks(x, [NAMES[r].replace(" ", "\n", 1) for r in piv.index], fontsize=9)
        ax.set_title(lab + " — tribal vs non-tribal tracts", color=FG, fontsize=13, fontweight="bold")
        ax.legend(facecolor=BG, edgecolor=MUTED, labelcolor=FG)
        for s in ("top", "right"): ax.spines[s].set_visible(False)
        frames.append(frame(fig))
    save_gif(frames, "tribal_strata_bars.gif", fps=0.6)


def gif_pipeline():
    steps = ["Overture 2026-08-19.0\nbuildings · roads · places", "Per-tract aggregation\n(STRtree, EPSG:5070)",
             "Expected reference\nfrom permitted signals", "Defined-component\nmean (organiser rule)",
             "Coverage gap score\n+ bias scorecard"]
    frames = []
    for k in range(1, len(steps) + 2):
        fig, ax = plt.subplots(figsize=(10, 3.2), dpi=90, facecolor=BG); ax.set_facecolor(BG); ax.set_axis_off()
        ax.set_xlim(0, len(steps)); ax.set_ylim(0, 1)
        for i, s in enumerate(steps):
            on = i < k
            ax.add_patch(plt.Rectangle((i + 0.06, 0.25), 0.88, 0.5, color="#238636" if on else "#21262d",
                                       ec="#3fb950" if on else MUTED, lw=1.5))
            ax.text(i + 0.5, 0.5, s, ha="center", va="center", fontsize=9, color=FG if on else MUTED)
            if i < len(steps) - 1:
                ax.annotate("", (i + 1.06, 0.5), (i + 0.94, 0.5),
                            arrowprops=dict(arrowstyle="->", color="#3fb950" if i + 1 < k else MUTED))
        ax.set_title("Rule-compliant pipeline: removed reference layers are never read", color=FG, fontsize=12)
        frames.append(frame(fig))
    save_gif(frames, "pipeline.gif", fps=1.2)


def fig_experiments():
    e = pd.read_csv(ROOT / "experiments" / "experiments.csv")
    e = e[pd.to_numeric(e.public_rmse, errors="coerce").notna()]
    if e.empty:
        return
    e["public_rmse"] = e.public_rmse.astype(float)
    frames = []
    for k in range(1, len(e) + 1):
        fig, ax = plt.subplots(figsize=(8, 4.2), dpi=90, facecolor=BG); ax.set_facecolor(BG)
        s = e.iloc[:k]
        ax.plot(range(k), s.public_rmse, "o-", color="#58a6ff")
        ax.plot(range(k), s.public_rmse.cummin(), "--", color="#3fb950", label="best so far")
        ax.set_xticks(range(len(e)), e.id, rotation=45, fontsize=8); ax.set_xlim(-0.5, len(e) - 0.5)
        ax.set_ylim(e.public_rmse.min() * 0.95, e.public_rmse.max() * 1.05)
        ax.set_ylabel("public RMSE (lower is better)")
        ax.set_title("Hypothesis-driven leaderboard experiments", color=FG, fontsize=13, fontweight="bold")
        ax.legend(facecolor=BG, edgecolor=MUTED, labelcolor=FG)
        for sp in ("top", "right"): ax.spines[sp].set_visible(False)
        frames.append(frame(fig))
    save_gif(frames, "experiments.gif", fps=1.0)


if __name__ == "__main__":
    f = load_features()
    pred = predict(f, PARAMS)
    gif_pipeline(); gif_regions(pred); gif_components(pred); gif_provenance(f)
    if (ROOT / "results" / "discovery_provenance_by_tribal.csv").exists():
        gif_strata_bars()
    fig_experiments()
    print(sorted(p.name for p in ASSETS.iterdir()))
