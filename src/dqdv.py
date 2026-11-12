"""
dqdv.py
-------
Incremental capacity analysis (dQ/dV) of the discharge curves.

Idea (similar to a CV): while the cell discharges at constant current, we ask
"how much charge flows while the voltage drops by 10 mV?". Where the voltage
curve has a plateau, a lot of charge flows in a small voltage window, so dQ/dV
shows a PEAK. Each peak belongs to an electrochemical process in the electrodes.

How ageing changes the peaks:
    peak moves to lower voltage   -> more polarisation (resistance, diffusion), or the
                                     two electrodes "slide" against each other when
                                     lithium is lost (full cell)
    less area under the curve     -> charge is really missing
                                     (lost lithium or lost active material)

Main functions:
    discharge_curve(data)           -> charge Q (Ah) and voltage V while the load is on
    incremental_capacity(q, v)      -> voltage grid and dQ/dV (Ah/V)
    find_main_peak(voltage, dqdv)   -> position (V) and height (Ah/V) of the biggest peak
    run_dqdv_analysis()             -> figures + CSV tables
"""

import numpy as np
import pandas as pd

from load_data import BATTERIES, load_battery


VOLTAGE_STEP = 0.010     # 10 mV voltage windows ("bins")
LOAD_CURRENT_LIMIT = 1.0 # the load is "on" when |current| > 1 A (it is 2 A in this test)
CURRENT_A = 2.0          # discharge current of the test (NASA README)
CYCLES_TO_SHOW = (1, 40, 80, 120)   # curves shown in the figure (+ the last cycle)


def discharge_curve(data):
    """Return Q (Ah, charge delivered so far) and V (V) for the part with the 2 A load on.

    Before the load starts and after it stops, the current is ~0 and the voltage
    relaxes; those points are removed.
    """
    time = data["Time"]
    current = np.abs(data["Current_measured"])
    voltage = data["Voltage_measured"]

    load_on = np.where(current > LOAD_CURRENT_LIMIT)[0]
    start, end = load_on[0], load_on[-1]
    time = time[start:end + 1]
    current = current[start:end + 1]
    voltage = voltage[start:end + 1]

    # Q = integral of I dt (trapezoid rule), converted from A*s to Ah
    charge_steps = 0.5 * (current[1:] + current[:-1]) * np.diff(time)
    q = np.concatenate([[0.0], np.cumsum(charge_steps)]) / 3600
    return q, voltage


def incremental_capacity(q, v, step=VOLTAGE_STEP):
    """dQ/dV: charge delivered in each voltage window of width 'step', divided by step.

    Returns (voltage at the centre of each window, dQ/dV in Ah/V).
    The values are positive (we use the size of the discharge dQ/dV).
    """
    # Voltage must only go down; remove tiny upward noise (there is almost none here)
    v_down = np.minimum.accumulate(v)
    edges = np.arange(v_down.max(), v_down.min(), -step)          # e.g. 3.98, 3.97, ...
    # charge delivered when the voltage reaches each edge (np.interp needs increasing x)
    q_at_edges = np.interp(edges[::-1], v_down[::-1], q[::-1])[::-1]
    centres = 0.5 * (edges[1:] + edges[:-1])
    return centres, np.diff(q_at_edges) / step


def find_main_peak(voltage, dqdv):
    """Position and height of the biggest peak.

    A parabola through the highest point and its two neighbours gives a position
    more precise than the 10 mV window size.
    """
    k = int(np.argmax(dqdv))
    if k == 0 or k == len(dqdv) - 1:
        return voltage[k], dqdv[k]
    left, top, right = dqdv[k - 1], dqdv[k], dqdv[k + 1]
    offset = 0.5 * (left - right) / (left - 2 * top + right)       # in units of windows
    window = voltage[k] - voltage[k + 1]
    position = voltage[k] - offset * window
    height = top - 0.25 * (left - right) * offset
    return position, height


def get_discharge_curves(name):
    """All discharge curves of one battery: list of (cycle number, Q, V)."""
    cycles = load_battery(name)
    discharges = [c for c in cycles if c["type"] == "discharge"]
    return [(n + 1, *discharge_curve(c["data"])) for n, c in enumerate(discharges)]


def make_peak_table(curves):
    """One row per cycle: capacity from the curve, main peak position and height."""
    rows = []
    for cycle_number, q, v in curves:
        voltage, dqdv = incremental_capacity(q, v)
        position, height = find_main_peak(voltage, dqdv)
        rows.append({
            "cycle_number": cycle_number,
            "capacity_from_curve_Ah": q[-1],
            "peak_voltage_V": position,
            "peak_height_Ah_per_V": height,
        })
    return pd.DataFrame(rows)


