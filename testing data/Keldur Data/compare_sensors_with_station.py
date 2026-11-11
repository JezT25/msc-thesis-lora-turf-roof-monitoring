from __future__ import annotations

from pathlib import Path
import argparse

import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import numpy as np
import pandas as pd


SENSOR_COLUMNS = {
    "air_temp": "field1",
    "humidity": "field2",
    "soil_temp": "field3",
    "soil_moisture_raw": "field4",
    "soil_moisture_pct": "soil_moisture_pct",
    "battery_voltage": "field5",
}

# Station side codes are resolved from the Parameters sheet descriptions.
DEFAULT_STATION_MAP = {
    "air_temp": "t",
    "humidity": "rh",
    # The script will choose the first available soil temperature if this is missing.
    "soil_temp": "tg",
}

SOIL_TEMP_FALLBACKS = ["tug5", "tug10", "tug15", "tug20", "tug50", "tug100", "tg"]
SENSOR_COLORS = ["#0072B2", "#E69F00", "#009E73", "#D55E00"]
STATION_COLOR = "#1f1f1f"

METRIC_YLABELS = {
    "air_temp": "Air temperature (C)",
    "humidity": "Humidity (%)",
    "soil_temp": "Soil temperature (C)",
    "soil_moisture_pct": "Soil moisture (gravimetric %)",
    "battery_voltage": "Battery voltage (V)",
}


def apply_presentation_style() -> None:
    plt.style.use("seaborn-v0_8-whitegrid")
    plt.rcParams.update(
        {
            "figure.dpi": 170,
            "savefig.dpi": 220,
            "font.family": "DejaVu Sans",
            "axes.titlesize": 18,
            "axes.labelsize": 13,
            "xtick.labelsize": 10,
            "ytick.labelsize": 10,
            "legend.fontsize": 10,
            "axes.titleweight": "bold",
            "axes.facecolor": "#ffffff",
            "figure.facecolor": "#ffffff",
            "axes.edgecolor": "#666666",
            "grid.color": "#d9d9d9",
            "grid.alpha": 0.5,
            "grid.linestyle": "--",
            "grid.linewidth": 0.7,
        }
    )


def format_time_axis(ax: plt.Axes) -> None:
    locator = mdates.AutoDateLocator(minticks=5, maxticks=9)
    formatter = mdates.ConciseDateFormatter(locator)
    ax.xaxis.set_major_locator(locator)
    ax.xaxis.set_major_formatter(formatter)


def get_common_time_window(
    sensor_sets: list[tuple[str, pd.DataFrame]], station_obs: pd.DataFrame
) -> tuple[pd.Timestamp, pd.Timestamp] | None:
    station_time = station_obs["time"].dropna()
    if station_time.empty:
        return None

    starts = [station_time.min()]
    ends = [station_time.max()]
    for _, sensor_df in sensor_sets:
        sensor_time = sensor_df["created_at"].dropna()
        if sensor_time.empty:
            continue
        starts.append(sensor_time.min())
        ends.append(sensor_time.max())

    start = max(starts)
    end = min(ends)
    if pd.isna(start) or pd.isna(end) or start >= end:
        return None
    return start, end


def find_xlsx_file(data_dir: Path) -> Path:
    candidates = sorted(
        p for p in data_dir.glob("*.xlsx") if not p.name.startswith("~$")
    )
    if not candidates:
        raise FileNotFoundError("No .xlsx file found in the data directory.")
    return candidates[0]


def load_station_data(xlsx_path: Path) -> tuple[pd.DataFrame, pd.DataFrame]:
    xl = pd.ExcelFile(xlsx_path)
    sheet_lookup = {s.lower(): s for s in xl.sheet_names}

    if "observations" not in sheet_lookup:
        raise ValueError("The workbook does not contain an 'Observations' sheet.")
    if "parameters" not in sheet_lookup:
        raise ValueError("The workbook does not contain a 'Parameters' sheet.")

    obs = pd.read_excel(xlsx_path, sheet_name=sheet_lookup["observations"])
    params = pd.read_excel(xlsx_path, sheet_name=sheet_lookup["parameters"])

    if "time" not in obs.columns:
        raise ValueError("Observations sheet must contain a 'time' column.")

    obs = obs.copy()
    obs["time"] = pd.to_datetime(obs["time"], errors="coerce", utc=True)
    obs = obs.dropna(subset=["time"]).sort_values("time").reset_index(drop=True)

    return obs, params


