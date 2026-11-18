"""
analysis.py
-----------
Calculations on the discharge tables made by load_data.py.

Milestone 4:
    add_retention(table)      -> adds two retention columns (%) to a discharge table
    first_cycle_below(...)    -> first cycle where capacity falls below a threshold
    make_summary_table(...)   -> one row per battery, saved to results/

All numbers about the test come from the NASA README (data/README.txt):
    rated capacity  = 2.0 Ah
    end of life     = 30% fade of rated capacity = 1.4 Ah
"""

from pathlib import Path

import pandas as pd


# Folder for the CSV tables: <project>/results
RESULTS_FOLDER = Path(__file__).resolve().parent.parent / "results"

# From the NASA README
RATED_CAPACITY_AH = 2.0
EOL_NASA_AH = 0.70 * RATED_CAPACITY_AH       # 1.4 Ah  (NASA: 30% fade)
EOL_INDUSTRY_AH = 0.80 * RATED_CAPACITY_AH   # 1.6 Ah  (common industry limit: 20% fade)

# Discharge cut-off voltage of each battery (NASA README). They are NOT all the same!
CUTOFF_VOLTAGE_V = {"B0005": 2.7, "B0006": 2.5, "B0007": 2.2, "B0018": 2.5}


def add_retention(table):
    """Add two retention columns (in %) to a discharge table.

    retention_vs_first_pct : capacity / capacity of cycle 1     x 100
    retention_vs_rated_pct : capacity / rated capacity (2.0 Ah) x 100
    """
    first_capacity = table["capacity_Ah"].iloc[0]
    table = table.copy()                     # work on a copy, keep the original unchanged
    table["retention_vs_first_pct"] = 100 * table["capacity_Ah"] / first_capacity
    table["retention_vs_rated_pct"] = 100 * table["capacity_Ah"] / RATED_CAPACITY_AH
    return table


def first_cycle_below(table, threshold_Ah):
    """Return the FIRST cycle number where capacity < threshold.
    Return None if the battery never goes below it.

    Note: because capacity sometimes recovers after a rest, a battery can go
    below the threshold and come back above it for a few cycles. We use the
    first crossing, which is the stricter (safer) definition.
    """
    below = table[table["capacity_Ah"] < threshold_Ah]
    if below.empty:
        return None
    return int(below["discharge_number"].iloc[0])


def make_summary_table(discharge_tables):
    """One row per battery with the main Milestone 4 numbers."""
    rows = []
    for name, table in discharge_tables.items():
        table = add_retention(table)
        last = table.iloc[-1]                # the last discharge cycle
        rows.append({
            "battery": name,
            "cutoff_voltage_V": CUTOFF_VOLTAGE_V[name],
            "number_of_cycles": len(table),
            "test_start": table["start_time"].iloc[0],
            "test_end": table["start_time"].iloc[-1],
            # 4 decimals, so that B0007's lowest value (1.40046) does not look like 1.400
            "first_capacity_Ah": round(table["capacity_Ah"].iloc[0], 4),
            "last_capacity_Ah": round(last["capacity_Ah"], 4),
            "lowest_capacity_Ah": round(table["capacity_Ah"].min(), 4),
            "last_retention_vs_first_pct": round(last["retention_vs_first_pct"], 1),
            "last_retention_vs_rated_pct": round(last["retention_vs_rated_pct"], 1),
            # Fade = how much was LOST = 100% - retention
            "fade_vs_first_pct": round(100 - last["retention_vs_first_pct"], 1),
            "fade_vs_rated_pct": round(100 - last["retention_vs_rated_pct"], 1),
            "cycle_below_1.6Ah_80pct": first_cycle_below(table, EOL_INDUSTRY_AH),
            "cycle_below_1.4Ah_NASA_EOL": first_cycle_below(table, EOL_NASA_AH),
        })
    summary = pd.DataFrame(rows)
    # "Int64" = whole numbers that are allowed to be empty (battery never reached EOL)
    for column in ["cycle_below_1.6Ah_80pct", "cycle_below_1.4Ah_NASA_EOL"]:
        summary[column] = summary[column].astype("Int64")
    return summary


def save_table(table, file_name):
    """Save a table as CSV in results/ and tell the user where it is."""
    RESULTS_FOLDER.mkdir(exist_ok=True)
    path = RESULTS_FOLDER / file_name
    try:
        table.to_csv(path, index=False)
        print(f"Saved: {path}")
    except PermissionError:
        # Windows "locks" a file while Excel has it open
        print(f"\nCould NOT save {path}")
        print("The file is probably open in Excel. Close it and run the script again.\n")
    return path


# =============================================================================
# Milestone 5: resistance (Re, Rct)
# =============================================================================

