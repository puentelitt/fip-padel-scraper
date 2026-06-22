#!/usr/bin/env python3
"""Build a self-contained dashboard (index.html) from the enriched CSV.

Reads fip_men_ranking_enriched.csv, embeds the rows as JSON inside a single
static HTML file with vanilla-JS filtering. No server or build step needed —
just open index.html in a browser.

Filters: name search, nationality (multi), playing side, age range,
height (taller/shorter than). Each row links to the player's FIP profile.
"""

import csv
import json

INPUT = "fip_men_ranking_enriched.csv"
OUTPUT = "index.html"


def load_rows():
    with open(INPUT, encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    out = []
    for r in rows:
        out.append(
            {
                "position": int(r["position"]) if r["position"] else None,
                "player": r["player"],
                "country": r["country"],
                "points": int(r["points"]) if r["points"] else None,
                "birthdate": r["birthdate"],
                "age": int(r["age"]) if r["age"] else None,
                "place_of_birth": r["place_of_birth"],
                "height_m": float(r["height_m"]) if r["height_m"] else None,
                "playing_side": r["playing_side"],
                "profile_url": r["profile_url"],
            }
        )
    return out


HTML = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>FIP Men's Padel Ranking — Top 300</title>
<style>
  :root {
    --bg: #0f1419; --panel: #1a2129; --panel2: #232c37; --line: #2e3a47;
    --text: #e6edf3; --muted: #8b98a5; --accent: #4ade80; --accent2: #38bdf8;
    --chip: #2b3642;
  }
  * { box-sizing: border-box; }
  body {
    margin: 0; font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
    background: var(--bg); color: var(--text); font-size: 14px;
  }
  header { padding: 20px 24px 12px; border-bottom: 1px solid var(--line); }
  h1 { margin: 0 0 4px; font-size: 20px; }
  .sub { color: var(--muted); font-size: 13px; }
  .layout { display: flex; align-items: flex-start; gap: 0; }
  aside {
    width: 280px; flex: 0 0 280px; padding: 18px 20px; border-right: 1px solid var(--line);
    position: sticky; top: 0; height: 100vh; overflow-y: auto;
  }
  main { flex: 1; padding: 14px 20px 60px; overflow-x: auto; }
  .group { margin-bottom: 20px; }
  .group h3 { margin: 0 0 8px; font-size: 12px; text-transform: uppercase; letter-spacing: .06em; color: var(--muted); }
  input[type=text], input[type=number], select {
    width: 100%; padding: 8px 10px; background: var(--panel); color: var(--text);
    border: 1px solid var(--line); border-radius: 8px; font-size: 13px;
  }
  input:focus, select:focus { outline: none; border-color: var(--accent2); }
  .row2 { display: flex; gap: 8px; }
  .row2 > * { flex: 1; }
  .seg { display: flex; gap: 6px; flex-wrap: wrap; }
  .seg button {
    flex: 1; padding: 7px 4px; background: var(--panel); color: var(--text);
    border: 1px solid var(--line); border-radius: 8px; cursor: pointer; font-size: 13px;
  }
  .seg button.active { background: var(--accent); color: #06210f; border-color: var(--accent); font-weight: 600; }
  .nats { max-height: 230px; overflow-y: auto; border: 1px solid var(--line); border-radius: 8px; padding: 6px; background: var(--panel); }
  .nat { display: flex; align-items: center; gap: 8px; padding: 4px 6px; border-radius: 6px; cursor: pointer; }
  .nat:hover { background: var(--panel2); }
  .nat input { accent-color: var(--accent); }
  .nat .cnt { margin-left: auto; color: var(--muted); font-size: 12px; }
  .reset {
    width: 100%; padding: 9px; background: var(--panel2); color: var(--text);
    border: 1px solid var(--line); border-radius: 8px; cursor: pointer; font-size: 13px;
  }
  .reset:hover { border-color: var(--accent2); }
  .count { margin: 4px 0 12px; color: var(--muted); }
  .count b { color: var(--text); }
  table { width: 100%; border-collapse: collapse; }
  th, td { text-align: left; padding: 9px 12px; border-bottom: 1px solid var(--line); white-space: nowrap; }
  th { font-size: 12px; text-transform: uppercase; letter-spacing: .04em; color: var(--muted); cursor: pointer; user-select: none; position: sticky; top: 0; background: var(--bg); }
  th:hover { color: var(--text); }
  th .arrow { color: var(--accent2); }
  tbody tr:hover { background: var(--panel); }
  td.num { text-align: right; font-variant-numeric: tabular-nums; }
  .pos { font-weight: 700; }
  .pname a { color: var(--text); text-decoration: none; font-weight: 600; }
  .pname a:hover { color: var(--accent2); text-decoration: underline; }
  .flag { display: inline-block; padding: 2px 7px; background: var(--chip); border-radius: 20px; font-size: 12px; }
  .side { font-size: 12px; padding: 2px 8px; border-radius: 20px; }
  .side.Right { background: #1e3a5f; color: #93c5fd; }
  .side.Left { background: #3f2d52; color: #d8b4fe; }
  .muted { color: var(--muted); }
  .fip { color: var(--accent2); text-decoration: none; font-size: 12px; }
  .fip:hover { text-decoration: underline; }
  @media (max-width: 820px) {
    .layout { flex-direction: column; }
    aside { width: 100%; flex: none; height: auto; position: static; border-right: none; border-bottom: 1px solid var(--line); }
  }
</style>
</head>
<body>
<header>
  <h1>FIP Men's Padel Ranking — Top 300</h1>
  <div class="sub">Snapshot scraped from padelfip.com · ranking date __DATE__</div>
</header>
<div class="layout">
  <aside>
    <div class="group">
      <h3>Search</h3>
      <input type="text" id="q" placeholder="Player name…">
    </div>
    <div class="group">
      <h3>Age</h3>
      <div class="row2">
        <input type="number" id="ageMin" placeholder="min" min="0">
        <input type="number" id="ageMax" placeholder="max" min="0">
      </div>
    </div>
    <div class="group">
      <h3>Height (m)</h3>
      <div class="row2">
        <input type="number" id="hMin" placeholder="taller ≥" step="0.01">
        <input type="number" id="hMax" placeholder="shorter ≤" step="0.01">
      </div>
    </div>
    <div class="group">
      <h3>Playing side</h3>
      <div class="seg" id="sideSeg">
        <button data-side="" class="active">All</button>
        <button data-side="Right">Right</button>
        <button data-side="Left">Left</button>
      </div>
    </div>
    <div class="group">
      <h3>Nationality</h3>
      <div class="nats" id="nats"></div>
    </div>
    <button class="reset" id="reset">Reset all filters</button>
  </aside>
  <main>
    <div class="count" id="count"></div>
    <table>
      <thead>
        <tr>
          <th data-k="position">#<span class="arrow"></span></th>
          <th data-k="player">Player<span class="arrow"></span></th>
          <th data-k="country">Nat.<span class="arrow"></span></th>
          <th data-k="points" class="num">Points<span class="arrow"></span></th>
          <th data-k="age" class="num">Age<span class="arrow"></span></th>
          <th data-k="birthdate">Born<span class="arrow"></span></th>
          <th data-k="height_m" class="num">Height<span class="arrow"></span></th>
          <th data-k="playing_side">Side<span class="arrow"></span></th>
          <th data-k="place_of_birth">Birthplace<span class="arrow"></span></th>
          <th>FIP</th>
        </tr>
      </thead>
      <tbody id="tbody"></tbody>
    </table>
  </main>
</div>
<script>
const DATA = __DATA__;
const state = { q:"", ageMin:null, ageMax:null, hMin:null, hMax:null, side:"", nats:new Set(), sortK:"position", sortDir:1 };

// Build nationality checkboxes with counts.
const natCounts = {};
DATA.forEach(d => { if(d.country) natCounts[d.country]=(natCounts[d.country]||0)+1; });
const natList = Object.keys(natCounts).sort((a,b)=> natCounts[b]-natCounts[a] || a.localeCompare(b));
const natsEl = document.getElementById("nats");
natList.forEach(c => {
  const lab = document.createElement("label"); lab.className="nat";
  lab.innerHTML = `<input type="checkbox" value="${c}"><span>${c}</span><span class="cnt">${natCounts[c]}</span>`;
  lab.querySelector("input").addEventListener("change", e => {
    if(e.target.checked) state.nats.add(c); else state.nats.delete(c);
    render();
  });
  natsEl.appendChild(lab);
});

function num(v){ return v===""||v===null||v===undefined||isNaN(v)?null:Number(v); }
document.getElementById("q").addEventListener("input", e=>{ state.q=e.target.value.toLowerCase().trim(); render(); });
document.getElementById("ageMin").addEventListener("input", e=>{ state.ageMin=num(e.target.value); render(); });
document.getElementById("ageMax").addEventListener("input", e=>{ state.ageMax=num(e.target.value); render(); });
document.getElementById("hMin").addEventListener("input", e=>{ state.hMin=num(e.target.value); render(); });
document.getElementById("hMax").addEventListener("input", e=>{ state.hMax=num(e.target.value); render(); });
document.getElementById("sideSeg").addEventListener("click", e=>{
  if(e.target.tagName!=="BUTTON") return;
  state.side=e.target.dataset.side;
  [...e.currentTarget.children].forEach(b=>b.classList.toggle("active", b===e.target));
  render();
});
document.querySelectorAll("th[data-k]").forEach(th=>{
  th.addEventListener("click", ()=>{
    const k=th.dataset.k;
    if(state.sortK===k) state.sortDir*=-1; else { state.sortK=k; state.sortDir=1; }
    render();
  });
});
document.getElementById("reset").addEventListener("click", ()=>{
  state.q=""; state.ageMin=state.ageMax=state.hMin=state.hMax=null; state.side=""; state.nats.clear();
  document.getElementById("q").value="";
  ["ageMin","ageMax","hMin","hMax"].forEach(id=>document.getElementById(id).value="");
  document.querySelectorAll("#nats input").forEach(i=>i.checked=false);
  [...document.getElementById("sideSeg").children].forEach(b=>b.classList.toggle("active", b.dataset.side===""));
  render();
});

function passes(d){
  if(state.q && !d.player.toLowerCase().includes(state.q)) return false;
  if(state.nats.size && !state.nats.has(d.country)) return false;
  if(state.side && d.playing_side!==state.side) return false;
  if(state.ageMin!==null && (d.age===null || d.age<state.ageMin)) return false;
  if(state.ageMax!==null && (d.age===null || d.age>state.ageMax)) return false;
  if(state.hMin!==null && (d.height_m===null || d.height_m<state.hMin)) return false;
  if(state.hMax!==null && (d.height_m===null || d.height_m>state.hMax)) return false;
  return true;
}

function render(){
  let rows = DATA.filter(passes);
  const k=state.sortK, dir=state.sortDir;
  rows.sort((a,b)=>{
    let x=a[k], y=b[k];
    if(x===null||x===undefined||x==="") return 1;   // blanks last
    if(y===null||y===undefined||y==="") return -1;
    if(typeof x==="string") return x.localeCompare(y)*dir;
    return (x-y)*dir;
  });
  // sort arrows
  document.querySelectorAll("th[data-k]").forEach(th=>{
    const a=th.querySelector(".arrow");
    a.textContent = th.dataset.k===k ? (dir>0?" ▲":" ▼") : "";
  });
  const tb=document.getElementById("tbody");
  tb.innerHTML = rows.map(d=>`
    <tr>
      <td class="num pos">${d.position??""}</td>
      <td class="pname"><a href="${d.profile_url}" target="_blank" rel="noopener">${d.player}</a></td>
      <td><span class="flag">${d.country||"—"}</span></td>
      <td class="num">${d.points!=null?d.points.toLocaleString():""}</td>
      <td class="num">${d.age??'<span class="muted">—</span>'}</td>
      <td class="muted">${d.birthdate||"—"}</td>
      <td class="num">${d.height_m!=null?d.height_m.toFixed(2):'<span class="muted">—</span>'}</td>
      <td>${d.playing_side?`<span class="side ${d.playing_side}">${d.playing_side}</span>`:'<span class="muted">—</span>'}</td>
      <td class="muted">${d.place_of_birth||"—"}</td>
      <td><a class="fip" href="${d.profile_url}" target="_blank" rel="noopener">profile ↗</a></td>
    </tr>`).join("");
  document.getElementById("count").innerHTML = `Showing <b>${rows.length}</b> of ${DATA.length} players`;
}
render();
</script>
</body>
</html>
"""


def main():
    rows = load_rows()
    # Pull a ranking date if available from any row's nothing — use placeholder.
    date = "22/06/2026"
    html = HTML.replace("__DATA__", json.dumps(rows, ensure_ascii=False))
    html = html.replace("__DATE__", date)
    with open(OUTPUT, "w", encoding="utf-8") as f:
        f.write(html)
    print(f"Wrote {OUTPUT} with {len(rows)} players embedded.")


if __name__ == "__main__":
    main()
