from __future__ import annotations

import unittest
from contextlib import nullcontext
from types import SimpleNamespace
from unittest.mock import Mock, patch

import pandas as pd

from ai_assistant.conversation_state import PROMPT_WIDGET_KEY
from ai_assistant.models import (
    AIResponse,
    INVALID_MODEL_RESPONSE_MESSAGE,
    parse_model_response,
    sanitize_ai_response,
    sanitize_model_text,
    sanitize_structured_response_data,
)
from tabs import tab_6_ai_assistant as ai_tab


class ModelResponseHygieneTests(unittest.TestCase):
    def assert_safe_invalid(self, raw: str) -> None:
        response = parse_model_response(raw)

        self.assertEqual(response.answer, INVALID_MODEL_RESPONSE_MESSAGE)
        self.assertNotIn(raw, response.answer)
        self.assertNotIn("secret", response.answer.lower())
        self.assertNotIn("<think", response.answer.lower())

    def test_01_closed_think_before_json_is_removed(self) -> None:
        response = parse_model_response(
            '<think>secret</think>{"answer":"final","code":""}'
        )

        self.assertEqual(response.answer, "final")
        self.assertEqual(response.code, "")

    def test_02_unclosed_think_is_invalid(self) -> None:
        self.assert_safe_invalid("<think>secret reasoning continues...")

    def test_03_reasoning_tags_are_case_insensitive_and_all_blocks_are_removed(
        self,
    ) -> None:
        raw = (
            "<THINK>secret one</think>"
            "<Analysis>secret two</ANALYSIS>"
            '{"answer":"final","code":""}'
        )

        self.assertEqual(
            sanitize_model_text(raw),
            '{"answer":"final","code":""}',
        )
        self.assertEqual(parse_model_response(raw).answer, "final")

    def test_04_think_inside_answer_is_removed(self) -> None:
        response = parse_model_response(
            '{"answer":"<think>secret</think>final","code":""}'
        )

        self.assertEqual(response.answer, "final")

    def test_05_think_inside_code_is_removed(self) -> None:
        response = parse_model_response(
            '{"answer":"ok","code":"<think>secret</think>fig = px.bar(...)"}'
        )

        self.assertEqual(response.code, "fig = px.bar(...)")
        self.assertNotIn("secret", response.code)

    def test_06_every_structured_model_field_is_sanitized(self) -> None:
        sanitized = sanitize_structured_response_data(
            {
                "answer": "<think>secret</think>answer",
                "code": "<think>secret</think>fig = 1",
                "explanation": "<reasoning>secret</reasoning>explanation",
                "chart_title": "<analysis>secret</analysis>title",
                "suggestions": [
                    "<scratchpad>secret</scratchpad>suggestion",
                    "<think>unclosed",
                ],
            }
        )

        self.assertEqual(sanitized["answer"], "answer")
        self.assertEqual(sanitized["code"], "fig = 1")
        self.assertEqual(sanitized["explanation"], "explanation")
        self.assertEqual(sanitized["chart_title"], "title")
        self.assertEqual(sanitized["suggestions"], ["suggestion"])

    def test_07_braces_inside_reasoning_cannot_be_selected_as_json(self) -> None:
        response = parse_model_response(
            '<think>{"fake":"json"} code {x:1}</think>'
            '{"answer":"final","code":""}'
        )

        self.assertEqual(response.answer, "final")

    def test_08_prose_before_valid_json_does_not_become_an_answer(self) -> None:
        response = parse_model_response(
            'Đây là kết quả:\n{"answer":"final","code":""}'
        )

        self.assertEqual(response.answer, "final")

    def test_09_malformed_json_is_not_used_as_raw_answer(self) -> None:
        self.assert_safe_invalid('{"answer":"final","code":')

    def test_10_alternate_schema_is_rejected(self) -> None:
        responses = [
            parse_model_response('{"python_code":"fig = px.bar(...)"}'),
            parse_model_response(
                '{"result":{"answer":"final","code":"fig = px.bar(...)"}}'
            ),
        ]

        for response in responses:
            self.assertEqual(response.answer, INVALID_MODEL_RESPONSE_MESSAGE)
            self.assertNotIn("python_code", response.answer)

    def test_11_reasoning_only_response_is_invalid(self) -> None:
        self.assert_safe_invalid("<think>Analyze User Request...</think>")

    def test_12_unclosed_reasoning_with_braces_is_invalid(self) -> None:
        self.assert_safe_invalid('<think>Analyze {"fake":"json"}')

    def test_13_last_response_boundary_replaces_reasoning_only_fields(self) -> None:
        response = sanitize_ai_response(
            AIResponse(
                answer="<think>secret</think>",
                code="",
                chart_title="<analysis>secret title</analysis>",
                suggestions=["<scratchpad>secret suggestion</scratchpad>"],
            )
        )

        self.assertEqual(response.answer, INVALID_MODEL_RESPONSE_MESSAGE)
        self.assertEqual(response.chart_title, "")
        self.assertEqual(response.suggestions, [])


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


