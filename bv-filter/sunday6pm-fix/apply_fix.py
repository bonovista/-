#!/usr/bin/env python3
"""필터 카드 가격 줄 "sunday 6pm" 오류 수정 — filter_ui.dev.js 에 적용한다.

원인: card() 는 이 화면의 서버 li 하나를 틀로 복제한 뒤 보이는 첫 "N won" 글자만 바꾼다.
틀은 '첫 재고 li' 인데, 공개 전 상품(판매가 대체문구 "sunday 6pm")이 목록 맨 앞에 있으면
그 li 가 틀이 되고 "N won" 이 없으니 가격이 안 바뀌어 모든 카드가 "sunday 6pm" 이 된다.

수정:
  1) 가격 자리(priceSlot)를 "N won" 또는 대체문구(요일+시각) 둘 다로 잡는다.
  2) 틀은 숫자 가격이 보이는 재고 li 를 먼저 고른다.
  3) 카드의 가격 줄은 그 상품 것으로 쓴다 — 이 화면의 서버 li 가 있으면 그 글자,
     없으면 NEW 목록 앞쪽에서 읽은 공개 전 번호(dropScan)에 있을 때만 대체문구, 나머지는 가격.

사용: cd ~/bonovista_pipeline/gender && python3 /경로/apply_fix.py filter_ui.dev.js
기준본: 2026-10-08 v3.16 (filter_ui.js 696~760행). 기준 문자열이 없으면 멈춘다.
"""
import sys

p = sys.argv[1] if len(sys.argv) > 1 else "filter_ui.dev.js"
s = open(p, encoding="utf-8").read()

if "function priceSlot(li)" in s:
    sys.exit("이미 적용됨: " + p)

edits = []

# 1) 틀: 숫자 가격이 보이는 재고 li 먼저
edits.append((
    """    for(i = 0; i < all.length; i++){ var im = all[i].querySelector('img[alt="품절"]'); if(im && !ICON) ICON = im.outerHTML; if(!im && !src) src = all[i]; }
    src = src || all[0]; if(!src) return null;
""",
    """    var num = null;                                                          /* 틀은 숫자 가격이 보이는 재고 li 먼저 — 대체문구 li 가 틀이면 가격 줄이 그 문구로 남는다 */
    for(i = 0; i < all.length; i++){ var im = all[i].querySelector('img[alt="품절"]'); if(im && !ICON) ICON = im.outerHTML; if(!im && !src) src = all[i]; if(!im && !num){ var ps = priceSlot(all[i]); if(ps && !ps.drop) num = all[i]; } }
    src = num || src || all[0]; if(!src) return null;
"""))

