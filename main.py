"""
TOSG-400M 패턴 신호 뷰어 메인 애플리케이션

다중 모델 아키텍처(ModelStore) 기반의 OTD/Excel 파형 편집 도구입니다.

레이아웃:
  상단: 제어 패널 (ControlPanel) — 파일 I/O 및 뷰 제어
  중앙:
    좌측: 모델 목록 (ModelListPanel) + 탭 노트북
          탭1: 신호 편집 (SignalTableWidget + SignalEditorPanel)
          탭2: 패턴 데이터 (PatternDataPanel)
          탭3: MULTIREMOTE (MultiRemotePanel)
    우측: 타이밍 다이어그램 (TimingViewer)
  하단: 상태 표시줄

주요 변경 (v3):
  - 상단 "모델 설정" 패널 제거 (피드백 1번)
  - OTD/Excel 불러오기 model_store 기반으로 통일 (피드백 2, 3, 4번)
  - SignalEditorPanel에 model_store 전달 (피드백 13번)
"""

import tkinter as tk
from tkinter import ttk
import sys
import os

# src 폴더를 모듈 검색 경로에 추가
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

from signal_model import SignalManager, SignalStorage
from sync_data import SyncDataManager
from timing_viewer import TimingViewer
from signal_table_widget import SignalTableWidget
from signal_editor_panel import SignalEditorPanel
from control_panel import ControlPanel
from pattern_data_panel import PatternDataPanel
from model_store import ModelStore
from model_list_panel import ModelListPanel
from multiremote_panel import MultiRemotePanel