def make_curve_table(curves, cycles_to_show=CYCLES_TO_SHOW):
    """The dQ/dV curves of the figure as a table, for Excel.

    Every cycle has slightly different voltages, so all curves are put on the
    same voltage grid (4.00, 3.99, ... 2.80 V). Voltages a cycle never reached stay empty.
    Columns: voltage_V, cycle_1, cycle_40, ..., cycle_<last>
    """
    grid = np.round(np.arange(4.00, 2.795, -VOLTAGE_STEP), 3)
    table = pd.DataFrame({"voltage_V": grid})
    for cycle_number in list(cycles_to_show) + [len(curves)]:
        _, q, v = curves[cycle_number - 1]
        voltage, dqdv = incremental_capacity(q, v)
        # np.interp needs increasing voltages, so reverse; outside the curve -> NaN (empty)
        table[f"cycle_{cycle_number}"] = np.interp(grid, voltage[::-1], dqdv[::-1],
                                                    left=np.nan, right=np.nan)
    return table


def capacity_lost_by_voltage_shift(q, v, shift_V):
    """Worst-case test: if the WHOLE curve only moved down by shift_V (pure polarisation),
    how much capacity would be lost before reaching the same cut-off voltage?"""
    cutoff = v.min()
    q_at_shifted_cutoff = np.interp(cutoff + shift_V, v[::-1], q[::-1])
    return q[-1] - q_at_shifted_cutoff


def make_dqdv_summary(peak_tables, curves_by_battery, eis_increase_mohm, points=5):
    """One row per battery. 'start'/'end' = average of the first/last 5 cycles."""
    rows = []
    for name, table in peak_tables.items():
        start, end = table.head(points).mean(), table.tail(points).mean()
        shift_V = end["peak_voltage_V"] - start["peak_voltage_V"]
        _, q_first, v_first = curves_by_battery[name][0]
        lost_by_shift = capacity_lost_by_voltage_shift(q_first, v_first, abs(shift_V))
        real_loss = start["capacity_from_curve_Ah"] - end["capacity_from_curve_Ah"]
        rows.append({
            "battery": name,
            "peak_start_V": round(start["peak_voltage_V"], 3),
            "peak_end_V": round(end["peak_voltage_V"], 3),
            "peak_shift_mV": round(1000 * shift_V),
            # what the EIS resistance growth alone would predict: shift = -I * dR
            "eis_predicted_shift_mV": round(-CURRENT_A * eis_increase_mohm[name]),
            "peak_height_change_pct": round(
                100 * (end["peak_height_Ah_per_V"] / start["peak_height_Ah_per_V"] - 1)),
            "capacity_change_pct": round(
                100 * (end["capacity_from_curve_Ah"] / start["capacity_from_curve_Ah"] - 1)),
            # share of the real capacity loss that a pure voltage shift could explain
            "loss_explained_by_shift_pct": round(100 * lost_by_shift / real_loss, 1),
        })
    return pd.DataFrame(rows)


def run_dqdv_analysis():
    """Make the dQ/dV figures and tables."""
    from analysis import (save_table, resistance_after_discharge, add_capacity,
                          make_resistance_summary)
    from load_data import get_all_tables
    from plots import plot_dqdv_curves, plot_dqdv_peak_vs_cycle, save_figure

    curves_by_battery = {name: get_discharge_curves(name) for name in BATTERIES}
    peak_tables = {name: make_peak_table(c) for name, c in curves_by_battery.items()}

    # EIS resistance growth (Re + Rct) from Milestone 5, to compare with the peak shift
    resistance_tables = {}
    for name in BATTERIES:
        discharge, impedance = get_all_tables(name)
        resistance_tables[name] = add_capacity(resistance_after_discharge(impedance), discharge)
    r = make_resistance_summary(resistance_tables).set_index("battery")
    eis_increase_mohm = {name: (r.loc[name, "Re_end_mohm"] + r.loc[name, "Rct_end_mohm"])
                         - (r.loc[name, "Re_start_mohm"] + r.loc[name, "Rct_start_mohm"])
                         for name in BATTERIES}

    summary = make_dqdv_summary(peak_tables, curves_by_battery, eis_increase_mohm)
    print("\ndQ/dV main peak (start/end = average of 5 cycles)\n")
    print(summary.to_string(index=False), "\n")
    save_table(summary, "dqdv_summary.csv")
    all_peaks = pd.concat([t.assign(battery=n) for n, t in peak_tables.items()])
    save_table(all_peaks.round(4), "dqdv_peaks_per_cycle.csv")

    curves_png = save_figure(plot_dqdv_curves(curves_by_battery, CYCLES_TO_SHOW),
                             "dqdv_curves.png")
    peaks_png = save_figure(plot_dqdv_peak_vs_cycle(peak_tables), "dqdv_peak_vs_cycle.png")

    from analysis import RESULTS_FOLDER
    from excel_report import write_dqdv_report
    curve_tables = {name: make_curve_table(c) for name, c in curves_by_battery.items()}
    write_dqdv_report(summary, peak_tables, curve_tables, [curves_png, peaks_png],
                      RESULTS_FOLDER / "dqdv_analysis.xlsx")


# Run this file directly:
#     .venv\Scripts\python.exe src\dqdv.py
if __name__ == "__main__":
    run_dqdv_analysis()
