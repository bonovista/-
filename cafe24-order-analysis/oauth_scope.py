#!/usr/bin/env python3
"""카페24 OAuth scope 확인·추가 — 토큰과 자격증명 값은 화면에 출력하지 않는다.

bonovista-brand-image 번들의 scripts/(api.py · .env · token.json)를 그대로 쓴다.

사용:
  python3 oauth_scope.py check                       # token.json scope에 mall.read_order가 있는지
  python3 oauth_scope.py url                         # 기존 scope + mall.read_order 승인 URL → authorize_url.txt
  python3 oauth_scope.py exchange "<리다이렉트 URL 또는 code>"   # 「동의함」 후 60초 안에. 기존 token.json은 백업

옵션: --api-dir <scripts 폴더> (기본: $BBI_SCRIPTS → /home/claude/bbi/scripts → 스킬 번들 순으로 찾음)
"""
import argparse, json, os, secrets, subprocess, sys, time, urllib.parse

NEED = "mall.read_order"
# bonovista-brand-image 준비 2번의 승인 URL scope
BASE_SCOPES = ["mall.read_application", "mall.write_application",
               "mall.read_product", "mall.write_product"]
API_DIR_CANDIDATES = [
    os.environ.get("BBI_SCRIPTS", ""),
    "/home/claude/bbi/scripts",
    "/mnt/skills/user/bonovista-brand-image/scripts",
]


def find_api_dir(explicit=None):
    for d in [explicit] + API_DIR_CANDIDATES:
        if d and os.path.isfile(os.path.join(d, "api.py")) and os.path.isfile(os.path.join(d, ".env")):
            return d
    raise SystemExit("[중단] api.py와 .env가 함께 있는 scripts 폴더를 찾지 못함 — --api-dir로 지정")


def load_api(api_dir):
    sys.path.insert(0, api_dir)
    import api
    return api


def token_scopes(api):
    if not os.path.isfile(api.TOKEN_FILE):
        return None
    tok = json.load(open(api.TOKEN_FILE))
    return tok.get("scopes")


def cmd_check(api):
    scopes = token_scopes(api)
    if scopes is None:
        print("token.json 없음 또는 scope 정보 없음 → url 단계부터 진행")
        return 1
    print("현재 scope:", ", ".join(scopes))
    if NEED in scopes:
        print(f"{NEED} 있음 — 승인 불필요")
        return 0
    print(f"{NEED} 없음 → python3 oauth_scope.py url")
    return 1


def cmd_url(api):
    scopes = list(BASE_SCOPES)
    for s in token_scopes(api) or []:
        if s not in scopes:
            scopes.append(s)
    if NEED not in scopes:
        scopes.append(NEED)
    redirect = api.ENV.get("CAFE24_REDIRECT_URI", "https://bonovista.cafe24.com")
    state = secrets.token_urlsafe(12)
    q = urllib.parse.urlencode({"response_type": "code", "client_id": api.ENV["CAFE24_CLIENT_ID"],
                                "redirect_uri": redirect, "scope": ",".join(scopes), "state": state},
                               safe=",")
    url = f"{api.BASE}/oauth/authorize?{q}"
    out = os.path.join(os.path.dirname(api.TOKEN_FILE), "authorize_url.txt")
    with open(out, "w") as f:
        f.write(url + "\n")
    os.chmod(out, 0o600)
    with open(out + ".state", "w") as f:
        f.write(state)
    os.chmod(out + ".state", 0o600)
    print("요청 scope:", ", ".join(scopes))
    print("승인 URL 저장:", out, "(client_id 포함 — 채팅에 붙이지 말고 브라우저로 연다)")
    print("「동의함」 → 리다이렉트 URL의 code를 60초 안에: python3 oauth_scope.py exchange \"<URL>\"")
    return 0


def cmd_exchange(api, arg):
    code, state = arg.strip(), None
    if "code=" in code:
        qs = urllib.parse.parse_qs(urllib.parse.urlparse(code).query)
        code, state = qs.get("code", [""])[0], qs.get("state", [None])[0]
    if not code:
        raise SystemExit("[중단] code를 찾지 못함")
    sfile = os.path.join(os.path.dirname(api.TOKEN_FILE), "authorize_url.txt.state")
    if state and os.path.isfile(sfile) and open(sfile).read().strip() != state:
        raise SystemExit("[중단] state 불일치 — 이 세션에서 만든 승인 URL이 아님")
    redirect = api.ENV.get("CAFE24_REDIRECT_URI", "https://bonovista.cafe24.com")
    r = subprocess.run(["curl", "-s", "-X", "POST", f"{api.BASE}/oauth/token",
                        "-u", f"{api.ENV['CAFE24_CLIENT_ID']}:{api.ENV['CAFE24_CLIENT_SECRET']}",
                        "-H", "Content-Type: application/x-www-form-urlencoded",
                        "-d", "grant_type=authorization_code", "-d", f"code={code}",
                        "-d", f"redirect_uri={redirect}"],
                       capture_output=True, text=True, timeout=60)
    try:
        data = json.loads(r.stdout)
    except Exception:
        raise SystemExit("[실패] 응답이 JSON이 아님")
    if "access_token" not in data:
        raise SystemExit(f"[실패] {data.get('error')}: {data.get('error_description')}")
    if os.path.isfile(api.TOKEN_FILE):
        bak = f"{api.TOKEN_FILE}.bak-{time.strftime('%Y%m%d%H%M%S')}"
        os.replace(api.TOKEN_FILE, bak)
        os.chmod(bak, 0o600)
        print("기존 token.json 백업:", os.path.basename(bak))
    with open(api.TOKEN_FILE, "w") as f:
        json.dump(data, f)
    os.chmod(api.TOKEN_FILE, 0o600)
    print("token.json 갱신 — scope:", ", ".join(data.get("scopes", [])))
    print("access 만료:", data.get("expires_at"), "/ refresh 만료:", data.get("refresh_token_expires_at"))
    today = time.strftime("%Y-%m-%d")
    n = api.call("GET", "/admin/orders/count", {"shop_no": 1, "start_date": today, "end_date": today})
    print("주문 API 확인 — 오늘 주문 수:", n.get("count"))
    print("토큰은 회전형 — 끝나면 프로젝트 문서 claude_cafe24-token.md 갱신")
    return 0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["check", "url", "exchange"])
    ap.add_argument("value", nargs="?")
    ap.add_argument("--api-dir")
    a = ap.parse_args()
    api = load_api(find_api_dir(a.api_dir))
    if a.cmd == "check":
        return cmd_check(api)
    if a.cmd == "url":
        return cmd_url(api)
    if not a.value:
        raise SystemExit("exchange에는 리다이렉트 URL 또는 code가 필요")
    return cmd_exchange(api, a.value)


if __name__ == "__main__":
    sys.exit(main())
