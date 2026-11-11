from __future__ import annotations

from pathlib import Path
import argparse

import matplotlib.dates as mdates
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd


SENSOR_COLORS = ["#0072B2", "#E69F00", "#009E73", "#D55E00"]
SENSOR_MAP = {
    "air_temp": "field1",
    "humidity": "field2",
    "soil_temp": "field3",
    "soil_moisture_raw": "field4",
    "battery_voltage": "field5",
}


def setup_style() -> None:
    plt.style.use("seaborn-v0_8-whitegrid")
    plt.rcParams.update(
        {
            "figure.dpi": 160,
            "savefig.dpi": 220,
            "font.family": "DejaVu Sans",
            "axes.titlesize": 16,
            "axes.labelsize": 12,
            "axes.facecolor": "#ffffff",
            "grid.alpha": 0.45,
            "grid.linestyle": "--",
            "grid.color": "#d9d9d9",
        }
    )


def adc_to_gravimetric_soil_moisture(adc: pd.Series) -> pd.Series:
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


def load_sensor_data(folder: Path) -> list[tuple[str, pd.DataFrame]]:
    files = sorted(folder.glob("HW_*_feeds.csv"))
    datasets: list[tuple[str, pd.DataFrame]] = []
    for file in files:
        df = pd.read_csv(file)
        if "created_at" not in df.columns:
            continue
        df["created_at"] = pd.to_datetime(df["created_at"], errors="coerce", utc=True)
        df = df.dropna(subset=["created_at"]).sort_values("created_at").reset_index(drop=True)

        for col in SENSOR_MAP.values():
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors="coerce")
                df[col] = replace_zero_spikes(df[col])
                df[col] = replace_outlier_spikes(df[col])

        if "field4" in df.columns:
            df["soil_moisture_pct"] = adc_to_gravimetric_soil_moisture(df["field4"])

        datasets.append((file.stem.replace("_feeds", ""), df))

    if not datasets:
        raise FileNotFoundError(f"No HW_*_feeds.csv files found in {folder}")
    return datasets


def _normalize_weather_columns(df: pd.DataFrame) -> pd.DataFrame:
    rename_map = {c: c.strip().lower() for c in df.columns}
    df = df.rename(columns=rename_map)
    if "time" not in df.columns:
        raise ValueError("Weather data must contain a 'time' column")

    df["time"] = pd.to_datetime(df["time"], errors="coerce", utc=True)
    df = df.dropna(subset=["time"]).sort_values("time").reset_index(drop=True)

    for c in ["t", "rh", "tg"]:
        if c in df.columns:
            df[c] = pd.to_numeric(df[c], errors="coerce")
    return df


def load_weather_data(folder: Path) -> pd.DataFrame:
    weather_files = sorted(folder.glob("Weatherdata_IMO_*"))
    if not weather_files:
        raise FileNotFoundError(f"No Weatherdata_IMO_* files found in {folder}")

    frames: list[pd.DataFrame] = []
    for file in weather_files:
        if file.suffix.lower() == ".xlsx":
            xl = pd.ExcelFile(file)
            if "Observations" not in xl.sheet_names:
                continue
            df = pd.read_excel(file, sheet_name="Observations")
            df = _normalize_weather_columns(df)
        elif file.suffix.lower() == ".csv":
            df = pd.read_csv(file, sep=";")
            df = _normalize_weather_columns(df)
        else:
            continue

        keep_cols = [c for c in ["time", "t", "rh", "tg"] if c in df.columns]
        frames.append(df[keep_cols].copy())

    if not frames:
        raise ValueError(f"No usable weather observations found in {folder}")

    weather = pd.concat(frames, ignore_index=True)
    weather = weather.groupby("time", as_index=False).mean(numeric_only=True)
    weather = weather.sort_values("time").reset_index(drop=True)

    if "tg" in weather.columns and weather["tg"].notna().sum() > 10:
        weather["soil_ref"] = weather["tg"]
    else:
        weather["soil_ref"] = weather.get("t")

    return weather


