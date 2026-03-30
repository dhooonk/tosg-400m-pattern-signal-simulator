"""
Excel PG Signal 임포터

Excel 파일의 각 시트를 하나의 모델로 읽고,
ModelStore에 필요한 ModelData 리스트로 반환합니다.

Excel 시트 양식 (excel_format_generator.py로 생성 가능):
  [신호 데이터 영역] (1~37행)
    A1=NUM, B1=NAME, C1=SIG TYPE, D1=SIG MODE, E1=INV
    F1=V1(V), G1=V2(V), H1=V3(V), I1=V4(V)
    J1=DELAY(us), K1=PERIOD(us), L1=WIDTH(us), M1=LENGTH(us), N1=AREA(us)
    A2~A37: S01~S36 (최대 36 신호)

  [SyncData 영역] (P/Q열, 2~4행)
    P2=SyncData(us),  Q2=값
    P3=Frequency(Hz), Q3=값
    P4=SyncCounter,   Q4=값

  [패턴 데이터 영역] (39행 이후)
    A39: '=== PATTERN DATA ===' 구분자
    A40=PTN_NO, B40=NAME,
    C~F=R_V1..V4, G~J=G_V1..V4, K~N=B_V1..V4, O~R=W_V1..V4, S40=TYPE

반환: List[ModelData]  (ModelStore.set_models()에 직접 사용)
"""

import os
from typing import List


