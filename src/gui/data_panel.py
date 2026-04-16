import customtkinter as ctk
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from typing import Callable
from src.core import database
from src.utils.excel_export import export_to_excel


class DataPanel(ctk.CTkFrame):
    def __init__(self, parent, **kwargs):
        super().__init__(parent, **kwargs)
        self._build()

    def _build(self):
        title = ctk.CTkLabel(self, text="📊 데이터 관리",
                              font=ctk.CTkFont(size=18, weight="bold"))
        title.pack(pady=(16, 4), padx=20, anchor="w")

        # ── Top button row ─────────────────────────────────────────────────
        btn_row = ctk.CTkFrame(self, fg_color="transparent")
        btn_row.pack(fill="x", padx=20, pady=(0, 8))

        ctk.CTkButton(btn_row, text="새로고침", width=100, command=self.refresh,
                       fg_color="#3498DB", hover_color="#2980B9").pack(side="left", padx=(0, 8))
        ctk.CTkButton(btn_row, text="엑셀 내보내기", width=120, command=self._export,
                       fg_color="#27AE60", hover_color="#219A52").pack(side="left", padx=(0, 8))
        ctk.CTkButton(btn_row, text="이름 설정", width=100, command=self._set_name,
                       fg_color="#E67E22", hover_color="#CA6F1E").pack(side="left")

        # ── Sessions treeview ──────────────────────────────────────────────
        ctk.CTkLabel(self, text="세션 목록", font=ctk.CTkFont(size=13, weight="bold"),
                     text_color="#A0C4E4").pack(anchor="w", padx=20, pady=(4, 2))

        tree_frame = ctk.CTkFrame(self, fg_color="#1A1A1A")
        tree_frame.pack(fill="both", expand=False, padx=20)

        style = ttk.Style()
        style.theme_use("clam")
        style.configure("Dark.Treeview",
                         background="#1E1E1E", foreground="white",
                         fieldbackground="#1E1E1E", rowheight=24,
                         borderwidth=0)
        style.configure("Dark.Treeview.Heading",
                         background="#2B2B2B", foreground="#A0C4E4",
                         borderwidth=0)
        style.map("Dark.Treeview", background=[("selected", "#2C5F8A")])

        cols = ("session_id", "participant_name", "created_at", "utterance_count", "total_duration")
        self.session_tree = ttk.Treeview(tree_frame, columns=cols, show="headings",
                                          height=7, style="Dark.Treeview")
        headers = {"session_id": ("ID", 50), "participant_name": ("참여자", 120),
                   "created_at": ("생성 시각", 160), "utterance_count": ("발화수", 60),
                   "total_duration": ("총 시간(초)", 90)}
        for col, (text, width) in headers.items():
            self.session_tree.heading(col, text=text)
            self.session_tree.column(col, width=width, anchor="center")
        self.session_tree.column("participant_name", anchor="w")
        self.session_tree.column("created_at", anchor="w")

        sb1 = ttk.Scrollbar(tree_frame, orient="vertical", command=self.session_tree.yview)
        self.session_tree.configure(yscrollcommand=sb1.set)
        self.session_tree.pack(side="left", fill="both", expand=True)
        sb1.pack(side="right", fill="y")
        self.session_tree.bind("<<TreeviewSelect>>", self._on_session_select)

        # ── Utterances treeview ────────────────────────────────────────────
        ctk.CTkLabel(self, text="발화 상세 (세션 선택 시 표시)",
                     font=ctk.CTkFont(size=13, weight="bold"),
                     text_color="#A0C4E4").pack(anchor="w", padx=20, pady=(10, 2))

        tree_frame2 = ctk.CTkFrame(self, fg_color="#1A1A1A")
        tree_frame2.pack(fill="both", expand=True, padx=20, pady=(0, 12))

        ucols = ("idx", "utterance_text", "prompt_text", "word_count", "duration", "spoken_at")
        self.utt_tree = ttk.Treeview(tree_frame2, columns=ucols, show="headings",
                                      height=8, style="Dark.Treeview")
        uheaders = {"idx": ("#", 40), "utterance_text": ("발화 원문", 180),
                    "prompt_text": ("프롬프트", 260), "word_count": ("단어수", 60),
                    "duration": ("시간(초)", 70), "spoken_at": ("발화 시각", 150)}
        for col, (text, width) in uheaders.items():
            self.utt_tree.heading(col, text=text)
            self.utt_tree.column(col, width=width, anchor="center" if col in ("idx","word_count","duration") else "w")

        sb2 = ttk.Scrollbar(tree_frame2, orient="vertical", command=self.utt_tree.yview)
        sb2h = ttk.Scrollbar(tree_frame2, orient="horizontal", command=self.utt_tree.xview)
        self.utt_tree.configure(yscrollcommand=sb2.set, xscrollcommand=sb2h.set)
        self.utt_tree.pack(side="left", fill="both", expand=True)
        sb2.pack(side="right", fill="y")

        self.refresh()

    def refresh(self):
        for row in self.session_tree.get_children():
            self.session_tree.delete(row)
        sessions = database.get_all_sessions()
        for s in sessions:
            self.session_tree.insert("", "end", iid=str(s["session_id"]),
                                      values=(s["session_id"], s["participant_name"] or "",
                                              s["created_at"][:19],
                                              s["utterance_count"],
                                              round(s["total_duration"], 1)))

    def _on_session_select(self, event):
        sel = self.session_tree.selection()
        if not sel:
            return
        session_id = int(sel[0])
        for row in self.utt_tree.get_children():
            self.utt_tree.delete(row)
        utterances = database.get_utterances_by_session(session_id)
        for u in utterances:
            self.utt_tree.insert("", "end", values=(
                u["utterance_index"], u["utterance_text"], u["prompt_text"],
                u["prompt_word_count"], round(u["duration_sec"], 1),
                u["spoken_at"][:19]
            ))

    def _set_name(self):
        sel = self.session_tree.selection()
        if not sel:
            messagebox.showwarning("선택 필요", "세션을 먼저 선택해 주세요.")
            return
        session_id = int(sel[0])
        dialog = NameDialog(self, session_id)
        self.wait_window(dialog)
        self.refresh()

    def _export(self):
        sessions_raw = database.get_all_sessions()
        sessions = [dict(s) for s in sessions_raw]
        utterances_by_session = {}
        for s in sessions:
            utts = database.get_utterances_by_session(s["session_id"])
            utterances_by_session[s["session_id"]] = [dict(u) for u in utts]

        path = filedialog.asksaveasfilename(
            defaultextension=".xlsx",
            filetypes=[("Excel 파일", "*.xlsx")],
            title="엑셀 저장 위치 선택"
        )
        if not path:
            return
        try:
            out = export_to_excel(sessions, utterances_by_session, path)
            messagebox.showinfo("완료", f"저장 완료:\n{out}")
        except Exception as e:
            messagebox.showerror("오류", str(e))


class NameDialog(ctk.CTkToplevel):
    def __init__(self, parent, session_id: int):
        super().__init__(parent)
        self.session_id = session_id
        self.title("참여자 이름 설정")
        self.geometry("320x150")
        self.resizable(False, False)
        self.grab_set()

        ctk.CTkLabel(self, text=f"세션 #{session_id} 참여자 이름",
                     font=ctk.CTkFont(size=13)).pack(pady=(20, 8))
        self.entry = ctk.CTkEntry(self, width=250, placeholder_text="이름 입력")
        self.entry.pack(pady=(0, 12))
        ctk.CTkButton(self, text="저장", command=self._save).pack()

    def _save(self):
        name = self.entry.get().strip()
        if name:
            database.update_participant_name(self.session_id, name)
        self.destroy()
