(() => {
  "use strict";

  const USE_CASES = JSON.parse(document.getElementById("use-cases").textContent);
  const INITIAL = JSON.parse(document.getElementById("initial-use-case").textContent);
  const AUTORUN = JSON.parse(document.getElementById("autorun").textContent); // ?run=1 or ?run=all
  const $ = (id) => document.getElementById(id);
  const TYPE_NAMES = { choice: "Choice", score: "Scale", noul: "Yes / No" };

  const session = { runs: [] }; // {ms, fields}
  let current = null;
  let busy = false;
  let autoran = false;

  // ---------- helpers ----------
  function el(tag, attrs = {}, ...children) {
    const node = document.createElement(tag);
    for (const [k, v] of Object.entries(attrs)) {
      if (v == null || v === false) continue;
      if (k === "class") node.className = v;
      else if (k === "style") node.style.cssText = v;
      else if (k === "text") node.textContent = v;
      else if (k.startsWith("on")) node.addEventListener(k.slice(2), v);
      else node.setAttribute(k, v === true ? "" : v);
    }
    for (const c of children.flat()) {
      if (c == null) continue;
      node.append(c instanceof Node ? c : document.createTextNode(String(c)));
    }
    return node;
  }
  const pct = (p) => `${Math.round(p * 100)}%`;
  const ms = (v) => (v == null ? "–" : v < 10 ? `${v.toFixed(1)} ms` : `${Math.round(v)} ms`);
  const cookie = (name) => document.cookie.split("; ").find((c) => c.startsWith(name + "="))?.split("=")[1];
  function percentile(values, p) {
    if (!values.length) return null;
    const s = [...values].sort((a, b) => a - b);
    const k = (s.length - 1) * p / 100, lo = Math.floor(k), hi = Math.min(lo + 1, s.length - 1);
    return s[lo] + (s[hi] - s[lo]) * (k - lo);
  }
  function tipAttrs(html) { return { "data-tip": html }; }
  const escapeHtml = (s) => String(s).replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));

  // ---------- tooltip ----------
  const tip = $("tooltip");
  document.addEventListener("pointermove", (e) => {
    const target = e.target.closest("[data-tip]");
    if (!target) { tip.hidden = true; return; }
    tip.innerHTML = target.getAttribute("data-tip");
    tip.hidden = false;
    const r = tip.getBoundingClientRect();
    let x = e.clientX + 14, y = e.clientY + 14;
    if (x + r.width > innerWidth - 8) x = e.clientX - r.width - 14;
    if (y + r.height > innerHeight - 8) y = e.clientY - r.height - 14;
    tip.style.left = `${x}px`; tip.style.top = `${y}px`;
  });
  document.addEventListener("pointerleave", () => { tip.hidden = true; });

  // ---------- model status ----------
  async function pollStatus() {
    try {
      const res = await fetch("/api/status");
      const s = await res.json();
      const pill = $("model-pill");
      pill.dataset.state = s.status === "ready" ? "ready" : s.status === "error" ? "error" : "loading";
      $("model-pill-text").textContent =
        s.status === "ready" ? "Model ready · on-device" :
        s.status === "error" ? "Model failed to load" :
        "Loading model… (first run downloads 843 MB)";
      if (s.status === "error") pill.title = s.error;
      $("hw").textContent = s.hardware;
      $("stat-hw").textContent = `runs on ${s.hardware}`;
      if (s.load_seconds != null) $("load-time").textContent = `${s.load_seconds.toFixed(1)} s`;
      renderServerStats(s.stats);
      if (s.status === "ready" && AUTORUN && !autoran) {
        autoran = true;
        AUTORUN === "all" ? runAll() : runOne();
      }
      if (s.status !== "ready" && s.status !== "error") setTimeout(pollStatus, 1500);
    } catch {
      setTimeout(pollStatus, 3000);
    }
  }

  function renderServerStats(stats) {
    if (!stats) return;
    $("total-runs").textContent = stats.total_predictions.toLocaleString();
    $("p95").textContent = ms(stats.p95_ms);
    if (stats.decisions_per_second != null) {
      $("stat-dps").textContent = Math.round(stats.decisions_per_second).toLocaleString();
    }
    if (stats.p50_ms != null) {
      $("stat-p50").textContent = ms(stats.p50_ms);
      $("hero-ms").textContent = `~${Math.round(stats.p50_ms)} ms`;
      $("stat-p50-sub").textContent = `model time, last ${stats.window} runs`;
    }
  }

  // ---------- use case nav ----------
  function renderNav() {
    const list = $("usecase-list");
    list.replaceChildren(...USE_CASES.map((uc) =>
      el("button", { class: "uc-btn", type: "button", "data-slug": uc.slug, onclick: () => select(uc.slug) },
        el("span", { class: "ind", text: uc.industry }),
        el("span", { class: "nm", text: uc.name }))));
  }

  function select(slug, { keepText = false } = {}) {
    current = USE_CASES.find((u) => u.slug === slug) || USE_CASES[0];
    if (!current) return;
    document.querySelectorAll(".uc-btn").forEach((b) => b.setAttribute("aria-current", b.dataset.slug === current.slug));
    $("uc-industry").textContent = current.industry;
    $("uc-name").textContent = current.name;
    $("uc-tagline").textContent = current.tagline;
    $("uc-description").textContent = current.description;
    $("uc-value").textContent = current.business_value;
    $("input-label").textContent = current.input_label;
    $("examples").replaceChildren(...current.examples.map((ex, i) =>
      el("button", { class: "chip", type: "button", "aria-pressed": "false", "data-i": i,
        onclick: (e) => pickExample(i, e.currentTarget) }, ex.title)));
    $("decides").replaceChildren(...current.fields.map((f) =>
      el("span", { class: "tag", ...tipAttrs(`<b>${escapeHtml(f.label)}</b><br>${escapeHtml(f.instructions)}`) },
        f.label, " ", el("span", { class: "t", text: `· ${TYPE_NAMES[f.type]}` }))));
    $("result").hidden = true;
    $("batch").hidden = true;
    $("error").textContent = "";
    if (!keepText && current.examples.length) pickExample(0, $("examples").firstChild);
    const url = new URL(location.href);
    url.searchParams.set("use_case", current.slug);
    history.replaceState(null, "", url);
  }

  function pickExample(i, chip) {
    $("message").value = current.examples[i].text;
    document.querySelectorAll(".chip").forEach((c) => c.setAttribute("aria-pressed", c === chip));
  }

  // ---------- classify ----------
  async function classify(text) {
    const started = performance.now();
    const res = await fetch("/api/classify", {
      method: "POST",
      headers: { "Content-Type": "application/json", "X-CSRFToken": cookie("csrftoken") || "" },
      body: JSON.stringify({ use_case: current.slug, text }),
    });
    const data = await res.json().catch(() => ({}));
    if (!res.ok || !data.answers) {
      const hint = res.status === 403 ? ": your session expired, reload the page" : "";
      throw new Error(data.error || `Request failed (${res.status})${hint}`);
    }
    data.metrics.rtt_ms = performance.now() - started;
    session.runs.push({ ms: data.metrics.model_ms, fields: data.metrics.fields });
    renderMetrics(data);
    return data;
  }

  async function runOne() {
    const text = $("message").value.trim();
    if (!text || busy) return;
    setBusy(true);
    try {
      const data = await classify(text);
      renderResult(data);
    } catch (err) {
      $("error").textContent = err.message;
    } finally {
      setBusy(false);
    }
  }

  async function runAll() {
    if (busy || !current.examples.length) return;
    setBusy(true);
    $("result").hidden = true;
    const uc = current;
    const table = $("batch-table");
    const head = el("tr", {},
      el("th", { text: "Example" }),
      uc.fields.map((f) => el("th", { text: f.label })),
      el("th", { text: "Decision" }),
      el("th", { class: "num", text: "Model" }));
    const rows = uc.examples.map((ex) => el("tr", { class: "pending" },
      el("td", {}, el("div", { text: ex.title }), el("div", { class: "sub", text: ex.text.length > 70 ? ex.text.slice(0, 68) + "…" : ex.text })),
      uc.fields.map(() => el("td", { text: "…" })), el("td", { text: "…" }), el("td", { class: "num", text: "…" })));
    table.replaceChildren(el("thead", {}, head), el("tbody", {}, rows));
    $("batch").hidden = false;
    $("batch-summary").textContent = `Running ${uc.examples.length} messages…`;

    const done = [];
    for (let i = 0; i < uc.examples.length; i++) {
      if (current !== uc) break;
      try {
        const data = await classify(uc.examples[i].text);
        done.push(data);
        const cells = [
          el("td", {}, el("div", { text: uc.examples[i].title }), el("div", { class: "sub", text: rows[i].querySelector(".sub").textContent })),
          ...uc.fields.map((f) => {
            const a = data.answers[f.key];
            return el("td", {}, el("div", { text: shortAnswer(f, a) }), el("div", { class: "sub mono", text: `conf ${pct(a.confidence)}` }));
          }),
          el("td", {}, decisionBadge(data.decision)),
          el("td", { class: "num", text: ms(data.metrics.model_ms) }),
        ];
        rows[i].className = "";
        rows[i].replaceChildren(...cells);
      } catch (err) {
        rows[i].lastChild.textContent = "error";
        $("error").textContent = err.message;
      }
    }
    if (done.length) {
      const auto = done.filter((d) => d.decision === "automate").length;
      const total = done.reduce((s, d) => s + d.metrics.model_ms, 0);
      const fields = done.reduce((s, d) => s + d.metrics.fields, 0);
      $("batch-summary").textContent =
        `${auto} of ${done.length} automated · ${fields} decisions in ${ms(total)} total · avg ${ms(total / done.length)} per message`;
    }
    setBusy(false);
  }

  function setBusy(v) {
    busy = v;
    $("run").disabled = v;
    $("run-all").disabled = v;
    if (v) $("error").textContent = "";
  }

  // ---------- rendering ----------
  // Scale fields: name the most likely level. The expected score can sit between levels.
  const topLevel = (a) => Number(Object.entries(a.probabilities).reduce((m, e) => (e[1] > m[1] ? e : m))[0]);

  function shortAnswer(field, a) {
    if (field.type === "choice") return a.choice;
    if (field.type === "noul") return a.noul >= 0.5 ? `Yes (${pct(a.noul)})` : `No (${pct(1 - a.noul)})`;
    return a.legend[String(topLevel(a))];
  }

  function decisionBadge(kind) {
    return el("span", { class: `badge ${kind}` }, kind === "automate" ? "✓ Automate" : "⚠ Human review");
  }

  function renderResult(data) {
    const d = $("decision");
    d.dataset.kind = data.decision;
    const why = data.decision === "automate"
      ? "Every gated answer cleared its confidence threshold. Safe to act without a person."
      : `Low confidence on ${data.reasons.map((r) => `${r.label} (${pct(r.confidence)} < ${pct(r.required)})`).join(", ")}. Route to a person.`;
    d.replaceChildren(
      el("span", { class: "icon", "aria-hidden": "true" }, data.decision === "automate" ? "✓" : "!"),
      el("div", {}, el("div", { class: "title", text: data.decision === "automate" ? "Automate" : "Send to human review" })),
      el("div", { class: "why", text: why }),
      el("div", { class: "speed", text: `${data.metrics.fields} decisions · ${ms(data.metrics.model_ms)}` }));

    $("fields").replaceChildren(...current.fields.map((f) => fieldCard(f, data.answers[f.key])));
    $("result").hidden = false;
    $("batch").hidden = true;
  }

  function fieldCard(f, a) {
    let answer, viz;
    if (f.type === "choice") {
      answer = el("div", { class: "answer" }, a.choice, el("small", { text: pct(a.probabilities[a.choice]) }));
      viz = el("div", { class: "bars" }, Object.entries(a.probabilities).map(([label, p]) => {
        const desc = f.options?.[label];
        return el("div", { class: `bar-row${label === a.choice ? " win" : ""}`,
          ...tipAttrs(`<b>${escapeHtml(label)}</b> · ${pct(p)}${desc ? `<br>${escapeHtml(desc)}` : ""}`) },
          el("span", { class: "bl", text: label }),
          el("span", { class: "track" }, el("span", { class: "fill", style: `display:block;width:${Math.max(p * 100, 0.5)}%` })),
          el("span", { class: "bv", text: pct(p) }));
      }));
    } else if (f.type === "score") {
      const n = Object.keys(a.legend).length;
      const level = topLevel(a);
      const pos = n > 1 ? (a.score / (n - 1)) * 100 : 0;
      answer = el("div", { class: "answer" }, a.legend[String(level)], el("small", { text: pct(a.probabilities[String(level)]) }));
      const probs = Object.entries(a.probabilities).map(([i, p]) => `${escapeHtml(a.legend[i])}: ${pct(p)}`).join("<br>");
      viz = el("div", { class: "scale", ...tipAttrs(`<b>Most likely: ${escapeHtml(a.legend[String(level)])}</b><br>${probs}<br>Expected level ${a.score.toFixed(2)} of ${n - 1}`) },
        el("div", { class: "scale-track" },
          el("div", { class: "scale-fill", style: `width:${pos}%` }),
          el("div", { class: "scale-marker", style: `left:${pos}%` })),
        el("div", { class: "scale-ticks" }, Object.entries(a.legend).map(([i, label]) =>
          el("span", { class: Number(i) === level ? "on" : "", text: label }))));
    } else {
      const yes = a.noul >= 0.5;
      answer = el("div", { class: "answer" }, yes ? "Yes" : "No", el("small", { text: pct(yes ? a.noul : 1 - a.noul) }));
      viz = el("div", { ...tipAttrs(`<b>Probability “yes”: ${pct(a.noul)}</b><br>50% line marks the decision boundary`) },
        el("div", { class: "meter" },
          el("div", { class: "fill", style: `width:${a.noul * 100}%` }),
          el("div", { class: "mid" })),
        el("div", { class: "meter-legend" }, el("span", { text: "No" }), el("span", { text: "Yes" })));
    }

    const gated = f.min_confidence != null;
    const ok = !gated || a.confidence >= f.min_confidence;
    const status = !gated
      ? el("span", { class: "status none", text: "informational" })
      : ok ? el("span", { class: "status ok" }, "✓ ", "confident")
           : el("span", { class: "status low" }, "⚠ ", "below gate");
    const conf = el("div", { class: "conf",
        ...tipAttrs(`<b>Confidence ${pct(a.confidence)}</b>${gated ? `<br>Automation gate: ${pct(f.min_confidence)}` : "<br>This field doesn't gate automation"}`) },
      el("span", { text: `Confidence ${pct(a.confidence)}` }),
      el("span", { class: "cm" },
        el("span", { class: "fill", style: `width:${a.confidence * 100}%` }),
        gated ? el("span", { class: "gate", style: `left:${f.min_confidence * 100}%` }) : null),
      status);

    return el("div", { class: "card field" },
      el("div", { class: "fhead" }, el("span", { class: "flabel", text: f.label }), el("span", { class: "ftype", text: TYPE_NAMES[f.type] })),
      el("div", { class: "question", text: f.instructions }),
      answer, viz, conf);
  }

  function renderMetrics(data) {
    const m = data.metrics;
    $("m-model").textContent = ms(m.model_ms);
    $("m-server").textContent = ms(m.server_ms);
    $("m-rtt").textContent = ms(m.rtt_ms);
    $("m-fields").textContent = m.fields;
    $("m-tokens").textContent = m.input_tokens.toLocaleString();
    $("m-throughput").textContent = `${Math.round(m.fields / (m.model_ms / 1000))} decisions/s`;
    renderServerStats(data.stats);
    renderHistogram();
  }

  function renderHistogram() {
    const runs = session.runs.slice(-40);
    const values = runs.map((r) => r.ms);
    const max = Math.max(...values) * 1.1;
    const p50 = percentile(session.runs.map((r) => r.ms), 50);
    const p95 = percentile(session.runs.map((r) => r.ms), 95);
    const hist = $("hist");
    hist.replaceChildren(
      ...runs.map((r, i) => el("div", { class: "b", style: `height:${(r.ms / max) * 100}%`,
        ...tipAttrs(`<b>${ms(r.ms)}</b><br>run ${session.runs.length - runs.length + i + 1} · ${r.fields} decisions`) })),
      el("div", { class: "p50", style: `bottom:${(p50 / max) * 100}%` }, el("span", { text: `p50 ${ms(p50)}` })));
    $("hist-summary").textContent = `${session.runs.length} runs · p95 ${ms(p95)}`;
  }

  // ---------- wire up ----------
  $("run").addEventListener("click", runOne);
  $("run-all").addEventListener("click", runAll);
  $("message").addEventListener("keydown", (e) => {
    if (e.key === "Enter" && (e.metaKey || e.ctrlKey)) { e.preventDefault(); runOne(); }
  });
  $("message").addEventListener("input", () =>
    document.querySelectorAll(".chip").forEach((c) => c.setAttribute("aria-pressed", "false")));
  if (!/Mac|iPhone|iPad/.test(navigator.platform)) document.querySelector("#run kbd").textContent = "Ctrl↵";

  renderNav();
  if (USE_CASES.length) select(INITIAL || USE_CASES[0].slug);
  else $("uc-name").textContent = "No active use cases. Add one in the admin panel.";
  pollStatus();
})();
