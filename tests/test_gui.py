"""Exercise the actual Tk worker/event loop when a display is available."""
import json
import time

import pytest

tk = pytest.importorskip("tkinter")
from Main import Main
from Tools import Tools


@pytest.fixture
def app():
    try:
        root = tk.Tk()
    except tk.TclError as exc:
        pytest.skip(f"Display unavailable (use xvfb-run): {exc}")
    root.withdraw()
    widget = Main(root)
    yield widget
    root.destroy()


def wait_for_completion(app):
    deadline = time.monotonic() + 10
    while app.busy and time.monotonic() < deadline:
        app.master.update()
        time.sleep(0.01)
    assert not app.busy
    app.master.update()


def test_live_gui_uses_input_snapshot_and_saves_complete_report(app, monkeypatch, tmp_path):
    app._select(False)
    app.selected["frequency"].set(True)
    app.selected["runs"].set(True)
    app.selected["spectral"].set(True)
    app.literal.set("01" * 50)
    app.execute()
    app.literal.set("0" * 100)
    app._select(False)
    wait_for_completion(app)
    results = {r["test_id"]: r for r in app.report["results"]}
    assert set(results) == {"frequency", "runs", "spectral"}
    assert results["frequency"]["p_values"] == {"p": 1.0}
    assert results["spectral"]["status"] == "not_applicable"
    app.tree.selection_set("spectral")
    app._details()
    assert "1,000,000" in app.details.get("1.0", "end")
    output = tmp_path / "report.json"
    monkeypatch.setattr("Main.filedialog.asksaveasfilename", lambda **_: str(output))
    app.save_result_to_file()
    saved = json.loads(output.read_text())
    assert saved == app.report
    assert saved["input"]["n_bits"] == 100


def test_invalid_gui_input_clears_previous_report_and_recovers(app, monkeypatch):
    errors = []
    monkeypatch.setattr("Main.messagebox.showerror", lambda *args: errors.append(args))
    app._select(False)
    app.selected["frequency"].set(True)
    app.literal.set("01" * 50)
    app.execute()
    wait_for_completion(app)
    assert app.report
    app.literal.set("010x")
    app.execute()
    wait_for_completion(app)
    assert app.report is None
    assert errors and "ASCII" in errors[0][1]
    assert app.save_button.instate(["disabled"])
    assert not app.execute_button.instate(["disabled"])


def test_unicode_encoding_is_utf8_bytes_not_variable_width_codepoints():
    assert Tools.string_to_binary("é") == "1100001110101001"
    assert Tools.string_to_binary("A") == "01000001"
    assert Tools.bytes_to_binary(bytes([0, 128, 1, 255])) == "00000000100000000000000111111111"
