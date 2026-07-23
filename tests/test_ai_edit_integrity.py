from __future__ import annotations

import copy
import json
import sys
import unittest
from contextlib import nullcontext
from types import SimpleNamespace
from unittest.mock import Mock, patch

from ai_assistant.code_sanitizer import (
    INCOMPLETE_AI_EDIT_MESSAGE,
    UNCHANGED_AI_EDIT_MESSAGE,
    sanitize_generated_code,
    validate_ai_edit_candidate,
)
from ai_assistant.conversation_state import (
    PENDING_APPROVAL,
    SUCCESS,
    apply_ai_edit_response,
    create_code_proposal_message,
)
from ai_assistant.models import AIResponse, ask_groq
from tabs import tab_6_ai_assistant as ai_tab


SOURCE_CODE = """\
df_filtered = df[df["location_name"] == "Ha Noi"]
df_chart = df_filtered.groupby("year")["T2M"].mean().reset_index()
fig = px.line(df_chart, x="year", y="T2M")
fig.update_layout(title="MANUAL TITLE")
"""

VALID_EDIT = """\
df_filtered = df[df["location_name"] == "Ha Noi"]
df_chart = df_filtered.groupby("year")["T2M"].mean().reset_index()
fig = px.bar(df_chart, x="year", y="T2M")
fig.update_layout(title="MANUAL TITLE")
"""


class AIEditCandidateValidationTests(unittest.TestCase):
    def test_01_empty_and_whitespace_are_rejected(self) -> None:
        for candidate in ("", "   ", "\n\t"):
            with self.subTest(candidate=repr(candidate)):
                result = validate_ai_edit_candidate(SOURCE_CODE, candidate)
                self.assertFalse(result.valid)
                self.assertEqual(result.reason, "empty")
                self.assertEqual(result.message, INCOMPLETE_AI_EDIT_MESSAGE)

    def test_02_ascii_and_unicode_ellipsis_are_rejected(self) -> None:
        for candidate in ("...", "…", "df_filtered = ..."):
            with self.subTest(candidate=candidate):
                result = validate_ai_edit_candidate(SOURCE_CODE, candidate)
                self.assertFalse(result.valid)
                self.assertEqual(result.reason, "placeholder")

    def test_03_fenced_ellipsis_is_rejected_after_sanitize(self) -> None:
        candidate = sanitize_generated_code("```python\n...\n```")

        self.assertEqual(candidate, "...")
        self.assertEqual(
            validate_ai_edit_candidate(SOURCE_CODE, candidate).reason,
            "placeholder",
        )

    def test_04_comment_only_and_pass_are_rejected(self) -> None:
        candidates = (
            "# phần code hoàn chỉnh sẽ đặt ở đây",
            "# ...",
            "pass",
        )

        for candidate in candidates:
            with self.subTest(candidate=candidate):
                result = validate_ai_edit_candidate(SOURCE_CODE, candidate)
                self.assertFalse(result.valid)
                self.assertIn(result.reason, {"fragment", "placeholder"})

    def test_05_placeholder_phrases_are_rejected(self) -> None:
        candidates = (
            "fig = px.line(df)\n# rest of the code",
            "fig = px.line(df)\n# rest unchanged",
            "fig = px.line(df)\n# same as above",
            "fig = px.line(df)\n# phần còn lại giữ nguyên",
        )

        for candidate in candidates:
            with self.subTest(candidate=candidate):
                result = validate_ai_edit_candidate(SOURCE_CODE, candidate)
                self.assertFalse(result.valid)
                self.assertEqual(result.reason, "placeholder")

    def test_06_syntax_invalid_candidate_is_rejected(self) -> None:
        result = validate_ai_edit_candidate(
            SOURCE_CODE,
            "if True\n    fig = px.line(df)",
        )

        self.assertFalse(result.valid)
        self.assertEqual(result.reason, "syntax_invalid")

    def test_07_candidate_missing_fig_assignment_is_rejected(self) -> None:
        candidate = """\
df_filtered = df[df["location_name"] == "Ha Noi"]
df_chart = df_filtered.groupby("year")["T2M"].mean().reset_index()
chart = px.bar(df_chart, x="year", y="T2M")
chart.update_layout(title="MANUAL TITLE")
"""

        result = validate_ai_edit_candidate(SOURCE_CODE, candidate)

        self.assertFalse(result.valid)
        self.assertEqual(result.reason, "missing_required_structure")

    def test_08_short_code_fragment_is_rejected_even_when_it_assigns_fig(
        self,
    ) -> None:
        result = validate_ai_edit_candidate(
            SOURCE_CODE,
            'fig = px.bar(df, x="year", y="T2M")',
        )

        self.assertFalse(result.valid)
        self.assertEqual(result.reason, "fragment")

    def test_09_unchanged_code_ignores_formatting_and_comments(self) -> None:
        candidate = """\
# formatting-only edit
df_filtered=df[df["location_name"]=="Ha Noi"]
df_chart=df_filtered.groupby("year")["T2M"].mean().reset_index()
fig=px.line(df_chart,x="year",y="T2M")
fig.update_layout(title="MANUAL TITLE")
"""

        result = validate_ai_edit_candidate(SOURCE_CODE, candidate)

        self.assertFalse(result.valid)
        self.assertEqual(result.reason, "unchanged")
        self.assertEqual(result.message, UNCHANGED_AI_EDIT_MESSAGE)

    def test_10_unsafe_candidate_is_rejected_before_state_mutation(self) -> None:
        candidate = VALID_EDIT + '\ncontent = open("secret.txt").read()\n'

        result = validate_ai_edit_candidate(SOURCE_CODE, candidate)

        self.assertFalse(result.valid)
        self.assertEqual(result.reason, "unsafe_or_invalid")

    def test_11_complete_changed_program_is_valid(self) -> None:
        result = validate_ai_edit_candidate(SOURCE_CODE, VALID_EDIT)

        self.assertTrue(result.valid)
        self.assertEqual(result.reason, "valid")


