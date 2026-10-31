#!/usr/bin/env python3
"""주문 품목의 재고 경과일 분석 — 카페24 Admin API(GET만) → 엑셀 1개.

  경과일 = 주문일 − 상품 등록일(created_date)
  구간   = 완료 개월 수 기준 0~6 / 6~12 / 12~18 / 18개월 이상 (엑셀 DATEDIF "m")
  분석   = 고객이 실제 보유한 품목만. 취소·반품·환불·교환완료 원품목은 '제외'.

사용:
  python3 order_inventory_age.py --email <주문자 이메일> --name <주문자명> \\
      --start YYYY-MM-DD --end YYYY-MM-DD \\
      --focus <주문번호>,<주문번호> --out 결과.xlsx

GET만 호출한다. 자격증명·토큰 값은 출력하지 않는다(api.py가 처리).
"""
import argparse, glob, json, os, subprocess, sys
from datetime import datetime

from openpyxl import Workbook, load_workbook
from openpyxl.chart import BarChart, Reference
from openpyxl.chart.label import DataLabelList
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter

from oauth_scope import find_api_dir, load_api, NEED

BANDS = ["0~6개월", "6~12개월", "12~18개월", "18개월 이상"]
SIENNA = "A0522D"
FONT = "Arial"
RECALC_CANDIDATES = [
    os.environ.get("XLSX_RECALC", ""),
    "/mnt/skills/public/xlsx/scripts/recalc.py",
    *glob.glob("/root/.claude/skills/**/xlsx/scripts/recalc.py", recursive=True),
]

# 클레임 거부·철회 → 고객 보유. 신청만 들어간 상태 → 확인필요.
KEEP_CODES = {"C11", "R11", "E11", "E41", "E50", "E51"}
PENDING_CODES = {"C00", "R00", "E00"}


def judge(code):
    c = (code or "").upper()
    if not c:
        return "확인필요"
    if c in KEEP_CODES:
        return "보유"
    if c in PENDING_CODES:
        return "확인필요"
    if c[0] in "CR" or c == "E40":
        return "제외"
    if c[0] == "E":
        return "확인필요"
    return "보유"


def kst(s):
    """'2026-10-22T13:45:12+09:00' → naive KST datetime"""
    if not s:
        return None
    return datetime.fromisoformat(s.replace("Z", "+00:00")).replace(tzinfo=None)


def money(v):
    try:
        return int(round(float(v or 0)))
    except ValueError:
        return 0


# ── API ──────────────────────────────────────────────────────────────────────

def fetch_orders(api, a):
    out, offset = [], 0
    while True:
        p = {"shop_no": 1, "start_date": a.start, "end_date": a.end, "date_type": "order_date",
             "buyer_email": a.email, "embed": "items,buyer", "limit": 100, "offset": offset}
        rows = api.call("GET", "/admin/orders", p).get("orders", [])
        out += rows
        if len(rows) < 100:
            return out
        offset += 100


def order_emails(o):
    b = o.get("buyer") or {}
    return {e.strip().casefold() for e in (b.get("email"), o.get("member_email"), o.get("buyer_email"))
            if isinstance(e, str) and e.strip()}


def order_name(o):
    return (o.get("buyer") or {}).get("name") or o.get("billing_name") or ""


def fetch_products(api, nos):
    found = {}
    nos = sorted(set(nos))
    for i in range(0, len(nos), 100):
        chunk = ",".join(str(n) for n in nos[i:i + 100])
        p = {"shop_no": 1, "product_no": chunk, "fields": "product_no,product_name,created_date", "limit": 100}
        for pr in api.call("GET", "/admin/products", p).get("products", []):
            found[int(pr["product_no"])] = pr
    return found


# ── 엑셀 ─────────────────────────────────────────────────────────────────────

HEAD_FILL = PatternFill("solid", fgColor=SIENNA)
HEAD_FONT = Font(name=FONT, bold=True, color="FFFFFF")
BODY_FONT = Font(name=FONT)
GREY_FONT = Font(name=FONT, color="9A9A9A")
BOLD = Font(name=FONT, bold=True)
TITLE = Font(name=FONT, bold=True, size=13)
NOTE = Font(name=FONT, size=9, color="666666")
THIN = Border(bottom=Side(style="thin", color="D9D9D9"))

COLS = [  # (헤더, 폭)
    ("주문번호", 19), ("품목주문번호", 22), ("상품번호", 10), ("상품명", 52), ("판매가(원)", 12),
    ("주문일", 17), ("현재 상태", 16), ("분석 포함", 10), ("등록일", 12), ("경과일", 9),
    ("경과 구간", 12), ("미결제 대상", 11), ("비고", 34),
]
C = {h: get_column_letter(i + 1) for i, (h, _) in enumerate(COLS)}
LIST = "'품목 목록'"


