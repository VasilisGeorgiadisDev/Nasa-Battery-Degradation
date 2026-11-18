r"""
main.py
-------
A simple numbered menu, like Vasilis' thesis tool: press 1, 2, 3... to run
each analysis. Start it from the project folder with:

    .venv\Scripts\python.exe src\main.py
"""

import os

from analysis import run_capacity_analysis, run_resistance_analysis, RESULTS_FOLDER
from dqdv import run_dqdv_analysis
from rul import run_rul_analysis
from plots import FIGURES_FOLDER


def run_everything():
    """Options 1 to 4 one after the other."""
    run_capacity_analysis()
    run_resistance_analysis()
    run_dqdv_analysis()
    run_rul_analysis()


def open_in_windows(path):
    """Open a folder or file with the normal Windows program (Explorer, Excel...)."""
    if not path.exists():
        print(f"Not found: {path}  (run the analysis first)")
    elif hasattr(os, "startfile"):            # os.startfile exists only on Windows
        os.startfile(path)
    else:
        print(f"Open this yourself: {path}")


# Each menu option: (key to press, text shown, function to run)
MENU = [
    ("1", "Capacity: capacity, retention, temperature (+ Excel)", run_capacity_analysis),
    ("2", "Resistance: Re and Rct vs cycle, EIS (+ Excel)",       run_resistance_analysis),
    ("3", "dQ/dV: incremental capacity analysis (+ Excel)",       run_dqdv_analysis),
    ("4", "RUL: predict the end of life (+ Excel)",               run_rul_analysis),
    ("5", "Run everything (1 + 2 + 3 + 4)",                       run_everything),
    ("6", "Open the figures folder",          lambda: open_in_windows(FIGURES_FOLDER)),
    ("7", "Open the results folder (Excel reports)",
          lambda: open_in_windows(RESULTS_FOLDER)),
]


def show_menu():
    print("\n" + "=" * 62)
    print("  NASA Li-ion Battery Degradation Analyser")
    print("=" * 62)
    for key, text, _ in MENU:
        print(f"  {key}. {text}")
    print("  0. Exit")
    print("-" * 62)


def main():
    while True:                                   # repeat until the user presses 0
        show_menu()
        # strip() removes spaces; "﻿" is an invisible character some terminals add
        choice = input("Choose an option: ").strip().lstrip("﻿")

        if choice == "0":
            print("Bye!")
            break

        # Find the option the user chose
        actions = {key: function for key, _, function in MENU}
        if choice not in actions:
            print(f"'{choice}' is not an option. Please type a number from the menu.")
            continue

        try:
            actions[choice]()
            print("\nDone.")
        except Exception as error:                # show the problem, but keep the menu open
            print(f"\nSomething went wrong: {error}")


if __name__ == "__main__":
    main()
