"""
test_ai_viewer_gui.py
=====================
Pytests for ``ai.ai_viewer_gui`` controller logic.

:date: 04/25/2026
:author: Shane del Villar
:class: CMSC 420
"""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock, mock_open, patch

import pytest

from ai.ai_viewer_gui import AIViewerManager


class _Signal:
    def __init__(self):
        self.connect = MagicMock()


class _Worker:
    def __init__(self, running: bool = False):
        self._running = running
        self.need_tools = _Signal()
        self.finished_reply = _Signal()
        self.failed = _Signal()
        self.finished = _Signal()
        self.out_messages = [{"role": "assistant", "content": "ok"}]
        self.deliver_tool_results = MagicMock()
        self.start = MagicMock()
        self.deleteLater = MagicMock()

    def isRunning(self):
        return self._running


@pytest.fixture
def mw():
    m = MagicMock()
    m.ai_chat_log = MagicMock()
    m.ai_input = MagicMock()
    m.ai_input.text.return_value = " hello "
    m.ai_send_btn = MagicMock()
    m.config_mgr = MagicMock()
    m.config_mgr.filepath = ""
    m.config_mgr.data = {"config": {"x": 1}}
    m.viewer_mgr = MagicMock()
    m.viewer_mgr._sync_detail_view = MagicMock()
    return m


def test_init_sets_defaults(mw):
    mgr = AIViewerManager(mw)
    assert mgr.mw is mw
    assert len(mgr.assistant_messages) == 1
    assert mgr._assistant_worker is None


def test_append_ai_chat_formats_line(mw):
    mgr = AIViewerManager(mw)
    mgr.append_ai_chat("You", "Hi")
    mw.ai_chat_log.appendPlainText.assert_called_once_with("You: Hi\n")


def test_refresh_syncs_inspector_via_viewer_mgr(mw):
    mgr = AIViewerManager(mw)
    mw.config_mgr.filepath = "/tmp/cfg.json"
    mgr.refresh_config_views_after_mutation()
    mw.config_mgr.load.assert_not_called()
    mw.viewer_mgr._sync_detail_view.assert_called_once_with(mw)


def test_send_assistant_message_returns_when_worker_running(mw):
    mgr = AIViewerManager(mw)
    mgr._assistant_worker = _Worker(running=True)
    mgr.send_assistant_message()
    mw.ai_input.clear.assert_not_called()


def test_send_assistant_message_returns_when_empty_input(mw):
    mgr = AIViewerManager(mw)
    mw.ai_input.text.return_value = "   "
    mgr.send_assistant_message()
    mw.ai_input.clear.assert_not_called()


@patch("ai.ai_viewer_gui.default_api_key", return_value="")
@patch("ai.ai_viewer_gui.QMessageBox.warning")
def test_send_assistant_message_warns_without_api_key(mock_warn, mock_key, mw):
    mgr = AIViewerManager(mw)
    mgr.send_assistant_message()
    mock_warn.assert_called_once()
    mw.ai_input.clear.assert_not_called()


@patch("ai.ai_viewer_gui.AssistantChatWorker")
@patch("ai.ai_viewer_gui.default_api_key", return_value="abc")
def test_send_assistant_message_starts_worker(mock_key, mock_worker_cls, mw):
    worker = _Worker(running=False)
    mock_worker_cls.return_value = worker
    mgr = AIViewerManager(mw)

    mgr.send_assistant_message()

    mw.ai_input.clear.assert_called_once()
    mw.ai_send_btn.setEnabled.assert_called_with(False)
    mw.ai_input.setEnabled.assert_called_with(False)
    worker.need_tools.connect.assert_called_once()
    worker.finished_reply.connect.assert_called_once()
    worker.failed.connect.assert_called_once()
    worker.finished.connect.assert_called_once()
    worker.start.assert_called_once()
    assert mgr._assistant_worker is worker
    assert mgr.assistant_messages[-1]["role"] == "user"


@patch("ai.ai_viewer_gui.execute_tool")
def test_on_assistant_need_tools_executes_and_delivers(mock_exec, mw):
    mock_exec.side_effect = ["ok1", "ok2"]
    mgr = AIViewerManager(mw)
    mgr._assistant_worker = _Worker()
    mgr.refresh_config_views_after_mutation = MagicMock()
    tool_calls = [
        {"id": "1", "name": "x", "arguments": '{"a": 1}'},
        {"id": "2", "name": "y", "arguments": "{bad json"},
    ]

    mgr.on_assistant_need_tools(tool_calls)

    assert mock_exec.call_count == 2
    mgr.refresh_config_views_after_mutation.assert_called_once()
    mgr._assistant_worker.deliver_tool_results.assert_called_once_with(
        [{"id": "1", "content": "ok1"}, {"id": "2", "content": "ok2"}]
    )


