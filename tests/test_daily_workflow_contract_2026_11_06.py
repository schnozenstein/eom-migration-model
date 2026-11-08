from pathlib import Path


def test_daily_refresh_schedule_and_ranking_recompute_are_wired():
    workflow = Path(".github/workflows/eom-daily-refresh.yml").read_text(encoding="utf-8")

    assert 'schedule:' in workflow
    assert '- cron: "17 17 * * *"' in workflow
    assert 'group: eom-daily-refresh-${{ github.ref }}' in workflow
    assert 'id: recompute_ranking' in workflow
    assert 'python -m eom_empirical.fit_macro_model' in workflow
    assert 'id: ranking_delta' in workflow
