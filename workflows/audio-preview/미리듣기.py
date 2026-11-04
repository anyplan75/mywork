# 다중 통로 원본을 날짜 폴더로 옮기고, 좌우 두 통로 미리듣기를 만든다.

import shutil
import subprocess
from datetime import datetime
from pathlib import Path

from config.불러오기 import 상대이름, 작업경로

소리확장 = {".wav", ".aif", ".aiff", ".caf", ".flac", ".w64"}
_마지막 = {"설명": ""}


def _기록(문장):
    경로 = Path(__file__).resolve().parent / "기록.log"
    시각 = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with 경로.open("a", encoding="utf-8") as 파일:
        파일.write(시각 + " " + 문장 + "\n")


def _이유기록(문장):
    if _마지막.get("설명") == 문장:
        return
    _마지막["설명"] = 문장
    _기록(문장)


def 도구있음():
    return bool(shutil.which("ffmpeg"))


def 점검(설정):
    결과 = {
        "도구": "있음" if 도구있음() else "없음",
        "원본폴더": "아직 없음",
        "보관폴더": "아직 없음",
        "미리듣기폴더": "아직 없음",
        "상대이름": 상대이름(설정, "음향원본") or "아직 없음",
        "설명": "",
    }
    원본 = 작업경로(설정, "음향원본")
    보관 = 작업경로(설정, "음향보관")
    듣기 = 작업경로(설정, "음향미리듣기")
    if not 원본 or not 보관 or not 듣기:
        결과["설명"] = "음향 폴더 경로가 아직 없어 미리듣기를 만들지 않습니다"
        _이유기록(결과["설명"])
        return 결과
    결과["원본폴더"] = "경로 있음"
    결과["보관폴더"] = "경로 있음"
    결과["미리듣기폴더"] = "경로 있음"
    도구 = shutil.which("ffmpeg")
    if not 도구:
        결과["설명"] = "에프엠펙이 없어 미리듣기를 만들지 않습니다"
        _이유기록(결과["설명"])
        return 결과
    원본폴더 = Path(원본)
    if not 원본폴더.is_dir():
        결과["설명"] = "음향 원본 폴더가 아직 없습니다"
        _이유기록(결과["설명"])
        return 결과
    날짜 = datetime.now().strftime("%Y-%m-%d")
    날짜폴더 = Path(보관) / 날짜
    듣기폴더 = Path(듣기)
    옮긴수 = 0
    for 파일 in sorted(원본폴더.iterdir()):
        if not 파일.is_file() or 파일.suffix.lower() not in 소리확장:
            continue
        날짜폴더.mkdir(parents=True, exist_ok=True)
        듣기폴더.mkdir(parents=True, exist_ok=True)
        들을파일 = 듣기폴더 / (파일.stem + "_미리듣기.m4a")
        try:
            subprocess.run(
                [도구, "-y", "-i", str(파일), "-ac", "2", "-c:a", "aac", str(들을파일)],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                check=True,
                timeout=3600,
            )
        except (OSError, subprocess.SubprocessError):
            _기록("미리듣기를 만들지 못했습니다: " + 파일.name)
            continue
        대상 = 날짜폴더 / 파일.name
        if 대상.exists():
            대상 = 날짜폴더 / (파일.stem + "-" + datetime.now().strftime("%H%M%S") + 파일.suffix)
        파일.replace(대상)
        옮긴수 += 1
        _기록("원본을 날짜 폴더로 옮기고 미리듣기를 만들었습니다: " + 파일.name)
    if 옮긴수:
        결과["설명"] = "미리듣기 " + str(옮긴수) + "개를 만들었습니다"
    else:
        결과["설명"] = "새로 옮길 녹음이 없습니다"
    _마지막["설명"] = 결과["설명"]
    return 결과
