#!/usr/bin/env python3
"""BV-NOFLICKER v1 → v2 교체 (되돌리기 포함) — 스킨 공통 레이아웃 파일에 적용한다.

블록 위치: PC·모바일 스킨 모두 공통 레이아웃의 <head> (상세·게시판·로그인 화면에도 같은 블록이 들어 있다).
           "<!-- BV-NOFLICKER v1" 부터 "<!-- /BV-NOFLICKER -->" 까지.

사용:
  python3 apply_noflicker.py <레이아웃.html>              v1 → v2 (원본은 .bak_noflicker_v1_YYYYMMDD 로 남김)
  python3 apply_noflicker.py <레이아웃.html> --rollback   v2 → v1 원문(noflicker_v1_live.html)
  python3 apply_noflicker.py <레이아웃.html> --check      바꾸지 않고 상태만 본다

v1 블록은 2026-11-20 라이브 원문(noflicker_v1_live.html)과 글자 단위로 같아야 바꾼다.
다르면(누가 v1 을 손봤으면) 멈추고 차이를 보여 준다 — 그 차이를 v2 에 먼저 옮긴 뒤 다시 돌린다.
"""
import datetime, difflib, os, sys

HERE = os.path.dirname(os.path.abspath(__file__))
V1 = open(os.path.join(HERE, "noflicker_v1_live.html"), encoding="utf-8").read().strip()
V2 = open(os.path.join(HERE, "noflicker_v2.html"), encoding="utf-8").read().strip()
END = "<!-- /BV-NOFLICKER -->"


def block(s, head):
    """head 로 시작해 END 로 끝나는 블록의 (시작, 끝) — 정확히 하나여야 한다."""
    n = s.count(head)
    if n != 1:
        return None, n
    a = s.index(head)
    b = s.find(END, a)
    if b < 0:
        sys.exit("블록 끝 표식(%s)이 없다" % END)
    return (a, b + len(END)), 1


def main():
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    path, mode = sys.argv[1], (sys.argv[2] if len(sys.argv) > 2 else "")
    s = open(path, encoding="utf-8", newline="").read()               # 줄끝(CRLF 섞임)을 그대로 — 블록 밖은 한 글자도 안 바꾼다
    r1, n1 = block(s, "<!-- BV-NOFLICKER v1")
    r2, n2 = block(s, "<!-- BV-NOFLICKER v2")
    state = "v1" if r1 else "v2" if r2 else "없음"
    if n1 > 1 or n2 > 1 or (r1 and r2):
        sys.exit("BV-NOFLICKER 블록이 여러 개다(v1 %d · v2 %d) — 손으로 정리한 뒤 다시" % (n1, n2))

    if mode == "--check":
        same = (s[r1[0]:r1[1]] == V1) if r1 else (s[r2[0]:r2[1]] == V2) if r2 else False
        print("상태: %s · 기준 원문과 %s" % (state, "같음" if same else "다름"))
        return

    if mode == "--rollback":
        if not r2:
            sys.exit("v2 블록이 없다(현재 %s) — 되돌릴 것이 없음" % state)
        out = s[:r2[0]] + V1 + s[r2[1]:]
    else:
        if r2:
            sys.exit("이미 v2 다: " + path)
        if not r1:
            sys.exit("v1 블록을 못 찾음: " + path)
        cur = s[r1[0]:r1[1]]
        if cur != V1:
            print("v1 블록이 기준 원문(2026-11-20 라이브)과 다르다 — 멈춤. 차이:")
            for line in difflib.unified_diff(V1.splitlines(), cur.splitlines(), "기준 v1", "이 파일", lineterm="", n=0):
                print("  " + line)
            sys.exit(1)
        bak = path + ".bak_noflicker_v1_" + datetime.date.today().strftime("%Y%m%d")
        open(bak, "w", encoding="utf-8", newline="").write(s)
        print("백업:", bak)
        out = s[:r1[0]] + V2 + s[r1[1]:]

    open(path, "w", encoding="utf-8", newline="").write(out)
    print("적용:", path, "→", "v1" if mode == "--rollback" else "v2")


if __name__ == "__main__":
    main()
