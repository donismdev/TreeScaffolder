import os
import ctypes
import tkinter as tk
from tkinter import ttk
from tkinter import scrolledtext

import merge_file


# =================================================================
# [SECTION 0] USER SETTINGS
# =================================================================

WIN_WIDTH = 1200
WIN_HEIGHT = 800
APP_ID = "donism.grep.merger.v2"


try:
	ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(APP_ID)
except Exception:
	pass


# =================================================================
# [SECTION 1] GUI APP
# =================================================================

class MergeGuiApp:
	def __init__(self, root):
		self.root = root
		self.root.title("UE5 FIND / GREP / MERGE TOOL")
		self.root.geometry(f"{WIN_WIDTH}x{WIN_HEIGHT}")
		self.build_layout()

	def build_layout(self):
		button_frame = ttk.Frame(self.root)
		button_frame.pack(fill=tk.X, padx=10, pady=10)

		ttk.Button(
			button_frame,
			text="1 파일찾기",
			command=self.run_file_find
		).pack(side=tk.LEFT, expand=True, fill=tk.X, padx=(0, 2))

		ttk.Button(
			button_frame,
			text="2 그랩 텍스트",
			command=self.run_text_grep
		).pack(side=tk.LEFT, expand=True, fill=tk.X, padx=2)

		ttk.Button(
			button_frame,
			text="3 파일 병합",
			command=self.run_merge
		).pack(side=tk.LEFT, expand=True, fill=tk.X, padx=2)

		ttk.Button(
			button_frame,
			text="결과 복사",
			command=self.copy_clipboard
		).pack(side=tk.LEFT, expand=True, fill=tk.X, padx=(2, 0))

		paned = ttk.PanedWindow(self.root, orient=tk.HORIZONTAL)
		paned.pack(fill=tk.BOTH, expand=True, padx=10, pady=(0, 10))

		left_frame = ttk.Frame(paned)
		paned.add(left_frame, weight=1)

		self.tabs = ttk.Notebook(left_frame)

		self.tab_raw = ttk.Frame(self.tabs)
		self.tab_tree = ttk.Frame(self.tabs)

		self.tabs.add(self.tab_raw, text=" Input ")
		self.tabs.add(self.tab_tree, text=" Tree View ")
		self.tabs.pack(fill=tk.BOTH, expand=True)

		self.raw_text = scrolledtext.ScrolledText(
			self.tab_raw,
			font=("Consolas", 10),
			tabs=("0.5c",)
		)
		self.raw_text.pack(fill=tk.BOTH, expand=True)

		self.tree_text = scrolledtext.ScrolledText(
			self.tab_tree,
			font=("Consolas", 10),
			tabs=("0.5c",)
		)
		self.tree_text.pack(fill=tk.BOTH, expand=True)

		right_frame = ttk.Frame(paned)
		paned.add(right_frame, weight=1)

		self.output_text = scrolledtext.ScrolledText(
			right_frame,
			font=("Consolas", 10),
			bg="#fafafa",
			tabs=("0.5c",)
		)
		self.output_text.pack(fill=tk.BOTH, expand=True)

	def clear_output(self):
		self.output_text.config(fg="black")
		self.output_text.delete("1.0", tk.END)

	def get_raw_input(self):
		return self.raw_text.get("1.0", tk.END).strip()

	def get_tree_input(self):
		return self.tree_text.get("1.0", tk.END).strip()

	def print_output(self, text):
		self.output_text.insert(tk.END, text)
		self.output_text.see("1.0")

	def run_file_find(self):
		self.clear_output()

		raw_value = self.get_raw_input()
		if raw_value == "":
			return

		result = merge_file.FileFinder.search(raw_value)
		self.print_output(result)

	def run_text_grep(self):
		self.clear_output()

		raw_value = self.get_raw_input()
		if raw_value == "":
			return

		result = merge_file.TextGrep.search(raw_value)
		self.print_output(result)

	def run_merge(self):
		self.clear_output()

		raw_value = self.get_raw_input()
		tree_value = self.get_tree_input()

		if raw_value == "":
			return

		success, result = merge_file.FileMerger.run(raw_value, tree_value)

		if success == True:
			if os.path.exists("output.txt") == True:
				with open("output.txt", "r", encoding="utf-8") as file:
					self.print_output(file.read())
			return

		self.output_text.config(fg="red")
		self.print_output("--- MERGE FAILED ---\n\n")

		for error in result:
			self.print_output(f"✖ {error}\n")

	def copy_clipboard(self):
		content = self.output_text.get("1.0", tk.END).strip()

		if content == "":
			return

		self.root.clipboard_clear()
		self.root.clipboard_append(content)

		try:
			ctypes.windll.user32.MessageBeep(0)
		except Exception:
			pass

		self.show_popup("Success", "복사되었습니다.", 2000)

	def show_popup(self, title, message, timeout):
		popup = tk.Toplevel(self.root)
		popup.title(title)
		popup.attributes("-topmost", True)

		width = 300
		height = 80

		x = self.root.winfo_x() + (WIN_WIDTH // 2) - (width // 2)
		y = self.root.winfo_y() + (WIN_HEIGHT // 2) - (height // 2)

		popup.geometry(f"{width}x{height}+{x}+{y}")

		ttk.Label(
			popup,
			text=message,
			padding=20
		).pack()

		popup.bind("<Button-1>", lambda event: popup.destroy())
		popup.after(timeout, popup.destroy)


# =================================================================
# [SECTION 2] ENTRY POINT
# =================================================================

if __name__ == "__main__":
	root = tk.Tk()
	app = MergeGuiApp(root)
	root.mainloop()
