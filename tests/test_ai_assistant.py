"""
test_ai_assistant.py
====================
Pytests for ``ai.ai_assistant`` with high branch coverage.

:date: 04/25/2026
:author: Shane del Villar
:class: CMSC 420
"""
from __future__ import annotations

import builtins
import json
import os
import sys
import types
from types import SimpleNamespace
from unittest.mock import MagicMock, mock_open, patch

import pytest
from PyQt6.QtWidgets import QApplication

import ai.ai_assistant as aa


@pytest.fixture(scope="module")
def qt_app():
    app = QApplication.instance()
    if app is None:
        app = QApplication(sys.argv)
    return app


def _ok_json(msg: str, **extra: object) -> str:
    return json.dumps({"ok": True, "message": msg, **extra})


def test_get_tool_schemas_non_empty():
    schemas = aa.get_tool_schemas()
    assert len(schemas) > 5
    names = {s["function"]["name"] for s in schemas if s.get("type") == "function"}
    assert "get_config_json" in names
    assert "open_native_gui" in names


def test_default_api_key_in_code_takes_precedence(monkeypatch):
    monkeypatch.setattr(aa, "OPENAI_API_KEY_IN_CODE", "  inline  ")
    monkeypatch.setenv("OPENAI_API_KEY", "env-ignored")
    assert aa.default_api_key() == "inline"


def test_default_api_key_from_file_on_disk(tmp_path, monkeypatch):
    monkeypatch.setattr(aa, "OPENAI_API_KEY_IN_CODE", "")
    (tmp_path / "config").mkdir()
    (tmp_path / "config" / "openai_key.txt").write_text(
        "  # c\n  sk-actual-key-from-file  \n", encoding="utf-8"
    )
    with patch.object(aa, "__file__", str(tmp_path / "ai" / "ai_assistant.py")):
        assert aa.default_api_key() == "sk-actual-key-from-file"


def test_default_api_key_skips_comments_and_placeholder_lines(tmp_path, monkeypatch):
    monkeypatch.setattr(aa, "OPENAI_API_KEY_IN_CODE", "")
    (tmp_path / "config").mkdir()
    (tmp_path / "config" / "openai_key.txt").write_text(
        "#c\n\nsk-your-key\nreal-key-abc\n", encoding="utf-8"
    )
    with patch.object(aa, "__file__", str(tmp_path / "ai" / "ai_assistant.py")):
        assert aa.default_api_key() == "real-key-abc"


def test_default_api_key_file_oserror_falls_back_to_env(tmp_path, monkeypatch):
    monkeypatch.setattr(aa, "OPENAI_API_KEY_IN_CODE", "")
    (tmp_path / "config").mkdir()
    (tmp_path / "config" / "openai_key.txt").write_text("x", encoding="utf-8")
    monkeypatch.setenv("OPENAI_API_KEY", "  from-env  ")
    with patch.object(aa, "__file__", str(tmp_path / "ai" / "ai_assistant.py")):
        with patch("builtins.open", side_effect=OSError("nope")):
            assert aa.default_api_key() == "from-env"


def test_default_api_key_env_when_no_file(monkeypatch):
    monkeypatch.setattr(aa, "OPENAI_API_KEY_IN_CODE", "")
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    with patch("os.path.isfile", return_value=False):
        assert aa.default_api_key() == ""


def test_ensure_config_block_builds_structures():
    mw = SimpleNamespace(config_mgr=SimpleNamespace(data=None))
    cfg = aa._ensure_config_block(mw)
    for k in ("rooms", "labs", "courses", "faculty"):
        assert isinstance(cfg[k], list)


def test_ensure_config_block_fixes_bad_config_type():
    mw = SimpleNamespace(config_mgr=SimpleNamespace(data={"config": "bad"}))
    cfg = aa._ensure_config_block(mw)
    assert isinstance(cfg, dict)
    assert isinstance(mw.config_mgr.data["config"], dict)


@patch("ai.ai_assistant.json.dump")
@patch("builtins.open", new_callable=mock_open)
def test_write_config_silent_pushes_and_writes(_open, dump):
    mw = SimpleNamespace(
        config_mgr=SimpleNamespace(filepath="/x/cfg.json", data={"a": 1}),
        assistant_push_config_undo_snapshot=MagicMock(),
    )
    aa._write_config_silent(mw)
    mw.assistant_push_config_undo_snapshot.assert_called_once()
    dump.assert_called_once()