# 2) 가격 자리·대체문구 판정 함수 (card 바로 앞)
edits.append((
    """  function card(i, row){
""",
    """  /* ── 가격 자리 ──
     보이는 첫 "N won"(숨김 .displaynone·취소선 strike 안의 "0 won" 은 건너뜀). 없으면 판매가 대체문구 — 공개 전 상품은 가격 대신 "sunday 6pm" 이 찍힌다.
     예전엔 "N won" 만 찾아서, 틀(이 화면의 첫 재고 li)이 공개 전 상품이면 가격이 안 바뀌고 모든 카드가 "sunday 6pm" 이 됐다(2026-10-18 태진 신고 · NEW 재고만).
     대체문구 모양(요일+시각)은 아래 DROP_RE 한 곳에서 고친다. */
  function priceSlot(li){
    var NUM_RE = /^\\s*[\\d,]+\\s*won\\s*$/, DROP_RE = /^\\s*(?:mon|tue|wed|thu|fri|sat|sun)[a-z]*\\.?\\s+\\d{1,2}(?::\\d{2})?\\s*[ap]\\.?m\\.?\\s*$/i;
    var w = (li.ownerDocument || document).createTreeWalker(li, NodeFilter.SHOW_TEXT, null, false), tn, drop = null;
    while((tn = w.nextNode())){
      var num = NUM_RE.test(tn.nodeValue); if(!num && (drop || !DROP_RE.test(tn.nodeValue))) continue;
      var pe = tn.parentNode, hid = false;
      while(pe && pe !== li){ if(pe.tagName === "STRIKE" || pe.tagName === "DEL" || (pe.classList && pe.classList.contains("displaynone"))){ hid = true; break; } pe = pe.parentNode; }
      if(hid) continue;
      if(num) return { n:tn, drop:false };
      drop = { n:tn, drop:true };
    }
    return drop;
  }
  /* 대체문구는 그 상품이 지금 공개 전일 때만 쓴다. 이 화면의 서버 li 가 있으면 그것이 정답(카페24가 방금 찍은 값),
     없으면 NEW 목록 앞쪽에서 읽은 공개 전 번호(dropScan). 읽기 전엔 비워 둔다 — 공개 전 가격이 잠깐이라도 보이지 않게. */
  function priceText(li){
    var pno = li.__bvPno, all = F.stash.concat(GT.lis(ul)), k, s;
    for(k = 0; k < all.length; k++){
      if(all[k].__bvFt || pnoOf(all[k]) !== pno) continue;
      s = priceSlot(all[k]); if(s) return s.drop ? s.n.nodeValue : li.__bvWon;
    }
    dropScan();
    if(DROP.ready) return DROP.ids[pno] || li.__bvWon;
    PEND.push(li); return "";
  }
  /* NEW 목록을 1쪽부터 읽어 공개 전 상품 번호와 문구를 모은다. 본 목록 끝 li 까지 공개 전이면 다음 쪽(최대 5쪽).
     10분 구간마다 한 번 — 같은 구간 안에서는 sessionStorage 의 결과를 쓴다. 읽기에 실패하면 가격으로 채우고 저장하지 않는다. */
  var DROP, PEND;                                                           /* 초기값 없이 — 이 줄보다 먼저 카드가 그려져도 진행 중인 읽기를 지우지 않게 */
  function dropScan(){
    if(DROP) return;
    var slot = Math.floor(Date.now() / 600000), page = 0, ok = true;
    var base = typeof newPath === "function" ? newPath() : "/product/list.html?cate_no=24";
    try { var c = JSON.parse(sessionStorage.getItem("bvDrop") || "null"); if(c && c.s === slot && c.ids){ DROP = { ready:1, ids:c.ids }; return; } } catch(e){}
    DROP = { ready:0, ids:{} }; PEND = [];
    function read(){
      page++;
      return fetch(base + (base.indexOf("?") < 0 ? "?" : "&") + "page=" + page, { credentials:"same-origin" }).then(function(r){
        if(!r.ok) throw new Error("drop " + r.status); return r.text();
      }).then(function(html){
        var doc = new DOMParser().parseFromString(html, "text/html"), main = null;
        [].forEach.call(doc.querySelectorAll("ul.prdList"), function(u){
          if(!main || u.children.length > main.children.length) main = u;
          [].forEach.call(u.children, function(li){ var s = priceSlot(li); if(s && s.drop) DROP.ids[pnoOf(li)] = s.n.nodeValue.trim(); });
        });
        var last = main && main.lastElementChild ? priceSlot(main.lastElementChild) : null;
        if(last && last.drop && page < 5) return read();
      });
    }
    read().catch(function(){ ok = false; }).then(function(){
      DROP.ready = 1;
      if(ok) try { sessionStorage.setItem("bvDrop", JSON.stringify({ s:slot, ids:DROP.ids })); } catch(e){}
      PEND.splice(0).forEach(function(li){ li.__bvSlot.nodeValue = DROP.ids[li.__bvPno] || li.__bvWon; });
    });
  }
  function card(i, row){
"""))

# 3) 카드 가격 줄: 틀의 가격 자리에 그 상품 것을 쓴다
edits.append((
    """    var price = (row[4] && row[4] < row[1]) ? row[4] : row[1];
    /* 가격 텍스트 노드: 숨김(.displaynone)·취소선(strike) 안의 "0 won" 은 건너뛰고 보이는 첫 값만 바꾼다 */
    var w = document.createTreeWalker(li, NodeFilter.SHOW_TEXT, null, false), tn;
    while((tn = w.nextNode())){
      if(!/^\\s*[\\d,]+\\s*won\\s*$/.test(tn.nodeValue)) continue;
      var pe = tn.parentNode, hid = false;
      while(pe && pe !== li){ if(pe.tagName === "STRIKE" || pe.tagName === "DEL" || (pe.classList && pe.classList.contains("displaynone"))){ hid = true; break; } pe = pe.parentNode; }
      if(hid) continue;
      tn.nodeValue = fmt(price) + " won"; break;
    }
""",
    """    var price = (row[4] && row[4] < row[1]) ? row[4] : row[1];
    /* 가격 자리는 틀이 공개 전 상품이어도 잡힌다(priceSlot). 품절은 늘 가격, 나머지는 priceText 가 그 상품 것으로 정한다 */
    var ps = priceSlot(li);
    if(ps){ li.__bvSlot = ps.n; li.__bvPno = pno; li.__bvWon = fmt(price) + " won"; ps.n.nodeValue = X.so[i] ? li.__bvWon : priceText(li); }
"""))

for old, new in edits:
    n = s.count(old)
    if n != 1:
        sys.exit("기준 문자열 %d곳 (1곳이어야 함) — 기준본과 달라졌다:\n%s" % (n, old[:160]))
    s = s.replace(old, new)

open(p, "w", encoding="utf-8").write(s)
print("적용:", p)
