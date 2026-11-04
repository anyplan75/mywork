# 맥북에서 띄우는 관제 화면. 표준 라이브러리만 쓴다. 주소와 경로는 설정 파일에서만 읽는다.

import json
import shutil
import subprocess
import sys
import threading
import time
import urllib.parse
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

루트 = Path(__file__).resolve().parents[1]
if str(루트) not in sys.path:
    sys.path.insert(0, str(루트))

from config.불러오기 import (
    깊게,
    설정읽기,
    작업경로,
    파일모듈,
    포트번호,
    프로그램경로,
    프로젝트루트,
)

모드 = 파일모듈(프로젝트루트() / "workflows/mode-switch/모드.py", "모드전환")
대리 = 파일모듈(프로젝트루트() / "workflows/proxy-media/대리영상.py", "대리영상")
변환 = 파일모듈(프로젝트루트() / "workflows/path-convert/경로변환.py", "경로변환")
보관 = 파일모듈(프로젝트루트() / "workflows/lightroom-archive/목록철보관.py", "목록철보관")
음향 = 파일모듈(프로젝트루트() / "workflows/audio-preview/미리듣기.py", "미리듣기")

잠금 = threading.Lock()
보고들 = {}
명령들 = []
다음번호 = 1
작업현황 = {"대리": {}, "음향": {}}
연결캐시 = {}
연결시각 = 0.0

기기순서 = (
    ("맥북프로", "맥북프로"),
    ("맥미니", "맥미니"),
    ("아이맥", "아이맥"),
    ("윈도우", "윈도우 컴퓨터"),
    ("나스", "나스"),
    ("오라클클라우드", "오라클 클라우드"),
)
담당 = {
    "프로프리젠터": "맥북프로",
    "브이믹스": "윈도우",
    "파이널컷": "맥북프로",
    "다빈치리졸브": "맥북프로",
    "라이트룸": "맥북프로",
}
표시이름 = {
    "프로프리젠터": "프로프리젠터",
    "브이믹스": "브이믹스",
    "파이널컷": "파이널 컷",
    "다빈치리졸브": "다빈치 리졸브",
    "라이트룸": "라이트룸",
}
작동기기 = {"맥북프로", "맥미니", "아이맥", "윈도우"}


def 용량문구(바이트):
    기가 = float(바이트) / (1024 ** 3)
    return f"{기가:.1f}기가바이트"


def _노드모으기(자료):
    노드 = []
    자신 = 자료.get("Self")
    if isinstance(자신, dict):
        노드.append(자신)
    동료 = 자료.get("Peer") or {}
    if isinstance(동료, dict):
        노드.extend(값 for 값 in 동료.values() if isinstance(값, dict))
    elif isinstance(동료, list):
        노드.extend(값 for 값 in 동료 if isinstance(값, dict))
    return 노드


def _표식(노드):
    표식 = set()
    이름 = str(노드.get("DNSName") or "").rstrip(".").casefold()
    if 이름:
        표식.add(이름)
    for 주소 in 노드.get("TailscaleIPs") or []:
        표식.add(str(주소).casefold())
    return 표식


def 연결표(설정):
    global 연결캐시, 연결시각
    지금 = time.time()
    if 연결캐시 and 지금 - 연결시각 < 10:
        return 연결캐시
    결과 = {}
    도구 = shutil.which("tailscale")
    자료 = None
    if 도구:
        try:
            출력 = subprocess.check_output([도구, "status", "--json"], text=True, timeout=8)
            자료 = json.loads(출력)
        except (OSError, subprocess.SubprocessError, json.JSONDecodeError):
            자료 = None
    노드 = _노드모으기(자료) if isinstance(자료, dict) else []
    for 키, _이름 in 기기순서:
        목표 = set()
        for 항목 in ("매직디엔에스", "아이피버전4", "아이피버전6"):
            값 = 깊게(설정, 키, 항목).casefold()
            if 값:
                목표.add(값)
        if not 목표:
            결과[키] = "아직 없음"
            continue
        if 자료 is None:
            결과[키] = "테일스케일 상태를 읽지 못했습니다"
            continue
        찾음 = None
        for 노드하나 in 노드:
            if 목표 & _표식(노드하나):
                찾음 = 노드하나
                break
        if not 찾음:
            결과[키] = "꺼짐"
        elif 찾음.get("Online") is True:
            결과[키] = "켜짐"
        else:
            결과[키] = "꺼짐"
    연결캐시 = 결과
    연결시각 = 지금
    return 결과


def 나스용량(설정):
    접두 = 깊게(설정, "나스", "맥연결경로")
    if not 접두 or not Path(접두).is_dir():
        return "아직 없음"
    try:
        사용 = shutil.disk_usage(접두)
    except OSError:
        return "아직 없음"
    return f"전체 {용량문구(사용.total)} 중 {용량문구(사용.used)} 사용"


def 최신보고(기기):
    보고 = 보고들.get(기기)
    if not 보고:
        return None
    if time.time() - 보고["받은시각"] > 15:
        return None
    return 보고["자료"]


