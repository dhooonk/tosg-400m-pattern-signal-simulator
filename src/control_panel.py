"""
제어 패널 (Control Panel)
모델 선택, 주파수 설정, 프레임 제어, 데이터 저장/로드 기능을 제공하는 상단 패널입니다.
"""

import tkinter as tk
from tkinter import ttk, messagebox
import os


class ControlPanel(tk.Frame):
    """
    제어 패널 위젯 클래스
    
    사용자가 시뮬레이션 환경을 설정하고 제어할 수 있는 UI를 제공합니다.
    - 모델 및 주파수 선택
    - SyncData 표시
    - 프레임 수 조절
    - 그리드 토글
    - 뷰 모드 전환 (개별/통합)
    - 시간 단위 설정 (us, Line, Pixel)
    - 데이터 저장 및 불러오기
    
    V11 업데이트:
    - 범례 위치 선택 기능 추가
    - 파일 저장/불러오기를 사용자 지정 파일로 변경
    - 시간 단위 콤보박스 제거 (Line 옵션 삭제)
    """
    
    def __init__(self, parent, sync_data_manager, timing_viewer, signal_manager, signal_storage,
                 pattern_data_panel=None, model_store=None):
        """
        초기화 메서드
        
        Args:
            parent: 부모 위젯
            sync_data_manager: SyncData 관리자
            timing_viewer: 타이밍 뷰어
            signal_manager: 신호 관리자
            signal_storage: 신호 저장소 (미사용 - 통하여 제거됨)
            pattern_data_panel: PatternDataPanel 참조
            model_store: ModelStore 인스턴스 (다중 모델 관리)
        """
        super().__init__(parent, bg='#e0e0e0')
        
        self.sync_data_manager = sync_data_manager
        self.timing_viewer     = timing_viewer
        self.signal_manager    = signal_manager
        self.signal_storage    = signal_storage
        self.pattern_data_panel = pattern_data_panel
        self.model_store       = model_store  # 다중 모델 저장소
        
        self._setup_ui()
        self._update_sync_data_display()
    
    def _setup_ui(self):
        """UI 구성"""
        # 좌측: 모델/주파수 설정 프레임
        left_frame = tk.LabelFrame(self, text="모델 설정", font=('Arial', 10, 'bold'), 
                                  padx=10, pady=10, bg='#e0e0e0', fg='#000')
        left_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # 모델 선택 콤보박스
        tk.Label(left_frame, text="디스플레이 모델:", font=('Arial', 9), 
                bg='#e0e0e0', fg='#000').grid(
            row=0, column=0, sticky='w', pady=3
        )
        
        self.model_combo = ttk.Combobox(left_frame, font=('Arial', 9), 
                                       state='readonly', width=15)
        self.model_combo['values'] = self.sync_data_manager.get_model_list()
        
        # 초기 모델 선택
        if self.model_combo['values']:
            self.model_combo.current(0)
            
        self.model_combo.grid(row=0, column=1, sticky='ew', pady=3, padx=5)
        self.model_combo.bind('<<ComboboxSelected>>', self._on_model_changed)
        
        # 모델 관리 버튼 (다이얼로그 열기)
        tk.Button(left_frame, text="모델 관리", command=self._on_manage_models,
                 bg='#9C27B0', fg='black', font=('Arial', 8, 'bold'),
                 relief=tk.RAISED, borderwidth=2).grid(row=0, column=2, sticky='w', pady=3, padx=2)
        
        # 주파수 선택 콤보박스
        tk.Label(left_frame, text="주파수:", font=('Arial', 9),
                bg='#e0e0e0', fg='#000').grid(
            row=1, column=0, sticky='w', pady=3
        )
        
        self.freq_combo = ttk.Combobox(left_frame, font=('Arial', 9), 
                                      state='readonly', width=15)
        self._update_frequency_list()
        self.freq_combo.grid(row=1, column=1, sticky='ew', pady=3, padx=5)
        self.freq_combo.bind('<<ComboboxSelected>>', self._on_frequency_changed)
        
        # SyncData 표시 레이블
        tk.Label(left_frame, text="SyncData:", font=('Arial', 9),
                bg='#e0e0e0', fg='#000').grid(
            row=2, column=0, sticky='w', pady=3
        )
        
        self.sync_data_label = tk.Label(left_frame, text="", font=('Arial', 9, 'bold'),
                                        fg='#2196F3', bg='#e0e0e0')
        self.sync_data_label.grid(row=2, column=1, sticky='w', pady=3, padx=5)
        
        left_frame.grid_columnconfigure(1, weight=1)
        
        # 중앙: 뷰 제어 (프레임, 시간)
        center_frame = tk.LabelFrame(self, text="뷰 제어", font=('Arial', 10, 'bold'),
                                    padx=10, pady=10, bg='#e0e0e0', fg='#000')
        center_frame.pack(side=tk.LEFT, fill=tk.BOTH, padx=5, pady=5)
        
        # 프레임 수
        tk.Label(center_frame, text="프레임 수:", font=('Arial', 9),
                bg='#e0e0e0', fg='#000').grid(row=0, column=0, sticky='w', pady=2)
        
        self.frame_spinbox = tk.Spinbox(center_frame, from_=1, to=10, 
                                       font=('Arial', 9), width=8,
                                       command=self._on_frame_changed)
        self.frame_spinbox.delete(0, tk.END)
        self.frame_spinbox.insert(0, '2')
        self.frame_spinbox.grid(row=0, column=1, sticky='w', pady=2, padx=5)
        
        # 시간 단위 제거 (Line 옵션 삭제)
        # X축 모드만 사용 (Frame/Time(us))
        
        # V11: X축 모드 선택 (Frame 기준 / 시간 기준)
        tk.Label(center_frame, text="X축 모드:", font=('Arial', 9),
                bg='#e0e0e0', fg='#000').grid(row=1, column=0, sticky='w', pady=2)
        
        self.x_axis_mode_var = tk.StringVar(value="frame")
        x_mode_frame = tk.Frame(center_frame, bg='#e0e0e0')
        x_mode_frame.grid(row=1, column=1, sticky='w', pady=2, padx=5)
        
        ttk.Radiobutton(x_mode_frame, text="Frame", variable=self.x_axis_mode_var,
                       value="frame", command=self._on_x_axis_mode_changed).pack(side=tk.LEFT, padx=2)
        ttk.Radiobutton(x_mode_frame, text="Time(us)", variable=self.x_axis_mode_var,
                       value="time", command=self._on_x_axis_mode_changed).pack(side=tk.LEFT, padx=2)
        
        # 뷰 시간 (X축 제한) - Time 모드일 때 사용
        tk.Label(center_frame, text="뷰 시간(us):", font=('Arial', 9),
                bg='#e0e0e0', fg='#000').grid(row=2, column=0, sticky='w', pady=2)
        
        self.view_time_entry = tk.Entry(center_frame, font=('Arial', 9), width=8)
        self.view_time_entry.grid(row=2, column=1, sticky='w', pady=2, padx=5)
        self.view_time_entry.bind('<Return>', self._on_view_time_changed)
        self.view_time_entry.bind('<FocusOut>', self._on_view_time_changed)
        
        # 우측: 기타 설정
        right_frame = tk.LabelFrame(self, text="기타 설정", font=('Arial', 10, 'bold'),
                                   padx=10, pady=10, bg='#e0e0e0', fg='#000')
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
                       value="separate", command=self._on_view_mode_changed).pack(side=tk.LEFT, padx=2)
        ttk.Radiobutton(mode_frame, text="합쳐 보기", variable=self.view_mode_var, 
                       value="combined", command=self._on_view_mode_changed).pack(side=tk.LEFT, padx=2)
        
        # 범례 위치 선택 (합쳐 보기 모드에서 사용)
        tk.Label(right_frame, text="범례 위치:", font=('Arial', 9),
                bg='#e0e0e0', fg='#000').pack(pady=2, fill=tk.X)
        
        self.legend_combo = ttk.Combobox(right_frame, font=('Arial', 9),
                                        state='readonly', width=12)
        self.legend_combo['values'] = ['우상 (upper right)', '좌상 (upper left)', 
                                       '우하 (lower right)', '좌하 (lower left)']
        self.legend_combo.current(0)
        self.legend_combo.pack(pady=2, fill=tk.X)
        self.legend_combo.bind('<<ComboboxSelected>>', self._on_legend_location_changed)
        
        # OTD / Excel 관련 프레임
        otd_frame = tk.LabelFrame(self, text="OTD / Excel", font=('Arial', 10, 'bold'),
                                  padx=6, pady=6, bg='#e0e0e0', fg='#000')
        otd_frame.pack(side=tk.LEFT, fill=tk.BOTH, padx=5, pady=5)

        btn_kw2 = dict(font=('Arial', 8), relief=tk.RAISED, borderwidth=2, width=14)
        tk.Button(otd_frame, text="OTD 불러오기",    command=self._on_load_otd,
                 bg='#8BC34A', fg='black', **btn_kw2).pack(pady=2)
        tk.Button(otd_frame, text="Excel 불러오기",  command=self._on_load_excel,
                 bg='#03A9F4', fg='black', **btn_kw2).pack(pady=2)
        tk.Button(otd_frame, text="OTD 내보내기",    command=self._on_export_otd,
                 bg='#FF9800', fg='black', **btn_kw2).pack(pady=2)
        tk.Button(otd_frame, text="Excel 파형 출력", command=self._on_export_excel_waveform,
                 bg='#9C27B0', fg='black', **btn_kw2).pack(pady=2)
        tk.Button(otd_frame, text="포맷 파일 생성",  command=self._on_create_format,
                 bg='#607D8B', fg='black', **btn_kw2).pack(pady=2)
        tk.Button(otd_frame, text="Excel 데이터 출력", command=self._on_export_excel,
                 bg='#00BCD4', fg='black', **btn_kw2).pack(pady=2)

    
    def _update_frequency_list(self):
        """현재 선택된 모델에 맞는 주파수 목록 업데이트"""
        model = self.model_combo.get()
        frequencies = self.sync_data_manager.get_frequency_list(model)
        self.freq_combo['values'] = [f"{f} Hz" for f in frequencies]
        if frequencies:
            self.freq_combo.current(0)
    
    def _update_sync_data_display(self):
        """SyncData 값 표시 업데이트 (초 단위)"""
        sync_data = self.sync_data_manager.get_current_sync_data()
        self.sync_data_label.config(text=f"{sync_data:.6f} s")
    
    def _on_model_changed(self, event=None):
        """
        모델 변경 이벤트 핸들러
        
        모델 변경 시 주파수 목록, SyncData, 그래프를 업데이트하고
        해당 모델의 저장된 신호를 자동으로 불러옵니다.
        """
        model = self.model_combo.get()
        self.sync_data_manager.set_model(model)
        self._update_frequency_list()
        self._update_sync_data_display()
        self.timing_viewer.update_plot()
        
        # 모델 변경 시 해당 모델의 신호 데이터 자동 로드는 제거
        # 사용자가 명시적으로 파일을 불러오도록 변경
    
    def _on_frequency_changed(self, event=None):
        """
        주파수 변경 이벤트 핸들러
        
        주파수 변경 시 SyncData와 그래프를 업데이트합니다.
        """
        freq_str = self.freq_combo.get()
        if freq_str:
            frequency = int(freq_str.split()[0])
            self.sync_data_manager.set_frequency(frequency)
            self._update_sync_data_display()
            self.timing_viewer.update_plot()
    
    def _on_frame_changed(self):
        """프레임 수 변경 이벤트 핸들러"""
        try:
            num_frames = int(self.frame_spinbox.get())
            self.timing_viewer.set_num_frames(num_frames)
        except ValueError:
            pass
    
    def _on_legend_location_changed(self, event=None):
        """범례 위치 변경 이벤트 핸들러"""
        location_map = {
            '우상 (upper right)': 'upper right',
            '좌상 (upper left)': 'upper left',
            '우하 (lower right)': 'lower right',
            '좌하 (lower left)': 'lower left'
        }
        location_str = self.legend_combo.get()
        location = location_map.get(location_str, 'upper right')
        self.timing_viewer.set_legend_location(location)
        
    def _on_view_time_changed(self, event=None):
        """뷰 시간(X축 제한) 변경 이벤트 핸들러"""
        try:
            val = self.view_time_entry.get().strip()
            if val:
                view_time = float(val)
            else:
                view_time = None
            self.timing_viewer.set_view_time(view_time)
        except ValueError:
            pass
    
    def _on_x_axis_mode_changed(self):
        """X축 모드 변경 이벤트 핸들러"""
        mode = self.x_axis_mode_var.get()
        self.timing_viewer.set_x_axis_mode(mode)
    
    def _on_toggle_grid(self):
        """그리드 토글 버튼 핸들러"""
        self.timing_viewer.toggle_grid()
        
    def _on_view_mode_changed(self):
        """뷰 모드 변경 이벤트 핸들러"""
        mode = self.view_mode_var.get()
        self.timing_viewer.set_view_mode(mode)
    
    def _on_save(self):
        """
        파일 저장 버튼 핸들러
        
        사용자가 지정한 파일명으로 신호를 JSON 파일로 저장합니다.
        """
        from tkinter import filedialog
        
        signals = self.signal_manager.get_all_signals()
        
        if not signals:
            tk.messagebox.showwarning("경고", "저장할 신호가 없습니다.")
            return
        
        # 기본 파일명 제안
        model = self.sync_data_manager.current_model
        default_filename = f"{model}_signals.json"
        
        # 파일 저장 대화상자
        filepath = filedialog.asksaveasfilename(
            defaultextension=".json",
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")],
            initialfile=default_filename,
            title="신호 데이터 저장"
        )
        
        if not filepath:
            return
        
        if self.signal_storage.save_signals_to_file(filepath, signals):
            tk.messagebox.showinfo("저장 완료", f"신호를 저장했습니다:\n{filepath}")
        else:
            tk.messagebox.showerror("저장 실패", "신호 저장에 실패했습니다.")
    
    def _on_load(self):
        """
        파일 불러오기 버튼 핸들러
        
        사용자가 선택한 JSON 파일에서 신호를 불러옵니다.
        """
        from tkinter import filedialog
        
        # 파일 열기 대화상자
        filepath = filedialog.askopenfilename(
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")],
            title="신호 데이터 불러오기"
        )
        
        if not filepath:
            return
        
        signals = self.signal_storage.load_signals_from_file(filepath)
        
        if signals:
            # 기존 신호 삭제 후 로드된 신호 추가
            self.signal_manager.clear_signals()
            for signal in signals:
                self.signal_manager.add_signal(signal)
            tk.messagebox.showinfo("불러오기 완료", 
                                 f"신호 {len(signals)}개를 불러왔습니다.")
        else:
            tk.messagebox.showwarning("불러오기 실패", "파일을 읽을 수 없거나 신호가 없습니다.")
    
    # ──────────────────────────────────────────────────────────────
    # OTD 불러오기
    # ──────────────────────────────────────────────────────────────
    def _on_load_otd(self):
        """
        OTD 파일 불러오기
        선택한 OTD 파일을 파싱하여 신호 및 패턴 데이터를 로드합니다.
        여러 모델이 있으면 선택 다이얼로그(간단한 표)로 선택합니다.
        """
        from tkinter import filedialog
        try:
            from otd_parser import OtdParser, otd_signal_to_signal_dict
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

        # 모델이 여러 개면 선택
        if len(otd_file.models) == 1:
            model = otd_file.models[0]
        else:
            model = self._select_otd_model(otd_file.models)
            if model is None:
                return

        # 신호 로드
        self.signal_manager.clear_signals()
        from signal_model import Signal
        for otd_sig in model.signals:
            sig_dict = otd_signal_to_signal_dict(otd_sig)
            self.signal_manager.add_signal(Signal.from_dict(sig_dict))

        # 패턴 데이터 패널 연동
        if self.pattern_data_panel is not None:
            patterns = [
                {
                    'ptn_no': p.ptn_no, 'name': p.name,
                    'r_v1': p.r_v1, 'r_v2': p.r_v2, 'r_v3': p.r_v3, 'r_v4': p.r_v4,
                    'g_v1': p.g_v1, 'g_v2': p.g_v2, 'g_v3': p.g_v3, 'g_v4': p.g_v4,
                    'b_v1': p.b_v1, 'b_v2': p.b_v2, 'b_v3': p.b_v3, 'b_v4': p.b_v4,
                    'w_v1': p.w_v1, 'w_v2': p.w_v2, 'w_v3': p.w_v3, 'w_v4': p.w_v4,
                    'ptn_type': p.ptn_type,
                }
                for p in model.patterns
            ]
            self.pattern_data_panel.set_patterns(patterns)

        # SyncData / 주파수 업데이트
        freq = round(model.sync_freq_hz)
        sync_val = model.sync_data_us
        self.sync_data_manager._update_from_otd(model.model_num, model.name,
                                                 freq, sync_val)
        self._update_sync_data_display()
        if self.timing_viewer:
            self.timing_viewer.update_plot()

        messagebox.showinfo("완료",
            f"OTD 불러오기 완료:\n"
            f"모델: {model.model_num} - {model.name}\n"
            f"신호: {len(model.signals)}개 / 패턴: {len(model.patterns)}개")

    def _select_otd_model(self, models):
        """복수 모델 선택 팝업"""
        dlg = tk.Toplevel(self)
        dlg.title("모델 선택")
        dlg.grab_set()
        selected = [None]

        tk.Label(dlg, text="불러올 모델을 선택하세요:", font=('Arial', 10)).pack(padx=10, pady=5)

        lb = tk.Listbox(dlg, font=('Arial', 9), width=40, height=min(len(models), 10))
        for m in models:
            lb.insert(tk.END, f"MODEL {m.model_num}: {m.name}  [{m.sync_freq_hz:.1f}Hz]")
        lb.pack(padx=10, pady=5)
        lb.selection_set(0)

        def _ok():
            idx = lb.curselection()
            if idx:
                selected[0] = models[idx[0]]
            dlg.destroy()

        tk.Button(dlg, text="확인", command=_ok, bg='#4CAF50', fg='black',
                  font=('Arial', 9, 'bold'), width=10).pack(pady=5)
        dlg.wait_window()
        return selected[0]

    # ──────────────────────────────────────────────────────────────
    # Excel PG Signal 불러오기
    # ──────────────────────────────────────────────────────────────
    def _on_load_excel(self):
        """
        사용자 PG Signal 엑셀 파일 불러오기
        A~N열 신호 데이터 + P/Q열 SyncData 파싱 후 신호 반영.
        """
        from tkinter import filedialog
        try:
            from excel_importer import import_excel_pg_signals
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
            result = import_excel_pg_signals(filepath)
        except Exception as e:
            messagebox.showerror("오류", f"Excel 파싱 실패:\n{e}")
            return

        if result.errors:
            messagebox.showwarning("경고", "\n".join(result.errors))

        if not result.signals:
            messagebox.showwarning("경고", "불러온 신호가 없습니다.\n엑셀 형식을 확인하세요.")
            return

        from signal_model import Signal
        self.signal_manager.clear_signals()
        for sig_dict in result.signals:
            self.signal_manager.add_signal(Signal.from_dict(sig_dict))

        # SyncData 업데이트
        if result.sync_data_us > 0 or result.frequency_hz > 0:
            self.sync_data_manager._update_from_otd(
                'EXCEL', result.model_name,
                round(result.frequency_hz), result.sync_data_us
            )
            self._update_sync_data_display()
            if self.timing_viewer:
                self.timing_viewer.update_plot()

        messagebox.showinfo("완료",
            f"Excel 불러오기 완료:\n신호: {len(result.signals)}개\n"
            f"주파수: {result.frequency_hz:.1f} Hz")

    # ──────────────────────────────────────────────────────────────
    # OTD 내보내기
    # ──────────────────────────────────────────────────────────────
    def _on_export_otd(self):
        """
        현재 신호/패턴 데이터를 OTD 파일로 내보내기.
        """
        from tkinter import filedialog
        try:
            from otd_exporter import OtdExporter
        except ImportError as e:
            messagebox.showerror("오류", f"OTD 내보내기 모듈 로드 실패:\n{e}")
            return

        signals = self.signal_manager.get_all_signals()
        if not signals:
            messagebox.showwarning("경고", "내보낼 신호가 없습니다.")
            return

        model = self.sync_data_manager.current_model or 'MODEL'
        freq  = self.sync_data_manager.current_frequency or 60
        default_filename = f"{model}_export.otd"

        filepath = filedialog.asksaveasfilename(
            defaultextension=".otd",
            filetypes=[("OTD files", "*.otd"), ("All files", "*.*")],
            initialfile=default_filename,
            title="OTD 파일 저장"
        )
        if not filepath:
            return

        # 패턴 데이터
        patterns = []
        if self.pattern_data_panel is not None:
            patterns = self.pattern_data_panel.get_patterns()

        model_data = [{
            'model_num': '001',
            'name': model,
            'frequency_hz': float(freq),
            'sync_cntr': 0,
            'signals': [s.to_dict() for s in signals],
            'patterns': patterns,
        }]

        exporter = OtdExporter()
        if exporter.export(filepath, model_data):
            messagebox.showinfo("완료", f"OTD 파일 저장:\n{filepath}")
        else:
            messagebox.showerror("오류", "OTD 파일 저장에 실패했습니다.")

    # ──────────────────────────────────────────────────────────────
    # Excel 파형 시각화 내보내기
    # ──────────────────────────────────────────────────────────────
    def _on_export_excel_waveform(self):
        """
        현재 신호 데이터를 엑셀 파형 시각화로 내보내기.
        셀 테두리로 HIGH/LOW 파형을 표현, 25% 줌, 구간 라벨+시간 화살표 포함.
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

        model = self.sync_data_manager.current_model or 'MODEL'
        freq  = self.sync_data_manager.current_frequency or 60
        sync_data_s = self.sync_data_manager.get_current_sync_data()
        sync_data_us = sync_data_s * 1_000_000

        default_filename = f"{model}_waveform.xlsx"
        filepath = filedialog.asksaveasfilename(
            defaultextension=".xlsx",
            filetypes=[("Excel files", "*.xlsx"), ("All files", "*.*")],
            initialfile=default_filename,
            title="Excel 파형 시각화 저장"
        )
        if not filepath:
            return

        sig_dicts = [s.to_dict() for s in visible_signals]
        exporter = ExcelWaveformExporter()
        try:
            exporter.export(filepath, sig_dicts, sync_data_us, model)
            messagebox.showinfo("완료", f"Excel 파형 시각화 저장:\n{filepath}")
        except Exception as e:
            messagebox.showerror("오류", f"Excel 파형 저장 실패:\n{e}")

    # ──────────────────────────────────────────────────────────────
    # 포맷 파일 생성
    # ──────────────────────────────────────────────────────────────
    def _on_create_format(self):
        """
        빈 OTD 포맷 파일(템플릿) 생성.
        헤더와 빈 모델 구조만 포함된 OTD 파일을 저장합니다.
        """
        from tkinter import filedialog, simpledialog
        try:
            from otd_exporter import OtdExporter
        except ImportError as e:
            messagebox.showerror("오류", f"OTD 내보내기 모듈 로드 실패:\n{e}")
            return

        model_count = simpledialog.askinteger(
            "포맷 파일 생성",
            "생성할 빈 모델 수를 입력하세요:",
            initialvalue=1, minvalue=1, maxvalue=20
        )
        if model_count is None:
            return

        filepath = filedialog.asksaveasfilename(
            defaultextension=".otd",
            filetypes=[("OTD files", "*.otd"), ("All files", "*.*")],
            initialfile="format_template.otd",
            title="OTD 포맷 파일 저장"
        )
        if not filepath:
            return

        exporter = OtdExporter()
        if exporter.export_format_file(filepath, model_count):
            messagebox.showinfo("완료", f"포맷 파일 생성:\n{filepath}")
        else:
            messagebox.showerror("오류", "포맷 파일 생성에 실패했습니다.")

    def _on_manage_models(self):
        """
        모델 관리 버튼 핸들러
        
        모델 관리 다이얼로그를 열고, 변경 사항이 있으면 UI를 갱신합니다.
        """
        from model_manager_dialog import ModelManagerDialog
        
        dialog = ModelManagerDialog(self, self.sync_data_manager)
        result = dialog.get_result()
        
        if result:
            # 모델 목록 갱신
            self.model_combo['values'] = self.sync_data_manager.get_model_list()
            if self.model_combo['values']:
                # 현재 모델 유지 시도
                current_model = self.sync_data_manager.current_model
                models = self.sync_data_manager.get_model_list()
                if current_model in models:
                    self.model_combo.set(current_model)
                else:
                    self.model_combo.current(0)
                
                self._update_frequency_list()
                self._update_sync_data_display()
                self.timing_viewer.update_plot()
    
    def _on_export_excel(self):
        """
        Excel 내보내기 버튼 핸들러
        
        현재 표시된 모든 신호의 파형 데이터를 Excel 파일로 내보냅니다.
        """
        try:
            import pandas as pd
        except ImportError:
            messagebox.showerror("오류", "pandas 라이브러리가 필요합니다.\n'pip install pandas openpyxl'을 실행하세요.")
            return
        
        signals = self.signal_manager.get_all_signals()
        visible_signals = [s for s in signals if getattr(s, 'visible', True)]
        
        if not visible_signals:
            messagebox.showwarning("경고", "내보낼 신호가 없습니다.")
            return
        
        from waveform_generator import WaveformGenerator
        from tkinter import filedialog
        
        # 파일 저장 경로 선택
        model = self.sync_data_manager.current_model
        freq = self.sync_data_manager.current_frequency
        default_filename = f"{model}_{freq}Hz_waveforms.xlsx"
        
        filepath = filedialog.asksaveasfilename(
            defaultextension=".xlsx",
            filetypes=[("Excel files", "*.xlsx"), ("All files", "*.*")],
            initialfile=default_filename
        )
        
        if not filepath:
            return
        
        # 파형 데이터 생성
        sync_data = self.sync_data_manager.get_current_sync_data()
        num_frames = self.timing_viewer.num_frames
        
        # 모든 신호의 데이터를 하나의 DataFrame으로 결합
        all_data = {}
        
        for signal in visible_signals:
            time, voltage = WaveformGenerator.generate_waveform(signal, num_frames, sync_data)
            
            # 첫 번째 신호의 시간 데이터 저장
            if 'Time (us)' not in all_data:
                all_data['Time (us)'] = time
            
            # 각 신호의 전압 데이터 저장
            all_data[f"{signal.name} (V)"] = voltage
        
        # DataFrame 생성 및 Excel 저장
        df = pd.DataFrame(all_data)
        
        try:
            with pd.ExcelWriter(filepath, engine='openpyxl') as writer:
                # 파형 데이터 시트
                df.to_excel(writer, sheet_name='Waveform Data', index=False)
                
                # 신호 파라미터 시트
                params_data = []
                for signal in visible_signals:
                    params_data.append({
                        'Name': signal.name,
                        'Type': signal.sig_type,
                        'SIG MODE': signal.sig_mode,
                        'INVERSION': signal.inversion,
                        'V1 (V)': signal.v1,
                        'V2 (V)': signal.v2,
                        'V3 (V)': signal.v3,
                        'V4 (V)': signal.v4,
                        'Delay (us)': signal.delay,
                        'Width (us)': signal.width,
                        'Period (us)': signal.period,
                        'Color': signal.color
                    })
                
                params_df = pd.DataFrame(params_data)
                params_df.to_excel(writer, sheet_name='Signal Parameters', index=False)
                
                # 모델 정보 시트
                info_data = {
                    'Parameter': ['Model', 'Frequency (Hz)', 'SyncData (s)', 'Num Frames'],
                    'Value': [model, freq, sync_data, num_frames]
                }
                info_df = pd.DataFrame(info_data)
                info_df.to_excel(writer, sheet_name='Model Info', index=False)
            
            messagebox.showinfo("완료", f"Excel 파일이 저장되었습니다:\n{filepath}")
        
        except Exception as e:
            messagebox.showerror("오류", f"Excel 파일 저장 실패:\n{str(e)}")