@patch("builtins.open", new_callable=mock_open)
@patch("ai.ai_assistant.json.dump")
def test_write_config_silent_no_snapshot_attr(_dump, _open):
    mw = SimpleNamespace(config_mgr=SimpleNamespace(filepath="/x/cfg.json", data={}))
    aa._write_config_silent(mw)


def test_faculty_display_name():
    assert aa._faculty_display_name({"name": "N"}) == "N"
    assert aa._faculty_display_name("plain") == "plain"


def test_normalize_weekday_for_editor():
    dmap = {"Monday": "Monday", "Tuesday": "Tuesday"}
    rev = {"MON": "Monday", "TUE": "Tuesday"}
    assert aa._normalize_weekday_for_editor("MON", dmap, rev) == "Monday"
    assert aa._normalize_weekday_for_editor("Monday", dmap, rev) == "Monday"
    assert aa._normalize_weekday_for_editor("monday", dmap, rev) == "Monday"
    assert aa._normalize_weekday_for_editor("", dmap, rev) is None
    assert aa._normalize_weekday_for_editor("ZZZ", dmap, rev) is None


def test_parse_hhmm():
    assert aa._parse_hhmm("09:30") is True
    assert aa._parse_hhmm("24:00") is False
    assert aa._parse_hhmm("bad") is False
    assert aa._parse_hhmm("9:ab") is False


def test_normalize_meeting_entries():
    dmap = {"Monday": "Monday"}
    rev = {"MON": "Monday"}
    ok, err = aa._normalize_meeting_entries(
        [{"day": "MON", "duration": 50, "lab": True}], dmap, rev
    )
    assert err is None and ok[0]["day"] == "Monday" and ok[0]["lab"] is True
    assert aa._normalize_meeting_entries([123], dmap, rev)[1] == "Each meeting must be an object."
    assert "Invalid weekday" in aa._normalize_meeting_entries([{"day": "X", "duration": 1}], dmap, rev)[1]
    assert aa._normalize_meeting_entries([], dmap, rev)[1] == "At least one meeting is required."
    assert aa._normalize_meeting_entries([{"day": "MON", "duration": "bad"}], dmap, rev)[1] == "duration must be an integer."
    assert aa._normalize_meeting_entries([{"day": "MON", "duration": 0}], dmap, rev)[1] == "duration must be >= 1."


def test_faculty_match_index():
    fac = [{"name": "Abe"}, "Bob", 3]
    assert aa._faculty_match_index(fac, "abe") == 0
    assert aa._faculty_match_index(fac, "ob") == 1
    assert aa._faculty_match_index(fac, "") is None
    assert aa._faculty_match_index(fac, "B") is None


def test_execute_tool_catches_and_returns_json_error():
    with patch.object(aa, "_execute_tool_impl", side_effect=RuntimeError("boom")):
        out = aa.execute_tool(MagicMock(), "x", {})
    parsed = json.loads(out)
    assert parsed["ok"] is False and "boom" in parsed["error"]


def test_execute_impl_requires_filepath_for_non_skip_tools():
    mw = MagicMock()
    mw.config_mgr.filepath = None
    out = json.loads(aa._execute_tool_impl(mw, "add_room", {"room_name": "A"}))
    assert out["ok"] is False and "config file path" in out["error"]


def test_handler_get_active_get_json_summary_session(qt_app):
    mw = MagicMock()
    cm = MagicMock()
    cm.filepath = "/c.json"
    cm.data = {"x": 1}
    cm.get_summary_text.return_value = "S"
    mw.config_mgr = cm
    mw.schedules = [1, 2]
    mw.current_schedule_index = 1
    assert json.loads(aa._execute_tool_impl(mw, "get_active_config_path", {}))["path"] == "/c.json"
    assert json.loads(aa._execute_tool_impl(mw, "get_config_summary_text", {}))["summary"] == "S"
    s = json.loads(aa._execute_tool_impl(mw, "get_schedule_session_info", {}))
    assert s["schedule_count"] == 2 and s["current_index"] == 1


