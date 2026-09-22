(() => {
  "use strict";

  const $ = (id) => document.getElementById(id);
  const slides = [...document.querySelectorAll(".slide")];
  const progress = $("progress");
  let current = 0;

  // ---------- navigation ----------
  const dots = slides.map((s, i) => {
    const b = document.createElement("button");
    b.type = "button";
    b.setAttribute("aria-label", `Slide ${i + 1}: ${s.dataset.title}`);
    b.addEventListener("click", () => go(i));
    progress.append(b);
    return b;
  });

  function go(i, { push = true } = {}) {
    current = Math.max(0, Math.min(slides.length - 1, i));
    slides.forEach((s, j) => {
      s.classList.toggle("active", j === current);
      s.classList.toggle("before", j < current);
      s.setAttribute("aria-hidden", j !== current);
      s.inert = j !== current;
    });
    dots.forEach((d, j) => {
      d.setAttribute("aria-current", j === current);
      d.classList.toggle("done", j < current);
    });
    document.querySelector('[data-go="prev"].nav-btn').disabled = current === 0;
    document.querySelector('[data-go="next"].nav-btn').disabled = current === slides.length - 1;
    $("slide-count").textContent = `${current + 1} / ${slides.length}`;
    slides[current].scrollTop = 0;
    if (push) history.replaceState(null, "", `#${current + 1}`);
  }

  document.addEventListener("click", (e) => {
    const t = e.target.closest("[data-go]");
    if (t) go(current + (t.dataset.go === "next" ? 1 : -1));
  });

  document.addEventListener("keydown", (e) => {
    if (e.target.closest("input, textarea")) return;
    if (["ArrowRight", "PageDown", " "].includes(e.key)) { e.preventDefault(); go(current + 1); }
    else if (["ArrowLeft", "PageUp"].includes(e.key)) { e.preventDefault(); go(current - 1); }
    else if (e.key === "Home") go(0);
    else if (e.key === "End") go(slides.length - 1);
  });

  let touchX = null;
  document.addEventListener("touchstart", (e) => {
    touchX = e.target.closest("input") ? null : e.touches[0].clientX;
  }, { passive: true });
  document.addEventListener("touchend", (e) => {
    if (touchX == null) return;
    const dx = e.changedTouches[0].clientX - touchX;
    if (Math.abs(dx) > 60) go(current + (dx < 0 ? 1 : -1));
    touchX = null;
  });

  // ---------- cost calculator ----------
  // Volume slider is logarithmic: 0..100 maps to 10k..10M messages a month.
  const volumeFromSlider = (v) => Math.round(10 ** (4 + (3 * v) / 100) / 1000) * 1000;
  const compact = new Intl.NumberFormat("en", { notation: "compact", maximumFractionDigits: 1 });
  const money = (v) => v >= 100000
    ? `$${compact.format(v)}`
    : `$${v.toLocaleString("en", { maximumFractionDigits: v < 100 ? 2 : 0 })}`;

  function recalc() {
    const volume = volumeFromSlider(Number($("in-volume").value));
    const share = Number($("in-share").value) / 100;
    const cost = Math.max(0, Number($("in-cost").value) || 0);
    const all = volume * cost;
    const hybrid = volume * (1 - share) * cost;
    const saved = all - hybrid;

    $("out-volume").textContent = compact.format(volume);
    $("out-share").textContent = `${Math.round(share * 100)}%`;
    $("bar-all").style.width = all ? "100%" : "0";
    $("bar-hybrid").style.width = all ? `${(hybrid / all) * 100}%` : "0";
    $("val-all").textContent = money(all);
    $("val-hybrid").textContent = money(hybrid);
    $("saving").textContent = `${money(saved)}/mo · ${money(saved * 12)}/yr`;

    const rows = document.querySelectorAll(".bc-row");
    rows[0].dataset.tip = `<b>${compact.format(volume)} LLM calls</b><br>× $${cost} = ${money(all)} a month`;
    rows[1].dataset.tip = `<b>${compact.format(Math.round(volume * (1 - share)))} LLM calls</b><br>` +
      `System 1 handles ${compact.format(Math.round(volume * share))} on its own<br>= ${money(hybrid)} a month`;
  }
  ["in-volume", "in-share", "in-cost"].forEach((id) => $(id).addEventListener("input", recalc));

  // ---------- tooltip ----------
  const tip = $("tooltip");
  document.addEventListener("pointermove", (e) => {
    const target = e.target.closest("[data-tip]");
    if (!target || !target.dataset.tip) { tip.hidden = true; return; }
    tip.innerHTML = target.dataset.tip;
    tip.hidden = false;
    const r = tip.getBoundingClientRect();
    let x = e.clientX + 14, y = e.clientY + 14;
    if (x + r.width > innerWidth - 8) x = e.clientX - r.width - 14;
    if (y + r.height > innerHeight - 8) y = e.clientY - r.height - 14;
    tip.style.left = `${x}px`; tip.style.top = `${y}px`;
  });

  recalc();
  const fromHash = parseInt(location.hash.slice(1), 10);
  go(Number.isFinite(fromHash) ? fromHash - 1 : 0, { push: false });
})();
