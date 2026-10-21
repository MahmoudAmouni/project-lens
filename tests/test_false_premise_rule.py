"""The agent's instructions tell the model to check a claim in the question instead of searching for it."""

from AI.messages import build_messages


def test_every_question_carries_the_false_premise_rule():
    system = build_messages("The contract says retention is 20%, right?", [])[0]["content"]
    assert "Never trust a number or claim in the question" in system
    assert 'search for the topic itself ("retention")' in system
