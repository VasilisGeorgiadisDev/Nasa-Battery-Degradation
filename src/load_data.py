"""
load_data.py
------------
Read the NASA battery .mat files and turn them into pandas tables (DataFrames).

Each .mat file holds one battery. Inside it there is a list called "cycle".
Every cycle is one experiment step: "charge", "discharge" or "impedance".

This file gives you three simple functions:
    load_battery(name)        -> the raw list of cycles (Python dictionaries)
    get_discharge_table(...)  -> one row per discharge: capacity, temperature, ...
    get_impedance_table(...)  -> one row per impedance test: Re, Rct
"""

from pathlib import Path   # a tidy way to build file paths (works on Windows too)
from datetime import datetime

import numpy as np
import pandas as pd
import scipy.io


# Folder where the .mat files live: <project>/data
# __file__ is this file (src/load_data.py), so .parent.parent is the project folder.
DATA_FOLDER = Path(__file__).resolve().parent.parent / "data"

# The four batteries in the dataset
BATTERIES = ["B0005", "B0006", "B0007", "B0018"]


def load_battery(name):
    """Open one .mat file (e.g. 'B0005') and return its list of cycles.

    simplify_cells=True tells scipy to turn MATLAB structures into normal
    Python dictionaries, which are much easier to read.
    """
    file_path = DATA_FOLDER / f"{name}.mat"
    mat = scipy.io.loadmat(file_path, simplify_cells=True)
    return mat[name]["cycle"]   # a Python list; each item is one cycle


def matlab_time_to_datetime(time_vector):
    """MATLAB stores the start time as [year, month, day, hour, minute, second].
    Turn that into a normal Python date-and-time."""
    year, month, day, hour, minute, second = time_vector
    whole_seconds = int(second)
    microseconds = int(round((second - whole_seconds) * 1e6))
    return datetime(int(year), int(month), int(day),
                    int(hour), int(minute), whole_seconds, min(microseconds, 999999))


def get_discharge_table(cycles):
    """Make a table with one row per discharge cycle."""
    rows = []
    discharge_number = 0
    for index, cycle in enumerate(cycles):
        if cycle["type"] != "discharge":
            continue                      # skip charge and impedance cycles
        discharge_number += 1
        data = cycle["data"]
        rows.append({
            "discharge_number": discharge_number,      # 1, 2, 3, ... (the "cycle number")
            "index_in_file": index,                    # position in the full list of cycles
            "start_time": matlab_time_to_datetime(cycle["time"]),
            "ambient_temperature_C": cycle["ambient_temperature"],
            "capacity_Ah": float(data["Capacity"]),
            "duration_s": float(data["Time"][-1]),     # last time point = how long it took
            "max_temperature_C": float(np.max(data["Temperature_measured"])),
            "min_voltage_V": float(np.min(data["Voltage_measured"])),
        })
    return pd.DataFrame(rows)


def get_impedance_table(cycles):
    """Make a table with one row per impedance (EIS) measurement.

    Impedance tests are NOT done on every cycle, so we also store:
      cycle_number  : how many discharges were done before this test
                      (so we can put Re and Rct on the same x-axis as capacity)
      previous_step : what was done just before the test ("charge" or "discharge").
                      After "discharge" the cell is empty, after "charge" it is full.
    """
    rows = []
    impedance_number = 0
    discharges_so_far = 0
    for index, cycle in enumerate(cycles):
        if cycle["type"] == "discharge":
            discharges_so_far += 1
        if cycle["type"] != "impedance":
            continue
        impedance_number += 1
        data = cycle["data"]
        rows.append({
            "impedance_number": impedance_number,
            "cycle_number": discharges_so_far,
            "previous_step": cycles[index - 1]["type"] if index > 0 else "start",
            "index_in_file": index,
            "start_time": matlab_time_to_datetime(cycle["time"]),
            "ambient_temperature_C": cycle["ambient_temperature"],
            "Re_ohm": float(data["Re"]),     # electrolyte resistance
            "Rct_ohm": float(data["Rct"]),   # charge transfer resistance
        })
    return pd.DataFrame(rows)


def get_all_tables(name):
    """Load one battery and return (discharge table, impedance table)."""
    cycles = load_battery(name)
    return get_discharge_table(cycles), get_impedance_table(cycles)


# This part only runs when you start the file directly:
#     .venv\Scripts\python.exe src\load_data.py
# It prints a short summary of battery B0005 so we can check the loading works.
if __name__ == "__main__":
    name = "B0005"
    cycles = load_battery(name)

    print(f"Battery {name}: {len(cycles)} cycles in total")
    types = pd.Series([c["type"] for c in cycles]).value_counts()
    print(types.to_string(), "\n")

    discharge = get_discharge_table(cycles)
    print("First 5 discharge cycles:")
    print(discharge.head().to_string(index=False), "\n")
    print("Last 5 discharge cycles:")
    print(discharge.tail().to_string(index=False), "\n")

    impedance = get_impedance_table(cycles)
    print("First 5 impedance measurements:")
    print(impedance.head().to_string(index=False))
