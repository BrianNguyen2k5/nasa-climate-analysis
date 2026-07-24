from __future__ import annotations

import copy
import unittest
import uuid
from contextlib import contextmanager, nullcontext
from types import SimpleNamespace
from unittest.mock import Mock, patch

import pandas as pd

from ai_assistant.conversation_state import (
    PROMPT_WIDGET_KEY,
    normalize_messages,
)
from ai_assistant.conversation_view import (
    build_answer_number_map,
    find_latest_assistant_answer_id,
)
from ai_assistant.models import AIResponse
from tabs import tab_6_ai_assistant as ai_tab


class _RerunRequested(Exception):
    pass


class _SessionState(dict):
    def __getattr__(self, name):
        try:
            return self[name]
        except KeyError as error:
            raise AttributeError(name) from error

    def __setattr__(self, name, value) -> None:
        self[name] = value


class _Upload:
    name = "chart.png"

    @staticmethod
    def getvalue() -> bytes:
        return b"fake-image"


class _Placeholder:
    def __init__(self, owner: "_LoadingStreamlit") -> None:
        self.owner = owner
        self.content: list[tuple] = []

    @contextmanager
    def container(self):
        previous_target = self.owner.target
        self.content.clear()
        self.owner.target = self.content
        try:
            yield
        finally:
            self.owner.target = previous_target


class _LoadingStreamlit:
    def __init__(
        self,
        *,
        mode: str,
        image: bool,
        send: bool,
        prompt: str,
        messages: list[dict],
    ) -> None:
        self.mode = mode
        self.image = _Upload() if image else None
        self.send = send
        self.prompt = prompt
        self.session_state = _SessionState(
            {
                "ai_session_id": "session-test",
                "ai_messages": messages,
                PROMPT_WIDGET_KEY: prompt,
            }
        )
        self.placeholder: _Placeholder | None = None
        self.target: list[tuple] | None = None
        self.capture_history = False
        self.history_events: list[tuple] = []
        self.current_role = ""
        self.rerun_count = 0

    @staticmethod
    def tabs(labels):
        return [nullcontext() for _ in labels]

    @staticmethod
    def columns(spec, **_kwargs):
        size = len(spec) if not isinstance(spec, int) else spec
        return [nullcontext() for _ in range(size)]

    def _record(self, event: tuple) -> None:
        if self.target is not None:
            self.target.append(event)
        elif self.capture_history:
            self.history_events.append(event)

    def markdown(self, content: str, **_kwargs) -> None:
        self._record(("markdown", self.current_role, content))

    @staticmethod
    def caption(*_args, **_kwargs) -> None:
        return None

    @staticmethod
    def info(*_args, **_kwargs) -> None:
        return None

    @staticmethod
    def error(*_args, **_kwargs) -> None:
        return None

    @staticmethod
    def code(*_args, **_kwargs) -> None:
        return None

    def segmented_control(self, *_args, **_kwargs):
        return self.mode

    def file_uploader(self, *_args, **_kwargs):
        return self.image

    def text_area(self, *_args, **_kwargs):
        return self.prompt

    def button(self, label, *_args, **_kwargs):
        return self.send and label == "Gửi yêu cầu cho AI"

    def empty(self):
        self.placeholder = _Placeholder(self)
        self.capture_history = True
        return self.placeholder

    @contextmanager
    def chat_message(self, role: str):
        previous_role = self.current_role
        self.current_role = role
        self._record(("chat", role))
        try:
            yield
        finally:
            self.current_role = previous_role

    @contextmanager
    def spinner(self, label: str, **_kwargs):
        self._record(("spinner", label))
        yield

    @contextmanager
    def expander(self, label: str, *, expanded=False, **_kwargs):
        self._record(("expander", label, expanded))
        yield

    def rerun(self) -> None:
        self.rerun_count += 1
        raise _RerunRequested


def completed_turn(name: str) -> list[dict]:
    return [
        {
            "id": f"user-{name}",
            "role": "user",
            "kind": "text",
            "content": f"Prompt {name}",
            "request_id": name,
        },
        {
            "id": f"answer-{name}",
            "role": "assistant",
            "kind": "text",
            "content": f"Answer {name}",
            "request_id": name,
        },
    ]


