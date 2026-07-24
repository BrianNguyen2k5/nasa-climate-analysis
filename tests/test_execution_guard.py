from __future__ import annotations

import copy
import unittest
from contextlib import contextmanager, nullcontext
from types import SimpleNamespace
from unittest.mock import Mock, patch

import pandas as pd
from fastapi import HTTPException

from ai_assistant.code_runner import (
    ExecutionResult,
    _execute_validated_code,
    execute_chart_code,
)
from ai_assistant.conversation_state import (
    PENDING_APPROVAL,
    SUCCESS,
    create_code_proposal_message,
)
from api import main as api_main
from tabs import tab_6_ai_assistant as ai_tab


VALID_LINE_CODE = """\
df_chart = df.groupby("year")["T2M"].mean().reset_index()
fig = px.line(df_chart, x="year", y="T2M")
fig.update_layout(title="Nhiệt độ trung bình")
"""


def runner_df() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "year": [2020, 2021],
            "T2M": [24.0, 25.0],
        }
    )


class SharedExecutionGuardTests(unittest.TestCase):
    def test_01_valid_code_reaches_execution_once(self) -> None:
        with patch(
            "ai_assistant.code_runner._execute_validated_code",
            wraps=_execute_validated_code,
        ) as execute:
            result = execute_chart_code(VALID_LINE_CODE, runner_df())

        self.assertTrue(result.ok, result.message)
        self.assertIsNotNone(result.fig_json)
        execute.assert_called_once()

    def test_02_output_and_ui_calls_never_reach_execution(self) -> None:
        cases = {
            "fig.show": (
                "\nfig.show()\n",
                "forbidden_output_call",
            ),
            "print": (
                "\nprint(fig)\n",
                "forbidden_output_call",
            ),
            "display": (
                "\ndisplay(fig)\n",
                "forbidden_output_call",
            ),
            "st.plotly_chart": (
                "\nst.plotly_chart(fig)\n",
                "forbidden_namespace",
            ),
            "st.pyplot": (
                "\nst.pyplot(fig)\n",
                "forbidden_namespace",
            ),
            "plt.show": (
                "\nplt.show()\n",
                "forbidden_output_call",
            ),
        }
        for name, (suffix, expected_reason) in cases.items():
            with self.subTest(name=name):
                with patch(
                    "ai_assistant.code_runner._execute_validated_code"
                ) as execute:
                    result = execute_chart_code(
                        VALID_LINE_CODE + suffix,
                        runner_df(),
                    )
                self.assertFalse(result.ok)
                self.assertEqual(
                    result.validation_reason,
                    expected_reason,
                )
                execute.assert_not_called()

    def test_03_invalid_structure_never_reaches_execution(self) -> None:
        cases = {
            "import": (
                "import streamlit as st\n" + VALID_LINE_CODE,
                "import_not_allowed",
            ),
            "unknown root": (
                'fig = sns.lineplot(data=df, x="year", y="T2M")',
                "unknown_runtime_name",
            ),
            "missing fig": (
                'df_chart = df.groupby("year")["T2M"].mean()',
                "missing_fig",
            ),
        }
        for name, (code, expected_reason) in cases.items():
            with self.subTest(name=name):
                with patch(
                    "ai_assistant.code_runner._execute_validated_code"
                ) as execute:
                    result = execute_chart_code(code, runner_df())
                self.assertFalse(result.ok)
                self.assertEqual(
                    result.validation_reason,
                    expected_reason,
                )
                execute.assert_not_called()

    def test_04_supported_plotly_variants_execute(self) -> None:
        variants = {
            "px.bar": VALID_LINE_CODE.replace("px.line", "px.bar"),
            "go.Figure": """\
df_chart = df.groupby("year")["T2M"].mean().reset_index()
fig = go.Figure(
    data=[go.Bar(x=df_chart["year"], y=df_chart["T2M"])]
)
fig.update_layout(title="Nhiệt độ trung bình")
""",
        }
        for name, code in variants.items():
            with self.subTest(name=name):
                result = execute_chart_code(code, runner_df())
                self.assertTrue(result.ok, result.message)
                self.assertIsNotNone(result.fig_json)

    def test_05_every_proposal_source_uses_the_same_guard(self) -> None:
        sources = (
            "generated proposal",
            "AI-edited proposal",
            "manual editor",
            "persisted proposal",
            "reloaded proposal",
        )
        for source in sources:
            with self.subTest(source=source):
                with patch(
                    "ai_assistant.code_runner._execute_validated_code"
                ) as execute:
                    result = execute_chart_code(
                        VALID_LINE_CODE + "\nfig.show()\n",
                        runner_df(),
                    )
                self.assertEqual(
                    result.validation_reason,
                    "forbidden_output_call",
                )
                execute.assert_not_called()

    def test_06_validation_messages_are_reason_specific(self) -> None:
        cases = {
            "\nfig.show()\n": ("fig.show", "tự hiển thị"),
            "\nprint(fig)\n": ("print()", "môi trường local"),
            "\nst.plotly_chart(fig)\n": ("namespace `st`", "biến `fig`"),
        }
        for suffix, expected_fragments in cases.items():
            with self.subTest(suffix=suffix):
                result = execute_chart_code(
                    VALID_LINE_CODE + suffix,
                    runner_df(),
                )
                for fragment in expected_fragments:
                    self.assertIn(fragment, result.message)

        import_result = execute_chart_code(
            "import streamlit as st\n" + VALID_LINE_CODE,
            runner_df(),
        )
        self.assertIn("`import`", import_result.message)
        self.assertIn("`df`", import_result.message)


