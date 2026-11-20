/* BV-NOFLICKER 전환 회귀 테스트 — 라이브 페이지를 받아 v1 블록을 그대로(v1) 또는 v2 로 바꿔 끼워(v2) 크로뮴에서 프레임 단위로 잰다.
   사용: node test_transition.js live|v2 [--shots 폴더]
     live = 라이브 그대로 잰다(배포 전: 문제 재현 · 배포 후: 모두 통과해야 함, v1 이라고 써도 같다)
     v2   = 라이브의 v1 블록을 noflicker_v2.html 로 바꿔 끼워 잰다(배포 전 확인)
   필요: playwright(크로뮴), m.bonovista.com·www.bonovista.com·bv-data.bonovista30.workers.dev(필터 색인)에 닿는 네트워크. 외부 호스트(GA·폰트 등)는 끊고 잰다.
   iOS 의 깨진 그림 아이콘(?)은 크로뮴에서 그대로 재현되지 않는다 — 대신 "아직 못 받은/깨진 사진이 화면에 보이는 프레임 수"를 센다.

   경우
     A 모바일 · 첫 그리기가 늦은 상황(시계를 당겨 재현) · 메인 사진 → NEW 슬라이드가 중간에 끊기는가
     B 모바일 · NEW 진입 · 받는 중인 사진이 보이는 프레임 / 첫 화면 사진 요청 시작 시각
     C 모바일 · tiny 404(관리자 업로드분) → onerror 로 medium 대체 · 깨진 사진이 보이는 프레임
     D 모바일 · NEW 필터 "재고만" → 필터 카드(bv_gender.js card()) · 카드 사진이 숨은 채 남는가
     E PC · NEW 진입 · B 와 같음 + 받기 전후 사진 높이 + 마우스 올림 둘째 사진(thumber_2)
     F 모바일 · NEW → 상품 → 뒤로 · 돌아온 첫 화면에 사진이 바로 보이는가 */
const { chromium, devices } = require("playwright");
const fs = require("fs"), path = require("path");

const MODE = process.argv[2];
if (!["live", "v1", "v2"].includes(MODE)) { console.error("사용: node test_transition.js live|v2 [--shots 폴더]"); process.exit(2); }
const SHOTS = process.argv.includes("--shots") ? process.argv[process.argv.indexOf("--shots") + 1] : null;
const V1 = fs.readFileSync(path.join(__dirname, "noflicker_v1_live.html"), "utf8").trim();
const V2 = fs.readFileSync(path.join(__dirname, "noflicker_v2.html"), "utf8").trim();
const Q = "ul.prdList .thumbnail a>img:first-of-type";

/* 프레임 기록: 앞 여섯 장의 상태·불투명도, 목록·본문 불투명도, 슬라이드 클래스가 떨어질 때의 애니메이션 진행 */
const INSTR = `(() => {
  const Q = ${JSON.stringify(Q)}, log = window.__bvLog = [], cut = window.__bvCut = [], an = window.__bvAnim = {};
  ["animationstart", "animationend", "animationcancel"].forEach((k) => addEventListener(k, (e) => { if (e.animationName === "bvSlideUp" && an[k] == null) an[k] = Math.round(performance.now()); }, true));
  function op(el){ let o = 1; for (let e = el; e && e.nodeType === 1; e = e.parentElement) o *= +getComputedStyle(e).opacity; return o; }
  (function arm(){
    const h = document.documentElement; if (!h) return setTimeout(arm, 0);
    let had = false;
    new MutationObserver(() => {
      const has = h.classList.contains("bv-slide");
      if (has && window.__bvSlideAt == null) window.__bvSlideAt = performance.now();
      if (had && !has) { const c = document.getElementById("contents") || document.getElementById("container");
        const a = c && c.getAnimations ? c.getAnimations().find(x => x.animationName === "bvSlideUp") : null;
        cut.push({ t: Math.round(performance.now()), state: a ? a.playState : "none", at: a ? Math.round(a.currentTime) : null,
                   top: c ? Math.round(c.getBoundingClientRect().top) : null }); }
      had = has;
    }).observe(h, { attributes: true, attributeFilter: ["class"] });
    had = h.classList.contains("bv-slide");
  })();
  (function f(){
    const ul = document.querySelector("ul.prdList"), c = document.getElementById("contents");
    const row = { t: Math.round(performance.now()), slide: !!(document.documentElement && document.documentElement.classList.contains("bv-slide")),
      top: c ? Math.round(c.getBoundingClientRect().top) : null, imgs: [] };
    document.querySelectorAll(Q).forEach((m, k) => {
      if (k >= 6) return; const r = m.getBoundingClientRect();
      row.imgs.push({ ok: m.complete && m.naturalWidth > 0, err: m.complete && !m.naturalWidth && !!m.getAttribute("src"),
        op: +op(m).toFixed(3), self: +(+getComputedStyle(m).opacity).toFixed(3), h: Math.round(r.height), inView: r.top < innerHeight && r.bottom > 0 });
    });
    log.push(row);
    if (performance.now() < 15000) requestAnimationFrame(f);
  })();
})();`;

