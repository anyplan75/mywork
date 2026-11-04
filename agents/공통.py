# 기기 작동기의 상태 보고와 모드 명령. 주소는 설정 파일에서만 읽는다.

import json
import os
import shutil
import signal
import subprocess
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime
from pathlib import Path

from config.불러오기 import (
    관제기준,
    설정읽기,
    파일모듈,
    프로그램경로,
    프로젝트루트,
)


프로그램키 = ("프로프리젠터", "브이믹스", "파이널컷", "다빈치리졸브", "라이트룸")


def _모듈(상대, 이름):
    return 파일모듈(프로젝트루트() / 상대, 이름)


def 모드모듈():
    return _모듈("workflows/mode-switch/모드.py", "모드전환")


def 보관모듈():
    return _모듈("workflows/lightroom-archive/목록철보관.py", "목록철보관")


def 용량문구(바이트):
    기가 = float(바이트) / (1024 ** 3)
    return f"{기가:.1f}기가바이트"


def 연산장치():
    if os.name == "nt":
        return _윈도우연산()
    try:
        출력 = subprocess.check_output(["ps", "-A", "-o", "%cpu="], text=True, timeout=8)
        합 = 0.0
        for 줄 in 출력.splitlines():
            토큰 = 줄.strip()
            if not 토큰:
                continue
            try:
                합 += float(토큰)
            except ValueError:
                continue
        코어 = os.cpu_count() or 1
        비율 = min(100.0, 합 / 코어)
        부하 = os.getloadavg()[0]
        return f"사용 {비율:.0f}퍼센트, 부하 {부하:.2f}"
    except (OSError, subprocess.SubprocessError):
        return "아직 없음"


def 기억장치():
    if os.name == "nt":
        return _윈도우기억()
    try:
        전체 = int(subprocess.check_output(["sysctl", "-n", "hw.memsize"], text=True, timeout=5).strip())
        쪽 = int(subprocess.check_output(["sysctl", "-n", "hw.pagesize"], text=True, timeout=5).strip())
        통계 = subprocess.check_output(["vm_stat"], text=True, timeout=5)
        표 = {}
        for 줄 in 통계.splitlines():
            if ":" not in 줄:
                continue
            키, _, 값 = 줄.partition(":")
            숫자 = "".join(글자 for 글자 in 값 if 글자.isdigit())
            if 숫자:
                표[키.strip()] = int(숫자)
        사용쪽 = 0
        for 키 in ("Pages active", "Pages wired down", "Pages occupied by compressor"):
            사용쪽 += 표.get(키, 0)
        return f"전체 {용량문구(전체)} 중 {용량문구(사용쪽 * 쪽)} 사용"
    except (OSError, subprocess.SubprocessError, ValueError):
        return "아직 없음"


def 디스크():
    try:
        사용 = shutil.disk_usage("/")
        return f"전체 {용량문구(사용.total)} 중 {용량문구(사용.used)} 사용"
    except OSError:
        return "아직 없음"


def _윈도우연산():
    try:
        출력 = subprocess.check_output(
            ["wmic", "cpu", "get", "loadpercentage"],
            text=True,
            timeout=8,
        )
        숫자 = [토큰 for 토큰 in 출력.split() if 토큰.isdigit()]
        if not 숫자:
            return "아직 없음"
        return "사용 " + 숫자[0] + "퍼센트"
    except (OSError, subprocess.SubprocessError):
        return "아직 없음"


def _윈도우기억():
    try:
        import ctypes

        class 상태(ctypes.Structure):
            _fields_ = [
                ("길이", ctypes.c_ulong),
                ("비율", ctypes.c_ulong),
                ("전체", ctypes.c_ulonglong),
                ("남음", ctypes.c_ulonglong),
                ("페이지전체", ctypes.c_ulonglong),
                ("페이지남음", ctypes.c_ulonglong),
                ("가상전체", ctypes.c_ulonglong),
                ("가상남음", ctypes.c_ulonglong),
                ("확장", ctypes.c_ulonglong),
            ]

        자료 = 상태()
        자료.길이 = ctypes.sizeof(상태)
        ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(자료))
        사용 = 자료.전체 - 자료.남음
        return f"전체 {용량문구(자료.전체)} 중 {용량문구(사용)} 사용"
    except (AttributeError, OSError, ValueError):
        return "아직 없음"


def 프로세스있음(경로):
    if not 경로:
        return None
    이름 = Path(경로).name
    try:
        if os.name == "nt":
            출력 = subprocess.check_output(["tasklist", "/FO", "CSV", "/NH"], text=True, timeout=8)
            return 이름.lower() in 출력.lower()
        출력 = subprocess.check_output(["ps", "-ax", "-o", "comm="], text=True, timeout=8)
    except (OSError, subprocess.SubprocessError):
        return None
    for 줄 in 출력.splitlines():
        토큰 = 줄.strip()
        if not 토큰:
            continue
        if Path(토큰).name == 이름:
            return True
    return False


def 프로그램표(설정, 기기):
    표 = {}
    for 키 in 프로그램키:
        경로 = 프로그램경로(설정, 키, 기기)
        if not 경로:
            표[키] = "아직 없음"
            continue
        있음 = 프로세스있음(경로)
        if 있음 is None:
            표[키] = "아직 없음"
        elif 있음:
            표[키] = "켜짐"
        else:
            표[키] = "꺼짐"
    return 표


def _묶음(경로):
    부분 = Path(경로).parts
    for 인덱스, 이름 in enumerate(부분):
        if 이름.endswith(".app"):
            return str(Path(*부분[: 인덱스 + 1]))
    return 경로


