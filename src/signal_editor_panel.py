"""
인라인 신호 편집기 패널

메인 윈도우 내에서 신호 파라미터를 직접 편집할 수 있는 폼 패널입니다.
팝업 다이얼로그 방식 대신 인라인 편집으로 사용성을 개선했습니다.

주요 기능:
  - 새 신호 추가 (신호 추가 버튼)
  - 기존 신호 수정 (신호 수정 버튼, SignalTableWidget에서 콜백 호출)
  - 신호 색상 선택 (컬러 피커)

피드백 13번:
  신호 추가/수정 동작 확인 및 모델 리스트에서 신호 선택 시
  올바른 인덱스가 전달되도록 수정.
  주요 수정 사항:
    - _on_save()에서 signal_manager.update_signal()에 전달하는 신호가
      model_store의 해당 모델 signals 리스트에도 반영되도록 처리.
    - edit_signal(index) 호출 시 index 유효성 재검증.
"""

import tkinter as tk
from tkinter import ttk, messagebox, colorchooser
from signal_model import Signal


class ToolTip:
    """
    위젯에 마우스를 올렸을 때 나타나는 툴팁

    Attributes:
        waittime (int): 툴팁 표시까지 대기 시간 (ms)
        wraplength (int): 텍스트 줄바꿈 너비 (px)
        widget: 툴팁을 연결할 위젯
        text (str): 표시할 텍스트
    """

    def __init__(self, widget, text='widget info'):
        self.waittime   = 500
        self.wraplength = 300
        self.widget     = widget
        self.text       = text
        self.id         = None
        self.tw         = None
        self.widget.bind("<Enter>",       self.enter)
        self.widget.bind("<Leave>",       self.leave)
        self.widget.bind("<ButtonPress>", self.leave)

    def enter(self, event=None):
        self.schedule()

    def leave(self, event=None):
        self.unschedule()
        self.hidetip()

    def schedule(self):
        self.unschedule()
        self.id = self.widget.after(self.waittime, self.showtip)

    def unschedule(self):
        _id = self.id
        self.id = None
        if _id:
            self.widget.after_cancel(_id)

    def showtip(self, event=None):
        """툴팁 팝업 표시"""
        x, y, cx, cy = self.widget.bbox("insert")
        x += self.widget.winfo_rootx() + 25
        y += self.widget.winfo_rooty() + 20
        self.tw = tk.Toplevel(self.widget)
        self.tw.wm_overrideredirect(True)   # 타이틀바 없음
        self.tw.wm_geometry(f"+{x}+{y}")
        label = tk.Label(
            self.tw, text=self.text, justify='left',
            background="#ffffe0", relief='solid', borderwidth=1,
            font=("tahoma", "8", "normal"),
            wraplength=self.wraplength
        )
        label.pack(ipadx=1)

    def hidetip(self):
        """툴팁 팝업 숨김"""
        tw = self.tw
        self.tw = None
        if tw:
            tw.destroy()