@patch("ai.ai_assistant._write_config_silent")
def test_save_update_delete_list_paths(_write, tmp_path, qt_app):
    mw = MagicMock()
    mw.config_mgr = MagicMock(filepath=str(tmp_path / "cfg.json"), data={
        "config": {"rooms": ["R1"], "labs": [], "courses": [{"course_id": "C1", "credits": 1}], "faculty": []}
    })
    assert json.loads(aa._execute_tool_impl(mw, "save_config_to_disk", {}))["ok"] is True
    up = json.loads(aa._execute_tool_impl(mw, "update_course", {"course_id": "C1", "credits": 2, "rooms": ["A"]}))
    assert up["ok"] is True and up["course"]["credits"] == 2 and up["course"]["room"] == ["A"]
    assert json.loads(aa._execute_tool_impl(mw, "delete_course", {"course_id": "C1"}))["ok"] is True
    assert json.loads(aa._execute_tool_impl(mw, "list_rooms", {}))["rooms"] == ["R1"]


@patch("ai.ai_assistant._write_config_silent")
def test_update_delete_course_not_found(_write, tmp_path, qt_app):
    mw = MagicMock()
    mw.config_mgr = MagicMock(filepath=str(tmp_path / "cfg.json"), data={"config": {"rooms": [], "labs": [], "courses": [], "faculty": []}})
    assert "not found" in json.loads(aa._execute_tool_impl(mw, "update_course", {"course_id": "Nope"}))["error"]
    assert "not found" in json.loads(aa._execute_tool_impl(mw, "delete_course", {"course_id": "Nope"}))["error"]


def test_unknown_tool_in_crud():
    mw = MagicMock()
    mw.config_mgr = MagicMock(filepath="/x.json", data={"config": {"rooms": [], "labs": [], "courses": [], "faculty": []}})
    assert "Unknown tool" in json.loads(
        aa._execute_tool_impl(mw, "not_a_registered_tool_xyz", {"room_name": "A"})
    )["error"]


def test_add_room_and_list_tools(tmp_path):
    cfg_path = tmp_path / "cfg.json"
    cfg_path.write_text(
        json.dumps(
            {
                "config": {"rooms": [], "labs": [], "courses": [], "faculty": []},
                "limit": 1,
                "optimizer_flags": [],
            }
        ),
        encoding="utf-8",
    )
    mw = MagicMock()
    mw.config_mgr = MagicMock(filepath=str(cfg_path), data=json.loads(cfg_path.read_text()))
    out = json.loads(aa._execute_tool_impl(mw, "add_room", {"room_name": "Awesome Freaking Room"}))
    assert out["ok"] is True
    assert "Awesome Freaking Room" in out["rooms"]
    listed = json.loads(aa._execute_tool_impl(mw, "list_rooms", {}))
    assert listed["rooms"] == ["Awesome Freaking Room"]


def test_get_config_json_truncates(qt_app):
    mw = MagicMock()
    mw.config_mgr = MagicMock(filepath="/x.json", data={"k": "x" * 90000})
    out = json.loads(aa._execute_tool_impl(mw, "get_config_json", {}))
    assert out["ok"] is True and "truncated" in out["json"]


def test_reload_success_and_failure(qt_app):
    mw = MagicMock()
    cm = MagicMock(filepath="/a.json")
    cm.load.return_value = {}
    mw.config_mgr = cm
    with patch.object(mw, "mid_panel", create=True) as mid:
        assert json.loads(aa._execute_tool_impl(mw, "reload_config_from_disk", {}))["ok"] is True
        mid.update_title.assert_called_with("/a.json")
    mw2 = SimpleNamespace(config_mgr=MagicMock(), assistant_push_config_undo_snapshot=MagicMock(), _sync_detail_view=MagicMock())
    mw2.config_mgr.load.return_value = None
    fail = json.loads(aa._execute_tool_impl(mw2, "reload_config_from_disk", {}))
    assert fail["ok"] is False


