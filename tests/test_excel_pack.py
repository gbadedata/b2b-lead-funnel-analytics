"""The workbook's formulas must give the same numbers as pandas."""

from pathlib import Path

import pytest
from openpyxl import load_workbook

from leadfunnel import excel_pack, funnel, quality, recalc, scoring
from leadfunnel.load import RawData


def _build(raw: RawData, path: Path):
    leads = funnel.build_leads(raw.mql, raw.deals)
    c = funnel.cohort(leads)
    rt = funnel.rate_table(c, "origin")
    od = funnel.adjusted_odds_ratios(c)
    pages, _ = funnel.landing_page_table(c)
    issues = quality.run_checks(raw, leads)
    sc = scoring.run(c)
    excel_pack.build(c, rt, od, pages, issues, sc["scored_test"], path, generated="test")
    return c, rt, sc


def test_workbook_structure(raw, tmp_path):
    path = tmp_path / "pack.xlsx"
    _build(raw, path)
    wb = load_workbook(path)
    assert wb.sheetnames[:2] == ["About", "Dashboard"]
    ws = wb["Dashboard"]
    assert ws["A8"].value.startswith("=COUNTIFS(")
    assert ws["B4"].value == "All"
    assert ws.data_validations.dataValidation, "source dropdown missing"
    for sheet in wb.worksheets:
        for row in sheet.iter_rows():
            for c in row:
                if isinstance(c.value, str) and c.value.startswith("="):
                    assert "XLOOKUP" not in c.value and "FILTER(" not in c.value


@pytest.mark.skipif(not recalc.available(), reason="needs LibreOffice")
def test_formulas_match_pandas(raw, tmp_path):
    path = tmp_path / "pack.xlsx"
    c, rt, sc = _build(raw, path)
    res = recalc.recalc(path)
    assert res["status"] == "success", res["errors"][:5]
    wb = load_workbook(path, data_only=True)
    ws = wb["Dashboard"]
    assert ws["A8"].value == len(c)
    assert ws["B8"].value == int(c["won_90d"].sum())
    assert ws["C8"].value == pytest.approx(c["won_90d"].mean())
    for r in range(11, 11 + len(rt)):
        src = ws.cell(row=r, column=1).value
        assert ws.cell(row=r, column=2).value == rt.loc[src, "leads"]
        assert ws.cell(row=r, column=3).value == rt.loc[src, "wins"]
    s = wb["Lead_Scoring"]
    assert s["E19"].value == pytest.approx(sc["metrics"]["logistic"]["top_30pct"], abs=0.01)