def 프로그램현황(설정):
    목록 = []
    for 키, 기기 in 담당.items():
        경로 = 프로그램경로(설정, 키, 기기)
        if not 경로:
            상태 = "아직 없음"
        else:
            보고 = 최신보고(기기)
            if not 보고:
                상태 = "작동기 없음"
            else:
                상태 = (보고.get("프로그램") or {}).get(키) or "작동기 없음"
        목록.append({"이름": 표시이름[키], "상태": 상태})
    return 목록


def 기기현황(설정):
    연결 = 연결표(설정)
    목록 = []
    for 키, 이름 in 기기순서:
        보고 = 최신보고(키) if 키 in 작동기기 else None
        if 키 not in 작동기기:
            연산 = "작동기 없음"
            기억 = "작동기 없음"
            디스크 = "작동기 없음"
        elif not 보고:
            연산 = "작동기 없음"
            기억 = "작동기 없음"
            디스크 = "작동기 없음"
        else:
            연산 = 보고.get("연산장치") or "작동기 없음"
            기억 = 보고.get("기억장치") or "작동기 없음"
            디스크 = 보고.get("디스크") or "작동기 없음"
        목록.append({
            "이름": 이름,
            "연결": 연결.get(키) or "아직 없음",
            "연산장치": 연산,
            "기억장치": 기억,
            "디스크": 디스크,
        })
    return 목록


def 명령표시():
    지금 = time.time()
    목록 = []
    for 항목 in 명령들[-12:]:
        if 항목["결과"]:
            글 = 항목["결과"]
        elif 지금 - 항목["시각"] > 8:
            글 = "응답 없음"
        else:
            글 = "요청 중입니다"
        목록.append({"요청": 항목["설명"], "결과": 글})
    return 목록


def 현황():
    설정 = 설정읽기()
    with 잠금:
        대리상태 = dict(작업현황.get("대리") or {})
        음향상태 = dict(작업현황.get("음향") or {})
        명령 = 명령표시()
    목록철 = 보관.상태(설정)
    일시 = 목록철.get("일시") or "아직 없음"
    return {
        "모드": 모드.읽기().get("모드") or "감시대기",
        "기기": 기기현황(설정),
        "나스": 나스용량(설정),
        "프로그램": 프로그램현황(설정),
        "명령": 명령,
        "대리": 대리상태,
        "음향": 음향상태,
        "목록철일시": 일시,
        "목록철이유": 목록철.get("이유") or "",
        "편집구조": "아직 없음" if not 작업경로(설정, "영상편집구조") else "경로 있음",
    }


def 명령추가(기기, 종류, 설명):
    global 다음번호
    항목 = {
        "번호": 다음번호,
        "기기": 기기,
        "종류": 종류,
        "설명": 설명,
        "시각": time.time(),
        "보냄": False,
        "결과": "",
    }
    다음번호 += 1
    명령들.append(항목)


def 모드요청(종류):
    if 종류 == "예배":
        모드.적용("예배")
        with 잠금:
            명령추가("맥북프로", "예배", "프로프리젠터 실행과 대리 영상 일시 정지")
            명령추가("윈도우", "예배", "브이믹스 실행")
            명령추가("아이맥", "예배", "아이맥 소리 입력 점검")
        return "예배·행사 모드를 요청했습니다"
    if 종류 == "평상시":
        모드.적용("평상시")
        with 잠금:
            명령추가("맥북프로", "평상시", "프로프리젠터 종료와 감시 대기")
            명령추가("윈도우", "평상시", "브이믹스 종료")
        return "평상시 작업 모드를 요청했습니다"
    return "알 수 없는 모드입니다"


def 작업루프():
    while True:
        try:
            설정 = 설정읽기()
            대리결과 = 대리.점검(설정)
            음향결과 = 음향.점검(설정)
            with 잠금:
                작업현황["대리"] = 대리결과
                작업현황["음향"] = 음향결과
        except Exception:
            pass
        time.sleep(20)


