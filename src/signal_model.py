"""
신호 데이터 모델
Signal 클래스와 SignalManager 클래스를 정의합니다.
"""

from dataclasses import dataclass
from typing import List, Callable
import random


@dataclass
class Signal:
    """
    신호 데이터 클래스
    
    TOSG-400M 패턴 생성기의 단일 신호를 표현합니다.
    각 신호는 이름, 타입, 모드, 반전 설정, 전압 레벨, 타이밍 파라미터를 가집니다.
    
    Attributes:
        name (str): 신호 이름 (예: "CLK", "VCOM")
        sig_type (str): 신호 타입 (현재 미사용, 향후 확장용)
        sig_mode (int): SIG MODE (0 또는 1)
            - 0: 단일 전압 쌍 사용 (V1, V2)
            - 1: 프레임별 전압 쌍 교대 (홀수: V1,V2 / 짝수: V3,V4)
        inversion (int): INVERSION 설정 (0 또는 1)
            - 0: 반전 없음
            - 1: 프레임별 반전 또는 전압 교대
        v1 (float): 전압 레벨 1 (Volts) - 일반적으로 Low 레벨
        v2 (float): 전압 레벨 2 (Volts) - 일반적으로 High 레벨
        v3 (float): 전압 레벨 3 (Volts) - MODE=1일 때 짝수 프레임 Low
        v4 (float): 전압 레벨 4 (Volts) - MODE=1일 때 짝수 프레임 High
        delay (float): 신호 시작 지연 시간 (us)
        width (float): 펄스 폭 (us) - High 상태 지속 시간
        period (float): 신호 주기 (us)
        color (str): 신호 표시 색상 (Hex code, 예: "#FF0000")
    
    Note:
        - DC 모드: delay=0, width=0, period=0일 때 활성화
        - 일반 모드: delay, width, period > 0일 때 활성화
    """
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
    color: str = "#0000FF"  # 기본값: 파란색
    visible: bool = True  # 기본값: 표시

    def __init__(self, name="Signal", sig_type="", sig_mode=0, inversion=0,
                 v1=0.0, v2=3.3, v3=0.0, v4=3.3,
                 delay=0.0, width=100.0, period=200.0, color=None, visible=True):
        self.name = name
        self.sig_type = sig_type
        self.sig_mode = sig_mode
        self.inversion = inversion
        self.v1 = v1
        self.v2 = v2
        self.v3 = v3
        self.v4 = v4
        self.delay = delay
        self.width = width
        self.period = period
        self.visible = visible
        
        if color is None:
            # 랜덤 색상 생성 (너무 밝거나 어두운 색 제외)
            self.color = "#{:06x}".format(random.randint(0, 0xFFFFFF))
        else:
            self.color = color
    
    def to_dict(self):
        """신호 데이터를 딕셔너리로 변환"""
        return {
            'name': self.name,
            'sig_type': self.sig_type,
            'sig_mode': self.sig_mode,
            'inversion': self.inversion,
            'v1': self.v1,
            'v2': self.v2,
            'v3': self.v3,
            'v4': self.v4,
            'delay': self.delay,
            'width': self.width,
            'period': self.period,
            'color': self.color,
            'visible': self.visible
        }
    
    @staticmethod
    def from_dict(data):
        """딕셔너리에서 Signal 객체 생성"""
        return Signal(
            name=data.get('name', 'Signal'),
            sig_type=data.get('sig_type', ''),
            sig_mode=data.get('sig_mode', 0),
            inversion=data.get('inversion', 0),
            v1=data.get('v1', 0.0),
            v2=data.get('v2', 3.3),
            v3=data.get('v3', 0.0),
            v4=data.get('v4', 3.3),
            delay=data.get('delay', 0.0),
            width=data.get('width', 100.0),
            period=data.get('period', 200.0),
            color=data.get('color', None),
            visible=data.get('visible', True)
        )
    
    def __repr__(self):
        return f"Signal(name={self.name}, mode={self.sig_mode}, inv={self.inversion}, color={self.color})"