def choose_station_soil_temp(obs: pd.DataFrame, params: pd.DataFrame) -> str | None:
    available = [c for c in SOIL_TEMP_FALLBACKS if c in obs.columns]
    if not available:
        return None

    params = params.copy()
    if "Parameter" in params.columns and "Description" in params.columns:
        param_desc = dict(zip(params["Parameter"], params["Description"]))
        for code in available:
            desc = str(param_desc.get(code, "")).lower()
            if "soil temperature" in desc:
                return code

    return available[0]


def load_sensor_csvs(data_dir: Path) -> list[tuple[str, pd.DataFrame]]:
    sensor_files = sorted(data_dir.glob("feeds*.csv"))
    if not sensor_files:
        raise FileNotFoundError("No sensor CSV files matching feeds*.csv were found.")

    datasets: list[tuple[str, pd.DataFrame]] = []
    for file in sensor_files:
        df = pd.read_csv(file)
        if "created_at" not in df.columns:
            raise ValueError(f"Missing 'created_at' column in {file.name}")

        df = df.copy()
        df["created_at"] = pd.to_datetime(df["created_at"], errors="coerce", utc=True)
        df = df.dropna(subset=["created_at"]).sort_values("created_at").reset_index(drop=True)

        for col in SENSOR_COLUMNS.values():
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors="coerce")

        # Replace only isolated zero spikes (single-point dropouts) with the previous value.
        for col in SENSOR_COLUMNS.values():
            if col in df.columns:
                df[col] = replace_zero_spikes(df[col])

        # Suppress startup transients only for requested channels.
        if "field1" in df.columns:
            df["field1"] = suppress_startup_spikes(df["field1"])
        if "field4" in df.columns:
            df["field4"] = suppress_startup_spikes(df["field4"])

        # Remove sharp outlier spikes while keeping normal variation and trends.
        for col in SENSOR_COLUMNS.values():
            if col in df.columns and col != "soil_moisture_pct":
                df[col] = replace_outlier_spikes(df[col], window=7, z_thresh=6.0)

        if "field4" in df.columns:
            df["soil_moisture_pct"] = adc_to_gravimetric_soil_moisture(df["field4"])

        datasets.append((file.stem, df))

    return datasets


def adc_to_gravimetric_soil_moisture(adc: pd.Series) -> pd.Series:
    # Soil Moisture (%) = 0.0006877 * ADC^2 - 0.5961 * ADC + 127.70
    adc_num = pd.to_numeric(adc, errors="coerce")
    return 0.0006877 * (adc_num ** 2) - 0.5961 * adc_num + 127.70


def replace_zero_spikes(series: pd.Series) -> pd.Series:
    arr = np.array(pd.to_numeric(series, errors="coerce"), dtype=float, copy=True)
    n = len(arr)
    i = 0

    while i < n:
        if arr[i] != 0:
            i += 1
            continue

        j = i
        while j < n and arr[j] == 0:
            j += 1

        run_len = j - i
        prev_val = arr[i - 1] if i > 0 else np.nan
        next_val = arr[j] if j < n else np.nan

        # Treat only isolated zeros between two nearby non-zero points as spikes.
        if (
            run_len == 1
            and np.isfinite(prev_val)
            and np.isfinite(next_val)
            and prev_val != 0
            and next_val != 0
        ):
            baseline = (abs(prev_val) + abs(next_val)) / 2
            if baseline > 0 and abs(prev_val - next_val) <= 0.35 * baseline:
                arr[i] = prev_val

        i = j

    return pd.Series(arr, index=series.index)


def replace_outlier_spikes(series: pd.Series, window: int = 7, z_thresh: float = 6.0) -> pd.Series:
    s = pd.to_numeric(series, errors="coerce").astype(float)
    med = s.rolling(window=window, center=True, min_periods=3).median()
    abs_dev = (s - med).abs()
    mad = abs_dev.rolling(window=window, center=True, min_periods=3).median()

    robust_sigma = 1.4826 * mad
    spike_mask = (
        med.notna()
        & robust_sigma.notna()
        & (robust_sigma > 0)
        & (abs_dev > (z_thresh * robust_sigma))
    )

    cleaned = s.copy()
    cleaned.loc[spike_mask] = med.loc[spike_mask]
    return cleaned


