"""
모델 목록 패널 (ModelListPanel)

로드된 전체 모델 목록을 Listbox로 표시합니다.
사용자가 모델을 클릭하면 해당 모델의 신호/패턴 데이터를 UI에 반영합니다.

연동 컴포넌트:
  - SignalManager: 선택 모델의 신호로 교체
  - PatternDataPanel: 선택 모델의 패턴으로 교체
  - SyncDataManager: 선택 모델의 주파수/SyncData로 업데이트
  - TimingViewer: 파형 다이어그램 갱신

피드백 2번:
  OTD 불러오기 후 팝업 없이 이 패널에 전체 모델이 표시되며,
  클릭 시 해당 모델의 신호/패턴/MULTIREMOTE가 자동 표시됩니다.
"""

import tkinter as tk
from tkinter import ttk


def _is_zero_signal(sig) -> bool:
    """신호의 모든 전압/타이밍 값이 0인지 확인 (편집되지 않은 빈 신호)"""
    return (
        getattr(sig, 'v1', 0) == 0 and getattr(sig, 'v2', 0) == 0 and
        getattr(sig, 'v3', 0) == 0 and getattr(sig, 'v4', 0) == 0 and
        getattr(sig, 'delay', 0) == 0 and getattr(sig, 'width', 0) == 0 and
        getattr(sig, 'period', 0) == 0
    )


