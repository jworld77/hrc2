# -*- coding: utf-8 -*-
"""
한세대학교 인권센터 · 공개자료 수집기  (v2)
================================================================
국가법령정보 OPEN API(법제처)에서 판례·헌재결정례·법령해석례 등을
키워드로 내려받아  data/data_api.js  를 만듭니다.

[실행 방법 - 둘 중 아무거나]
  A) 이 파일(수집기.py)을 그대로 더블클릭
  B) START.bat 을 더블클릭

인증키는 이미 넣어 두었습니다. 바로 실행하면 됩니다.
문제가 생기면 화면에 원인과 해결 방법이 표시되고,
같은 폴더에 「응답샘플.xml」 이 저장됩니다.
"""

import json, os, re, ssl, sys, time, urllib.error, urllib.parse, urllib.request
import xml.etree.ElementTree as ET

try:                                    # 한글 콘솔에서 글자 때문에 멈추지 않도록
    sys.stdout.reconfigure(errors="replace")
    sys.stderr.reconfigure(errors="replace")
except Exception:
    pass

# ==============================================================
#  설정
# ==============================================================

OC = "hanseihrc"          # 국가법령정보 OPEN API 인증키

KEYWORDS = [
    "성희롱", "성폭력", "직장 내 괴롭힘", "인권침해", "차별행위",
    "2차 피해", "공익신고자", "대학 교원 징계", "지도교수", "스토킹",
]

TARGETS = [                # (target 코드, 자료 구분 이름)
    ("prec",  "판례"),
    ("detc",  "헌재결정례"),
    ("expc",  "법령해석례"),
    ("decc",  "인권위결정례"),
]

PAGES_PER_KEYWORD   = 1    # 1페이지 = 최대 100건
SLEEP               = 0.5  # 요청 간격(초)
FETCH_BODY          = True
MAX_BODY_PER_TARGET = 60

# ==============================================================
#  이하 수정 불필요
# ==============================================================

LIST_URL = "http://www.law.go.kr/DRF/lawSearch.do"
BODY_URL = "http://www.law.go.kr/DRF/lawService.do"
OUT_JS   = os.path.join("data", "data_api.js")
SAMPLE   = "응답샘플.xml"

CTX = ssl.create_default_context()
CTX.check_hostname = False
CTX.verify_mode = ssl.CERT_NONE

TAG_RULES = [
    ("성희롱", ["성희롱"]),
    ("성폭력|강제추행|강간|추행", ["성폭력"]),
    ("촬영|영상물|정보통신망|음란", ["디지털성폭력"]),
    ("괴롭힘|갑질|위력|우월", ["갑질", "직장내괴롭힘"]),
    ("차별", ["차별"]),
    ("징계|파면|해임|해고", ["징계"]),
    ("공익신고|내부고발|신고자", ["공익신고"]),
    ("불이익|보복", ["불이익금지"]),
    ("대학|학교|교원|학생|교수", ["대학·학교"]),
    ("정보공개", ["정보공개"]),
    ("손해배상|위자료", ["손해배상"]),
    ("스토킹", ["스토킹"]),
    ("개인정보", ["개인정보"]),
]

LINE = "-" * 64


def say(*a):
    print(*a, flush=True)


def http_get(url, timeout=25):
    req = urllib.request.Request(url, headers={
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
        "Accept": "application/xml,text/xml,*/*",
    })
    with urllib.request.urlopen(req, timeout=timeout, context=CTX) as r:
        return r.read()


def list_url(target, query, page, display=100):
    return (f"{LIST_URL}?OC={urllib.parse.quote(OC)}&target={target}&type=XML"
            f"&query={urllib.parse.quote(query)}&display={display}&page={page}")


def alltext(el):
    s = " ".join(t for t in el.itertext() if t)
    return re.sub(r"\s+", " ", s).strip()


def pick(node, patterns, exclude=()):
    """자식 태그 이름을 정규식으로 찾아 값을 돌려줍니다(태그 이름이 달라도 동작)."""
    for pat in patterns:
        for child in node:
            name = child.tag
            if re.search(pat, name) and not any(re.search(x, name) for x in exclude):
                v = alltext(child)
                if v:
                    return v
    return ""


