"""
ai_viewer_gui.py
================
Controller for AI assistant chat/view interactions.

:date: 04/22/2026
:author: Shane del Villar
:class: CMSC 420
"""

from __future__ import annotations

import copy
import json
import os
from typing import Any

from PyQt6.QtWidgets import QMessageBox

from .ai_assistant import (
    AssistantChatWorker,
    OPENAI_MODEL,
    SYSTEM_PROMPT,
    default_api_key,
    execute_tool,
)


class AIViewerManager:
    """Controller that owns assistant chat flow + assistant-specific undo/redo."""

    def __init__(self, main_window: Any) -> None:
        self.mw = main_window
        self._assistant_worker: AssistantChatWorker | None = None
        self.assistant_messages: list = [{"role": "system", "content": SYSTEM_PROMPT}]
        self._assistant_config_undo_stack: list = []
        self._assistant_config_redo_stack: list = []

    def append_ai_chat(self, who: str, text: str) -> None:
        self.mw.ai_chat_log.appendPlainText(f"{who}: {text}\n")

    def refresh_config_views_after_mutation(self) -> None:
        path = getattr(self.mw.config_mgr, "filepath", None)
        if path and os.path.isfile(path):
            self.mw.config_mgr.load(self.mw)
        self.mw._sync_detail_view()

    def send_assistant_message(self) -> None:
        if self._assistant_worker is not None and self._assistant_worker.isRunning():
            return
        user_text = self.mw.ai_input.text().strip()
        if not user_text:
            return

        key = default_api_key()
        if not key:
            QMessageBox.warning(
                self.mw,
                "OpenAI API key",
                "Set your key in app/ai_assistant.py (OPENAI_API_KEY_IN_CODE), "
                "or put it in config/openai_key.txt, or set OPENAI_API_KEY in the environment.",
            )
            return

        self.mw.ai_input.clear()
        self.append_ai_chat("You", user_text)
        self.assistant_messages.append({"role": "user", "content": user_text})
        self.mw.ai_send_btn.setEnabled(False)
        self.mw.ai_input.setEnabled(False)

        msgs = copy.deepcopy(self.assistant_messages)
        worker = AssistantChatWorker(key, OPENAI_MODEL, msgs)
        self._assistant_worker = worker
        worker.need_tools.connect(self.on_assistant_need_tools)
        worker.finished_reply.connect(self.on_assistant_finished)
        worker.failed.connect(self.on_assistant_failed)
        worker.finished.connect(lambda w=worker: self.dispose_assistant_chat_worker(w))
        worker.start()

    def on_assistant_need_tools(self, tool_calls: list) -> None:
        results = []
        for tc in tool_calls:
            try:
                args = json.loads(tc.get("arguments") or "{}")
            except json.JSONDecodeError:
                args = {}
            out = execute_tool(self.mw, tc["name"], args)
            results.append({"id": tc["id"], "content": out})
        self.refresh_config_views_after_mutation()
        if self._assistant_worker is not None:
            self._assistant_worker.deliver_tool_results(results)

    def dispose_assistant_chat_worker(self, worker: AssistantChatWorker) -> None:
        if self._assistant_worker is worker:
            self._assistant_worker = None
        worker.deleteLater()

    def on_assistant_finished(self, text: str) -> None:
        self.append_ai_chat("Assistant", text)
        if self._assistant_worker is not None:
            self.assistant_messages = self._assistant_worker.out_messages
        self.mw.ai_send_btn.setEnabled(True)
        self.mw.ai_input.setEnabled(True)

    def on_assistant_failed(self, err: str) -> None:
        self.append_ai_chat("Assistant", f"(Error) {err}")
        self.mw.ai_send_btn.setEnabled(True)
        self.mw.ai_input.setEnabled(True)

    def assistant_push_config_undo_snapshot(self) -> None:
        path = getattr(self.mw.config_mgr, "filepath", None)
        if not path:
            return
        self._assistant_config_redo_stack.clear()
        self._assistant_config_undo_stack.append(copy.deepcopy(self.mw.config_mgr.data))
        if len(self._assistant_config_undo_stack) > 40:
            self._assistant_config_undo_stack.pop(0)

    def assistant_undo_config_change(self) -> bool:
        if not self._assistant_config_undo_stack:
            return False
        path = getattr(self.mw.config_mgr, "filepath", None)
        self._assistant_config_redo_stack.append(copy.deepcopy(self.mw.config_mgr.data))
        self.mw.config_mgr.data = self._assistant_config_undo_stack.pop()
        if path:
            try:
                with open(path, "w", encoding="utf-8") as f:
                    json.dump(self.mw.config_mgr.data, f, indent=4)
            except OSError:
                return False
        self.mw._sync_detail_view()
        return True

    def assistant_redo_config_change(self) -> bool:
        if not self._assistant_config_redo_stack:
            return False
        path = getattr(self.mw.config_mgr, "filepath", None)
        self._assistant_config_undo_stack.append(copy.deepcopy(self.mw.config_mgr.data))
        self.mw.config_mgr.data = self._assistant_config_redo_stack.pop()
        if path:
            try:
                with open(path, "w", encoding="utf-8") as f:
                    json.dump(self.mw.config_mgr.data, f, indent=4)
            except OSError:
                return False
        self.mw._sync_detail_view()
        return True
