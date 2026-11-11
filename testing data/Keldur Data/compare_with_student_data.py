"""Compare the LoRa sensor nodes at Keldur with the data received from the
Department of Civil and Environmental Engineering (HI) project sensors.

Outputs (all derived from the two measured datasets, nothing synthetic):
  plots_student_comparison/*.png      figures used in the thesis
  plots_student_comparison/*.csv      statistics quoted in the text
"""
from __future__ import annotations

from pathlib import Path

import matplotlib.dates as mdates
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
XLSX = HERE / "Keldur Data from another thesis student.xlsx"
OUT = HERE / "plots_student_comparison"
OUT.mkdir(exist_ok=True)

# Day after burial: ADC readings drop from air-like values at ~15:00 UTC on 17 Oct.
START = pd.Timestamp("2025-10-18 00:00")
END = pd.Timestamp("2026-01-27 12:00")  # last record of the other dataset

NODES = [1, 3, 5, 7]
NODE_DEPTH_MM = {1: 80, 3: 60, 5: 65, 7: 85}
NODE_EXPOSED = {1: False, 3: False, 5: True, 7: True}
NODE_COLOR = {1: "#0072B2", 3: "#E69F00", 5: "#009E73", 7: "#D55E00"}

# (sheet, label, depth_mm) from the 'Sensor placement' diagram (depths given in cm there).
THEIR_SOIL = {
    "Inside turf 93": ("#93 upper-outer", 20),
    "Inside turf 94": ("#94 upper-inner", 105),
    "Inside turf 95": ("#95 lower-outer", 15),
    "Inside turf 96": ("#96 lower-inner", 240),
}
THEIR_COLOR = {"#93": "#6A3D9A", "#94": "#CAB2D6", "#95": "#B15928", "#96": "#000000"}
THEIR_AIR = {"Air outside": "Project outside air (#34)", "Air inside": "Project inside air (#33)"}

plt.rcParams.update(
    {
        "figure.dpi": 150,
        "savefig.dpi": 250,
        "font.family": "DejaVu Sans",
        "font.size": 10,
        "axes.titlesize": 11,
        "axes.labelsize": 10,
        "legend.fontsize": 8.5,
        "axes.grid": True,
        "grid.alpha": 0.35,
        "grid.linestyle": "--",
        "axes.spines.top": False,
        "axes.spines.right": False,
    }
)


# ---------------------------------------------------------------- loading
def load_mine() -> dict[int, pd.DataFrame]:
    out = {}
    for n in NODES:
        f = pd.read_csv(HERE / f"feeds{n}.csv", parse_dates=["created_at"])
        f["created_at"] = f["created_at"].dt.tz_convert("UTC").dt.tz_localize(None)
        f = f[f["field5"] > 0].copy()  # all-zero placeholder rows have battery = 0
        d = pd.DataFrame(
            {
                "air_t": f["field1"].where(f["field1"] != 0),
                "rh": f["field2"].where(f["field2"] != 0),
                "soil_t": f["field3"].where(f["field3"] != 0),
                "adc": f["field4"].where(f["field4"] > 0),
            }
        )
        d.index = f["created_at"]
        d = d.loc[START:END].resample("1h").mean()
        out[n] = d
    return out


def load_theirs() -> tuple[dict[str, pd.DataFrame], dict[str, pd.DataFrame]]:
    sheets = pd.read_excel(XLSX, sheet_name=None)
    soil, air = {}, {}
    for name, df in sheets.items():
        if name == "Sensor placement":
            continue
        df = df.copy()
        df.columns = [c.strip() for c in df.columns]
        df = df.set_index(df.columns[0]).sort_index().loc[START:END]
        if name.startswith("Inside turf"):
            df = df.rename(columns={"DE Perm , Ea": "perm", "Temperature , °C": "soil_t"})
            soil[name] = df[["perm", "soil_t"]].resample("1h").mean()
        else:
            df = df.rename(columns={"Temperature (°C)": "air_t", "RH (%)": "rh"})
            air[name] = df[["air_t", "rh"]].resample("1h").mean()
    return soil, air


