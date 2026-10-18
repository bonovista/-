/* card() 가격 줄 회귀 테스트 — jsdom 으로 카드 섹션만 떼어 돌린다.
   사용: node test_card_price.js <카드 섹션.js> [--expect-bug]
   카드 섹션 = filter_ui.js 의 "카드: 이 화면의 서버 li 를 틀로" 부터 function applyDims 앞까지.
   서버 li 마크업은 카페24 목록 형태를 흉내 낸 합성본이다(실제 스킨 마크업은 하네스의 live_*.html 로 따로 확인). */
const fs = require("fs");
const { JSDOM } = require("jsdom");

const src = fs.readFileSync(process.argv[2], "utf8");
const section = src.slice(0, src.indexOf("  function applyDims(){"));
const expectBug = process.argv.includes("--expect-bug");

function li(pno, priceText, { sold = false, code = "P000" + pno } = {}) {
  const href = `/product/detail.html?product_no=${pno}&cate_no=24&display_group=1`;
  return `<li id="anchorBoxId_${pno}" class="xans-record-">
  <div class="thumbnail"><div class="prdImg"><a href="${href}"><img src="/web/product/medium/${pno}.jpg" alt=""></a></div></div>
  <div class="description">
    <strong class="name"><a href="${href}"><span class="title displaynone">상품명</span> <span>BRAND ${pno}</span></a></strong>
    <ul class="spec">
      <li><strong class="title displaynone">소비자가</strong> <span><strike>0 won</strike></span></li>
      <li class="price"><strong class="title displaynone">판매가</strong> <span>${priceText}</span></li>
      <li class="displaynone"><span>0 won</span></li>
    </ul>
    <div class="icon"><div class="promotion">${sold ? '<img src="/web/upload/sold.png" class="icon_img" alt="품절">' : ""}</div></div>
    <ul class="act"><li class="cart"><img src="/cart.png" onclick="category_add_basket('${pno}','24','1','A0000',false,'1','${code}','A','F','0');"></li></ul>
  </div>
</li>`;
}
const page = (lis) => `<!doctype html><html><body><ul class="prdList">${lis.join("")}</ul></body></html>`;

/* 렌더할 상품 (색인 순서) — pno · 행[이름, 가격, 사진, 코드, 할인가] · 품절 · 기대 가격 줄 */
const PRODUCTS = [
  { pno: 86500, row: ["MARNI", 120000, "/web/product/medium/86500.jpg", "P00086500", 0], so: 0, want: "sunday 6pm" }, // 이 화면에 있는 공개 전 상품
  { pno: 86010, row: ["COACH", 128000, "/web/product/medium/86010.jpg", "P00086010", 0], so: 0, want: "128,000 won" }, // 이 화면에 있는 공개 상품
  { pno: 85000, row: ["ACNE STUDIOS", 99000, "/web/product/medium/85000.jpg", "P00085000", 0], so: 0, want: "99,000 won" }, // 화면 밖 공개 상품
  { pno: 86498, row: ["JIMI CHOO", 150000, "/web/product/medium/86498.jpg", "P00086498", 0], so: 0, want: "sunday 6pm" }, // 화면 밖 공개 전(NEW 2쪽)
  { pno: 84000, row: ["MARY QUANT", 80000, "/web/product/medium/84000.jpg", "P00084000", 70000], so: 1, want: "70,000 won" }, // 화면 밖 품절
];

/* NEW 목록: 1쪽은 전부 공개 전 → 2쪽까지 읽어야 86498 이 잡힌다 */
const NEW_PAGES = {
  1: page([li(86500, "sunday 6pm"), li(86499, "sunday 6pm")]),
  2: page([li(86498, "sunday 6pm"), li(86100, "110,000 won")]),
};