화면 = """<!DOCTYPE html>
<html lang="ko">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>내 작업 관제</title>
<style>
body { margin: 0; background: #f3efe6; color: #1c1915; font-family: "Apple SD Gothic Neo", sans-serif; }
main { max-width: 880px; margin: 0 auto; padding: 28px 16px 64px; }
h1 { font-size: 1.9rem; margin: 0 0 8px; }
h2 { font-size: 1.15rem; margin: 0 0 10px; }
p { margin: 6px 0; line-height: 1.45; }
section { background: #fffdf8; border-radius: 16px; padding: 16px 18px; margin: 14px 0; }
button { font: inherit; font-size: 1.05rem; background: #1f4d3a; color: #fff; border: 0; border-radius: 12px; padding: 12px 16px; margin: 0 8px 8px 0; }
button.보조 { background: #3f4a44; }
input { font: inherit; width: 100%; box-sizing: border-box; padding: 10px 12px; border-radius: 10px; border: 1px solid #cfc6b8; margin: 8px 0; }
.기기 { border-top: 1px solid #eee6d8; padding-top: 8px; margin-top: 8px; }
</style>
</head>
<body>
<main>
<h1>내 작업 관제</h1>
<p id="모드글">모드를 읽는 중입니다</p>
<section>
<h2>모드</h2>
<button id="예배단추" type="button">예배·행사 모드</button>
<button id="평상단추" class="보조" type="button">평상시 작업 모드</button>
<div id="명령목록"></div>
</section>
<section>
<h2>경로 바꾸기</h2>
<p id="편집안내"></p>
<input id="맥경로" placeholder="편집 구조 문서의 맥 경로를 붙여 넣으세요">
<button id="변환단추" type="button">윈도우 경로로 바꾸기</button>
<p id="변환결과"></p>
</section>
<section>
<h2>기기</h2>
<div id="기기목록"></div>
</section>
<section>
<h2>나스 용량</h2>
<p id="나스용량"></p>
</section>
<section>
<h2>프로그램</h2>
<div id="프로그램목록"></div>
</section>
<section>
<h2>대리 영상</h2>
<div id="대리글"></div>
</section>
<section>
<h2>미리듣기</h2>
<div id="음향글"></div>
</section>
<section>
<h2>목록철 보관</h2>
<p id="목록철글"></p>
</section>
</main>
<script>
function 문단(부모, 글) {
  const 단락 = document.createElement("p");
  단락.textContent = 글;
  부모.appendChild(단락);
}
function 비우기(마디) {
  while (마디.firstChild) 마디.removeChild(마디.firstChild);
}
function 그리기(자료) {
  document.getElementById("모드글").textContent = "지금 모드: " + (자료.모드 || "감시대기");
  document.getElementById("편집안내").textContent = "편집 구조 폴더: " + (자료.편집구조 || "아직 없음");
  const 명령상자 = document.getElementById("명령목록");
  비우기(명령상자);
  (자료.명령 || []).forEach(function (항목) {
    문단(명령상자, 항목.요청 + " — " + 항목.결과);
  });
  const 기기상자 = document.getElementById("기기목록");
  비우기(기기상자);
  (자료.기기 || []).forEach(function (기기) {
    const 칸 = document.createElement("div");
    칸.className = "기기";
    문단(칸, 기기.이름 + " 연결: " + 기기.연결);
    문단(칸, "연산 장치: " + 기기.연산장치);
    문단(칸, "기억 장치: " + 기기.기억장치);
    문단(칸, "디스크: " + 기기.디스크);
    기기상자.appendChild(칸);
  });
  document.getElementById("나스용량").textContent = 자료.나스 || "아직 없음";
  const 프로그램상자 = document.getElementById("프로그램목록");
  비우기(프로그램상자);
  (자료.프로그램 || []).forEach(function (항목) {
    문단(프로그램상자, 항목.이름 + ": " + 항목.상태);
  });
  const 대리상자 = document.getElementById("대리글");
  비우기(대리상자);
  const 대리 = 자료.대리 || {};
  문단(대리상자, "변환 도구: " + (대리.도구 || "아직 없음"));
  문단(대리상자, "받을 폴더: " + (대리.받을폴더 || "아직 없음"));
  문단(대리상자, "대리 폴더: " + (대리.대리폴더 || "아직 없음"));
  문단(대리상자, 대리.설명 || "아직 없음");
  const 음항상자 = document.getElementById("음향글");
  비우기(음항상자);
  const 음향 = 자료.음향 || {};
  문단(음항상자, "변환 도구: " + (음향.도구 || "아직 없음"));
  문단(음항상자, "원본 폴더: " + (음향.원본폴더 || "아직 없음"));
  문단(음항상자, 음향.설명 || "아직 없음");
  const 이유 = 자료.목록철이유 ? " " + 자료.목록철이유 : "";
  document.getElementById("목록철글").textContent = "최근 보관 일시: " + (자료.목록철일시 || "아직 없음") + 이유;
}
async function 다시읽기() {
  try {
    const 응답 = await fetch("/now");
    그리기(await 응답.json());
  } catch (오류) {
    document.getElementById("모드글").textContent = "화면을 다시 읽지 못했습니다";
  }
}
async function 모드보내기(종류) {
  document.getElementById("모드글").textContent = "요청 중입니다";
  await fetch("/mode", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ 종류: 종류 })
  });
  다시읽기();
}
document.getElementById("예배단추").addEventListener("click", function () { 모드보내기("예배"); });
document.getElementById("평상단추").addEventListener("click", function () { 모드보내기("평상시"); });
document.getElementById("변환단추").addEventListener("click", async function () {
  const 맥경로 = document.getElementById("맥경로").value;
  const 응답 = await fetch("/convert", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ 맥경로: 맥경로 })
  });
  const 자료 = await 응답.json();
  if (자료.이유) {
    document.getElementById("변환결과").textContent = 자료.이유;
  } else {
    document.getElementById("변환결과").textContent = "바뀐 경로: " + (자료.바뀐경로 || "아직 없음");
  }
});
다시읽기();
setInterval(다시읽기, 3000);
</script>
</body>
</html>
"""