mine = load_mine()
t_soil, t_air = load_theirs()


def short(sheet: str) -> str:
    return THEIR_SOIL[sheet][0].split()[0]


def daily_mean(s: pd.Series, min_hours: int = 12) -> pd.Series:
    g = s.resample("1D")
    return g.mean().where(g.count() >= min_hours)


def daily_range(s: pd.Series, min_hours: int = 20) -> pd.Series:
    g = s.resample("1D")
    return (g.max() - g.min()).where(g.count() >= min_hours)


def spearman(a: pd.Series, b: pd.Series) -> float:
    # scipy is not installed in the venv: Spearman = Pearson on ranks
    return a.rank().corr(b.rank())


def fmt_dates(ax):
    loc = mdates.MonthLocator()
    ax.xaxis.set_major_locator(loc)
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%d %b %Y"))
    ax.set_xlim(START, END)


def corr_stats(a: pd.Series, b: pd.Series) -> dict:
    d = pd.concat([a, b], axis=1, keys=["a", "b"]).dropna()
    if len(d) < 24:
        return dict(n=len(d), r=np.nan, bias=np.nan, rmse=np.nan)
    diff = d["a"] - d["b"]
    return dict(
        n=len(d),
        r=d["a"].corr(d["b"]),
        bias=diff.mean(),
        rmse=float(np.sqrt((diff**2).mean())),
    )


# ---------------------------------------------------------------- Fig 1: coverage
def fig_coverage():
    fig, ax = plt.subplots(figsize=(7.2, 3.3))
    rows = []
    for n in NODES:
        rows.append((f"Node {n}", NODE_COLOR[n], mine[n]["soil_t"].dropna().index))
    for sheet, (lab, _) in THEIR_SOIL.items():
        rows.append((f"Project {lab.split()[0]}", THEIR_COLOR[lab.split()[0]], t_soil[sheet]["soil_t"].dropna().index))
    for i, (lab, col, idx) in enumerate(rows):
        days = pd.Series(1, index=idx).resample("1D").count()
        days = days[days >= 1].index
        ax.broken_barh([(mdates.date2num(d), 1) for d in days], (i - 0.35, 0.7), facecolors=col, linewidth=0)
    ax.set_yticks(range(len(rows)))
    ax.set_yticklabels([r[0] for r in rows])
    ax.invert_yaxis()
    ax.axhline(3.5, color="0.4", lw=0.8)
    ax.xaxis_date()
    fmt_dates(ax)
    ax.grid(axis="y", visible=False)
    fig.tight_layout()
    fig.savefig(OUT / "cmp_coverage.png")
    plt.close(fig)


# ---------------------------------------------------------------- Fig 2/3: air temp and RH
def fig_air(var: str, ylabel: str, fname: str, title: str):
    fig, axes = plt.subplots(2, 1, figsize=(7.2, 6.0), sharex=True, sharey=True)
    groups = [(axes[0], [1, 3], "(a) Developed nodes with enclosed sensors (1, 3)"),
              (axes[1], [5, 7], "(b) Developed nodes with exposed sensors (5, 7)")]
    for ax, nodes, ttl in groups:
        ax.plot(daily_mean(t_air["Air outside"][var]), color="0.15", lw=1.6, label=THEIR_AIR["Air outside"])
        ax.plot(daily_mean(t_air["Air inside"][var]), color="0.55", lw=1.6, ls="--", label=THEIR_AIR["Air inside"])
        for n in nodes:
            ax.plot(daily_mean(mine[n][{"air_t": "air_t", "rh": "rh"}[var]]), color=NODE_COLOR[n], lw=1.2, label=f"Node {n}")
        ax.set_ylabel(ylabel)
        ax.set_title(ttl, loc="left")
        if var == "air_t":
            ax.set_ylim(-12, 10)
            ax.legend(ncol=4, loc="lower center")
        else:
            ax.legend(ncol=2, loc="lower right")
    fmt_dates(axes[1])
    fig.tight_layout()
    fig.savefig(OUT / fname)
    plt.close(fig)