class _FakeStreamlit:
    def __init__(self, proposal: dict, editor_code: str) -> None:
        self.session_state = SimpleNamespace(ai_messages=[proposal])
        self.editor_code = editor_code
        self.events: list[str] = []
        self.warnings: list[str] = []
        self.rerun = Mock()

    @staticmethod
    def markdown(*_args, **_kwargs) -> None:
        return None

    @staticmethod
    def caption(*_args, **_kwargs) -> None:
        return None

    def text_area(self, *_args, **_kwargs) -> str:
        return self.editor_code

    @staticmethod
    def text_input(*_args, **_kwargs) -> str:
        return ""

    @staticmethod
    def columns(spec):
        return [nullcontext() for _ in spec]

    @staticmethod
    def button(label, *_args, **_kwargs) -> bool:
        return label == "Chấp nhận & chạy"

    @contextmanager
    def spinner(self, *_args, **_kwargs):
        self.events.append("spinner")
        yield

    def warning(self, message: str) -> None:
        self.events.append("warning")
        self.warnings.append(message)


class ExecutionButtonGuardTests(unittest.TestCase):
    def run_review(
        self,
        proposal: dict,
        editor_code: str,
        execution_result: ExecutionResult | None = None,
    ):
        fake_st = _FakeStreamlit(proposal, editor_code)
        persist = Mock()
        execute = Mock(
            return_value=execution_result
            or ExecutionResult(
                True,
                "Thực thi thành công trên dữ liệu local.",
                fig_json={"data": [], "layout": {}},
            )
        )
        with (
            patch.object(ai_tab, "st", fake_st),
            patch.object(ai_tab, "_persist_active_messages", persist),
            patch.object(ai_tab, "execute_chart_code", execute),
        ):
            ai_tab._render_code_review(
                proposal["id"],
                runner_df(),
                SimpleNamespace(),
                "dataset context",
            )
        return fake_st, persist, execute

    def test_07_invalid_editor_code_is_blocked_before_spinner(self) -> None:
        invalid_cases = (
            VALID_LINE_CODE + "\nfig.show()\n",
            VALID_LINE_CODE + "\nprint(fig)\n",
            VALID_LINE_CODE + "\nst.plotly_chart(fig)\n",
        )
        for editor_code in invalid_cases:
            with self.subTest(editor_code=editor_code[-30:]):
                proposal = create_code_proposal_message(
                    "Code ban đầu",
                    VALID_LINE_CODE,
                )
                before = copy.deepcopy(proposal)
                fake_st, persist, execute = self.run_review(
                    proposal,
                    editor_code,
                )

                self.assertEqual(proposal, before)
                self.assertEqual(fake_st.events, ["warning"])
                self.assertEqual(len(fake_st.warnings), 1)
                persist.assert_not_called()
                execute.assert_not_called()
                fake_st.rerun.assert_not_called()

    def test_08_invalid_run_preserves_existing_result_and_timeline(self) -> None:
        proposal = create_code_proposal_message(
            "Code ban đầu",
            VALID_LINE_CODE,
        )
        proposal.update(
            {
                "status": PENDING_APPROVAL,
                "result": {"old": True},
                "executed_code": "old executed code",
                "revision": 7,
            }
        )
        before = copy.deepcopy(proposal)

        fake_st, persist, execute = self.run_review(
            proposal,
            VALID_LINE_CODE + "\nfig.show()\n",
        )

        self.assertEqual(proposal, before)
        self.assertEqual(len(fake_st.session_state.ai_messages), 1)
        persist.assert_not_called()
        execute.assert_not_called()
        fake_st.rerun.assert_not_called()

    def test_09_valid_run_keeps_existing_success_flow(self) -> None:
        proposal = create_code_proposal_message(
            "Code ban đầu",
            VALID_LINE_CODE,
        )

        fake_st, persist, execute = self.run_review(
            proposal,
            VALID_LINE_CODE,
        )

        self.assertEqual(fake_st.events, ["spinner"])
        self.assertEqual(fake_st.warnings, [])
        execute.assert_called_once_with(VALID_LINE_CODE, unittest.mock.ANY)
        self.assertEqual(proposal["status"], SUCCESS)
        self.assertEqual(proposal["executed_code"], VALID_LINE_CODE)
        self.assertIsNotNone(proposal["result"])
        self.assertEqual(persist.call_count, 2)
        fake_st.rerun.assert_called_once()


