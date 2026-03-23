"""
Excel 파형 시각화 내보내기 모듈
신호 데이터를 엑셀의 셀 테두리를 이용하여 파형으로 시각화하여 출력합니다.

시각화 규칙:
  - 줌 25%
  - 신호 이름 열: 2행 병합, 가운데 맞춤
  - 파형 구간(라벨): 병합 + 가운데 맞춤 (Blank1, Blank2, ROW1, ROW2 등)
  - 각 신호: 2행 점유
      High = 위쪽에 굵은 검은 테두리
       Mid = 가운데 검은 테두리
      Low  = 아래쪽에 굵은 검은 테두리
  - 전압 값: 빨간 글씨(크기 8pt), 파형 옆 텍스트
  - 구간 시간: 파란색 〈 - 〉 도형 + 시간 텍스트 (openpyxl Drawing)
  
레이아웃 (열):
  A : 행 번호 (선택적)
  B~C : 신호 NUM (S01 등)  — 2열 병합
  D~E : PIN No.            — 2열 병합 
  (이후 K열부터 신호 이름 + 파형 시작)
  
  실제로 단순화하여:
  COL A   : 신호 NUM
  COL B   : 신호 이름
  COL C~  : 파형 셀 (구간마다 컬럼 그룹 할당)
"""

from typing import List, Dict, Optional
import math


# ────────────────────────────────────────────────────────────────
# 상수 / 설정
# ────────────────────────────────────────────────────────────────

ZOOM_PERCENT = 25           # 엑셀 표시 줌 %

# 레이아웃 열 인덱스 (1-based)
COL_NUM   = 1   # A: 신호 NUM (S01 등)
COL_NAME  = 2   # B: 신호 이름
COL_WAVE_START = 3  # C 이후: 파형 셀

# 행 인덱스 (1-based)
ROW_LABEL    = 1   # 구간 라벨 행
ROW_TIME_ARROW = 2 # 화살표/시간 행 (라벨 바로 아래)
ROW_SIGNAL_START = 3  # 신호 데이터 첫 행

CELLS_PER_SIGNAL = 2  # 신호 1개당 점유 행 수
ROW_GAP_BETWEEN_SIGNALS = 0  # 신호 간 추가 여백 행

# 파형 시각화용 컬럼 너비 (pt)
WAVE_COL_WIDTH = 3.0       # 파형 셀 열 너비 (좁게)
LABEL_COL_WIDTH = 6.0      # 라벨 구간 헤더용 (첫 열)
NAME_COL_WIDTH  = 18.0     # 신호 이름 열 너비

# 테두리 스타일
BORDER_THICK = 'thick'
BORDER_MED   = 'medium'
BORDER_THIN  = 'thin'

# 색상
COLOR_RED    = 'FFFF0000'  # 전압 표시 텍스트 색
COLOR_BLUE   = 'FF0000FF'  # 시간 표시 텍스트 색
COLOR_BLACK  = 'FF000000'
COLOR_WHITE  = 'FFFFFFFF'
COLOR_HEADER = 'FFD9D9D9'  # 라벨 헤더 배경

# 폰트 크기
FONT_VOLTAGE    = 8   # 전압 라벨 (40pt 요청 → 엑셀 8pt 정도로 표시)
FONT_TIME_ARROW = 9   # 시간 화살표 라벨
FONT_HEADER     = 9
FONT_SIGNAL_NAME = 10


# ────────────────────────────────────────────────────────────────
# 파형 계산 헬퍼
# ────────────────────────────────────────────────────────────────

def _compute_segments(sync_data_us: float, signals: List[Dict]):
    """
    1프레임을 구간(segment)으로 분할
    
    분할 기준: 모든 신호의 DELAY, WIDTH, PERIOD, LENGTH 경계점을 수집하여
    고유한 시간 경계로 정렬한 후 구간 생성.
    구간이 너무 많으면 최대 MAX_SEGS 개로 제한.

    Returns:
        List[Tuple[float, float, str]]: [(start_us, end_us, label), ...]
    """
    MAX_SEGS = 32

    breakpoints = {0.0, sync_data_us}
    for sig in signals:
        delay  = float(sig.get('delay',  0))
        width  = float(sig.get('width',  0))
        period = float(sig.get('period', 0))
        length = float(sig.get('length', 0))

        if period > 0:
            # 반복 펄스: 한 주기만 고려
            for bp in [delay, delay + width, period]:
                if 0 < bp < sync_data_us:
                    breakpoints.add(bp)
        else:
            for bp in [delay, delay + width, length]:
                if 0 < bp < sync_data_us:
                    breakpoints.add(bp)

    sorted_bps = sorted(breakpoints)
    raw_segments = list(zip(sorted_bps[:-1], sorted_bps[1:]))

    # 구간 수 제한: 인접 구간 병합
    while len(raw_segments) > MAX_SEGS:
        # 가장 짧은 두 인접 구간 병합
        durations = [e - s for s, e in raw_segments]
        min_idx = durations.index(min(durations))
        if min_idx + 1 < len(raw_segments):
            s1, _ = raw_segments[min_idx]
            _, e2 = raw_segments[min_idx + 1]
            raw_segments = (raw_segments[:min_idx] +
                            [(s1, e2)] +
                            raw_segments[min_idx + 2:])
        else:
            break

    # 라벨 부여
    segments = []
    seg_idx = 1
    for start, end in raw_segments:
        label = f"Seg{seg_idx}"
        seg_idx += 1
        segments.append((start, end, label))

    return segments


