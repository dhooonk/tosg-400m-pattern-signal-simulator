"""
신호 데이터 모델 및 저장소 모듈
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
포함 클래스/함수:
  - Signal        : 단일 신호 데이터 (전압·타이밍 파라미터)
  - SignalManager : 신호 목록 관리 + 변경 알림 (Observer 패턴)
  - SignalStorage : 신호 데이터를 JSON 파일로 영속 저장/복원

단위 규칙:
  - 전압: V (볼트)
  - 시간: us (마이크로초)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""

import json
import os
import random
from dataclasses import dataclass
from typing import List, Callable


# ════════════════════════════════════════════════════════
# Signal — 단일 신호 데이터
# ════════════════════════════════════════════════════════

@dataclass
class Signal:
    """
    TOSG-400M 패턴 생성기의 단일 신호를 표현하는 데이터 클래스.

    파형 생성 모드
    ──────────────
    • DC 모드  : delay=0, width=0, period=0 → 프레임 전체 일정 전압
    • 일반 모드 : delay/width/period 중 하나라도 0이 아닐 때

    SIG MODE / INVERSION 조합 (일반 모드)
    ──────────────────────────────────────
    MODE=0, INV=0 : 모든 프레임에서 V1(Low) / V2(High)
    MODE=0, INV=1 : 홀수 프레임 V1/V2, 짝수 프레임 V2/V1 (전압 교대)
    MODE=1, INV=0 : 홀수 프레임 V1/V2, 짝수 프레임 V3/V4
    MODE=1, INV=1 : 홀수 프레임 V1/V2, 짝수 프레임 V4/V3

    SIG MODE / INVERSION 조합 (DC 모드)
    ──────────────────────────────────────
    MODE=0, INV=0 : V1 고정 DC
    MODE=0, INV=1 : 프레임별 V1 ↔ V2 반복
    MODE=1, INV=0 : 프레임별 V1 ↔ V3 반복
    MODE=1, INV=1 : 프레임별 V1 ↔ V4 반복

    Attributes:
        name      (str)  : 신호 이름 (예: "CLK", "VCOM")
        sig_type  (str)  : 신호 타입 문자열 (예: "0","1","CLK" 등)
        sig_mode  (int)  : SIG MODE (0 또는 1)
        inversion (int)  : INVERSION 설정 (0 또는 1)
        v1..v4   (float) : 전압 레벨 1~4 (V)
        delay    (float) : 신호 시작 지연 시간 (us)
        width    (float) : 펄스 폭 — High 상태 지속 시간 (us)
        period   (float) : 신호 주기 (us)
        color     (str)  : 타이밍 다이어그램 표시 색상 (Hex, 예: "#FF0000")
        visible   (bool) : 타이밍 다이어그램 표시 여부
    """

    # ── 필드 선언 (dataclass 필수 필드) ─────────────────
    name: str
    sig_type: str
    sig_mode: int
    inversion: int
    v1: float
    v2: float
    v3: float
    v4: float
    delay: float
    width: float
    period: float
    color: str = "#0000FF"   # 기본색: 파란색
    visible: bool = True     # 기본: 표시

    def __init__(self, name="Signal", sig_type="", sig_mode=0, inversion=0,
                 v1=0.0, v2=3.3, v3=0.0, v4=3.3,
                 delay=0.0, width=100.0, period=200.0,
                 color=None, visible=True):
        """
        Signal 생성자

        Args:
            name      : 신호 이름
            sig_type  : 신호 타입 문자열
            sig_mode  : SIG MODE (0 또는 1)
            inversion : INVERSION (0 또는 1)
            v1..v4    : 전압 레벨 (V)
            delay     : 지연 시간 (us)
            width     : 펄스 폭 (us)
            period    : 주기 (us)
            color     : 표시 색상 (None이면 랜덤 생성)
            visible   : 표시 여부
        """
        self.name      = name
        self.sig_type  = sig_type
        self.sig_mode  = sig_mode
        self.inversion = inversion
        self.v1 = v1
        self.v2 = v2
        self.v3 = v3
        self.v4 = v4
        self.delay  = delay
        self.width  = width
        self.period = period
        self.visible = visible
        # 색상 미지정 시 랜덤 생성 (너무 밝거나 어두운 색은 포함될 수 있음)
        self.color = color if color is not None else "#{:06x}".format(
            random.randint(0, 0xFFFFFF))

    def to_dict(self) -> dict:
        """
        Signal → 딕셔너리 변환

        OTD 내보내기·Excel 내보내기·JSON 저장 등에서 사용됩니다.

        Returns:
            dict: 신호 파라미터 딕셔너리
        """
        return {
            'name':      self.name,
            'sig_type':  self.sig_type,
            'sig_mode':  self.sig_mode,
            'inversion': self.inversion,
            'v1': self.v1,
            'v2': self.v2,
            'v3': self.v3,
            'v4': self.v4,
            'delay':  self.delay,
            'width':  self.width,
            'period': self.period,
            'color':  self.color,
            'visible': self.visible,
        }

    @staticmethod
    def from_dict(data: dict) -> 'Signal':
        """
        딕셔너리 → Signal 객체 생성

        OTD 파싱·Excel 불러오기·JSON 복원에서 사용됩니다.

        Args:
            data: 신호 파라미터 딕셔너리

        Returns:
            Signal: 복원된 Signal 객체
        """
        return Signal(
            name      = data.get('name',      'Signal'),
            sig_type  = data.get('sig_type',  ''),
            sig_mode  = data.get('sig_mode',  0),
            inversion = data.get('inversion', 0),
            v1 = data.get('v1', 0.0),
            v2 = data.get('v2', 3.3),
            v3 = data.get('v3', 0.0),
            v4 = data.get('v4', 3.3),
            delay  = data.get('delay',  0.0),
            width  = data.get('width',  100.0),
            period = data.get('period', 200.0),
            color   = data.get('color',   None),
            visible = data.get('visible', True),
        )

    def __repr__(self) -> str:
        return (f"Signal(name={self.name!r}, mode={self.sig_mode}, "
                f"inv={self.inversion}, color={self.color!r})")


# ════════════════════════════════════════════════════════
# SignalManager — 신호 목록 + Observer 패턴
# ════════════════════════════════════════════════════════

class SignalManager:
    """
    여러 Signal 객체를 관리하는 컨테이너.

    Observer 패턴으로 신호 변경(추가/수정/삭제/이동) 시
    등록된 리스너들에게 자동 알림을 보냅니다.
    TimingViewer, SignalTableWidget 등이 리스너로 등록되어
    신호 변경 즉시 UI를 갱신합니다.

    Attributes:
        _signals   (List[Signal])   : 관리 중인 신호 리스트
        _listeners (List[Callable]) : 변경 알림을 받을 콜백 함수 리스트
    """

    def __init__(self):
        """SignalManager 초기화 — 빈 신호 리스트와 리스너 리스트로 시작"""
        self._signals:   List[Signal]   = []
        self._listeners: List[Callable] = []

    # ── 리스너 관리 ──────────────────────────────────────

    def add_listener(self, listener: Callable):
        """
        신호 변경 리스너 등록

        등록된 함수는 신호 추가·수정·삭제·이동 시 인수 없이 호출됩니다.

        Args:
            listener: 신호 변경 시 호출할 콜백 함수
        """
        self._listeners.append(listener)

    def _notify_listeners(self):
        """
        모든 리스너에게 변경 알림

        등록된 리스너를 순서대로 호출합니다.
        예외가 발생해도 나머지 리스너는 계속 호출합니다.
        """
        for listener in self._listeners:
            try:
                listener()
            except Exception as e:
                print(f"SignalManager listener error: {e}")

    # ── CRUD 연산 ────────────────────────────────────────

    def add_signal(self, signal: Signal):
        """
        신호 추가 (리스트 끝에 append)

        Args:
            signal: 추가할 Signal 객체
        """
        self._signals.append(signal)
        self._notify_listeners()

    def update_signal(self, index: int, signal: Signal):
        """
        기존 신호 교체

        Args:
            index : 교체할 인덱스 (0-based)
            signal: 새로운 Signal 객체
        """
        if 0 <= index < len(self._signals):
            self._signals[index] = signal
            self._notify_listeners()

    def remove_signal(self, index: int):
        """
        신호 삭제

        Args:
            index: 삭제할 인덱스 (0-based)
        """
        if 0 <= index < len(self._signals):
            del self._signals[index]
            self._notify_listeners()

    def clear_signals(self):
        """모든 신호 삭제 (파일 불러오기 전 초기화에 사용)"""
        self._signals.clear()
        self._notify_listeners()

    # ── 조회 ─────────────────────────────────────────────

    def get_signal(self, index: int) -> 'Signal':
        """
        특정 인덱스의 Signal 반환

        Args:
            index: 조회할 인덱스 (0-based)

        Returns:
            Signal 또는 None (인덱스 범위 초과 시)
        """
        if 0 <= index < len(self._signals):
            return self._signals[index]
        return None

    def get_all_signals(self) -> List[Signal]:
        """
        전체 신호 리스트 반환

        Returns:
            List[Signal]: 관리 중인 모든 Signal (참조, 복사 아님)
        """
        return self._signals

    # ── 순서 이동 ─────────────────────────────────────────

    def move_signal_up(self, index: int):
        """
        신호를 한 칸 위로 이동 (index ↔ index-1 스왑)

        Args:
            index: 이동할 신호의 인덱스
        """
        if 0 < index < len(self._signals):
            self._signals[index], self._signals[index - 1] = \
                self._signals[index - 1], self._signals[index]
            self._notify_listeners()

    def move_signal_down(self, index: int):
        """
        신호를 한 칸 아래로 이동 (index ↔ index+1 스왑)

        Args:
            index: 이동할 신호의 인덱스
        """
        if 0 <= index < len(self._signals) - 1:
            self._signals[index], self._signals[index + 1] = \
                self._signals[index + 1], self._signals[index]
            self._notify_listeners()


# ════════════════════════════════════════════════════════
# SignalStorage — JSON 기반 신호 영속 저장
# [통합] 구 signal_storage.py에서 이동
# ════════════════════════════════════════════════════════

class SignalStorage:
    """
    신호 데이터를 JSON 파일로 저장하고 복원하는 클래스.

    파일 구조:
        {storage_dir}/{safe_model_name}.json
        → {"model": "모델명", "signals": [{...}, ...]}

    사용 목적:
        • 모델별 신호 세트를 로컬 파일로 백업/복원
        • OTD·Excel과 독립적인 JSON 기반 영속 저장

    Args:
        storage_dir (str): JSON 파일을 저장할 디렉토리 경로
    """

    def __init__(self, storage_dir: str = 'signal_data'):
        """
        SignalStorage 초기화

        지정한 디렉토리가 없으면 자동 생성합니다.

        Args:
            storage_dir: 데이터 저장 디렉토리 (기본: 'signal_data')
        """
        self.storage_dir = storage_dir
        # 저장 디렉토리 없으면 자동 생성
        if not os.path.exists(storage_dir):
            os.makedirs(storage_dir)

    def _safe_path(self, model_name: str) -> str:
        """
        모델 이름으로 저장 파일 경로 생성.

        파일명에 사용할 수 없는 문자(알파벳·숫자·'-'·'_' 외)를 제거합니다.

        Args:
            model_name: 모델 이름

        Returns:
            str: {storage_dir}/{safe_name}.json
        """
        safe = "".join(c for c in model_name if c.isalnum() or c in ('-', '_'))
        return os.path.join(self.storage_dir, f"{safe}.json")

    # 하위 호환성을 위해 구 이름도 유지
    get_file_path = _safe_path

    def save_signals(self, model_name: str, signals: list) -> bool:
        """
        모델별 신호 리스트를 JSON으로 저장

        Args:
            model_name: 저장 키로 쓸 모델 이름
            signals   : Signal 객체 리스트

        Returns:
            bool: 저장 성공 여부
        """
        try:
            data = {
                'model':   model_name,
                'signals': [s.to_dict() for s in signals],
            }
            with open(self._safe_path(model_name), 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            return True
        except Exception as e:
            print(f"신호 저장 실패: {e}")
            return False

    def load_signals(self, model_name: str) -> list:
        """
        모델명에 해당하는 JSON에서 신호 리스트 복원

        Args:
            model_name: 불러올 모델 이름

        Returns:
            List[Signal]: 복원된 신호 리스트 (파일 없으면 빈 리스트)
        """
        try:
            path = self._safe_path(model_name)
            if not os.path.exists(path):
                return []
            with open(path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            return [Signal.from_dict(d) for d in data.get('signals', [])]
        except Exception as e:
            print(f"신호 로드 실패: {e}")
            return []

    def get_saved_models(self) -> list:
        """
        저장 디렉토리 내 모든 저장된 모델 이름 목록 반환

        Returns:
            List[str]: 저장된 모델 이름 리스트
        """
        models = []
        try:
            for fname in os.listdir(self.storage_dir):
                if fname.endswith('.json'):
                    fpath = os.path.join(self.storage_dir, fname)
                    with open(fpath, 'r', encoding='utf-8') as f:
                        d = json.load(f)
                    models.append(d.get('model', fname[:-5]))
        except Exception as e:
            print(f"저장 모델 목록 조회 실패: {e}")
        return models

    def delete_model_data(self, model_name: str) -> bool:
        """
        특정 모델의 JSON 파일 삭제

        Args:
            model_name: 삭제할 모델 이름

        Returns:
            bool: 삭제 성공 여부
        """
        try:
            path = self._safe_path(model_name)
            if os.path.exists(path):
                os.remove(path)
                return True
        except Exception as e:
            print(f"모델 데이터 삭제 실패: {e}")
        return False

    def save_signals_to_file(self, filepath: str, signals: list) -> bool:
        """
        사용자 지정 경로로 신호 저장 (모델명 없이 파일 경로 직접 지정)

        Args:
            filepath: 저장할 .json 파일 절대/상대 경로
            signals : Signal 객체 리스트

        Returns:
            bool: 저장 성공 여부
        """
        try:
            data = {'signals': [s.to_dict() for s in signals]}
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            return True
        except Exception as e:
            print(f"신호 저장 실패: {e}")
            return False

    def load_signals_from_file(self, filepath: str) -> list:
        """
        사용자 지정 경로의 JSON에서 신호 복원

        Args:
            filepath: 불러올 .json 파일 경로

        Returns:
            List[Signal]: 복원된 신호 리스트 (파일 없으면 빈 리스트)
        """
        try:
            if not os.path.exists(filepath):
                return []
            with open(filepath, 'r', encoding='utf-8') as f:
                data = json.load(f)
            return [Signal.from_dict(d) for d in data.get('signals', [])]
        except Exception as e:
            print(f"신호 로드 실패: {e}")
            return []
