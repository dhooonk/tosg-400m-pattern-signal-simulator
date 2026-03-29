"""
모델 목록 패널 (ModelListPanel)

로드된 전체 모델을 Listbox로 표시하고,
클릭하면 SignalManager와 PatternDataPanel을 해당 모델 데이터로 업데이트합니다.
"""

import tkinter as tk
from tkinter import ttk


class ModelListPanel(tk.Frame):
    """
    좌측 모델 선택 패널

    ModelStore에서 모델 목록을 가져와 리스트박스로 표시.
    선택 시:
      - signal_manager 의 신호를 해당 모델 신호로 교체
      - pattern_data_panel 의 패턴을 해당 모델 패턴으로 교체
      - sync_data_manager 를 해당 모델 주파수/SyncData 로 업데이트
      - timing_viewer 업데이트
    """

    def __init__(self, parent, model_store, signal_manager,
                 sync_data_manager, timing_viewer=None,
                 pattern_data_panel=None):
        super().__init__(parent, bg='#e8e8e8')
        self.model_store       = model_store
        self.signal_manager    = signal_manager
        self.sync_data_manager = sync_data_manager
        self.timing_viewer     = timing_viewer
        self.pattern_data_panel = pattern_data_panel

        self._setup_ui()
        self.model_store.add_listener(self._refresh)

    # ──────────────────────────────────────────────────────────
    def _setup_ui(self):
        header = tk.Label(self, text="MODEL LIST",
                          font=('Arial', 10, 'bold'),
                          bg='#2c3e50', fg='white',
                          pady=6)
        header.pack(side=tk.TOP, fill=tk.X)

        listframe = tk.Frame(self, bg='#e8e8e8')
        listframe.pack(side=tk.TOP, fill=tk.BOTH, expand=True, padx=4, pady=4)

        self._listbox = tk.Listbox(listframe,
                                   font=('Consolas', 9),
                                   bg='#ffffff', fg='#1a1a1a',
                                   selectbackground='#2980b9',
                                   selectforeground='white',
                                   activestyle='none',
                                   height=20)
        vsb = ttk.Scrollbar(listframe, orient='vertical',
                             command=self._listbox.yview)
        self._listbox.configure(yscrollcommand=vsb.set)
        self._listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        vsb.pack(side=tk.RIGHT, fill=tk.Y)

        self._listbox.bind('<<ListboxSelect>>', self._on_select)

        # 하단 카운트 표시
        self._count_var = tk.StringVar(value="모델 없음")
        tk.Label(self, textvariable=self._count_var,
                 font=('Arial', 8), bg='#e8e8e8', fg='#555').pack(
            side=tk.BOTTOM, pady=2)

    # ──────────────────────────────────────────────────────────
    def _refresh(self):
        """ModelStore 변경 시 리스트 갱신"""
        self._listbox.delete(0, tk.END)
        for m in self.model_store.models:
            self._listbox.insert(tk.END, m.display_name)

        # 현재 선택 복원
        idx = self.model_store.current_index
        if 0 <= idx < len(self.model_store.models):
            self._listbox.selection_set(idx)
            self._listbox.see(idx)

        count = len(self.model_store.models)
        self._count_var.set(f"총 {count}개 모델" if count else "모델 없음")

    def _on_select(self, event=None):
        """모델 선택 시 UI 컴포넌트 업데이트"""
        sel = self._listbox.curselection()
        if not sel:
            return
        idx = sel[0]
        model = self.model_store.models[idx]
        self.model_store._current_idx = idx  # notify 없이 인덱스만 업데이트

        # ── 신호 업데이트 ────────────────────────────────────
        from signal_model import Signal
        self.signal_manager.clear_signals()
        for sig in model.signals:
            if isinstance(sig, Signal):
                self.signal_manager.add_signal(sig)
            elif isinstance(sig, dict):
                self.signal_manager.add_signal(Signal.from_dict(sig))

        # ── 패턴 업데이트 ────────────────────────────────────
        if self.pattern_data_panel is not None:
            self.pattern_data_panel.set_patterns(model.patterns)

        # ── SyncData 업데이트 ────────────────────────────────
        self.sync_data_manager._update_from_otd(
            model.model_num, model.name,
            int(round(model.frequency_hz)), model.sync_data_us
        )

        # ── 타이밍 뷰어 업데이트 ────────────────────────────
        if self.timing_viewer:
            self.timing_viewer.update_plot()

    def set_timing_viewer(self, tv):
        self.timing_viewer = tv

    def set_pattern_panel(self, pp):
        self.pattern_data_panel = pp
