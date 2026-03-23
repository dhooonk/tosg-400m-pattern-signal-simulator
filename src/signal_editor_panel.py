"""
인라인 신호 편집기 패널
메인 윈도우 내에서 신호 파라미터를 직접 편집할 수 있는 패널입니다.
기존의 팝업 다이얼로그 방식을 대체하여 사용성을 개선했습니다.
"""

import tkinter as tk
from tkinter import ttk, messagebox, colorchooser
from signal_model import Signal


class ToolTip(object):
    """
    위젯에 마우스를 올렸을 때 나타나는 툴팁 클래스
    """
    def __init__(self, widget, text='widget info'):
        self.waittime = 500     # miliseconds
        self.wraplength = 300   # pixels
        self.widget = widget
        self.text = text
        self.widget.bind("<Enter>", self.enter)
        self.widget.bind("<Leave>", self.leave)
        self.widget.bind("<ButtonPress>", self.leave)
        self.id = None
        self.tw = None

    def enter(self, event=None):
        self.schedule()

    def leave(self, event=None):
        self.unschedule()
        self.hidetip()

    def schedule(self):
        self.unschedule()
        self.id = self.widget.after(self.waittime, self.showtip)

    def unschedule(self):
        id = self.id
        self.id = None
        if id:
            self.widget.after_cancel(id)

    def showtip(self, event=None):
        x = y = 0
        x, y, cx, cy = self.widget.bbox("insert")
        x += self.widget.winfo_rootx() + 25
        y += self.widget.winfo_rooty() + 20
        
        # creates a toplevel window
        self.tw = tk.Toplevel(self.widget)
        
        # Leaves only the label and removes the app window
        self.tw.wm_overrideredirect(True)
        self.tw.wm_geometry("+%d+%d" % (x, y))
        
        label = tk.Label(self.tw, text=self.text, justify='left',
                       background="#ffffe0", relief='solid', borderwidth=1,
                       font=("tahoma", "8", "normal"),
                       wraplength=self.wraplength)
        label.pack(ipadx=1)

    def hidetip(self):
        tw = self.tw
        self.tw= None
        if tw:
            tw.destroy()