def parse_items(raw):
    """응답 XML에서 항목 노드를 찾아 표준 형태로 바꿉니다.
       (반환) (items, 오류메시지)  — 오류가 없으면 오류메시지는 None"""
    head = raw[:400].decode("utf-8", "replace").lower()
    if "<html" in head or "<!doctype html" in head:
        return None, "HTML 페이지가 돌아왔습니다(인증키 오류 또는 미승인일 가능성이 큽니다)."
    try:
        root = ET.fromstring(raw)
    except ET.ParseError as e:
        return None, f"XML 형식이 아닙니다: {e}"

    items = []
    for node in root:                       # 자식을 가진 루트의 직계 자식 = 항목
        if len(node) == 0:
            continue
        rec = {
            "sid":   pick(node, [r"일련번호$", r"^ID$", r"^id$"]),
            "title": pick(node, [r"사건명", r"안건명", r"제목", r"결정문명", r"명$"]),
            "no":    pick(node, [r"사건번호", r"안건번호", r"결정문번호", r"번호$"],
                          exclude=[r"일련번호"]),
            "date":  pick(node, [r"선고일자", r"결정일자", r"회신일자", r"일자$", r"일$"]),
            "org":   pick(node, [r"법원명", r"기관명", r"위원회", r"회신기관"]),
            "link":  pick(node, [r"링크", r"link"]),
            "extra": alltext(node)[:1200],
        }
        if rec["title"] or rec["no"]:
            items.append(rec)
    return items, None


def fetch_body(target, sid):
    try:
        raw = http_get(f"{BODY_URL}?OC={urllib.parse.quote(OC)}&target={target}"
                       f"&type=XML&ID={urllib.parse.quote(sid)}")
        root = ET.fromstring(raw)
    except Exception:
        return ""
    keep = ("판시사항", "판결요지", "참조조문", "판례내용", "재판요지", "결정요지",
            "이유", "주문", "질의요지", "회답", "이유내용", "결정문내용", "내용", "요지")
    parts = []
    for el in root.iter():
        if any(k in el.tag for k in keep):
            t = alltext(el)
            if t and len(t) > 10:
                parts.append(f"[{el.tag}] {t}")
    if not parts:                            # 태그 이름이 달라도 전체 텍스트라도 담습니다
        parts = [alltext(root)]
    return "\n".join(parts)[:6000]


def auto_tags(text, label):
    tags = []
    for pat, tg in TAG_RULES:
        if re.search(pat, text):
            for t in tg:
                if t not in tags:
                    tags.append(t)
    return tags or [label]


# --------------------------------------------------------------
#  1단계 : 연결 테스트
# --------------------------------------------------------------
def connection_test():
    say(LINE)
    say(" 1단계  연결 및 인증키 확인")
    say(LINE)
    say(f" 인증키(OC) : {OC}")
    ok_targets, first_raw = [], None

    for target, label in TARGETS:
        url = list_url(target, "성희롱", 1, display=3)
        try:
            raw = http_get(url)
        except urllib.error.HTTPError as e:
            say(f"  [{label:<7}] 실패 - 서버 응답 코드 {e.code}")
            continue
        except urllib.error.URLError as e:
            say(f"  [{label:<7}] 실패 - 인터넷 연결/프록시 문제 : {e.reason}")
            say("")
            say(" ** 인터넷에 연결되지 않았거나 학교 방화벽이 막고 있습니다. **")
            say("    브라우저에서 아래 주소가 열리는지 먼저 확인해 주세요.")
            say(f"    {url}")
            return [], None
        except Exception as e:
            say(f"  [{label:<7}] 실패 - {type(e).__name__}: {e}")
            continue

        if first_raw is None:
            first_raw = raw
        items, err = parse_items(raw)
        if err:
            say(f"  [{label:<7}] 실패 - {err}")
        elif not items:
            say(f"  [{label:<7}] 응답은 정상이나 결과 0건 (이 자료는 신청되지 않았을 수 있습니다)")
        else:
            say(f"  [{label:<7}] 정상  (예: {items[0]['title'][:40] or items[0]['no']})")
            ok_targets.append((target, label))
        time.sleep(SLEEP)

    if first_raw is not None:
        try:
            with open(SAMPLE, "wb") as f:
                f.write(first_raw)
            say(f"\n 첫 응답을 「{SAMPLE}」 에 저장했습니다. (문제 확인용)")
        except Exception:
            pass

    say("")
    if not ok_targets:
        say(" ** 사용 가능한 자료가 없습니다. 아래를 확인해 주세요. **")
        say("   1) open.law.go.kr 로그인 → [API인증키관리]/[API인증값변경] 에서")
        say(f"      인증키가 정말 '{OC}' 인지 확인")
        say("   2) [OPEN API 신청] 에서 '판례' 등 자료별 신청이 승인되었는지 확인")
        say("      (자료마다 따로 신청해야 하며, 신청하지 않은 자료는 0건이 나옵니다)")
        say("   3) 브라우저에서 아래 주소를 넣어 XML 이 나오는지 확인")
        say(f"      {list_url('prec', '성희롱', 1, 3)}")
        say(f"   4) 같은 폴더의 「{SAMPLE}」 파일 내용을 알려주시면 원인을 찾아드립니다.")
    else:
        say(f" 사용 가능한 자료 : " + ", ".join(l for _, l in ok_targets))
    return ok_targets, first_raw


