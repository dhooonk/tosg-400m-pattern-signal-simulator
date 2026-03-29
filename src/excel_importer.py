"""
Excel PG Signal 임포터 v2 (피드백 6)

각 시트 = 1개 모델.
전체 시트를 읽어 List[ModelData]로 반환합니다.

시트 양식:
  A1=NUM, B1=NAME, ..., N1=AREA
  A2~A37: S01~S36 신호 데이터
  P2=SyncData(us), Q2=값
  P3=Frequency(Hz), Q3=값
  P4=SyncCounter,   Q4=값
  
  A39=구분자, A40=패턴헤더, A41~=패턴데이터
  A열=PTN_NO, B열=NAME, C~F=R V1-V4, G~J=G V1-V4, K~N=B V1-V4, O~R=W V1-V4, S열=TYPE
"""

import os
from typing import List, Optional


def import_excel_all_models(filepath: str) -> 'List':
    """
    Excel 파일 전체 시트를 읽어 ModelData 리스트 반환
    
    Args:
        filepath: .xlsx 파일 경로
        
    Returns:
        List[ModelData]: 모든 시트에서 파싱된 모델 데이터
    """
    try:
        import openpyxl
    except ImportError:
        raise ImportError("openpyxl이 필요합니다.")

    from model_store import ModelData
    from signal_model import Signal

    if not os.path.exists(filepath):
        raise FileNotFoundError(f"파일을 찾을 수 없습니다: {filepath}")

    wb = openpyxl.load_workbook(filepath, data_only=True)
    result_models: List[ModelData] = []

    default_colors = [
        '#1f77b4', '#ff7f0e', '#2ca02c', '#d62728', '#9467bd',
        '#8c564b', '#e377c2', '#7f7f7f', '#bcbd22', '#17becf',
        '#aec7e8', '#ffbb78', '#98df8a', '#ff9896', '#c5b0d5',
    ]

    for sheet_idx, ws in enumerate(wb.worksheets):
        model_name  = ws.title
        model_num   = f"{sheet_idx+1:03d}"

        # ── SyncData / Frequency 읽기 ─────────────────────────
        def _safe_float(cell_val, default=0.0):
            try: return float(cell_val) if cell_val is not None else default
            except: return default
        def _safe_int(cell_val, default=0):
            try: return int(cell_val) if cell_val is not None else default
            except: return default

        sync_data_us = _safe_float(ws['Q2'].value)
        freq_hz      = _safe_float(ws['Q3'].value)
        sync_cntr    = _safe_int(ws['Q4'].value)

        if freq_hz <= 0 and sync_data_us > 0:
            freq_hz = 1_000_000.0 / sync_data_us
        elif sync_data_us <= 0 and freq_hz > 0:
            sync_data_us = 1_000_000.0 / freq_hz
        if freq_hz <= 0:
            freq_hz = 60.0
        if sync_data_us <= 0:
            sync_data_us = 1_000_000.0 / freq_hz

        # ── 신호 데이터 (2~37행) ──────────────────────────────
        signals: List[Signal] = []
        for row_idx in range(2, 38):
            row = ws[row_idx]
            if not row or row[0].value is None:
                continue
            num_val = str(row[0].value).strip()
            if not num_val.upper().startswith('S'):
                continue
            name_val = str(row[1].value).strip() if len(row) > 1 and row[1].value else ''
            if not name_val:
                continue

            def col(i, dv=0.0):
                v = row[i].value if len(row) > i else None
                try: return float(v) if v is not None else dv
                except: return dv
            def icol(i, dv=0):
                v = row[i].value if len(row) > i else None
                try: return int(v) if v is not None else dv
                except: return dv

            try:
                num_idx = int(num_val[1:]) - 1
            except:
                num_idx = row_idx - 2
            color = default_colors[num_idx % len(default_colors)]

            sig = Signal(
                name       = name_val,
                sig_type   = str(icol(2, 0)),
                sig_mode   = icol(3, 0),
                inversion  = icol(4, 0),
                v1 = col(5), v2 = col(6), v3 = col(7), v4 = col(8),
                delay  = col(9),
                period = col(10),
                width  = col(11),
                color  = color,
                visible= True,
            )
            # 확장 필드
            sig._num    = num_val
            sig._length = col(12)
            sig._area   = col(13)
            signals.append(sig)

        # ── 패턴 데이터 (40행 이후) ───────────────────────────
        patterns = []
        ptn_start_row = None
        for row_idx in range(39, ws.max_row + 1):
            cell_a = ws.cell(row_idx, 1).value
            if cell_a is not None and str(cell_a).strip().startswith('==='):
                ptn_start_row = row_idx + 2  # 헤더 행(+1) 다음 데이터행(+2)
                break

        if ptn_start_row:
            for row_idx in range(ptn_start_row, ws.max_row + 1):
                row_vals = [ws.cell(row_idx, c).value for c in range(1, 20)]
                if row_vals[0] is None:
                    continue
                try:
                    ptn_no = int(row_vals[0])
                except:
                    continue
                ptn_name = str(row_vals[1]).strip() if row_vals[1] else f'PTN{ptn_no:02d}'

                def pv(i):
                    try: return float(row_vals[i]) if row_vals[i] is not None else 0.0
                    except: return 0.0
                def ptype():
                    try: return int(row_vals[18]) if row_vals[18] is not None else 0
                    except: return 0

                patterns.append({
                    'ptn_no': ptn_no, 'name': ptn_name,
                    'r_v1': pv(2), 'r_v2': pv(3), 'r_v3': pv(4), 'r_v4': pv(5),
                    'g_v1': pv(6), 'g_v2': pv(7), 'g_v3': pv(8), 'g_v4': pv(9),
                    'b_v1': pv(10), 'b_v2': pv(11), 'b_v3': pv(12), 'b_v4': pv(13),
                    'w_v1': pv(14), 'w_v2': pv(15), 'w_v3': pv(16), 'w_v4': pv(17),
                    'ptn_type': ptype(),
                })

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
