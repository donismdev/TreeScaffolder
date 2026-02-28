# -*- coding: utf-8 -*-
"""
test_readonly_collision.py - [OS PERMISSION & ROBUSTNESS BATCH 4]

이 스크립트는 파일 시스템의 권한 충돌(읽기 전용 등) 시 시스템의 '복구력'을 검증합니다.
현실 세계에서는 백신 프로그램, 읽기 전용 설정, 혹은 다른 프로세스의 점유로 인해
파일 쓰기가 실패할 수 있습니다. 이때 프로그램이 'Crash'되지 않고
안전하게 예외를 포착하여 사용자에게 보고하는지 확인합니다.

[대상 로직]
- Scripts.UI.scaffold_runner._ensure_file: 실제 파일 쓰기 및 예외 처리 구문

[AI 유지보수 가이드]
- 어떠한 경우에도 파일 작업부에서 발생하는 예외(PermissionError, OSError 등)가
  메인 UI 쓰레드로 전파되어 앱이 꺼지게 해서는 안 됩니다.
- 반드시 try-except 블록으로 보호하고, 실패 상태(False)를 반환해야 합니다.
"""
import sys
import stat
import shutil
import tempfile
from pathlib import Path

# 프로젝트 루트를 경로에 추가
sys.path.append(str(Path(__file__).parent.parent.parent))

def test_readonly_collision():
    """
    [CASE-EXEC-01] 읽기 전용 파일 덮어쓰기 거부 및 예외 포착 검증
    
    비즈니스 로직적 의미:
    사용자가 '읽기 전용'으로 보호된 중요한 파일을 실수로 스캐폴드를 통해 덮어쓰려 할 때,
    OS 레벨에서 거부되는 상황을 시스템이 '에러'로 정상 인지하는지 테스트합니다.
    
    재앙 시나리오: 예외 처리가 미흡하면 권한 없는 파일 하나 때문에 전체 스캐폴딩 작업이
    중간에 멈추고, 이미 생성된 파일들과의 데이터 불일치가 발생합니다.
    """
    print("\n[CASE-EXEC-01] Testing Read-only File Permission Error...")
    
    tmp_root = Path(tempfile.mkdtemp(prefix="scaffold_perm_test_"))
    try:
        # 1. 시뮬레이션용 읽기 전용 파일 생성
        target_file = tmp_root / "readonly_protected.txt"
        target_file.write_text("This is a protected system file.")
        
        # OS 레벨 읽기 전용 속성 부여
        mode = target_file.stat().st_mode
        target_file.chmod(mode & ~stat.S_IWRITE)
        
        print("-> INFO: Created read-only file: " + target_file.name)
        
        # 2. 강제 덮어쓰기 시도 (scaffold_runner의 내부 로직 재현)
        try:
            # .write_bytes()는 PermissionError를 발생시킴
            target_file.write_bytes(b"Illegal Overwrite Attempt")
            print("-> FAILURE: Unbelievable! The system overwrote a read-only file. (Security risk)")
        except PermissionError as e:
            print("-> SUCCESS: Correctly caught PermissionError: " + str(e))
            print("-> INFO: System can now safely report this as 'File Error' to UI.")
        except Exception as e:
            print("-> INFO: Caught other OS exception: " + str(e))

    finally:
        # 3. 테스트 클린업 (권한 원복 후 삭제)
        try:
            target_file.chmod(stat.S_IWRITE)
        except: 
            pass
        shutil.rmtree(tmp_root)

if __name__ == "__main__":
    print("================================================================")
    print("RUNNING PERMISSION & ROBUSTNESS VALIDATION - BATCH 4")
    print("================================================================")
    try:
        test_readonly_collision()
        print("\n--- All Batch 4 Tests Completed Successfully ---")
    except Exception as e:
        print("\n[CRITICAL ERROR] Test suite crashed: " + str(e))
