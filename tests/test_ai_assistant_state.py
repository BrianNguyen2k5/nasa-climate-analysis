from __future__ import annotations

import unittest

from ai_assistant import constants, data_context, dataset_qa
from ai_assistant.conversation_state import (
    APPROVED_AND_EXECUTING,
    PENDING_APPROVAL,
    SUCCESS,
    attach_execution_result,
    code_sha256,
    create_code_proposal_message,
    mark_proposal_approved,
    normalize_message,
    reset_ai_transient_state,
    update_proposal_code,
)


class AIAssistantStateTests(unittest.TestCase):
    def test_01_two_proposals_are_independent(self) -> None:
        proposal_a = create_code_proposal_message("A", "fig = code_a")
        proposal_b = create_code_proposal_message("B", "fig = code_b")
        messages = [proposal_a, proposal_b]

        self.assertNotEqual(proposal_a["id"], proposal_b["id"])
        self.assertNotEqual(proposal_a["current_code"], proposal_b["current_code"])

        update_proposal_code(messages, proposal_b["id"], "fig = edited_b")

        self.assertEqual(proposal_a["current_code"], "fig = code_a")
        self.assertEqual(proposal_b["current_code"], "fig = edited_b")
        self.assertIsNone(proposal_a["result"])
        self.assertIsNone(proposal_b["result"])

    def test_02_ai_edit_resets_only_proposal_b_and_increments_revision(self) -> None:
        proposal_a = create_code_proposal_message("A", "fig = code_a")
        proposal_b = create_code_proposal_message("B", "fig = old_b")
        messages = [proposal_a, proposal_b]
        proposal_b.update(
            {
                "status": SUCCESS,
                "result": {"old": True},
                "error": "old error",
                "conclusion": "old conclusion",
            }
        )

        update_proposal_code(
            messages,
            proposal_b["id"],
            "fig = new_b",
            edit_instruction="Sửa B",
            increment_revision=True,
        )

        self.assertEqual(proposal_a["current_code"], "fig = code_a")
        self.assertEqual(proposal_a["revision"], 1)
        self.assertEqual(proposal_b["current_code"], "fig = new_b")
        self.assertEqual(proposal_b["revision"], 2)
        self.assertEqual(proposal_b["status"], PENDING_APPROVAL)
        self.assertIsNone(proposal_b["result"])
        self.assertIsNone(proposal_b["error"])
        self.assertIsNone(proposal_b["conclusion"])

    def test_03_result_attaches_to_requested_message_only(self) -> None:
        proposal_a = create_code_proposal_message("A", "fig = code_a")
        proposal_b = create_code_proposal_message("B", "fig = code_b")
        messages = [proposal_a, proposal_b]
        mark_proposal_approved(messages, proposal_b["id"], "fig = edited_b")

        attach_execution_result(
            messages,
            proposal_b["id"],
            executed_code="fig = edited_b",
            ok=True,
            result={"fig_json": {"data": [], "layout": {}}},
            error=None,
        )

        self.assertIsNone(proposal_a["result"])
        self.assertEqual(proposal_a["status"], PENDING_APPROVAL)
        self.assertEqual(proposal_b["status"], SUCCESS)
        self.assertIsNotNone(proposal_b["result"])

    def test_04_approved_and_executed_code_hashes_must_match(self) -> None:
        proposal = create_code_proposal_message("A", "fig = original")
        messages = [proposal]
        approved = "fig = approved"
        mark_proposal_approved(messages, proposal["id"], approved)

        self.assertEqual(proposal["status"], APPROVED_AND_EXECUTING)
        self.assertEqual(proposal["approved_code_hash"], code_sha256(approved))

        with self.assertRaises(ValueError):
            attach_execution_result(
                messages,
                proposal["id"],
                executed_code="fig = different",
                ok=True,
                result={"unexpected": True},
                error=None,
            )

        self.assertEqual(proposal["status"], APPROVED_AND_EXECUTING)
        self.assertIsNone(proposal["result"])

        attach_execution_result(
            messages,
            proposal["id"],
            executed_code=approved,
            ok=True,
            result={"expected": True},
            error=None,
        )
        self.assertEqual(proposal["approved_code_hash"], proposal["executed_code_hash"])
        self.assertEqual(proposal["status"], SUCCESS)

    def test_05_reset_removes_only_ai_transient_state(self) -> None:
        history = [{"role": "user", "content": "keep"}]
        state = {
            "ai_pending_code": "old",
            "ai_pending_answer": "old",
            "ai_last_result": {"old": True},
            "ai_chart_conclusion": "old",
            "ai_code_editor": "old",
            "ai_fix_instruction": "old",
            "ai_prompt_box": "old",
            "active_proposal_message_id": "old-id",
            "ai_code_editor_message-1_1": "old",
            "ai_fix_instruction_message-1_1": "old",
            "ai_messages": history,
            "ai_config": {"model": "keep"},
            "groq_api_key": "keep-key",
            "ai_dataset_cache": {"df": "keep"},
        }

        reset_ai_transient_state(state)

        self.assertEqual(state["ai_messages"], history)
        self.assertEqual(state["ai_config"], {"model": "keep"})
        self.assertEqual(state["groq_api_key"], "keep-key")
        self.assertEqual(state["ai_dataset_cache"], {"df": "keep"})
        self.assertNotIn("active_proposal_message_id", state)
        self.assertFalse(any(key.startswith("ai_code_editor") for key in state))
        self.assertFalse(any(key.startswith("ai_fix_instruction") for key in state))
        self.assertNotIn("ai_prompt_box", state)

    def test_06_legacy_message_normalizes_without_losing_code(self) -> None:
        legacy = {
            "role": "assistant",
            "content": "Legacy answer",
            "code": "fig = legacy_code",
        }

        normalized = normalize_message(legacy)

        self.assertTrue(normalized["id"])
        self.assertEqual(normalized["kind"], "code_proposal")
        self.assertEqual(normalized["current_code"], "fig = legacy_code")
        self.assertEqual(normalized["original_code"], "fig = legacy_code")
        self.assertEqual(normalized["revision"], 1)
        self.assertEqual(normalized["status"], PENDING_APPROVAL)
        self.assertIsNone(normalized["result"])
        self.assertIsNone(normalized["error"])

    def test_07_region_constants_and_dataset_mapping_are_complete(self) -> None:
        expected = [
            "Trung du và miền núi phía Bắc",
            "Đồng bằng sông Hồng",
            "Bắc Trung Bộ",
            "Nam Trung Bộ",
            "Đông Nam Bộ",
            "Đồng bằng sông Cửu Long",
        ]
        self.assertEqual(constants.OFFICIAL_REGIONS, expected)
        self.assertEqual(len(set(constants.OFFICIAL_REGIONS)), 6)
        self.assertIs(data_context.OFFICIAL_REGIONS, constants.OFFICIAL_REGIONS)
        self.assertIs(dataset_qa.OFFICIAL_REGIONS, constants.OFFICIAL_REGIONS)

        df = data_context.load_dataset()
        pairs = df[["location_name", "region"]].drop_duplicates()
        self.assertEqual(set(df["region"].unique()), set(expected))
        self.assertEqual(set(pairs["location_name"]), set(constants.LOCATION_TO_REGION))
        self.assertEqual(len(constants.LOCATION_TO_REGION), 20)
        self.assertTrue(
            all(
                constants.LOCATION_TO_REGION[row.location_name] == row.region
                for row in pairs.itertuples(index=False)
            )
        )

        count_answer = dataset_qa.answer_dataset_question("Dataset có bao nhiêu vùng?", df)
        region_answer = dataset_qa.answer_dataset_question(
            "Liệt kê địa điểm thuộc Đông Nam Bộ.",
            df,
        )
        self.assertIn("6 vùng", count_answer or "")
        self.assertIn("Đông Nam Bộ", region_answer or "")
        self.assertIn("TP. Hồ Chí Minh", region_answer or "")
        self.assertIn("Vũng Tàu", region_answer or "")


if __name__ == "__main__":
    unittest.main()