class _FakeStreamlit:
    def __init__(self, mode: str, *, image: bool) -> None:
        self.mode = mode
        self.image = _Upload() if image else None
        self.session_state = _SessionState(
            {
                "ai_session_id": "session-test",
                "ai_messages": [],
                PROMPT_WIDGET_KEY: "Hãy phân tích",
            }
        )
        self.rerun_count = 0

    @staticmethod
    def tabs(labels):
        return [nullcontext() for _ in labels]

    @staticmethod
    def columns(spec, **_kwargs):
        size = len(spec) if not isinstance(spec, int) else spec
        return [nullcontext() for _ in range(size)]

    @staticmethod
    def markdown(*_args, **_kwargs) -> None:
        return None

    @staticmethod
    def caption(*_args, **_kwargs) -> None:
        return None

    def segmented_control(self, *_args, **_kwargs):
        return self.mode

    def file_uploader(self, *_args, **_kwargs):
        return self.image

    def text_area(self, *_args, **_kwargs):
        return self.session_state[PROMPT_WIDGET_KEY]

    @staticmethod
    def spinner(*_args, **_kwargs):
        return nullcontext()

    @staticmethod
    def chat_message(*_args, **_kwargs):
        return nullcontext()

    @staticmethod
    def expander(*_args, **_kwargs):
        return nullcontext()

    def button(self, label, *_args, **_kwargs):
        return label == "Gửi yêu cầu cho AI"

    def rerun(self) -> None:
        self.rerun_count += 1
        raise _RerunRequested