def test_export_helpers(qt_app, tmp_path):
    mw = MagicMock()
    mw.config_mgr = MagicMock()
    assert json.loads(aa._export_all_schedules_pdf(mw, {"pdf_path": " "}, _ok_json))["ok"] is False
    assert json.loads(aa._export_all_schedules_json(mw, {"json_path": " "}, _ok_json))["ok"] is False
    mw.schedules = []
    assert "No schedules" in json.loads(aa._export_all_schedules_pdf(mw, {"pdf_path": str(tmp_path / "x")}, _ok_json))["error"]
    assert "No schedules" in json.loads(aa._export_all_schedules_json(mw, {"json_path": str(tmp_path / "x")}, _ok_json))["error"]

    mw.schedules = [1]
    mw.config_mgr._write_schedules_pdf.side_effect = OSError("p")
    assert json.loads(aa._export_all_schedules_pdf(mw, {"pdf_path": str(tmp_path / "x")}, _ok_json))["ok"] is False
    mw.config_mgr.write_schedules_json_file.side_effect = OSError("j")
    assert json.loads(aa._export_all_schedules_json(mw, {"json_path": str(tmp_path / "x")}, _ok_json))["ok"] is False

    mw.config_mgr._write_schedules_pdf.side_effect = None
    mw.config_mgr.write_schedules_json_file.side_effect = None
    with patch("ai.ai_assistant.os.path.abspath", side_effect=lambda p: p), patch("ai.ai_assistant.os.path.expanduser", side_effect=lambda p: p):
        assert json.loads(aa._export_all_schedules_pdf(mw, {"pdf_path": str(tmp_path / "ok.pdf")}, _ok_json))["ok"] is True
        assert json.loads(aa._export_all_schedules_json(mw, {"json_path": str(tmp_path / "ok.json")}, _ok_json))["ok"] is True


def test_undo_redo_paths_and_execute(qt_app):
    mw = MagicMock()
    mw.assistant_undo_config_change.return_value = False
    mw.assistant_redo_config_change.return_value = False
    assert "Nothing to undo" in json.loads(aa._assistant_undo(mw, _ok_json))["error"]
    assert "Nothing to redo" in json.loads(aa._assistant_redo(mw, _ok_json))["error"]
    mw.assistant_undo_config_change.return_value = True
    mw.assistant_redo_config_change.return_value = True
    assert json.loads(aa._assistant_undo(mw, _ok_json))["ok"] is True
    assert json.loads(aa._assistant_redo(mw, _ok_json))["ok"] is True
    mw.config_mgr = MagicMock(filepath="/x.json")
    aa._execute_tool_impl(mw, "undo_configuration_change", {})
    aa._execute_tool_impl(mw, "redo_configuration_change", {})


def test_handle_native_gui(qt_app):
    def okify(msg: str, **extra):
        return json.dumps({"ok": True, "message": msg, **extra})

    mw = MagicMock()
    m = MagicMock()
    m.add_course_via_dialog = MagicMock()
    m.add_faculty_via_dialog = MagicMock()
    mw.course_manager = m
    mw.faculty_manager = m
    out = json.loads(aa._handle_native_gui(mw, {"action": "course_add"}, okify))
    assert out["ok"] is True
    unmapped = json.loads(aa._handle_native_gui(mw, {"action": "not_real"}, okify))
    assert unmapped["ok"] is False
    assert json.loads(aa._handle_native_gui(mw, {"action": "faculty_add"}, okify))["ok"] is True
    m.add_faculty_via_dialog.assert_called_once_with(mw)


def test_run_schedule_generation_and_show_summary(qt_app):
    mw = MagicMock()
    mw.config_mgr = MagicMock(filepath="/c.json", data={})
    mw.viewer_mgr = MagicMock()
    assert json.loads(aa._execute_tool_impl(mw, "run_schedule_generation", {}))["ok"] is True
    assert json.loads(aa._execute_tool_impl(mw, "show_config_summary_dialog", {}))["ok"] is True
    mw.viewer_mgr.handle_view_summary.assert_called_once_with(mw)


def test_open_schedule_viewer_tool(qt_app):
    mw = MagicMock()
    mw.viewer_mgr = MagicMock()
    out = json.loads(aa._execute_tool_impl(mw, "open_schedule_viewer", {"mode": "faculty"}))
    assert out["ok"] is True
    mw.viewer_mgr.update_schedule_display.assert_called_once_with(mw, "faculty")
    bad = json.loads(aa._execute_tool_impl(mw, "open_schedule_viewer", {"mode": "nope"}))
    assert bad["ok"] is False