class APIExecutionBoundaryTests(unittest.TestCase):
    def test_10_api_execute_uses_shared_runner_boundary(self) -> None:
        request = api_main.ExecuteRequest(
            prompt="Vẽ biểu đồ",
            original_code=VALID_LINE_CODE,
            approved_code=VALID_LINE_CODE,
        )
        guarded_result = ExecutionResult(
            True,
            "Thực thi thành công trên dữ liệu local.",
            fig_json={"data": [{"type": "scatter"}]},
        )
        with (
            patch.object(api_main, "load_dataset", return_value=runner_df()),
            patch.object(
                api_main,
                "execute_chart_code",
                return_value=guarded_result,
            ) as execute,
            patch.object(api_main, "write_log_entry") as write_log,
        ):
            response = api_main.execute_code(request)

        execute.assert_called_once_with(request.approved_code, unittest.mock.ANY)
        write_log.assert_called_once()
        self.assertEqual(response["status"], "success")
        self.assertEqual(response["fig_json"], guarded_result.fig_json)

    def test_11_api_invalid_code_returns_guard_message(self) -> None:
        request = api_main.ExecuteRequest(
            prompt="Vẽ biểu đồ",
            original_code=VALID_LINE_CODE,
            approved_code=VALID_LINE_CODE + "\nfig.show()\n",
        )
        guarded_result = ExecutionResult(
            False,
            "Không thể chạy code vì `fig.show()` không được hỗ trợ.",
            validation_reason="forbidden_output_call",
            validation_detail="fig.show",
        )
        with (
            patch.object(api_main, "load_dataset", return_value=runner_df()),
            patch.object(
                api_main,
                "execute_chart_code",
                return_value=guarded_result,
            ) as execute,
            patch.object(api_main, "write_log_entry") as write_log,
        ):
            with self.assertRaises(HTTPException) as raised:
                api_main.execute_code(request)

        execute.assert_called_once()
        write_log.assert_called_once()
        self.assertIn("fig.show", raised.exception.detail)


if __name__ == "__main__":
    unittest.main()
