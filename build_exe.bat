@echo off
REM ========================================
REM TOSG Pattern Viewer - EXE 빌드 스크립트
REM ========================================

echo ========================================
echo TOSG Pattern Viewer EXE 빌드 시작
echo ========================================
echo.

REM 1. 이전 빌드 파일 정리
echo [1/5] 이전 빌드 파일 정리 중...
if exist build rmdir /s /q build
if exist dist rmdir /s /q dist
echo 완료!
echo.

REM 2. Python 버전 확인
echo [2/5] Python 버전 확인 중...
python --version
if errorlevel 1 (
    echo 오류: Python이 설치되어 있지 않습니다!
    echo Python 3.8 이상을 설치하세요.
    pause
    exit /b 1
)
echo.

REM 3. 필요한 패키지 확인
echo [3/5] 필요한 패키지 확인 중...
python -c "import py2exe" 2>nul
if errorlevel 1 (
    echo py2exe가 설치되어 있지 않습니다.
    echo 설치 중...
    pip install py2exe
    if errorlevel 1 (
        echo 오류: py2exe 설치 실패!
        pause
        exit /b 1
    )
)
echo py2exe 확인 완료!
echo.

REM 4. EXE 빌드 실행
echo [4/5] EXE 파일 빌드 중...
echo 이 작업은 1-3분 정도 소요됩니다...
python setup.py py2exe
if errorlevel 1 (
    echo.
    echo 오류: 빌드 실패!
    echo 위의 에러 메시지를 확인하세요.
    pause
    exit /b 1
)
echo.

REM 5. 빌드 결과 확인
echo [5/5] 빌드 결과 확인 중...
if exist dist\TOSG-Pattern-Viewer.exe (
    echo.
    echo ========================================
    echo 빌드 성공!
    echo ========================================
    echo.
    echo 생성된 파일 위치: dist\TOSG-Pattern-Viewer.exe
    echo.
    echo 다음 단계:
    echo 1. dist 폴더로 이동
    echo 2. TOSG-Pattern-Viewer.exe 실행하여 테스트
    echo 3. 문제없으면 dist 폴더 전체를 배포
    echo.
) else (
    echo.
    echo 오류: EXE 파일이 생성되지 않았습니다!
    echo setup.py 파일을 확인하세요.
    pause
    exit /b 1
)

REM 6. 배포 준비 안내
echo ========================================
echo 배포 준비 방법
echo ========================================
echo.
echo 1. dist 폴더를 "TOSG-Pattern-Viewer-v1.0"으로 이름 변경
echo 2. README.txt 파일 추가
echo 3. 폴더를 ZIP으로 압축
echo 4. 다른 Windows PC에서 테스트
echo.

pause
