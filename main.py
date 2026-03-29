"""
TOSG-400M 패턴 신호 뷰어 v2
다중 모델 아키텍처 (ModelStore) 기반

레이아웃:
  상단: 제어 패널 (ControlPanel)
  중앙 좌측: 모델 목록 (ModelListPanel) + 탭 노트북
        탭1: 신호 편집 (Signal Table + Editor)
        탭2: 패턴 데이터 (PatternDataPanel)
        탭3: MULTIREMOTE (MultiRemotePanel)
  중앙 우측: 타이밍 다이어그램 (TimingViewer)
  하단: 상태 표시줄
"""

import tkinter as tk
from tkinter import ttk
import sys
import os

sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

from signal_model import SignalManager
from sync_data import SyncDataManager
from signal_storage import SignalStorage
from timing_viewer import TimingViewer
from signal_table_widget import SignalTableWidget
from signal_editor_panel import SignalEditorPanel
from control_panel import ControlPanel
from pattern_data_panel import PatternDataPanel
from model_store import ModelStore
from model_list_panel import ModelListPanel
from multiremote_panel import MultiRemotePanel


class MainApplication(tk.Tk):
    """메인 애플리케이션 v2 (다중 모델 지원)"""

    def __init__(self):
        super().__init__()
        self.title("TOSG-400M Pattern Signal Viewer")
        self.geometry("1900x1050")
        self.configure(bg='#f0f0f0')

        # ── 공유 관리자 초기화 ────────────────────────────────
        self.model_store       = ModelStore()
        self.sync_data_manager = SyncDataManager(
            config_file='config/models_config.json')
        self.signal_storage    = SignalStorage(
            storage_dir='data/signal_data')
        self.signal_manager    = SignalManager()

        self._setup_ui()

    def _setup_ui(self):
        # ── 상단: 제어 패널 ───────────────────────────────────
        # (pattern_data_panel과 model_store는 아래에서 생성 후 연결)
        self.control_panel = ControlPanel(
            self,
            self.sync_data_manager,
            None,               # timing_viewer: 나중에 연결
            self.signal_manager,
            self.signal_storage,
            model_store=self.model_store,
        )
        self.control_panel.pack(side=tk.TOP, fill=tk.X, padx=4, pady=4)

        # ── 중앙 ─────────────────────────────────────────────
        center = tk.Frame(self, bg='#f0f0f0')
        center.pack(fill=tk.BOTH, expand=True, padx=4, pady=4)

        paned = ttk.PanedWindow(center, orient=tk.HORIZONTAL)
        paned.pack(fill=tk.BOTH, expand=True)

        # ── 좌측: 모델 목록 + 탭 ─────────────────────────────
        left_outer = tk.Frame(paned, bg='#e0e0e0')

        # 모델 목록 패널
        self.model_list_panel = ModelListPanel(
            left_outer,
            self.model_store,
            self.signal_manager,
            self.sync_data_manager,
            timing_viewer=None,     # 나중에 연결
            pattern_data_panel=None,
        )
        self.model_list_panel.pack(side=tk.TOP, fill=tk.X)

        # 탭 노트북
        nb = ttk.Notebook(left_outer)
        nb.pack(side=tk.TOP, fill=tk.BOTH, expand=True)

        # 탭1: 신호 편집
        sig_tab = tk.Frame(nb, bg='#f5f5f5')
        nb.add(sig_tab, text='  신호 편집  ')

        tbl_frame = tk.LabelFrame(sig_tab, text="신호 목록",
                                  font=('Arial', 10, 'bold'),
                                  bg='#f0f0f0', padx=4, pady=4)
        tbl_frame.pack(fill=tk.BOTH, expand=False, pady=(0, 3))
        tbl_frame.configure(height=200)

        self.signal_table = SignalTableWidget(
            tbl_frame, self.signal_manager, self._on_edit_signal)
        self.signal_table.pack(fill=tk.BOTH, expand=True)

        edt_frame = tk.LabelFrame(sig_tab, text="신호 편집기",
                                  font=('Arial', 10, 'bold'),
                                  bg='#f0f0f0', padx=4, pady=4)
        edt_frame.pack(fill=tk.BOTH, expand=True, pady=(3, 0))

        self.signal_editor = SignalEditorPanel(edt_frame, self.signal_manager)
        self.signal_editor.pack(fill=tk.BOTH, expand=True)

        # 탭2: 패턴 데이터
        ptn_tab = tk.Frame(nb, bg='#f5f5f5')
        nb.add(ptn_tab, text='  패턴 데이터  ')
        self.pattern_panel = PatternDataPanel(ptn_tab)
        self.pattern_panel.pack(fill=tk.BOTH, expand=True)

        # 탭3: MULTIREMOTE
        mrt_tab = tk.Frame(nb, bg='#f5f5f5')
        nb.add(mrt_tab, text='  MULTIREMOTE  ')
        self.multiremote_panel = MultiRemotePanel(mrt_tab, self.model_store)
        self.multiremote_panel.pack(fill=tk.BOTH, expand=True)

        paned.add(left_outer, weight=1)

        # ── 우측: 타이밍 다이어그램 ──────────────────────────
        viewer_frame = tk.LabelFrame(paned, text="타이밍 다이어그램",
                                     font=('Arial', 11, 'bold'),
                                     bg='#f0f0f0', padx=4, pady=4)
        self.timing_viewer = TimingViewer(
            viewer_frame, self.signal_manager, self.sync_data_manager)
        self.timing_viewer.pack(fill=tk.BOTH, expand=True)
        paned.add(viewer_frame, weight=3)

        # ── 지연 연결 (패널 생성 후 참조 업데이트) ───────────
        self.control_panel.timing_viewer      = self.timing_viewer
        self.control_panel.pattern_data_panel = self.pattern_panel

        self.model_list_panel.timing_viewer     = self.timing_viewer
        self.model_list_panel.pattern_data_panel = self.pattern_panel

        # ── 하단: 상태 표시줄 ────────────────────────────────
        self.statusbar = tk.Label(
            self, text="준비", bd=1, relief=tk.SUNKEN,
            anchor=tk.W, font=('Arial', 9), bg='#d8d8d8', fg='#000')
        self.statusbar.pack(side=tk.BOTTOM, fill=tk.X)

        self.signal_manager.add_listener(self._update_status)
        self.model_store.add_listener(self._update_status)
        self._update_status()

    def _on_edit_signal(self, index):
        self.signal_editor.edit_signal(index)

    def _update_status(self):
        n_sigs    = len(self.signal_manager.get_all_signals())
        n_models  = len(self.model_store.models)
        n_mrts    = len(self.model_store.multiremote_groups)
        cur_model = (self.model_store.current_model.display_name
                     if self.model_store.current_model else "없음")
        freq      = self.sync_data_manager.current_frequency or '-'
        n_ptns    = (len(self.pattern_panel.get_patterns())
                     if hasattr(self, 'pattern_panel') else 0)
        self.statusbar.config(
            text=(f"모델: {n_models}개 | 현재: {cur_model} | "
                  f"신호: {n_sigs}개 | 패턴: {n_ptns}개 | "
                  f"MRT: {n_mrts}개 | 주파수: {freq}Hz")
        )


def main():
    app = MainApplication()
    app.mainloop()


if __name__ == '__main__':
    main()
