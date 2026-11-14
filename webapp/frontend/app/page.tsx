type RankingRow = {
  destination_id: string;
  destination_name: string;
  country_code: string;
  year?: string;
  comparison_year?: string;
  energy_equal_weight?: string;
  energy_rank?: string;
  enhanced_energy_20pct?: string;
  enhanced_rank_20pct?: string;
  score_status?: string;
  interpretation?: string;
};

type RankingResponse = {
  model: string;
  comparison_year: string | null;
  count: number;
  methodology_note: string;
  results: RankingRow[];
};

const API_URL = process.env.EOM_API_URL ?? "http://127.0.0.1:8000";

async function getRanking(model: string): Promise<RankingResponse | null> {
  try {
    const response = await fetch(`${API_URL}/api/rankings?model=${model}&limit=50`, { cache: "no-store" });
    if (!response.ok) return null;
    return (await response.json()) as RankingResponse;
  } catch {
    return null;
  }
}

export default async function Home({ searchParams }: { searchParams: Promise<{ model?: string }> }) {
  const params = await searchParams;
  const model = params.model === "oecd" ? "oecd" : "baseline";
  const ranking = await getRanking(model);
  const rows = ranking?.results ?? [];
  const year = ranking?.comparison_year ?? "—";

  return (
    <main className="shell">
      <aside className="sidebar">
        <a className="brand" href="/"><span className="brand-mark">E</span><span>EOM<span className="brand-sub">RESEARCH OBSERVATORY</span></span></a>
        <div className="nav-label">WORKSPACE</div>
        <a className="nav-item active" href="/">◫ <span>Overview</span></a>
        <a className="nav-item" href="/?model=baseline">↗ <span>Country rankings</span></a>
        <a className="nav-item" href="/?model=oecd">◎ <span>OECD lens</span></a>
        <div className="sidebar-foot"><span className="status-dot" /> Research preview<br/><small>Local development</small></div>
      </aside>

      <section className="main">
        <header className="topbar"><div><span className="eyebrow">MIGRATION ECONOMICS / GLOBAL VIEW</span><h1>Research overview</h1></div><div className="top-pill">MODEL STATUS <b>EXPLORATORY</b></div></header>
        <section className="intro">
          <div><div className="eyebrow light">ENTROPY-ORIENTED MIGRATION MODEL</div><h2>Understand the forces<br/>shaping migration.</h2><p>A research platform for destination systems, migration flows and macro-level signals.</p></div>
          <div className="intro-orbit"><div className="orbit orbit-one"/><div className="orbit orbit-two"/><div className="orbit-core">EOM</div></div>
        </section>

        <div className="section-head"><div><span className="eyebrow">LATEST MODEL OUTPUTS</span><h2>Destination landscape</h2></div><span className="year-tag">DATA YEAR · {year}</span></div>
        <div className="metrics">
          <article className="metric"><span>DESTINATIONS IN VIEW</span><strong>{ranking?.count ?? "—"}</strong><small>Broad macro comparison</small></article>
          <article className="metric"><span>ACTIVE VIEW</span><strong>{model === "oecd" ? "OECD" : "EOM"}</strong><small>{model === "oecd" ? "Migration ecosystem lens" : "Equal-weight macro proxy"}</small></article>
          <article className="metric"><span>COMPARISON YEAR</span><strong>{year}</strong><small>Latest available artifact</small></article>
        </div>

        <div className="section-head ranking-head"><div><span className="eyebrow">COUNTRY COMPARISON</span><h2>{model === "oecd" ? "OECD-enhanced ranking" : "Baseline EOM ranking"}</h2></div><div className="tabs"><a className={model === "baseline" ? "tab selected" : "tab"} href="/">Baseline</a><a className={model === "oecd" ? "tab selected" : "tab"} href="/?model=oecd">OECD lens</a></div></div>
        <div className="table-wrap">
          {ranking ? <table><thead><tr><th>RANK</th><th>DESTINATION</th><th>COUNTRY CODE</th><th>ENERGY / SCORE</th></tr></thead><tbody>{rows.map((row, index) => <tr key={row.destination_id}><td><span className="rank">{model === "oecd" ? row.enhanced_rank_20pct : row.energy_rank ?? index + 1}</span></td><td className="country">{row.destination_name}</td><td className="code">{row.country_code}</td><td className="score">{Number(model === "oecd" ? row.enhanced_energy_20pct : row.energy_equal_weight).toFixed(3)}</td></tr>)}</tbody></table> : <div className="empty"><strong>API not connected yet</strong><p>Start the FastAPI service on port 8000. The dashboard will load the committed research outputs automatically.</p><code>py -m uvicorn webapp.backend.app.main:app --reload --port 8000</code></div>}
        </div>
        <p className="method-note"><b>Interpretation note</b> {ranking?.methodology_note ?? "Scores are research proxies, not personal migration probabilities. The model is not calibrated or validated for individual decisions."}</p>
        <footer>ENTROPY-ORIENTED MIGRATION MODEL <span>LOCAL BUILD · V0.1.0</span></footer>
      </section>
    </main>
  );
}
