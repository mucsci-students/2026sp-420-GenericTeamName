"""
Tests for ``ai.ai_assistant`` (tool execution helpers, default API key, chat worker).
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

import ai.ai_assistant as aa


@pytest.fixture(scope="module")
def qt_core_app():
    from PyQt6.QtCore import QCoreApplication

    app = QCoreApplication.instance()
    if app is None:
        app = QCoreApplication(sys.argv)
    return app


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


# --- private helpers (module-level) ---


def test_ensure_config_block_builds_structures():
    mw = SimpleNamespace()
    mw.config_mgr = SimpleNamespace(data=None)
    cfg = aa._ensure_config_block(mw)
    assert isinstance(mw.config_mgr.data, dict)
    for k in ("rooms", "labs", "courses", "faculty"):
        assert isinstance(cfg[k], list)


def test_ensure_config_block_fixes_bad_config_type():
    mw = SimpleNamespace()
    mw.config_mgr = SimpleNamespace(data={"config": "bad"})
    cfg = aa._ensure_config_block(mw)
    assert isinstance(mw.config_mgr.data["config"], dict)
    assert "rooms" in cfg


@patch("ai.ai_assistant.json.dump")
@patch("builtins.open", new_callable=mock_open)
def test_write_config_silent_pushes_and_writes(mock_file, mock_dump):
    mw = SimpleNamespace(
        config_mgr=SimpleNamespace(
            filepath="/x/cfg.json", data={"a": 1}
        ),
        assistant_push_config_undo_snapshot=MagicMock(),
    )
    aa._write_config_silent(mw)
    mw.assistant_push_config_undo_snapshot.assert_called_once()
    mock_dump.assert_called_once()


@patch("builtins.open", new_callable=mock_open)
@patch("ai.ai_assistant.json.dump")
def test_write_config_silent_no_snapshot_attr(mock_dump, mock_file):
    mw = SimpleNamespace(
        config_mgr=SimpleNamespace(filepath="/x/cfg.json", data={})
    )
    aa._write_config_silent(mw)


def test_faculty_display_name():
    assert aa._faculty_display_name({"name": "N"}) == "N"
    assert aa._faculty_display_name("plain") == "plain"


def test_normalize_weekday_for_editor():
    dmap = {
        "Monday": "Monday",
        "Tuesday": "Tuesday",
    }
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


def test_normalize_meeting_entries_branches():
    dmap, rev = ({"Monday": "Monday"}, {"MON": "Monday"})
    assert aa._normalize_meeting_entries([], dmap, rev) == (None, "At least one meeting is required.")
    assert aa._normalize_meeting_entries(
        [{"day": "MON", "duration": "nope", "lab": False}], dmap, rev
    )[1] == "duration must be an integer."
    assert aa._normalize_meeting_entries(
        [{"day": "MON", "duration": 0, "lab": False}], dmap, rev
    )[1] == "duration must be >= 1."


def test_normalize_meeting_entries():
    dmap = {"Monday": "Monday"}
    rev = {"MON": "Monday"}
    ok, err = aa._normalize_meeting_entries(
        [{"day": "MON", "duration": 50, "lab": True}], dmap, rev
    )
    assert err is None and ok[0]["day"] == "Monday" and ok[0]["lab"] is True
    r = aa._normalize_meeting_entries([123], dmap, rev)
    assert r[0] is None
    r2 = aa._normalize_meeting_entries(
        [{"day": "X", "duration": 1}], dmap, rev
    )
    assert "Invalid weekday" in r2[1]


def test_faculty_match_index():
    fac = [{"name": "Abe"}, "Bob", 3]
    assert aa._faculty_match_index(fac, "abe") == 0
    assert aa._faculty_match_index(fac, "ob") == 1
    assert aa._faculty_match_index(fac, "") is None
    assert aa._faculty_match_index(fac, "B") is None


def test_execute_tool_catches_and_returns_json_error():
    mw = MagicMock()
    with patch.object(aa, "_execute_tool_impl", side_effect=RuntimeError("boom")):
        out = aa.execute_tool(mw, "x", {})
    assert "boom" in out
    assert json.loads(out)["ok"] is False


def test_execute_impl_requires_filepath_for_add_room():
    mw = MagicMock()
    mw.config_mgr.filepath = None
    out = json.loads(
        aa._execute_tool_impl(mw, "add_room", {"room_name": "A"})
    )
    assert out["ok"] is False
    assert "config file path" in out["error"]


def test_handler_get_active_get_json_summary_session(qt_core_app):
    mw = MagicMock()
    cm = MagicMock()
    cm.filepath = "/c.json"
    cm.data = {"x": 1}
    cm.get_summary_text.return_value = "S"
    mw.config_mgr = cm
    mw.schedules = [1, 2]
    mw.current_schedule_index = 1

    a = json.loads(aa._execute_tool_impl(mw, "get_active_config_path", {}))
    assert a["ok"] and a["path"] == "/c.json"

    b = json.loads(aa._execute_tool_impl(mw, "get_config_summary_text", {}))
    assert b["ok"] and b["summary"] == "S"

    c = json.loads(aa._execute_tool_impl(mw, "get_schedule_session_info", {}))
    assert c["ok"] and c["schedule_count"] == 2 and c["current_index"] == 1


@patch("ai.ai_assistant._write_config_silent")
def test_save_config_to_disk(mock_write, qt_core_app):
    mw = MagicMock()
    mw.config_mgr = MagicMock(filepath="/a.json", data={})
    r = json.loads(aa._execute_tool_impl(mw, "save_config_to_disk", {}))
    assert r["ok"] is True
    mock_write.assert_called_once_with(mw)


@patch("ai.ai_assistant._write_config_silent")
def test_update_delete_course_and_list_rooms(mock_write, tmp_path, qt_core_app):
    mw = MagicMock()
    cm = MagicMock()
    cm.filepath = str(tmp_path / "c.json")
    cm.data = {
        "config": {
            "rooms": ["R1"],
            "labs": [],
            "courses": [
                {
                    "course_id": "C1",
                    "credits": 1,
                }
            ],
            "faculty": [],
        }
    }
    mw.config_mgr = cm

    u = json.loads(
        aa._execute_tool_impl(
            mw,
            "update_course",
            {
                "course_id": "C1",
                "credits": 2,
                "rooms": ["A"],
            },
        )
    )
    assert u["ok"] is True
    assert u["course"]["credits"] == 2
    assert u["course"]["room"] == ["A"]

    d = json.loads(
        aa._execute_tool_impl(mw, "delete_course", {"course_id": "C1"})
    )
    assert d["ok"] is True
    assert not cm.data["config"]["courses"]

    lr = json.loads(aa._execute_tool_impl(mw, "list_rooms", {}))
    assert lr["ok"] and lr["rooms"] == ["R1"]


@patch("ai.ai_assistant._write_config_silent")
def test_update_course_not_found(mock_write, tmp_path, qt_core_app):
    mw = MagicMock()
    cm = MagicMock(
        filepath=str(tmp_path / "c.json"),
        data={"config": {"rooms": [], "labs": [], "courses": [], "faculty": []}},
    )
    mw.config_mgr = cm
    out = json.loads(
        aa._execute_tool_impl(mw, "update_course", {"course_id": "Nope"})
    )
    assert out["ok"] is False
    assert "not found" in out["error"]


@patch("ai.ai_assistant._write_config_silent")
def test_delete_course_not_found(mock_write, tmp_path, qt_core_app):
    mw = MagicMock()
    cm = MagicMock(
        filepath=str(tmp_path / "c.json"),
        data={"config": {"rooms": [], "labs": [], "courses": [], "faculty": []}},
    )
    mw.config_mgr = cm
    out = json.loads(
        aa._execute_tool_impl(mw, "delete_course", {"course_id": "Nope"})
    )
    assert out["ok"] is False
    assert "not found" in out["error"]


def test_unknown_tool_in_crud(qt_core_app):
    mw = MagicMock()
    cm = MagicMock()
    cm.filepath = "/x.json"
    cm.data = {
        "config": {"rooms": [], "labs": [], "courses": [], "faculty": []}
    }
    mw.config_mgr = cm
    out = json.loads(aa._execute_tool_impl(mw, "add_room", {"room_name": "A"}))
    assert "Unknown tool" in out["error"]


def test_get_config_json_truncates(qt_core_app):
    big = {"k": "x" * 90000}
    mw = MagicMock()
    cm = MagicMock()
    cm.filepath = "/x.json"
    cm.data = big
    mw.config_mgr = cm
    out = json.loads(aa._execute_tool_impl(mw, "get_config_json", {}))
    assert out["ok"] and "truncated" in out["json"]


@patch("ai.ai_assistant._write_config_silent")
def test_handle_reload_success(mock_write, qt_core_app):
    mw = MagicMock()
    cm = MagicMock()
    cm.filepath = "/a.json"
    cm.load = MagicMock(return_value={})
    mw.config_mgr = cm
    with patch.object(mw, "mid_panel", create=True) as mid:
        r = json.loads(aa._execute_tool_impl(mw, "reload_config_from_disk", {}))
    assert r["ok"] is True
    mw.assistant_push_config_undo_snapshot.assert_called_once()
    mid.update_title.assert_called_with("/a.json")
    mw._sync_detail_view.assert_called_once()


@patch("ai.ai_assistant._write_config_silent")
def test_handle_reload_fails_no_mid_panel(mock_write, qt_core_app):
    cm = MagicMock()
    cm.load = MagicMock(return_value=None)
    mw = SimpleNamespace(
        config_mgr=cm,
        assistant_push_config_undo_snapshot=MagicMock(),
        _sync_detail_view=MagicMock(),
    )
    r = json.loads(aa._execute_tool_impl(mw, "reload_config_from_disk", {}))
    assert r["ok"] is False
    assert "Failed to reload" in r["error"]


def _ok_json(msg: str, **extra: object) -> str:
    return json.dumps({"ok": True, "message": msg, **extra})


def test_export_all_schedules_success_branches(tmp_path, qt_core_app):
    """Hit success returns in _export_all_schedules_pdf / _export_all_schedules_json."""
    with patch("ai.ai_assistant.os.path.abspath", side_effect=lambda p: p), patch(
        "ai.ai_assistant.os.path.expanduser", side_effect=lambda p: p
    ):
        mw = MagicMock()
        mw.config_mgr = MagicMock()
        mw.schedules = [{"x": 1}]

        out_pdf = json.loads(
            aa._export_all_schedules_pdf(
                mw, {"pdf_path": str(tmp_path / "a.pdf")}, _ok_json
            )
        )
        assert out_pdf["ok"] is True
        mw.config_mgr._write_schedules_pdf.assert_called_once()

        out_j = json.loads(
            aa._export_all_schedules_json(
                mw, {"json_path": str(tmp_path / "a.json")}, _ok_json
            )
        )
        assert out_j["ok"] is True
        mw.config_mgr.write_schedules_json_file.assert_called_once()


@patch("ai.ai_assistant._export_all_schedules_json")
@patch("ai.ai_assistant._export_all_schedules_pdf")
def test_export_tools(mock_pdf, mock_json, tmp_path, qt_core_app):
    mw = MagicMock()
    mw.config_mgr = MagicMock(filepath="/x.json")
    mw.schedules = [{"a": 1}]

    mock_pdf.return_value = '{"ok": true}'
    mock_json.return_value = '{"ok": true}'
    assert "ok" in aa._execute_tool_impl(
        mw, "export_all_schedules_to_pdf", {"pdf_path": str(tmp_path / "out.pdf")}
    )
    assert "ok" in aa._execute_tool_impl(
        mw, "export_all_schedules_to_json", {"json_path": str(tmp_path / "j.json")}
    )


def test_export_pdf_path_errors(tmp_path, qt_core_app):
    mw = MagicMock()
    mw.config_mgr = MagicMock()
    out = json.loads(
        aa._export_all_schedules_pdf(mw, {"pdf_path": "  "}, lambda **k: "")
    )
    assert out["ok"] is False
    p = str(tmp_path / "noext")
    mw.schedules = []
    o2 = json.loads(aa._export_all_schedules_pdf(mw, {"pdf_path": p}, lambda **k: ""))
    assert "No schedules" in o2["error"]


def test_export_json_path_errors(qt_core_app):
    out = json.loads(
        aa._export_all_schedules_json(MagicMock(), {"json_path": "  "}, _ok_json)
    )
    assert out["ok"] is False
    assert "json_path" in out["error"]
    mw = MagicMock()
    mw.schedules = []
    mw.config_mgr = MagicMock()
    o2 = json.loads(
        aa._export_all_schedules_json(
            mw, {"json_path": "/tmp/x.json"}, lambda **k: json.dumps(k)
        )
    )
    assert o2["ok"] is False
    assert "No schedules" in o2["error"]


def test_export_adds_ext_and_errors_on_write(tmp_path, qt_core_app):
    mw = MagicMock()
    mw.config_mgr = MagicMock()
    mw.schedules = [1, 2]
    mw.config_mgr._write_schedules_pdf.side_effect = OSError("w")

    p = str(tmp_path / "doc")
    o = json.loads(
        aa._export_all_schedules_pdf(mw, {"pdf_path": p}, lambda **k: json.dumps(k))
    )
    assert o["ok"] is False
    called_path = mw.config_mgr._write_schedules_pdf.call_args[0][0]
    assert str(called_path).lower().endswith(".pdf")

    mw2 = MagicMock()
    mw2.config_mgr = MagicMock()
    mw2.schedules = [1]
    mw2.config_mgr.write_schedules_json_file.side_effect = OSError("j")
    o2 = json.loads(
        aa._export_all_schedules_json(
            mw2, {"json_path": str(tmp_path / "d")}, lambda **k: json.dumps(k)
        )
    )
    assert o2["ok"] is False


def test_assistant_undo_redo_branches(qt_core_app):
    mw = MagicMock()
    mw.assistant_undo_config_change.return_value = False
    mw.assistant_redo_config_change.return_value = False
    out = json.loads(aa._assistant_undo(mw, lambda *a, **k: ""))
    assert "Nothing to undo" in out["error"]
    out2 = json.loads(aa._assistant_redo(mw, lambda *a, **k: ""))
    assert "Nothing to redo" in out2["error"]


def test_assistant_undo_redo_success_path(qt_core_app):
    def ok(msg: str, **extra):
        return json.dumps({"ok": True, "message": msg, **extra})

    mw = MagicMock()
    mw.assistant_undo_config_change.return_value = True
    out = json.loads(aa._assistant_undo(mw, ok))
    assert out["ok"] is True
    mw.assistant_redo_config_change.return_value = True
    out2 = json.loads(aa._assistant_redo(mw, ok))
    assert out2["ok"] is True


@patch("ai.ai_assistant._assistant_redo", return_value="{}")
@patch("ai.ai_assistant._assistant_undo", return_value="{}")
def test_undo_redo_handlers_through_execute(mock_u, mock_r, qt_core_app):
    mw = MagicMock()
    mw.config_mgr = MagicMock(filepath="/a.json")
    aa._execute_tool_impl(mw, "undo_configuration_change", {})
    mock_u.assert_called_once()
    aa._execute_tool_impl(mw, "redo_configuration_change", {})
    mock_r.assert_called_once()


def test_native_gui_success_and_unmapped_and_non_callable(qt_core_app):
    def okify(msg: str, **extra) -> str:
        return json.dumps({"ok": True, "message": msg, **extra})

    mw = MagicMock()
    m = MagicMock()
    m.add_course_via_dialog = MagicMock()
    m.add_faculty_via_dialog = 123
    mw.course_manager = m
    mw.faculty_manager = m

    o = json.loads(aa._handle_native_gui(mw, {"action": "course_add"}, okify))
    assert o["ok"] is True
    m.add_course_via_dialog.assert_called_once()

    o2 = json.loads(aa._handle_native_gui(mw, {"action": "not_real"}, okify))
    assert o2["ok"] is False

    o3 = json.loads(aa._handle_native_gui(mw, {"action": "faculty_add"}, okify))
    assert o3["ok"] is True


def test_run_schedule_generation_and_show_summary(qt_core_app):
    mw = MagicMock()
    cm = MagicMock(filepath="/c.json", data={})
    mw.config_mgr = cm
    r1 = json.loads(aa._execute_tool_impl(mw, "run_schedule_generation", {}))
    assert r1["ok"] is True
    mw.gen_manager.run_scheduler.assert_called_with(mw)

    r2 = json.loads(
        aa._execute_tool_impl(mw, "show_config_summary_dialog", {})
    )
    assert r2["ok"] is True
    assert mw.handle_view_summary.called


# --- AssistantChatWorker.run ---

def _install_fake_openai(client_chat):
    omod = types.ModuleType("openai")

    class _OpenAI:
        def __init__(self, **kwargs):
            self.chat = client_chat

    omod.OpenAI = _OpenAI
    prev = sys.modules.get("openai")
    sys.modules["openai"] = omod
    return prev


def _restore_openai(prev):
    if prev is not None:
        sys.modules["openai"] = prev
    else:
        sys.modules.pop("openai", None)


def _client_with_create(side_effect):
    c = SimpleNamespace()
    c.chat = SimpleNamespace()
    c.chat.completions = SimpleNamespace()
    c.chat.completions.create = MagicMock(side_effect=side_effect)
    return c


@patch("ai.ai_assistant.get_tool_schemas", return_value=[])
def test_worker_import_error(_schemas, qt_core_app):
    from unittest.mock import Mock

    real = builtins.__import__

    def fake_import(name, globals=None, locals=None, fromlist=(), level=0):
        if name == "openai":
            raise ImportError("no openai")
        return real(name, globals, locals, fromlist, level)

    w = aa.AssistantChatWorker("k", "m", [])
    w.failed = Mock()
    with patch("builtins.__import__", side_effect=fake_import):
        w.run()
    w.failed.emit.assert_called_once()
    assert "not installed" in w.failed.emit.call_args[0][0]


@patch("ai.ai_assistant.get_tool_schemas", return_value=[])
def test_worker_completes_with_text_and_tool_loop(_schemas, qt_core_app):
    from unittest.mock import Mock

    tool_tc = SimpleNamespace(
        id="t1", function=SimpleNamespace(name="n", arguments="{}")
    )
    msg1 = SimpleNamespace(content=None, tool_calls=[tool_tc])
    msg2 = SimpleNamespace(content="  Hi  ", tool_calls=None)
    r1 = SimpleNamespace(choices=[SimpleNamespace(message=msg1)])
    r2 = SimpleNamespace(choices=[SimpleNamespace(message=msg2)])
    client = _client_with_create([r1, r2])
    prev = _install_fake_openai(client.chat)
    try:
        w = aa.AssistantChatWorker("k", "m", [{"role": "user", "content": "x"}])
        w.failed = Mock()
        w.finished_reply = Mock()
        w.need_tools = SimpleNamespace(
            emit=lambda s: w.deliver_tool_results(
                [{"id": "t1", "content": "tool-out"}]
            )
        )
        w.run()
        w.finished_reply.emit.assert_called_once()
        call_arg = w.finished_reply.emit.call_args[0][0]
        assert "Hi" in call_arg
        assert len(w.out_messages) > 0
    finally:
        _restore_openai(prev)


@patch("ai.ai_assistant.get_tool_schemas", return_value=[])
def test_worker_empty_reply_text(_schemas, qt_core_app):
    from unittest.mock import Mock

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


@patch("ai.ai_assistant.get_tool_schemas", return_value=[])
def test_worker_tool_timeout(_schemas, qt_core_app):
    from unittest.mock import Mock

    tool_tc = SimpleNamespace(
        id="t1", function=SimpleNamespace(name="n", arguments="{}")
    )
    msg = SimpleNamespace(content="x", tool_calls=[tool_tc])
    r = SimpleNamespace(choices=[SimpleNamespace(message=msg)])
    client = _client_with_create([r])
    prev = _install_fake_openai(client.chat)
    try:
        w = aa.AssistantChatWorker("k", "m", [])
        w.failed = Mock()
        w.need_tools = Mock()
        w._done.wait = MagicMock(return_value=False)
        w.run()
        w.failed.emit.assert_called_with("Timed out waiting for tool execution.")
    finally:
        _restore_openai(prev)


@patch("ai.ai_assistant.get_tool_schemas", return_value=[])
def test_worker_api_exception(_schemas, qt_core_app):
    from unittest.mock import Mock

    client = _client_with_create([ValueError("api")])
    prev = _install_fake_openai(client.chat)
    try:
        w = aa.AssistantChatWorker("k", "m", [])
        w.failed = Mock()
        w.run()
        w.failed.emit.assert_called_with("api")
    finally:
        _restore_openai(prev)
