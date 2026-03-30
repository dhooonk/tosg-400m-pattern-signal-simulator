"""
제어 패널 (Control Panel)

상단 고정 패널로 다음 기능을 제공합니다.
  - 뷰 제어: 프레임 수, X축 모드, 뷰 시간 설정
  - 기타 설정: 그리드 토글, 뷰 모드(개별/합쳐 보기), 범례 위치
  - OTD/Excel I/O: 불러오기(OTD/Excel), 내보내기(OTD/Excel 파형/Excel 데이터),
                   포맷 파일 생성

변경 이력:
  v3 (피드백 1번): 모델 설정 패널(디스플레이 모델/주파수) 제거
  v3 (피드백 2번): OTD 불러오기 → model_store에 전체 모델 저장, 팝업 제거
  v3 (피드백 3번): MULTIREMOTE multiremote_panel 자동 갱신 연결
  v3 (피드백 4번): Excel 불러오기 → import_excel_all_models로 통일
  v3 (피드백 9번): 포맷 파일 생성 → Excel 형식으로 변경
  v3 (피드백 10,11,12번): Excel 데이터 출력 개선 (Waveform Data 시트 제거,
                           A열=No., B열부터 Name, Excel 불러오기 양식 준수)
"""

import tkinter as tk
from tkinter import ttk, messagebox
import os