def suppress_startup_spikes(
    series: pd.Series,
    startup_points: int = 10,
    baseline_start: int = 10,
    baseline_len: int = 24,
    z_thresh: float = 5.5,
) -> pd.Series:
    s = pd.to_numeric(series, errors="coerce").astype(float).copy()
    if s.notna().sum() < (baseline_start + 5):
        return s

    baseline = s.iloc[baseline_start : baseline_start + baseline_len].dropna()
    if baseline.empty:
        return s

    center = baseline.median()
    mad = (baseline - center).abs().median()
    scale = 1.4826 * mad
    if not np.isfinite(scale) or scale == 0:
        std = baseline.std()
        scale = std if np.isfinite(std) and std > 0 else None
    if scale is None:
        return s

    n = min(startup_points, len(s))
    startup = s.iloc[:n]
    spike_mask = startup.notna() & ((startup - center).abs() > (z_thresh * scale))
    if not spike_mask.any():
        return s

    s.loc[spike_mask.index[spike_mask]] = np.nan
    s.iloc[:n] = s.iloc[:n].bfill().ffill()
    return s


def nearest_time_merge(
    sensor_df: pd.DataFrame,
    station_df: pd.DataFrame,
    station_col: str,
    tolerance: str,
) -> pd.DataFrame:
    left = sensor_df[["created_at"] + [c for c in SENSOR_COLUMNS.values() if c in sensor_df.columns]].copy()
    right = station_df[["time", station_col]].copy()

    merged = pd.merge_asof(
        left.sort_values("created_at"),
        right.sort_values("time"),
        left_on="created_at",
        right_on="time",
        direction="nearest",
        tolerance=pd.Timedelta(tolerance),
    )
    return merged


def add_station_column_asof(
    base_df: pd.DataFrame,
    station_df: pd.DataFrame,
    station_col: str,
    tolerance: str,
) -> pd.DataFrame:
    right = station_df[["time", station_col]].sort_values("time").copy()
    merged = pd.merge_asof(
        base_df.sort_values("created_at"),
        right,
        left_on="created_at",
        right_on="time",
        direction="nearest",
        tolerance=pd.Timedelta(tolerance),
    )
    return merged.drop(columns=["time"], errors="ignore")


def save_metric_plot(
    output_dir: Path,
    metric_name: str,
    sensor_datasets: list[tuple[str, pd.DataFrame]],
    station_series: pd.DataFrame,
    station_col: str,
    plot_window: tuple[pd.Timestamp, pd.Timestamp] | None,
) -> None:
    if plot_window is not None:
        start, end = plot_window
        station_series = station_series[
            (station_series["time"] >= start) & (station_series["time"] <= end)
        ]
        clipped_sets: list[tuple[str, pd.DataFrame]] = []
        for sensor_name, df in sensor_datasets:
            clipped = df[(df["created_at"] >= start) & (df["created_at"] <= end)].copy()
            clipped_sets.append((sensor_name, clipped))
        sensor_datasets = clipped_sets

    if station_series.empty:
        return

    fig, ax = plt.subplots(figsize=(13, 6))

    ax.plot(
        station_series["time"],
        station_series[station_col],
        color=STATION_COLOR,
        linewidth=2.6,
        linestyle="--",
        label=f"Weather station ({station_col})",
        zorder=5,
    )

    for idx, (sensor_name, df) in enumerate(sensor_datasets):
        sensor_col = SENSOR_COLUMNS[metric_name]
        if sensor_col not in df.columns:
            continue
        ax.plot(
            df["created_at"],
            df[sensor_col],
            linewidth=2,
            alpha=0.98,
            label=sensor_name,
            color=SENSOR_COLORS[idx % len(SENSOR_COLORS)],
        )

    ax.set_title(f"{metric_name.replace('_', ' ').title()} comparison")
    ax.set_xlabel("Time (UTC)")
    ax.set_ylabel(METRIC_YLABELS.get(metric_name, metric_name.replace("_", " ").title()))
    ax.grid(alpha=0.3)
    if plot_window is not None:
        ax.set_xlim(plot_window[0], plot_window[1])
    format_time_axis(ax)
    ax.legend(ncols=3, loc="upper center", bbox_to_anchor=(0.5, 1.16), frameon=True)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    fig.tight_layout()

    out_file = output_dir / f"compare_{metric_name}.png"
    fig.savefig(out_file, dpi=150)
    plt.close(fig)