def band_formula(r):
    j, g, k = f"{C['등록일']}{r}", f"{C['주문일']}{r}", f"{C['경과일']}{r}"
    m = f"DATEDIF(INT({j}),INT({g}),\"m\")"
    return (f'=IF({j}="","미확인",IF({k}<0,"확인필요",IF({m}<6,"{BANDS[0]}",'
            f'IF({m}<12,"{BANDS[1]}",IF({m}<18,"{BANDS[2]}","{BANDS[3]}")))))')


def header(ws, row, names):
    for i, h in enumerate(names, 1):
        c = ws.cell(row=row, column=i, value=h)
        c.fill, c.font = HEAD_FILL, HEAD_FONT
        c.alignment = Alignment(horizontal="center", vertical="center")


def write_list(ws, rows):
    header(ws, 1, [h for h, _ in COLS])
    for i, (_, w) in enumerate(COLS, 1):
        ws.column_dimensions[get_column_letter(i)].width = w
    for r, it in enumerate(rows, 2):
        vals = {"주문번호": it["order_id"], "품목주문번호": it["item_code"], "상품번호": it["product_no"],
                "상품명": it["product_name"], "판매가(원)": it["price"], "주문일": it["order_dt"],
                "현재 상태": it["status"], "분석 포함": it["judge"], "등록일": it["created_dt"],
                "경과일": f'=IF({C["등록일"]}{r}="","",INT({C["주문일"]}{r})-INT({C["등록일"]}{r}))',
                "경과 구간": band_formula(r), "미결제 대상": "Y" if it["focus"] else "",
                "비고": it["note"]}
        for ci, (h, _) in enumerate(COLS, 1):
            c = ws.cell(row=r, column=ci, value=vals[h])
            c.font = GREY_FONT if it["judge"] == "제외" else BODY_FONT
            c.border = THIN
        ws[f"{C['판매가(원)']}{r}"].number_format = "#,##0"
        ws[f"{C['주문일']}{r}"].number_format = "yyyy-mm-dd hh:mm"
        ws[f"{C['등록일']}{r}"].number_format = "yyyy-mm-dd"
        ws[f"{C['경과일']}{r}"].number_format = "#,##0"
    ws.freeze_panes = "A2"
    ws.auto_filter.ref = f"A1:{get_column_letter(len(COLS))}{max(len(rows) + 1, 2)}"


def write_distribution(ws, title, extra, notes, chart_title):
    """extra: COUNTIFS/SUMIFS에 더할 조건 문자열 (예: ',\'품목 목록\'!$L:$L,"Y"')"""
    ws["A1"], ws["A1"].font = title, TITLE
    header(ws, 3, ["구간", "품목 수", "판매가 합계(원)", "품목 비중(%)", "금액 비중(%)"])
    band_col, inc_col, price_col = (f"{LIST}!${C[h]}:${C[h]}" for h in ("경과 구간", "분석 포함", "판매가(원)"))
    for i, b in enumerate(BANDS):
        r = 4 + i
        # '~'는 COUNTIFS 와일드카드 이스케이프 — "0~6개월"을 글자 그대로 맞추려면 "~~"로
        cond = f'{band_col},SUBSTITUTE($A{r},"~","~~"),{inc_col},"보유"{extra}'
        ws[f"A{r}"] = b
        ws[f"B{r}"] = f"=COUNTIFS({cond})"
        ws[f"C{r}"] = f"=SUMIFS({price_col},{cond})"
        ws[f"D{r}"] = f"=IFERROR(B{r}/$B$8,0)"
        ws[f"E{r}"] = f"=IFERROR(C{r}/$C$8,0)"
    ws["A8"] = "합계"
    for col in "BCDE":
        ws[f"{col}8"] = f"=SUM({col}4:{col}7)"
    ws["A9"] = "보유 중 구간 미확인(분포 제외)"
    ws["B9"] = f'=COUNTIFS({inc_col},"보유"{extra})-B8'
    for r in range(4, 10):
        for col in "ABCDE":
            c = ws[f"{col}{r}"]
            c.font = BOLD if r == 8 else (NOTE if r == 9 else BODY_FONT)
            c.border = THIN
        ws[f"B{r}"].number_format = "#,##0"
        ws[f"C{r}"].number_format = "#,##0"
        ws[f"D{r}"].number_format = "0.0%"
        ws[f"E{r}"].number_format = "0.0%"
    for col, w in zip("ABCDE", (30, 10, 16, 13, 13)):
        ws.column_dimensions[col].width = w

    for anchor, col, name in (("G3", 2, "품목 수"), ("G20", 3, "판매가 합계(원)")):
        ch = BarChart()
        ch.type, ch.style = "col", 10
        ch.title = f"{chart_title} — {name}"
        ch.y_axis.title, ch.x_axis.title = name, "재고 경과 구간"
        ch.add_data(Reference(ws, min_col=col, min_row=3, max_row=7), titles_from_data=True)
        ch.set_categories(Reference(ws, min_col=1, min_row=4, max_row=7))
        ch.legend = None
        ch.series[0].graphicalProperties.solidFill = SIENNA
        ch.series[0].graphicalProperties.line.solidFill = SIENNA
        ch.dataLabels = DataLabelList(showVal=True, showCatName=False, showSerName=False,
                                      showLegendKey=False, showPercent=False)
        ch.dataLabels.numFmt = "#,##0"
        ch.y_axis.majorGridlines = None
        ch.y_axis.delete = False
        ch.x_axis.delete = False
        ch.height, ch.width = 7.5, 15
        ws.add_chart(ch, anchor)

    r = 12
    ws[f"A{r}"], ws[f"A{r}"].font = "기준", BOLD
    for i, n in enumerate(notes, 1):
        ws[f"A{r + i}"] = n
        ws[f"A{r + i}"].font = NOTE
    return r + len(notes) + 2


