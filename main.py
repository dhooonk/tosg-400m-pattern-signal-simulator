"""
TOSG-400M 패턴 신호 뷰어 (TOSG-400M Pattern Signal Viewer)
메인 애플리케이션 진입점

타이밍 신호 시각화 프로그램의 메인 윈도우와 전체 구조를 정의합니다.
"""

import tkinter as tk
from tkinter import ttk
import sys
import os

# src 디렉토리를 모듈 검색 경로에 추가
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

from signal_model import SignalManager
from sync_data import SyncDataManager
from signal_storage import SignalStorage
from timing_viewer import TimingViewer
from signal_table_widget import SignalTableWidget
from signal_editor_panel import SignalEditorPanel
from control_panel import ControlPanel
from pattern_data_panel import PatternDataPanel


class MainApplication(tk.Tk):
    """
    메인 애플리케이션 클래스

    레이아웃:
      상단: 제어 패널 (ControlPanel)
      중앙 좌: 탭 노트북 (신호 목록+편집기 / 패턴 데이터)
      중앙 우: 타이밍 다이어그램 (TimingViewer)
      하단: 상태 표시줄
    """

    def __init__(self):
        super().__init__()

        self.title("TOSG-400M Pattern Signal Viewer")
        self.geometry("1800x1050")
        self.configure(bg='#f5f5f5')

        self.sync_data_manager = SyncDataManager(config_file='config/models_config.json')
        self.signal_storage    = SignalStorage(storage_dir='data/signal_data')
        self.signal_manager    = SignalManager()

        self._setup_ui()
        self._load_initial_signals()

    def _setup_ui(self):
        """UI 구성"""
        main_container = tk.Frame(self, bg='#f5f5f5')
        main_container.pack(fill=tk.BOTH, expand=True)

        # ── 상단: 제어 패널 ────────────────────────────────────
        # PatternDataPanel을 먼저 더미로 만들고 ControlPanel에 참조 전달.
        # (ControlPanel 생성 시 pattern_data_panel 인수가 필요하기 때문)
        # 이후 실제 패널로 교체해 ControlPanel 참조를 업데이트.
        self._dummy_pattern = PatternDataPanel(main_container)

        self.control_panel = ControlPanel(
            main_container,
            self.sync_data_manager,
            None,
            self.signal_manager,
            self.signal_storage,
            pattern_data_panel=self._dummy_pattern,
        )
        self.control_panel.pack(side=tk.TOP, fill=tk.X, padx=5, pady=5)

        # ── 중앙: 좌우 PanedWindow ────────────────────────────
        paned = ttk.PanedWindow(main_container, orient=tk.HORIZONTAL)
        paned.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        # ── 좌측: 탭 노트북 ──────────────────────────────────
        left_notebook = ttk.Notebook(paned)

        # 탭 1 – 신호 편집
        signal_tab = tk.Frame(left_notebook, bg='#f5f5f5')
        left_notebook.add(signal_tab, text='  신호 편집  ')

        table_frame = tk.LabelFrame(signal_tab, text="신호 목록",
                                    font=('Arial', 10, 'bold'), padx=4, pady=4,
                                    bg='#f0f0f0', fg='#000')
        table_frame.pack(side=tk.TOP, fill=tk.BOTH, expand=False, pady=(0, 4))
        table_frame.configure(height=230)

        self.signal_table = SignalTableWidget(
            table_frame, self.signal_manager, self._on_edit_signal)
        self.signal_table.pack(fill=tk.BOTH, expand=True)

        editor_frame = tk.LabelFrame(signal_tab, text="신호 편집기",
                                     font=('Arial', 10, 'bold'), padx=4, pady=4,
                                     bg='#f0f0f0', fg='#000')
        editor_frame.pack(side=tk.TOP, fill=tk.BOTH, expand=True, pady=(4, 0))

        self.signal_editor = SignalEditorPanel(editor_frame, self.signal_manager)
        self.signal_editor.pack(fill=tk.BOTH, expand=True)

        # 탭 2 – 패턴 데이터
        pattern_tab = tk.Frame(left_notebook, bg='#f5f5f5')
        left_notebook.add(pattern_tab, text='  패턴 데이터  ')

        # 더미 패널 제거하고 실제 패널 생성
        self._dummy_pattern.destroy()
        self.pattern_panel = PatternDataPanel(pattern_tab)
        self.pattern_panel.pack(fill=tk.BOTH, expand=True)
        # ControlPanel 참조 업데이트
        self.control_panel.pattern_data_panel = self.pattern_panel

        paned.add(left_notebook, weight=1)

        # ── 우측: 타이밍 다이어그램 ──────────────────────────
        viewer_frame = tk.LabelFrame(paned, text="타이밍 다이어그램",
                                     font=('Arial', 11, 'bold'), padx=4, pady=4,
                                     bg='#f0f0f0', fg='#000')

        self.timing_viewer = TimingViewer(
            viewer_frame, self.signal_manager, self.sync_data_manager)
        self.timing_viewer.pack(fill=tk.BOTH, expand=True)
        paned.add(viewer_frame, weight=3)

        # 제어 패널에 타이밍 뷰어 연결
        self.control_panel.timing_viewer = self.timing_viewer

        # ── 하단: 상태 표시줄 ────────────────────────────────
        self.statusbar = tk.Label(self, text="준비", bd=1, relief=tk.SUNKEN,
                                  anchor=tk.W, font=('Arial', 9),
                                  bg='#e0e0e0', fg='#000')
        self.statusbar.pack(side=tk.BOTTOM, fill=tk.X)

        self._update_statusbar()
        self.signal_manager.add_listener(self._update_statusbar)

    def _on_edit_signal(self, index):
        self.signal_editor.edit_signal(index)

    def _update_statusbar(self):
        num_signals  = len(self.signal_manager.get_all_signals())
        model        = self.sync_data_manager.current_model
        freq         = self.sync_data_manager.current_frequency
        num_patterns = len(self.pattern_panel.get_patterns()) \
                       if hasattr(self, 'pattern_panel') else 0
        self.statusbar.config(
            text=f"신호: {num_signals}개 | 패턴: {num_patterns}개 | 모델: {model} | 주파수: {freq}Hz"
        )

    def _load_initial_signals(self):
        model = self.sync_data_manager.current_model
        signals = self.signal_storage.load_signals(model)
        if signals:
            for signal in signals:
                self.signal_manager.add_signal(signal)
            self._update_statusbar()


def main():
    app = MainApplication()
    app.mainloop()


if __name__ == '__main__':
    main()
