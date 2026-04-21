"""
MULTIREMOTE 설정 패널

각 MULTIREMOTE 그룹(MRT)의 구동 순서를 정의합니다.
- MRT 그룹 목록 (좌측 상단)
- 해당 MRT의 Model/Pattern 순서 목록 (우측)
- 항목 추가/수정/삭제

OTD 포맷:
  501=MRT,001,B6-250916-T      # MRT 번호, 이름
  601=MRT01,8,1,0              # 순서, Model번호, Pattern번호, Time
  602=MRT02,1,1,0
"""

import tkinter as tk
from tkinter import ttk, messagebox, simpledialog


class MultiRemotePanel(tk.Frame):
    """
    MULTIREMOTE 설정 탭 패널

    외부에서 model_store를 주입받아 사용.
    model_store.multiremote_groups 를 읽고 편집.
    """

    def __init__(self, parent, model_store):
        super().__init__(parent, bg='#f0f0f0')
        self.model_store = model_store
        self._current_mrt_idx = -1
        self._setup_ui()
        self.model_store.add_listener(self._refresh_mrt_list)

    # ──────────────────────────────────────────────────────────
    def _setup_ui(self):
        # ── 상단: MRT 그룹 관리 버튼 ─────────────────────────
        top_btn = tk.Frame(self, bg='#f0f0f0')
        top_btn.pack(side=tk.TOP, fill=tk.X, padx=5, pady=3)

        tk.Label(top_btn, text="MULTIREMOTE 설정",
                 font=('Arial', 11, 'bold'), bg='#f0f0f0').pack(side=tk.LEFT)

        for text, cmd, color in [
            ("MRT 추가", self._on_add_mrt,    '#4CAF50'),
            ("MRT 삭제", self._on_delete_mrt, '#F44336'),
        ]:
            tk.Button(top_btn, text=text, command=cmd,
                      bg=color, fg='black', font=('Arial', 9),
                      relief=tk.RAISED, borderwidth=2, width=9).pack(
                side=tk.RIGHT, padx=2)

        # ── 좌우 분할 ────────────────────────────────────────
        pw = ttk.PanedWindow(self, orient=tk.HORIZONTAL)
        pw.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        # ── 좌: MRT 목록 ─────────────────────────────────────
        left_frame = tk.LabelFrame(pw, text="MRT 목록",
                                   font=('Arial', 10, 'bold'),
                                   bg='#f0f0f0')
        self._mrt_listbox = tk.Listbox(left_frame, font=('Consolas', 9),
                                       bg='white', selectbackground='#2980b9',
                                       selectforeground='white')
        vsb1 = ttk.Scrollbar(left_frame, command=self._mrt_listbox.yview)
        self._mrt_listbox.configure(yscrollcommand=vsb1.set)
        self._mrt_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        vsb1.pack(side=tk.RIGHT, fill=tk.Y)
        self._mrt_listbox.bind('<<ListboxSelect>>', self._on_mrt_select)
        pw.add(left_frame, weight=1)

        # ── 우: MRT 항목 편집 ────────────────────────────────
        right_frame = tk.Frame(pw, bg='#f0f0f0')
        pw.add(right_frame, weight=3)

        # 이름 편집 행
        name_row = tk.Frame(right_frame, bg='#f0f0f0')
        name_row.pack(side=tk.TOP, fill=tk.X, padx=4, pady=4)
        tk.Label(name_row, text="MRT 이름:", font=('Arial', 9),
                 bg='#f0f0f0').pack(side=tk.LEFT)
        self._mrt_name_var = tk.StringVar()
        self._mrt_name_entry = tk.Entry(name_row, textvariable=self._mrt_name_var,
                                        width=25, font=('Arial', 9))
        self._mrt_name_entry.pack(side=tk.LEFT, padx=4)
        tk.Button(name_row, text="이름 저장", command=self._on_save_name,
                  bg='#FF9800', fg='black', font=('Arial', 9),
                  relief=tk.RAISED, borderwidth=2).pack(side=tk.LEFT)

        # 항목 버튼
        entry_btn = tk.Frame(right_frame, bg='#f0f0f0')
        entry_btn.pack(side=tk.TOP, fill=tk.X, padx=4, pady=2)
        for text, cmd, color in [
            ("항목 추가", self._on_add_entry,    '#4CAF50'),
            ("항목 수정", self._on_edit_entry,   '#FF9800'),
            ("항목 삭제", self._on_delete_entry, '#F44336'),
            ("↑ 위로",   self._on_move_up,      '#607D8B'),
            ("↓ 아래로", self._on_move_down,     '#607D8B'),
        ]:
            tk.Button(entry_btn, text=text, command=cmd,
                      bg=color, fg='black', font=('Arial', 8),
                      relief=tk.RAISED, borderwidth=2, width=8).pack(
                side=tk.LEFT, padx=2)

        # 항목 테이블
        self._entry_tree = ttk.Treeview(
            right_frame,
            columns=('seq', 'model', 'ptn', 'time'),
            show='headings', height=15
        )
        for col, label, w in [
            ('seq',   '순서',       60),
            ('model', 'Model 번호', 100),
            ('ptn',   'Pattern No', 100),
            ('time',  'Time',        80),
        ]:
            self._entry_tree.heading(col, text=label)
            self._entry_tree.column(col, width=w, anchor='center')

        vsb2 = ttk.Scrollbar(right_frame, command=self._entry_tree.yview)
        self._entry_tree.configure(yscrollcommand=vsb2.set)
        self._entry_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(4, 0))
        vsb2.pack(side=tk.LEFT, fill=tk.Y, padx=(0, 4))

        # 모델 정보 참조 표시 (읽기전용)
        info_frame = tk.LabelFrame(right_frame, text="현재 로드된 모델",
                                   font=('Arial', 9), bg='#f0f0f0')
        info_frame.pack(side=tk.BOTTOM, fill=tk.X, padx=4, pady=4)
        self._model_info_text = tk.Text(info_frame, height=6, width=40,
                                        font=('Consolas', 8), state='disabled',
                                        bg='#fafafa')
        self._model_info_text.pack(fill=tk.X)

    # ──────────────────────────────────────────────────────────
    # MRT 목록
    # ──────────────────────────────────────────────────────────
    def _refresh_mrt_list(self):
        self._mrt_listbox.delete(0, tk.END)
        for g in self.model_store.multiremote_groups:
            self._mrt_listbox.insert(tk.END, f"[{g.mrt_no}] {g.name}")
        self._refresh_model_info()

    def _on_mrt_select(self, event=None):
        sel = self._mrt_listbox.curselection()
        if not sel:
            return
        self._current_mrt_idx = sel[0]
        grp = self.model_store.multiremote_groups[self._current_mrt_idx]
        self._mrt_name_var.set(grp.name)
        self._refresh_entry_tree(grp)

    def _refresh_entry_tree(self, grp):
        for row in self._entry_tree.get_children():
            self._entry_tree.delete(row)
        for e in grp.entries:
            self._entry_tree.insert('', 'end',
                values=(f"MRT{e.seq:02d}", e.model_num, e.ptn_no, e.time))

    def _refresh_model_info(self):
        self._model_info_text.configure(state='normal')
        self._model_info_text.delete('1.0', tk.END)
        for m in self.model_store.models:
            ptns = ", ".join(f"PTN{p.get('ptn_no','?'):02d}" if isinstance(p, dict)
                             else str(p) for p in m.patterns[:4])
            self._model_info_text.insert(
                tk.END,
                f"[{m.model_num}] {m.name} | {m.frequency_hz:.0f}Hz | 패턴: {ptns}\n"
            )
        self._model_info_text.configure(state='disabled')

    # ──────────────────────────────────────────────────────────
    # MRT 그룹 추가/삭제
    # ──────────────────────────────────────────────────────────
    def _on_add_mrt(self):
        name = simpledialog.askstring("MRT 추가", "MRT 이름 입력:")
        if not name:
            return
        from model_store import MultiRemoteGroup
        next_no = f"{len(self.model_store.multiremote_groups)+1:03d}"
        grp = MultiRemoteGroup(mrt_no=next_no, name=name)
        self.model_store.multiremote_groups.append(grp)
        self._refresh_mrt_list()
        self._mrt_listbox.selection_set(len(self.model_store.multiremote_groups) - 1)
        self._on_mrt_select()

    def _on_delete_mrt(self):
        if self._current_mrt_idx < 0:
            messagebox.showwarning("선택 없음", "삭제할 MRT를 선택하세요.")
            return
        if messagebox.askyesno("확인", "선택된 MRT를 삭제하시겠습니까?"):
            del self.model_store.multiremote_groups[self._current_mrt_idx]
            self._current_mrt_idx = -1
            self._refresh_mrt_list()

    def _on_save_name(self):
        if self._current_mrt_idx < 0:
            return
        self.model_store.multiremote_groups[self._current_mrt_idx].name = \
            self._mrt_name_var.get().strip()
        self._refresh_mrt_list()

    # ──────────────────────────────────────────────────────────
    # 항목 추가/수정/삭제/이동
    # ──────────────────────────────────────────────────────────
    def _current_group(self):
        if self._current_mrt_idx < 0 or \
           self._current_mrt_idx >= len(self.model_store.multiremote_groups):
            return None
        return self.model_store.multiremote_groups[self._current_mrt_idx]

    def _get_selected_entry_idx(self):
        sel = self._entry_tree.selection()
        if not sel:
            return -1
        return self._entry_tree.index(sel[0])

    def _on_add_entry(self):
        grp = self._current_group()
        if grp is None:
            messagebox.showwarning("경고", "먼저 MRT를 선택하세요.")
            return
        dlg = MrtEntryDialog(self, grp, None,
                             self.model_store.models)
        result = dlg.get_result()
        if result:
            from model_store import MrtEntry
            seq = len(grp.entries) + 1
            grp.entries.append(MrtEntry(seq=seq, **result))
            self._refresh_entry_tree(grp)

    def _on_edit_entry(self):
        grp = self._current_group()
        idx = self._get_selected_entry_idx()
        if grp is None or idx < 0:
            messagebox.showwarning("선택 없음", "수정할 항목을 선택하세요.")
            return
        entry = grp.entries[idx]
        dlg = MrtEntryDialog(self, grp, entry, self.model_store.models)
        result = dlg.get_result()
        if result:
            entry.model_num = result['model_num']
            entry.ptn_no   = result['ptn_no']
            entry.time     = result['time']
            self._refresh_entry_tree(grp)

    def _on_delete_entry(self):
        grp = self._current_group()
        idx = self._get_selected_entry_idx()
        if grp is None or idx < 0:
            return
        del grp.entries[idx]
        # 순서 재정렬
        for i, e in enumerate(grp.entries, 1):
            e.seq = i
        self._refresh_entry_tree(grp)

    def _on_move_up(self):
        grp = self._current_group()
        idx = self._get_selected_entry_idx()
        if grp is None or idx <= 0:
            return
        grp.entries[idx], grp.entries[idx-1] = \
            grp.entries[idx-1], grp.entries[idx]
        for i, e in enumerate(grp.entries, 1):
            e.seq = i
        self._refresh_entry_tree(grp)

    def _on_move_down(self):
        grp = self._current_group()
        idx = self._get_selected_entry_idx()
        if grp is None or idx < 0 or idx >= len(grp.entries) - 1:
            return
        grp.entries[idx], grp.entries[idx+1] = \
            grp.entries[idx+1], grp.entries[idx]
        for i, e in enumerate(grp.entries, 1):
            e.seq = i
        self._refresh_entry_tree(grp)