class AIEditStateIntegrityTests(unittest.TestCase):
    def proposal_with_execution_state(self) -> dict:
        proposal = create_code_proposal_message("Code ban đầu", SOURCE_CODE)
        proposal.update(
            {
                "status": SUCCESS,
                "result": {"fig_json": {"data": [], "layout": {}}},
                "error": "old error",
                "conclusion": "old conclusion",
                "executed_code": SOURCE_CODE,
                "executed_code_hash": "old hash",
                "revision": 3,
                "edit_history": [{"answer": "old edit"}],
            }
        )
        return proposal

    def test_12_every_invalid_candidate_preserves_the_entire_proposal(self) -> None:
        candidates = (
            "",
            "...",
            "…",
            "# ... rest of the code ...",
            "df_filtered = ...",
            "pass",
            "# comment only",
            'fig = px.bar(df, x="year", y="T2M")',
            SOURCE_CODE,
        )

        for candidate in candidates:
            with self.subTest(candidate=candidate):
                proposal = self.proposal_with_execution_state()
                messages = [proposal]
                before = copy.deepcopy(proposal)

                returned, applied = apply_ai_edit_response(
                    messages,
                    proposal["id"],
                    candidate,
                    edit_instruction="Sửa biểu đồ",
                    edit_answer="AI nói đã sửa.",
                    source_code=SOURCE_CODE,
                )

                self.assertFalse(applied)
                self.assertIs(returned, proposal)
                self.assertEqual(proposal, before)

    def test_13_valid_candidate_updates_once_and_clears_execution_state(
        self,
    ) -> None:
        proposal = self.proposal_with_execution_state()
        messages = [proposal]

        updated, applied = apply_ai_edit_response(
            messages,
            proposal["id"],
            VALID_EDIT,
            edit_instruction="Đổi line thành bar",
            edit_answer="Đã đổi loại biểu đồ.",
            source_code=SOURCE_CODE,
        )

        self.assertTrue(applied)
        self.assertEqual(updated["current_code"], VALID_EDIT.strip())
        self.assertEqual(updated["code"], VALID_EDIT.strip())
        self.assertEqual(updated["revision"], 4)
        self.assertEqual(updated["status"], PENDING_APPROVAL)
        self.assertIsNone(updated["result"])
        self.assertIsNone(updated["error"])
        self.assertIsNone(updated["executed_code"])
        self.assertEqual(len(updated["edit_history"]), 2)

    def test_14_manual_editor_source_controls_unchanged_detection(self) -> None:
        canonical_code = SOURCE_CODE.replace("MANUAL TITLE", "Tiêu đề cũ")
        proposal = create_code_proposal_message("Code ban đầu", canonical_code)
        messages = [proposal]
        before = copy.deepcopy(proposal)

        _, applied = apply_ai_edit_response(
            messages,
            proposal["id"],
            SOURCE_CODE,
            edit_instruction="Sửa phần khác",
            edit_answer="AI nói đã sửa.",
            source_code=SOURCE_CODE,
        )

        self.assertFalse(applied)
        self.assertEqual(proposal, before)