# ---------------------------------------------------------------- Fig 4: soil temperature
def fig_air_simple():
    fig, axes = plt.subplots(2, 1, figsize=(7.2, 5.6), sharex=True)
    for ax, var, yl in [(axes[0], "air_t", "Daily mean air\ntemperature (°C)"),
                        (axes[1], "rh", "Daily mean relative\nhumidity (%)")]:
        ax.plot(daily_mean(t_air["Air outside"][var]), color="0.15", lw=1.8, label="Project outside sensor")
        for n in NODES:
            ax.plot(daily_mean(mine[n][var]), color=NODE_COLOR[n], lw=1.2,
                    ls="--" if not NODE_EXPOSED[n] else "-",
                    label=f"Node {n} ({'exposed' if NODE_EXPOSED[n] else 'enclosed'})")
        ax.set_ylabel(yl)
        ax.legend(ncol=3, loc="lower center" if var == "air_t" else "lower right")
    axes[0].set_ylim(-14, 9)
    axes[1].set_ylim(25, 103)
    axes[0].set_title("(a) Air temperature", loc="left")
    axes[1].set_title("(b) Relative humidity", loc="left")
    fmt_dates(axes[1])
    fig.tight_layout()
    fig.savefig(OUT / "cmp_air_rh_simple.png")
    plt.close(fig)


# ---------------------------------------------------------------- Fig 4: soil temperature
def fig_soil_temp():
    fig, axes = plt.subplots(2, 1, figsize=(7.2, 6.0), sharex=True, sharey=True)
    for n in NODES:
        axes[0].plot(daily_mean(mine[n]["soil_t"]), color=NODE_COLOR[n], lw=1.3,
                     label=f"Node {n} ({NODE_DEPTH_MM[n]} mm)")
    for sheet, (lab, depth) in THEIR_SOIL.items():
        k = lab.split()[0]
        axes[1].plot(daily_mean(t_soil[sheet]["soil_t"]), color=THEIR_COLOR[k], lw=1.3,
                     label=f"{lab} ({depth} mm)")
    axes[0].set_title("(a) Developed nodes (four roofs)", loc="left")
    axes[1].set_title("(b) Project soil sensors (one roof)", loc="left")
    for ax in axes:
        ax.set_ylabel("Daily mean soil temperature (°C)")
        ax.axhline(0, color="0.6", lw=0.8)
        ax.legend(ncol=2, loc="upper right")
    fmt_dates(axes[1])
    fig.tight_layout()
    fig.savefig(OUT / "cmp_soil_temp_daily.png")
    plt.close(fig)


def best_week() -> tuple[pd.Timestamp, pd.Timestamp]:
    cols = [mine[n]["soil_t"] for n in NODES] + [t_soil[s]["soil_t"] for s in THEIR_SOIL]
    ok = pd.concat(cols, axis=1).notna().all(axis=1).astype(float)
    cov = ok.rolling(24 * 7).mean()
    end = cov.idxmax()
    return end - pd.Timedelta(days=7), end


def fig_week(week):
    a, b = week
    fig, axes = plt.subplots(2, 1, figsize=(7.2, 5.6), sharex=True, sharey=True)
    for n in NODES:
        axes[0].plot(mine[n]["soil_t"].loc[a:b], color=NODE_COLOR[n], lw=1.3, label=f"Node {n} ({NODE_DEPTH_MM[n]} mm)")
    for sheet, (lab, depth) in THEIR_SOIL.items():
        k = lab.split()[0]
        axes[1].plot(t_soil[sheet]["soil_t"].loc[a:b], color=THEIR_COLOR[k], lw=1.3, label=f"{lab} ({depth} mm)")
    axes[0].set_title("(a) Developed nodes", loc="left")
    axes[1].set_title("(b) Project soil sensors", loc="left")
    for ax in axes:
        ax.set_ylabel("Soil temperature (°C)")
        ax.set_ylim(-3.8, 3.0)
        ax.legend(ncol=2, loc="lower left")
    axes[1].xaxis.set_major_locator(mdates.DayLocator())
    axes[1].xaxis.set_major_formatter(mdates.DateFormatter("%d %b"))
    axes[1].set_xlim(a, b)
    fig.tight_layout()
    fig.savefig(OUT / "cmp_soil_temp_week.png")
    plt.close(fig)


