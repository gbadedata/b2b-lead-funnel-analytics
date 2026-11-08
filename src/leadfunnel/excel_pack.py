"""Excel reporting pack: a live dashboard driven by formulas, not pasted numbers.

The Dashboard and Lead_Scoring sheets recalculate from the Leads and scored-lead
tables, so a manager can change the source or month dropdowns (or paste in next
month's leads) without touching Python. Model outputs that need Python
(intervals, adjusted odds ratios, shrinkage) sit on their own sheets, labelled.
"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

import pandas as pd
from openpyxl import Workbook
from openpyxl.chart import BarChart, LineChart, Reference
from openpyxl.formatting.rule import CellIsRule, ColorScaleRule, DataBarRule
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter
from openpyxl.worksheet.datavalidation import DataValidation

FONT = "Arial"
NAVY = "1F3864"
HEAD = Font(name=FONT, bold=True, color="FFFFFF")
HEAD_FILL = PatternFill("solid", fgColor=NAVY)
TITLE = Font(name=FONT, bold=True, size=14, color=NAVY)
BODY = Font(name=FONT, size=10)
NOTE = Font(name=FONT, size=9, italic=True, color="52514E")
INPUT_FONT = Font(name=FONT, size=10, bold=True, color="0000FF")
INPUT_FILL = PatternFill("solid", fgColor="FFFF00")
KPI_FONT = Font(name=FONT, size=16, bold=True, color=NAVY)
THIN = Border(bottom=Side(style="thin", color="D9D9D9"))
PCT = "0.0%"
INT = "#,##0"


def _header(ws, row: int, labels: list[str], col: int = 1) -> None:
    for j, lab in enumerate(labels):
        c = ws.cell(row=row, column=col + j, value=lab)
        c.font, c.fill = HEAD, HEAD_FILL
        c.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)


def _widths(ws, widths: dict[str, float]) -> None:
    for col, w in widths.items():
        ws.column_dimensions[col].width = w


def _arial(ws) -> None:
    """Apply Arial everywhere while keeping each cell's weight, size and colour."""
    for row in ws.iter_rows():
        for c in row:
            f = c.font
            if f.name != FONT:
                c.font = Font(name=FONT, bold=f.b, italic=f.i, size=f.sz, color=f.color)


def _write_table(ws, df: pd.DataFrame, start_row: int, start_col: int = 1, formats: dict | None = None) -> int:
    _header(ws, start_row, list(df.columns), start_col)
    formats = formats or {}
    for i, rec in enumerate(df.itertuples(index=False), start=start_row + 1):
        for j, v in enumerate(rec):
            c = ws.cell(row=i, column=start_col + j, value=None if pd.isna(v) else v)
            c.font = BODY
            fmt = formats.get(df.columns[j])
            if fmt:
                c.number_format = fmt
    return start_row + len(df)