def resistance_after_discharge(impedance_table):
    """Keep only the impedance tests done right AFTER a discharge (cell empty).

    Why: Rct depends on the state of charge. NASA measured impedance both on the
    empty cell (after discharge) and on the full cell (after charge). Mixing them
    makes the curve zig-zag, so we compare like with like.
    Also adds the resistances in milliohm (mOhm), which are easier to read.
    """
    table = impedance_table[impedance_table["previous_step"] == "discharge"].copy()
    table["Re_mohm"] = 1000 * table["Re_ohm"]
    table["Rct_mohm"] = 1000 * table["Rct_ohm"]
    table["total_mohm"] = table["Re_mohm"] + table["Rct_mohm"]
    return table


def add_capacity(resistance_table, discharge_table):
    """Add the capacity of the discharge that came just before each impedance test."""
    capacity = discharge_table[["discharge_number", "capacity_Ah"]]
    return resistance_table.merge(capacity, left_on="cycle_number",
                                  right_on="discharge_number", how="left")


def make_resistance_summary(resistance_tables, points_to_average=5):
    """One row per battery: Re and Rct at the start and end, and the % increase.

    'start' and 'end' are the average of the first / last 5 tests, so one noisy
    measurement does not change the result much.
    The correlation r (from -1 to +1) tells how closely resistance follows
    capacity: r close to -1 means "resistance up <-> capacity down".
    """
    rows = []
    for name, table in resistance_tables.items():
        row = {"battery": name, "number_of_tests": len(table)}
        for column, label in [("Re_mohm", "Re"), ("Rct_mohm", "Rct")]:
            start = table[column].head(points_to_average).mean()
            end = table[column].tail(points_to_average).mean()
            row[f"{label}_start_mohm"] = round(start, 1)
            row[f"{label}_end_mohm"] = round(end, 1)
            row[f"{label}_increase_pct"] = round(100 * (end - start) / start, 1)
            row[f"{label}_vs_capacity_r"] = round(table[column].corr(table["capacity_Ah"]), 2)
        row["total_vs_capacity_r"] = round(table["total_mohm"].corr(table["capacity_Ah"]), 2)
        rows.append(row)
    return pd.DataFrame(rows)


# =============================================================================
# Running the analyses (main.py will call these in Milestone 6)
# =============================================================================

def run_capacity_analysis():
    """Milestones 3-4: capacity, retention, temperature, CSV and Excel report."""
    from load_data import BATTERIES, load_battery, get_discharge_table
    from plots import (plot_capacity_vs_cycle, plot_retention_vs_cycle,
                       plot_temperature_vs_cycle, save_figure)

    tables = {name: get_discharge_table(load_battery(name)) for name in BATTERIES}

    summary = make_summary_table(tables)
    print("\nCapacity retention and end of life\n")
    print(summary.to_string(index=False), "\n")
    save_table(summary, "capacity_summary.csv")

    retention_tables = {name: add_retention(table) for name, table in tables.items()}

    # Make both figures, so the Excel file always gets the newest versions
    capacity_png = save_figure(plot_capacity_vs_cycle(tables), "capacity_vs_cycle.png")
    retention_png = save_figure(plot_retention_vs_cycle(retention_tables), "retention_vs_cycle.png")
    temperature_png = save_figure(plot_temperature_vs_cycle(tables), "temperature_vs_cycle.png")

    # Excel report: sheet 1 = figures + summary, sheet 2 = all data
    from excel_report import write_capacity_report
    write_capacity_report(summary, retention_tables,
                          [capacity_png, retention_png, temperature_png],
                          RESULTS_FOLDER / "capacity_analysis.xlsx")


def run_resistance_analysis():
    """Milestone 5: Re and Rct vs cycle, and how they relate to capacity."""
    from load_data import BATTERIES, get_all_tables
    from plots import plot_resistance_vs_cycle, plot_capacity_vs_resistance, save_figure

    resistance_tables = {}
    for name in BATTERIES:
        discharge, impedance = get_all_tables(name)
        resistance_tables[name] = add_capacity(resistance_after_discharge(impedance), discharge)

    summary = make_resistance_summary(resistance_tables)
    print("\nResistance growth (tests after discharge, start/end = average of 5 tests)\n")
    print(summary.to_string(index=False), "\n")
    save_table(summary, "resistance_summary.csv")

    resistance_png = save_figure(plot_resistance_vs_cycle(resistance_tables),
                                 "resistance_vs_cycle.png")
    scatter_png = save_figure(plot_capacity_vs_resistance(resistance_tables),
                              "capacity_vs_resistance.png")

    from excel_report import write_resistance_report
    write_resistance_report(summary, resistance_tables, [resistance_png, scatter_png],
                            RESULTS_FOLDER / "resistance_analysis.xlsx")


# Run this file directly to do everything:
#     .venv\Scripts\python.exe src\analysis.py
if __name__ == "__main__":
    from dqdv import run_dqdv_analysis
    run_capacity_analysis()
    run_resistance_analysis()
    run_dqdv_analysis()