class SignalEditorPanel(tk.Frame):
    """
    인라인 신호 편집기 패널 클래스
    
    신호의 모든 파라미터(이름, 모드, 전압, 타이밍 등)를 입력받는 폼을 제공합니다.
    새 신호 추가 및 기존 신호 수정 기능을 모두 지원합니다.
    """
    
    def __init__(self, parent, signal_manager):
        """
        초기화 메서드
        
        Args:
            parent: 부모 위젯
            signal_manager (SignalManager): 신호 관리자 객체
        """
        super().__init__(parent, relief=tk.RAISED, borderwidth=2, bg='#f0f0f0')
        
        self.signal_manager = signal_manager
        self.current_index = None  # 현재 편집 중인 신호 인덱스 (None이면 새 신호)
        self.entries = {}  # 입력 필드 위젯 저장 딕셔너리
        self.color_var = None # 색상 변수
        self.color_btn = None # 색상 버튼
        
        self._setup_ui()
    
    def _setup_ui(self):
        """UI 구성"""
        # 메인 폼 프레임
        form_frame = tk.Frame(self, bg='#f0f0f0', padx=15, pady=10)
        form_frame.pack(side=tk.TOP, fill=tk.BOTH, expand=True)
        
        # 입력 필드 정의 (키, 라벨, 기본값, 데이터타입)
        fields = [
            ('name', '신호 이름', 'Signal1', 'str'),
            ('sig_type', 'SIG TYPE', '', 'str'),
            ('sig_mode', 'SIG MODE', '0', 'int'),
            ('inversion', 'INVERSION', '0', 'int'),
            ('v1', 'V1 (V)', '0.0', 'float'),
            ('v2', 'V2 (V)', '3.3', 'float'),
            ('v3', 'V3 (V)', '0.0', 'float'),
            ('v4', 'V4 (V)', '3.3', 'float'),
            ('delay', 'DELAY (us)', '0.0', 'float'),
            ('width', 'WIDTH (us)', '100.0', 'float'),
            ('period', 'PERIOD (us)', '200.0', 'float'),
        ]
        
        # 2열 그리드 레이아웃 생성
        for idx, (key, label, default, dtype) in enumerate(fields):
            row = idx // 2
            col = idx % 2
            
            # 각 필드를 감싸는 프레임
            field_frame = tk.Frame(form_frame, bg='#f0f0f0')
            field_frame.grid(row=row, column=col, sticky='ew', padx=5, pady=3)
            
            # 라벨
            label_widget = tk.Label(field_frame, text=label, font=('Arial', 9), 
                    bg='#f0f0f0', fg='#000', width=12, anchor='w')
            label_widget.pack(side=tk.LEFT)
            
            # SIG MODE에 툴팁 추가
            if key == 'sig_mode':
                help_icon = tk.Label(field_frame, text="❓", font=('Arial', 9),
                                    bg='#f0f0f0', fg='blue', cursor="hand2")
                help_icon.pack(side=tk.LEFT, padx=(0, 5))
                
                help_text = """일반 모드 (Delay, Width, Period > 0):
  MODE=0, INV=0: V1,V2 사용 / 프레임별 반전 없음
  MODE=0, INV=1: V1,V2 사용 / 프레임별 반전 적용
  MODE=1, INV=0: 홀수 프레임: V1,V2 / 짝수 프레임: V3,V4
  MODE=1, INV=1: 홀수 프레임: V1,V2 / 짝수 프레임: V4,V3

DC 모드 (Delay=0, Width=0, Period=0):
  MODE=0, INV=0: V1 DC 출력
  MODE=0, INV=1: 프레임별 V1, V2 반복
  MODE=1, INV=0: 프레임별 V1, V3 반복
  MODE=1, INV=1: 프레임별 V1, V4 반복"""
                ToolTip(help_icon, help_text)
            
            # 입력 필드 (Entry)
            entry = tk.Entry(field_frame, font=('Arial', 9), width=15, 
                           bg='white', fg='black', relief=tk.SOLID, borderwidth=1)
            entry.pack(side=tk.LEFT, fill=tk.X, expand=True)
            entry.insert(0, default)
            
            # 나중에 값을 가져오기 위해 저장
            self.entries[key] = (entry, dtype)
        
        # 색상 선택 필드 추가
        color_frame = tk.Frame(form_frame, bg='#f0f0f0')
        color_frame.grid(row=(len(fields))//2, column=(len(fields))%2, sticky='ew', padx=5, pady=3)
        
        tk.Label(color_frame, text="색상", font=('Arial', 9), 
                bg='#f0f0f0', fg='#000', width=12, anchor='w').pack(side=tk.LEFT)
        
        self.color_var = tk.StringVar(value="#0000FF")
        self.color_btn = tk.Button(color_frame, text="색상 선택", bg="#0000FF", fg="white",
                                  command=self._choose_color, width=15)
        self.color_btn.pack(side=tk.LEFT, fill=tk.X, expand=True)
        
        # 컬럼 가중치 설정 (창 크기 조절 시 균등하게 늘어남)
        form_frame.grid_columnconfigure(0, weight=1)
        form_frame.grid_columnconfigure(1, weight=1)
        
        # 버튼 프레임
        btn_frame = tk.Frame(self, bg='#f0f0f0', pady=10)
        btn_frame.pack(side=tk.TOP, fill=tk.X)
        
        # 저장/취소 버튼
        self.save_btn = tk.Button(btn_frame, text="신호 추가", command=self._on_save,
                 bg='#4CAF50', fg='black', font=('Arial', 10, 'bold'),
                 width=12, relief=tk.RAISED, borderwidth=2)
        self.save_btn.pack(side=tk.LEFT, padx=5)
        
        tk.Button(btn_frame, text="취소", command=self._on_cancel,
                 bg='#9E9E9E', fg='black', font=('Arial', 10, 'bold'),
                 width=12, relief=tk.RAISED, borderwidth=2).pack(side=tk.LEFT, padx=5)
    
    def _choose_color(self):
        """색상 선택 다이얼로그"""
        color = colorchooser.askcolor(title="신호 색상 선택", color=self.color_var.get())
        if color[1]:
            self.color_var.set(color[1])
            self.color_btn.config(bg=color[1])
    
    def edit_signal(self, index=None):
        """
        신호 편집 모드 설정
        
        Args:
            index (int, optional): 편집할 신호 인덱스. None이면 새 신호 추가 모드.
        """
        self.current_index = index
        
        if index is None:
            # 새 신호 추가 모드
            self.save_btn.config(text="신호 추가", bg='#4CAF50')
            self._clear_fields()
        else:
            # 기존 신호 수정 모드
            self.save_btn.config(text="신호 수정", bg='#FF9800')
            signal = self.signal_manager.get_signal(index)
            if signal:
                self._load_signal_data(signal)
    
    def _clear_fields(self):
        """모든 입력 필드를 기본값으로 초기화"""
        defaults = {
            'name': 'Signal1',
            'sig_type': '',
            'sig_mode': '0',
            'inversion': '0',
            'v1': '0.0',
            'v2': '3.3',
            'v3': '0.0',
            'v4': '3.3',
            'delay': '0.0',
            'width': '100.0',
            'period': '200.0',
        }
        
        for key, (entry, _) in self.entries.items():
            entry.delete(0, tk.END)
            entry.insert(0, defaults.get(key, ''))
        
        # 색상 초기화 (파란색)
        self.color_var.set("#0000FF")
        self.color_btn.config(bg="#0000FF")
    
    def _load_signal_data(self, signal):
        """
        신호 데이터를 입력 필드에 로드
        
        Args:
            signal (Signal): 로드할 신호 객체
        """
        field_map = {
            'name': signal.name,
            'sig_type': signal.sig_type,
            'sig_mode': str(signal.sig_mode),
            'inversion': str(signal.inversion),
            'v1': str(signal.v1),
            'v2': str(signal.v2),
            'v3': str(signal.v3),
            'v4': str(signal.v4),
            'delay': str(signal.delay),
            'width': str(signal.width),
            'period': str(signal.period),
        }
        
        for key, value in field_map.items():
            if key in self.entries:
                entry, _ = self.entries[key]
                entry.delete(0, tk.END)
                entry.insert(0, value)
        
        # 색상 로드
        if hasattr(signal, 'color') and signal.color:
            self.color_var.set(signal.color)
            self.color_btn.config(bg=signal.color)
    
    def _validate_and_get_values(self):
        """
        입력값 유효성 검사 및 데이터 추출
        
        Returns:
            dict: 유효한 입력값 딕셔너리 (실패 시 None)
        """
        values = {}
        
        for key, (entry, dtype) in self.entries.items():
            value_str = entry.get().strip()
            
            try:
                # 데이터 타입 변환
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
        
        # 추가 유효성 검사
        if not values['name']:
            messagebox.showerror("입력 오류", "신호 이름을 입력하세요.")
            return None
        
        if values['sig_mode'] not in [0, 1]:
            messagebox.showerror("입력 오류", "SIG MODE는 0 또는 1이어야 합니다.")
            return None
        
        if values['inversion'] not in [0, 1]:
            messagebox.showerror("입력 오류", "INVERSION은 0 또는 1이어야 합니다.")
            return None
        
        values['color'] = self.color_var.get()
        
        return values
    
    def _on_save(self):
        """저장(신호 추가) 버튼 핸들러"""
        values = self._validate_and_get_values()
        if values is None:
            return
        
        # Signal 객체 생성
        signal = Signal(
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
            period=values['period'],
            color=values['color']
        )
        
        if self.current_index is None:
            # 새 신호 추가
            self.signal_manager.add_signal(signal)
        else:
            # 기존 신호 수정
            self.signal_manager.update_signal(self.current_index, signal)
        
        # 입력 필드 초기화 및 모드 리셋
        self._clear_fields()
        self.current_index = None
        self.save_btn.config(text="신호 추가", bg='#4CAF50')
    
    def _on_cancel(self):
        """취소 버튼 핸들러"""
        self._clear_fields()
        self.current_index = None
        self.save_btn.config(text="신호 추가", bg='#4CAF50')