# ---------------------------------------------------------------- Fig 5: damping vs depth
def fig_damping() -> pd.DataFrame:
    rows = []
    for n in NODES:
        r = daily_range(mine[n]["soil_t"])
        rows.append(("mine", f"Node {n}", NODE_DEPTH_MM[n], r.median(), r.quantile(.25), r.quantile(.75), r.count(), NODE_COLOR[n]))
    for sheet, (lab, depth) in THEIR_SOIL.items():
        r = daily_range(t_soil[sheet]["soil_t"])
        rows.append(("theirs", lab.split()[0], depth, r.median(), r.quantile(.25), r.quantile(.75), r.count(), THEIR_COLOR[lab.split()[0]]))
    d = pd.DataFrame(rows, columns=["who", "label", "depth_mm", "median", "q25", "q75", "days", "color"])
    d.drop(columns="color").to_csv(OUT / "stats_daily_range.csv", index=False)

    offsets = {"Node 3": (-12, 8), "Node 5": (-14, -16), "Node 7": (8, 6), "Node 1": (8, -12)}
    fig, ax = plt.subplots(figsize=(6.4, 4.0))
    for _, r in d.iterrows():
        mk = "o" if r.who == "mine" else "s"
        ax.errorbar(r.depth_mm, r["median"], yerr=[[r["median"] - r.q25], [r.q75 - r["median"]]],
                    fmt=mk, ms=8, color=r.color, mec="k", capsize=3, lw=1.2, zorder=3)
        ax.annotate(r.label, (r.depth_mm, r["median"]), textcoords="offset points",
                    xytext=offsets.get(r.label, (7, 5)), fontsize=8.5)
    ax.plot([], [], "o", color="0.7", mec="k", label="Developed nodes")
    ax.plot([], [], "s", color="0.7", mec="k", label="Project sensors")
    ax.set_ylim(-0.12, None)
    ax.set_xlabel("Depth below turf surface (mm)")
    ax.set_ylabel("Median daily temperature range (°C)")
    ax.legend(loc="upper right")
    fig.tight_layout()
    fig.savefig(OUT / "cmp_damping_depth.png")
    plt.close(fig)
    return d


# ---------------------------------------------------------------- Fig 6: correlation heatmap
def fig_heatmap() -> pd.DataFrame:
    m = pd.DataFrame({f"Node {n}": daily_mean(mine[n]["soil_t"]) for n in NODES})
    t = pd.DataFrame({short(s): daily_mean(t_soil[s]["soil_t"]) for s in THEIR_SOIL})
    r = pd.DataFrame(index=m.columns, columns=t.columns, dtype=float)
    cnt = r.copy()
    bias = r.copy()
    for a in m.columns:
        for b in t.columns:
            d = pd.concat([m[a], t[b]], axis=1).dropna()
            r.loc[a, b] = d.iloc[:, 0].corr(d.iloc[:, 1]) if len(d) > 10 else np.nan
            cnt.loc[a, b] = len(d)
            bias.loc[a, b] = (d.iloc[:, 0] - d.iloc[:, 1]).mean() if len(d) > 10 else np.nan
    r.to_csv(OUT / "stats_soil_temp_corr_daily.csv")
    cnt.to_csv(OUT / "stats_soil_temp_corr_days.csv")
    bias.to_csv(OUT / "stats_soil_temp_bias_daily.csv")

    fig, ax = plt.subplots(figsize=(5.6, 3.8))
    im = ax.imshow(r.values.astype(float), vmin=0, vmax=1, cmap="viridis", aspect="auto")
    ax.set_xticks(range(len(t.columns)))
    ax.set_xticklabels([f"{c}\n({THEIR_SOIL[s][1]} mm)" for c, s in zip(t.columns, THEIR_SOIL)])
    ax.set_yticks(range(len(m.columns)))
    ax.set_yticklabels([f"{c} ({NODE_DEPTH_MM[int(c.split()[1])]} mm)" for c in m.columns])
    for i in range(r.shape[0]):
        for j in range(r.shape[1]):
            v = r.values[i, j]
            ax.text(j, i, f"{v:.2f}" if np.isfinite(v) else "n/a", ha="center", va="center",
                    color="w" if (np.isfinite(v) and v < 0.6) else "k", fontsize=10)
    ax.grid(False)
    ax.spines[:].set_visible(False)
    fig.colorbar(im, ax=ax, label="Pearson r")
    fig.tight_layout()
    fig.savefig(OUT / "cmp_soil_temp_corr.png")
    plt.close(fig)
    return r


