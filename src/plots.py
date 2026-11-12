"""
plots.py
--------
All plotting functions, in ONE consistent style copied from Vasilis' thesis
(GCD and colouration-efficiency figures, Chapter 3):

    - Arial, everything bold (numbers, axis labels, legend)
    - thick lines and a thick black frame on all four sides
    - ticks pointing outwards, no grid
    - legend above the plot, in one row, without a box
    - the same five colours as the thesis, in the same order

Every figure is saved as PNG at 300 dpi in the figures/ folder.
"""

import logging
from pathlib import Path

import matplotlib.pyplot as plt

# Hide harmless "findfont: Failed to find font weight bold..." messages.
# matplotlib always loads one maths font (cmex10) that has no bold version.
logging.getLogger("matplotlib.font_manager").setLevel(logging.ERROR)


# Folder where the figures are saved: <project>/figures
FIGURES_FOLDER = Path(__file__).resolve().parent.parent / "figures"

# Colours measured from the thesis figures (same order as in the thesis).
THESIS_COLORS = {
    "grey":   "#515151",
    "red":    "#F14040",
    "blue":   "#1A6FDF",
    "green":  "#37AD6B",
    "purple": "#B177DE",
}

# One fixed colour per battery, used in EVERY figure of the project.
BATTERY_COLORS = {
    "B0005": THESIS_COLORS["grey"],
    "B0006": THESIS_COLORS["red"],
    "B0007": THESIS_COLORS["blue"],
    "B0018": THESIS_COLORS["green"],
}

# Line and frame thickness (in points). Change these to make all plots thicker/thinner.
LINE_WIDTH = 2.2
FRAME_WIDTH = 1.8


def apply_thesis_style():
    """Set matplotlib's defaults so every plot looks like the thesis plots."""
    plt.rcParams.update({
        # Font: Arial, bold everywhere
        "font.family": "sans-serif",
        "font.sans-serif": ["Arial", "Helvetica", "DejaVu Sans"],
        "font.weight": "bold",
        "axes.labelweight": "bold",
        # Maths text (subscripts like R$_e$) also in bold Arial, not matplotlib's own fonts
        "mathtext.fontset": "custom",
        "mathtext.rm": "Arial:bold",
        "mathtext.it": "Arial:bold:italic",
        "mathtext.bf": "Arial:bold",
        "mathtext.default": "bf",
        "mathtext.fallback": None,         # no backup maths fonts (avoids "findfont" warnings)
        # Font sizes
        "font.size": 13,
        "axes.labelsize": 17,
        "xtick.labelsize": 14,
        "ytick.labelsize": 14,
        "legend.fontsize": 14,
        # Thick black frame on all four sides
        "axes.linewidth": FRAME_WIDTH,
        "axes.edgecolor": "black",
        # Ticks: outwards, thick, only on the bottom and left axes
        "xtick.direction": "out",
        "ytick.direction": "out",
        "xtick.major.size": 6,
        "ytick.major.size": 6,
        "xtick.major.width": FRAME_WIDTH,
        "ytick.major.width": FRAME_WIDTH,
        # Lines
        "lines.linewidth": LINE_WIDTH,
        # No grid, white background
        "axes.grid": False,
        "figure.facecolor": "white",
        # Saving
        "savefig.dpi": 300,
        "savefig.bbox": "tight",
    })


def add_legend_on_top(ax, columns):
    """Legend above the plot, without a box, like in the thesis."""
    ax.legend(loc="lower center", bbox_to_anchor=(0.5, 1.0), ncol=columns,
              frameon=False, handlelength=2.2, columnspacing=1.6)


def save_figure(fig, file_name):
    """Save a figure in figures/ as a 300 dpi PNG and tell the user where it is."""
    FIGURES_FOLDER.mkdir(exist_ok=True)
    path = FIGURES_FOLDER / file_name
    try:
        fig.savefig(path)
        print(f"Saved: {path}")
    except OSError:
        # Windows "locks" a file while another program (e.g. Photos) has it open
        print(f"\nCould NOT save {path}")
        print("The image is probably open in another program. Close it and run again.\n")
    plt.close(fig)                  # free the memory used by the figure
    return path