class SignalManager:
    """
    신호 관리 클래스
    
    여러 Signal 객체를 관리하고, 신호 추가/수정/삭제 기능을 제공합니다.
    Observer 패턴을 사용하여 신호 변경 시 리스너들에게 알립니다.
    
    Attributes:
        _signals (List[Signal]): 관리 중인 신호 리스트
        _listeners (List[Callable]): 신호 변경 시 호출될 콜백 함수 리스트
    """
    
    def __init__(self):
        """SignalManager 초기화"""
        self._signals: List[Signal] = []  # 신호 저장 리스트
        self._listeners: List[Callable] = []  # 변경 리스너 리스트
    
    def add_listener(self, listener: Callable):
        """
        신호 변경 리스너 등록
        
        신호가 추가/수정/삭제될 때 호출될 콜백 함수를 등록합니다.
        주로 UI 업데이트를 위해 사용됩니다.
        
        Args:
            listener (Callable): 신호 변경 시 호출될 함수
        """
        self._listeners.append(listener)
    
    def _notify_listeners(self):
        """
        모든 리스너에게 변경 알림
        
        등록된 모든 리스너 함수를 호출하여 신호가 변경되었음을 알립니다.
        UI 컴포넌트들이 자동으로 업데이트되도록 합니다.
        """
        for listener in self._listeners:
            listener()
    
    def add_signal(self, signal: Signal):
        """
        새 신호 추가
        
        Args:
            signal (Signal): 추가할 Signal 객체
        
        Note:
            신호 추가 후 자동으로 리스너들에게 알립니다.
        """
        self._signals.append(signal)
        self._notify_listeners()
    
    def update_signal(self, index: int, signal: Signal):
        """
        기존 신호 수정
        
        Args:
            index (int): 수정할 신호의 인덱스 (0부터 시작)
            signal (Signal): 새로운 Signal 객체
        
        Note:
            인덱스가 유효한 범위 내에 있을 때만 수정됩니다.
        """
        if 0 <= index < len(self._signals):
            self._signals[index] = signal
            self._notify_listeners()
    
    def remove_signal(self, index: int):
        """
        신호 삭제
        
        Args:
            index (int): 삭제할 신호의 인덱스 (0부터 시작)
        
        Note:
            인덱스가 유효한 범위 내에 있을 때만 삭제됩니다.
        """
        if 0 <= index < len(self._signals):
            del self._signals[index]
            self._notify_listeners()
    
    def get_signal(self, index: int) -> Signal:
        """
        특정 인덱스의 신호 가져오기
        
        Args:
            index (int): 가져올 신호의 인덱스 (0부터 시작)
        
        Returns:
            Signal: 해당 인덱스의 Signal 객체, 인덱스가 유효하지 않으면 None
        """
        if 0 <= index < len(self._signals):
            return self._signals[index]
        return None
    
    def get_all_signals(self) -> List[Signal]:
        """
        모든 신호 가져오기
        
        Returns:
            List[Signal]: 관리 중인 모든 Signal 객체의 리스트
        """
        return self._signals
    
    def clear_signals(self):
        """
        모든 신호 삭제
        
        관리 중인 모든 신호를 삭제하고 리스너들에게 알립니다.
        주로 파일 불러오기 전이나 전체 삭제 시 사용됩니다.
        """
        self._signals.clear()
        self._notify_listeners()
    
    def move_signal_up(self, index: int):
        """
        신호를 위로 이동 (인덱스 감소)
        
        Args:
            index (int): 이동할 신호의 인덱스
        """
        if 0 < index < len(self._signals):
            self._signals[index], self._signals[index - 1] = \
                self._signals[index - 1], self._signals[index]
            self._notify_listeners()
    
    def move_signal_down(self, index: int):
        """
        신호를 아래로 이동 (인덱스 증가)
        
        Args:
            index (int): 이동할 신호의 인덱스
        """
        if 0 <= index < len(self._signals) - 1:
            self._signals[index], self._signals[index + 1] = \
                self._signals[index + 1], self._signals[index]
            self._notify_listeners()
