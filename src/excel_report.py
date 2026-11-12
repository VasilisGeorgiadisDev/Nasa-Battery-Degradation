"""
excel_report.py
---------------
Formatted Excel reports, all in the same style (asked by Vasilis):

    header rows -> dark blue background, white bold text
    data rows   -> alternating light blue / white ("banded rows")

Three reports, all built from the same helper functions:

    write_capacity_report()   -> results/capacity_analysis.xlsx
    write_resistance_report() -> results/resistance_analysis.xlsx
    write_dqdv_report()       -> results/dqdv_analysis.xlsx

Each report has:
    Sheet "Summary" : the figures side by side, then small tables and short notes
    Sheet "Data"    : every measurement, one block of columns per battery,
                      with one empty column between the blocks
"""

import pandas as pd
import xlsxwriter
from PIL import Image          # only used to read the size of the PNG files


# ----- Colours and sizes (change them here) -----------------------------------
DARK_BLUE = "#1F3864"
LIGHT_BLUE = "#DDEBF7"
WHITE = "#FFFFFF"
BORDER_GREY = "#B4C6E7"

SUMMARY_COLUMN_WIDTH = 15   # width of the table columns on the Summary sheet
GAP_WIDTH = 3               # width of the empty column between two batteries


# =============================================================================
# Building blocks used by all three reports
# =============================================================================

def make_formats(workbook):
    """Create the fixed cell styles: headers, titles and notes."""
    header = {"bold": True, "font_color": WHITE, "bg_color": DARK_BLUE,
              "align": "center", "valign": "vcenter", "text_wrap": True,
              "border": 1, "border_color": DARK_BLUE}
    return {
        "workbook": workbook,
        "header": workbook.add_format(header),
        "block_title": workbook.add_format({**header, "font_size": 13}),
        "page_title": workbook.add_format({"bold": True, "font_size": 16,
                                           "font_color": DARK_BLUE}),
        "table_title": workbook.add_format({"bold": True, "font_size": 12,
                                            "font_color": DARK_BLUE}),
        "note": workbook.add_format({"italic": True, "font_color": "#595959"}),
    }


def row_format(formats, colour_name, number_format):
    """Style of a data cell: light blue or white, with a number format.
    Each style is created the first time it is needed, then reused."""
    key = (colour_name, number_format)
    if key not in formats:
        settings = {"bg_color": LIGHT_BLUE if colour_name == "light" else WHITE,
                    "align": "center", "border": 1, "border_color": BORDER_GREY}
        if number_format:
            settings["num_format"] = number_format
        formats[key] = formats["workbook"].add_format(settings)
    return formats[key]


def write_table(sheet, first_row, first_col, table, columns, formats,
                empty_text="Not reached"):
    """Write a pandas table: dark blue header row, then banded rows.

    columns    : list of (pandas column, header text, number format)
                 number format: "0.0000" = 4 decimals, "0.0" = 1 decimal, "0" = whole number
    empty_text : what to write in empty cells
    Returns the row number just below the table.
    """
    sheet.set_row(first_row, 36)                       # taller, so 2-line headers fit
    for i, (_, header_text, _) in enumerate(columns):
        sheet.write(first_row, first_col + i, header_text, formats["header"])

    for n, (_, values) in enumerate(table.iterrows()):
        row = first_row + 1 + n
        colour_name = "light" if n % 2 == 0 else "white"
        for i, (column_name, _, number_format) in enumerate(columns):
            value = values[column_name]
            cell_format = row_format(formats, colour_name, number_format)
            if pd.isna(value):
                sheet.write(row, first_col + i, empty_text, cell_format)
            elif isinstance(value, pd.Timestamp):
                sheet.write_datetime(row, first_col + i, value.to_pydatetime(), cell_format)
            else:
                sheet.write(row, first_col + i, value, cell_format)
    return first_row + 1 + len(table)


def insert_figures(sheet, first_row, figure_paths, scale):
    """Put the PNG figures side by side. Returns the first free row below them."""
    x_offset = 0
    tallest = 0
    for path in figure_paths:
        width_px, height_px = Image.open(path).size
        # PNGs are 300 dpi; Excel shows images at 96 dpi
        shown_width = width_px * 96 / 300 * scale
        shown_height = height_px * 96 / 300 * scale
        sheet.insert_image(first_row, 0, str(path), {
            "x_offset": x_offset, "y_offset": 0, "x_scale": scale, "y_scale": scale,
            "object_position": 3,                      # don't stretch when columns change
        })
        x_offset += shown_width + 15                   # small gap between figures
        tallest = max(tallest, shown_height)
    return first_row + int(tallest / 20) + 2           # a normal Excel row is 20 px tall


