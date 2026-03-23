# -*- coding: utf-8 -*-
"""
TOSG Pattern Viewer - py2exe Setup Script
이 파일은 Python 프로그램을 Windows EXE 파일로 변환하는 설정 파일입니다.

사용 방법:
    python setup.py py2exe

또는 배치 파일 사용:
    build_exe.bat
"""

from distutils.core import setup
import py2exe
import sys
import os

# ========================================
# py2exe 옵션 설정
# ========================================
opts = {
    'py2exe': {
        # 명시적으로 포함할 모듈
        'includes': [
            'pandas',
            'numpy', 
            'matplotlib',
            'matplotlib.backends.backend_tkagg',  # matplotlib GUI 지원
            'openpyxl',
            'tkinter',  # GUI 라이브러리
        ],
        
        # 제외할 모듈 (충돌 방지 및 크기 최적화)
        'excludes': [
            'typing',      # 백포트 충돌 방지
            'unittest',    # 테스트 프레임워크 (불필요)
            'email',       # 이메일 라이브러리 (불필요)
            'http',        # HTTP 라이브러리 (불필요)
            'xml',         # XML 라이브러리 (불필요)
        ],
        
        # DLL 제외 (호환성 문제 방지)
        'dll_excludes': ['MSVCP90.dll'],
        
        # 번들링 옵션
        'bundle_files': 1,  # 1 = 모든 것을 하나의 EXE로, 2 = DLL 분리, 3 = 모든 파일 분리
        'compressed': True,  # 압축 활성화 (파일 크기 감소)
        
        # 최적화 레벨
        'optimize': 2,  # 0 = 최적화 없음, 1 = 기본, 2 = 최대
    }
}

# ========================================
# 데이터 파일 수집
# ========================================
data_files = []

def collect_files(source_dir, target_dir):
    """
    지정된 디렉토리의 모든 파일을 재귀적으로 수집
    
    Args:
        source_dir: 소스 디렉토리 경로
        target_dir: 대상 디렉토리 경로 (EXE 기준)
    """
    if not os.path.exists(source_dir):
        print(f"경고: {source_dir} 폴더를 찾을 수 없습니다.")
        return
    
    for root, dirs, files in os.walk(source_dir):
        for file in files:
            source_path = os.path.join(root, file)
            relative_path = os.path.relpath(root, source_dir)
            target_path = os.path.join(target_dir, relative_path)
            
            if relative_path == '.':
                target_path = target_dir
            
            # 중복 확인 및 추가
            found = False
            for i, (tgt, src_list) in enumerate(data_files):
                if tgt == target_path:
                    src_list.append(source_path)
                    found = True
                    break
            
            if not found:
                data_files.append((target_path, [source_path]))

# config 및 data 폴더의 파일들을 포함
print("데이터 파일 수집 중...")
collect_files('config', 'config')
collect_files('data', 'data')
print(f"총 {len(data_files)}개의 데이터 파일 그룹이 포함됩니다.")

# ========================================
# Setup 설정
# ========================================
setup(
    # 기본 정보
    name='TOSG-Pattern-Viewer',
    version='1.0.0',
    description='TOSG-400M Pattern Signal Viewer',
    author='TOSG',
    
    # Windows GUI 애플리케이션 설정
    windows=[{
        'script': 'main.py',                    # 메인 진입점
        'dest_base': 'TOSG-Pattern-Viewer',     # 생성될 EXE 파일 이름
        # 'icon_resources': [(1, 'icon.ico')],  # 아이콘 (있는 경우 주석 해제)
        'version': '1.0.0',
        'company_name': 'TOSG',
        'copyright': 'Copyright (C) 2025 TOSG',
        'description': 'TOSG Pattern Signal Viewer',
    }],
    
    # 콘솔 애플리케이션 (디버깅용, 필요시 주석 해제)
    # console=[{
    #     'script': 'main.py',
    #     'dest_base': 'TOSG-Pattern-Viewer-Debug',
    # }],
    
    # py2exe 옵션
    options=opts,
    
    # 데이터 파일
    data_files=data_files,
    
    # ZIP 파일 생성 안 함 (모든 것을 EXE에 포함)
    zipfile=None,
)

print("\n빌드 완료!")
print("생성된 파일: dist/TOSG-Pattern-Viewer.exe")