# --------------------------------------------------------------
#  2단계 : 수집
# --------------------------------------------------------------
def collect(ok_targets):
    say("")
    say(LINE)
    say(" 2단계  자료 수집")
    say(LINE)
    seen, out = set(), []
    for target, label in ok_targets:
        got, body_cnt = 0, 0
        for kw in KEYWORDS:
            for page in range(1, PAGES_PER_KEYWORD + 1):
                try:
                    raw = http_get(list_url(target, kw, page))
                except Exception as e:
                    say(f"  [{label}] '{kw}' 요청 실패 : {e}")
                    break
                time.sleep(SLEEP)
                items, err = parse_items(raw)
                if err or not items:
                    break
                for it in items:
                    key = (target, it["sid"] or it["no"] or it["title"])
                    if key in seen:
                        continue
                    seen.add(key)
                    link = it["link"] or ""
                    if link.startswith("/"):
                        link = "https://www.law.go.kr" + link
                    body = ""
                    if FETCH_BODY and it["sid"] and body_cnt < MAX_BODY_PER_TARGET:
                        body = fetch_body(target, it["sid"])
                        body_cnt += 1
                        time.sleep(SLEEP)
                    if not body:
                        body = it["extra"] or "(본문 미수집 - '원문 열기'로 확인하세요)"
                    out.append({
                        "id":      f"{target}-{it['sid'] or len(out)}",
                        "src":     label,
                        "cat":     it["org"] or label,
                        "ref":     it["no"],
                        "title":   it["title"] or it["no"],
                        "chapter": "",
                        "date":    it["date"],
                        "tags":    auto_tags((it["title"] or "") + " " + body, label),
                        "body":    body,
                        "url":     link,
                    })
                    got += 1
                say(f"  [{label}] '{kw}' -> 누적 {got}건")
        say(f"  * {label} 완료 : {got}건")
    return out


def save(out):
    os.makedirs("data", exist_ok=True)
    js = ("// 국가법령정보 OPEN API 수집 결과 (수집기.py 자동 생성)\n"
          f"// 수집 건수 : {len(out)}\n"
          "window.DATA_API = " + json.dumps(out, ensure_ascii=False, indent=1) + ";\n")
    with open(OUT_JS, "w", encoding="utf-8") as f:
        f.write(js)


def main():
    say("")
    say("=" * 64)
    say("  한세대학교 인권센터 - 공개자료 수집기")
    say("=" * 64)
    say(f" 작업 폴더 : {os.getcwd()}")

    if not os.path.isdir("data"):
        say("")
        say(" ** 이 폴더에 data 폴더가 없습니다. **")
        say("    압축을 푼 폴더 안에서 실행해 주세요.")
        return

    ok, _ = connection_test()
    if not ok:
        return

    out = collect(ok)
    if not out:
        say("\n 수집된 자료가 없습니다.")
        return
    save(out)

    say("")
    say("=" * 64)
    say(f"  완료 : 총 {len(out)}건을 {OUT_JS} 에 저장했습니다.")
    by = {}
    for r in out:
        by[r["src"]] = by.get(r["src"], 0) + 1
    for k, v in by.items():
        say(f"   - {k} : {v}건")
    say("")
    say("  이제 「검색.html」 을 열고 F5 로 새로고침하세요.")
    say("=" * 64)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        say("\n 사용자가 중단했습니다.")
    except Exception:
        say("\n" + LINE)
        say(" 예상하지 못한 오류가 발생했습니다. 아래 내용을 알려주시면 고쳐 드립니다.")
        say(LINE)
        import traceback
        traceback.print_exc()
    try:
        input("\n 엔터를 누르면 창이 닫힙니다. ")
    except Exception:
        pass
