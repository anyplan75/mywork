# 신규 촬영본이 오면 저용량 대리 영상을 만든다. 변환 도구가 있을 때만 한다.

import shutil
import subprocess
from datetime import datetime
from pathlib import Path

import importlib.util

from config.불러오기 import 상대이름, 작업경로


def _모드():
    경로 = Path(__file__).resolve().parents[1] / "mode-switch" / "모드.py"
    스펙 = importlib.util.spec_from_file_location("모드전환", 경로)
    모듈 = importlib.util.module_from_spec(스펙)
    스펙.loader.exec_module(모듈)
    return 모듈


_마지막 = {"설명": ""}
영상확장 = {".mov", ".mp4", ".mxf", ".mts", ".m2ts", ".avi", ".mkv", ".r3d", ".braw"}


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


def _인코더():
    도구 = shutil.which("ffmpeg")
    if not 도구:
        return ""
    try:
        출력 = subprocess.check_output(
            [도구, "-hide_banner", "-encoders"],
            text=True,
            stderr=subprocess.DEVNULL,
            timeout=15,
        )
    except (OSError, subprocess.SubprocessError):
        return ""
    if "prores_ks" in 출력:
        return "프로레스"
    if "libx264" in 출력:
        return "저용량"
    return ""


def _만들기(도구, 원본, 출력, 방식):
    if 방식 == "프로레스":
        명령 = [
            도구, "-y", "-i", str(원본),
            "-vf", "scale=-2:720",
            "-c:v", "prores_ks", "-profile:v", "0",
            "-c:a", "pcm_s16le",
            str(출력),
        ]
    else:
        명령 = [
            도구, "-y", "-i", str(원본),
            "-vf", "scale=-2:720",
            "-c:v", "libx264", "-preset", "veryfast", "-crf", "28",
            "-c:a", "aac", "-movflags", "+faststart",
            str(출력),
        ]
    subprocess.run(명령, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True, timeout=3600)


def 점검(설정):
    모드 = _모드()
    상대 = 상대이름(설정, "영상신규촬영") or "아직 없음"
    결과 = {
        "도구": "있음" if 도구있음() else "없음",
        "받을폴더": "아직 없음",
        "대리폴더": "아직 없음",
        "상대이름": 상대,
        "설명": "",
    }
    if 모드.일시정지():
        결과["설명"] = "예배·행사 모드라 대리 영상을 잠시 멈췄습니다"
        _이유기록(결과["설명"])
        return 결과
    받을 = 작업경로(설정, "영상신규촬영")
    대리 = 작업경로(설정, "영상대리")
    if not 받을 or not 대리:
        결과["설명"] = "촬영본 폴더 경로가 아직 없어 대리 영상을 만들지 않습니다"
        _이유기록(결과["설명"])
        return 결과
    결과["받을폴더"] = "경로 있음"
    결과["대리폴더"] = "경로 있음"
    도구 = shutil.which("ffmpeg")
    if not 도구:
        결과["설명"] = "에프엠펙이 없습니다"
        _이유기록(결과["설명"])
        return 결과
    방식 = _인코더()
    if not 방식:
        결과["설명"] = "에프엠펙에 쓸 인코더가 없습니다"
        _이유기록(결과["설명"])
        return 결과
    원본폴더 = Path(받을)
    출력폴더 = Path(대리)
    if not 원본폴더.is_dir():
        결과["설명"] = "촬영본 폴더가 아직 없습니다"
        _이유기록(결과["설명"])
        return 결과
    출력폴더.mkdir(parents=True, exist_ok=True)
    만든수 = 0
    for 파일 in sorted(원본폴더.iterdir()):
        if not 파일.is_file() or 파일.suffix.lower() not in 영상확장:
            continue
        if 파일.stem.endswith("_대리"):
            continue
        출력 = 출력폴더 / (파일.stem + "_대리.mov")
        if 출력.is_file() and 출력.stat().st_mtime >= 파일.stat().st_mtime:
            continue
        try:
            _만들기(도구, 파일, 출력, 방식)
            만든수 += 1
            _기록("대리 영상을 만들었습니다: " + 파일.name)
        except (OSError, subprocess.SubprocessError):
            _기록("대리 영상을 만들지 못했습니다: " + 파일.name)
    if 만든수:
        결과["설명"] = "대리 영상 " + str(만든수) + "개를 만들었습니다"
    else:
        결과["설명"] = "새로 만들 촬영본이 없습니다"
    _마지막["설명"] = 결과["설명"]
    return 결과
