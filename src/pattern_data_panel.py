"""
패턴 데이터 패널
PATTERN_DATA (PTN 목록: NUM, NAME, R/G/B/W V1-V4, TYPE) 을 표시하고 편집합니다.
"""

import tkinter as tk
from tkinter import ttk, messagebox


_VOLTAGE_KEYS = [
    'r_v1', 'r_v2', 'r_v3', 'r_v4',
    'g_v1', 'g_v2', 'g_v3', 'g_v4',
    'b_v1', 'b_v2', 'b_v3', 'b_v4',
    'w_v1', 'w_v2', 'w_v3', 'w_v4',
]


def _is_zero_pattern(p: dict) -> bool:
    """모든 전압 값이 0인 편집되지 않은 빈 패턴인지 확인"""
    return all(float(p.get(k, 0)) == 0 for k in _VOLTAGE_KEYS)


PATTERN_TYPE_NAMES = {
    0: '-',    1: 'A',     2: 'B',    3: 'PF1',  4: 'PF2',
    5: 'PF3',  6: 'ZIV',  7: 'ZRB',  8: 'ZRB2', 9: 'ZRB3',
    10: 'MUX4D', 11: 'MUX1D'
}


class PatternDataPanel(tk.Frame):
    """
    패턴 데이터 목록 및 편집 패널
    
    외부에서 set_patterns(patterns) 로 패턴 목록을 세팅.
    get_patterns() 로 현재 편집된 패턴 목록을 얻을 수 있음.
    """

    # 테이블 컬럼 정의: (key, 표시명, 너비)
    COLUMNS = [
        ('ptn_no',  'No.',    40),
        ('name',    'NAME',   90),
        ('r_v1',    'R_V1',   55), ('r_v2','R_V2',55), ('r_v3','R_V3',55), ('r_v4','R_V4',55),
        ('g_v1',    'G_V1',   55), ('g_v2','G_V2',55), ('g_v3','G_V3',55), ('g_v4','G_V4',55),
        ('b_v1',    'B_V1',   55), ('b_v2','B_V2',55), ('b_v3','B_V3',55), ('b_v4','B_V4',55),
        ('w_v1',    'W_V1',   55), ('w_v2','W_V2',55), ('w_v3','W_V3',55), ('w_v4','W_V4',55),
        ('ptn_type','TYPE',   70),
    ]

    def __init__(self, parent):
        super().__init__(parent, bg='#f0f0f0')
        self._patterns: list = []   # List[dict]
        self._setup_ui()

    # ──────────────────────────────────────────────────────────
    def _setup_ui(self):
        """UI 구성"""
        # 상단: 버튼
        btn_frame = tk.Frame(self, bg='#f0f0f0')
        btn_frame.pack(side=tk.TOP, fill=tk.X, padx=5, pady=3)

        btn_cfg = dict(bg='#e8e8e8', fg='#333333', font=('Arial', 9),
                       relief=tk.GROOVE, borderwidth=1, width=10)
        tk.Button(btn_frame, text="추가",     command=self._on_add,    **btn_cfg).pack(side=tk.LEFT, padx=2)
        tk.Button(btn_frame, text="수정",     command=self._on_edit,   **btn_cfg).pack(side=tk.LEFT, padx=2)
        tk.Button(btn_frame, text="삭제",     command=self._on_delete, **btn_cfg).pack(side=tk.LEFT, padx=2)
        tk.Button(btn_frame, text="전체삭제", command=self._on_clear,  **btn_cfg).pack(side=tk.LEFT, padx=2)

        # 패턴 수 표시
        self._count_label = tk.Label(btn_frame, text="패턴: 0개", font=('Arial', 9),
                                     bg='#f0f0f0', fg='#333')
        self._count_label.pack(side=tk.RIGHT, padx=8)

        # 테이블
        table_frame = tk.Frame(self, bg='#f0f0f0')
        table_frame.pack(side=tk.TOP, fill=tk.BOTH, expand=True, padx=5, pady=3)

        col_ids = [c[0] for c in self.COLUMNS]
        self._tree = ttk.Treeview(table_frame, columns=col_ids, show='headings', height=8)

        for key, label, width in self.COLUMNS:
            self._tree.heading(key, text=label)
            self._tree.column(key, width=width, minwidth=30, anchor='center')

        # 스크롤바
        vsb = ttk.Scrollbar(table_frame, orient='vertical',   command=self._tree.yview)
        hsb = ttk.Scrollbar(table_frame, orient='horizontal',  command=self._tree.xview)
        self._tree.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)

        self._tree.grid(row=0, column=0, sticky='nsew')
        vsb.grid(row=0, column=1, sticky='ns')
        hsb.grid(row=1, column=0, sticky='ew')
        table_frame.grid_rowconfigure(0, weight=1)
        table_frame.grid_columnconfigure(0, weight=1)

        self._tree.bind('<Double-1>', lambda e: self._on_edit())

    # ──────────────────────────────────────────────────────────
    def set_patterns(self, patterns: list):
        """패턴 목록 설정 후 테이블 갱신 (모든 값이 0인 패턴은 제외)"""
        self._patterns = [dict(p) for p in patterns if not _is_zero_pattern(p)]
        self._refresh_table()

    def get_patterns(self) -> list:
        """현재 패턴 목록 반환"""
        return [dict(p) for p in self._patterns]

    def clear(self):
        """패턴 목록 초기화"""
        self._patterns.clear()
        self._refresh_table()

    # ──────────────────────────────────────────────────────────
    def _refresh_table(self):
        """테이블 전체 갱신"""
        for item in self._tree.get_children():
            self._tree.delete(item)

        for p in self._patterns:
            values = []
            for key, _, _ in self.COLUMNS:
                v = p.get(key, 0)
                if key == 'ptn_type':
                    v = PATTERN_TYPE_NAMES.get(int(v), str(v))
                elif key == 'name':
                    v = str(v)
                elif key == 'ptn_no':
                    v = str(v)
                else:
                    v = f"{float(v):.2f}"
                values.append(v)
            self._tree.insert('', 'end', values=values)

        self._count_label.config(text=f"패턴: {len(self._patterns)}개")

    def _get_selected_index(self) -> int:
        """선택된 행의 인덱스 반환 (-1이면 선택 없음)"""
        sel = self._tree.selection()
        if not sel:
            return -1
        return self._tree.index(sel[0])

    # ──────────────────────────────────────────────────────────
    def _on_add(self):
        """패턴 추가"""
        dlg = PatternEditDialog(self, None, len(self._patterns) + 1)
        result = dlg.get_result()
        if result is not None:
            self._patterns.append(result)
            self._refresh_table()

    def _on_edit(self):
        """선택 패턴 수정"""
        idx = self._get_selected_index()
        if idx < 0:
            messagebox.showwarning("선택 없음", "수정할 패턴을 선택하세요.")
            return
        dlg = PatternEditDialog(self, self._patterns[idx], idx + 1)
        result = dlg.get_result()
        if result is not None:
            self._patterns[idx] = result
            self._refresh_table()

    def _on_delete(self):
        """선택 패턴 삭제"""
        idx = self._get_selected_index()
        if idx < 0:
            messagebox.showwarning("선택 없음", "삭제할 패턴을 선택하세요.")
            return
        if messagebox.askyesno("확인", f"PTN{idx+1:02d} 을 삭제하시겠습니까?"):
            del self._patterns[idx]
            # 번호 재정렬
            for i, p in enumerate(self._patterns, 1):
                p['ptn_no'] = i
            self._refresh_table()

    def _on_clear(self):
        """전체 삭제"""
        if self._patterns and messagebox.askyesno("확인", "모든 패턴을 삭제하시겠습니까?"):
            self._patterns.clear()
            self._refresh_table()