# ---------------------------------------------------------------- Fig 7: moisture trend
def fig_moisture() -> pd.DataFrame:
    def z(s):
        return (s - s.mean()) / s.std()

    fig, axes = plt.subplots(2, 1, figsize=(7.2, 6.0), sharex=True, sharey=True)
    moist_nodes = [1, 3, 7]  # Node 5 ADC saturates at 768 for most of the record
    for n in moist_nodes:
        axes[0].plot(z(-daily_mean(mine[n]["adc"])), color=NODE_COLOR[n], lw=1.3, label=f"Node {n} (−ADC)")
    for sheet, (lab, depth) in THEIR_SOIL.items():
        k = lab.split()[0]
        axes[1].plot(z(daily_mean(t_soil[sheet]["perm"])), color=THEIR_COLOR[k], lw=1.3, label=f"{lab} (ε)")
    axes[0].set_title("(a) Developed nodes (raw ADC, inverted: up = wetter)", loc="left")
    axes[1].set_title("(b) Project sensors (dielectric permittivity: up = wetter)", loc="left")
    for ax in axes:
        ax.set_ylabel("Standardised daily mean (z-score)")
        ax.legend(ncol=2, loc="lower right")
    fmt_dates(axes[1])
    fig.tight_layout()
    fig.savefig(OUT / "cmp_moisture_trend.png")
    plt.close(fig)

    rows = []
    for n in NODES:
        for sheet in THEIR_SOIL:
            a = -daily_mean(mine[n]["adc"])
            b = daily_mean(t_soil[sheet]["perm"])
            d = pd.concat([a, b], axis=1, keys=["a", "b"]).dropna()
            da = d.diff().dropna()
            rows.append(dict(node=n, sensor=short(sheet), days=len(d),
                             spearman=spearman(d["a"], d["b"]) if len(d) > 10 else np.nan,
                             spearman_diff=spearman(da["a"], da["b"]) if len(da) > 10 else np.nan))
    res = pd.DataFrame(rows)
    res.to_csv(OUT / "stats_moisture_trend.csv", index=False)
    return res


# ---------------------------------------------------------------- Fig 8: ADC offset fitted to project envelope
# Laboratory pairs (Test 1 mean ADC -> HOBO-derived permittivity), sorted by ascending ADC.
LAB_ADC = np.array([197.18, 219.97, 235.73, 319.36, 484.89])
LAB_EPS = np.array([23.957, 19.175, 15.273, 9.578, 2.251])


def adc_to_eps(adc: pd.Series, offset: float) -> pd.Series:
    # Shifted ADC values outside the calibrated lab range are invalid (NaN), never clamped.
    a = adc + offset
    ok = (a >= LAB_ADC.min()) & (a <= LAB_ADC.max())
    return pd.Series(np.interp(a, LAB_ADC, LAB_EPS), index=adc.index).where(ok & adc.notna())