class AIEditPromptContractTests(unittest.TestCase):
    def test_15_edit_request_sends_full_source_and_full_code_contract(self) -> None:
        captured: dict = {}

        class FakeCompletions:
            @staticmethod
            def create(**kwargs):
                captured.update(kwargs)
                content = json.dumps(
                    {
                        "answer": "Đã sửa.",
                        "code": VALID_EDIT,
                        "chart_title": "",
                        "suggestions": [],
                    },
                    ensure_ascii=False,
                )
                return SimpleNamespace(
                    choices=[
                        SimpleNamespace(
                            message=SimpleNamespace(content=content),
                        )
                    ]
                )

        class FakeGroq:
            def __init__(self, api_key: str) -> None:
                self.api_key = api_key
                self.chat = SimpleNamespace(
                    completions=FakeCompletions(),
                )

        config = SimpleNamespace(
            groq_api_key="test-key",
            groq_api_key_backup=None,
            groq_primary_model="primary-model",
            groq_backup_model="backup-model",
            groq_code_model="code-model",
        )
        fake_module = SimpleNamespace(Groq=FakeGroq)

        with patch.dict(sys.modules, {"groq": fake_module}):
            response = ask_groq(
                config,
                "Đổi line thành bar",
                "dataset context",
                "Sửa code",
                code_input=SOURCE_CODE,
            )

        self.assertEqual(response.code, VALID_EDIT.strip())
        system_prompt = captured["messages"][0]["content"]
        user_prompt = captured["messages"][1]["content"]
        self.assertIn("TOÀN BỘ chương trình Python", system_prompt)
        self.assertIn("Không trả diff hoặc patch", system_prompt)
        self.assertIn("phần còn lại giữ nguyên", system_prompt)
        self.assertIn(SOURCE_CODE, user_prompt)
        self.assertIn("Đổi line thành bar", user_prompt)


class AIEditUIBoundaryTests(unittest.TestCase):
    def test_16_invalid_edit_warns_without_persist_or_rerun(self) -> None:
        proposal = create_code_proposal_message("Code ban đầu", SOURCE_CODE)
        before = copy.deepcopy(proposal)

        class FakeStreamlit:
            def __init__(self) -> None:
                self.session_state = SimpleNamespace(ai_messages=[proposal])
                self.warnings: list[str] = []
                self.rerun = Mock()

            @staticmethod
            def markdown(*_args, **_kwargs) -> None:
                return None

            @staticmethod
            def caption(*_args, **_kwargs) -> None:
                return None

            @staticmethod
            def text_area(*_args, **_kwargs) -> str:
                return SOURCE_CODE

            @staticmethod
            def text_input(*_args, **_kwargs) -> str:
                return "Đổi line thành bar"

            @staticmethod
            def columns(spec):
                return [nullcontext() for _ in spec]

            @staticmethod
            def spinner(*_args, **_kwargs):
                return nullcontext()

            @staticmethod
            def button(label, *_args, **_kwargs) -> bool:
                return label == "Nhờ AI sửa code"

            def warning(self, message: str) -> None:
                self.warnings.append(message)

        fake_st = FakeStreamlit()
        persist = Mock()

        with (
            patch.object(ai_tab, "st", fake_st),
            patch.object(
                ai_tab,
                "ask_groq",
                return_value=AIResponse(
                    answer="Đã sửa code.",
                    code="...",
                ),
            ),
            patch.object(ai_tab, "_persist_active_messages", persist),
        ):
            ai_tab._render_code_review(
                proposal["id"],
                None,
                SimpleNamespace(),
                "dataset context",
            )

        self.assertEqual(proposal, before)
        self.assertEqual(fake_st.warnings, [INCOMPLETE_AI_EDIT_MESSAGE])
        persist.assert_not_called()
        fake_st.rerun.assert_not_called()


if __name__ == "__main__":
    unittest.main()
