from scripts.oecd_imo_2026_annex import parse_annex_html, parse_numeric

def test_missing_markers_are_not_zero():
    assert parse_numeric("..") == (None, "missing", "..")
    assert parse_numeric(".") == (None, "missing", ".")
    assert parse_numeric("1 234.5") == (1234.5, "observed", "")

def test_extracts_required_tables_and_keeps_dimensions_separate():
    html = """
    <html><body>
      <h3>Table A.1. Inflows of foreign population into selected OECD countries</h3>
      <table><thead><tr><th>Country</th><th>2023</th><th>2024</th></tr></thead><tbody><tr><td>Germany</td><td>100.0</td><td>110.0</td></tr></tbody></table>
      <h3>Table A.4. Stocks of foreign-born population in OECD countries</h3>
      <table><thead><tr><th>Country</th><th>2023</th><th>2024</th></tr></thead><tbody><tr><td>Germany</td><td>15000</td><td>15500</td></tr><tr><td>% of total population</td><td>18.0</td><td>18.5</td></tr></tbody></table>
      <h3>Table B.4. Stocks of foreign-born population by country of birth – Germany</h3>
      <table><thead><tr><th>Country of birth</th><th>2023</th><th>2024</th></tr></thead><tbody><tr><td>India</td><td>100</td><td>120</td></tr></tbody></table>
      <h3>Table A.6. Acquisitions of nationality in OECD countries</h3>
      <table><thead><tr><th>Country</th><th>2023</th><th>2024</th></tr></thead><tbody><tr><td>Germany</td><td>200000</td><td>220000</td></tr><tr><td>% of foreign population</td><td>1.2</td><td>1.3</td></tr></tbody></table>
    </body></html>
    """
    frame, audit = parse_annex_html(html, "2026-11-14T00:00:00+00:00", "test", "abc")
    assert {"A.1", "A.4", "B.4", "A.6"}.issubset(set(frame.table_code))
    assert ((frame.table_code == "B.4") & (frame.destination == "Germany") & (frame.origin == "India")).any()
    assert ((frame.table_code == "A.4") & (frame.measure == "foreign_born_population_share")).any()
    assert ((frame.table_code == "A.6") & (frame.measure == "naturalisation_rate_foreign_population")).any()
    assert audit["duplicate_natural_keys_rejected"] == 0