class MainApplication(tk.Tk):
    """
    메인 애플리케이션 클래스

    모든 UI 컴포넌트를 초기화하고 배치합니다.
    공유 관리자(ModelStore, SignalManager, SyncDataManager 등)를
    각 컴포넌트에 주입합니다.
    """

    def __init__(self):
        super().__init__()
        self.title("TOSG-400M Pattern Signal Viewer")
        self.geometry("1900x1050")
        self.configure(bg='#f0f0f0')

        # ── 공유 관리자 초기화 ────────────────────────────────────
        # ModelStore: OTD/Excel에서 불러온 모든 모델을 중앙 관리
        self.model_store       = ModelStore()
        # SyncDataManager: 현재 선택된 모델의 SyncData/주파수 정보 관리
        self.sync_data_manager = SyncDataManager(
            config_file='config/models_config.json')
        # SignalStorage: 신호 JSON 저장/불러오기 (현재 보조 기능)
        self.signal_storage    = SignalStorage(
            storage_dir='data/signal_data')
        # SignalManager: 현재 표시/편집 중인 신호 목록 관리
        self.signal_manager    = SignalManager()

        self._setup_ui()

    def _setup_ui(self):
        """전체 UI 레이아웃 구성"""

        # ── 상단: 제어 패널 ───────────────────────────────────────
        # pattern_data_panel, timing_viewer는 아래에서 생성 후 지연 연결
        self.control_panel = ControlPanel(
            self,
            self.sync_data_manager,
            None,                    # timing_viewer: 나중에 연결
            self.signal_manager,
            self.signal_storage,
            model_store=self.model_store,
        )
        self.control_panel.pack(side=tk.TOP, fill=tk.X, padx=4, pady=4)

        # ── 중앙 영역 ─────────────────────────────────────────────
        center = tk.Frame(self, bg='#f0f0f0')
        center.pack(fill=tk.BOTH, expand=True, padx=4, pady=4)

        paned = ttk.PanedWindow(center, orient=tk.HORIZONTAL)
        paned.pack(fill=tk.BOTH, expand=True)

        # ── 좌측: 모델 목록 + 탭 노트북 ──────────────────────────
        left_outer = tk.Frame(paned, bg='#e0e0e0')

        # 좌측 상단: 모델 목록 패널
        # 모델 클릭 시 signal_manager/pattern_data_panel/timing_viewer 갱신
        self.model_list_panel = ModelListPanel(
            left_outer,
            self.model_store,
            self.signal_manager,
            self.sync_data_manager,
            timing_viewer=None,       # 나중에 연결
            pattern_data_panel=None,  # 나중에 연결
            listbox_height=8,         # 높이 축소 (8줄)
        )
        self.model_list_panel.pack(side=tk.TOP, fill=tk.X)

        # 좌측 하단: 탭 노트북
        nb = ttk.Notebook(left_outer)
        nb.pack(side=tk.TOP, fill=tk.BOTH, expand=True)

        # ── 탭1: 신호 편집 ────────────────────────────────────────
        sig_tab = tk.Frame(nb, bg='#f5f5f5')
        nb.add(sig_tab, text='  신호 편집  ')

        tbl_frame = tk.LabelFrame(
            sig_tab, text="신호 목록",
            font=('Arial', 10, 'bold'),
            bg='#f0f0f0', padx=4, pady=4
        )
        tbl_frame.pack(fill=tk.BOTH, expand=False, pady=(0, 3))
        tbl_frame.configure(height=200)

        self.signal_table = SignalTableWidget(
            tbl_frame, self.signal_manager, self._on_edit_signal
        )
        self.signal_table.pack(fill=tk.BOTH, expand=True)

        edt_frame = tk.LabelFrame(
            sig_tab, text="신호 편집기",
            font=('Arial', 10, 'bold'),
            bg='#f0f0f0', padx=4, pady=4
        )
        edt_frame.pack(fill=tk.BOTH, expand=True, pady=(3, 0))

        # 피드백 13번: model_store를 SignalEditorPanel에 전달
        # → 신호 추가/수정 시 model_store 현재 모델에도 동기화됨
        self.signal_editor = SignalEditorPanel(
            edt_frame, self.signal_manager, self.model_store
        )
        self.signal_editor.pack(fill=tk.BOTH, expand=True)

        # ── 탭2: 패턴 데이터 ──────────────────────────────────────
        ptn_tab = tk.Frame(nb, bg='#f5f5f5')
        nb.add(ptn_tab, text='  패턴 데이터  ')
        self.pattern_panel = PatternDataPanel(ptn_tab)
        self.pattern_panel.pack(fill=tk.BOTH, expand=True)

        # ── 탭3: MULTIREMOTE ──────────────────────────────────────
        mrt_tab = tk.Frame(nb, bg='#f5f5f5')
        nb.add(mrt_tab, text='  MULTIREMOTE  ')
        self.multiremote_panel = MultiRemotePanel(mrt_tab, self.model_store)
        self.multiremote_panel.pack(fill=tk.BOTH, expand=True)

        paned.add(left_outer, weight=1)

        # ── 우측: 타이밍 다이어그램 ───────────────────────────────
        viewer_frame = tk.LabelFrame(
            paned, text="타이밍 다이어그램",
            font=('Arial', 11, 'bold'),
            bg='#f0f0f0', padx=4, pady=4
        )
        self.timing_viewer = TimingViewer(
            viewer_frame, self.signal_manager, self.sync_data_manager
        )
        self.timing_viewer.pack(fill=tk.BOTH, expand=True)
        paned.add(viewer_frame, weight=3)

        # ── 지연 연결: 패널 생성 후 참조 업데이트 ─────────────────
        # control_panel은 timing_viewer/pattern_data_panel 없이 먼저 생성됨
        self.control_panel.timing_viewer      = self.timing_viewer
        self.control_panel.pattern_data_panel = self.pattern_panel

        # model_list_panel도 timing_viewer/pattern_data_panel 연결
        self.model_list_panel.timing_viewer      = self.timing_viewer
        self.model_list_panel.pattern_data_panel = self.pattern_panel

        # ── 하단: 상태 표시줄 ─────────────────────────────────────
        self.statusbar = tk.Label(
            self, text="준비", bd=1, relief=tk.SUNKEN,
            anchor=tk.W, font=('Arial', 9),
            bg='#d8d8d8', fg='#000'
        )
        self.statusbar.pack(side=tk.BOTTOM, fill=tk.X)

        # 상태 표시줄: signal_manager와 model_store 변경 시 갱신
        self.signal_manager.add_listener(self._update_status)
        self.model_store.add_listener(self._update_status)
        self._update_status()

    def _on_edit_signal(self, index):
        """
        신호 편집 콜백

        SignalTableWidget에서 "신호 수정" 또는 "신호 추가" 버튼 클릭 시 호출됩니다.

        Args:
            index (int|None): 수정할 신호 인덱스 (None이면 추가 모드)
        """
        self.signal_editor.edit_signal(index)

    def _update_status(self):
        """
        하단 상태 표시줄 업데이트

        현재 모델 수, 선택 모델, 신호 수, 패턴 수, MULTIREMOTE 수를 표시합니다.
        """
        n_sigs    = len(self.signal_manager.get_all_signals())
        n_models  = len(self.model_store.models)
        n_mrts    = len(self.model_store.multiremote_groups)
        cur_model = (self.model_store.current_model.display_name
                     if self.model_store.current_model else "없음")
        n_ptns    = (len(self.pattern_panel.get_patterns())
                     if hasattr(self, 'pattern_panel') else 0)
        self.statusbar.config(
            text=(
                f"모델: {n_models}개 | 현재: {cur_model} | "
                f"신호: {n_sigs}개 | 패턴: {n_ptns}개 | "
                f"MRT: {n_mrts}개"
            )
        )


def main():
    """애플리케이션 진입점"""
    app = MainApplication()
    app.mainloop()


if __name__ == '__main__':
    main()