def test_on_assistant_need_tools_no_worker_after_refresh(mw):
    mgr = AIViewerManager(mw)
    mgr._assistant_worker = None
    mgr.refresh_config_views_after_mutation = MagicMock()
    with patch("ai.ai_viewer_gui.execute_tool", return_value="z"):
        mgr.on_assistant_need_tools([{"id": "1", "name": "x", "arguments": "{}"}])
    mgr.refresh_config_views_after_mutation.assert_called_once()


def test_dispose_assistant_chat_worker_current_worker(mw):
    mgr = AIViewerManager(mw)
    worker = _Worker()
    mgr._assistant_worker = worker
    mgr.dispose_assistant_chat_worker(worker)
    assert mgr._assistant_worker is None
    worker.deleteLater.assert_called_once()


def test_dispose_assistant_chat_worker_non_current_worker(mw):
    mgr = AIViewerManager(mw)
    current = _Worker()
    other = _Worker()
    mgr._assistant_worker = current
    mgr.dispose_assistant_chat_worker(other)
    assert mgr._assistant_worker is current
    other.deleteLater.assert_called_once()


def test_on_assistant_finished_uses_out_messages_when_worker_exists(mw):
    mgr = AIViewerManager(mw)
    worker = _Worker()
    worker.out_messages = [{"role": "assistant", "content": "done"}]
    mgr._assistant_worker = worker
    mgr.on_assistant_finished("done")
    assert mgr.assistant_messages == worker.out_messages
    mw.ai_send_btn.setEnabled.assert_called_with(True)
    mw.ai_input.setEnabled.assert_called_with(True)


def test_on_assistant_failed_reenables_controls(mw):
    mgr = AIViewerManager(mw)
    mgr.on_assistant_failed("boom")
    mw.ai_chat_log.appendPlainText.assert_called_once()
    mw.ai_send_btn.setEnabled.assert_called_with(True)
    mw.ai_input.setEnabled.assert_called_with(True)


def test_assistant_push_snapshot_returns_without_path(mw):
    mgr = AIViewerManager(mw)
    mgr._assistant_config_redo_stack = [1]
    mgr.assistant_push_config_undo_snapshot()
    assert mgr._assistant_config_redo_stack == [1]
    assert mgr._assistant_config_undo_stack == []


def test_assistant_push_snapshot_clears_redo_and_caps_stack(mw):
    mgr = AIViewerManager(mw)
    mw.config_mgr.filepath = "/tmp/cfg.json"
    mgr._assistant_config_undo_stack = list(range(40))
    mgr._assistant_config_redo_stack = [9]
    mgr.assistant_push_config_undo_snapshot()
    assert mgr._assistant_config_redo_stack == []
    assert len(mgr._assistant_config_undo_stack) == 40


def test_assistant_undo_returns_false_when_stack_empty(mw):
    mgr = AIViewerManager(mw)
    assert mgr.assistant_undo_config_change() is False


@patch("ai.ai_viewer_gui.open", new_callable=mock_open)
def test_assistant_undo_success_writes_and_syncs(mock_file, mw):
    mgr = AIViewerManager(mw)
    mw.config_mgr.filepath = "/tmp/cfg.json"
    mw.config_mgr.data = {"v": 2}
    mgr._assistant_config_undo_stack = [{"v": 1}]
    assert mgr.assistant_undo_config_change() is True
    assert mgr._assistant_config_redo_stack[-1] == {"v": 2}
    assert mw.config_mgr.data == {"v": 1}
    mw.viewer_mgr._sync_detail_view.assert_called_once_with(mw)


@patch("ai.ai_viewer_gui.open", side_effect=OSError)
def test_assistant_undo_returns_false_on_write_error(mock_file, mw):
    mgr = AIViewerManager(mw)
    mw.config_mgr.filepath = "/tmp/cfg.json"
    mgr._assistant_config_undo_stack = [{"v": 1}]
    assert mgr.assistant_undo_config_change() is False


def test_assistant_redo_returns_false_when_stack_empty(mw):
    mgr = AIViewerManager(mw)
    assert mgr.assistant_redo_config_change() is False


@patch("ai.ai_viewer_gui.open", new_callable=mock_open)
def test_assistant_redo_success_writes_and_syncs(mock_file, mw):
    mgr = AIViewerManager(mw)
    mw.config_mgr.filepath = "/tmp/cfg.json"
    mw.config_mgr.data = {"v": 1}
    mgr._assistant_config_redo_stack = [{"v": 2}]
    assert mgr.assistant_redo_config_change() is True
    assert mgr._assistant_config_undo_stack[-1] == {"v": 1}
    assert mw.config_mgr.data == {"v": 2}
    mw.viewer_mgr._sync_detail_view.assert_called_once_with(mw)


@patch("ai.ai_viewer_gui.open", side_effect=OSError)
def test_assistant_redo_returns_false_on_write_error(mock_file, mw):
    mgr = AIViewerManager(mw)
    mw.config_mgr.filepath = "/tmp/cfg.json"
    mgr._assistant_config_redo_stack = [{"v": 2}]
    assert mgr.assistant_redo_config_change() is False