def save_sensor_overview_plot(
    output_dir: Path,
    sensor_name: str,
    merged: pd.DataFrame,
    station_map: dict[str, str],
    plot_window: tuple[pd.Timestamp, pd.Timestamp] | None,
) -> None:
    metric_order = ["air_temp", "humidity", "soil_temp", "soil_moisture_pct", "battery_voltage"]

    if plot_window is not None:
        start, end = plot_window
        merged = merged[(merged["created_at"] >= start) & (merged["created_at"] <= end)].copy()

    if merged.empty:
        return

    fig, axes = plt.subplots(len(metric_order), 1, figsize=(13, 14), sharex=True)

    for idx, metric in enumerate(metric_order):
        ax = axes[idx]
        sensor_col = SENSOR_COLUMNS[metric]

        if sensor_col in merged.columns:
            ax.plot(
                merged["created_at"],
                merged[sensor_col],
                label=f"Sensor {metric}",
                linewidth=2,
                color="#0072B2",
            )

        station_col = station_map.get(metric)
        if station_col and station_col in merged.columns:
            ax.plot(
                merged["created_at"],
                merged[station_col],
                label=f"Station {station_col}",
                linewidth=2.2,
                color=STATION_COLOR,
                linestyle="--",
                alpha=0.85,
            )

        ax.set_ylabel(METRIC_YLABELS.get(metric, metric.replace("_", " ")))
        ax.grid(alpha=0.3)
        ax.legend(loc="upper right")
        if plot_window is not None:
            ax.set_xlim(plot_window[0], plot_window[1])
        ax.spines["top"].set_visible(False)
        ax.spines["right"].set_visible(False)

    axes[-1].set_xlabel("Time (UTC)")
    format_time_axis(axes[-1])
    fig.suptitle(f"{sensor_name} vs weather station", y=0.995)
    fig.tight_layout()

    out_file = output_dir / f"overview_{sensor_name}.png"
    fig.savefig(out_file, dpi=150)
    plt.close(fig)