def write_summary_sheet(formats, title, figure_paths, figure_scale, tables, notes):
    """Sheet "Summary": title, figures, then the small tables and the notes.

    tables : list of (table title, pandas table, columns)
    """
    sheet = formats["workbook"].add_worksheet("Summary")
    sheet.hide_gridlines(2)                            # clean white background
    sheet.set_column(0, 12, SUMMARY_COLUMN_WIDTH)
    sheet.write(0, 0, title, formats["page_title"])

    row = insert_figures(sheet, 2, figure_paths, figure_scale)
    for table_title, table, columns in tables:
        sheet.write(row, 0, table_title, formats["table_title"])
        row = write_table(sheet, row + 1, 0, table, columns, formats) + 2

    for i, line in enumerate(notes):
        sheet.write(row - 1 + i, 0, line, formats["note"])


def write_battery_blocks(formats, sheet_name, tables_by_battery, block_columns,
                         empty_text=""):
    """A sheet with one block of columns per battery, one empty column between blocks.

    block_columns : list of (pandas column, header text, width, number format),
                    or a dictionary {battery: that list} if the headers differ per battery
    """
    sheet = formats["workbook"].add_worksheet(sheet_name)

    first_col = 0
    for battery, table in tables_by_battery.items():
        spec = block_columns[battery] if isinstance(block_columns, dict) else block_columns
        last_col = first_col + len(spec) - 1

        # Row 1: battery name across the whole block (merged cells)
        sheet.merge_range(0, first_col, 0, last_col, battery, formats["block_title"])
        # Row 2 and below: header and data
        columns = [(name, header, fmt) for name, header, _, fmt in spec]
        write_table(sheet, 1, first_col, table, columns, formats, empty_text)

        for i, (_, _, width, _) in enumerate(spec):
            sheet.set_column(first_col + i, first_col + i, width)
        sheet.set_column(last_col + 1, last_col + 1, GAP_WIDTH)
        first_col = last_col + 2                       # +1 empty column

    sheet.set_row(0, 22)
    sheet.freeze_panes(2, 0)                           # titles + headers stay visible


def save_workbook(workbook, excel_path):
    """Save. If the file is open in Excel, Windows does not allow overwriting it."""
    try:
        workbook.close()
        print(f"Saved: {excel_path}")
    except (PermissionError, xlsxwriter.exceptions.FileCreateError):
        print(f"\nCould NOT save {excel_path}")
        print("The file is probably open in Excel. Close it and run the script again.\n")


# =============================================================================
# Report 1: capacity
# =============================================================================

def write_capacity_report(summary, retention_tables, figure_paths, excel_path):
    """summary from analysis.make_summary_table, retention_tables from analysis.add_retention"""
    workbook = xlsxwriter.Workbook(excel_path)
    formats = make_formats(workbook)

    overview = [
        ("battery",            "Battery",                       None),
        ("cutoff_voltage_V",   "Cut-off voltage (V)",           "0.0"),
        ("number_of_cycles",   "Cycles tested",                 "0"),
        ("first_capacity_Ah",  "Initial capacity (Ah)",         "0.0000"),
        ("last_capacity_Ah",   "Final capacity (Ah)",           "0.0000"),
        ("fade_vs_rated_pct",  "Fade vs rated 2.0 Ah (%)",      "0.0"),
        ("fade_vs_first_pct",  "Fade vs initial capacity (%)",  "0.0"),
    ]
    end_of_life = [
        ("battery",                    "Battery",                                     None),
        ("cycle_below_1.6Ah_80pct",    "Industry EOL cycle\n(80% of rated = 1.6 Ah)", "0"),
        ("cycle_below_1.4Ah_NASA_EOL", "NASA lab EOL cycle\n(70% of rated = 1.4 Ah)", "0"),
    ]
    write_summary_sheet(
        formats, "NASA Li-ion battery ageing: capacity", figure_paths, 0.6,
        [("Table 1. Battery overview", summary, overview),
         ("Table 2. End of life (EOL): industry vs NASA lab", summary, end_of_life)],
        ["Source: NASA Ames PCoE, Li-ion Battery Aging Datasets. Rated capacity 2.0 Ah.",
         "EOL cycle = first cycle below the limit (capacity can briefly recover after "
         "long rests). Cut-off voltages differ between batteries."])

    write_battery_blocks(formats, "Data", retention_tables, [
        ("discharge_number",       "Cycle number",                  8,  "0"),
        ("start_time",             "Date and time",                 16, "dd/mm/yyyy hh:mm"),
        ("capacity_Ah",            "Capacity (Ah)",                 10, "0.0000"),
        ("retention_vs_first_pct", "Retention vs initial (%)",      11, "0.00"),
        ("retention_vs_rated_pct", "Retention vs rated 2.0 Ah (%)", 12, "0.00"),
        ("max_temperature_C",      "Max temperature (°C)",          11, "0.0"),
    ])
    save_workbook(workbook, excel_path)


# =============================================================================
# Report 2: resistance (Re, Rct)
# =============================================================================