class ModelListPanel(tk.Frame):
    """
    좌측 모델 선택 패널

    ModelStore에서 모델 목록을 가져와 Listbox로 표시하고,
    클릭 시 관련 UI 컴포넌트를 해당 모델 데이터로 갱신합니다.

    Attributes:
        model_store: ModelStore 인스턴스
        signal_manager: SignalManager 인스턴스
        sync_data_manager: SyncDataManager 인스턴스
        timing_viewer: TimingViewer 인스턴스 (지연 연결)
        pattern_data_panel: PatternDataPanel 인스턴스 (지연 연결)
        _listbox: 모델 목록 Listbox 위젯
        _count_var: 모델 수 표시 StringVar
    """

    def __init__(self, parent, model_store, signal_manager,
                 sync_data_manager, timing_viewer=None,
                 pattern_data_panel=None, listbox_height=8):
        """
        초기화 메서드

        Args:
            parent: 부모 위젯
            model_store: ModelStore 인스턴스
            signal_manager: SignalManager 인스턴스
            sync_data_manager: SyncDataManager 인스턴스
            timing_viewer: TimingViewer (나중에 연결 가능)
            pattern_data_panel: PatternDataPanel (나중에 연결 가능)
            listbox_height: Listbox 표시 행 수 (기본 8)
        """
        super().__init__(parent, bg='#e8e8e8')
        self.model_store        = model_store
        self.signal_manager     = signal_manager
        self.sync_data_manager  = sync_data_manager
        self.timing_viewer      = timing_viewer
        self.pattern_data_panel = pattern_data_panel
        self._listbox_height    = listbox_height
        self._plot_after_id     = None  # 비동기 plot 예약 ID

        self._setup_ui()
        # ModelStore 변경 시 자동 갱신 등록
        self.model_store.add_listener(self._refresh)

    # ──────────────────────────────────────────────────────────────
    # UI 구성
    # ──────────────────────────────────────────────────────────────

    def _setup_ui(self):
        """Listbox + 스크롤바 UI 구성"""
        # 헤더 레이블
        header = tk.Label(
            self, text="MODEL LIST",
            font=('Arial', 12, 'bold'),
            bg='#555555', fg='white', pady=6
        )
        header.pack(side=tk.TOP, fill=tk.X)

        # Listbox 프레임
        listframe = tk.Frame(self, bg='#e8e8e8')
        listframe.pack(side=tk.TOP, fill=tk.BOTH, expand=True, padx=4, pady=4)

        self._listbox = tk.Listbox(
            listframe,
            font=('Consolas', 9),
            bg='#ffffff', fg='#1a1a1a',
            selectbackground='#2980b9',
            selectforeground='white',
            activestyle='none',
            height=self._listbox_height
        )
        vsb = ttk.Scrollbar(listframe, orient='vertical',
                             command=self._listbox.yview)
        self._listbox.configure(yscrollcommand=vsb.set)
        self._listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        vsb.pack(side=tk.RIGHT, fill=tk.Y)

        # 클릭 이벤트: 모델 선택
        self._listbox.bind('<<ListboxSelect>>', self._on_select)

        # 하단 모델 수 표시
        self._count_var = tk.StringVar(value="모델 없음")
        tk.Label(
            self, textvariable=self._count_var,
            font=('Arial', 8), bg='#e8e8e8', fg='#555'
        ).pack(side=tk.BOTTOM, pady=2)

    # ──────────────────────────────────────────────────────────────
    # ModelStore 갱신 콜백
    # ──────────────────────────────────────────────────────────────

    def _refresh(self):
        """
        ModelStore 변경 시 Listbox 갱신

        모델 목록을 다시 그리고, 현재 선택 모델을 복원합니다.
        OTD/Excel 불러오기 후 자동 호출됩니다.
        """
        self._listbox.delete(0, tk.END)
        for m in self.model_store.models:
            self._listbox.insert(tk.END, m.display_name)

        # 현재 선택 인덱스 복원
        idx = self.model_store.current_index
        if 0 <= idx < len(self.model_store.models):
            self._listbox.selection_set(idx)
            self._listbox.see(idx)

        count = len(self.model_store.models)
        self._count_var.set(f"총 {count}개 모델" if count else "모델 없음")

        # 첫 번째 모델을 자동으로 선택하여 내용 표시
        if count > 0 and self.model_store.current_index >= 0:
            self._load_model(self.model_store.current_index)

    # ──────────────────────────────────────────────────────────────
    # 모델 선택 핸들러
    # ──────────────────────────────────────────────────────────────

    def _on_select(self, event=None):
        """
        모델 클릭 이벤트: 선택된 모델 데이터로 UI 갱신

        피드백 2번: 클릭 시 해당 모델의 신호/패턴/타이밍 정보를 표시
        """
        sel = self._listbox.curselection()
        if not sel:
            return
        self._load_model(sel[0])

    def _load_model(self, idx: int):
        """
        지정 인덱스의 모델 데이터를 UI에 반영

        Args:
            idx: ModelStore.models의 인덱스
        """
        if not (0 <= idx < len(self.model_store.models)):
            return

        model = self.model_store.models[idx]
        # ModelStore의 현재 인덱스만 업데이트 (notify 없이)
        self.model_store._current_idx = idx

        # ── 신호 목록 갱신 ────────────────────────────────────────
        from signal_model import Signal
        self.signal_manager.clear_signals()
        for sig in model.signals:
            if isinstance(sig, Signal):
                if _is_zero_signal(sig):
                    sig.visible = False
                self.signal_manager.add_signal(sig)
            elif isinstance(sig, dict):
                s = Signal.from_dict(sig)
                if _is_zero_signal(s):
                    s.visible = False
                self.signal_manager.add_signal(s)

        # ── 패턴 데이터 갱신 ──────────────────────────────────────
        if self.pattern_data_panel is not None:
            self.pattern_data_panel.set_patterns(model.patterns)

        # ── SyncData / 주파수 갱신 ────────────────────────────────
        self.sync_data_manager._update_from_otd(
            model.model_num,
            model.name,
            int(round(model.frequency_hz)),
            model.sync_data_us
        )

        # ── 타이밍 다이어그램 갱신 (비동기: 빠른 클릭 시 불필요한 연산 방지) ──
        if self.timing_viewer:
            # 기존 대기 중인 업데이트 취소 후 새로 예약
            if hasattr(self, '_plot_after_id') and self._plot_after_id:
                try:
                    self.after_cancel(self._plot_after_id)
                except Exception:
                    pass
            self._plot_after_id = self.after(50, self._deferred_update_plot)

    def _deferred_update_plot(self):
        """비동기 타이밍 다이어그램 갱신 (after() 콜백)"""
        self._plot_after_id = None
        if self.timing_viewer:
            self.timing_viewer.update_plot()

    def set_timing_viewer(self, tv):
        """타이밍 뷰어 참조 업데이트"""
        self.timing_viewer = tv

    def set_pattern_panel(self, pp):
        """패턴 데이터 패널 참조 업데이트"""
        self.pattern_data_panel = pp
