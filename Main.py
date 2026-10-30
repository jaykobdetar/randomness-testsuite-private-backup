"""Tk front end for the same validated scientific runner used by the CLI."""
import json
import queue
import threading
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

from BitInput import read_bits, require_distinct_output
from Suite import TEST_NAMES, run_suite
from Validation import validate_bits


class Main(ttk.Frame):
    def __init__(self, master=None):
        super().__init__(master, padding=16)
        self.pack(fill="both", expand=True)
        self.master.title("Randomness diagnostics - SP 800-22")
        self.master.geometry("1150x850")
        self.master.minsize(850, 700)
        self.events = queue.Queue()
        self.report = None
        self.busy = False
        self.source_mode = tk.StringVar(value="bits")
        self.literal = tk.StringVar()
        self.path = tk.StringVar()
        self.file_format = tk.StringVar(value="ascii")
        self.status = tk.StringVar(value="Choose input and tests. Parameters are fixed before evaluation.")
        self.selected = {key: tk.BooleanVar(value=True) for key in TEST_NAMES}
        self._build()

    def _build(self):
        ttk.Label(self, text="Randomness diagnostics", font=("TkDefaultFont", 20, "bold")).pack(anchor="w")
        ttk.Label(self, text="Tests against independent, equally probable bits | alpha = 0.01").pack(anchor="w", pady=(2, 12))
        inputs = ttk.LabelFrame(self, text="Input", padding=10)
        inputs.pack(fill="x")
        inputs.columnconfigure(1, weight=1)
        ttk.Radiobutton(inputs, text="Literal bits", variable=self.source_mode, value="bits").grid(row=0, column=0, sticky="w")
        ttk.Entry(inputs, textvariable=self.literal).grid(row=0, column=1, columnspan=2, sticky="ew", padx=8)
        ttk.Radiobutton(inputs, text="File", variable=self.source_mode, value="file").grid(row=1, column=0, sticky="w", pady=6)
        ttk.Entry(inputs, textvariable=self.path).grid(row=1, column=1, sticky="ew", padx=8)
        ttk.Button(inputs, text="Browse...", command=self._browse).grid(row=1, column=2)
        ttk.Label(inputs, text="File encoding").grid(row=2, column=0, sticky="w")
        ttk.Combobox(inputs, textvariable=self.file_format, values=("ascii", "bytes"), state="readonly", width=12).grid(row=2, column=1, sticky="w", padx=8)
        ttk.Label(inputs, text="ascii: 0/1 text with whitespace | bytes: packed bits, most significant bit first").grid(row=3, column=0, columnspan=3, sticky="w", pady=(6, 0))
        choices = ttk.LabelFrame(self, text="Tests - unsupported sample sizes are reported as not applicable", padding=8)
        choices.pack(fill="x", pady=10)
        for i, (key, label) in enumerate(TEST_NAMES.items()):
            ttk.Checkbutton(choices, text=label, variable=self.selected[key]).grid(row=i // 2, column=i % 2, sticky="w", padx=8, pady=1)
        choices.columnconfigure(0, weight=1)
        choices.columnconfigure(1, weight=1)
        actions = ttk.Frame(self)
        actions.pack(fill="x", pady=(0, 8))
        self.execute_button = ttk.Button(actions, text="Run selected tests", command=self.execute)
        self.execute_button.pack(side="left")
        self.save_button = ttk.Button(actions, text="Save JSON report...", command=self.save_result_to_file, state="disabled")
        self.save_button.pack(side="left", padx=8)
        ttk.Button(actions, text="Select all", command=lambda: self._select(True)).pack(side="left")
        ttk.Button(actions, text="Clear selection", command=lambda: self._select(False)).pack(side="left", padx=8)
        self.progress = ttk.Progressbar(actions, mode="determinate")
        self.progress.pack(side="right", fill="x", expand=True, padx=(12, 0))
        frame = ttk.Frame(self)
        frame.pack(fill="both", expand=True)
        self.tree = ttk.Treeview(frame, columns=("channel", "p", "decision"), selectmode="browse")
        for column, title in (("#0", "Test / applicability"), ("channel", "Channel"), ("p", "p-value"), ("decision", "Decision")):
            self.tree.heading(column, text=title)
        self.tree.column("#0", width=370)
        self.tree.column("channel", width=110, stretch=False)
        self.tree.column("p", width=135, stretch=False)
        self.tree.column("decision", width=140, stretch=False)
        scrollbar = ttk.Scrollbar(frame, command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set)
        scrollbar.pack(side="right", fill="y")
        self.tree.pack(fill="both", expand=True)
        self.tree.bind("<<TreeviewSelect>>", self._details)
        self.details = tk.Text(self, height=4, wrap="word", state="disabled")
        self.details.pack(fill="x", pady=6)
        ttk.Label(self, textvariable=self.status, wraplength=1000).pack(anchor="w")
        ttk.Label(self, text="Not rejected means no detected departure for that test; it does not prove randomness or physical entropy.", wraplength=1000).pack(anchor="w", pady=(6, 0))

    def _select(self, value):
        for selected in self.selected.values():
            selected.set(value)

    def _browse(self):
        path = filedialog.askopenfilename(title="Select data file")
        if path:
            self.path.set(path)
            self.source_mode.set("file")

    def execute(self):
        if self.busy:
            return
        tests = [key for key, selected in self.selected.items() if selected.get()]
        if not tests:
            messagebox.showerror("No tests selected", "Select at least one test.")
            return
        # Tk reads happen on the main thread. Changes to controls cannot relabel
        # the immutable input snapshot that is passed to the worker.
        request = (self.source_mode.get(), self.literal.get(), self.path.get(), self.file_format.get(), tests)
        self.busy = True
        self.report = None
        self.execute_button.configure(state="disabled")
        self.save_button.configure(state="disabled")
        self.tree.delete(*self.tree.get_children())
        self._set_details("")
        self.progress.configure(maximum=len(tests), value=0)
        self.status.set("Reading and validating the complete input...")
        threading.Thread(target=self._worker, args=(request,), daemon=True).start()
        self.after(50, self._poll)

    def _worker(self, request):
        try:
            mode, literal, path, input_format, tests = request
            if mode == "file":
                bits, source = read_bits(path, input_format)
            else:
                validate_bits(literal)
                bits, source = literal, {"format": "literal-bits"}
            report = run_suite(bits, tests, progress=lambda result: self.events.put(("result", result.to_dict())))
            report["source"] = source
            self.events.put(("complete", report))
        except Exception as exc:
            self.events.put(("error", f"{type(exc).__name__}: {exc}"))

    def _poll(self):
        try:
            while True:
                event, value = self.events.get_nowait()
                if event == "result":
                    self._add_result(value)
                    self.progress.step()
                    self.status.set(f"Evaluated {value['name']}: {value['status']}")
                elif event == "complete":
                    self.report = value
                    self._details()
                    self.busy = False
                    self.execute_button.configure(state="normal")
                    self.save_button.configure(state="normal")
                    self.progress.configure(value=self.progress["maximum"])
                    errors = sum(r["status"] == "error" for r in value["results"])
                    self.status.set(f"Complete: {value['input']['n_bits']:,} bits. {errors} computation errors. Select a result for parameters and applicability.")
                    return
                elif event == "error":
                    self.busy = False
                    self.execute_button.configure(state="normal")
                    self.status.set(value)
                    messagebox.showerror("Unable to complete tests", value)
                    return
        except queue.Empty:
            pass
        self.after(50, self._poll)

    def _add_result(self, result):
        key = result["test_id"]
        self.tree.insert("", "end", iid=key, text=result["name"], values=("", "", result["status"].replace("_", " ")), open=len(result["p_values"]) <= 2)
        for channel, p in result["p_values"].items():
            decision = "Reject H0" if result["decisions"][channel] == "reject" else "Not rejected"
            self.tree.insert(key, "end", text="", values=(channel, f"{p:.9g}", decision))

    def _set_details(self, text):
        self.details.configure(state="normal")
        self.details.delete("1.0", "end")
        self.details.insert("1.0", text)
        self.details.configure(state="disabled")

    def _details(self, _event=None):
        if not self.report or not self.tree.selection():
            return
        key = self.tree.selection()[0]
        key = self.tree.parent(key) or key
        result = next(r for r in self.report["results"] if r["test_id"] == key)
        self._set_details(f"{result['name']}: {result['reason'] or 'Evaluated using the supported profile.'}\n"
                          f"Parameters: {result['parameters']}\nBits used: {result['bits_used']:,}; discarded remainder: {result['discarded_bits']:,}. "
                          f"Input SHA-256: {self.report['input']['sha256_ascii_bits']}")

    def save_result_to_file(self):
        if self.report is None:
            return
        path = filedialog.asksaveasfilename(title="Save complete scientific report", defaultextension=".json", filetypes=[("JSON", "*.json")])
        if path:
            try:
                source_path = self.report.get("source", {}).get("path")
                if source_path is not None:
                    require_distinct_output(source_path, path)
                with open(path, "w", encoding="utf-8") as handle:
                    json.dump(self.report, handle, indent=2, allow_nan=False)
                    handle.write("\n")
                self.status.set(f"Saved complete report to {path}")
            except (OSError, ValueError) as exc:
                messagebox.showerror("Unable to save", str(exc))


if __name__ == "__main__":
    root = tk.Tk()
    Main(root)
    root.mainloop()
