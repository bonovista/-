# 주문 품목 재고 경과일 분석

카페24 Admin API(GET만)로 특정 주문자의 주문 품목을 받아, 주문일 기준 재고 경과일을 6개월 구간으로 나눠 엑셀 1개로 만든다.
`bonovista-brand-image` 번들의 `scripts/`(api.py · .env · token.json)를 그대로 쓴다. 자격증명·토큰 값은 출력하지 않는다.

## 1. 권한 — mall.read_order

```bash
python3 oauth_scope.py check          # 있으면 3번으로
python3 oauth_scope.py url            # 기존 scope + mall.read_order → scripts/authorize_url.txt
# 브라우저로 그 URL 열기 → 카페24 관리자 로그인 상태에서 「동의함」
python3 oauth_scope.py exchange "<리다이렉트 URL>"   # 60초 안에. 기존 token.json은 .bak-시각으로 백업
```

교환 후 주문 API를 한 번 찔러 확인한다. 토큰은 회전형이라 끝나면 프로젝트 문서 `claude_cafe24-token.md`를 갱신한다.

## 2. 분석

```bash
python3 order_inventory_age.py --email <주문자 이메일> --name <주문자명> \
  --start YYYY-MM-DD --end YYYY-MM-DD \
  --focus <주문번호>,<주문번호> \
  --out /mnt/user-data/outputs/주문_재고경과.xlsx
```

`--api-dir`를 안 주면 `$BBI_SCRIPTS` → `/home/claude/bbi/scripts` → `/mnt/skills/user/bonovista-brand-image/scripts` 순으로 찾는다.
주문자 정보는 인자로만 받는다. 저장소에 고객 정보를 남기지 않는다.

## 결과 엑셀

| 시트 | 내용 |
|---|---|
| 품목 목록 | 주문번호 · 품목주문번호 · 상품번호 · 상품명 · 판매가 · 주문일 · 현재 상태 · 분석 포함 · 등록일 · 경과일 · 경과 구간 · 미결제 대상 · 비고. 경과일 긴 순 |
| 구간별 분포 | 보유 품목의 구간별 품목 수 · 판매가 합계 · 품목/금액 비중, 막대 차트 2개 |
| 요약 | `--focus` 주문 품목만 같은 분포 + 대상 품목 목록 |

## 판정 기준

- **주문 조회**: `buyer_email` 파라미터로 받은 뒤, 응답의 주문자 이메일로 한 번 더 거른다. 이메일 정보가 없는 주문이 섞이면 멈춘다.
- **경과일** = 주문일 − 상품 `created_date`. 등록일은 상품 등록 시점이라 실제 입고·매입일과 다를 수 있다. 재등록·복사된 상품은 등록일이 주문일보다 늦을 수 있다(비고에 표시, 구간은 '확인필요').
- **구간**: 등록일→주문일 완료 개월 수(엑셀 `DATEDIF "m"`) 6 미만 / 6~12 / 12~18 / 18 이상.
- **분석 포함**
  - 보유: N00~N50, 클레임 거부·철회(C11 · R11 · E11 · E41 · E50 · E51)
  - 제외: 그 밖의 C·R 코드(취소·반품·환불), E40(교환완료 원품목)
  - 확인필요: C00 · R00 · E00(신청만 접수), 진행 중 교환 — 분포에서 빠지고 목록에만 남는다
- 분포 수식은 COUNTIFS/SUMIFS라 시트에서 판정을 고치면 다시 계산된다. 구간 라벨의 `~`는 와일드카드 이스케이프라 수식에서 `~~`로 바꿔 맞춘다.
