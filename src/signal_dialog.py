"""
신호 편집 다이얼로그
신호 추가/수정을 위한 입력 폼
"""

import tkinter as tk
from tkinter import ttk, messagebox
from signal_model import Signal


class SignalDialog(tk.Toplevel):
    """신호 편집 다이얼로그"""
    
    def __init__(self, parent, signal=None, title="신호 편집"):
        super().__init__(parent)
        
        self.title(title)
        self.geometry("500x600")
        self.resizable(False, False)
        
        self.signal = signal
        self.result = None
        
        self._setup_ui()
        
        # 기존 신호 데이터 로드
        if signal:
            self._load_signal_data()
        
        # 모달 다이얼로그
        self.transient(parent)
        self.grab_set()
        
        # 중앙 배치
        self.update_idletasks()
        x = (self.winfo_screenwidth() // 2) - (self.winfo_width() // 2)
        y = (self.winfo_screenheight() // 2) - (self.winfo_height() // 2)
        self.geometry(f"+{x}+{y}")
    
    def _setup_ui(self):
        """UI 구성"""
        # 메인 프레임
        main_frame = tk.Frame(self, padx=20, pady=20)
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # 입력 필드
        self.entries = {}
        
        fields = [
            ('name', '신호 이름', 'Signal1', 'str'),
            ('sig_type', 'SIG TYPE', '', 'str'),
            ('sig_mode', 'SIG MODE', '0', 'int'),
            ('inversion', 'INVERSION', '0', 'int'),
            ('v1', 'V1 (V)', '0.0', 'float'),
            ('v2', 'V2 (V)', '3.3', 'float'),
            ('v3', 'V3 (V)', '0.0', 'float'),
            ('v4', 'V4 (V)', '3.3', 'float'),
            ('delay', 'DELAY (μm)', '0.0', 'float'),
            ('width', 'WIDTH (μm)', '100.0', 'float'),
            ('period', 'PERIOD (μm)', '200.0', 'float'),
        ]
        
        for idx, (key, label, default, dtype) in enumerate(fields):
            # 레이블
            tk.Label(main_frame, text=label, font=('Arial', 10)).grid(
                row=idx, column=0, sticky='w', pady=5
            )
            
            # 입력 필드
            entry = tk.Entry(main_frame, font=('Arial', 10), width=30)
            entry.grid(row=idx, column=1, sticky='ew', pady=5)
            entry.insert(0, default)
            
            self.entries[key] = (entry, dtype)
        
        main_frame.grid_columnconfigure(1, weight=1)
        
        # 도움말 프레임
        help_frame = tk.LabelFrame(main_frame, text="SIG MODE 설명", 
                                   font=('Arial', 9, 'bold'), padx=10, pady=10)
        help_frame.grid(row=len(fields), column=0, columnspan=2, sticky='ew', pady=10)
        
        help_text = """
일반 모드 (Delay, Width, Period > 0):
  MODE=0, INV=0: V1,V2 사용, Frame별 반전 없음
  MODE=0, INV=1: V1,V2 사용, Frame별 반전 적용
  MODE=1, INV=0: Odd Frame은 V1,V2, Even Frame은 V3,V4
  MODE=1, INV=1: Odd Frame은 V1,V2, Even Frame은 V4,V3

DC 모드 (Delay=0, Width=0, Period=0):
  MODE=0, INV=0: V1 DC 출력
  MODE=0, INV=1: Frame별 V1, V2 반복
  MODE=1, INV=0: Frame별 V1, V3 반복
  MODE=1, INV=1: Frame별 V1, V4 반복
        """
        
        tk.Label(help_frame, text=help_text.strip(), font=('Arial', 8),
                justify=tk.LEFT, fg='#555').pack(anchor='w')
        
        # 버튼 프레임
        btn_frame = tk.Frame(main_frame)
        btn_frame.grid(row=len(fields)+1, column=0, columnspan=2, pady=20)
        
        tk.Button(btn_frame, text="확인", command=self._on_ok,
                 bg='#4CAF50', fg='white', font=('Arial', 11, 'bold'),
                 width=10).pack(side=tk.LEFT, padx=5)
        tk.Button(btn_frame, text="취소", command=self._on_cancel,
                 bg='#9E9E9E', fg='white', font=('Arial', 11, 'bold'),
                 width=10).pack(side=tk.LEFT, padx=5)
    
    def _load_signal_data(self):
        """기존 신호 데이터 로드"""
        if not self.signal:
            return
        
        field_map = {
            'name': self.signal.name,
            'sig_type': self.signal.sig_type,
            'sig_mode': str(self.signal.sig_mode),
            'inversion': str(self.signal.inversion),
            'v1': str(self.signal.v1),
            'v2': str(self.signal.v2),
            'v3': str(self.signal.v3),
            'v4': str(self.signal.v4),
            'delay': str(self.signal.delay),
            'width': str(self.signal.width),
            'period': str(self.signal.period),
        }
        
        for key, value in field_map.items():
            if key in self.entries:
                entry, _ = self.entries[key]
                entry.delete(0, tk.END)
                entry.insert(0, value)
    
    def _validate_and_get_values(self):
        """입력 검증 및 값 가져오기"""
        values = {}
        
        for key, (entry, dtype) in self.entries.items():
            value_str = entry.get().strip()
            
            try:
                if dtype == 'int':
                    values[key] = int(value_str)
                elif dtype == 'float':
                    values[key] = float(value_str)
                else:
                    values[key] = value_str
            except ValueError:
                messagebox.showerror("입력 오류", 
                                   f"{key} 필드의 값이 올바르지 않습니다.")
                return None
        
        # 추가 검증
        if not values['name']:
            messagebox.showerror("입력 오류", "신호 이름을 입력하세요.")
            return None
        
        if values['sig_mode'] not in [0, 1]:
            messagebox.showerror("입력 오류", "SIG MODE는 0 또는 1이어야 합니다.")
            return None
        
        if values['inversion'] not in [0, 1]:
            messagebox.showerror("입력 오류", "INVERSION은 0 또는 1이어야 합니다.")
            return None
        
        if values['period'] <= 0:
            messagebox.showerror("입력 오류", "PERIOD는 0보다 커야 합니다.")
            return None
        
        return values
    
    def _on_ok(self):
        """확인 버튼"""
        values = self._validate_and_get_values()
        if values is None:
            return
        
        # Signal 객체 생성
        self.result = Signal(
            name=values['name'],
            sig_type=values['sig_type'],
            sig_mode=values['sig_mode'],
            inversion=values['inversion'],
            v1=values['v1'],
            v2=values['v2'],
            v3=values['v3'],
            v4=values['v4'],
            delay=values['delay'],
            width=values['width'],
            period=values['period']
        )
        
        self.destroy()
    
    def _on_cancel(self):
        """취소 버튼"""
        self.result = None
        self.destroy()
    
    def get_result(self):
        """결과 반환"""
        self.wait_window()
        return self.result