class SingleAnswerRoutingTests(unittest.TestCase):
    def run_request(
        self,
        *,
        mode: str,
        image: bool,
        gemini_result: str = "Kết luận Gemini",
        groq_result: AIResponse | None = None,
    ):
        fake_st = _FakeStreamlit(mode, image=image)
        gemini = Mock(return_value=gemini_result)
        groq = Mock(return_value=groq_result or AIResponse(answer="Kết luận Groq"))
        append = Mock()

        with (
            patch.object(ai_tab, "st", fake_st),
            patch.object(ai_tab, "load_ai_config", return_value=SimpleNamespace()),
            patch.object(
                ai_tab,
                "_load_ai_data_and_context",
                return_value=(pd.DataFrame(), "dataset context", 2),
            ),
            patch.object(ai_tab, "ask_gemini_vision", gemini),
            patch.object(ai_tab, "ask_groq", groq),
            patch.object(ai_tab, "append_message", append),
            patch.object(ai_tab, "_render_history"),
        ):
            with self.assertRaises(_RerunRequested):
                ai_tab.render_ai_assistant_tab()

        return fake_st, gemini, groq, append

    @staticmethod
    def assistant_messages(fake_st: _FakeStreamlit) -> list[dict]:
        return [
            message
            for message in fake_st.session_state.ai_messages
            if message.get("role") == "assistant"
        ]

    def test_14_image_conclusion_uses_only_gemini_and_one_final_message(self) -> None:
        fake_st, gemini, groq, append = self.run_request(
            mode="Kết luận chart/dataset",
            image=True,
        )

        gemini.assert_called_once()
        groq.assert_not_called()
        assistant_messages = self.assistant_messages(fake_st)
        self.assertEqual(len(assistant_messages), 1)
        self.assertEqual(assistant_messages[0]["content"], "Kết luận Gemini")
        self.assertEqual(assistant_messages[0]["source"], "gemini_vision")
        request_id = assistant_messages[0]["request_id"]
        self.assertTrue(request_id)
        same_request = [
            message
            for message in fake_st.session_state.ai_messages
            if message.get("request_id") == request_id
            and message.get("role") == "assistant"
        ]
        self.assertEqual(len(same_request), 1)
        assistant_persists = [
            call
            for call in append.call_args_list
            if len(call.args) >= 2 and call.args[1] == "assistant"
        ]
        self.assertEqual(len(assistant_persists), 1)
        self.assertEqual(fake_st.rerun_count, 1)

        rendered = Mock()
        with (
            patch.object(ai_tab, "st", fake_st),
            patch.object(ai_tab, "_render_ai_response_detail", rendered),
        ):
            ai_tab._render_messages(
                pd.DataFrame(),
                SimpleNamespace(),
                "dataset context",
            )
        rendered.assert_called_once()

    def test_15_image_conclusion_error_does_not_fall_through_or_leak_raw(
        self,
    ) -> None:
        fake_st, gemini, groq, _append = self.run_request(
            mode="Kết luận chart/dataset",
            image=True,
            gemini_result="<think>secret provider exception",
        )

        gemini.assert_called_once()
        groq.assert_not_called()
        assistant_messages = self.assistant_messages(fake_st)
        self.assertEqual(len(assistant_messages), 1)
        self.assertIn("không chứa nội dung an toàn", assistant_messages[0]["content"])
        self.assertNotIn("secret", assistant_messages[0]["content"])

    def test_16_conclusion_without_image_keeps_groq_flow(self) -> None:
        fake_st, gemini, groq, _append = self.run_request(
            mode="Kết luận chart/dataset",
            image=False,
        )

        gemini.assert_not_called()
        groq.assert_called_once()
        assistant_messages = self.assistant_messages(fake_st)
        self.assertEqual(len(assistant_messages), 1)
        self.assertEqual(assistant_messages[0]["content"], "Kết luận Groq")
        self.assertEqual(assistant_messages[0]["source"], "groq")

    def test_17_full_code_response_still_creates_one_code_proposal(self) -> None:
        fake_st, gemini, groq, _append = self.run_request(
            mode="Sinh chart/code",
            image=False,
            groq_result=AIResponse(
                answer="Đã tạo chart.",
                code="fig = px.bar(df, x='region', y='T2M')",
                chart_title="Nhiệt độ",
            ),
        )

        gemini.assert_not_called()
        groq.assert_called_once()
        assistant_messages = self.assistant_messages(fake_st)
        self.assertEqual(len(assistant_messages), 1)
        self.assertEqual(assistant_messages[0]["kind"], "code_proposal")
        self.assertIn("fig = px.bar", assistant_messages[0]["current_code"])

    def test_18_intermediate_image_output_is_not_appended_before_groq(self) -> None:
        fake_st, gemini, groq, _append = self.run_request(
            mode="AI gợi ý",
            image=True,
            gemini_result="Phân tích ảnh trung gian",
            groq_result=AIResponse(answer="Câu trả lời cuối"),
        )

        gemini.assert_called_once()
        groq.assert_called_once()
        assistant_messages = self.assistant_messages(fake_st)
        self.assertEqual(len(assistant_messages), 1)
        self.assertEqual(assistant_messages[0]["content"], "Câu trả lời cuối")
        self.assertNotIn(
            "Phân tích ảnh trung gian",
            [message["content"] for message in assistant_messages],
        )


if __name__ == "__main__":
    unittest.main()