const MEMO = new Map();                                                   /* 사진 외 응답 캐시: 프록시 지연이 첫 그리기 시점을 흔들지 않게 */
async function cached(r) {
  const u = r.request().url();
  if (!MEMO.has(u)) { const res = await r.fetch(); MEMO.set(u, { status: res.status(), headers: res.headers(), body: await res.body() }); }
  const m = MEMO.get(u); return { status: m.status, headers: m.headers, body: m.body };
}
async function newCtx(browser, device, { delayHead = 0, tiny404 = 0 } = {}) {
  const ctx = await browser.newContext({ ...device, reducedMotion: "no-preference" });
  const deny = new Set();
  await ctx.route("**/*", async (r) => {
    const req = r.request(), u = new URL(req.url());
    if (!/(^|\.)bonovista\.com$/.test(u.hostname) && u.hostname !== "bv-data.bonovista30.workers.dev") return r.abort();   /* 필터 색인은 bv-data 에서 */
    if (/bv_gender\.js/.test(u.pathname) && delayHead) await new Promise((z) => setTimeout(z, delayHead));
    if (tiny404 && /\/web\/product\/tiny\//.test(u.pathname)) {          /* 앞 상품 몇 개의 tiny 를 404 로 — 관리자 업로드분 흉내 */
      if (deny.size < tiny404 || deny.has(u.pathname)) { deny.add(u.pathname); return r.fulfill({ status: 404, body: "" }); }
    }
    if (req.resourceType() === "document" && /\/(category|product)\//.test(u.pathname) && !/detail/.test(u.pathname)) {
      const res = await cached(r); let body = res.body.toString("utf8");
      if (MODE === "v2") {
        if (body.indexOf(V1) < 0) throw new Error("라이브에서 v1 블록을 못 찾음: " + u.href + " — noflicker_v1_live.html 을 다시 떠야 한다");
        body = body.replace(V1, V2);
      }
      return r.fulfill({ status: res.status, body, headers: { ...res.headers, "content-type": "text/html; charset=utf-8" } });
    }
    if (["script", "stylesheet"].includes(req.resourceType()) && req.method() === "GET") return r.fulfill(await cached(r));
    return r.continue();
  });
  await ctx.addInitScript(INSTR);
  ctx.__deny = deny;
  return ctx;
}
async function settle(page, ms) { await page.waitForTimeout(ms); }
async function grab(page) { return page.evaluate(() => ({ log: window.__bvLog || [], cut: window.__bvCut || [], an: window.__bvAnim || {} })); }
async function shots(page, name, ms) {
  if (!SHOTS) return settle(page, ms);
  fs.mkdirSync(SHOTS, { recursive: true });
  let cdp, list = [];
  try {
    cdp = await page.context().newCDPSession(page);
    cdp.on("Page.screencastFrame", async (f) => { list.push(f); try { await cdp.send("Page.screencastFrameAck", { sessionId: f.sessionId }); } catch (e) {} });
    await cdp.send("Page.startScreencast", { format: "jpeg", quality: 70, maxWidth: 430, everyNthFrame: 1 });
  } catch (e) { console.log(`      (화면 녹화 생략: ${name})`); return settle(page, ms); }
  await settle(page, ms); try { await cdp.send("Page.stopScreencast"); } catch (e) {}
  const t0 = list.length ? list[0].metadata.timestamp : 0;
  list.forEach((f, k) => fs.writeFileSync(path.join(SHOTS, `${MODE}_${name}_${String(k).padStart(3, "0")}_${Math.round((f.metadata.timestamp - t0) * 1000)}ms.jpg`), Buffer.from(f.data, "base64")));
}
/* 받기 전/깨진 사진이 화면에 보인 프레임 수(목록이 보일 때만 센다) · 받는 순간 '툭'(첫 프레임부터 0.9 이상) 켜진 사진 수 */
function judge(log) {
  let unready = 0, broken = 0, pops = 0; const seen = {};
  log.forEach((r) => r.imgs.forEach((m, k) => {
    if (!m.inView) return;
    if (!m.ok && !m.err && m.op > 0.05) unready++;
    if (m.err && m.op > 0.05) broken++;
    if (m.ok && !seen[k]) { seen[k] = 1; if (m.self > 0.9 && m.op > 0.5) pops++; }
  }));
  return { unready, broken, pops };
}
async function stuck(page) {                                               /* 받았는데 투명하게 남은 사진(화면 안) */
  return page.evaluate((Q) => [...document.querySelectorAll(Q)].filter((m) => {
    const r = m.getBoundingClientRect(); if (!(r.top < innerHeight && r.bottom > 0)) return false;
    return m.complete && m.naturalWidth > 0 && +getComputedStyle(m).opacity < 0.99;
  }).length, Q);
}