def common_window(sensor_sets: list[tuple[str, pd.DataFrame]], weather: pd.DataFrame) -> tuple[pd.Timestamp, pd.Timestamp] | None:
    if weather.empty:
        return None
    starts = [weather["time"].min()]
    ends = [weather["time"].max()]
    for _, df in sensor_sets:
        if df.empty:
            continue
        starts.append(df["created_at"].min())
        ends.append(df["created_at"].max())
    start = max(starts)
    end = min(ends)
    if start >= end:
        return None
    return start, end


def merge_sensor_with_weather(sensor_df: pd.DataFrame, weather: pd.DataFrame, tolerance: str) -> pd.DataFrame:
    cols = [c for c in ["time", "t", "rh", "soil_ref"] if c in weather.columns]
    merged = pd.merge_asof(
        sensor_df.sort_values("created_at"),
        weather[cols].sort_values("time"),
        left_on="created_at",
        right_on="time",
        direction="nearest",
        tolerance=pd.Timedelta(tolerance),
    )
    return merged.drop(columns=["time"], errors="ignore")


def make_wide_table(sensor_sets: list[tuple[str, pd.DataFrame]], weather: pd.DataFrame, tolerance: str, window: tuple[pd.Timestamp, pd.Timestamp] | None) -> pd.DataFrame:
    rows = []
    for sensor_name, sdf in sensor_sets:
        merged = merge_sensor_with_weather(sdf, weather, tolerance)
        if window is not None:
            start, end = window
            merged = merged[(merged["created_at"] >= start) & (merged["created_at"] <= end)].copy()
        if merged.empty:
            continue

        wide = pd.DataFrame(
            {
                "sensor": sensor_name,
                "time_utc": merged["created_at"],
                "air_temp_sensor_c": merged.get("field1"),
                "air_temp_station_c": merged.get("t"),
                "humidity_sensor_pct": merged.get("field2"),
                "humidity_station_pct": merged.get("rh"),
                "soil_temp_sensor_c": merged.get("field3"),
                "soil_temp_station_c": merged.get("soil_ref"),
                "soil_moisture_raw_adc": merged.get("field4"),
                "soil_moisture_gravimetric_pct": merged.get("soil_moisture_pct"),
                "battery_voltage_v": merged.get("field5"),
            }
        )
        wide["air_temp_diff_c"] = wide["air_temp_sensor_c"] - wide["air_temp_station_c"]
        wide["humidity_diff_pct"] = wide["humidity_sensor_pct"] - wide["humidity_station_pct"]
        wide["soil_temp_diff_c"] = wide["soil_temp_sensor_c"] - wide["soil_temp_station_c"]
        rows.append(wide)

    if not rows:
        return pd.DataFrame()
    return pd.concat(rows, ignore_index=True).sort_values(["sensor", "time_utc"])


def summarize_table(wide: pd.DataFrame) -> pd.DataFrame:
    metrics = [
        ("air_temp", "air_temp_sensor_c", "air_temp_station_c", "air_temp_diff_c"),
        ("humidity", "humidity_sensor_pct", "humidity_station_pct", "humidity_diff_pct"),
        ("soil_temp", "soil_temp_sensor_c", "soil_temp_station_c", "soil_temp_diff_c"),
    ]
    rows: list[dict[str, float | str | int]] = []
    for sensor, g in wide.groupby("sensor"):
        for m, s_col, st_col, d_col in metrics:
            valid = g[[s_col, st_col, d_col]].dropna()
            if valid.empty:
                continue
            rows.append(
                {
                    "sensor": sensor,
                    "metric": m,
                    "n_points": int(len(valid)),
                    "mae": float(valid[d_col].abs().mean()),
                    "rmse": float(np.sqrt((valid[d_col] ** 2).mean())),
                    "bias": float(valid[d_col].mean()),
                    "correlation": float(valid[s_col].corr(valid[st_col])) if pd.notna(valid[s_col].corr(valid[st_col])) else np.nan,
                }
            )
    return pd.DataFrame(rows)


def _format_time_axis(ax: plt.Axes) -> None:
    locator = mdates.AutoDateLocator(minticks=5, maxticks=9)
    formatter = mdates.ConciseDateFormatter(locator)
    ax.xaxis.set_major_locator(locator)
    ax.xaxis.set_major_formatter(formatter)


