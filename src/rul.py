"""
rul.py
------
Milestone 9: remaining useful life (RUL) with simple curve fits.

Idea: pretend we are at cycle N and only know the capacity up to cycle N.
Fit a curve to that part, extend it into the future, and find the cycle where it
reaches the end-of-life limit (NASA: 1.4 Ah). Because we DO have the real future
data, we can check how good the prediction was.

Two simple models (as planned in CLAUDE.md):
    linear      : C(n) = c0 + s*n        capacity drops by the same AMOUNT every cycle
    exponential : C(n) = a * exp(b*n)    capacity drops by the same PERCENTAGE every cycle

    RUL at cycle N = predicted EOL cycle - N
"""

import numpy as np
import pandas as pd

from analysis import EOL_NASA_AH, first_cycle_below


PREDICTION_CYCLES = (60, 80, 100)   # "we are at cycle N" for the summary table
FIGURE_PREDICTION_CYCLE = 80        # the cycle used for the example figure
FIRST_SWEEP_CYCLE = 20              # earliest cycle for the "prediction vs time" figure
SWEEP_STEP = 5


def fit_linear(cycles, capacity):
    """Straight line through the points. Returns (c0, s): C = c0 + s*n."""
    s, c0 = np.polyfit(cycles, capacity, 1)
    return c0, s


def fit_exponential(cycles, capacity):
    """C = a*exp(b*n). Taking the logarithm gives ln C = ln a + b*n, a straight line,
    so we can use the same simple straight-line fit."""
    b, ln_a = np.polyfit(cycles, np.log(capacity), 1)
    return np.exp(ln_a), b


def linear_curve(params, cycles):
    c0, s = params
    return c0 + s * cycles


def exponential_curve(params, cycles):
    a, b = params
    return a * np.exp(b * cycles)


def eol_from_linear(params, limit_Ah):
    """Cycle where the line reaches the limit. None if the line does not go down."""
    c0, s = params
    return (limit_Ah - c0) / s if s < 0 else None


def eol_from_exponential(params, limit_Ah):
    """Cycle where a*exp(b*n) = limit  ->  n = ln(limit/a) / b. None if it does not go down."""
    a, b = params
    return np.log(limit_Ah / a) / b if b < 0 else None


def predict_from(table, prediction_cycle, limit_Ah=EOL_NASA_AH):
    """Use only the cycles up to 'prediction_cycle'. Returns both fits and both EOL cycles."""
    known = table[table["discharge_number"] <= prediction_cycle]
    n, c = known["discharge_number"].values, known["capacity_Ah"].values
    linear = fit_linear(n, c)
    exponential = fit_exponential(n, c)
    return {
        "linear_params": linear,
        "exponential_params": exponential,
        "linear_eol": eol_from_linear(linear, limit_Ah),
        "exponential_eol": eol_from_exponential(exponential, limit_Ah),
    }


def make_prediction_sweep(table, limit_Ah=EOL_NASA_AH):
    """Predicted EOL cycle when we are at cycle 20, 25, 30, ... (until the real EOL,
    or until the end of the data if the battery never reaches the limit)."""
    actual = first_cycle_below(table, limit_Ah)
    last = actual - 1 if actual is not None else int(table["discharge_number"].max())
    rows = []
    for n in range(FIRST_SWEEP_CYCLE, last + 1, SWEEP_STEP):
        p = predict_from(table, n, limit_Ah)
        rows.append({"prediction_cycle": n,
                     "linear_eol": p["linear_eol"],
                     "exponential_eol": p["exponential_eol"],
                     "actual_eol": actual})
    return pd.DataFrame(rows)


def make_rul_summary(discharge_tables, limit_Ah=EOL_NASA_AH):
    """One row per battery and prediction cycle (60, 80, 100)."""
    rows = []
    for name, table in discharge_tables.items():
        actual = first_cycle_below(table, limit_Ah)
        for n in PREDICTION_CYCLES:
            if actual is not None and n >= actual:
                continue                    # already past end of life: nothing to predict
            p = predict_from(table, n, limit_Ah)
            row = {"battery": name, "prediction_cycle": n, "actual_eol": actual}
            for model in ["linear", "exponential"]:
                eol = p[f"{model}_eol"]
                row[f"{model}_eol"] = None if eol is None else round(eol)
                row[f"{model}_rul"] = None if eol is None else round(eol - n)
                row[f"{model}_error"] = (None if eol is None or actual is None
                                         else round(eol - actual))
            rows.append(row)
    summary = pd.DataFrame(rows)
    for column in summary.columns[1:]:
        summary[column] = summary[column].astype("Int64")   # whole numbers, may be empty
    return summary


def run_rul_analysis():
    """Make the RUL figures, tables and Excel report."""
    from analysis import RESULTS_FOLDER, save_table
    from load_data import BATTERIES, load_battery, get_discharge_table
    from plots import plot_rul_example, plot_rul_sweep, save_figure
    from excel_report import write_rul_report

    tables = {name: get_discharge_table(load_battery(name)) for name in BATTERIES}

    summary = make_rul_summary(tables)
    print(f"\nEnd-of-life prediction (limit {EOL_NASA_AH} Ah). "
          "error = predicted - actual EOL cycle (+ = too late, - = too early)\n")
    print(summary.to_string(index=False), "\n")
    save_table(summary, "rul_summary.csv")

    sweeps = {name: make_prediction_sweep(t) for name, t in tables.items()}
    example_png = save_figure(plot_rul_example(tables, FIGURE_PREDICTION_CYCLE),
                              "rul_prediction_example.png")
    sweep_png = save_figure(plot_rul_sweep(sweeps), "rul_prediction_vs_cycle.png")

    write_rul_report(summary, sweeps, [example_png, sweep_png],
                     RESULTS_FOLDER / "rul_analysis.xlsx")


# Run this file directly:
#     .venv\Scripts\python.exe src\rul.py
if __name__ == "__main__":
    run_rul_analysis()