def plot_capacity_vs_cycle(discharge_tables, eol_capacity_Ah=1.4):
    """Milestone 3: discharge capacity vs cycle number, all batteries on one graph.

    discharge_tables : dictionary like {"B0005": table, "B0006": table, ...}
                       (each table comes from load_data.get_discharge_table)
    eol_capacity_Ah  : end-of-life line (NASA README: 30% fade of 2 Ah = 1.4 Ah)
    """
    apply_thesis_style()
    fig, ax = plt.subplots(figsize=(6.5, 5))

    # One line per battery
    for name, table in discharge_tables.items():
        ax.plot(table["discharge_number"], table["capacity_Ah"],
                color=BATTERY_COLORS[name], label=name)

    # Dashed end-of-life line, with a small label at the left end (empty area there)
    ax.axhline(eol_capacity_Ah, color="black", linestyle="--", linewidth=1.5)
    ax.text(4, eol_capacity_Ah + 0.015, f"EOL ({eol_capacity_Ah} Ah)",
            ha="left", va="bottom", fontsize=13)

    # Axes: labels with units, limits and tick spacing
    ax.set_xlabel("Cycle number")
    ax.set_ylabel("Capacity (Ah)")
    ax.set_xlim(0, 200)
    ax.set_ylim(1.0, 2.1)
    ax.set_xticks(range(0, 201, 25))
    ax.set_yticks([1.0, 1.2, 1.4, 1.6, 1.8, 2.0])
    ax.yaxis.set_major_formatter("{x:.1f}")   # always one decimal: 1.0, 1.2, ...

    add_legend_on_top(ax, columns=4)
    return fig


def plot_retention_vs_cycle(retention_tables):
    """Milestone 4: capacity retention (% of cycle 1) vs cycle number.

    retention_tables : {"B0005": table, ...}, tables from analysis.add_retention
    """
    apply_thesis_style()
    fig, ax = plt.subplots(figsize=(6.5, 5))

    for name, table in retention_tables.items():
        ax.plot(table["discharge_number"], table["retention_vs_first_pct"],
                color=BATTERY_COLORS[name], label=name)

    ax.set_xlabel("Cycle number")
    ax.set_ylabel("Capacity retention (%)")
    ax.set_xlim(0, 200)
    ax.set_ylim(50, 105)
    ax.set_xticks(range(0, 201, 25))
    ax.set_yticks(range(50, 101, 10))

    add_legend_on_top(ax, columns=4)
    return fig


def plot_temperature_vs_cycle(discharge_tables):
    """Highest cell temperature reached during each discharge vs cycle number.

    discharge_tables : {"B0005": table, ...} from load_data.get_discharge_table
    """
    apply_thesis_style()
    fig, ax = plt.subplots(figsize=(6.5, 5))

    for name, table in discharge_tables.items():
        ax.plot(table["discharge_number"], table["max_temperature_C"],
                color=BATTERY_COLORS[name], label=name)

    ax.set_xlabel("Cycle number")
    ax.set_ylabel("Max temperature (°C)")
    ax.set_xlim(0, 200)
    ax.set_ylim(35, 44)
    ax.set_xticks(range(0, 201, 25))
    ax.set_yticks(range(35, 45, 1))

    add_legend_on_top(ax, columns=4)
    return fig


# Marker shapes per battery, like the thesis scatter plots (square, circle, triangle...)
BATTERY_MARKERS = {"B0005": "s", "B0006": "o", "B0007": "^", "B0018": "D"}


def add_panel_label(ax, text):
    """Bold '(a)', '(b)' label at the top-left, outside the plot, like the thesis."""
    ax.text(-0.16, 1.10, text, transform=ax.transAxes,
            fontsize=20, fontweight="bold", va="bottom")


def plot_resistance_vs_cycle(resistance_tables):
    """Milestone 5: (a) Re and (b) Rct vs cycle number, side by side.

    resistance_tables : {"B0005": table, ...} from analysis.resistance_after_discharge
    """
    apply_thesis_style()
    fig, (ax_re, ax_rct) = plt.subplots(1, 2, figsize=(13, 5))

    for name, table in resistance_tables.items():
        ax_re.plot(table["cycle_number"], table["Re_mohm"],
                   color=BATTERY_COLORS[name], label=name)
        ax_rct.plot(table["cycle_number"], table["Rct_mohm"],
                    color=BATTERY_COLORS[name], label=name)

    ax_re.set_ylabel("R$_e$ (mΩ)")
    ax_re.set_ylim(30, 80)
    ax_rct.set_ylabel("R$_{ct}$ (mΩ)")
    ax_rct.set_ylim(50, 110)
    for ax, label in [(ax_re, "(a)"), (ax_rct, "(b)")]:
        ax.set_xlabel("Cycle number")
        ax.set_xlim(0, 200)
        ax.set_xticks(range(0, 201, 25))
        add_panel_label(ax, label)

    # One shared legend above both panels
    handles, labels = ax_re.get_legend_handles_labels()
    fig.legend(handles, labels, loc="lower center", bbox_to_anchor=(0.5, 0.93),
               ncol=4, frameon=False, handlelength=2.2, columnspacing=1.6)
    fig.subplots_adjust(wspace=0.3, top=0.85)
    return fig


