"""
모델 관리 다이얼로그
디스플레이 모델(크기)과 각 모델별 주파수, H/V Total을 추가, 수정, 삭제하는 관리 창입니다.
"""

import tkinter as tk
from tkinter import ttk, messagebox


class ModelManagerDialog(tk.Toplevel):
    """
    모델 관리 다이얼로그 클래스
    
    모달 창으로 실행되며, 모델 목록과 각 모델의 주파수, H/V Total 설정을 관리합니다.
    """
    
    def __init__(self, parent, sync_data_manager):
        """
        초기화 메서드
        
        Args:
            parent: 부모 위젯
            sync_data_manager: SyncData 관리자 객체
        """
        super().__init__(parent)
        
        self.title("모델 관리")
        self.geometry("700x550")
        self.resizable(True, True)
        self.configure(bg='#f0f0f0')
        
        self.sync_data_manager = sync_data_manager
        self.result = False  # 변경 사항 발생 여부
        
        self._setup_ui()
        self._refresh_model_list()
        
        # 모달 다이얼로그 설정 (부모 창 제어 차단)
        self.transient(parent)
        self.grab_set()
        
        # 화면 중앙에 배치
        self.update_idletasks()
        x = (self.winfo_screenwidth() // 2) - (self.winfo_width() // 2)
        y = (self.winfo_screenheight() // 2) - (self.winfo_height() // 2)
        self.geometry(f"+{x}+{y}")
    
    def _setup_ui(self):
        """UI 구성"""
        # 타이틀 프레임
        title_frame = tk.Frame(self, bg='#2196F3')
        title_frame.pack(side=tk.TOP, fill=tk.X)
        
        tk.Label(title_frame, text="디스플레이 모델 관리", 
                font=('Arial', 14, 'bold'), bg='#2196F3', fg='black', 
                pady=10).pack()
        
        # 메인 컨테이너
        main_frame = tk.Frame(self, bg='#f0f0f0', padx=20, pady=20)
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # 좌측: 모델 목록
        left_frame = tk.LabelFrame(main_frame, text="모델 목록", 
                                  font=('Arial', 10, 'bold'), 
                                  bg='#f0f0f0', fg='#000', padx=10, pady=10)
        left_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 10))
        
        # 리스트박스 및 스크롤바
        list_container = tk.Frame(left_frame, bg='white')
        list_container.pack(fill=tk.BOTH, expand=True)
        
        scrollbar = tk.Scrollbar(list_container)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        self.model_listbox = tk.Listbox(list_container, font=('Arial', 10),
                                       bg='white', fg='black',
                                       yscrollcommand=scrollbar.set,
                                       selectmode=tk.SINGLE)
        self.model_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.config(command=self.model_listbox.yview)
        
        # 목록 선택 이벤트 바인딩
        self.model_listbox.bind('<<ListboxSelect>>', self._on_model_selected)
        
        # 모델 추가/삭제 버튼
        model_btn_frame = tk.Frame(left_frame, bg='#f0f0f0')
        model_btn_frame.pack(fill=tk.X, pady=(10, 0))
        
        tk.Button(model_btn_frame, text="새 모델", command=self._on_new_model,
                 bg='#4CAF50', fg='black', font=('Arial', 9, 'bold'),
                 relief=tk.RAISED, borderwidth=2).pack(side=tk.LEFT, padx=2)
        tk.Button(model_btn_frame, text="모델 삭제", command=self._on_delete_model,
                 bg='#f44336', fg='black', font=('Arial', 9, 'bold'),
                 relief=tk.RAISED, borderwidth=2).pack(side=tk.LEFT, padx=2)
        
        # 우측: 모델 상세 정보
        right_frame = tk.LabelFrame(main_frame, text="모델 정보", 
                                   font=('Arial', 10, 'bold'),
                                   bg='#f0f0f0', fg='#000', padx=10, pady=10)
        right_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        # 모델 이름 입력
        tk.Label(right_frame, text="모델 이름:", font=('Arial', 9),
                bg='#f0f0f0', fg='#000').grid(row=0, column=0, sticky='w', pady=5)
        
        self.model_name_entry = tk.Entry(right_frame, font=('Arial', 9), width=20,
                                         bg='white', fg='black')
        self.model_name_entry.grid(row=0, column=1, sticky='ew', pady=5, padx=5)
        
        tk.Label(right_frame, text='(예: 12.3", 20.5")', font=('Arial', 8),
                bg='#f0f0f0', fg='#666').grid(row=0, column=2, sticky='w', pady=5)
        
        # H Total 입력
        tk.Label(right_frame, text="H Total:", font=('Arial', 9),
                bg='#f0f0f0', fg='#000').grid(row=1, column=0, sticky='w', pady=5)
        
        self.h_total_entry = tk.Entry(right_frame, font=('Arial', 9), width=10,
                                      bg='white', fg='black')
        self.h_total_entry.grid(row=1, column=1, sticky='w', pady=5, padx=5)
        self.h_total_entry.insert(0, "1000")
        
        # V Total 입력
        tk.Label(right_frame, text="V Total:", font=('Arial', 9),
                bg='#f0f0f0', fg='#000').grid(row=2, column=0, sticky='w', pady=5)
        
        self.v_total_entry = tk.Entry(right_frame, font=('Arial', 9), width=10,
                                      bg='white', fg='black')
        self.v_total_entry.grid(row=2, column=1, sticky='w', pady=5, padx=5)
        self.v_total_entry.insert(0, "1000")
        
        # 주파수 목록
        tk.Label(right_frame, text="주파수 목록:", font=('Arial', 9),
                bg='#f0f0f0', fg='#000').grid(row=3, column=0, sticky='nw', pady=5)
        
        freq_container = tk.Frame(right_frame, bg='white')
        freq_container.grid(row=3, column=1, columnspan=2, sticky='ew', pady=5, padx=5)
        
        freq_scrollbar = tk.Scrollbar(freq_container)
        freq_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        self.freq_listbox = tk.Listbox(freq_container, font=('Arial', 9),
                                      height=6, bg='white', fg='black',
                                      yscrollcommand=freq_scrollbar.set)
        self.freq_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        freq_scrollbar.config(command=self.freq_listbox.yview)
        
        # 주파수 추가/삭제 입력
        freq_input_frame = tk.Frame(right_frame, bg='#f0f0f0')
        freq_input_frame.grid(row=4, column=1, columnspan=2, sticky='ew', pady=5, padx=5)
        
        tk.Label(freq_input_frame, text="주파수 (Hz):", font=('Arial', 9),
                bg='#f0f0f0', fg='#000').pack(side=tk.LEFT)
        
        self.freq_entry = tk.Entry(freq_input_frame, font=('Arial', 9), width=10,
                                   bg='white', fg='black')
        self.freq_entry.pack(side=tk.LEFT, padx=5)
        
        tk.Button(freq_input_frame, text="추가", command=self._on_add_frequency,
                 bg='#4CAF50', fg='black', font=('Arial', 8, 'bold'),
                 relief=tk.RAISED, borderwidth=2).pack(side=tk.LEFT, padx=2)
        tk.Button(freq_input_frame, text="삭제", command=self._on_delete_frequency,
                 bg='#f44336', fg='black', font=('Arial', 8, 'bold'),
                 relief=tk.RAISED, borderwidth=2).pack(side=tk.LEFT, padx=2)
        
        # 모델 저장 버튼
        tk.Button(right_frame, text="모델 저장", command=self._on_save_model,
                 bg='#2196F3', fg='black', font=('Arial', 10, 'bold'),
                 relief=tk.RAISED, borderwidth=2).grid(row=5, column=1, columnspan=2, 
                                                       sticky='ew', pady=10, padx=5)
        
        right_frame.grid_columnconfigure(1, weight=1)
        
        # 하단: 닫기 버튼
        bottom_frame = tk.Frame(self, bg='#f0f0f0', pady=10)
        bottom_frame.pack(side=tk.BOTTOM, fill=tk.X)
        
        tk.Button(bottom_frame, text="닫기", command=self._on_close,
                 bg='#9E9E9E', fg='black', font=('Arial', 10, 'bold'),
                 width=15, relief=tk.RAISED, borderwidth=2).pack()
    
    def _refresh_model_list(self):
        """모델 목록 갱신"""
        self.model_listbox.delete(0, tk.END)
        models = self.sync_data_manager.get_model_list()
        for model in models:
            frequencies = self.sync_data_manager.get_frequency_list(model)
            freq_str = ", ".join([f"{f}Hz" for f in frequencies])
            self.model_listbox.insert(tk.END, f"{model} ({freq_str})")
    
    def _on_model_selected(self, event=None):
        """모델 선택 이벤트 핸들러"""
        selection = self.model_listbox.curselection()
        if not selection:
            return
        
        idx = selection[0]
        models = self.sync_data_manager.get_model_list()
        if idx < len(models):
            model = models[idx]
            self.model_name_entry.delete(0, tk.END)
            self.model_name_entry.insert(0, model)
            
            # H/V Total 로드
            params = self.sync_data_manager.get_model_params(model)
            self.h_total_entry.delete(0, tk.END)
            self.h_total_entry.insert(0, str(params['h_total']))
            self.v_total_entry.delete(0, tk.END)
            self.v_total_entry.insert(0, str(params['v_total']))
            
            # 주파수 목록 로드
            self.freq_listbox.delete(0, tk.END)
            frequencies = self.sync_data_manager.get_frequency_list(model)
            for freq in frequencies:
                self.freq_listbox.insert(tk.END, f"{freq} Hz")
    
    def _on_new_model(self):
        """새 모델 버튼 핸들러 (입력 필드 초기화)"""
        self.model_name_entry.delete(0, tk.END)
        self.h_total_entry.delete(0, tk.END)
        self.h_total_entry.insert(0, "1000")
        self.v_total_entry.delete(0, tk.END)
        self.v_total_entry.insert(0, "1000")
        self.freq_listbox.delete(0, tk.END)
        self.model_name_entry.focus()
    
    def _on_save_model(self):
        """모델 저장 버튼 핸들러"""
        model_name = self.model_name_entry.get().strip()
        if not model_name:
            messagebox.showerror("오류", "모델 이름을 입력하세요.")
            return
        
        try:
            h_total = int(self.h_total_entry.get())
            v_total = int(self.v_total_entry.get())
            if h_total <= 0 or v_total <= 0:
                raise ValueError()
        except ValueError:
            messagebox.showerror("오류", "H/V Total은 양의 정수여야 합니다.")
            return
        
        # 리스트박스에서 주파수 목록 추출
        frequencies = []
        for i in range(self.freq_listbox.size()):
            freq_str = self.freq_listbox.get(i)
            freq = int(freq_str.split()[0])
            frequencies.append(freq)
        
        if not frequencies:
            messagebox.showerror("오류", "최소 하나의 주파수를 추가하세요.")
            return
        
        # 모델 추가 또는 업데이트
        self.sync_data_manager.add_model(model_name, frequencies, h_total, v_total)
        self._refresh_model_list()
        messagebox.showinfo("완료", f"{model_name} 모델이 저장되었습니다.")
        self.result = True
    
    def _on_delete_model(self):
        """모델 삭제 버튼 핸들러"""
        selection = self.model_listbox.curselection()
        if not selection:
            messagebox.showwarning("경고", "삭제할 모델을 선택하세요.")
            return
        
        idx = selection[0]
        models = self.sync_data_manager.get_model_list()
        if idx < len(models):
            model = models[idx]
            if messagebox.askyesno("확인", f"{model} 모델을 삭제하시겠습니까?"):
                self.sync_data_manager.remove_model(model)
                self._refresh_model_list()
                self._on_new_model()
                self.result = True
    
    def _on_add_frequency(self):
        """주파수 추가 버튼 핸들러"""
        freq_str = self.freq_entry.get().strip()
        if not freq_str:
            return
        
        try:
            freq = int(freq_str)
            if freq <= 0:
                raise ValueError()
            
            # 중복 체크
            for i in range(self.freq_listbox.size()):
                existing = self.freq_listbox.get(i)
                if f"{freq} Hz" == existing:
                    messagebox.showwarning("경고", "이미 존재하는 주파수입니다.")
                    return
            
            self.freq_listbox.insert(tk.END, f"{freq} Hz")
            self.freq_entry.delete(0, tk.END)
        except ValueError:
            messagebox.showerror("오류", "유효한 주파수를 입력하세요 (양의 정수).")
    
    def _on_delete_frequency(self):
        """주파수 삭제 버튼 핸들러"""
        selection = self.freq_listbox.curselection()
        if not selection:
            messagebox.showwarning("경고", "삭제할 주파수를 선택하세요.")
            return
        
        self.freq_listbox.delete(selection[0])
    
    def _on_close(self):
        """닫기 버튼 핸들러"""
        self.destroy()
    
    def get_result(self):
        """
        다이얼로그 결과 반환
        
        Returns:
            bool: 변경 사항이 있으면 True, 없으면 False
        """
        self.wait_window()
        return self.result