def save_quick_plots(out_dir: Path, wide: pd.DataFrame) -> None:
    if wide.empty:
        return

    metrics = [
        ("air_temp_sensor_c", "air_temp_station_c", "Air Temp (C)", "quick_air_temp_compare.png"),
        ("humidity_sensor_pct", "humidity_station_pct", "Humidity (%)", "quick_humidity_compare.png"),
        ("soil_temp_sensor_c", "soil_temp_station_c", "Soil Temp (C)", "quick_soil_temp_compare.png"),
    ]

    for sensor_col, st_col, ylabel, filename in metrics:
        fig, ax = plt.subplots(figsize=(12, 5.5))
        station = wide[["time_utc", st_col]].dropna()
        if not station.empty:
            station = station.groupby("time_utc", as_index=False).mean(numeric_only=True)
            ax.plot(station["time_utc"], station[st_col], color="#1f1f1f", linestyle="--", linewidth=2.4, label="Station")

        for idx, (sensor, g) in enumerate(wide.groupby("sensor")):
            ax.plot(g["time_utc"], g[sensor_col], color=SENSOR_COLORS[idx % len(SENSOR_COLORS)], linewidth=1.8, label=sensor)

        ax.set_title(f"{ylabel} - Quick Comparison")
        ax.set_xlabel("Time (UTC)")
        ax.set_ylabel(ylabel)
        _format_time_axis(ax)
        ax.legend(ncols=3, loc="upper center", bbox_to_anchor=(0.5, 1.15), frameon=True)
        ax.spines["top"].set_visible(False)
        ax.spines["right"].set_visible(False)
        fig.tight_layout()
        fig.savefig(out_dir / filename)
        plt.close(fig)

    fig, ax = plt.subplots(figsize=(12, 5.5))
    for idx, (sensor, g) in enumerate(wide.groupby("sensor")):
        ax.plot(
            g["time_utc"],
            g["soil_moisture_gravimetric_pct"],
            color=SENSOR_COLORS[idx % len(SENSOR_COLORS)],
            linewidth=1.8,
            label=sensor,
        )
    ax.set_title("Soil Moisture (Gravimetric %) - Quick Comparison")
    ax.set_xlabel("Time (UTC)")
    ax.set_ylabel("Soil Moisture (gravimetric %)")
    _format_time_axis(ax)
    ax.legend(ncols=4, loc="upper center", bbox_to_anchor=(0.5, 1.15), frameon=True)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    fig.tight_layout()
    fig.savefig(out_dir / "quick_soil_moisture_compare.png")
    plt.close(fig)


def run_folder(folder: Path, tolerance: str) -> None:
    output = folder / "analysis_outputs"
    output.mkdir(parents=True, exist_ok=True)

    sensor_sets = load_sensor_data(folder)
    weather = load_weather_data(folder)
    window = common_window(sensor_sets, weather)

    wide = make_wide_table(sensor_sets, weather, tolerance=tolerance, window=window)
    if wide.empty:
        raise ValueError(f"No merged records produced for {folder}")

    long_df = wide.melt(
        id_vars=["sensor", "time_utc"],
        var_name="variable",
        value_name="value",
    )
    summary = summarize_table(wide)

    wide.to_csv(output / "quick_comparison_wide.csv", index=False)
    long_df.to_csv(output / "quick_comparison_long.csv", index=False)
    summary.to_csv(output / "quick_summary.csv", index=False)

    save_quick_plots(output, wide)

    print(f"Done: {folder}")
    print(f"Output: {output}")
    if window is not None:
        print(f"Common window: {window[0]} -> {window[1]}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Quick plots and analysis for June/October testing folders.")
    parser.add_argument("--base-dir", default=".", help="Base folder containing June Testing and October Testing")
    parser.add_argument("--folders", nargs="*", default=["June Testing", "October Testing"], help="Folder names to process")
    parser.add_argument("--tolerance", default="40min", help="Nearest timestamp tolerance")
    args = parser.parse_args()

    setup_style()

    base = Path(args.base_dir)
    for name in args.folders:
        folder = base / name
        if not folder.exists():
            print(f"Skipping missing folder: {folder}")
            continue
        run_folder(folder, tolerance=args.tolerance)


if __name__ == "__main__":
    main()