def build(
    cohort: pd.DataFrame,
    rate_tbl: pd.DataFrame,
    odds: pd.DataFrame,
    pages: pd.DataFrame,
    issues: pd.DataFrame,
    scored: pd.DataFrame,
    path: Path,
    generated: str | None = None,
) -> Path:
    wb = Workbook()
    generated = generated or datetime.now().strftime("%d %b %Y")

    # ---------------- Leads (data) ----------------
    leads = pd.DataFrame({
        "Lead ID": cohort["mql_id"].str[:8],
        "First contact": cohort["first_contact_date"],
        "Month": cohort["month"],
        "Source": cohort["origin"],
        "Landing page": cohort["landing_page_id"].str[:8],
        "Won in 90 days": cohort["won_90d"].astype(int),
        "Days to close": cohort["days_to_close"].where(cohort["won_90d"]),
        "Lead type": cohort["lead_type"],
        "Segment": cohort["business_segment"],
    }).sort_values(["First contact", "Lead ID"])
    n = len(leads)
    last = n + 1
    ws_l = wb.active
    ws_l.title = "Leads"
    _write_table(ws_l, leads, 1, formats={"First contact": "dd mmm yyyy", "Days to close": "0"})
    ws_l.freeze_panes = "A2"
    ws_l.auto_filter.ref = f"A1:I{last}"
    _widths(ws_l, {"A": 11, "B": 13, "C": 9, "D": 17, "E": 13, "F": 10, "G": 10, "H": 15, "I": 24})

    rng = {k: f"Leads!${c}$2:${c}${last}" for k, c in
           {"id": "A", "month": "C", "source": "D", "won": "F", "days": "G"}.items()}

    # ---------------- Lists (dropdown sources) ----------------
    ws_x = wb.create_sheet("Lists")
    sources = list(rate_tbl.index)
    months = sorted(leads["Month"].unique())
    ws_x["A1"], ws_x["B1"] = "Source", "Month"
    for i, v in enumerate(["All"] + sources, start=2):
        ws_x.cell(row=i, column=1, value=v)
    for i, v in enumerate(["All"] + months, start=2):
        ws_x.cell(row=i, column=2, value=v)
    _header(ws_x, 1, ["Source", "Month"])
    ws_x.sheet_state = "hidden"

    # ---------------- Dashboard ----------------
    ws = wb.create_sheet("Dashboard", 0)
    ws["A1"] = "Lead funnel dashboard"
    ws["A1"].font = TITLE
    ws["A2"] = (f"Leads first contacted Jan to May 2018 (n={n:,}). A lead is won if the deal closes "
                "within 90 days. Change the yellow cells to filter.")
    ws["A2"].font = NOTE
    ws["A4"], ws["A5"] = "Source", "Month"
    for ref, opts in (("B4", f"=Lists!$A$2:$A${len(sources) + 2}"), ("B5", f"=Lists!$B$2:$B${len(months) + 2}")):
        ws[ref] = "All"
        ws[ref].font, ws[ref].fill = INPUT_FONT, INPUT_FILL
        dv = DataValidation(type="list", formula1=opts, allow_blank=False)
        ws.add_data_validation(dv)
        dv.add(ws[ref])
    ws["C4"] = "choose a source, or All"
    ws["C5"] = "choose a month, or All"
    ws["C4"].font = ws["C5"].font = NOTE
    # Criteria helpers: "*" matches every value when All is chosen.
    ws["J3"] = "criteria"
    ws["J4"] = '=IF($B$4="All","*",$B$4)'
    ws["J5"] = '=IF($B$5="All","*",$B$5)'
    ws.column_dimensions["J"].hidden = True

    kpis = ["Leads", "Won in 90 days", "Conversion", "Avg days to close (won)", "Share of all leads"]
    _header(ws, 7, kpis)
    crit = f"{rng['source']},$J$4,{rng['month']},$J$5"
    ws["A8"] = f"=COUNTIFS({crit})"
    ws["B8"] = f"=SUMIFS({rng['won']},{crit})"
    ws["C8"] = "=IFERROR(B8/A8,0)"
    ws["D8"] = f'=IFERROR(AVERAGEIFS({rng["days"]},{crit},{rng["won"]},1),"-")'
    ws["E8"] = f"=IFERROR(A8/COUNTA({rng['id']}),0)"
    for ref, fmt in (("A8", INT), ("B8", INT), ("C8", PCT), ("D8", "0.0"), ("E8", PCT)):
        ws[ref].font, ws[ref].number_format = KPI_FONT, fmt
        ws[ref].alignment = Alignment(horizontal="center")

    top = 11
    _header(ws, top - 1, ["Source", "Leads", "Won", "Conversion", "Share of leads", "Share of wins",
                          "Index vs average"])
    first, lastrow = top, top + len(sources) - 1
    for i, src in enumerate(sources):
        r = top + i
        ws.cell(row=r, column=1, value=src)
        ws.cell(row=r, column=2, value=f"=COUNTIFS({rng['source']},$A{r},{rng['month']},$J$5)")
        ws.cell(row=r, column=3, value=f"=SUMIFS({rng['won']},{rng['source']},$A{r},{rng['month']},$J$5)")
        ws.cell(row=r, column=4, value=f"=IFERROR(C{r}/B{r},0)")
        ws.cell(row=r, column=5, value=f"=IFERROR(B{r}/SUM($B${first}:$B${lastrow}),0)")
        ws.cell(row=r, column=6, value=f"=IFERROR(C{r}/SUM($C${first}:$C${lastrow}),0)")
        ws.cell(row=r, column=7, value=f"=IFERROR(D{r}/(SUM($C${first}:$C${lastrow})/SUM($B${first}:$B${lastrow})),0)")
        for col, fmt in ((2, INT), (3, INT), (4, PCT), (5, PCT), (6, PCT), (7, "0.00")):
            ws.cell(row=r, column=col).number_format = fmt
            ws.cell(row=r, column=col).border = THIN
    tot = lastrow + 1
    ws.cell(row=tot, column=1, value="Total").font = Font(name=FONT, bold=True)
    ws.cell(row=tot, column=2, value=f"=SUM(B{first}:B{lastrow})").number_format = INT
    ws.cell(row=tot, column=3, value=f"=SUM(C{first}:C{lastrow})").number_format = INT
    ws.cell(row=tot, column=4, value=f"=IFERROR(C{tot}/B{tot},0)").number_format = PCT
    for col in (2, 3, 4):
        ws.cell(row=tot, column=col).font = Font(name=FONT, bold=True)
    ws.conditional_formatting.add(f"D{first}:D{lastrow}", ColorScaleRule(
        start_type="min", start_color="FFFFFF", end_type="max", end_color="6DA7EC"))
    ws.conditional_formatting.add(f"B{first}:B{lastrow}", DataBarRule(
        start_type="min", end_type="max", color="9EC5F4"))
    ws.cell(row=tot + 1, column=1, value="Index vs average: 1.00 = the average conversion for the "
            "selected month; 2.00 = twice as likely to convert.").font = NOTE

    mtop = tot + 4
    ws.cell(row=mtop - 1, column=1, value="By month (for the selected source)").font = Font(name=FONT, bold=True)
    _header(ws, mtop, ["Month", "Leads", "Won", "Conversion"])
    for i, mth in enumerate(months):
        r = mtop + 1 + i
        ws.cell(row=r, column=1, value=mth)
        ws.cell(row=r, column=2, value=f"=COUNTIFS({rng['month']},$A{r},{rng['source']},$J$4)").number_format = INT
        sumifs = f"=SUMIFS({rng['won']},{rng['month']},$A{r},{rng['source']},$J$4)"
        ws.cell(row=r, column=3, value=sumifs).number_format = INT
        ws.cell(row=r, column=4, value=f"=IFERROR(C{r}/B{r},0)").number_format = PCT
    mlast = mtop + len(months)

    bar = BarChart()
    bar.type = "bar"
    bar.title = "Conversion by source"
    bar.y_axis.numFmt = "0%"
    bar.add_data(Reference(ws, min_col=4, min_row=top - 1, max_row=lastrow), titles_from_data=True)
    bar.set_categories(Reference(ws, min_col=1, min_row=first, max_row=lastrow))
    bar.legend = None
    bar.height, bar.width = 8, 14
    ws.add_chart(bar, "I7")
    line = LineChart()
    line.title = "Leads by month"
    line.add_data(Reference(ws, min_col=2, min_row=mtop, max_row=mlast), titles_from_data=True)
    line.set_categories(Reference(ws, min_col=1, min_row=mtop + 1, max_row=mlast))
    line.legend = None
    for ser in line.series:
        ser.smooth = False
    line.height, line.width = 7, 14
    ws.add_chart(line, f"I{mtop - 2}")
    _widths(ws, {"A": 22, "B": 14, "C": 14, "D": 16, "E": 14, "F": 13, "G": 14})
    ws.freeze_panes = "A7"

    # ---------------- Lead scoring ----------------
    ws_s = wb.create_sheet("Lead_Scoring", 1)
    sc = scored.sort_values("score", ascending=False)
    sdata = pd.DataFrame({
        "Lead ID": sc["mql_id"].str[:8],
        "First contact": sc["first_contact_date"],
        "Source": sc["origin"],
        "Landing page": sc["landing_page_id"].str[:8],
        "Score": sc["score"],
        "Decile": sc["decile"].astype(int),
        "Won in 90 days": sc["won_90d"].astype(int),
    })
    ws_s["A1"] = "Lead score: who to call first"
    ws_s["A1"].font = TITLE
    ws_s["A2"] = ("Scores come from a logistic model trained on Jan-Mar 2018 leads and applied to "
                  "Apr-May 2018 leads it never saw. Decile 1 = highest scores.")
    ws_s["A2"].font = NOTE
    srow0, slast = 4, len(sdata) + 4
    _write_table(ws_s, sdata, srow0, start_col=9, formats={"First contact": "dd mmm yyyy", "Score": "0.000"})
    dec = f"$N${srow0 + 1}:$N${slast}"
    won = f"$O${srow0 + 1}:$O${slast}"
    _header(ws_s, 4, ["Decile", "Leads", "Won", "Conversion", "Cumulative share of leads",
                      "Cumulative share of wins", "Lift"])
    for d in range(1, 11):
        r = 4 + d
        ws_s.cell(row=r, column=1, value=d)
        ws_s.cell(row=r, column=2, value=f"=COUNTIFS({dec},A{r})").number_format = INT
        ws_s.cell(row=r, column=3, value=f"=SUMIFS({won},{dec},A{r})").number_format = INT
        ws_s.cell(row=r, column=4, value=f"=IFERROR(C{r}/B{r},0)").number_format = PCT
        ws_s.cell(row=r, column=5, value=f"=SUM($B$5:B{r})/SUM($B$5:$B$14)").number_format = PCT
        ws_s.cell(row=r, column=6, value=f"=SUM($C$5:C{r})/SUM($C$5:$C$14)").number_format = PCT
        ws_s.cell(row=r, column=7, value=f"=IFERROR(D{r}/(SUM($C$5:$C$14)/SUM($B$5:$B$14)),0)").number_format = "0.00"
    ws_s.conditional_formatting.add("D5:D14", ColorScaleRule(
        start_type="min", start_color="FFFFFF", end_type="max", end_color="6DA7EC"))
    ws_s["A17"] = "Deciles the team can call first"
    ws_s["E17"] = 3
    ws_s["E17"].font, ws_s["E17"].fill = INPUT_FONT, INPUT_FILL
    dv = DataValidation(type="whole", operator="between", formula1="1", formula2="10")
    ws_s.add_data_validation(dv)
    dv.add(ws_s["E17"])
    ws_s["A18"] = "Share of leads called"
    ws_s["E18"] = f"=COUNTIFS({dec},\"<=\"&E17)/COUNT({dec})"
    ws_s["A19"] = "Share of 90-day wins reached"
    ws_s["E19"] = f"=SUMIFS({won},{dec},\"<=\"&E17)/SUM({won})"
    for ref in ("E18", "E19"):
        ws_s[ref].number_format = PCT
        ws_s[ref].font = Font(name=FONT, bold=True, color=NAVY)
    ws_s["A20"] = "Change the yellow cell (1-10) to see the trade-off."
    ws_s["A20"].font = NOTE
    _widths(ws_s, {"A": 10, "B": 10, "C": 10, "D": 12, "E": 14, "F": 14, "G": 8, "H": 3,
                   "I": 11, "J": 13, "K": 19, "L": 13, "M": 8, "N": 8, "O": 10})
    ws_s.freeze_panes = "A5"

    # ---------------- Channel stats (Python outputs) ----------------
    ws_c = wb.create_sheet("Channel_Stats", 2)
    ws_c["A1"] = "Source statistics (computed in Python, not live)"
    ws_c["A1"].font = TITLE
    ws_c["A2"] = ("Wilson 95% intervals; odds ratios from a logistic model with month fixed effects, "
                  "against organic search, Holm-adjusted for 10 comparisons.")
    ws_c["A2"].font = NOTE
    t = rate_tbl.reset_index().merge(odds, on="origin", how="left")
    t = pd.DataFrame({
        "Source": t["origin"], "Leads": t["leads"], "Won": t["wins"], "Conversion": t["rate"],
        "95% low": t["ci_low"], "95% high": t["ci_high"], "Odds ratio vs organic": t["odds_ratio"],
        "OR low": t["or_low"], "OR high": t["or_high"], "Holm p": t["p_holm"],
        "Ranked (100+ leads)": t["rankable"].map({True: "yes", False: "no"}),
    })
    _write_table(ws_c, t, 4, formats={"Conversion": PCT, "95% low": PCT, "95% high": PCT,
                                      "Odds ratio vs organic": "0.00", "OR low": "0.00", "OR high": "0.00",
                                      "Holm p": "0.000", "Leads": INT, "Won": INT})
    _widths(ws_c, {get_column_letter(i): 13 for i in range(1, 12)} | {"A": 18})

    # ---------------- Landing pages ----------------
    ws_p = wb.create_sheet("Landing_Pages", 3)
    ws_p["A1"] = "Landing pages with 20+ leads, ranked on shrunk conversion"
    ws_p["A1"].font = TITLE
    ws_p["A2"] = ("Shrunk rate = raw rate pulled toward the pooled page rate in proportion to how little "
                  "traffic the page has (beta-binomial). 90% credible interval shown.")
    ws_p["A2"].font = NOTE
    pp = pages[pages["leads"] >= 20].reset_index()
    pp = pd.DataFrame({"Page": pp["page"], "Leads": pp["leads"], "Won": pp["wins"], "Raw rate": pp["raw_rate"],
                       "Shrunk rate": pp["shrunk_rate"], "90% low": pp["cred_low"], "90% high": pp["cred_high"]})
    _write_table(ws_p, pp, 4, formats={"Raw rate": PCT, "Shrunk rate": PCT, "90% low": PCT, "90% high": PCT})
    _widths(ws_p, {"A": 12, "B": 9, "C": 9, "D": 11, "E": 12, "F": 10, "G": 10})

    # ---------------- Data quality ----------------
    ws_q = wb.create_sheet("Data_Quality", 4)
    ws_q["A1"] = "Data quality log"
    ws_q["A1"].font = TITLE
    q = pd.DataFrame({"Code": issues["code"], "Severity": issues["severity"], "Check": issues["check"],
                      "Records affected": issues["affected"], "Share": issues["share"],
                      "Finding": issues["finding"], "Why it matters": issues["impact"],
                      "Recommendation": issues["recommendation"]})
    qlast = _write_table(ws_q, q, 3, formats={"Share": PCT, "Records affected": INT})
    for row in ws_q.iter_rows(min_row=4, max_row=qlast):
        for c in row:
            c.alignment = Alignment(wrap_text=True, vertical="top")
    for sev, color in (("high", "F8D7D7"), ("medium", "FCE8C8"), ("low", "EAF1FB"), ("pass", "E2F0E2")):
        ws_q.conditional_formatting.add(f"B4:B{qlast}", CellIsRule(operator="equal", formula=[f'"{sev}"'],
                                                                   fill=PatternFill("solid", fgColor=color)))
    _widths(ws_q, {"A": 7, "B": 9, "C": 30, "D": 10, "E": 8, "F": 55, "G": 45, "H": 45})
    ws_q.freeze_panes = "A4"

    # ---------------- About ----------------
    ws_a = wb.create_sheet("About", 0)
    lines = [
        ("Lead funnel reporting pack", TITLE),
        (f"Generated {generated} by b2b-lead-funnel-analytics.", NOTE),
        ("", BODY),
        ("What is in this workbook", Font(name=FONT, bold=True)),
        ("Dashboard - live leads, wins and conversion by source and month (formulas over the Leads sheet).", BODY),
        ("Lead_Scoring - score deciles for Apr-May 2018 leads, and the share of wins reached by calling "
         "the top deciles first.", BODY),
        ("Channel_Stats - intervals and adjusted odds ratios from the Python analysis (static values).", BODY),
        ("Landing_Pages - page conversion with shrinkage so small pages are not over-ranked (static values).", BODY),
        ("Data_Quality - issues found in the source data, with impact and a recommended fix.", BODY),
        ("Leads - one row per lead in the analysis cohort; the Dashboard reads from here.", BODY),
        ("", BODY),
        ("Definitions", Font(name=FONT, bold=True)),
        ("Lead: a marketing qualified lead (an enquiry that asked to be contacted).", BODY),
        ("Won in 90 days: the deal closed within 90 days of first contact. Every lead in the cohort has at "
         "least 167 days of deal data, so this is fully observed.", BODY),
        ("Cohort: leads first contacted 1 Jan to 31 May 2018. Earlier leads are excluded because deal records "
         "start in December 2017 (see Data_Quality, DQ01).", BODY),
        ("Yellow cells are inputs. Everything else on Dashboard and Lead_Scoring is a formula.", BODY),
        ("", BODY),
        ("Source data", Font(name=FONT, bold=True)),
        ("Olist Marketing Funnel and Brazilian E-Commerce public datasets (Kaggle), licence CC BY-NC-SA 4.0. "
         "IDs are shortened to 8 characters here.", BODY),
    ]
    for i, (txt, f) in enumerate(lines, start=1):
        ws_a.cell(row=i, column=1, value=txt).font = f
    ws_a.column_dimensions["A"].width = 120

    for w in wb.worksheets:
        w.sheet_view.showGridLines = w.title in {"Leads"}
        _arial(w)
    wb.active = wb.sheetnames.index("Dashboard")
    wb.save(path)
    return path