# ────────────────────────────────────────────────────────────────
# 패턴 편집 다이얼로그
# ────────────────────────────────────────────────────────────────

class PatternEditDialog(tk.Toplevel):
    """패턴 데이터 추가/수정 다이얼로그"""

    VOLTAGE_FIELDS = [
        ('r_v1', 'R_V1 (V)'), ('r_v2', 'R_V2 (V)'), ('r_v3', 'R_V3 (V)'), ('r_v4', 'R_V4 (V)'),
        ('g_v1', 'G_V1 (V)'), ('g_v2', 'G_V2 (V)'), ('g_v3', 'G_V3 (V)'), ('g_v4', 'G_V4 (V)'),
        ('b_v1', 'B_V1 (V)'), ('b_v2', 'B_V2 (V)'), ('b_v3', 'B_V3 (V)'), ('b_v4', 'B_V4 (V)'),
        ('w_v1', 'W_V1 (V)'), ('w_v2', 'W_V2 (V)'), ('w_v3', 'W_V3 (V)'), ('w_v4', 'W_V4 (V)'),
    ]

    def __init__(self, parent, pattern: dict = None, ptn_no: int = 1):
        super().__init__(parent)
        self.title("패턴 편집")
        self.resizable(False, False)
        self._result = None
        self._ptn_no = ptn_no
        self._entries = {}
        self._pattern = pattern or {}
        self._setup_ui()

        if pattern:
            self._load(pattern)

        self.transient(parent)
        self.grab_set()
        self.update_idletasks()
        x = (self.winfo_screenwidth()  // 2) - (self.winfo_width()  // 2)
        y = (self.winfo_screenheight() // 2) - (self.winfo_height() // 2)
        self.geometry(f"+{x}+{y}")

    def _setup_ui(self):
        pad = dict(padx=6, pady=3)
        frm = tk.Frame(self, padx=15, pady=10)
        frm.pack(fill=tk.BOTH, expand=True)

        # 이름 / 번호
        tk.Label(frm, text=f"PTN No: {self._ptn_no:02d}", font=('Arial', 10, 'bold')).grid(
            row=0, column=0, columnspan=4, sticky='w', **pad)

        tk.Label(frm, text="NAME:", font=('Arial', 9)).grid(row=1, column=0, sticky='e', **pad)
        self._name_entry = tk.Entry(frm, width=20)
        self._name_entry.grid(row=1, column=1, columnspan=3, sticky='ew', **pad)
        self._name_entry.insert(0, self._pattern.get('name', f'PTN{self._ptn_no:02d}'))

        # 전압 필드 (4열 그리드)
        tk.Label(frm, text="전압 (V 단위)", font=('Arial', 9, 'bold')).grid(
            row=2, column=0, columnspan=4, sticky='w', padx=6, pady=(8, 2))

        for i, (key, label) in enumerate(self.VOLTAGE_FIELDS):
            row = 3 + i // 4
            col = (i % 4) * 2
            tk.Label(frm, text=label, font=('Arial', 8), width=9, anchor='e').grid(
                row=row, column=col, sticky='e', padx=(4, 1), pady=2)
            ent = tk.Entry(frm, width=8)
            ent.grid(row=row, column=col + 1, sticky='ew', padx=(0, 4), pady=2)
            ent.insert(0, '0.0')
            self._entries[key] = ent

        # TYPE
        type_row = 3 + len(self.VOLTAGE_FIELDS) // 4
        tk.Label(frm, text="TYPE:", font=('Arial', 9)).grid(row=type_row, column=0, sticky='e', **pad)
        self._type_combo = ttk.Combobox(frm, width=12, state='readonly')
        self._type_combo['values'] = [f"{k}: {v}" for k, v in PATTERN_TYPE_NAMES.items()]
        self._type_combo.current(0)
        self._type_combo.grid(row=type_row, column=1, columnspan=3, sticky='ew', **pad)

        # 버튼
        btn_row = type_row + 1
        _BTN = dict(bg='#e8e8e8', fg='#333333', font=('Arial', 10),
                    relief=tk.GROOVE, borderwidth=1, width=10)
        tk.Button(frm, text="확인", command=self._on_ok,     **_BTN).grid(
            row=btn_row, column=0, columnspan=2, pady=10)
        tk.Button(frm, text="취소", command=self.destroy,    **_BTN).grid(
            row=btn_row, column=2, columnspan=2, pady=10)

        frm.grid_columnconfigure(1, weight=1)
        frm.grid_columnconfigure(3, weight=1)

    def _load(self, p: dict):
        """기존 패턴 데이터 필드에 로드"""
        self._name_entry.delete(0, tk.END)
        self._name_entry.insert(0, p.get('name', ''))
        for key, ent in self._entries.items():
            ent.delete(0, tk.END)
            ent.insert(0, str(p.get(key, 0.0)))
        ptn_type = int(p.get('ptn_type', 0))
        self._type_combo.current(ptn_type if ptn_type < len(PATTERN_TYPE_NAMES) else 0)

    def _on_ok(self):
        result = {'ptn_no': self._ptn_no, 'name': self._name_entry.get().strip()}
        for key, ent in self._entries.items():
            try:
                result[key] = float(ent.get())
            except ValueError:
                messagebox.showerror("입력 오류", f"{key} 값이 올바르지 않습니다.")
                return
        type_idx = self._type_combo.current()
        result['ptn_type'] = type_idx
        self._result = result
        self.destroy()

    def get_result(self):
        self.wait_window()
        return self._result