async function run(name, serverLis, { failFetch = false, storage = null } = {}) {
  const dom = new JSDOM(page(serverLis), { url: "https://bonovista.com/product/list.html?cate_no=24", runScripts: "outside-only" });
  const w = dom.window;
  if (storage) w.sessionStorage.setItem("bvDrop", storage);
  const fetched = [];
  w.fetch = (url) => {
    fetched.push(url);
    const m = String(url).match(/page=(\d+)/), body = NEW_PAGES[m ? +m[1] : 1];
    if (failFetch) return Promise.reject(new Error("offline"));
    return Promise.resolve({ ok: !!body, status: body ? 200 : 404, text: () => Promise.resolve(body || "") });
  };
  const IDX = { id: PRODUCTS.map((p) => p.pno), key: PRODUCTS.map(() => 0), disp: PRODUCTS.map(() => 0), so: PRODUCTS.map((p) => p.so) };
  w.__IDX = IDX;
  w.eval(`(function(){
    var F = { stash: [] }, GT = { lis: function(u){ return [].slice.call(u.children); } }, ul = document.querySelector("ul.prdList");
    var TPL = null, ICON = null, MO_ = false, IDX = window.__IDX;
    function fmt(n){ return String(n).replace(/\\B(?=(\\d{3})+(?!\\d))/g, ","); }
    function esc(s){ return String(s).replace(/[&<>"]/g, function(c){ return "&#" + c.charCodeAt(0) + ";"; }); }
    function urlCate(){ return 24; }
    function newPath(){ return "/category/new/24/"; }
    ${section}
    window.__card = card;
  })();`);
  const out = w.document.createElement("ul");
  const cards = PRODUCTS.map((p, i) => { const c = w.__card(i, p.row); out.appendChild(c); return c; });
  const priceOf = (c) => c.querySelector("ul.spec li.price span").textContent;
  const before = cards.map(priceOf);
  await new Promise((r) => setTimeout(r, 30));
  const after = cards.map(priceOf);
  return { name, before, after, fetched, stored: w.sessionStorage.getItem("bvDrop") };
}

let fail = 0;
function check(label, got, want) {
  const ok = got === want;
  if (!ok) fail++;
  console.log(`${ok ? "PASS" : "FAIL"}  ${label}: ${JSON.stringify(got)}${ok ? "" : "  (기대 " + JSON.stringify(want) + ")"}`);
}

(async () => {
  /* 이 화면 서버 li: 공개 전 2개가 맨 앞(= 예전 틀), 그 뒤 공개 1개·품절 1개 */
  const SERVER = [li(86500, "sunday 6pm"), li(86499, "sunday 6pm"), li(86010, "128,000 won"), li(86005, "50,000 won", { sold: true })];
  const SERVER_ALL_DROP = [li(86500, "sunday 6pm"), li(86499, "sunday 6pm")];

  if (expectBug) {
    const r = await run("기존 코드", SERVER);
    console.log("# 기존 코드 — 신고 재현");
    PRODUCTS.forEach((p, i) => check(`${p.pno} (${p.want === "sunday 6pm" ? "공개 전" : "무관"})`, r.after[i], "sunday 6pm"));
    console.log(fail ? `재현 실패 ${fail}` : "재현됨: 무관한 상품까지 전부 sunday 6pm");
    process.exit(fail ? 1 : 0);
  }

  const a = await run("공개 상품이 섞인 화면", SERVER);
  console.log("# 1) 서버 li 에 공개 전·공개 상품이 섞인 화면 (NEW 2쪽까지 읽음)");
  PRODUCTS.forEach((p, i) => check(`${p.pno}`, a.after[i], p.want));
  check("읽기 전 화면 밖 재고 카드는 빈칸(가격 미노출)", [a.before[2], a.before[3]].join("|"), "|");
  check("읽은 NEW 쪽 수", a.fetched.length, 2);

  const b = await run("전부 공개 전인 화면", SERVER_ALL_DROP);
  console.log("# 2) 서버 li 가 전부 공개 전(숫자 틀 없음)");
  PRODUCTS.forEach((p, i) => check(`${p.pno}`, b.after[i], p.want));

  const c = await run("같은 10분 구간 재방문", SERVER, { storage: a.stored });
  console.log("# 3) 같은 10분 구간 재방문 — 저장본 사용");
  PRODUCTS.forEach((p, i) => check(`${p.pno} 즉시`, c.before[i], p.want));
  check("다시 읽은 쪽 수", c.fetched.length, 0);

  const d = await run("NEW 읽기 실패", SERVER, { failFetch: true });
  console.log("# 4) NEW 읽기 실패 — 화면 밖은 가격으로, 저장 안 함");
  check("85000", d.after[2], "99,000 won");
  check("86500 (화면 안 공개 전은 그대로)", d.after[0], "sunday 6pm");
  check("저장본", d.stored, null);

  console.log(fail ? `\n실패 ${fail}` : "\n모두 통과");
  process.exit(fail ? 1 : 0);
})();