def import_excel_all_models(filepath: str) -> list:
    """
    Excel 파일 전체 시트를 읽어 ModelData 리스트 반환

    각 시트를 독립적인 모델로 처리합니다.
    시트 이름이 모델 이름으로 사용됩니다.

    Args:
        filepath: .xlsx 파일 경로

    Returns:
        List[ModelData]: 파싱된 모델 데이터 리스트

    Raises:
        ImportError: openpyxl이 설치되지 않은 경우
        FileNotFoundError: 파일이 존재하지 않는 경우
    """
    try:
        import openpyxl
    except ImportError:
        raise ImportError("openpyxl이 필요합니다. 'pip install openpyxl'을 실행하세요.")

    from model_store import ModelData
    from signal_model import Signal

    if not os.path.exists(filepath):
        raise FileNotFoundError(f"파일을 찾을 수 없습니다: {filepath}")

    wb = openpyxl.load_workbook(filepath, data_only=True)
    result_models: List[ModelData] = []

    # 신호 색상 기본 팔레트 (matplotlib 기본 색상 기반)
    default_colors = [
        '#1f77b4', '#ff7f0e', '#2ca02c', '#d62728', '#9467bd',
        '#8c564b', '#e377c2', '#7f7f7f', '#bcbd22', '#17becf',
        '#aec7e8', '#ffbb78', '#98df8a', '#ff9896', '#c5b0d5',
    ]

    for sheet_idx, ws in enumerate(wb.worksheets):
        model_name = ws.title
        model_num  = f"{sheet_idx + 1:03d}"

        # ── 안전한 셀 값 읽기 헬퍼 함수 ──────────────────────
        def _safe_float(cell_val, default=0.0):
            """셀 값을 float로 변환 (실패 시 default 반환)"""
            try:
                return float(cell_val) if cell_val is not None else default
            except (ValueError, TypeError):
                return default

        def _safe_int(cell_val, default=0):
            """셀 값을 int로 변환 (실패 시 default 반환)"""
            try:
                return int(cell_val) if cell_val is not None else default
            except (ValueError, TypeError):
                return default

        # ── SyncData / Frequency / SyncCounter 읽기 (Q열) ─────
        # P열: 라벨명, Q열: 값
        sync_data_us = _safe_float(ws['Q2'].value)   # SyncData (us)
        freq_hz      = _safe_float(ws['Q3'].value)   # Frequency (Hz)
        sync_cntr    = _safe_int(ws['Q4'].value)     # SyncCounter

        # 한쪽 값이 없으면 다른 값으로 계산
        if freq_hz <= 0 and sync_data_us > 0:
            freq_hz = 1_000_000.0 / sync_data_us
        elif sync_data_us <= 0 and freq_hz > 0:
            sync_data_us = 1_000_000.0 / freq_hz
        # 둘 다 없으면 기본값 60Hz
        if freq_hz <= 0:
            freq_hz = 60.0
        if sync_data_us <= 0:
            sync_data_us = 1_000_000.0 / freq_hz

        # ── 신호 데이터 읽기 (2~37행, S01~S36) ──────────────────
        signals: List[Signal] = []

        for row_idx in range(2, 38):
            row = ws[row_idx]
            if not row or row[0].value is None:
                continue

            # A열: NUM (S01, S02, ...)
            num_val = str(row[0].value).strip()
            if not num_val.upper().startswith('S'):
                continue

            # B열: NAME (빈 경우 NUM 값 사용)
            name_val = (str(row[1].value).strip()
                        if len(row) > 1 and row[1].value else '')
            if not name_val:
                name_val = num_val  # 빈 이름이면 S01 등으로 대체

            def col(i, dv=0.0):
                """열 인덱스로 float 값 읽기"""
                v = row[i].value if len(row) > i else None
                try:
                    return float(v) if v is not None else dv
                except (ValueError, TypeError):
                    return dv

            def icol(i, dv=0):
                """열 인덱스로 int 값 읽기"""
                v = row[i].value if len(row) > i else None
                try:
                    return int(v) if v is not None else dv
                except (ValueError, TypeError):
                    return dv

            # 신호 인덱스 계산 (S01→0, S02→1, ...)
            try:
                num_idx = int(num_val[1:]) - 1
            except (ValueError, IndexError):
                num_idx = row_idx - 2
            color = default_colors[num_idx % len(default_colors)]

            # 열 순서: A=NUM, B=NAME, C=SIGTYPE, D=SIGMODE, E=INV
            #          F=V1, G=V2, H=V3, I=V4
            #          J=DELAY, K=PERIOD, L=WIDTH, M=LENGTH, N=AREA
            sig = Signal(
                name      = name_val,
                sig_type  = str(icol(2, 0)),    # C: SIG TYPE
                sig_mode  = icol(3, 0),         # D: SIG MODE
                inversion = icol(4, 0),         # E: INV
                v1 = col(5),                    # F: V1
                v2 = col(6),                    # G: V2
                v3 = col(7),                    # H: V3
                v4 = col(8),                    # I: V4
                delay  = col(9),                # J: DELAY
                period = col(10),               # K: PERIOD
                width  = col(11),               # L: WIDTH
                color  = color,
                visible= True,
            )
            # NUM 및 확장 필드 저장 (OTD 내보내기에서 활용)
            sig._num    = num_val
            sig._length = col(12)               # M: LENGTH
            sig._area   = col(13)               # N: AREA
            signals.append(sig)

        # ── 패턴 데이터 읽기 ('=== PATTERN DATA ===' 구분자 이후) ──
        patterns = []
        ptn_start_row = None

        # 39행부터 구분자 행 검색
        for row_idx in range(39, ws.max_row + 1):
            cell_a = ws.cell(row_idx, 1).value
            if cell_a is not None and str(cell_a).strip().startswith('==='):
                # 구분자 다음 행이 헤더(+1), 그 다음이 데이터(+2)
                ptn_start_row = row_idx + 2
                break

        if ptn_start_row:
            for row_idx in range(ptn_start_row, ws.max_row + 1):
                # A~S열 (1~19번) 읽기
                row_vals = [ws.cell(row_idx, c).value for c in range(1, 20)]
                if row_vals[0] is None:
                    continue
                try:
                    ptn_no = int(row_vals[0])
                except (ValueError, TypeError):
                    continue

                ptn_name = (str(row_vals[1]).strip()
                            if row_vals[1] else f'PTN{ptn_no:02d}')

                def pv(i):
                    """패턴 행의 i번째 값을 float로 변환"""
                    try:
                        return float(row_vals[i]) if row_vals[i] is not None else 0.0
                    except (ValueError, TypeError):
                        return 0.0

                def ptype():
                    """패턴 타입 (S열=19번째) int 변환"""
                    try:
                        return int(row_vals[18]) if row_vals[18] is not None else 0
                    except (ValueError, TypeError):
                        return 0

                patterns.append({
                    'ptn_no': ptn_no,
                    'name':   ptn_name,
                    'r_v1': pv(2),  'r_v2': pv(3),  'r_v3': pv(4),  'r_v4': pv(5),
                    'g_v1': pv(6),  'g_v2': pv(7),  'g_v3': pv(8),  'g_v4': pv(9),
                    'b_v1': pv(10), 'b_v2': pv(11), 'b_v3': pv(12), 'b_v4': pv(13),
                    'w_v1': pv(14), 'w_v2': pv(15), 'w_v3': pv(16), 'w_v4': pv(17),
                    'ptn_type': ptype(),
                })

        # ModelData 생성 및 리스트에 추가
        model = ModelData(
            model_num    = model_num,
            name         = model_name,
            frequency_hz = freq_hz,
            sync_data_us = sync_data_us,
            sync_cntr    = sync_cntr,
            signals      = signals,
            patterns     = patterns,
        )
        result_models.append(model)

    wb.close()
    return result_models