class SignalEditorPanel(tk.Frame):
    """
    인라인 신호 편집기 패널

    신호의 모든 파라미터(이름, 타입, 모드, 전압, 타이밍 등)를 입력받는
    폼을 제공합니다.

    모드:
      - 신호 추가 모드 (current_index=None): "신호 추가" 버튼 표시
      - 신호 수정 모드 (current_index=int): "신호 수정" 버튼 표시

    Attributes:
        signal_manager: SignalManager 인스턴스
        model_store: ModelStore 인스턴스 (신호 수정 시 model_store에도 반영)
        current_index (int|None): 현재 편집 중인 신호 인덱스
        entries (dict): 입력 필드 위젯 (key → (Entry, dtype))
        color_var (StringVar): 색상 변수
        color_btn (Button): 색상 표시 버튼
    """

    def __init__(self, parent, signal_manager, model_store=None):
        """
        초기화 메서드

        Args:
            parent: 부모 위젯
            signal_manager (SignalManager): 신호 관리자
            model_store: ModelStore 인스턴스 (신호 수정 후 동기화용, 선택적)
        """
        super().__init__(parent, relief=tk.RAISED, borderwidth=2, bg='#f0f0f0')

        self.signal_manager = signal_manager
        self.model_store    = model_store    # 수정 후 model_store 동기화용
        self.current_index  = None           # None이면 새 신호 추가, int이면 수정
        self.entries        = {}             # { key: (Entry 위젯, dtype 문자열) }
        self.color_var      = None
        self.color_btn      = None

        self._setup_ui()

    def _setup_ui(self):
        """폼 UI 구성"""
        form_frame = tk.Frame(self, bg='#f0f0f0', padx=15, pady=10)
        form_frame.pack(side=tk.TOP, fill=tk.BOTH, expand=True)

        # 입력 필드 정의: (key, 라벨, 기본값, dtype)
        fields = [
            ('name',      '신호 이름',     'Signal1',  'str'),
            ('sig_type',  'SIG TYPE',      '',         'str'),
            ('sig_mode',  'SIG MODE',      '0',        'int'),
            ('inversion', 'INVERSION',     '0',        'int'),
            ('v1',        'V1 (V)',         '0.0',     'float'),
            ('v2',        'V2 (V)',         '3.3',     'float'),
            ('v3',        'V3 (V)',         '0.0',     'float'),
            ('v4',        'V4 (V)',         '3.3',     'float'),
            ('delay',     'DELAY (us)',     '0.0',     'float'),
            ('width',     'WIDTH (us)',    '100.0',    'float'),
            ('period',    'PERIOD (us)',   '200.0',    'float'),
        ]

        # 2열 그리드 레이아웃
        for idx, (key, label, default, dtype) in enumerate(fields):
            row = idx // 2
            col = idx % 2

            field_frame = tk.Frame(form_frame, bg='#f0f0f0')
            field_frame.grid(row=row, column=col, sticky='ew', padx=5, pady=3)

            label_widget = tk.Label(
                field_frame, text=label, font=('Arial', 9),
                bg='#f0f0f0', fg='#000', width=12, anchor='w'
            )
            label_widget.pack(side=tk.LEFT)

            # SIG MODE에 툴팁 추가
            if key == 'sig_mode':
                help_icon = tk.Label(
                    field_frame, text="❓", font=('Arial', 9),
                    bg='#f0f0f0', fg='blue', cursor="hand2"
                )
                help_icon.pack(side=tk.LEFT, padx=(0, 5))
                help_text = (
                    "일반 모드 (Delay, Width, Period > 0):\n"
                    "  MODE=0, INV=0: V1,V2 사용 / 프레임별 반전 없음\n"
                    "  MODE=0, INV=1: V1,V2 사용 / 프레임별 반전 적용\n"
                    "  MODE=1, INV=0: 홀수 프레임: V1,V2 / 짝수 프레임: V3,V4\n"
                    "  MODE=1, INV=1: 홀수 프레임: V1,V2 / 짝수 프레임: V4,V3\n\n"
                    "DC 모드 (Delay=0, Width=0, Period=0):\n"
                    "  MODE=0, INV=0: V1 DC 출력\n"
                    "  MODE=0, INV=1: 프레임별 V1, V2 반복\n"
                    "  MODE=1, INV=0: 프레임별 V1, V3 반복\n"
                    "  MODE=1, INV=1: 프레임별 V1, V4 반복"
                )
                ToolTip(help_icon, help_text)

            entry = tk.Entry(
                field_frame, font=('Arial', 9), width=15,
                bg='white', fg='black', relief=tk.SOLID, borderwidth=1
            )
            entry.pack(side=tk.LEFT, fill=tk.X, expand=True)
            entry.insert(0, default)
            self.entries[key] = (entry, dtype)

        # 색상 선택 필드
        color_frame = tk.Frame(form_frame, bg='#f0f0f0')
        color_frame.grid(
            row=len(fields) // 2, column=len(fields) % 2,
            sticky='ew', padx=5, pady=3
        )
        tk.Label(
            color_frame, text="색상", font=('Arial', 9),
            bg='#f0f0f0', fg='#000', width=12, anchor='w'
        ).pack(side=tk.LEFT)

        self.color_var = tk.StringVar(value="#0000FF")
        self.color_btn = tk.Button(
            color_frame, text="색상 선택", bg="#0000FF", fg="white",
            command=self._choose_color, width=15
        )
        self.color_btn.pack(side=tk.LEFT, fill=tk.X, expand=True)

        form_frame.grid_columnconfigure(0, weight=1)
        form_frame.grid_columnconfigure(1, weight=1)

        # 버튼 (신호 추가 / 취소)
        btn_frame = tk.Frame(self, bg='#f0f0f0', pady=10)
        btn_frame.pack(side=tk.TOP, fill=tk.X)

        _BTN = dict(bg='#e8e8e8', fg='#333333', font=('Arial', 10),
                    relief=tk.GROOVE, borderwidth=1, width=12)
        self.save_btn = tk.Button(btn_frame, text="신호 추가",
                                  command=self._on_save, **_BTN)
        self.save_btn.pack(side=tk.LEFT, padx=5)

        tk.Button(btn_frame, text="취소", command=self._on_cancel,
                  **_BTN).pack(side=tk.LEFT, padx=5)

    def _choose_color(self):
        """색상 선택 다이얼로그 열기"""
        color = colorchooser.askcolor(title="신호 색상 선택",
                                       color=self.color_var.get())
        if color[1]:
            self.color_var.set(color[1])
            self.color_btn.config(bg=color[1])

    def edit_signal(self, index=None):
        """
        편집 모드 설정

        Args:
            index (int|None): 수정할 신호의 인덱스.
                              None이면 새 신호 추가 모드.
        """
        # 피드백 13번: 유효하지 않은 인덱스 방어 처리
        signals = self.signal_manager.get_all_signals()
        if index is not None and not (0 <= index < len(signals)):
            messagebox.showwarning("경고", "유효하지 않은 신호 인덱스입니다.")
            return

        self.current_index = index

        if index is None:
            # 새 신호 추가 모드: 버튼 녹색, 필드 초기화
            self.save_btn.config(text="신호 추가", bg='#4CAF50')
            self._clear_fields()
        else:
            # 기존 신호 수정 모드: 버튼 주황색, 신호 데이터 로드
            self.save_btn.config(text="신호 수정", bg='#FF9800')
            signal = self.signal_manager.get_signal(index)
            if signal:
                self._load_signal_data(signal)

    def _clear_fields(self):
        """모든 입력 필드를 기본값으로 초기화"""
        defaults = {
            'name':      'Signal1',
            'sig_type':  '',
            'sig_mode':  '0',
            'inversion': '0',
            'v1':        '0.0',
            'v2':        '3.3',
            'v3':        '0.0',
            'v4':        '3.3',
            'delay':     '0.0',
            'width':     '100.0',
            'period':    '200.0',
        }
        for key, (entry, _) in self.entries.items():
            entry.delete(0, tk.END)
            entry.insert(0, defaults.get(key, ''))
        self.color_var.set("#0000FF")
        self.color_btn.config(bg="#0000FF")

    def _load_signal_data(self, signal: Signal):
        """
        신호 데이터를 입력 필드에 로드

        Args:
            signal (Signal): 로드할 신호 객체
        """
        field_map = {
            'name':      signal.name,
            'sig_type':  signal.sig_type,
            'sig_mode':  str(signal.sig_mode),
            'inversion': str(signal.inversion),
            'v1':        str(signal.v1),
            'v2':        str(signal.v2),
            'v3':        str(signal.v3),
            'v4':        str(signal.v4),
            'delay':     str(signal.delay),
            'width':     str(signal.width),
            'period':    str(signal.period),
        }
        for key, value in field_map.items():
            if key in self.entries:
                entry, _ = self.entries[key]
                entry.delete(0, tk.END)
                entry.insert(0, value)
        if hasattr(signal, 'color') and signal.color:
            try:
                self.color_var.set(signal.color)
                self.color_btn.config(bg=signal.color)
            except Exception:
                pass  # 잘못된 색상 코드 무시

    def _validate_and_get_values(self):
        """
        입력값 유효성 검사 및 데이터 추출

        Returns:
            dict: 유효한 입력값 딕셔너리 (실패 시 None 반환)
        """
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
                                     f"'{key}' 필드의 값이 올바르지 않습니다: '{value_str}'")
                return None

        # 신호 이름 필수 검사
        if not values.get('name'):
            messagebox.showerror("입력 오류", "신호 이름을 입력하세요.")
            return None

        # SIG MODE 범위 검사 (0 또는 1)
        if values.get('sig_mode') not in [0, 1]:
            messagebox.showerror("입력 오류", "SIG MODE는 0 또는 1이어야 합니다.")
            return None

        # INVERSION 범위 검사 (0 또는 1)
        if values.get('inversion') not in [0, 1]:
            messagebox.showerror("입력 오류", "INVERSION은 0 또는 1이어야 합니다.")
            return None

        values['color'] = self.color_var.get()
        return values

    def _on_save(self):
        """
        저장 버튼 핸들러 (신호 추가 또는 수정)

        피드백 13번: 수정 후 model_store의 현재 모델 signals에도 반영.
        """
        values = self._validate_and_get_values()
        if values is None:
            return

        # Signal 객체 생성
        signal = Signal(
            name      = values['name'],
            sig_type  = values['sig_type'],
            sig_mode  = values['sig_mode'],
            inversion = values['inversion'],
            v1        = values['v1'],
            v2        = values['v2'],
            v3        = values['v3'],
            v4        = values['v4'],
            delay     = values['delay'],
            width     = values['width'],
            period    = values['period'],
            color     = values['color'],
        )

        if self.current_index is None:
            # ── 새 신호 추가 ──────────────────────────
            self.signal_manager.add_signal(signal)

            # model_store 현재 모델에도 추가 동기화
            if self.model_store and self.model_store.current_model is not None:
                self.model_store.current_model.signals.append(signal)

        else:
            # ── 기존 신호 수정 ─────────────────────────
            # 현재 인덱스의 유효성 재확인
            signals = self.signal_manager.get_all_signals()
            if not (0 <= self.current_index < len(signals)):
                messagebox.showerror("오류", "수정할 신호 인덱스가 유효하지 않습니다.")
                return

            self.signal_manager.update_signal(self.current_index, signal)

            # model_store 현재 모델에도 수정 동기화
            if self.model_store and self.model_store.current_model is not None:
                model_signals = self.model_store.current_model.signals
                if 0 <= self.current_index < len(model_signals):
                    model_signals[self.current_index] = signal

        # 폼 초기화 및 추가 모드로 복귀
        self._clear_fields()
        self.current_index = None
        self.save_btn.config(text="신호 추가", bg='#4CAF50')

    def _on_cancel(self):
        """취소 버튼 핸들러: 폼 초기화 및 추가 모드로 복귀"""
        self._clear_fields()
        self.current_index = None
        self.save_btn.config(text="신호 추가", bg='#4CAF50')
