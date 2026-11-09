(function () {
  "use strict";

  const PLACEHOLDER = { food: "🐟", litter: "🪣", meds: "💧" };
  const STORE_NAME = { amazon: "Amazon", walmart: "Walmart" };
  const $ = (id) => document.getElementById(id);

  const defaults = { cat: "all", store: "all", brand: "all", sort: "discount", onlyLow: false, sns: false, q: "", tiers: null };

  // The price/discount shown for an item, depending on the Subscribe & Save switch.
  function view(d) {
    if (state.sns && d.sns_tier) {
      return { price: d.sns_price, ratio: d.sns_ratio, pct: d.sns_pct_off, tier: d.sns_tier,
               ref: d.sns_ref_price, refType: d.sns_ref_type, sns: true };
    }
    if (!d.tier) return null;
    return { price: d.price, ratio: d.ratio, pct: d.pct_off, tier: d.tier, ref: d.ref_price, refType: d.ref_type, sns: false };
  }
  let state = Object.assign({}, defaults);
  try {
    const saved = JSON.parse(localStorage.getItem("catdeals-filters") || "null");
    if (saved) state = Object.assign(state, saved, { q: "" });
  } catch (e) { /* storage unavailable */ }
  const save = () => { try { localStorage.setItem("catdeals-filters", JSON.stringify(state)); } catch (e) {} };

  let DATA = null;

  const esc = (s) => String(s == null ? "" : s).replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
  const money = (n) => "$" + Number(n).toFixed(2);

  fetch("data/deals.json", { cache: "no-cache" })
    .then((r) => { if (!r.ok) throw new Error(r.status); return r.json(); })
    .then((d) => { DATA = d; init(); })
    .catch(() => { $("list").innerHTML = '<div class="empty">还没有数据。等今天的自动任务跑完再来看看 🐱</div>'; });

  function init() {
    if (!state.tiers) state.tiers = DATA.tiers.map((t) => t.key);
    renderMeta();
    renderStores();
    $("sort").value = state.sort;
    $("onlyLow").checked = state.onlyLow;
    $("sort").onchange = (e) => { state.sort = e.target.value; update(); };
    $("onlyLow").onchange = (e) => { state.onlyLow = e.target.checked; update(); };
    $("sns").checked = state.sns;
    $("sns").onchange = (e) => { state.sns = e.target.checked; update(); };
    $("q").oninput = (e) => { state.q = e.target.value.trim().toLowerCase(); update(); };
    $("brand").onchange = (e) => { state.brand = e.target.value; update(); };
    update();
  }

  function renderMeta() {
    const when = new Date(DATA.generated_at);
    const parts = [`<span class="pill">更新于 ${esc(when.toLocaleString("zh-CN", { month: "numeric", day: "numeric", hour: "2-digit", minute: "2-digit" }))}</span>`];
    Object.values(DATA.sources || {}).forEach((s) => {
      const txt = s.status === "ok" ? "正常" : s.status === "partial" ? "部分失败" : "今日抓取失败";
      parts.push(`<span class="pill"><span class="dot ${esc(s.status)}"></span>${esc(s.label)} ${txt}</span>`);
    });
    $("meta").innerHTML = parts.join("");
    if (DATA.demo) {
      $("banner").innerHTML = '<div class="banner">⚠️ 现在显示的是<b>示例数据</b>，价格是随机生成的。填好 Amazon / Walmart 的接口密钥后，第二天就会换成真实折扣。</div>';
    }
  }

  function renderStores() {
    const opts = [["all", "全部商店"], ["amazon", "Amazon"], ["walmart", "Walmart"]];
    $("stores").innerHTML = opts.map(([k, l]) => `<button type="button" data-k="${k}" aria-pressed="${state.store === k}">${l}</button>`).join("");
    $("stores").querySelectorAll("button").forEach((b) => b.onclick = () => { state.store = b.dataset.k; renderStores(); update(); });
  }

  function base(opts) {
    // Everything except the dimension being counted.
    const o = Object.assign({ cat: true, store: true, brand: true, tiers: true }, opts);
    return DATA.deals.filter((d) =>
      view(d) &&
      (!o.cat || state.cat === "all" || d.category === state.cat) &&
      (!o.store || state.store === "all" || d.store === state.store) &&
      (!o.brand || state.brand === "all" || d.brand === state.brand) &&
      (!o.tiers || state.tiers.includes(view(d).tier)) &&
      (!state.onlyLow || d.is_low30) &&
      (!state.q || (d.title + " " + d.brand).toLowerCase().includes(state.q)));
  }

  function renderTabs() {
    const pool = base({ cat: false });
    const count = (c) => pool.filter((d) => c === "all" || d.category === c).length;
    const tabs = [["all", "全部"]].concat(Object.entries(DATA.categories));
    $("tabs").innerHTML = tabs.map(([k, l]) =>
      `<button class="tab" role="tab" data-k="${k}" aria-selected="${state.cat === k}">${esc(l)}<span class="n">${count(k)}</span></button>`).join("");
    $("tabs").querySelectorAll(".tab").forEach((b) => b.onclick = () => {
      state.cat = b.dataset.k;
      const ok = DATA.brands.some((x) => x.brand === state.brand && (state.cat === "all" || x.category === state.cat));
      if (!ok) state.brand = "all";
      update();
    });
  }

  function renderBrands() {
    const pool = base({ brand: false });
    const n = {};
    pool.forEach((d) => { n[d.brand] = (n[d.brand] || 0) + 1; });
    const groups = {};
    DATA.brands.filter((b) => state.cat === "all" || b.category === state.cat).forEach((b) => {
      const g = DATA.categories[b.category];
      (groups[g] = groups[g] || []).push(b);
    });
    let html = `<option value="all">全部品牌</option>`;
    Object.entries(groups).forEach(([g, list]) => {
      html += `<optgroup label="${esc(g)}">` + list.map((b) =>
        `<option value="${esc(b.brand)}"${state.brand === b.brand ? " selected" : ""}>${esc(b.group ? b.group + " · " + b.brand : b.brand)} (${n[b.brand] || 0})</option>`).join("") + `</optgroup>`;
    });
    $("brand").innerHTML = html;
    $("brand").value = state.brand;
  }

  function renderTierbar() {
    const pool = base({ tiers: false });
    $("tierbar").innerHTML = DATA.tiers.map((t) => {
      const c = pool.filter((d) => view(d).tier === t.key).length;
      return `<button type="button" class="chip" data-tier="${esc(t.key)}" aria-pressed="${state.tiers.includes(t.key)}" title="${esc(t.sub)}">${esc(t.label)}<span class="n">${c}</span></button>`;
    }).join("");
    $("tierbar").querySelectorAll(".chip").forEach((b) => b.onclick = () => {
      const k = b.dataset.tier;
      state.tiers = state.tiers.includes(k) ? state.tiers.filter((x) => x !== k) : state.tiers.concat(k);
      update();
    });
  }

  function sorter() {
    if (state.sort === "price") return (a, b) => view(a).price - view(b).price;
    if (state.sort === "low30") return (a, b) => (b.is_low30 - a.is_low30) || (view(a).ratio - view(b).ratio);
    return (a, b) => (view(a).ratio - view(b).ratio) || (view(a).price - view(b).price);
  }

  function card(d) {
    const v = view(d);
    const refNote = { listed: "", high30: "30天最高", onetime: "单次购买价" }[v.refType] || "";
    const ref = `<span class="was"${v.refType === "high30" ? ' title="商家没标原价，用本站记录的30天最高价"' : ""}>${money(v.ref)}</span>`
      + (refNote ? `<span class="small">${refNote}</span>` : "");
    const snsLine = v.sns
      ? `<div class="small sns">订阅价 · 单次购买 ${money(d.price)}</div>`
      : (d.sns_price ? `<div class="small sns">订阅价 ${money(d.sns_price)}</div>` : "");
    const img = d.image
      ? `<img src="${esc(d.image)}" alt="" loading="lazy" referrerpolicy="no-referrer">`
      : `<span class="ph">${PLACEHOLDER[d.category] || "🐾"}</span>`;
    const badges = [
      d.is_low30 ? `<span class="badge low">30天最低</span>` : "",
      d.deal ? `<span class="badge">${esc(d.deal)}</span>` : "",
      d.stale ? `<span class="badge stale">昨日数据</span>` : "",
    ].join("");
    return `<article class="card" data-tier="${esc(v.tier)}">
      <div class="thumb">${img}<span class="off">-${v.pct}%</span><span class="store ${esc(d.store)}">${STORE_NAME[d.store] || esc(d.store)}</span></div>
      <div class="body">
        <div class="brandline"><span>${esc(d.group ? d.group + " · " + d.brand : d.brand)}</span>${badges}</div>
        <h3 class="title" title="${esc(d.title)}">${esc(d.title)}</h3>
        <div class="prices"><span class="now">${money(v.price)}</span>${ref}</div>
        ${snsLine}
        ${d.unit_price ? `<div class="small">${esc(d.unit_price)}</div>` : ""}
        <a class="go" href="${esc(d.url)}" target="_blank" rel="nofollow sponsored noopener">去 ${STORE_NAME[d.store] || "商店"} 看看 →</a>
      </div>
    </article>`;
  }

  function renderList() {
    const items = base({}).sort(sorter());
    if (!items.length) {
      $("list").innerHTML = '<div class="empty">这个筛选条件下今天没有折扣 😿<br>换个品牌或档位试试</div>';
      return;
    }
    $("list").innerHTML = DATA.tiers.filter((t) => state.tiers.includes(t.key)).map((t) => {
      const list = items.filter((d) => view(d).tier === t.key);
      if (!list.length) return "";
      return `<section class="tier" data-tier="${esc(t.key)}">
        <div class="tier-head"><h2>${esc(t.label)}</h2><span class="sub">${esc(t.sub)}</span><span class="count">${list.length} 件</span></div>
        <div class="grid">${list.map(card).join("")}</div>
      </section>`;
    }).join("");
  }

  function update() {
    save();
    renderTabs();
    renderBrands();
    renderTierbar();
    renderList();
  }
})();