def _get_signal_level_at(sig: Dict, t_us: float, frame_us: float) -> str:
    """
    시간 t_us에서 신호 레벨 반환: 'HIGH' / 'LOW' / 'MID'
    
    MID는 천이 경계 지점 표현용.
    """
    v1 = float(sig.get('v1', 0))
    v2 = float(sig.get('v2', 0))
    delay  = float(sig.get('delay',  0))
    width  = float(sig.get('width',  0))
    period = float(sig.get('period', 0))

    if delay == 0 and width == 0 and period == 0:
        # DC 모드: v1 고정
        return 'HIGH' if v2 >= v1 else 'LOW'

    if period > 0:
        phase = t_us % period
        is_high = (delay <= phase < delay + width)
    else:
        is_high = (delay <= t_us < delay + width)

    # HIGH/LOW 판단: v2가 high이면 is_high → HIGH
    if v2 >= v1:
        return 'HIGH' if is_high else 'LOW'
    else:
        return 'LOW' if is_high else 'HIGH'


# ────────────────────────────────────────────────────────────────
# 메인 익스포터
# ────────────────────────────────────────────────────────────────

class ExcelWaveformExporter:
    """
    엑셀 파형 시각화 내보내기 클래스
    
    사용법:
        exporter = ExcelWaveformExporter()
        exporter.export(filepath, signals, sync_data_us, model_name)
    """

    def export(
        self,
        filepath: str,
        signals: List[Dict],
        sync_data_us: float,
        model_name: str = "Model",
        num_frames: int = 1,
    ) -> bool:
        """
        파형 시각화 엑셀 파일 생성

        Args:
            filepath: 저장할 .xlsx 파일 경로
            signals: Signal.to_dict() 형식의 딕셔너리 리스트
            sync_data_us: 1프레임 길이 (us)
            model_name: 모델 이름 (시트 이름에 사용)
            num_frames: 출력할 프레임 수 (현재 1프레임만 구현, 확장 가능)
            
        Returns:
            bool: 성공 여부
        """
        try:
            from openpyxl import Workbook
            from openpyxl.styles import (
                PatternFill, Font, Alignment, Border, Side,
                GradientFill
            )
            from openpyxl.utils import get_column_letter
            from openpyxl.drawing.spreadsheet_drawing import SpreadsheetDrawing
        except ImportError:
            raise ImportError("openpyxl이 필요합니다. 'pip install openpyxl'을 실행하세요.")

        if not signals:
            return False

        wb = Workbook()
        ws = wb.active
        ws.title = model_name[:31]  # 시트 이름 최대 31자

        # ── 줌 25% 설정 ───────────────────────────────────────
        ws.sheet_view.zoomScale = ZOOM_PERCENT

        # ── 구간 계산 ─────────────────────────────────────────
        segments = _compute_segments(sync_data_us, signals)
        num_segs = len(segments)

        # 구간별 컬럼 수: 시간 비율에 따라 배분 (최소 1, 최대 16)
        total_us = sync_data_us
        TOTAL_WAVE_COLS = min(num_segs * 8, 128)  # 전체 파형 컬럼 수
        seg_cols = []
        for start, end, label in segments:
            ratio = (end - start) / total_us if total_us > 0 else 1 / num_segs
            n_cols = max(1, round(ratio * TOTAL_WAVE_COLS))
            seg_cols.append(n_cols)

        # 합이 TOTAL_WAVE_COLS와 다른 경우 마지막 구간 조정
        diff = TOTAL_WAVE_COLS - sum(seg_cols)
        seg_cols[-1] = max(1, seg_cols[-1] + diff)

        # 열 시작 인덱스 계산
        seg_start_cols = []
        cur_col = COL_WAVE_START
        for n in seg_cols:
            seg_start_cols.append(cur_col)
            cur_col += n

        total_cols = COL_WAVE_START + TOTAL_WAVE_COLS - 1

        # ── 열 너비 설정 ──────────────────────────────────────
        ws.column_dimensions[get_column_letter(COL_NUM)].width  = 8
        ws.column_dimensions[get_column_letter(COL_NAME)].width = NAME_COL_WIDTH
        for col_idx in range(COL_WAVE_START, total_cols + 1):
            ws.column_dimensions[get_column_letter(col_idx)].width = WAVE_COL_WIDTH

        # ── 행 높이 설정 ──────────────────────────────────────
        ws.row_dimensions[ROW_LABEL].height = 25      # 구간 라벨
        ws.row_dimensions[ROW_TIME_ARROW].height = 20  # 화살표/시간

        for sig_idx in range(len(signals)):
            base_row = ROW_SIGNAL_START + sig_idx * CELLS_PER_SIGNAL
            ws.row_dimensions[base_row].height = 12
            ws.row_dimensions[base_row + 1].height = 12

        # ── 스타일 준비 ───────────────────────────────────────
        from openpyxl.styles import Side

        def _border(top=None, bottom=None, left=None, right=None):
            return Border(
                top    = Side(style=top)    if top    else Side(style=None),
                bottom = Side(style=bottom) if bottom else Side(style=None),
                left   = Side(style=left)   if left   else Side(style=None),
                right  = Side(style=right)  if right  else Side(style=None),
            )

        thick_top_border    = _border(top=BORDER_THICK)
        thick_bottom_border = _border(bottom=BORDER_THICK)
        mid_border          = _border(top=BORDER_MED)
        thin_left_border    = _border(left=BORDER_THIN)

        center_align = Alignment(horizontal='center', vertical='center', wrap_text=True)
        left_align   = Alignment(horizontal='left',   vertical='center')
        right_align  = Alignment(horizontal='right',  vertical='center')

        header_fill = PatternFill('solid', fgColor=COLOR_HEADER)
        name_font   = Font(bold=True, size=FONT_SIGNAL_NAME)
        label_font  = Font(bold=True, size=FONT_HEADER)
        red_font    = Font(color=COLOR_RED,  bold=True, size=FONT_VOLTAGE)
        blue_font   = Font(color=COLOR_BLUE, bold=True, size=FONT_TIME_ARROW)

        # ── 행 1: 구간 라벨 (병합) ───────────────────────────
        # NUM / NAME 헤더
        ws.cell(ROW_LABEL, COL_NUM,  "NUM").font  = label_font
        ws.cell(ROW_LABEL, COL_NAME, "신호 이름").font = label_font
        ws.cell(ROW_LABEL, COL_NUM).alignment  = center_align
        ws.cell(ROW_LABEL, COL_NAME).alignment = center_align
        ws.cell(ROW_LABEL, COL_NUM).fill  = header_fill
        ws.cell(ROW_LABEL, COL_NAME).fill = header_fill

        for s_idx, (start, end, label) in enumerate(segments):
            c1 = seg_start_cols[s_idx]
            c2 = c1 + seg_cols[s_idx] - 1
            # 라벨 셀
            cell = ws.cell(ROW_LABEL, c1, label)
            cell.font      = label_font
            cell.alignment = center_align
            cell.fill      = header_fill
            cell.border    = _border(left=BORDER_THIN, right=BORDER_THIN,
                                     top=BORDER_MED, bottom=BORDER_MED)
            if c2 > c1:
                ws.merge_cells(
                    start_row=ROW_LABEL, start_column=c1,
                    end_row=ROW_LABEL,   end_column=c2
                )

        # ── 행 2: 화살표 & 시간 표시 ─────────────────────────
        for s_idx, (start, end, label) in enumerate(segments):
            seg_dur_us = end - start
            # 화살표 + 시간 텍스트: "← 1000.0 us →"
            if seg_dur_us >= 1.0:
                time_str = f"{seg_dur_us:.1f} us" if seg_dur_us < 10000 else f"{seg_dur_us/1000:.2f} ms"
            else:
                time_str = f"{seg_dur_us*1000:.0f} ns"
            arrow_text = f"↔ {time_str}"

            c1 = seg_start_cols[s_idx]
            c2 = c1 + seg_cols[s_idx] - 1

            cell = ws.cell(ROW_TIME_ARROW, c1, arrow_text)
            cell.font      = blue_font
            cell.alignment = center_align
            if c2 > c1:
                ws.merge_cells(
                    start_row=ROW_TIME_ARROW, start_column=c1,
                    end_row=ROW_TIME_ARROW,   end_column=c2
                )

        # ── NUM / NAME 열 병합 (신호 행들) ───────────────────
        for sig_idx, sig in enumerate(signals):
            base_row = ROW_SIGNAL_START + sig_idx * CELLS_PER_SIGNAL
            top_row    = base_row
            bottom_row = base_row + CELLS_PER_SIGNAL - 1

            # NUM 셀
            num_str = sig.get('num', f'S{sig_idx+1:02d}')
            ws.cell(top_row, COL_NUM, num_str).font = Font(bold=True, size=9)
            ws.cell(top_row, COL_NUM).alignment = center_align
            if bottom_row > top_row:
                ws.merge_cells(
                    start_row=top_row, start_column=COL_NUM,
                    end_row=bottom_row, end_column=COL_NUM
                )

            # NAME 셀
            ws.cell(top_row, COL_NAME, sig.get('name', '')).font = name_font
            ws.cell(top_row, COL_NAME).alignment = center_align
            if bottom_row > top_row:
                ws.merge_cells(
                    start_row=top_row, start_column=COL_NAME,
                    end_row=bottom_row, end_column=COL_NAME
                )

        # ── 파형 그리기 ───────────────────────────────────────
        for sig_idx, sig in enumerate(signals):
            base_row = ROW_SIGNAL_START + sig_idx * CELLS_PER_SIGNAL
            high_row = base_row        # 상단 행 (HIGH)
            low_row  = base_row + 1    # 하단 행 (LOW)

            v1 = float(sig.get('v1', 0))
            v2 = float(sig.get('v2', v1 + 1))
            high_v = max(v1, v2)
            low_v  = min(v1, v2)

            prev_level = None

            for s_idx, (start, end, label) in enumerate(segments):
                seg_mid_us = (start + end) / 2
                level = _get_signal_level_at(sig, seg_mid_us, sync_data_us)
                c1 = seg_start_cols[s_idx]
                c2 = c1 + seg_cols[s_idx] - 1

                is_rising  = (prev_level == 'LOW'  and level == 'HIGH')
                is_falling = (prev_level == 'HIGH' and level == 'LOW')
                is_first   = (s_idx == 0)

                # ── HIGH 행 (상단) 파형 그리기 ─────────────────
                for col in range(c1, c2 + 1):
                    ch = ws.cell(high_row, col)
                    cl = ws.cell(low_row,  col)
                    is_leftmost = (col == c1)

                    if level == 'HIGH':
                        # HIGH: 상단+좌우에 굵은 테두리
                        ch.border = Border(
                            top    = Side(style=BORDER_THICK),
                            left   = Side(style=BORDER_THICK if (is_leftmost and is_rising) else BORDER_THIN if is_leftmost else None),
                            right  = Side(style=None),
                            bottom = Side(style=None),
                        )
                        cl.border = Border(
                            bottom = Side(style=BORDER_THICK if (col == c2) else None),
                            left   = Side(style=BORDER_THICK if (is_leftmost and is_rising) else BORDER_THIN if is_leftmost else None),
                            right  = Side(style=None),
                            top    = Side(style=None),
                        )
                    else:
                        # LOW: 하단+좌우에 굵은 테두리
                        ch.border = Border(
                            top    = Side(style=None),
                            left   = Side(style=BORDER_THICK if (is_leftmost and is_falling) else BORDER_THIN if is_leftmost else None),
                            right  = Side(style=None),
                            bottom = Side(style=None),
                        )
                        cl.border = Border(
                            bottom = Side(style=BORDER_THICK),
                            left   = Side(style=BORDER_THICK if (is_leftmost and is_falling) else BORDER_THIN if is_leftmost else None),
                            right  = Side(style=None),
                            top    = Side(style=None),
                        )

                # 전압 텍스트 (구간 첫 열에 배치)
                if level == 'HIGH':
                    v_cell = ws.cell(high_row, c1)
                    v_cell.value = f"{high_v:.1f}V" if s_idx == 0 else None
                    if s_idx == 0:
                        v_cell.font = red_font
                else:
                    v_cell = ws.cell(low_row, c1)
                    v_cell.value = f"{low_v:.1f}V" if s_idx == 0 else None
                    if s_idx == 0:
                        v_cell.font = red_font

                # 구간 병합 (같은 레벨이면 병합)
                # ※ 천이(경계)가 있으면 병합 안 함 — 이미 개별 셀로 처리됨

                prev_level = level

        # ── 파일 저장 ─────────────────────────────────────────
        wb.save(filepath)
        return True

    def _col_letter(self, col_idx: int) -> str:
        from openpyxl.utils import get_column_letter
        return get_column_letter(col_idx)
