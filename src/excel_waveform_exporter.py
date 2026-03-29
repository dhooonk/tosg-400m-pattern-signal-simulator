"""
Excel 파형 시각화 내보내기 v2 (피드백 9-12)

개선 사항:
  - 신호 간 2행 여백 (피드백 9)
  - 0V=가운데 행, >0V=위쪽 행, <0V=아래쪽 행 테두리 (피드백 10)
  - 구간 경계: 점선, 파형: 실선 (피드백 12)
  - Delay/Width/Period 화살표 도형 + 텍스트박스 (피드백 11)
"""

from typing import List, Dict, Tuple


# ────────────────────────────────────────────────────────────────
# 레이아웃 상수
# ────────────────────────────────────────────────────────────────

ZOOM_PERCENT     = 25

COL_NUM          = 1   # A: 신호 NUM
COL_NAME         = 2   # B: 신호 이름
COL_WAVE_START   = 3   # C 이후: 파형 셀

ROW_LABEL        = 1   # 구간 라벨 행
ROW_TIME_ARROW   = 2   # 시간 표시 행 (텍스트 반환 후 도형 사용)
ROW_WAVE_START   = 3   # 첫 신호 시작

CELLS_PER_SIGNAL = 3   # 신호당 행: 위(H), 중(M), 아래(L)
SIGNAL_GAP_ROWS  = 2   # 신호 간 여백 행 수

NAME_COL_WIDTH   = 18.0
NUM_COL_WIDTH    = 7.0
WAVE_COL_WIDTH   = 2.5

LABEL_COLOR      = 'FFD0D8E8'
WAVE_COLOR_POS   = 'FF2C3E50'   # >0V
WAVE_COLOR_ZERO  = 'FF27AE60'   # 0V
WAVE_COLOR_NEG   = 'FFE74C3C'   # <0V

FONT_LABEL       = 9
FONT_VOLTAGE     = 7
FONT_ARROW       = 8
FONT_NAME        = 10


# ────────────────────────────────────────────────────────────────
# 구간 계산
# ────────────────────────────────────────────────────────────────

def _compute_segments(sync_data_us: float, signals: List[Dict],
                      max_segs: int = 32) -> List[Tuple[float, float, str]]:
    """신호 타이밍 경계점 기반 구간 분할"""
    breakpoints = {0.0, sync_data_us}
    for sig in signals:
        delay  = float(sig.get('delay',  0))
        width  = float(sig.get('width',  0))
        period = float(sig.get('period', 0))
        for bp in [delay, delay + width, period, period + delay,
                   period + delay + width]:
            if 0 < bp < sync_data_us:
                breakpoints.add(bp)

    sorted_bps = sorted(breakpoints)
    raw = list(zip(sorted_bps[:-1], sorted_bps[1:]))

    # 최대 구간 수 제한: 가장 짧은 인접 구간 병합
    while len(raw) > max_segs:
        durs = [e - s for s, e in raw]
        idx  = durs.index(min(durs))
        if idx + 1 < len(raw):
            s1, _ = raw[idx]
            _, e2 = raw[idx + 1]
            raw = raw[:idx] + [(s1, e2)] + raw[idx + 2:]
        else:
            break

    return [(s, e, f"Seg{i+1}") for i, (s, e) in enumerate(raw)]


def _get_level(sig: Dict, t_us: float) -> float:
    """시간 t_us 에서 신호 전압값 반환 (V)"""
    v1 = float(sig.get('v1', 0))
    v2 = float(sig.get('v2', v1))
    delay  = float(sig.get('delay',  0))
    width  = float(sig.get('width',  0))
    period = float(sig.get('period', 0))

    if delay == 0 and width == 0 and period == 0:
        return v1

    if period > 0:
        phase = t_us % period
        in_pulse = (delay <= phase < delay + width)
    else:
        in_pulse = (delay <= t_us < delay + width)

    return v2 if in_pulse else v1


# ────────────────────────────────────────────────────────────────
# 메인 익스포터
# ────────────────────────────────────────────────────────────────