def fit_offset(adc: pd.Series, lo: pd.Series, hi: pd.Series) -> float:
    grid = np.arange(-600, 101)
    cost = []
    for o in grid:
        e = adc_to_eps(adc, o)
        inside = (e >= lo) & (e <= hi)  # NaN (out of calibrated range) counts as not inside
        cost.append(1.0 - inside.mean())
    cost = np.array(cost)
    best = grid[cost <= cost.min() + 1e-9]
    return float(np.median(best))  # centre of the equally good offsets

def fig_moisture_offset() -> pd.DataFrame:
    perm = pd.concat([daily_mean(t_soil[s]["perm"]) for s in THEIR_SOIL], axis=1)
    lo, hi = perm.min(axis=1), perm.max(axis=1)
    pmean = perm.mean(axis=1)
    nodes = [1, 3, 7]  # Node 5 ADC is stuck at 768 for ~half of the hours
    fig, axes = plt.subplots(len(nodes), 1, figsize=(7.2, 7.4), sharex=True, sharey=True)
    rows = []
    for ax, n in zip(axes, nodes):
        adc = daily_mean(mine[n]["adc"])
        d = pd.concat([adc, lo, hi], axis=1, keys=["adc", "lo", "hi"]).dropna()
        half = len(d) // 2
        tr, te = d.iloc[:half], d.iloc[half:]
        off = fit_offset(tr["adc"], tr["lo"], tr["hi"])
        est = adc_to_eps(adc, off)

        def inside(part):
            e = adc_to_eps(part["adc"], off)
            return ((e >= part["lo"]) & (e <= part["hi"])).mean(), e.isna().mean()

        in_tr, oor_tr = inside(tr)
        in_te, oor_te = inside(te)
        e_te = adc_to_eps(te["adc"], off)
        rows.append(dict(node=n, offset=off, days_fit=len(tr), days_test=len(te),
                         inside_fit=in_tr, inside_test=in_te, out_of_range_fit=oor_tr, out_of_range_test=oor_te,
                         median_envelope_width=(d["hi"] - d["lo"]).median(),
                         test_r=e_te.corr(pmean.reindex(e_te.index)),
                         split_date=str(te.index[0].date())))
        ax.fill_between(lo.index, lo, hi, color="#CAB2D6", alpha=0.55, lw=0, label="Range of the four project sensors")
        ax.plot(pmean.index, pmean, color="#6A3D9A", lw=1.0, label="Mean of the four project sensors")
        ax.plot(est.index, est, color=NODE_COLOR[n], lw=1.5, label=f"Node {n} (ADC {off:+.0f} counts)")
        ax.axvline(te.index[0], color="0.3", ls=":", lw=1)
        ax.text(te.index[0], 38.5, " test period", fontsize=8, va="top")
        ax.text(tr.index[0], 38.5, " fit period", fontsize=8, va="top")
        ax.set_ylabel("Permittivity ε")
        ax.set_ylim(0, 40)
        ax.legend(loc="lower left", ncol=1)
    fmt_dates(axes[-1])
    fig.tight_layout()
    fig.savefig(OUT / "cmp_moisture_offset.png")
    plt.close(fig)
    res = pd.DataFrame(rows)
    res.to_csv(OUT / "stats_moisture_offset.csv", index=False)
    return res