# ────────────────────────────────────────────────────────────────
# MRT 항목 편집 다이얼로그
# ────────────────────────────────────────────────────────────────

class MrtEntryDialog(tk.Toplevel):
    def __init__(self, parent, mrt_group, entry=None, models=None):
        super().__init__(parent)
        self.title("MRT 항목 편집")
        self.resizable(False, False)
        self._result = None
        self._models = models or []

        frm = tk.Frame(self, padx=15, pady=12)
        frm.pack()

        # Model 선택
        tk.Label(frm, text="Model:", font=('Arial', 10)).grid(
            row=0, column=0, sticky='e', pady=4, padx=4)
        model_opts = [f"[{m.model_num}] {m.name}" for m in self._models] or [""]
        self._model_var = tk.StringVar()
        self._model_combo = ttk.Combobox(frm, textvariable=self._model_var,
                                          values=model_opts, width=25, state='readonly')
        self._model_combo.grid(row=0, column=1, pady=4, padx=4)
        if model_opts:
            self._model_combo.current(0)
        self._model_combo.bind('<<ComboboxSelected>>', self._on_model_or_ptn_changed)

        # Pattern No
        tk.Label(frm, text="Pattern No:", font=('Arial', 10)).grid(
            row=1, column=0, sticky='e', pady=4, padx=4)
        self._ptn_var = tk.IntVar(value=1)
        ptn_spinbox = tk.Spinbox(frm, from_=1, to=99, textvariable=self._ptn_var,
                                  width=8, command=self._on_model_or_ptn_changed)
        ptn_spinbox.grid(row=1, column=1, sticky='w', pady=4, padx=4)
        ptn_spinbox.bind('<KeyRelease>', self._on_model_or_ptn_changed)

        # 패턴 이름 표시 라벨
        tk.Label(frm, text="패턴 이름:", font=('Arial', 10)).grid(
            row=2, column=0, sticky='e', pady=4, padx=4)
        self._ptn_name_var = tk.StringVar(value="—")
        tk.Label(frm, textvariable=self._ptn_name_var,
                 font=('Arial', 10, 'bold'), fg='#1a5fa8',
                 width=20, anchor='w').grid(row=2, column=1, sticky='w', pady=4, padx=4)

        # Time
        tk.Label(frm, text="Time:", font=('Arial', 10)).grid(
            row=3, column=0, sticky='e', pady=4, padx=4)
        self._time_var = tk.IntVar(value=0)
        tk.Spinbox(frm, from_=0, to=99999, textvariable=self._time_var,
                   width=8).grid(row=3, column=1, sticky='w', pady=4, padx=4)

        # 기존 값 로드
        if entry:
            for i, m in enumerate(self._models):
                if m.model_num == entry.model_num:
                    self._model_combo.current(i)
                    break
            self._ptn_var.set(entry.ptn_no)
            self._time_var.set(entry.time)

        self._update_pattern_name()

        # 버튼
        tk.Button(frm, text="확인", command=self._ok,
                  bg='#4CAF50', fg='black', font=('Arial', 10, 'bold'),
                  width=10).grid(row=4, column=0, pady=10)
        tk.Button(frm, text="취소", command=self.destroy,
                  bg='#9E9E9E', fg='black', font=('Arial', 10, 'bold'),
                  width=10).grid(row=4, column=1, pady=10)

        self.transient(parent)
        self.grab_set()

    def _on_model_or_ptn_changed(self, event=None):
        self._update_pattern_name()

    def _update_pattern_name(self):
        """선택된 Model과 Pattern No에 해당하는 패턴 이름을 표시"""
        model_idx = self._model_combo.current()
        if model_idx < 0 or model_idx >= len(self._models):
            self._ptn_name_var.set("—")
            return
        model = self._models[model_idx]
        try:
            ptn_no = int(self._ptn_var.get())
        except (ValueError, tk.TclError):
            self._ptn_name_var.set("—")
            return

        for p in model.patterns:
            p_no = p.get('ptn_no', 0) if isinstance(p, dict) else 0
            if int(p_no) == ptn_no:
                name = p.get('name', '—') if isinstance(p, dict) else '—'
                self._ptn_name_var.set(name or '—')
                return
        self._ptn_name_var.set("(없음)")

    def _ok(self):
        idx = self._model_combo.current()
        if idx < 0 or idx >= len(self._models):
            tk.messagebox.showwarning("경고", "모델을 선택하세요.")
            return
        model_num = self._models[idx].model_num
        self._result = {
            'model_num': model_num,
            'ptn_no': self._ptn_var.get(),
            'time': self._time_var.get(),
        }
        self.destroy()

    def get_result(self):
        self.wait_window()
        return self._result