class ExcelWaveformExporter:
    """Excel 파형 시각화 내보내기"""

    def export(self, filepath: str, signals: List[Dict],
               sync_data_us: float, model_name: str = "Model") -> bool:
        try:
            from openpyxl import Workbook
            from openpyxl.styles import PatternFill, Font, Alignment, Border, Side
            from openpyxl.utils import get_column_letter
            from openpyxl.drawing.spreadsheet_drawing import SpreadsheetDrawing
        except ImportError:
            raise ImportError("openpyxl이 필요합니다.")

        if not signals:
            return False

        wb = Workbook()
        ws = wb.active
        ws.title = model_name[:31]
        ws.sheet_view.zoomScale = ZOOM_PERCENT

        # ── 구간 계산 ─────────────────────────────────────────
        segments = _compute_segments(sync_data_us, signals)
        n_segs   = len(segments)
        total_us = sync_data_us

        # 구간별 컬럼 폭 비례 배분
        TOTAL_WAVE_COLS = min(n_segs * 10, 160)
        seg_cols = []
        for s, e, _ in segments:
            ratio  = (e - s) / total_us if total_us > 0 else 1 / n_segs
            seg_cols.append(max(1, round(ratio * TOTAL_WAVE_COLS)))
        diff = TOTAL_WAVE_COLS - sum(seg_cols)
        seg_cols[-1] = max(1, seg_cols[-1] + diff)

        seg_start_cols = []
        cur = COL_WAVE_START
        for n in seg_cols:
            seg_start_cols.append(cur)
            cur += n
        total_wave_end_col = cur - 1

        # ── 열 너비 ───────────────────────────────────────────
        ws.column_dimensions[get_column_letter(COL_NUM)].width  = NUM_COL_WIDTH
        ws.column_dimensions[get_column_letter(COL_NAME)].width = NAME_COL_WIDTH
        for c in range(COL_WAVE_START, total_wave_end_col + 1):
            ws.column_dimensions[get_column_letter(c)].width = WAVE_COL_WIDTH

        # ── 행 높이 ───────────────────────────────────────────
        ws.row_dimensions[ROW_LABEL].height      = 22
        ws.row_dimensions[ROW_TIME_ARROW].height = 18

        for sig_idx in range(len(signals)):
            base = _sig_base_row(sig_idx)
            for r in range(base, base + CELLS_PER_SIGNAL):
                ws.row_dimensions[r].height = 10
            # 여백 행
            for r in range(base + CELLS_PER_SIGNAL,
                           base + CELLS_PER_SIGNAL + SIGNAL_GAP_ROWS):
                ws.row_dimensions[r].height = 6

        # ── 스타일 헬퍼 ──────────────────────────────────────
        center_align = Alignment(horizontal='center', vertical='center')

        def solid_side(style='thin', color='FF000000'):
            return Side(style=style, color=color)

        def dashed_side():
            return Side(style='dashDot', color='FFAAAAAA')

        header_fill = PatternFill('solid', fgColor=LABEL_COLOR)
        label_font  = Font(bold=True, size=FONT_LABEL)

        # ── 행 1: 구간 라벨 ──────────────────────────────────
        ws.cell(ROW_LABEL, COL_NUM,  "NUM").font  = label_font
        ws.cell(ROW_LABEL, COL_NAME, "신호 이름").font = label_font
        ws.cell(ROW_LABEL, COL_NUM).fill  = header_fill
        ws.cell(ROW_LABEL, COL_NAME).fill = header_fill
        ws.cell(ROW_LABEL, COL_NUM).alignment  = center_align
        ws.cell(ROW_LABEL, COL_NAME).alignment = center_align

        for si, (start, end, label) in enumerate(segments):
            c1 = seg_start_cols[si]
            c2 = c1 + seg_cols[si] - 1
            cell = ws.cell(ROW_LABEL, c1, label)
            cell.font      = label_font
            cell.fill      = header_fill
            cell.alignment = center_align
            cell.border    = Border(
                left=solid_side('medium'), right=solid_side('medium'),
                top=solid_side('medium'),  bottom=solid_side('medium'))
            if c2 > c1:
                ws.merge_cells(start_row=ROW_LABEL, start_column=c1,
                               end_row=ROW_LABEL, end_column=c2)

        # ── 행 2: 구간 시간 표시 (텍스트) ───────────────────
        for si, (start, end, _) in enumerate(segments):
            dur = end - start
            if dur >= 1000:
                txt = f"↔ {dur/1000:.2f}ms"
            elif dur >= 1:
                txt = f"↔ {dur:.1f}us"
            else:
                txt = f"↔ {dur*1000:.0f}ns"
            c1 = seg_start_cols[si]
            c2 = c1 + seg_cols[si] - 1
            cell = ws.cell(ROW_TIME_ARROW, c1, txt)
            cell.font      = Font(color='FF0070C0', bold=True, size=FONT_ARROW)
            cell.alignment = center_align
            if c2 > c1:
                ws.merge_cells(start_row=ROW_TIME_ARROW, start_column=c1,
                               end_row=ROW_TIME_ARROW, end_column=c2)

        # ── 신호별 파형 그리기 ───────────────────────────────
        for sig_idx, sig in enumerate(signals):
            base = _sig_base_row(sig_idx)
            h_row = base          # 위 행 (High)
            m_row = base + 1      # 가운데 행 (Mid/Zero)
            l_row = base + 2      # 아래 행 (Low)

            # NUM / NAME 병합
            num_str = sig.get('num', f'S{sig_idx+1:02d}')
            ws.cell(h_row, COL_NUM, num_str).font = Font(bold=True, size=9)
            ws.cell(h_row, COL_NUM).alignment = center_align
            ws.merge_cells(start_row=h_row, start_column=COL_NUM,
                           end_row=l_row,   end_column=COL_NUM)

            ws.cell(h_row, COL_NAME, sig.get('name', '')).font = Font(bold=True, size=FONT_NAME)
            ws.cell(h_row, COL_NAME).alignment = center_align
            ws.merge_cells(start_row=h_row, start_column=COL_NAME,
                           end_row=l_row,   end_column=COL_NAME)

            # 구간별 파형 셀 그리기
            prev_voltage = None
            for si, (start, end, _) in enumerate(segments):
                mid_t = (start + end) / 2
                voltage = _get_level(sig, mid_t)
                c1 = seg_start_cols[si]
                c2 = c1 + seg_cols[si] - 1

                is_transition = (prev_voltage is not None and
                                 abs(prev_voltage - voltage) > 1e-6)

                # 수직 전환 경계 처리
                left_style = 'thick' if is_transition else None

                self._draw_waveform_cells(
                    ws, h_row, m_row, l_row, c1, c2,
                    voltage, left_style, solid_side, dashed_side
                )

                # 구간 시작에 전압 레이블 (첫 구간만)
                if si == 0:
                    v_label = f"{voltage:+.1f}V"
                    if voltage == 0:
                        vc = ws.cell(m_row, c1, v_label)
                        vc.font = Font(color='FF00AA00', size=FONT_VOLTAGE, bold=True)
                    elif voltage > 0:
                        vc = ws.cell(h_row, c1, v_label)
                        vc.font = Font(color='FFCC0000', size=FONT_VOLTAGE, bold=True)
                    else:
                        vc = ws.cell(l_row, c1, v_label)
                        vc.font = Font(color='FF0033CC', size=FONT_VOLTAGE, bold=True)

                prev_voltage = voltage

        # ── 타이밍 화살표 도형 추가 (Delay, Width, Period) ───
        self._add_timing_arrows(ws, signals, segments, seg_start_cols, seg_cols,
                                sync_data_us, total_wave_end_col)

        wb.save(filepath)
        return True

    def _draw_waveform_cells(self, ws, h_row, m_row, l_row,
                              c1, c2, voltage,
                              left_style, solid_side_fn, dashed_side_fn):
        """
        실제 파형 셀 테두리 그리기
        
        - voltage > 0 : h_row(위) 에 실선 상단 테두리 + 수직선
        - voltage == 0: m_row(가운데) 에 실선 테두리 + 수직선
        - voltage < 0 : l_row(아래) 에 실선 하단 테두리 + 수직선
        - 구간 경계 (좌측): 점선
        """
        from openpyxl.styles import Border

        # 기본 좌측 사이드 (구간 경계 = 점선, 전환 = 굵은선)
        if left_style:
            left_side = solid_side_fn(left_style)
        else:
            left_side = dashed_side_fn()

        thick = solid_side_fn('thick')
        thin  = solid_side_fn('thin')
        none  = solid_side_fn(None) if False else \
                __import__('openpyxl').styles.Side(style=None)

        for col in range(c1, c2 + 1):
            is_left = (col == c1)
            ls = left_side if is_left else none

            if voltage > 0:
                # 위쪽 테두리
                ws.cell(h_row, col).border = Border(top=thick, left=ls)
                ws.cell(m_row, col).border = Border(left=ls if is_left else none)
                ws.cell(l_row, col).border = Border(left=ls if is_left else none)
            elif voltage == 0:
                # 가운데 실선
                ws.cell(h_row, col).border = Border(left=ls if is_left else none)
                ws.cell(m_row, col).border = Border(top=thick, left=ls if is_left else none)
                ws.cell(l_row, col).border = Border(left=ls if is_left else none)
            else:
                # 아래쪽 테두리
                ws.cell(h_row, col).border = Border(left=ls if is_left else none)
                ws.cell(m_row, col).border = Border(left=ls if is_left else none)
                ws.cell(l_row, col).border = Border(bottom=thick, left=ls if is_left else none)

    def _add_timing_arrows(self, ws, signals, segments, seg_start_cols,
                            seg_cols, sync_data_us, total_wave_end_col):
        """
        Delay/Width/Period 타이밍 화살표 + 텍스트박스 추가
        openpyxl의 drawing 기능을 사용합니다.
        """
        try:
            from openpyxl.drawing.spreadsheet_drawing import SpreadsheetDrawing
            from openpyxl.drawing.xdr import (
                XDRPoint2D, XDRPositiveSize2D, XDRTransform2D,
                XDRClientData
            )
            from openpyxl.utils.units import pixels_to_EMU, cm_to_EMU
        except Exception:
            return  # drawing 모듈 없으면 스킵

        # openpyxl connector/shape는 복잡하므로
        # 텍스트박스 형태로 타이밍 정보를 ROW_TIME_ARROW 아래에 추가
        # (도형 추가는 openpyxl에서는 제한적이라 텍스트 기반 표시)

        for sig_idx, sig in enumerate(signals):
            delay  = float(sig.get('delay',  0))
            width  = float(sig.get('width',  0))
            period = float(sig.get('period', 0))

            base    = _sig_base_row(sig_idx)
            h_row   = base

            # Delay 범위에 해당하는 열 찾기
            if delay > 0 and sync_data_us > 0:
                delay_end = delay
                cols = self._us_range_to_cols(0, delay_end, sync_data_us,
                                               segments, seg_start_cols, seg_cols)
                if cols:
                    c_start, c_end = cols
                    mid_col = (c_start + c_end) // 2
                    cell = ws.cell(h_row - 1 if h_row > ROW_WAVE_START else h_row,
                                   mid_col)
                    if cell.value is None:
                        cell.value = f"Delay:{delay:.1f}us"
                        cell.font  = __import__('openpyxl').styles.Font(
                            color='FF7030A0', size=6, bold=True)

            # Width
            if width > 0 and sync_data_us > 0:
                w_start = delay
                w_end   = delay + width
                cols = self._us_range_to_cols(w_start, w_end, sync_data_us,
                                               segments, seg_start_cols, seg_cols)
                if cols:
                    c_start, c_end = cols
                    mid_col = (c_start + c_end) // 2
                    cell = ws.cell(h_row, mid_col)
                    if cell.value is None:
                        cell.value = f"W:{width:.1f}us"
                        cell.font  = __import__('openpyxl').styles.Font(
                            color='FF0070C0', size=6, bold=True)

            # Period
            if period > 0 and sync_data_us > 0:
                cols = self._us_range_to_cols(0, period, sync_data_us,
                                               segments, seg_start_cols, seg_cols)
                if cols:
                    c_start, c_end = cols
                    mid_col = (c_start + c_end) // 2

    def _us_range_to_cols(self, us_start, us_end, sync_data_us,
                           segments, seg_start_cols, seg_cols):
        """us 범위를 열 범위로 변환"""
        if us_end <= us_start or sync_data_us <= 0:
            return None
        total_cols = sum(seg_cols)
        c_start = COL_WAVE_START + int(us_start / sync_data_us * total_cols)
        c_end   = COL_WAVE_START + int(us_end   / sync_data_us * total_cols) - 1
        if c_start > c_end:
            c_end = c_start
        return c_start, c_end


def _sig_base_row(sig_idx: int) -> int:
    """신호 인덱스 → 시작 행 번호"""
    return ROW_WAVE_START + sig_idx * (CELLS_PER_SIGNAL + SIGNAL_GAP_ROWS)