def export_llm_tables(
    output_dir: Path,
    sensor_sets: list[tuple[str, pd.DataFrame]],
    station_obs: pd.DataFrame,
    station_map: dict[str, str],
    tolerance: str,
    plot_window: tuple[pd.Timestamp, pd.Timestamp] | None,
) -> None:
    wide_frames: list[pd.DataFrame] = []

    for sensor_name, sensor_df in sensor_sets:
        merged = sensor_df.copy()
        for metric, station_col in station_map.items():
            if station_col in station_obs.columns:
                merged = add_station_column_asof(merged, station_obs, station_col, tolerance)

        if plot_window is not None:
            start, end = plot_window
            merged = merged[(merged["created_at"] >= start) & (merged["created_at"] <= end)].copy()

        if merged.empty:
            continue

        wide = pd.DataFrame(
            {
                "sensor": sensor_name,
                "time_utc": merged["created_at"],
                "air_temp_sensor_c": merged.get("field1"),
                "air_temp_station_c": merged.get(station_map.get("air_temp", "")),
                "humidity_sensor_pct": merged.get("field2"),
                "humidity_station_pct": merged.get(station_map.get("humidity", "")),
                "soil_temp_sensor_c": merged.get("field3"),
                "soil_temp_station_c": merged.get(station_map.get("soil_temp", "")),
                "soil_moisture_raw_adc": merged.get("field4"),
                "soil_moisture_gravimetric_pct": merged.get("soil_moisture_pct"),
                "battery_voltage_v": merged.get("field5"),
            }
        )

        wide["air_temp_diff_c"] = wide["air_temp_sensor_c"] - wide["air_temp_station_c"]
        wide["humidity_diff_pct"] = wide["humidity_sensor_pct"] - wide["humidity_station_pct"]
        wide["soil_temp_diff_c"] = wide["soil_temp_sensor_c"] - wide["soil_temp_station_c"]

        wide_frames.append(wide)

    if not wide_frames:
        return

    llm_wide = pd.concat(wide_frames, ignore_index=True).sort_values(["sensor", "time_utc"])
    llm_wide.to_csv(output_dir / "llm_comparison_wide.csv", index=False)

    id_cols = ["sensor", "time_utc"]
    value_cols = [
        "air_temp_sensor_c",
        "air_temp_station_c",
        "air_temp_diff_c",
        "humidity_sensor_pct",
        "humidity_station_pct",
        "humidity_diff_pct",
        "soil_temp_sensor_c",
        "soil_temp_station_c",
        "soil_temp_diff_c",
        "soil_moisture_raw_adc",
        "soil_moisture_gravimetric_pct",
        "battery_voltage_v",
    ]
    llm_long = llm_wide.melt(id_vars=id_cols, value_vars=value_cols, var_name="variable", value_name="value")
    llm_long.to_csv(output_dir / "llm_comparison_long.csv", index=False)

    summary_rows: list[dict[str, float | str]] = []
    metric_triplets = [
        ("air_temp", "air_temp_sensor_c", "air_temp_station_c", "air_temp_diff_c"),
        ("humidity", "humidity_sensor_pct", "humidity_station_pct", "humidity_diff_pct"),
        ("soil_temp", "soil_temp_sensor_c", "soil_temp_station_c", "soil_temp_diff_c"),
    ]
    for sensor_name, group in llm_wide.groupby("sensor"):
        for metric_name, sensor_col, station_col, diff_col in metric_triplets:
            valid = group[[sensor_col, station_col, diff_col]].dropna()
            if valid.empty:
                continue
            mae = valid[diff_col].abs().mean()
            rmse = np.sqrt((valid[diff_col] ** 2).mean())
            bias = valid[diff_col].mean()
            corr = valid[sensor_col].corr(valid[station_col])
            summary_rows.append(
                {
                    "sensor": sensor_name,
                    "metric": metric_name,
                    "n_points": int(len(valid)),
                    "mae": float(mae),
                    "rmse": float(rmse),
                    "bias": float(bias),
                    "correlation": float(corr) if pd.notna(corr) else np.nan,
                }
            )

    if summary_rows:
        summary_df = pd.DataFrame(summary_rows).sort_values(["sensor", "metric"])
        summary_df.to_csv(output_dir / "llm_summary_by_sensor.csv", index=False)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Compare sensor CSV data with official weather station XLSX observations."
    )
    parser.add_argument(
        "--data-dir",
        default=".",
        help="Directory containing feeds*.csv and the weather station .xlsx file.",
    )
    parser.add_argument(
        "--xlsx",
        default=None,
        help="Optional explicit XLSX filename/path. If omitted, first .xlsx file in data dir is used.",
    )
    parser.add_argument(
        "--tolerance",
        default="40min",
        help="Nearest-time matching tolerance (pandas Timedelta string). Default: 40min",
    )
    parser.add_argument(
        "--output-dir",
        default="plots",
        help="Output directory for generated PNG plots.",
    )

    args = parser.parse_args()
    data_dir = Path(args.data_dir)
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    xlsx_path = Path(args.xlsx) if args.xlsx else find_xlsx_file(data_dir)

    station_obs, station_params = load_station_data(xlsx_path)
    sensor_sets = load_sensor_csvs(data_dir)

    station_map = DEFAULT_STATION_MAP.copy()
    station_soil = choose_station_soil_temp(station_obs, station_params)
    if station_map["soil_temp"] not in station_obs.columns and station_soil:
        station_map["soil_temp"] = station_soil
    plot_window = get_common_time_window(sensor_sets, station_obs)

    apply_presentation_style()

    print(f"Using XLSX: {xlsx_path}")
    print(f"Station mapping: {station_map}")
    print(f"Loaded sensors: {[name for name, _ in sensor_sets]}")
    if plot_window is not None:
        print(f"Common time window: {plot_window[0]} -> {plot_window[1]}")
    else:
        print("No common full overlap window found; plotting full available ranges.")

    for metric in ["air_temp", "humidity", "soil_temp"]:
        station_col = station_map.get(metric)
        if not station_col or station_col not in station_obs.columns:
            print(f"Skipping metric '{metric}': station parameter not found.")
            continue

        # Build a lightweight list for this metric plot from raw sensor data.
        raw_sets = [(name, df[["created_at", SENSOR_COLUMNS[metric]]].copy()) for name, df in sensor_sets if SENSOR_COLUMNS[metric] in df.columns]
        station_series = station_obs[["time", station_col]].dropna(subset=[station_col]).copy()
        save_metric_plot(output_dir, metric, raw_sets, station_series, station_col, plot_window)

    # Sensor overviews include direct nearest-time matched station values in each panel.
    for sensor_name, sensor_df in sensor_sets:
        merged = sensor_df.copy()
        for metric, station_col in station_map.items():
            if station_col in station_obs.columns:
                merged = add_station_column_asof(merged, station_obs, station_col, args.tolerance)
        save_sensor_overview_plot(output_dir, sensor_name, merged, station_map, plot_window)

    export_llm_tables(
        output_dir=output_dir,
        sensor_sets=sensor_sets,
        station_obs=station_obs,
        station_map=station_map,
        tolerance=args.tolerance,
        plot_window=plot_window,
    )

    print(f"Plots saved in: {output_dir.resolve()}")
    print(f"LLM tables saved in: {output_dir.resolve()}")


if __name__ == "__main__":
    main()
