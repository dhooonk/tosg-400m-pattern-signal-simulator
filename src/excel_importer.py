"""
Excel PG Signal 파일 임포터
사용자가 작성하는 PG Signal 엑셀 파일을 파싱하여 Signal 객체 리스트로 변환합니다.

엑셀 파일 구조:
  1행  : 헤더 (열 이름)
  A열  : NUM (S01~S32)
  B열  : 신호 이름
  C열  : SIG TYPE (0~6)
  D열  : SIG MODE (0~4)
  E열  : INVERSION (0/1)
  F~I열: V1~V4 (V 단위)
  J열  : DELAY (us)
  K열  : PERIOD (us)
  L열  : WIDTH (us)
  M열  : LENGTH (us)
  N열  : AREA (us)

  P2:Q4 영역:
    P2='SyncData', Q2=SyncData 값 (us 단위, 엑셀에서 직접 입력)
    P3='Frequency', Q3=주파수 (Hz)
    P4='SyncCounter', Q4=카운터 값
"""

import os
from typing import List, Tuple, Optional, Dict


class ExcelImportResult:
    """Excel 임포트 결과 컨테이너"""
    def __init__(self):
        self.signals: List[dict] = []   # Signal.from_dict() 용 딕셔너리 리스트
        self.sync_data_us: float = 0.0   # 1프레임 길이 (us)
        self.frequency_hz: float = 0.0   # 주파수 (Hz)
        self.sync_counter: int = 0
        self.model_name: str = ""
        self.errors: List[str] = []      # 파싱 경고/오류 메시지


def import_excel_pg_signals(filepath: str) -> ExcelImportResult:
    """
    PG Signal 엑셀 파일을 읽어 ExcelImportResult 반환
    
    Args:
        filepath: .xlsx 파일 경로
        
    Returns:
        ExcelImportResult: 파싱된 신호 데이터 및 동기화 정보
        
    Raises:
        ImportError: openpyxl이 설치되지 않은 경우
        FileNotFoundError: 파일이 없는 경우
    """
    try:
        import openpyxl
    except ImportError:
        raise ImportError("openpyxl 라이브러리가 필요합니다. 'pip install openpyxl'을 실행하세요.")

    if not os.path.exists(filepath):
        raise FileNotFoundError(f"파일을 찾을 수 없습니다: {filepath}")

    result = ExcelImportResult()
    result.model_name = os.path.splitext(os.path.basename(filepath))[0]

    wb = openpyxl.load_workbook(filepath, data_only=True)
    ws = wb.active  # 첫 번째 시트 사용

    # ── P/Q 영역: SyncData / Frequency / SyncCounter 읽기 ──────
    try:
        sync_val   = ws['Q2'].value
        freq_val   = ws['Q3'].value
        scntr_val  = ws['Q4'].value

        if sync_val is not None:
            result.sync_data_us = float(sync_val)
        if freq_val is not None:
            result.frequency_hz = float(freq_val)
            # SyncData 가 없으면 주파수로 계산
            if result.sync_data_us == 0.0 and result.frequency_hz > 0:
                result.sync_data_us = 1_000_000.0 / result.frequency_hz
        elif result.sync_data_us > 0:
            result.frequency_hz = 1_000_000.0 / result.sync_data_us

        if scntr_val is not None:
            result.sync_counter = int(scntr_val)
    except Exception as e:
        result.errors.append(f"SyncData 읽기 실패: {e}")

    # ── A~N열: 신호 데이터 읽기 (2행부터) ──────────────────────
    # 색상 팔레트 (신호 번호 기반 순환)
    default_colors = [
        '#1f77b4', '#ff7f0e', '#2ca02c', '#d62728', '#9467bd',
        '#8c564b', '#e377c2', '#7f7f7f', '#bcbd22', '#17becf',
        '#aec7e8', '#ffbb78', '#98df8a', '#ff9896', '#c5b0d5',
    ]

    for row_idx, row in enumerate(ws.iter_rows(min_row=2, values_only=True), start=2):
        # A열 (index 0): NUM
        if not row or row[0] is None:
            continue   # 비어있는 행 건너뜀

        num_val = str(row[0]).strip()
        if not num_val.startswith('S') and not num_val.startswith('s'):
            continue   # S01~S32 형식이 아니면 건너뜀

        # B열: 신호 이름
        name_val = str(row[1]).strip() if len(row) > 1 and row[1] is not None else ""
        if not name_val:
            continue   # 신호 이름이 없으면 건너뜀

        def safe_int(val, default=0) -> int:
            try:
                return int(val) if val is not None else default
            except (ValueError, TypeError):
                return default

        def safe_float(val, default=0.0) -> float:
            try:
                return float(val) if val is not None else default
            except (ValueError, TypeError):
                return default

        sig_type  = safe_int(row[2] if len(row) > 2 else None,  0)
        sig_mode  = safe_int(row[3] if len(row) > 3 else None,  0)
        inversion = safe_int(row[4] if len(row) > 4 else None,  0)

        v1 = safe_float(row[5]  if len(row) > 5  else None, 0.0)
        v2 = safe_float(row[6]  if len(row) > 6  else None, 0.0)
        v3 = safe_float(row[7]  if len(row) > 7  else None, 0.0)
        v4 = safe_float(row[8]  if len(row) > 8  else None, 0.0)

        delay  = safe_float(row[9]  if len(row) > 9  else None, 0.0)   # J열
        period = safe_float(row[10] if len(row) > 10 else None, 0.0)   # K열
        width  = safe_float(row[11] if len(row) > 11 else None, 0.0)   # L열
        length = safe_float(row[12] if len(row) > 12 else None, 0.0)   # M열
        area   = safe_float(row[13] if len(row) > 13 else None, 0.0)   # N열

        # 색상: 번호에서 순환 선택
        try:
            num_idx = int(num_val[1:]) - 1  # S01→0
        except ValueError:
            num_idx = row_idx - 2
        color = default_colors[num_idx % len(default_colors)]

        sig_dict = {
            'name': name_val,
            'sig_type': str(sig_type),
            'sig_mode': sig_mode,
            'inversion': inversion,
            'v1': v1,
            'v2': v2,
            'v3': v3,
            'v4': v4,
            'delay': delay,
            'width': width,
            'period': period,
            'color': color,
            'visible': True,
            # 확장 필드
            'num': num_val,
            'length': length,
            'area': area,
        }
        result.signals.append(sig_dict)

    wb.close()
    return result
