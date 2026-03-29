"""
다중 모델 데이터 저장소 (ModelStore)

OTD 또는 Excel에서 불러온 모든 모델 데이터를 중앙에서 관리합니다.
앱 전체 컴포넌트에서 단일 인스턴스로 공유됩니다.
"""

from dataclasses import dataclass, field
from typing import List, Optional, Callable, Dict


# ────────────────────────────────────────────────────────────────
# 데이터 클래스
# ────────────────────────────────────────────────────────────────

@dataclass
class MrtEntry:
    """MULTIREMOTE의 단일 구동 항목"""
    seq: int          # 순서 번호 (MRT01, MRT02 ...)
    model_num: str    # 구동할 모델 번호
    ptn_no: int       # 구동할 패턴 번호
    time: int = 0     # TIME 값 (OTD 기준)


@dataclass
class MultiRemoteGroup:
    """하나의 MULTIREMOTE 그룹 (501=MRT 에 해당)"""
    mrt_no: str       # MRT 번호 (예: '001')
    name: str         # MRT 이름 (예: 'B6-250916-T')
    entries: List[MrtEntry] = field(default_factory=list)


@dataclass
class ModelData:
    """하나의 모델 데이터"""
    model_num: str         # 모델 번호 (예: '010')
    name: str              # 모델 이름
    frequency_hz: float    # 주파수 (Hz)
    sync_data_us: float    # 1프레임 길이 (us)
    sync_cntr: int = 0
    signals: list = field(default_factory=list)   # List[Signal]
    patterns: list = field(default_factory=list)  # List[dict]

    @property
    def display_name(self) -> str:
        return f"[{self.model_num}] {self.name}"


# ────────────────────────────────────────────────────────────────
# ModelStore
# ────────────────────────────────────────────────────────────────

class ModelStore:
    """
    다중 모델 데이터 저장소

    전체 앱에서 단일 인스턴스로 사용.
    OTD/Excel 로드 시 모든 모델을 models 리스트에 저장.
    컴포넌트는 add_listener()로 변경 알림을 구독.
    """

    def __init__(self):
        self.models: List[ModelData] = []
        self.multiremote_groups: List[MultiRemoteGroup] = []
        self._current_idx: int = -1
        self._listeners: List[Callable] = []

    # ── 리스너 ────────────────────────────────────────────────
    def add_listener(self, callback: Callable):
        if callback not in self._listeners:
            self._listeners.append(callback)

    def remove_listener(self, callback: Callable):
        if callback in self._listeners:
            self._listeners.remove(callback)

    def _notify(self):
        for cb in self._listeners:
            try:
                cb()
            except Exception as e:
                print(f"ModelStore listener error: {e}")

    # ── 모델 관리 ─────────────────────────────────────────────
    def clear(self):
        """전체 데이터 초기화"""
        self.models.clear()
        self.multiremote_groups.clear()
        self._current_idx = -1
        self._notify()

    def set_models(self, models: List[ModelData],
                   multiremote: Optional[List[MultiRemoteGroup]] = None):
        """모델 목록 일괄 교체"""
        self.models = list(models)
        self.multiremote_groups = list(multiremote or [])
        self._current_idx = 0 if self.models else -1
        self._notify()

    def add_model(self, model: ModelData):
        """단일 모델 추가"""
        self.models.append(model)
        if self._current_idx < 0:
            self._current_idx = 0
        self._notify()

    # ── 현재 모델 선택 ────────────────────────────────────────
    @property
    def current_index(self) -> int:
        return self._current_idx

    @current_index.setter
    def current_index(self, idx: int):
        if 0 <= idx < len(self.models):
            self._current_idx = idx
            self._notify()

    @property
    def current_model(self) -> Optional[ModelData]:
        if 0 <= self._current_idx < len(self.models):
            return self.models[self._current_idx]
        return None

    def select_by_name_or_num(self, name_or_num: str) -> bool:
        """이름 또는 번호로 모델 선택"""
        for i, m in enumerate(self.models):
            if m.name == name_or_num or m.model_num == name_or_num:
                self.current_index = i
                return True
        return False

    # ── Model 번호 → 인덱스 조회 ────────────────────────────────
    def find_by_model_num(self, model_num: str) -> Optional[ModelData]:
        for m in self.models:
            if m.model_num == model_num:
                return m
        return None

    # ── MULTIREMOTE ──────────────────────────────────────────
    def set_multiremote(self, groups: List[MultiRemoteGroup]):
        self.multiremote_groups = list(groups)
        self._notify()

    def get_multiremote_display_names(self) -> List[str]:
        return [f"[{g.mrt_no}] {g.name}" for g in self.multiremote_groups]
