# 비용 장부 안내 · '돈을 썼을 때' 시연

온라인 비용 장부 사용 안내(cost.bonovista.com 직원용)의 '돈을 썼을 때' 그림을 Stageshow로 다시 만든 시연입니다. 원래 있던 앱 캡처 두 장(금액부터 용도까지, 결제부터 사진까지)을 대신합니다.

- 시안 페이지: 비공개 아티팩트 '비용 장부 안내 시안'
- 정지 화면(포스터): `poster.png`

## 장면

폰 한 대, 위에서 고정, 아래는 화면 끝에서 잘림. 한 번 재생되고, 끝난 상태가 그대로 남습니다. 캡션 옆의 '다시 보기'를 누르면 처음부터 다시 재생됩니다.

1. 금액 칸에 30,000이 입력됩니다.
2. 거래처 단추 '국제세탁'을 누르면 거래처 칸이 채워집니다.
3. 0.3초 뒤 종류 '세탁'이 같이 선택되고, 세탁 품목 줄이 열립니다.
4. '가죽다림'을 두 번 누르면 '가죽다림 1', '가죽다림 2'가 되고 옆에 − 단추가 생깁니다.

움직임 줄이기 설정을 켠 기기에서는 마지막 상태가 정지 화면으로 보입니다.

## 파일

| 경로 | 내용 |
|---|---|
| `expense/` | 시연 컴포넌트(React)와 스타일, Pretendard 부분 글꼴 |
| `embed/` | 안내 페이지에 넣을 단일 스크립트·스타일로 묶는 Vite 설정 |
| `compose.py` | 안내 페이지 사본에 시연을 끼워 넣는 스크립트 |

## 다시 빌드하기

`.claude/skills/stageshow`를 작업용 폴더로 복사한 뒤 그 안에서:

```sh
npm install
cp -r <repo>/bv-ledger-demo/expense examples/bv-expense
cp -r <repo>/bv-ledger-demo/embed embed
node node_modules/vite/bin/vite.js build --config embed/vite.config.ts   # embed/dist/ 생성
python3 <repo>/bv-ledger-demo/compose.py <안내 원본.html> embed/dist <글꼴 폴더> <결과.html>
```

미리보기 서버는 `node node_modules/vite/bin/vite.js playground --config playground/vite.config.ts`, 화면 확인은 `CHROME_PATH=<chromium> node scripts/film.mjs "http://127.0.0.1:<port>/?capture=bv-expense" --select '#example' --gate`입니다.

## 점검 기록 (REHEARSAL)

- **참고한 기준 예시:** `phone-touch`(폰 고정 구도, 터치 커서), `form-error`(한 번 재생, 포스터가 결과 화면).
- **바꾼 것:** 안내 페이지의 색(종이색, 잉크, 번트 시에나)과 Pretendard, 선택 단추는 잉크 채움, 모서리 없음. 폰 테두리는 안내 페이지의 가는 선과 맞추려고 `outline`을 썼습니다. 용도·결제·증빙은 이야기 밖이라 회색 막대로 두었습니다.
- **통과:** `film.mjs --gate` 결과 `rehearsal passed`(넓은 화면). 정지 화면은 572px, 390px 두 너비 모두 지적 없음.
- **남은 지적과 판단:**
  - 0.07초의 글자 폭 점프: 미리보기 서버에서 글꼴이 늦게 불러와져 생긴 것. 안내 페이지에서는 글꼴이 페이지 안에 들어 있어 거의 생기지 않습니다.
  - 금액 숫자가 입력될 때 한 자리씩 왼쪽으로 밀리는 것: 오른쪽 정렬 입력칸의 실제 동작이라 `data-snap`으로 표시했습니다.
- **확인하지 못한 것:**
  - 품목 단추가 종류에 따라 바뀌는지(세탁을 고르기 전에는 품목 줄이 없는지). 기존 기록(물보라 '지퍼', 중앙단추 '단추')을 보고 그렇게 추정해서 만들었습니다.
  - 거래처 칸의 빈 상태 안내 문구('거래처 이름')는 실제 앱 문구가 아닐 수 있습니다.
  - 실제 아이폰 사파리에서의 재생 속도와 스크롤 중 동작.
  - 별도 리뷰어의 검토(review.md)는 하지 않았습니다.
