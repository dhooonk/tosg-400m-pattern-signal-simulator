"""
신호 목록 위젯 (SignalTableWidget)
신호 리스트를 테이블 형태로 표시하고 추가/수정/삭제 기능을 제공합니다.
"""

import tkinter as tk
from tkinter import ttk, messagebox
import copy
from signal_model import Signal


class SignalTableWidget(tk.Frame):
    """
    신호 목록 테이블 위젯
    
    Treeview를 사용하여 신호 목록을 표시하고, 상단에 CRUD 버튼을 배치합니다.
    SignalManager와 연동하여 데이터 변경 시 자동으로 테이블을 갱신합니다.
    """
    
    def __init__(self, parent, signal_manager, on_edit_callback):
        """
        초기화 메서드
        
        Args:
            parent: 부모 위젯
            signal_manager (SignalManager): 신호 관리자 객체
            on_edit_callback (callable): 신호 수정/추가 시 호출될 콜백 함수
        """
        super().__init__(parent, bg='#f0f0f0')
        
        self.signal_manager = signal_manager
        self.on_edit_callback = on_edit_callback
        
        self._setup_ui()
        
        # 신호 변경 리스너 등록 (데이터 변경 시 테이블 자동 갱신)
        self.signal_manager.add_listener(self.refresh_table)
    
    def _setup_ui(self):
        """UI 구성"""
        # 버튼 프레임 (상단)
        btn_frame = tk.Frame(self, bg='#f0f0f0')
        btn_frame.pack(side=tk.TOP, fill=tk.X, padx=5, pady=5)
        
        # CRUD 버튼 생성
        _BTN = dict(bg='#e8e8e8', fg='#333333', font=('Arial', 9),
                    relief=tk.GROOVE, borderwidth=1)
        tk.Button(btn_frame, text="신호 추가", command=self._on_add,    **_BTN).pack(side=tk.LEFT, padx=2)
        tk.Button(btn_frame, text="신호 수정", command=self._on_edit,   **_BTN).pack(side=tk.LEFT, padx=2)
        tk.Button(btn_frame, text="신호 복제", command=self._on_duplicate, **_BTN).pack(side=tk.LEFT, padx=2)
        tk.Button(btn_frame, text="신호 삭제", command=self._on_delete,  **_BTN).pack(side=tk.LEFT, padx=2)
        tk.Button(btn_frame, text="전체 삭제", command=self._on_clear,   **_BTN).pack(side=tk.LEFT, padx=2)

        # 순서 변경 버튼
        tk.Button(btn_frame, text="위로 ↑",   command=self._on_move_up,   **_BTN).pack(side=tk.LEFT, padx=2)
        tk.Button(btn_frame, text="아래로 ↓", command=self._on_move_down, **_BTN).pack(side=tk.LEFT, padx=2)
        
        # 테이블 프레임
        table_frame = tk.Frame(self, bg='white')
        table_frame.pack(side=tk.TOP, fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # 스크롤바 생성
        scrollbar_y = tk.Scrollbar(table_frame, orient=tk.VERTICAL)
        scrollbar_x = tk.Scrollbar(table_frame, orient=tk.HORIZONTAL)
        
        # Treeview (테이블) 생성
        # Color, Visible 컬럼 추가
        columns = ('Visible', 'Color', 'Name', 'Type', 'Mode', 'Inv', 'V1', 'V2', 'V3', 'V4', 
                  'Delay', 'Width', 'Period')
        
        # 가시성을 위한 커스텀 스타일 설정
        style = ttk.Style()
        style.configure("Custom.Treeview", 
                       background="white",
                       foreground="black",
                       fieldbackground="white",
                       font=('Arial', 9))
        style.configure("Custom.Treeview.Heading",
                       background="#2196F3",
                       foreground="white",
                       font=('Arial', 10, 'bold'))
        
        self.tree = ttk.Treeview(table_frame, columns=columns, show='headings',
                                yscrollcommand=scrollbar_y.set,
                                xscrollcommand=scrollbar_x.set,
                                style="Custom.Treeview")
        
        # 행 텍스트 색상을 검정색으로 강제 설정하기 위한 태그
        self.tree.tag_configure('blacktext', foreground='black')
        
        # 컬럼 너비 및 정렬 설정
        col_widths = {
            'Visible': 50, 'Color': 50, 'Name': 100, 'Type': 60, 'Mode': 50, 'Inv': 40,
            'V1': 60, 'V2': 60, 'V3': 60, 'V4': 60,
            'Delay': 70, 'Width': 70, 'Period': 70
        }
        
        for col in columns:
            self.tree.heading(col, text=col)
            self.tree.column(col, width=col_widths.get(col, 80), anchor='center')
        
        # 스크롤바 연결
        scrollbar_y.config(command=self.tree.yview)
        scrollbar_x.config(command=self.tree.xview)
        
        # 그리드 배치
        self.tree.grid(row=0, column=0, sticky='nsew')
        scrollbar_y.grid(row=0, column=1, sticky='ns')
        scrollbar_x.grid(row=1, column=0, sticky='ew')
        
        table_frame.grid_rowconfigure(0, weight=1)
        table_frame.grid_columnconfigure(0, weight=1)
        
        # 더블클릭 이벤트 바인딩 (수정 기능)
        self.tree.bind('<Double-1>', lambda e: self._on_edit())
        
        # 클릭 이벤트 바인딩 (Visible 체크박스 토글)
        self.tree.bind('<Button-1>', self._on_tree_click)
    
    def refresh_table(self):
        """
        테이블 갱신
        
        SignalManager에서 최신 신호 목록을 가져와 테이블을 다시 그립니다.
        """
        # 기존 항목 모두 삭제
        for item in self.tree.get_children():
            self.tree.delete(item)
        
        # 신호 목록 가져오기 및 추가
        signals = self.signal_manager.get_all_signals()
        for signal in signals:
            # 색상 정보가 없으면 기본값 사용
            color_hex = getattr(signal, 'color', '#0000FF')
            visible = getattr(signal, 'visible', True)
            visible_str = "☑" if visible else "☐"
            
            values = (
                visible_str,  # 가시성 체크박스
                "■", # 색상 표시용 문자
                signal.name,
                signal.sig_type,
                signal.sig_mode,
                signal.inversion,
                f"{signal.v1:.2f}V",
                f"{signal.v2:.2f}V",
                f"{signal.v3:.2f}V",
                f"{signal.v4:.2f}V",
                f"{signal.delay:.1f}us",
                f"{signal.width:.1f}us",
                f"{signal.period:.1f}us"
            )
            
            # 태그 생성 (색상별로 다른 태그 사용)
            # 색상 사각형(■)이 신호 색상으로 표시되도록 foreground 색상 설정
            tag_name = f"color_{color_hex.replace('#', '')}"
            self.tree.tag_configure(tag_name, foreground=color_hex)
            
            # 색상 태그를 적용하여 색상 사각형이 신호 색상으로 표시됨
            item_id = self.tree.insert('', tk.END, values=values, tags=(tag_name,))
    
    def get_selected_index(self):
        """
        선택된 항목의 인덱스 반환
        
        Returns:
            int: 선택된 항목의 인덱스 (없으면 None)
        """
        selection = self.tree.selection()
        if not selection:
            return None
        
        item = selection[0]
        return self.tree.index(item)
    
    def _on_add(self):
        """신호 추가 버튼 핸들러"""
        # 콜백 호출 (인덱스 None은 새 신호 추가를 의미)
        self.on_edit_callback(None)
    
    def _on_edit(self):
        """신호 수정 버튼 핸들러"""
        index = self.get_selected_index()
        if index is None:
            messagebox.showwarning("경고", "수정할 신호를 선택하세요.")
            return
        
        # 콜백 호출 (선택된 인덱스 전달)
        self.on_edit_callback(index)
        
    def _on_duplicate(self):
        """신호 복제 버튼 핸들러"""
        index = self.get_selected_index()
        if index is None:
            messagebox.showwarning("경고", "복제할 신호를 선택하세요.")
            return
        
        # 선택된 신호 가져오기
        original_signal = self.signal_manager.get_signal(index)
        if original_signal:
            # 신호 복제 (Deep Copy)
            new_signal = copy.deepcopy(original_signal)
            new_signal.name = f"{new_signal.name}_Copy"
            
            # 신호 추가
            self.signal_manager.add_signal(new_signal)
            messagebox.showinfo("완료", f"'{original_signal.name}' 신호가 복제되었습니다.")
    
    def _on_delete(self):
        """신호 삭제 버튼 핸들러"""
        index = self.get_selected_index()
        if index is None:
            messagebox.showwarning("경고", "삭제할 신호를 선택하세요.")
            return
        
        if messagebox.askyesno("확인", "선택한 신호를 삭제하시겠습니까?"):
            self.signal_manager.remove_signal(index)
    
    def _on_clear(self):
        """전체 삭제 버튼 핸들러"""
        if not self.signal_manager.get_all_signals():
            return
        
        if messagebox.askyesno("확인", "모든 신호를 삭제하시겠습니까?"):
            self.signal_manager.clear_signals()
    
    def _on_move_up(self):
        """신호 위로 이동 버튼 핸들러"""
        index = self.get_selected_index()
        if index is None:
            messagebox.showwarning("경고", "이동할 신호를 선택하세요.")
            return
        
        if index == 0:
            messagebox.showinfo("정보", "이미 맨 위에 있습니다.")
            return
        
        self.signal_manager.move_signal_up(index)
    
    def _on_move_down(self):
        """신호 아래로 이동 버튼 핸들러"""
        index = self.get_selected_index()
        if index is None:
            messagebox.showwarning("경고", "이동할 신호를 선택하세요.")
            return
        
        signals = self.signal_manager.get_all_signals()
        if index == len(signals) - 1:
            messagebox.showinfo("정보", "이미 맨 아래에 있습니다.")
            return
        
        self.signal_manager.move_signal_down(index)
    
    def _on_tree_click(self, event):
        """트리 클릭 이벤트 핸들러 (Visible 체크박스 토글)"""
        region = self.tree.identify_region(event.x, event.y)
        if region != "cell":
            return
        
        column = self.tree.identify_column(event.x)
        item = self.tree.identify_row(event.y)
        
        # Visible 컬럼 (#1)을 클릭한 경우
        if column == '#1' and item:
            index = self.tree.index(item)
            signal = self.signal_manager.get_signal(index)
            if signal:
                signal.visible = not signal.visible
                self.signal_manager._notify_listeners()
