import os
import subprocess
import shutil
from pathlib import Path
from datetime import datetime
import pytest

# 프로젝트 루트 경로 설정
PROJECT_ROOT = Path(__file__).parent.parent.resolve()
SCRIPTS_DIR = PROJECT_ROOT / "scripts"
OUTPUT_DIR = PROJECT_ROOT / "output"
LOGS_DIR = PROJECT_ROOT / "logs"

@pytest.fixture
def clean_environment():
    """
    테스트 격리를 위해 임시 출력/로그 디렉토리 또는 오늘자 산출물 격리 환경 제공
    """
    today_str = datetime.now().strftime("%Y-%m-%d")
    daily_report_dir = OUTPUT_DIR / "reports" / "daily" / today_str
    backup_dir = None
    
    # 만약 기존에 당일자 리포트 폴더가 이미 있으면 백업해두고 격리
    if daily_report_dir.exists():
        backup_dir = daily_report_dir.parent / f"{today_str}_backup_test"
        if backup_dir.exists():
            shutil.rmtree(backup_dir)
        shutil.move(daily_report_dir, backup_dir)
        
    yield daily_report_dir
    
    # 테스트 종료 후 원래 상태 복구 및 정리
    if daily_report_dir.exists():
        shutil.rmtree(daily_report_dir)
        
    if backup_dir and backup_dir.exists():
        shutil.move(backup_dir, daily_report_dir)

def test_scheduler_pipeline_full_cycle(clean_environment):
    """
    [통합 무결성 검증 테스트]
    1. scripts/run_scheduled_report.sh가 에러 없이 성공적으로 실행되는지 (Exit Code 0)
    2. 생성된 일간 보고서 및 마크다운/JSON 산출물의 폴더/파일 무결성이 기준을 통과하는지
    단일 트랜잭션 내에서 연속 검증하여 Fixture Teardown으로 인한 상태 소실을 방지합니다.
    """
    script_path = SCRIPTS_DIR / "run_scheduled_report.sh"
    
    # 셸 스크립트 실행 권한 부여
    os.chmod(script_path, 0o755)
    
    # 최소화된 환경 변수 맵 생성 (launchd 모방)
    minimal_env = {
        "PATH": "/usr/bin:/bin:/usr/sbin:/sbin:/usr/local/bin",
        "HOME": os.environ.get("HOME", "/Users/sookbunlee"),
        "USER": os.environ.get("USER", "sookbunlee"),
    }
    
    # 만약 기존 .env 파일이 있다면 환경 로드를 위해 필요한 설정 제공
    if (PROJECT_ROOT / ".env").exists():
        minimal_env["OPENAI_API_KEY"] = os.environ.get("OPENAI_API_KEY", "")
    
    # 1. 백그라운드 스크립트 격리 실행 및 종료 코드 검증
    process = subprocess.run(
        ["/bin/bash", str(script_path)],
        cwd=str(PROJECT_ROOT),
        env=minimal_env,
        capture_output=True,
        text=True
    )
    
    assert process.returncode == 0, f"스크립트 실행 실패!\nSTDOUT: {process.stdout}\nSTDERR: {process.stderr}"
    
    # 2. 산출물 구조적 존재 여부 및 마크다운 무결성 검증
    today_str = datetime.now().strftime("%Y-%m-%d")
    report_path = OUTPUT_DIR / "reports" / "daily" / today_str
    
    assert report_path.is_dir(), f"일간 분석 보고서 폴더가 생성되지 않았습니다: {report_path}"
    
    sector_report = report_path / "01_sector_report.md"
    stocks_dir = report_path / "02_stocks"
    final_report = report_path / "03_final_report.md"
    
    assert sector_report.is_file(), "01_sector_report.md 파일이 존재하지 않습니다."
    assert stocks_dir.is_dir(), "02_stocks 종목별 폴더가 존재하지 않습니다."
    assert final_report.is_file(), "03_final_report.md 파일이 존재하지 않습니다."
    
    # 마크다운 내용 체크
    with open(final_report, "r", encoding="utf-8") as f:
        content = f.read()
        assert content.strip().startswith("#"), "보고서가 올바른 마크다운 제목(#) 포맷으로 시작하지 않습니다."