def 앱실행(경로):
    if not 경로:
        return "경로가 아직 없습니다"
    if not Path(경로).exists():
        return "실행 파일이 없습니다"
    try:
        if os.name == "nt":
            subprocess.Popen([경로])
        else:
            subprocess.Popen(["open", _묶음(경로)], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except OSError:
        return "실행하지 못했습니다"
    return "실행을 요청했습니다"


def 앱종료(경로):
    if not 경로:
        return "경로가 아직 없습니다"
    이름 = Path(경로).name
    찾은번호 = []
    try:
        if os.name == "nt":
            출력 = subprocess.check_output(["tasklist", "/FO", "CSV", "/NH"], text=True, timeout=8)
            for 줄 in 출력.splitlines():
                if 이름.lower() in 줄.lower():
                    칸 = 줄.split(",")
                    if len(칸) > 1 and 칸[1].strip().strip('"').isdigit():
                        찾은번호.append(int(칸[1].strip().strip('"')))
        else:
            출력 = subprocess.check_output(["ps", "-ax", "-o", "pid=,comm="], text=True, timeout=8)
            for 줄 in 출력.splitlines():
                토큰 = 줄.strip().split(None, 1)
                if len(토큰) != 2 or not 토큰[0].isdigit():
                    continue
                if Path(토큰[1]).name == 이름:
                    찾은번호.append(int(토큰[0]))
    except (OSError, subprocess.SubprocessError):
        return "실행 여부를 확인하지 못했습니다"
    if not 찾은번호:
        return "이미 꺼져 있습니다"
    for 번호 in 찾은번호:
        try:
            os.kill(번호, signal.SIGTERM)
        except OSError:
            return "종료하지 못했습니다"
    return "종료를 요청했습니다"


def 소리입력점검():
    try:
        출력 = subprocess.check_output(["system_profiler", "SPAudioDataType"], text=True, timeout=25)
    except (OSError, subprocess.SubprocessError):
        return "소리 입력 점검에 실패했습니다"
    if "Input Source" in 출력 or "입력" in 출력:
        return "소리 입력을 확인했습니다"
    return "소리 입력 장치를 찾지 못했습니다"


def 명령수행(기기, 종류, 설정):
    모드 = 모드모듈()
    if 기기 == "맥북프로" and 종류 == "예배":
        모드.적용("예배")
        실행 = 앱실행(프로그램경로(설정, "프로프리젠터", "맥북프로"))
        return "대리 영상 작업을 일시 정지했습니다. 프로프리젠터: " + 실행
    if 기기 == "맥북프로" and 종류 == "평상시":
        모드.적용("평상시")
        종료 = 앱종료(프로그램경로(설정, "프로프리젠터", "맥북프로"))
        return "감시 대기로 돌아갔습니다. 프로프리젠터: " + 종료
    if 기기 == "윈도우" and 종류 == "예배":
        return "브이믹스: " + 앱실행(프로그램경로(설정, "브이믹스", "윈도우"))
    if 기기 == "윈도우" and 종류 == "평상시":
        return "브이믹스: " + 앱종료(프로그램경로(설정, "브이믹스", "윈도우"))
    if 기기 == "아이맥" and 종류 == "예배":
        return 소리입력점검()
    if 종류 in ("예배", "평상시"):
        return "이 기기는 상태만 보고합니다"
    return "알 수 없는 명령입니다"


def _요청(주소, 자료=None, 방법="GET"):
    본문 = None
    헤더 = {}
    if 자료 is not None:
        본문 = json.dumps(자료, ensure_ascii=False).encode("utf-8")
        헤더["Content-Type"] = "application/json; charset=utf-8"
    요청 = urllib.request.Request(주소, data=본문, headers=헤더, method=방법)
    # 집 밖 프록시를 타지 않고, 설정에 적힌 관제 주소로만 붙는다.
    여는이 = urllib.request.build_opener(urllib.request.ProxyHandler({}))
    with 여는이.open(요청, timeout=5) as 응답:
        원문 = 응답.read().decode("utf-8")
    if not 원문:
        return {}
    return json.loads(원문)


def 상태만들기(기기, 설정):
    return {
        "기기": 기기,
        "시각": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "연산장치": 연산장치(),
        "기억장치": 기억장치(),
        "디스크": 디스크(),
        "프로그램": 프로그램표(설정, 기기),
    }


def 루프(기기):
    print(기기 + " 작동기를 시작했습니다")
    이전라이트룸 = None
    while True:
        try:
            설정 = 설정읽기()
            기준 = 관제기준(설정)
            if not 기준:
                print("관제 주소가 아직 없습니다")
                time.sleep(3)
                continue
            상태 = 상태만들기(기기, 설정)
            if 기기 == "맥북프로":
                지금 = 상태["프로그램"].get("라이트룸") == "켜짐"
                if 이전라이트룸 is True and not 지금:
                    보관모듈().반응(설정, True)
                else:
                    보관모듈().상태(설정)
                if 상태["프로그램"].get("라이트룸") != "아직 없음":
                    이전라이트룸 = 지금
            _요청(기준 + "/beat", 상태, "POST")
            질의 = urllib.parse.urlencode({"기기": 기기})
            명령 = _요청(기준 + "/cmd?" + 질의)
            if 명령.get("번호"):
                결과 = 명령수행(기기, 명령.get("종류") or "", 설정)
                _요청(기준 + "/done", {"번호": 명령["번호"], "결과": 결과}, "POST")
        except (OSError, urllib.error.URLError, json.JSONDecodeError, ValueError):
            print("관제 화면과 연결하지 못했습니다")
        time.sleep(2)