class ActiveRequestLoadingTests(unittest.TestCase):
    def run_request(
        self,
        *,
        mode: str = "AI gợi ý",
        image: bool = False,
        send: bool = True,
        prompt: str = "Prompt C",
        messages: list[dict] | None = None,
        gemini_result: str = "Kết luận Gemini",
        groq_result: AIResponse | None = None,
        dataset_answer: str | None = None,
        fixed_request_id: uuid.UUID | None = None,
    ):
        fake_st = _LoadingStreamlit(
            mode=mode,
            image=image,
            send=send,
            prompt=prompt,
            messages=messages or [],
        )
        gemini = Mock(return_value=gemini_result)
        groq = Mock(
            return_value=groq_result
            or AIResponse(answer="Câu trả lời Groq")
        )
        append = Mock()
        dataset_qa = Mock(return_value=dataset_answer)
        uuid_patch = (
            patch.object(ai_tab.uuid, "uuid4", return_value=fixed_request_id)
            if fixed_request_id is not None
            else nullcontext()
        )

        with (
            patch.object(ai_tab, "st", fake_st),
            patch.object(
                ai_tab,
                "load_ai_config",
                return_value=SimpleNamespace(),
            ),
            patch.object(
                ai_tab,
                "_load_ai_data_and_context",
                return_value=(pd.DataFrame(), "dataset context", 2),
            ),
            patch.object(ai_tab, "ask_gemini_vision", gemini),
            patch.object(ai_tab, "ask_groq", groq),
            patch.object(ai_tab, "answer_dataset_question", dataset_qa),
            patch.object(ai_tab, "append_message", append),
            patch.object(ai_tab, "_render_history"),
            uuid_patch,
        ):
            if send:
                with self.assertRaises(_RerunRequested):
                    ai_tab.render_ai_assistant_tab()
            else:
                ai_tab.render_ai_assistant_tab()

        return fake_st, gemini, groq, append, dataset_qa

    @staticmethod
    def history_markdown(fake_st: _LoadingStreamlit) -> list[tuple]:
        return [
            event
            for event in fake_st.history_events
            if event[0] == "markdown"
        ]

    def test_01_active_gemini_block_is_visually_before_history(self) -> None:
        old_messages = completed_turn("A") + completed_turn("B")

        fake_st, gemini, groq, _append, _dataset = self.run_request(
            mode="Kết luận chart/dataset",
            image=True,
            prompt="nhận xét biểu đồ",
            messages=old_messages,
        )

        self.assertEqual(
            fake_st.placeholder.content,
            [
                ("chat", "user"),
                ("markdown", "user", "nhận xét biểu đồ"),
                ("spinner", "Gemini Vision đang phân tích ảnh..."),
            ],
        )
        self.assertEqual(
            self.history_markdown(fake_st),
            [
                ("markdown", "user", "Prompt B"),
                ("markdown", "assistant", "Answer B"),
                ("markdown", "user", "Prompt A"),
                ("markdown", "assistant", "Answer A"),
            ],
        )
        gemini.assert_called_once()
        groq.assert_not_called()

    def test_02_active_groq_block_is_visually_before_history(self) -> None:
        fake_st, gemini, groq, _append, _dataset = self.run_request(
            image=False,
            messages=completed_turn("A") + completed_turn("B"),
        )

        self.assertEqual(
            fake_st.placeholder.content[-1],
            ("spinner", "Groq đang xử lý yêu cầu..."),
        )
        self.assertEqual(
            fake_st.placeholder.content[1],
            ("markdown", "user", "Prompt C"),
        )
        gemini.assert_not_called()
        groq.assert_called_once()

    def test_03_active_request_without_history_is_safe(self) -> None:
        fake_st, _gemini, _groq, _append, _dataset = self.run_request()

        self.assertEqual(
            fake_st.placeholder.content,
            [
                ("chat", "user"),
                ("markdown", "user", "Prompt C"),
                ("spinner", "Groq đang xử lý yêu cầu..."),
            ],
        )
        self.assertEqual(fake_st.history_events, [])

    def test_04_active_prompt_is_rendered_only_once(self) -> None:
        fake_st, _gemini, _groq, _append, _dataset = self.run_request(
            messages=completed_turn("A") + completed_turn("B"),
        )

        all_markdown = (
            fake_st.placeholder.content
            + self.history_markdown(fake_st)
        )
        prompt_occurrences = [
            event
            for event in all_markdown
            if event[:2] == ("markdown", "user")
            and event[2] == "Prompt C"
        ]
        self.assertEqual(len(prompt_occurrences), 1)

    def test_05_existing_active_user_is_not_duplicated(self) -> None:
        request_uuid = uuid.UUID("00000000-0000-0000-0000-000000000003")
        request_id = str(request_uuid)
        active_user = {
            "id": "user-C",
            "role": "user",
            "kind": "text",
            "content": "Prompt C",
            "request_id": request_id,
        }
        messages = completed_turn("A") + [active_user]

        fake_st, _gemini, _groq, append, _dataset = self.run_request(
            messages=messages,
            fixed_request_id=request_uuid,
        )

        users = [
            item
            for item in fake_st.session_state.ai_messages
            if item.get("role") == "user"
            and item.get("request_id") == request_id
        ]
        self.assertEqual(len(users), 1)
        self.assertEqual(
            fake_st.placeholder.content[1],
            ("markdown", "user", "Prompt C"),
        )
        self.assertNotIn(
            ("markdown", "user", "Prompt C"),
            self.history_markdown(fake_st),
        )
        persisted_user_calls = [
            call
            for call in append.call_args_list
            if len(call.args) >= 2 and call.args[1] == "user"
        ]
        self.assertEqual(persisted_user_calls, [])

    def test_06_pending_ui_does_not_change_answer_view_state(self) -> None:
        messages = normalize_messages(
            completed_turn("A") + completed_turn("B")
        )
        before = copy.deepcopy(messages)
        numbers_before = build_answer_number_map(messages)
        latest_before = find_latest_assistant_answer_id(messages)

        fake_st, _gemini, _groq, append, _dataset = self.run_request(
            messages=messages,
        )

        completed_messages = [
            item
            for item in fake_st.session_state.ai_messages
            if item.get("request_id") in {"A", "B"}
        ]
        self.assertEqual(completed_messages, before)
        self.assertEqual(
            build_answer_number_map(completed_messages),
            numbers_before,
        )
        self.assertEqual(
            find_latest_assistant_answer_id(completed_messages),
            latest_before,
        )
        persisted_roles = [call.args[1] for call in append.call_args_list]
        self.assertEqual(persisted_roles.count("user"), 1)
        self.assertEqual(persisted_roles.count("assistant"), 1)

    def test_07_final_rerun_removes_pending_and_opens_answer(self) -> None:
        first_run, _gemini, _groq, _append, _dataset = self.run_request(
            messages=completed_turn("A"),
        )
        final_messages = copy.deepcopy(
            first_run.session_state.ai_messages
        )

        final_run, _gemini, _groq, _append, _dataset = self.run_request(
            send=False,
            messages=final_messages,
        )

        self.assertEqual(final_run.placeholder.content, [])
        user_markdown = [
            event[2]
            for event in self.history_markdown(final_run)
            if event[1] == "user"
        ]
        self.assertEqual(user_markdown, ["Prompt C", "Prompt A"])
        expanders = [
            event
            for event in final_run.history_events
            if event[0] == "expander"
        ]
        self.assertEqual(expanders[0][2], True)
        self.assertEqual(expanders[1][2], False)

    def test_08_dataset_qa_keeps_local_routing(self) -> None:
        fake_st, gemini, groq, _append, dataset_qa = self.run_request(
            mode="Thống kê dataset",
            dataset_answer="Kết quả local",
            messages=completed_turn("A"),
        )

        dataset_qa.assert_called_once()
        gemini.assert_not_called()
        groq.assert_not_called()
        assistants = [
            item
            for item in fake_st.session_state.ai_messages
            if item.get("role") == "assistant"
        ]
        self.assertEqual(assistants[-1]["content"], "Kết quả local")

    def test_09_code_proposal_keeps_groq_routing(self) -> None:
        fake_st, gemini, groq, _append, _dataset = self.run_request(
            mode="Sinh chart/code",
            groq_result=AIResponse(
                answer="Đã tạo code",
                code="fig = px.line(df, x='year', y='T2M')",
            ),
        )

        gemini.assert_not_called()
        groq.assert_called_once()
        self.assertEqual(
            fake_st.placeholder.content[-1],
            ("spinner", "Groq đang xử lý yêu cầu..."),
        )
        proposals = [
            item
            for item in fake_st.session_state.ai_messages
            if item.get("kind") == "code_proposal"
        ]
        self.assertEqual(len(proposals), 1)

    def test_10_provider_error_ends_spinner_without_duplicate_answer(
        self,
    ) -> None:
        fake_st = _LoadingStreamlit(
            mode="AI gợi ý",
            image=False,
            send=True,
            prompt="Prompt lỗi",
            messages=completed_turn("A"),
        )
        groq = Mock(side_effect=RuntimeError("provider failed"))
        append = Mock()

        with (
            patch.object(ai_tab, "st", fake_st),
            patch.object(
                ai_tab,
                "load_ai_config",
                return_value=SimpleNamespace(),
            ),
            patch.object(
                ai_tab,
                "_load_ai_data_and_context",
                return_value=(pd.DataFrame(), "dataset context", 2),
            ),
            patch.object(ai_tab, "ask_groq", groq),
            patch.object(ai_tab, "append_message", append),
            patch.object(ai_tab, "_render_history"),
        ):
            with self.assertRaises(RuntimeError):
                ai_tab.render_ai_assistant_tab()

        groq.assert_called_once()
        assistants = [
            item
            for item in fake_st.session_state.ai_messages
            if item.get("role") == "assistant"
            and item.get("request_id")
            not in {"A"}
        ]
        self.assertEqual(assistants, [])
        self.assertEqual(
            fake_st.placeholder.content[-1],
            ("spinner", "Groq đang xử lý yêu cầu..."),
        )
        assistant_persists = [
            call
            for call in append.call_args_list
            if len(call.args) >= 2 and call.args[1] == "assistant"
        ]
        self.assertEqual(assistant_persists, [])


if __name__ == "__main__":
    unittest.main()