class ControlPanel(tk.Frame):
    """
    제어 패널 위젯 클래스

    애플리케이션 상단에 배치되어 뷰 제어 및 파일 I/O 기능을 제공합니다.

    Attributes:
        sync_data_manager: SyncData 관리자 (타이밍 정보 저장)
        timing_viewer: 타이밍 다이어그램 뷰어 (지연 연결)
        signal_manager: 신호 관리자
        signal_storage: 신호 저장소 (현재 미사용)
        pattern_data_panel: 패턴 데이터 패널 (지연 연결)
        model_store: 다중 모델 데이터 저장소
    """

    def __init__(self, parent, sync_data_manager, timing_viewer, signal_manager,
                 signal_storage, pattern_data_panel=None, model_store=None):
        """
        초기화 메서드

        Args:
            parent: 부모 위젯
            sync_data_manager: SyncData 관리자
            timing_viewer: 타이밍 뷰어 (나중에 연결 가능)
            signal_manager: 신호 관리자
            signal_storage: 신호 저장소 (미사용)
            pattern_data_panel: PatternDataPanel 참조 (나중에 연결 가능)
            model_store: ModelStore 인스턴스 (다중 모델 관리)
        """
        super().__init__(parent, bg='#e0e0e0')

        self.sync_data_manager  = sync_data_manager
        self.timing_viewer      = timing_viewer
        self.signal_manager     = signal_manager
        self.signal_storage     = signal_storage
        self.pattern_data_panel = pattern_data_panel
        self.model_store        = model_store   # 다중 모델 저장소

        self._setup_ui()

    def _setup_ui(self):
        """UI 구성"""

        # ── 뷰 제어 프레임 ────────────────────────────────────────
        center_frame = tk.LabelFrame(self, text="뷰 제어",
                                     font=('Arial', 10, 'bold'),
                                     padx=10, pady=10,
                                     bg='#e0e0e0', fg='#000')
        center_frame.pack(side=tk.LEFT, fill=tk.BOTH, padx=5, pady=5)

        # 프레임 수 스핀박스
        tk.Label(center_frame, text="프레임 수:", font=('Arial', 9),
                 bg='#e0e0e0', fg='#000').grid(row=0, column=0, sticky='w', pady=2)

        self.frame_spinbox = tk.Spinbox(center_frame, from_=1, to=10,
                                        font=('Arial', 9), width=8,
                                        command=self._on_frame_changed)
        self.frame_spinbox.delete(0, tk.END)
        self.frame_spinbox.insert(0, '2')
        self.frame_spinbox.grid(row=0, column=1, sticky='w', pady=2, padx=5)

        # X축 모드 선택 (Frame 기준 / 시간 기준)
        tk.Label(center_frame, text="X축 모드:", font=('Arial', 9),
                 bg='#e0e0e0', fg='#000').grid(row=1, column=0, sticky='w', pady=2)

        self.x_axis_mode_var = tk.StringVar(value="frame")
        x_mode_frame = tk.Frame(center_frame, bg='#e0e0e0')
        x_mode_frame.grid(row=1, column=1, sticky='w', pady=2, padx=5)

        ttk.Radiobutton(x_mode_frame, text="Frame", variable=self.x_axis_mode_var,
                        value="frame", command=self._on_x_axis_mode_changed).pack(
            side=tk.LEFT, padx=2)
        ttk.Radiobutton(x_mode_frame, text="Time(us)", variable=self.x_axis_mode_var,
                        value="time", command=self._on_x_axis_mode_changed).pack(
            side=tk.LEFT, padx=2)

        # 뷰 시간 (X축 제한)
        tk.Label(center_frame, text="뷰 시간(us):", font=('Arial', 9),
                 bg='#e0e0e0', fg='#000').grid(row=2, column=0, sticky='w', pady=2)

        self.view_time_entry = tk.Entry(center_frame, font=('Arial', 9), width=8)
        self.view_time_entry.grid(row=2, column=1, sticky='w', pady=2, padx=5)
        self.view_time_entry.bind('<Return>',   self._on_view_time_changed)
        self.view_time_entry.bind('<FocusOut>', self._on_view_time_changed)

        # ── 기타 설정 프레임 ──────────────────────────────────────
        right_frame = tk.LabelFrame(self, text="기타 설정",
                                    font=('Arial', 10, 'bold'),
                                    padx=10, pady=10,
                                    bg='#e0e0e0', fg='#000')
        right_frame.pack(side=tk.LEFT, fill=tk.BOTH, padx=5, pady=5)

        # 그리드 토글 버튼
        tk.Button(right_frame, text="그리드 토글", command=self._on_toggle_grid,
                  font=('Arial', 9), bg='#FF9800', fg='black',
                  relief=tk.RAISED, borderwidth=2).pack(pady=2, fill=tk.X)

        # 뷰 모드 전환 (개별/통합)
        self.view_mode_var = tk.StringVar(value="separate")
        mode_frame = tk.Frame(right_frame, bg='#e0e0e0')
        mode_frame.pack(pady=2, fill=tk.X)
        ttk.Radiobutton(mode_frame, text="개별 보기", variable=self.view_mode_var,
                        value="separate", command=self._on_view_mode_changed).pack(
            side=tk.LEFT, padx=2)
        ttk.Radiobutton(mode_frame, text="합쳐 보기", variable=self.view_mode_var,
                        value="combined", command=self._on_view_mode_changed).pack(
            side=tk.LEFT, padx=2)

        # 범례 위치 선택 (합쳐 보기 모드에서 사용)
        tk.Label(right_frame, text="범례 위치:", font=('Arial', 9),
                 bg='#e0e0e0', fg='#000').pack(pady=2, fill=tk.X)

        self.legend_combo = ttk.Combobox(right_frame, font=('Arial', 9),
                                         state='readonly', width=12)
        self.legend_combo['values'] = [
            '우상 (upper right)', '좌상 (upper left)',
            '우하 (lower right)', '좌하 (lower left)'
        ]
        self.legend_combo.current(0)
        self.legend_combo.pack(pady=2, fill=tk.X)
        self.legend_combo.bind('<<ComboboxSelected>>', self._on_legend_location_changed)

        # ── OTD / Excel I/O 프레임 ────────────────────────────────
        otd_frame = tk.LabelFrame(self, text="OTD / Excel",
                                  font=('Arial', 10, 'bold'),
                                  padx=6, pady=6,
                                  bg='#e0e0e0', fg='#000')
        otd_frame.pack(side=tk.LEFT, fill=tk.BOTH, padx=5, pady=5)

        btn_kw = dict(font=('Arial', 8), relief=tk.RAISED, borderwidth=2, width=14)
        tk.Button(otd_frame, text="OTD 불러오기",    command=self._on_load_otd,
                  bg='#8BC34A', fg='black', **btn_kw).pack(pady=2)
        tk.Button(otd_frame, text="Excel 불러오기",  command=self._on_load_excel,
                  bg='#03A9F4', fg='black', **btn_kw).pack(pady=2)
        tk.Button(otd_frame, text="OTD 내보내기",    command=self._on_export_otd,
                  bg='#FF9800', fg='black', **btn_kw).pack(pady=2)
        tk.Button(otd_frame, text="Excel 파형 출력", command=self._on_export_excel_waveform,
                  bg='#9C27B0', fg='black', **btn_kw).pack(pady=2)
        # 피드백 9번: 포맷 파일 생성 → Excel 형식으로 변경
        tk.Button(otd_frame, text="포맷 파일 생성",  command=self._on_create_format,
                  bg='#607D8B', fg='black', **btn_kw).pack(pady=2)
        tk.Button(otd_frame, text="Excel 데이터 출력", command=self._on_export_excel,
                  bg='#00BCD4', fg='black', **btn_kw).pack(pady=2)

    # ──────────────────────────────────────────────────────────────
    # 뷰 제어 핸들러
    # ──────────────────────────────────────────────────────────────

    def _on_frame_changed(self):
        """프레임 수 변경: 타이밍 뷰어에 새 프레임 수 적용"""
        try:
            num_frames = int(self.frame_spinbox.get())
            self.timing_viewer.set_num_frames(num_frames)
        except (ValueError, AttributeError):
            pass

    def _on_x_axis_mode_changed(self):
        """X축 모드(Frame/Time) 변경: 타이밍 뷰어에 모드 전달"""
        if self.timing_viewer:
            self.timing_viewer.set_x_axis_mode(self.x_axis_mode_var.get())

    def _on_view_time_changed(self, event=None):
        """뷰 시간(X축 최대값) 변경: 타이밍 뷰어에 적용"""
        try:
            val = self.view_time_entry.get().strip()
            view_time = float(val) if val else None
            if self.timing_viewer:
                self.timing_viewer.set_view_time(view_time)
        except (ValueError, AttributeError):
            pass

    def _on_legend_location_changed(self, event=None):
        """범례 위치 변경: 타이밍 뷰어에 위치 전달"""
        location_map = {
            '우상 (upper right)': 'upper right',
            '좌상 (upper left)':  'upper left',
            '우하 (lower right)': 'lower right',
            '좌하 (lower left)':  'lower left',
        }
        location = location_map.get(self.legend_combo.get(), 'upper right')
        if self.timing_viewer:
            self.timing_viewer.set_legend_location(location)

    def _on_toggle_grid(self):
        """그리드 토글: 타이밍 뷰어 그리드 표시/숨김"""
        if self.timing_viewer:
            self.timing_viewer.toggle_grid()

    def _on_view_mode_changed(self):
        """뷰 모드(개별/합쳐 보기) 변경: 타이밍 뷰어에 전달"""
        if self.timing_viewer:
            self.timing_viewer.set_view_mode(self.view_mode_var.get())

    # ──────────────────────────────────────────────────────────────
    # OTD 불러오기  (피드백 2, 3번)
    # ──────────────────────────────────────────────────────────────

    def _on_load_otd(self):
        """
        OTD 파일 불러오기

        피드백 2번: 모델 선택 팝업을 제거하고, 파싱된 모든 모델을
        model_store에 저장합니다. 좌측 ModelListPanel이 자동으로
        갱신되어 모델을 클릭하면 신호/패턴 데이터가 표시됩니다.

        피드백 3번: MULTIREMOTE 데이터도 model_store에 함께 저장하여
        MultiRemotePanel에 자동 표시됩니다.
        """
        from tkinter import filedialog
        try:
            from otd_parser import OtdParser
        except ImportError as e:
            messagebox.showerror("오류", f"OTD 파서 로드 실패:\n{e}")
            return

        filepath = filedialog.askopenfilename(
            filetypes=[("OTD files", "*.otd *.OTD"), ("All files", "*.*")],
            title="OTD 파일 불러오기"
        )
        if not filepath:
            return

        try:
            otd_file = OtdParser.parse(filepath)
        except Exception as e:
            messagebox.showerror("파싱 오류", f"OTD 파일 파싱 실패:\n{e}")
            return

        if not otd_file.models:
            messagebox.showwarning("경고", "OTD 파일에서 모델을 찾을 수 없습니다.")
            return

        # OtdFile → ModelData 리스트 + MultiRemoteGroup 리스트로 변환
        try:
            from otd_to_model_store import otd_file_to_model_store
            model_list, mrt_groups = otd_file_to_model_store(otd_file)
        except Exception as e:
            messagebox.showerror("변환 오류", f"모델 데이터 변환 실패:\n{e}")
            return

        # ModelStore에 모든 모델 및 MULTIREMOTE 저장
        # → ModelListPanel과 MultiRemotePanel이 listener를 통해 자동 갱신
        self.model_store.set_models(model_list, mrt_groups)

        n_models = len(model_list)
        n_mrt    = len(mrt_groups)
        messagebox.showinfo(
            "완료",
            f"OTD 불러오기 완료:\n"
            f"파일: {os.path.basename(filepath)}\n"
            f"모델: {n_models}개  |  MULTIREMOTE: {n_mrt}개\n\n"
            f"좌측 모델 목록에서 모델을 클릭하세요."
        )

    # ──────────────────────────────────────────────────────────────
    # Excel 불러오기  (피드백 4번)
    # ──────────────────────────────────────────────────────────────

    def _on_load_excel(self):
        """
        Excel PG Signal 파일 불러오기

        피드백 4번: import_excel_pg_signals 대신 import_excel_all_models를
        사용하고, 결과를 model_store에 저장합니다 (OTD 불러오기와 동일 흐름).
        """
        from tkinter import filedialog
        try:
            from excel_importer import import_excel_all_models
        except ImportError as e:
            messagebox.showerror("오류", f"Excel 임포터 로드 실패:\n{e}")
            return

        filepath = filedialog.askopenfilename(
            filetypes=[("Excel files", "*.xlsx *.xls"), ("All files", "*.*")],
            title="PG Signal Excel 파일 불러오기"
        )
        if not filepath:
            return

        try:
            model_list = import_excel_all_models(filepath)
        except Exception as e:
            messagebox.showerror("오류", f"Excel 파싱 실패:\n{e}")
            return

        if not model_list:
            messagebox.showwarning("경고", "불러온 모델이 없습니다.\nExcel 형식을 확인하세요.")
            return

        # ModelStore에 저장 (MULTIREMOTE는 Excel에 없으므로 빈 리스트)
        self.model_store.set_models(model_list, [])

        n_sigs_total = sum(len(m.signals) for m in model_list)
        messagebox.showinfo(
            "완료",
            f"Excel 불러오기 완료:\n"
            f"파일: {os.path.basename(filepath)}\n"
            f"모델: {len(model_list)}개  |  총 신호: {n_sigs_total}개\n\n"
            f"좌측 모델 목록에서 모델을 클릭하세요."
        )

    # ──────────────────────────────────────────────────────────────
    # OTD 내보내기  (피드백 5, 6번 → otd_exporter.py에서 처리됨)
    # ──────────────────────────────────────────────────────────────

    def _on_export_otd(self):
        """
        현재 model_store의 모든 모델을 OTD 파일로 내보내기.

        신호/패턴/MULTIREMOTE 데이터를 모두 포함합니다.
        model_store에 데이터가 없으면 현재 signal_manager 신호만 내보냅니다.
        """
        from tkinter import filedialog
        try:
            from otd_exporter import OtdExporter
        except ImportError as e:
            messagebox.showerror("오류", f"OTD 내보내기 모듈 로드 실패:\n{e}")
            return

        # model_store에 모델이 있으면 전체 내보내기
        if self.model_store and self.model_store.models:
            default_name = "models_export.otd"
            filepath = filedialog.asksaveasfilename(
                defaultextension=".otd",
                filetypes=[("OTD files", "*.otd"), ("All files", "*.*")],
                initialfile=default_name,
                title="OTD 파일 저장"
            )
            if not filepath:
                return

            exporter = OtdExporter()
            if exporter.export_from_model_store(filepath, self.model_store):
                messagebox.showinfo("완료", f"OTD 파일 저장:\n{filepath}")
            else:
                messagebox.showerror("오류", "OTD 파일 저장에 실패했습니다.")
            return

        # model_store가 없거나 비었으면: 현재 signal_manager 신호만 내보내기
        signals = self.signal_manager.get_all_signals()
        if not signals:
            messagebox.showwarning("경고", "내보낼 신호가 없습니다.")
            return

        filepath = filedialog.asksaveasfilename(
            defaultextension=".otd",
            filetypes=[("OTD files", "*.otd"), ("All files", "*.*")],
            initialfile="export.otd",
            title="OTD 파일 저장"
        )
        if not filepath:
            return

        sync_val = self.sync_data_manager.get_current_sync_data() * 1_000_000
        patterns = []
        if self.pattern_data_panel is not None:
            patterns = self.pattern_data_panel.get_patterns()

        model_data = [{
            'model_num':    '001',
            'name':         self.sync_data_manager.current_model or 'MODEL',
            'frequency_hz': float(self.sync_data_manager.current_frequency or 60),
            'sync_data_us': sync_val,
            'sync_cntr':    0,
            'signals':      [s.to_dict() for s in signals],
            'patterns':     patterns,
        }]

        exporter = OtdExporter()
        if exporter.export(filepath, model_data):
            messagebox.showinfo("완료", f"OTD 파일 저장:\n{filepath}")
        else:
            messagebox.showerror("오류", "OTD 파일 저장에 실패했습니다.")

    # ──────────────────────────────────────────────────────────────
    # Excel 파형 출력  (피드백 7, 8번 → excel_waveform_exporter.py에서 처리됨)
    # ──────────────────────────────────────────────────────────────

    def _on_export_excel_waveform(self):
        """
        현재 표시 중인 신호 데이터를 Excel 파형 시각화로 내보내기.

        각 신호는 셀 테두리로 파형을 표현하고,
        전압 전환 구간 위에 ↔ timing 텍스트를 표시합니다.
        """
        from tkinter import filedialog
        try:
            from excel_waveform_exporter import ExcelWaveformExporter
        except ImportError as e:
            messagebox.showerror("오류", f"Excel 파형 내보내기 모듈 로드 실패:\n{e}")
            return

        signals = self.signal_manager.get_all_signals()
        visible_signals = [s for s in signals if getattr(s, 'visible', True)]
        if not visible_signals:
            messagebox.showwarning("경고", "내보낼 신호가 없습니다.")
            return

        model        = self.sync_data_manager.current_model or 'MODEL'
        sync_data_s  = self.sync_data_manager.get_current_sync_data()
        sync_data_us = sync_data_s * 1_000_000

        filepath = filedialog.asksaveasfilename(
            defaultextension=".xlsx",
            filetypes=[("Excel files", "*.xlsx"), ("All files", "*.*")],
            initialfile=f"{model}_waveform.xlsx",
            title="Excel 파형 시각화 저장"
        )
        if not filepath:
            return

        sig_dicts = [s.to_dict() for s in visible_signals]
        # 신호 번호(_num) 추가
        for i, (sig, d) in enumerate(zip(visible_signals, sig_dicts)):
            d['num'] = getattr(sig, '_num', f'S{i+1:02d}')

        exporter = ExcelWaveformExporter()
        try:
            exporter.export(filepath, sig_dicts, sync_data_us, model)
            messagebox.showinfo("완료", f"Excel 파형 시각화 저장:\n{filepath}")
        except Exception as e:
            messagebox.showerror("오류", f"Excel 파형 저장 실패:\n{e}")

    # ──────────────────────────────────────────────────────────────
    # 포맷 파일 생성  (피드백 9번: OTD → Excel 형식으로 변경)
    # ──────────────────────────────────────────────────────────────

    def _on_create_format(self):
        """
        Excel 불러오기용 빈 양식 파일 생성

        피드백 9번: 기존 OTD 포맷 파일 생성 대신,
        Excel 불러오기에 사용하는 양식(.xlsx)을 생성합니다.
        """
        from tkinter import filedialog, simpledialog
        try:
            from excel_format_generator import generate_excel_format_file
        except ImportError as e:
            messagebox.showerror("오류", f"양식 생성 모듈 로드 실패:\n{e}")
            return

        model_count = simpledialog.askinteger(
            "포맷 파일 생성",
            "생성할 빈 모델(시트) 수를 입력하세요:",
            initialvalue=1, minvalue=1, maxvalue=20
        )
        if model_count is None:
            return

        # 피드백 9번: 확장자 .xlsx, 저장 제목 변경
        filepath = filedialog.asksaveasfilename(
            defaultextension=".xlsx",
            filetypes=[("Excel files", "*.xlsx"), ("All files", "*.*")],
            initialfile="pg_signal_format.xlsx",
            title="Excel 포맷 파일 저장"
        )
        if not filepath:
            return

        try:
            generate_excel_format_file(filepath, model_count)
            messagebox.showinfo("완료", f"Excel 포맷 파일 생성:\n{filepath}")
        except Exception as e:
            messagebox.showerror("오류", f"포맷 파일 생성 실패:\n{e}")

    # ──────────────────────────────────────────────────────────────
    # Excel 데이터 출력  (피드백 10, 11, 12번)
    # ──────────────────────────────────────────────────────────────

    def _on_export_excel(self):
        """
        현재 신호 데이터를 Excel 파일로 내보내기

        피드백 10번: Waveform Data 시트 삭제
        피드백 11번: A열=No.(S01~S36), B열부터 Name 표시
        피드백 12번: Excel 불러오기 양식(excel_format_generator 규격)에 맞게 출력

        출력 시트 구조:
          - [모델이름] 시트: 신호 파라미터 (excel_importer 양식 호환)
          - [Model Info] 시트: 모델 기본 정보
        """
        try:
            import openpyxl
            from openpyxl import Workbook
            from openpyxl.styles import PatternFill, Font, Alignment, Border, Side
            from openpyxl.utils import get_column_letter
        except ImportError:
            messagebox.showerror(
                "오류",
                "openpyxl 라이브러리가 필요합니다.\n'pip install openpyxl'을 실행하세요."
            )
            return

        signals = self.signal_manager.get_all_signals()
        visible_signals = [s for s in signals if getattr(s, 'visible', True)]

        if not visible_signals:
            messagebox.showwarning("경고", "내보낼 신호가 없습니다.")
            return

        from tkinter import filedialog
        model    = self.sync_data_manager.current_model or 'MODEL'
        freq     = self.sync_data_manager.current_frequency or 60
        sync_data_s  = self.sync_data_manager.get_current_sync_data()
        sync_data_us = sync_data_s * 1_000_000

        filepath = filedialog.asksaveasfilename(
            defaultextension=".xlsx",
            filetypes=[("Excel files", "*.xlsx"), ("All files", "*.*")],
            initialfile=f"{model}_data.xlsx",
            title="Excel 데이터 저장"
        )
        if not filepath:
            return

        # ── 스타일 정의 ──────────────────────────────────
        header_fill  = PatternFill('solid', fgColor='FF2C3E50')
        sync_fill    = PatternFill('solid', fgColor='FF27AE60')
        info_fill    = PatternFill('solid', fgColor='FF2980B9')
        row_fill_alt = PatternFill('solid', fgColor='FFECF0F1')

        header_font = Font(bold=True, size=10, color='FFFFFFFF')
        sync_font   = Font(bold=True, size=9,  color='FFFFFFFF')
        info_font   = Font(bold=True, size=9,  color='FFFFFFFF')
        num_font    = Font(bold=True, size=9,  color='FF2C3E50')
        normal_font = Font(size=9)

        center = Alignment(horizontal='center', vertical='center')
        left   = Alignment(horizontal='left',   vertical='center')

        def _side(style='thin'):
            return Side(style=style)

        thin_border = Border(
            left=_side(), right=_side(), top=_side(), bottom=_side()
        )

        try:
            wb = Workbook()
            # 기본 시트를 모델 신호 데이터 시트로 사용
            ws = wb.active
            import re
            safe_title = re.sub(r'[\\/*?\[\]:]', '_', model)[:31]
            ws.title = safe_title

            # ── 피드백 11번: 신호 파라미터 헤더 ─────────────────
            # A열=No.(S01~S36), B열=Name, C~N열=파라미터
            SIGNAL_HEADERS = [
                ('A', 'NUM',         8),
                ('B', 'NAME',        14),
                ('C', 'SIG TYPE',    9),
                ('D', 'SIG MODE',    9),
                ('E', 'INV',         7),
                ('F', 'V1 (V)',      9),
                ('G', 'V2 (V)',      9),
                ('H', 'V3 (V)',      9),
                ('I', 'V4 (V)',      9),
                ('J', 'DELAY (us)',  11),
                ('K', 'PERIOD (us)', 11),
                ('L', 'WIDTH (us)',  11),
                ('M', 'LENGTH (us)', 11),
                ('N', 'AREA (us)',   11),
            ]

            # 1행: 헤더
            ws.row_dimensions[1].height = 20
            for col_letter, label, width in SIGNAL_HEADERS:
                col_idx = ord(col_letter) - ord('A') + 1
                cell = ws.cell(row=1, column=col_idx, value=label)
                cell.font      = header_font
                cell.fill      = header_fill
                cell.alignment = center
                cell.border    = thin_border
                ws.column_dimensions[col_letter].width = width

            # 2~37행: 신호 데이터 (S01~S36)
            # 피드백 12번: excel_importer 양식 호환 형식으로 출력
            for i in range(36):
                row_num = i + 2
                # A열: No. (S01~S36)
                num_str = f'S{i + 1:02d}'
                num_cell = ws.cell(row=row_num, column=1, value=num_str)
                num_cell.font      = num_font
                num_cell.alignment = center
                num_cell.border    = thin_border
                if row_num % 2 == 0:
                    num_cell.fill = row_fill_alt

                # 신호 데이터가 있으면 채우고, 없으면 빈 셀
                if i < len(visible_signals):
                    sig = visible_signals[i]
                    # B열: Name
                    sig_values = [
                        sig.name,                      # B: NAME
                        sig.sig_type,                  # C: SIG TYPE
                        sig.sig_mode,                  # D: SIG MODE
                        sig.inversion,                 # E: INV
                        sig.v1,                        # F: V1
                        sig.v2,                        # G: V2
                        sig.v3,                        # H: V3
                        sig.v4,                        # I: V4
                        sig.delay,                     # J: DELAY
                        sig.period,                    # K: PERIOD
                        sig.width,                     # L: WIDTH
                        getattr(sig, '_length', 0),    # M: LENGTH
                        getattr(sig, '_area',   0),    # N: AREA
                    ]
                else:
                    sig_values = [''] * 13  # 빈 셀 (B~N)

                for col_offset, val in enumerate(sig_values):
                    col_idx = 2 + col_offset  # B열=2부터
                    c = ws.cell(row=row_num, column=col_idx, value=val)
                    c.border    = thin_border
                    c.alignment = center
                    c.font      = normal_font
                    if row_num % 2 == 0:
                        c.fill = row_fill_alt

            # 피드백 12번: SyncData 영역 (P/Q열, 2~4행)
            sync_labels = [
                ('SyncData (us)', sync_data_us),
                ('Frequency (Hz)', float(freq)),
                ('SyncCounter', 0),
            ]
            ws.column_dimensions['P'].width = 16
            ws.column_dimensions['Q'].width = 12
            for row_offset, (label, val) in enumerate(sync_labels):
                row_num = row_offset + 2
                p_cell = ws.cell(row=row_num, column=16, value=label)
                p_cell.font      = sync_font
                p_cell.fill      = sync_fill
                p_cell.alignment = left
                p_cell.border    = thin_border

                q_cell = ws.cell(row=row_num, column=17, value=val)
                q_cell.border    = thin_border
                q_cell.alignment = center

            # 피드백 12번: 패턴 데이터 영역 (39~40행 이후)
            ws.row_dimensions[38].height = 6
            ws.row_dimensions[39].height = 18
            ws.row_dimensions[40].height = 18

            ws.merge_cells('A39:S39')
            sep = ws.cell(row=39, column=1, value='=== PATTERN DATA (아래에 패턴 입력) ===')
            sep.font      = Font(bold=True, size=9, color='FFFFFFFF')
            sep.fill      = PatternFill('solid', fgColor='FF8E44AD')
            sep.alignment = center

            PATTERN_HEADERS = [
                ('A', 'PTN_NO', 8), ('B', 'NAME',   12),
                ('C', 'R_V1',   8), ('D', 'R_V2',    8),
                ('E', 'R_V3',   8), ('F', 'R_V4',    8),
                ('G', 'G_V1',   8), ('H', 'G_V2',    8),
                ('I', 'G_V3',   8), ('J', 'G_V4',    8),
                ('K', 'B_V1',   8), ('L', 'B_V2',    8),
                ('M', 'B_V3',   8), ('N', 'B_V4',    8),
                ('O', 'W_V1',   8), ('P', 'W_V2',    8),
                ('Q', 'W_V3',   8), ('R', 'W_V4',    8),
                ('S', 'TYPE',   8),
            ]
            ptn_header_fill = PatternFill('solid', fgColor='FF8E44AD')
            ptn_header_font = Font(bold=True, size=9, color='FFFFFFFF')

            for col_letter, label, width in PATTERN_HEADERS:
                col_idx = ord(col_letter) - ord('A') + 1
                cell = ws.cell(row=40, column=col_idx, value=label)
                cell.font      = ptn_header_font
                cell.fill      = ptn_header_fill
                cell.alignment = center
                cell.border    = thin_border

            # 패턴 데이터: pattern_data_panel에서 가져오기
            patterns = []
            if self.pattern_data_panel is not None:
                patterns = self.pattern_data_panel.get_patterns()

            for ptn_offset, ptn in enumerate(patterns):
                ptn_row = 41 + ptn_offset
                ptn_vals = [
                    ptn.get('ptn_no', ptn_offset + 1),
                    ptn.get('name', f'PTN{ptn_offset+1:02d}'),
                    ptn.get('r_v1', 0), ptn.get('r_v2', 0),
                    ptn.get('r_v3', 0), ptn.get('r_v4', 0),
                    ptn.get('g_v1', 0), ptn.get('g_v2', 0),
                    ptn.get('g_v3', 0), ptn.get('g_v4', 0),
                    ptn.get('b_v1', 0), ptn.get('b_v2', 0),
                    ptn.get('b_v3', 0), ptn.get('b_v4', 0),
                    ptn.get('w_v1', 0), ptn.get('w_v2', 0),
                    ptn.get('w_v3', 0), ptn.get('w_v4', 0),
                    ptn.get('ptn_type', 0),
                ]
                for col_idx, val in enumerate(ptn_vals, 1):
                    c = ws.cell(row=ptn_row, column=col_idx, value=val)
                    c.border    = thin_border
                    c.alignment = center

            # ── Model Info 시트 ───────────────────────────────────
            ws_info = wb.create_sheet("Model Info")
            info_headers = ['Parameter', 'Value']
            for col_idx, label in enumerate(info_headers, 1):
                cell = ws_info.cell(row=1, column=col_idx, value=label)
                cell.font      = info_font
                cell.fill      = info_fill
                cell.alignment = center
                cell.border    = thin_border

            info_data = [
                ('Model',            model),
                ('Frequency (Hz)',   float(freq)),
                ('SyncData (us)',    sync_data_us),
                ('Signal Count',     len(visible_signals)),
            ]
            for row_offset, (param, val) in enumerate(info_data, 2):
                ws_info.cell(row=row_offset, column=1, value=param).border = thin_border
                ws_info.cell(row=row_offset, column=2, value=val).border   = thin_border

            ws_info.column_dimensions['A'].width = 18
            ws_info.column_dimensions['B'].width = 18

            wb.save(filepath)
            messagebox.showinfo("완료", f"Excel 파일이 저장되었습니다:\n{filepath}")

        except Exception as e:
            messagebox.showerror("오류", f"Excel 파일 저장 실패:\n{str(e)}")