def recalc(path):
    for p in RECALC_CANDIDATES:
        if p and os.path.isfile(p):
            r = subprocess.run([sys.executable, p, path, "60"], capture_output=True, text=True)
            try:
                return json.loads(r.stdout)
            except Exception:
                return {"error": (r.stdout + r.stderr)[-300:]}
    return {"error": "recalc.py 없음 — 엑셀에서 열면 계산됨"}


# ── 본체 ─────────────────────────────────────────────────────────────────────

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--email", required=True)
    ap.add_argument("--name", default="")
    ap.add_argument("--start", required=True)
    ap.add_argument("--end", required=True)
    ap.add_argument("--focus", default="", help="미결제 대상 주문번호, 쉼표 구분")
    ap.add_argument("--out", required=True)
    ap.add_argument("--api-dir")
    a = ap.parse_args()
    api = load_api(find_api_dir(a.api_dir))
    focus = [s.strip() for s in a.focus.split(",") if s.strip()]
    target = a.email.strip().casefold()
    warn = []

    tok = json.load(open(api.TOKEN_FILE)) if os.path.isfile(api.TOKEN_FILE) else {}
    if tok.get("scopes") is not None and NEED not in tok["scopes"]:
        raise SystemExit(f"[중단] 토큰 scope에 {NEED} 없음 — python3 oauth_scope.py url 부터")

    # 1) 주문 — buyer_email 파라미터 + 응답의 이메일로 이중 확인
    raw = fetch_orders(api, a)
    orders = []
    for o in raw:
        em = order_emails(o)
        if not em:
            raise SystemExit(f"[중단] 주문 {o.get('order_id')}에 주문자 이메일 정보가 없어 본인 확인 불가")
        if target in em:
            orders.append(o)
    print(f"주문: 조회 {len(raw)}건 → 이메일 일치 {len(orders)}건 ({a.start} ~ {a.end}, 주문일 기준)")
    for o in orders:
        if a.name and order_name(o) != a.name:
            warn.append(f"주문 {o['order_id']}: 주문자명 '{order_name(o)}' ≠ '{a.name}'")
        if o.get("member_id"):
            warn.append(f"주문 {o['order_id']}: 회원 주문(member_id 있음) — 비회원 전제와 다름")
    got = {o["order_id"] for o in orders}
    for fid in focus:
        if fid in got:
            continue
        try:
            fo = api.call("GET", f"/admin/orders/{fid}", {"shop_no": 1, "embed": "items,buyer"}).get("order", {})
            same = target in order_emails(fo)
            warn.append(f"미결제 대상 {fid}: 조회 결과에 없음 — 주문일 {fo.get('order_date', '?')[:10]}, "
                        f"이메일 {'일치' if same else '불일치'} (분석에 넣지 않음)")
        except RuntimeError as e:
            warn.append(f"미결제 대상 {fid}: 단건 조회 실패 — {str(e)[:120]}")

    # 2) 품목
    items = []
    for o in orders:
        odt = kst(o.get("order_date"))
        paid = o.get("paid")
        for it in o.get("items") or []:
            code = it.get("order_status") or ""
            qty = int(it.get("quantity") or 1)
            note = []
            if qty > 1:
                note.append(f"수량 {qty} — 판매가는 단가×수량")
            if paid == "F":
                note.append("주문 미결제")
            items.append({
                "order_id": o["order_id"], "item_code": it.get("order_item_code", ""),
                "product_no": int(it.get("product_no") or 0), "product_name": it.get("product_name", ""),
                "price": (money(it.get("product_price")) + money(it.get("option_price"))) * qty,
                "order_dt": odt, "status": f"{it.get('status_text', '')} ({code})".strip(),
                "judge": judge(code), "focus": o["order_id"] in focus, "note": note, "created_dt": None,
            })

    # 3) 등록일
    prods = fetch_products(api, [i["product_no"] for i in items if i["product_no"]])
    for i in items:
        pr = prods.get(i["product_no"])
        if not pr:
            i["note"].append("상품 조회 안 됨(삭제 가능성) — 등록일 미확인")
            continue
        i["created_dt"] = kst(pr.get("created_date"))
        if i["created_dt"] and i["order_dt"] and i["created_dt"].date() > i["order_dt"].date():
            i["note"].append("등록일이 주문일보다 늦음 — 재등록·복사 가능성")
    for i in items:
        i["days"] = (i["order_dt"].date() - i["created_dt"].date()).days if i["created_dt"] and i["order_dt"] else None
        i["note"] = " / ".join(i["note"])
    items.sort(key=lambda i: (i["days"] is None, -(i["days"] or 0)))  # 경과일 긴 순, 미확인은 맨 뒤

    # 4) 엑셀
    wb = Workbook()
    ws1 = wb.active
    ws1.title = "품목 목록"
    write_list(ws1, items)
    period = f"{a.start} ~ {a.end} (주문일 기준)"
    common = [
        f"기간: {period} · 주문자 이메일 일치 주문 {len(orders)}건 · 조회 {datetime.now():%Y-%m-%d %H:%M} (카페24 Admin API)",
        "경과일 = 주문일 − 상품 등록일(카페24 created_date). 등록일은 상품 등록 시점이라 실제 입고·매입일과 다를 수 있음",
        "구간 = 등록일→주문일 완료 개월 수(DATEDIF \"m\"): 6개월 미만 / 6~12 / 12~18 / 18개월 이상",
        "분석 포함 = '보유'만. 취소·반품·환불·교환완료 원품목 = '제외', 클레임 신청만 들어간 품목 = '확인필요'(분포 제외)",
    ]
    ws2 = wb.create_sheet("구간별 분포")
    write_distribution(ws2, "구간별 분포 — 고객 보유 품목", "", common, "전체")
    ws3 = wb.create_sheet("요약")
    extra = f',{LIST}!${C["미결제 대상"]}:${C["미결제 대상"]},"Y"'
    r = write_distribution(ws3, f"미결제 대상 주문 — {', '.join(focus)}", extra,
                           common + ["대상 = 품목 목록의 '미결제 대상' = Y"], "미결제 대상")
    ws3[f"A{r}"], ws3[f"A{r}"].font = "대상 품목", BOLD
    sub = [i for i in items if i["focus"]]
    names = ["주문번호", "품목주문번호", "상품번호", "상품명", "판매가(원)", "현재 상태", "분석 포함", "경과일"]
    for ci, h in enumerate(names, 1):
        c = ws3.cell(row=r + 1, column=ci, value=h)
        c.fill, c.font = HEAD_FILL, HEAD_FONT
    for k, i in enumerate(sub, r + 2):
        for ci, v in enumerate([i["order_id"], i["item_code"], i["product_no"], i["product_name"],
                                i["price"], i["status"], i["judge"], i["days"]], 1):
            c = ws3.cell(row=k, column=ci, value=v)
            c.font = GREY_FONT if i["judge"] == "제외" else BODY_FONT
        ws3.cell(row=k, column=5).number_format = "#,##0"
    wb.calculation.fullCalcOnLoad = True
    os.makedirs(os.path.dirname(os.path.abspath(a.out)), exist_ok=True)
    wb.save(a.out)

    # 5) 재계산 + 보고 (엑셀 수식 결과를 그대로 읽어 보고 — 숫자 출처를 하나로)
    rc = recalc(a.out)
    if rc.get("error") or rc.get("status") != "success":
        warn.append(f"재계산: {rc.get('error') or rc}")
    cnt = {k: sum(1 for i in items if i["judge"] == k) for k in ("보유", "제외", "확인필요")}
    print(f"품목: {len(items)}개 — 보유 {cnt['보유']} · 제외 {cnt['제외']} · 확인필요 {cnt['확인필요']}")
    if rc.get("status") == "success":
        vb = load_workbook(a.out, data_only=True)
        for sh in ("구간별 분포", "요약"):
            w = vb[sh]
            print(f"\n[{sh}]")
            for r in range(4, 10):
                b, c, d = w[f"B{r}"].value, w[f"C{r}"].value, w[f"D{r}"].value
                if b is None:
                    continue
                print(f"  {w[f'A{r}'].value:<22} {b:>3}개  {int(c or 0):>10,}원  {(d or 0) * 100:5.1f}%"
                      if r < 9 else f"  {w[f'A{r}'].value} {b}개")
    for w in warn:
        print("주의:", w)
    print("\n저장:", a.out)


if __name__ == "__main__":
    main()