const results = [];
function check(name, ok, detail) { results.push({ name, ok, detail }); console.log(`${ok ? "PASS" : "FAIL"}  ${name} — ${detail}`); }

(async () => {
  const browser = await chromium.launch({ proxy: { server: process.env.HTTPS_PROXY } });
  const M = devices["iPhone 15 Pro Max"], PC = { viewport: { width: 1440, height: 900 }, deviceScaleFactor: 1, userAgent: "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.0 Safari/605.1.15" };
  console.log(`# ${MODE} — ${new Date().toISOString()}`);

  { /* A — 실제 회선 속도와 무관하게: 슬라이드가 막 시작했을 때(80ms 지점) 페이지 시계를 1.8초 지점으로 당겨 v1 의 1.8초 타이머를 그 순간 터뜨린다.
         (머리 스크립트가 늦게 받아져 첫 그리기가 1.05초 넘게 늦은 상황과 같다. CSS 애니메이션은 페이지 시계와 무관하게 실시간으로 돈다.) */
    const ctx = await newCtx(browser, M), p = await ctx.newPage();
    await p.goto("https://m.bonovista.com/category/new/24/", { waitUntil: "load" });   /* 캐시 데우기 */
    await p.goto("https://m.bonovista.com/", { waitUntil: "domcontentloaded" });
    await p.evaluate(() => { sessionStorage.setItem("bvSlide", "1"); sessionStorage.setItem("bvFwd", "1"); });
    await p.clock.install();
    await p.goto("https://m.bonovista.com/category/new/24/", { waitUntil: "commit" });
    let st = null;
    for (let k = 0; k < 200; k++) {
      st = await p.evaluate(() => { const c = document.getElementById("contents"); const a = c && c.getAnimations ? c.getAnimations().find((x) => x.animationName === "bvSlideUp") : null;
        return { cur: a ? a.currentTime : null, now: performance.now(), at: window.__bvSlideAt }; }).catch(() => null);
      if (st && st.cur != null && st.cur >= 80) break; await new Promise((z) => setTimeout(z, 25));
    }
    if (!st || st.cur == null) check("A 슬라이드가 끝까지 감(첫 그리기 늦음)", false, "슬라이드가 시작되지 않음");
    else {
      const jump = Math.max(0, Math.ceil(st.at + 1830 - st.now));
      if (jump) await p.clock.fastForward(jump);
      await shots(p, "A", 2000);
      const { cut, an, log } = await grab(p), c = cut[0] || {};
      const before = [...log].reverse().find((r) => r.t < (c.t || 1e12) && r.slide) || {};
      /* 끊김 = 끝(animationend) 전에 취소되었거나, 클래스를 뗄 때 본문이 아직 제자리(0px)가 아니었다.
         (크롬은 끝난 뒤 클래스를 떼도 animationcancel 을 한 번 더 쏠 때가 있다 — 끝난 다음의 취소는 화면에 영향 없음) */
      const cancelledEarly = an.animationcancel != null && (an.animationend == null || an.animationcancel < an.animationend);
      const fine = !!cut.length && an.animationend != null && an.animationend <= c.t && !cancelledEarly && (before.top == null || Math.abs(before.top) <= 2);
      check("A 슬라이드가 끝까지 감(첫 그리기 늦음)", fine, `슬라이드 ${Math.round(st.cur)}ms 지점에서 시계 +${jump}ms → ` + (fine ? `끝(animationend)까지 감 · 뗄 때 본문 ${before.top == null ? "-" : before.top}px` : `중간에 끊김 · 뗄 때 본문이 ${before.top}px 아래에서 0px 로 한 번에 점프`) + ` [시작 ${an.animationstart} · 끝 ${an.animationend} · 취소 ${an.animationcancel} · 뗌 ${c.t} (페이지 시계 ms)]`);
    }
    await ctx.close();
  }
  { /* B */
    const ctx = await newCtx(browser, M), p = await ctx.newPage();
    await p.goto("https://m.bonovista.com/", { waitUntil: "domcontentloaded" });
    await p.evaluate(() => { sessionStorage.setItem("bvSlide", "1"); });
    await p.goto("https://m.bonovista.com/category/new/24/", { waitUntil: "commit" }); await shots(p, "B", 6000);
    const j = judge((await grab(p)).log), s = await stuck(p);
    const req = await p.evaluate(() => performance.getEntriesByType("resource").filter((e) => /\/web\/product\/(medium|tiny)\//.test(e.name)).slice(0, 6).map((e) => Math.round(e.startTime)));
    check("B 받는 중인 사진이 보이지 않음", j.unready === 0, `보인 프레임 ${j.unready} · 툭 켜짐 ${j.pops}장`);
    check("B 받은 사진이 숨은 채 남지 않음", s === 0, `숨은 채 남은 사진 ${s}장`);
    console.log(`      첫 화면 사진 요청 시작(ms): ${req.join(", ")}`);
    await ctx.close();
  }
  { /* C */
    const ctx = await newCtx(browser, { ...M, deviceScaleFactor: 1 }, { tiny404: 2 }), p = await ctx.newPage();
    await p.goto("https://m.bonovista.com/category/new/24/", { waitUntil: "commit" }); await shots(p, "C", 6000);
    const j = judge((await grab(p)).log), s = await stuck(p);
    check("C 깨진 사진(tiny 404)이 보이지 않음", j.broken === 0, `tiny 404 ${ctx.__deny.size}건 · 깨진 채 보인 프레임 ${j.broken}`);
    check("C onerror 대체 후 사진이 보임", s === 0, `숨은 채 남은 사진 ${s}장`);
    await ctx.close();
  }
  { /* D */
    const ctx = await newCtx(browser, M), p = await ctx.newPage();
    await p.goto("https://m.bonovista.com/category/new/24/", { waitUntil: "load" }); await settle(p, 1500);
    await p.evaluate(() => { const t = document.querySelector(".bv-ft-toggle"); if (t) t.click(); });
    await p.waitForSelector('.bv-ft-chip[data-f="a"][data-v="1"]', { timeout: 15000 }).catch(() => null);
    const n0 = await p.evaluate(() => document.querySelectorAll('.bv-ft-chip[data-f="a"][data-v="1"]').length);
    if (n0) {
      await p.evaluate(() => { window.__bvLog.length = 0; document.querySelector('.bv-ft-chip[data-f="a"][data-v="1"]').click(); });
      await shots(p, "D", 6000);
      const j = judge((await grab(p)).log), s = await stuck(p);
      const cards = await p.evaluate(() => document.querySelectorAll("li.bv-ft-card").length);
      check("D 필터 카드: 받는 중인 사진이 보이지 않음", cards > 0 && j.unready === 0, `카드 ${cards}장 · 받는 중 보인 프레임 ${j.unready}`);
      check("D 필터 카드: 사진이 숨은 채 남지 않음", cards > 0 && s === 0, `숨은 채 남은 사진 ${s}장`);
    } else check("D 필터 카드", false, "재고만 칩을 못 찾음");
    await ctx.close();
  }
  { /* E */
    const ctx = await newCtx(browser, PC), p = await ctx.newPage();
    await p.goto("https://www.bonovista.com/category/new/24/", { waitUntil: "commit" }); await shots(p, "E", 6000);
    const { log } = await grab(p), j = judge(log), s = await stuck(p);
    const h0 = (log.find((r) => r.imgs.length && !r.imgs[0].ok) || {}).imgs, h1 = log[log.length - 1].imgs;
    const hb = h0 ? h0[0].h : null, ha = h1 && h1[0] ? h1[0].h : null;
    check("E PC 받는 중인 사진이 보이지 않음", j.unready === 0, `보인 프레임 ${j.unready} · 툭 켜짐 ${j.pops}장`);
    check("E PC 받은 사진이 숨은 채 남지 않음", s === 0, `숨은 채 남은 사진 ${s}장`);
    check("E PC 받기 전후 사진 높이 같음", hb === ha, `받기 전 ${hb}px · 받은 뒤 ${ha}px`);
    const t2 = await p.evaluate(async () => { const b = document.querySelector("ul.prdList .thumbnail"); const m = b && b.querySelector("img.thumber_2"); return m ? getComputedStyle(m).opacity : "none"; });
    const box = p.locator("ul.prdList .thumbnail").first(); await box.hover(); await settle(p, 600);
    const t2h = await p.evaluate(() => { const m = document.querySelector("ul.prdList .thumbnail img.thumber_2"); return m ? getComputedStyle(m).opacity : "none"; });
    check("E PC 둘째 사진(thumber_2) 그대로", t2 === "0" && t2h === "1", `평소 ${t2} · 마우스 올림 ${t2h}`);
    await ctx.close();
  }
  { /* F */
    const ctx = await newCtx(browser, M), p = await ctx.newPage();
    await p.goto("https://m.bonovista.com/category/new/24/", { waitUntil: "load" }); await settle(p, 2500);
    const href = await p.evaluate(() => document.querySelector("ul.prdList .thumbnail a").getAttribute("href"));
    await p.goto(new URL(href, "https://m.bonovista.com/").href, { waitUntil: "domcontentloaded" }); await settle(p, 800);
    await p.goBack({ waitUntil: "domcontentloaded" }); await settle(p, 50);
    const first = await p.evaluate((Q) => [...document.querySelectorAll(Q)].slice(0, 4).map((m) => (m.complete && m.naturalWidth > 0 ? "받음" : "받는중") + "/" + (+getComputedStyle(m).opacity).toFixed(2)), Q);
    await settle(p, 2500); const s = await stuck(p);
    check("F 뒤로가기 후 사진이 숨은 채 남지 않음", s === 0, `돌아온 직후 앞 넷 ${first.join(" ")} · 숨은 채 남은 사진 ${s}장`);
    await ctx.close();
  }
  await browser.close();
  const bad = results.filter((r) => !r.ok).length;
  console.log(bad ? `\n# ${MODE}: 실패 ${bad} / ${results.length}` : `\n# ${MODE}: 모두 통과 ${results.length}`);
  process.exit(bad ? 1 : 0);
})().catch((e) => { console.error(e); process.exit(2); });
