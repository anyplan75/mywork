# 로컬 설정 파일을 읽는다. 주소와 경로는 이 파일에 적지 않는다.

import importlib.util
from pathlib import Path


def 프로젝트루트():
    return Path(__file__).resolve().parent.parent


def _주석제거(줄):
    결과 = []
    따옴 = None
    for 글자 in 줄:
        if 따옴:
            결과.append(글자)
            if 글자 == 따옴:
                따옴 = None
            continue
        if 글자 in ("'", '"'):
            따옴 = 글자
            결과.append(글자)
            continue
        if 글자 == "#":
            break
        결과.append(글자)
    return "".join(결과).rstrip()


def _값(토큰):
    토큰 = 토큰.strip()
    if len(토큰) >= 2 and 토큰[0] == 토큰[-1] and 토큰[0] in ("'", '"'):
        return 토큰[1:-1].replace('\\"', '"').replace("\\'", "'")
    return 토큰


def 분석(텍스트):
    내용 = []
    for 원문 in 텍스트.splitlines():
        본문 = _주석제거(원문)
        if not 본문.strip():
            continue
        들여 = len(본문) - len(본문.lstrip(" "))
        내용.append((들여, 본문.strip()))

    루트 = {}
    스택 = [(-1, 루트)]
    for 위치, (들여, 줄) in enumerate(내용):
        while 스택 and 들여 <= 스택[-1][0]:
            스택.pop()
        대상 = 스택[-1][1]
        if 줄.startswith("- "):
            if not isinstance(대상, list):
                raise ValueError("목록 형식 오류")
            대상.append(_값(줄[2:]))
            continue
        if ":" not in 줄:
            raise ValueError("설정 형식 오류")
        키, _, 나머지 = 줄.partition(":")
        키 = 키.strip()
        나머지 = 나머지.strip()
        if not isinstance(대상, dict):
            raise ValueError("설정 형식 오류")
        if 나머지 == "":
            다음 = 내용[위치 + 1] if 위치 + 1 < len(내용) else None
            if 다음 and 다음[0] > 들여 and 다음[1].startswith("- "):
                자식 = []
            else:
                자식 = {}
            대상[키] = 자식
            스택.append((들여, 자식))
        else:
            대상[키] = _값(나머지)
    return 루트


def 설정읽기():
    경로 = 프로젝트루트() / "config" / "설정.yaml"
    if not 경로.is_file():
        raise FileNotFoundError("설정 파일이 없습니다")
    return 분석(경로.read_text(encoding="utf-8"))


def 문자(값):
    if 값 is None:
        return ""
    return str(값).strip()


def 깊게(설정, *키들):
    현재 = 설정
    for 키 in 키들:
        if not isinstance(현재, dict) or 키 not in 현재:
            return ""
        현재 = 현재[키]
    if isinstance(현재, (dict, list)):
        return ""
    return 문자(현재)


def 작업경로(설정, 키):
    직접 = 깊게(설정, "나스실경로", 키)
    if 직접:
        return 직접
    접두 = 깊게(설정, "나스", "맥연결경로")
    상대 = 깊게(설정, "나스상대경로", 키)
    if 접두 and 상대:
        return str(Path(접두) / 상대)
    return ""


def 상대이름(설정, 키):
    return 깊게(설정, "나스상대경로", 키)


def 프로그램경로(설정, 프로그램, 기기):
    return 깊게(설정, "프로그램", 프로그램, 기기)


def 관제기준(설정):
    호스트 = 깊게(설정, "맥북프로", "아이피버전4")
    포트 = 깊게(설정, "관제화면", "포트")
    if not 호스트 or not 포트:
        return ""
    return "http://" + 호스트 + ":" + 포트


def 포트번호(설정):
    값 = 깊게(설정, "관제화면", "포트")
    if not 값.isdigit():
        return None
    return int(값)


def 파일모듈(경로, 이름):
    스펙 = importlib.util.spec_from_file_location(이름, 경로)
    모듈 = importlib.util.module_from_spec(스펙)
    스펙.loader.exec_module(모듈)
    return 모듈