def write_resistance_report(summary, resistance_tables, figure_paths, excel_path):
    """summary from analysis.make_resistance_summary,
    resistance_tables from analysis.resistance_after_discharge + add_capacity"""
    workbook = xlsxwriter.Workbook(excel_path)
    formats = make_formats(workbook)

    growth = [
        ("battery",          "Battery",                None),
        ("number_of_tests",  "EIS tests used",         "0"),
        ("Re_start_mohm",    "Re start (mΩ)",          "0.0"),
        ("Re_end_mohm",      "Re end (mΩ)",            "0.0"),
        ("Re_increase_pct",  "Re increase (%)",        "0.0"),
        ("Rct_start_mohm",   "Rct start (mΩ)",         "0.0"),
        ("Rct_end_mohm",     "Rct end (mΩ)",           "0.0"),
        ("Rct_increase_pct", "Rct increase (%)",       "0.0"),
    ]
    link = [
        ("battery",             "Battery",                       None),
        ("Re_vs_capacity_r",    "r: Re vs capacity",             "0.00"),
        ("Rct_vs_capacity_r",   "r: Rct vs capacity",            "0.00"),
        ("total_vs_capacity_r", "r: (Re + Rct) vs capacity",     "0.00"),
    ]
    write_summary_sheet(
        formats, "NASA Li-ion battery ageing: resistance (EIS)", figure_paths, 0.6,
        [("Table 1. Resistance growth", summary, growth),
         ("Table 2. Link with capacity (correlation r)", summary, link)],
        ["Only EIS tests done right after a discharge (empty cell) are used. "
         "Start / end = average of the first / last 5 tests.",
         "r close to −1 = resistance rises when capacity falls. "
         "B0018: Rct first falls, then rises, so r is weak."])

    write_battery_blocks(formats, "Data", resistance_tables, [
        ("cycle_number", "Cycle number",                    8,  "0"),
        ("start_time",   "Date and time",                   16, "dd/mm/yyyy hh:mm"),
        ("Re_mohm",      "Re (mΩ)",                         9,  "0.00"),
        ("Rct_mohm",     "Rct (mΩ)",                        9,  "0.00"),
        ("total_mohm",   "Re + Rct (mΩ)",                   10, "0.00"),
        ("capacity_Ah",  "Capacity of previous discharge (Ah)", 13, "0.0000"),
    ])
    save_workbook(workbook, excel_path)


# =============================================================================
# Report 3: dQ/dV
# =============================================================================

def write_dqdv_report(summary, peak_tables, curve_tables, figure_paths, excel_path):
    """summary from dqdv.make_dqdv_summary, peak_tables from dqdv.make_peak_table,
    curve_tables from dqdv.make_curve_table"""
    workbook = xlsxwriter.Workbook(excel_path)
    formats = make_formats(workbook)

    peak = [
        ("battery",                "Battery",                    None),
        ("peak_start_V",           "Peak position start (V)",    "0.000"),
        ("peak_end_V",             "Peak position end (V)",      "0.000"),
        ("peak_shift_mV",          "Peak shift (mV)",            "0"),
        ("peak_height_change_pct", "Peak height change (%)",     "0"),
        ("capacity_change_pct",    "Capacity change (%)",        "0"),
    ]
    test = [
        ("battery",                     "Battery",                               None),
        ("peak_shift_mV",               "Observed peak shift (mV)",              "0"),
        ("eis_predicted_shift_mV",      "Shift predicted by EIS\n(−I·ΔR, mV)",   "0"),
        ("loss_explained_by_shift_pct", "Capacity loss explained\nby the shift (%)", "0.0"),
    ]
    write_summary_sheet(
        formats, "NASA Li-ion battery ageing: dQ/dV (incremental capacity)",
        figure_paths, 0.55,
        [("Table 1. Main dQ/dV peak", summary, peak),
         ("Table 2. Is the capacity loss caused by polarisation (voltage shift)?",
          summary, test)],
        ["Start / end = average of the first / last 5 cycles. dQ/dV calculated in 10 mV windows.",
         "Even if the whole curve moved down by the full observed shift, this would explain "
         "only 0.6–1.4% of the capacity loss: the charge is really missing."])

    write_battery_blocks(formats, "Peak data", peak_tables, [
        ("cycle_number",           "Cycle number",              8,  "0"),
        ("capacity_from_curve_Ah", "Capacity from curve (Ah)",  11, "0.0000"),
        ("peak_voltage_V",         "Peak position (V)",         10, "0.000"),
        ("peak_height_Ah_per_V",   "Peak height (Ah/V)",        10, "0.000"),
    ])

    # The dQ/dV curves of the figure: one voltage column + one column per cycle.
    # The last cycle is different for each battery, so the headers differ per battery.
    curve_columns = {}
    for battery, table in curve_tables.items():
        spec = [("voltage_V", "Voltage (V)", 9, "0.000")]
        for column in table.columns[1:]:
            cycle = column.replace("cycle_", "")
            spec.append((column, f"dQ/dV cycle {cycle} (Ah/V)", 10, "0.000"))
        curve_columns[battery] = spec
    write_battery_blocks(formats, "dQdV curves", curve_tables, curve_columns)

    save_workbook(workbook, excel_path)
