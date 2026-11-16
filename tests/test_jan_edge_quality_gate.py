"""Synthetic output tests only."""
import unittest
from jan_edge_quality_gate import classify_answer


class QualityGateTests(unittest.TestCase):
    def test_valid_plain_answer(self):
        self.assertTrue(classify_answer('Art Deco, because of its geometry.', 'stop')['complete_user_answer'])

    def test_token_limit_never_passes(self):
        self.assertFalse(classify_answer('Normal-looking answer.', 'length')['complete_user_answer'])

    def test_empty_answer_never_passes(self):
        self.assertFalse(classify_answer('   ', 'stop')['complete_user_answer'])

    def test_explicit_thinking_rejected(self):
        self.assertFalse(classify_answer('First <think>internal</think> then answer.', 'stop')['complete_user_answer'])

    def test_orphan_marker_rejected(self):
        self.assertFalse(classify_answer('thinking </think> Finished.', 'stop')['complete_user_answer'])

    def test_planning_preamble_rejected(self):
        self.assertTrue(classify_answer('Okay, so I need to answer the user.', 'stop')['has_unmarked_planning'])

    def test_meta_commentary_rejected(self):
        self.assertFalse(classify_answer('The response should mention a robot.', 'stop')['complete_user_answer'])

    def test_normal_hedge_accepted(self):
        self.assertTrue(classify_answer('Let me think. I prefer Art Deco.', 'stop')['complete_user_answer'])

    def test_normal_task_phrase_accepted(self):
        self.assertTrue(classify_answer('I need to repair the robot first.', 'stop')['complete_user_answer'])

    def test_none_rejected(self):
        self.assertFalse(classify_answer(None, 'stop')['complete_user_answer'])