# --- AssistantChatWorker.run ---
def _install_fake_openai(client_chat):
    module = types.ModuleType("openai")

    class _OpenAI:
        def __init__(self, **kwargs):
            self.chat = client_chat

    module.OpenAI = _OpenAI
    prev = sys.modules.get("openai")
    sys.modules["openai"] = module
    return prev


def _restore_openai(prev):
    if prev is None:
        sys.modules.pop("openai", None)
    else:
        sys.modules["openai"] = prev


def _client_with_create(side_effect):
    c = SimpleNamespace()
    c.chat = SimpleNamespace()
    c.chat.completions = SimpleNamespace()
    c.chat.completions.create = MagicMock(side_effect=side_effect)
    return c


@patch("ai.ai_assistant.get_tool_schemas", return_value=[])
def test_worker_import_error(_schemas, qt_app):
    from unittest.mock import Mock

    real_import = builtins.__import__

    def fake_import(name, globals=None, locals=None, fromlist=(), level=0):
        if name == "openai":
            raise ImportError("no openai")
        return real_import(name, globals, locals, fromlist, level)

    w = aa.AssistantChatWorker("k", "m", [])
    w.failed = Mock()
    with patch("builtins.__import__", side_effect=fake_import):
        w.run()
    w.failed.emit.assert_called_once()


@patch("ai.ai_assistant.get_tool_schemas", return_value=[])
def test_worker_tool_loop_and_finish(_schemas, qt_app):
    from unittest.mock import Mock

    tool_tc = SimpleNamespace(id="t1", function=SimpleNamespace(name="n", arguments="{}"))
    msg1 = SimpleNamespace(content=None, tool_calls=[tool_tc])
    msg2 = SimpleNamespace(content="  Hi  ", tool_calls=None)
    r1 = SimpleNamespace(choices=[SimpleNamespace(message=msg1)])
    r2 = SimpleNamespace(choices=[SimpleNamespace(message=msg2)])
    client = _client_with_create([r1, r2])
    prev = _install_fake_openai(client.chat)
    try:
        w = aa.AssistantChatWorker("k", "m", [{"role": "user", "content": "x"}])
        w.finished_reply = Mock()
        w.failed = Mock()
        w.need_tools = SimpleNamespace(
            emit=lambda tools: w.deliver_tool_results([{"id": "t1", "content": "tool-out"}])
        )
        w.run()
        w.finished_reply.emit.assert_called_once()
        assert len(w.out_messages) > 0
    finally:
        _restore_openai(prev)


@patch("ai.ai_assistant.get_tool_schemas", return_value=[])
def test_worker_empty_text_timeout_and_exception(_schemas, qt_app):
    from unittest.mock import Mock

    # empty text
    msg = SimpleNamespace(content=None, tool_calls=None)
    r = SimpleNamespace(choices=[SimpleNamespace(message=msg)])
    client = _client_with_create([r])
    prev = _install_fake_openai(client.chat)
    try:
        w = aa.AssistantChatWorker("k", "m", [])
        w.finished_reply = Mock()
        w.run()
        w.finished_reply.emit.assert_called_with("(No text reply.)")
    finally:
        _restore_openai(prev)

    # timeout
    tool_tc = SimpleNamespace(id="t1", function=SimpleNamespace(name="n", arguments="{}"))
    msg_t = SimpleNamespace(content="x", tool_calls=[tool_tc])
    rt = SimpleNamespace(choices=[SimpleNamespace(message=msg_t)])
    client_t = _client_with_create([rt])
    prev = _install_fake_openai(client_t.chat)
    try:
        w = aa.AssistantChatWorker("k", "m", [])
        w.failed = Mock()
        w.need_tools = Mock()
        w._done.wait = MagicMock(return_value=False)
        w.run()
        w.failed.emit.assert_called_with("Timed out waiting for tool execution.")
    finally:
        _restore_openai(prev)

    # API exception
    client_e = _client_with_create([ValueError("api")])
    prev = _install_fake_openai(client_e.chat)
    try:
        w = aa.AssistantChatWorker("k", "m", [])
        w.failed = Mock()
        w.run()
        w.failed.emit.assert_called_with("api")
    finally:
        _restore_openai(prev)