# ---------------------------------------------------------------- tables
def tables(week):
    # soil temperature summary
    rows = []
    for n in NODES:
        s = mine[n]["soil_t"].dropna()
        rows.append(dict(who="mine", sensor=f"Node {n}", depth_mm=NODE_DEPTH_MM[n], hours=len(s),
                         mean=s.mean(), sd=s.std(), min=s.min(), max=s.max()))
    for sheet, (lab, depth) in THEIR_SOIL.items():
        s = t_soil[sheet]["soil_t"].dropna()
        rows.append(dict(who="theirs", sensor=lab.split()[0], depth_mm=depth, hours=len(s),
                         mean=s.mean(), sd=s.std(), min=s.min(), max=s.max()))
    pd.DataFrame(rows).to_csv(OUT / "stats_soil_temp_summary.csv", index=False)

    # envelope: fraction of hours my node lies within min/max of their four sensors
    their = pd.concat([t_soil[s]["soil_t"] for s in THEIR_SOIL], axis=1)
    lo, hi = their.min(axis=1), their.max(axis=1)
    env = []
    for n in NODES:
        d = pd.concat([mine[n]["soil_t"], lo, hi], axis=1, keys=["m", "lo", "hi"]).dropna()
        inside = ((d["m"] >= d["lo"]) & (d["m"] <= d["hi"])).mean()
        within1 = ((d["m"] >= d["lo"] - 1) & (d["m"] <= d["hi"] + 1)).mean()
        env.append(dict(node=n, hours=len(d), inside_envelope=inside, within_1C_of_envelope=within1,
                        bias_to_their_mean=(d["m"] - (d["lo"] + d["hi"]) / 2).mean()))
    pd.DataFrame(env).to_csv(OUT / "stats_soil_temp_envelope.csv", index=False)

    # air temperature / RH pairwise
    air_rows = []
    for var in ("air_t", "rh"):
        for n in NODES:
            for sheet in THEIR_AIR:
                st = corr_stats(mine[n][var], t_air[sheet][var])
                air_rows.append(dict(var=var, node=n, ref=sheet, **st))
    pd.DataFrame(air_rows).to_csv(OUT / "stats_air_pairwise_hourly.csv", index=False)

    # daily-mean correlation for air temperature
    d_rows = []
    for var in ("air_t", "rh"):
        for n in NODES:
            for sheet in THEIR_AIR:
                st = corr_stats(daily_mean(mine[n][var]), daily_mean(t_air[sheet][var]))
                d_rows.append(dict(var=var, node=n, ref=sheet, **st))
    pd.DataFrame(d_rows).to_csv(OUT / "stats_air_pairwise_daily.csv", index=False)

    # RH distribution summary
    rh = []
    for n in NODES:
        s = mine[n]["rh"].dropna()
        rh.append(dict(who="mine", sensor=f"Node {n}", hours=len(s), mean=s.mean(), median=s.median(),
                       p_ge95=(s >= 95).mean(), p_ge99=(s >= 99).mean()))
    for sheet in THEIR_AIR:
        s = t_air[sheet]["rh"].dropna()
        rh.append(dict(who="theirs", sensor=sheet, hours=len(s), mean=s.mean(), median=s.median(),
                       p_ge95=(s >= 95).mean(), p_ge99=(s >= 99).mean()))
    pd.DataFrame(rh).to_csv(OUT / "stats_rh_summary.csv", index=False)

    air = []
    for n in NODES:
        s = mine[n]["air_t"].dropna()
        air.append(dict(who="mine", sensor=f"Node {n}", hours=len(s), mean=s.mean(), min=s.min(), max=s.max(),
                        median_daily_range=daily_range(mine[n]["air_t"]).median()))
    for sheet in THEIR_AIR:
        s = t_air[sheet]["air_t"].dropna()
        air.append(dict(who="theirs", sensor=sheet, hours=len(s), mean=s.mean(), min=s.min(), max=s.max(),
                        median_daily_range=daily_range(t_air[sheet]["air_t"]).median()))
    pd.DataFrame(air).to_csv(OUT / "stats_air_temp_summary.csv", index=False)

    with open(OUT / "stats_meta.txt", "w") as fh:
        fh.write(f"window {START} .. {END}\nweek {week[0]} .. {week[1]}\n")
        fh.write("moisture ADC node5 frac==768: %.3f\n" % (mine[5]["adc"].round() == 768).mean())


if __name__ == "__main__":
    week = best_week()
    fig_coverage()
    fig_air("air_t", "Daily mean air temperature (°C)", "cmp_air_temp.png",
            "Air temperature: my nodes vs. the other project's sensors")
    fig_air("rh", "Daily mean relative humidity (%)", "cmp_rh.png",
            "Relative humidity: my nodes vs. the other project's sensors")
    fig_soil_temp()
    fig_air_simple()
    fig_week(week)
    fig_damping()
    fig_heatmap()
    fig_moisture()
    fig_moisture_offset()
    tables(week)
    print("done", week)