def plot_capacity_vs_resistance(resistance_tables):
    """Milestone 5: capacity vs total resistance (Re + Rct), one point per test.
    The legend shows the correlation r for each battery."""
    apply_thesis_style()
    fig, ax = plt.subplots(figsize=(6.5, 5))

    for name, table in resistance_tables.items():
        r = table["total_mohm"].corr(table["capacity_Ah"])
        ax.scatter(table["total_mohm"], table["capacity_Ah"],
                   color=BATTERY_COLORS[name], marker=BATTERY_MARKERS[name],
                   s=22, alpha=0.8, linewidths=0,
                   label=f"{name} (r = {r:.2f})".replace("-", "−"))  # real minus sign

    ax.set_xlabel("R$_e$ + R$_{ct}$ (mΩ)")
    ax.set_ylabel("Capacity (Ah)")
    ax.set_xlim(100, 190)
    ax.set_ylim(1.0, 2.1)
    ax.set_yticks([1.0, 1.2, 1.4, 1.6, 1.8, 2.0])
    ax.yaxis.set_major_formatter("{x:.1f}")

    ax.legend(loc="lower center", bbox_to_anchor=(0.5, 1.0), ncol=2, frameon=False,
              markerscale=2, handletextpad=0.3, columnspacing=1.2)
    return fig


def plot_dqdv_curves(curves_by_battery, cycles_to_show=(1, 40, 80, 120)):
    """dQ/dV curves, one panel per battery: cycles 1, 40, 80, 120 and the last cycle.
    Colours = thesis order (grey, red, blue, green, purple), like thesis Fig. 3.5.

    curves_by_battery : {"B0005": [(cycle, Q, V), ...], ...} from dqdv.get_discharge_curves
    """
    from dqdv import incremental_capacity

    apply_thesis_style()
    fig, axes = plt.subplots(2, 2, figsize=(12, 9.5))
    colours = list(THESIS_COLORS.values())

    for ax, label, (name, curves) in zip(axes.flat, ["(a)", "(b)", "(c)", "(d)"],
                                         curves_by_battery.items()):
        chosen = list(cycles_to_show) + [len(curves)]       # add the last cycle
        for colour, cycle_number in zip(colours, chosen):
            _, q, v = curves[cycle_number - 1]
            voltage, dqdv = incremental_capacity(q, v)
            ax.plot(voltage, dqdv, color=colour, label=f"Cycle {cycle_number}")

        ax.set_xlabel("V (V)")
        ax.set_ylabel("dQ/dV (Ah/V)")
        ax.set_xlim(2.8, 4.0)
        ax.set_ylim(0, 7)
        ax.legend(loc="upper left", frameon=False, fontsize=12, title=name,
                  title_fontproperties={"weight": "bold", "size": 14})
        add_panel_label(ax, label)

    fig.subplots_adjust(wspace=0.3, hspace=0.45)
    return fig


def plot_dqdv_peak_vs_cycle(peak_tables):
    """(a) main dQ/dV peak position and (b) its height vs cycle number."""
    apply_thesis_style()
    fig, (ax_pos, ax_height) = plt.subplots(1, 2, figsize=(13, 5))

    for name, table in peak_tables.items():
        ax_pos.plot(table["cycle_number"], table["peak_voltage_V"],
                    color=BATTERY_COLORS[name], label=name)
        ax_height.plot(table["cycle_number"], table["peak_height_Ah_per_V"],
                       color=BATTERY_COLORS[name], label=name)

    ax_pos.set_ylabel("Peak position (V)")
    ax_pos.set_ylim(3.2, 3.6)
    ax_height.set_ylabel("Peak height (Ah/V)")
    ax_height.set_ylim(0, 7)
    for ax, label in [(ax_pos, "(a)"), (ax_height, "(b)")]:
        ax.set_xlabel("Cycle number")
        ax.set_xlim(0, 200)
        ax.set_xticks(range(0, 201, 25))
        add_panel_label(ax, label)

    handles, labels = ax_pos.get_legend_handles_labels()
    fig.legend(handles, labels, loc="lower center", bbox_to_anchor=(0.5, 0.93),
               ncol=4, frameon=False, handlelength=2.2, columnspacing=1.6)
    fig.subplots_adjust(wspace=0.3, top=0.85)
    return fig


# Run this file directly to make the Milestone 3 figure:
#     .venv\Scripts\python.exe src\plots.py
if __name__ == "__main__":
    from load_data import BATTERIES, load_battery, get_discharge_table

    tables = {}
    for name in BATTERIES:
        tables[name] = get_discharge_table(load_battery(name))
        print(f"{name}: {len(tables[name])} discharge cycles loaded")

    figure = plot_capacity_vs_cycle(tables)
    save_figure(figure, "capacity_vs_cycle.png")
