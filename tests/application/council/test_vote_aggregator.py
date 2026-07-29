from aegis_trade.domain.council import AgentVote
from aegis_trade.application.council.vote_aggregator import VoteAggregator

def test_vote_aggregator_equal_weights():
    aggregator = VoteAggregator()
    
    votes = [
        AgentVote("Agent1", "BUY", 0.8),
        AgentVote("Agent2", "BUY", 0.6),
        AgentVote("Agent3", "SELL", 0.4),
        AgentVote("Agent4", "WAIT", 0.0)
    ]
    
    final_vote, confidence, buy_score, sell_score = aggregator.aggregate(votes)
    
    assert final_vote == "BUY"
    # All weights are equal = 0.25 each. 
    # buy_score = (0.8 * 0.25) + (0.6 * 0.25) = 0.35
    # sell_score = 0.4 * 0.25 = 0.1
    assert buy_score == 0.35
    assert sell_score == 0.1
    assert confidence == buy_score

def test_vote_aggregator_custom_weights():
    weights = {
        "Agent1": 0.5,
        "Agent2": 0.1,
        "Agent3": 0.4
    }
    aggregator = VoteAggregator(agent_weights=weights)
    
    votes = [
        AgentVote("Agent1", "BUY", 0.8),   # Weight 0.5 -> 0.4
        AgentVote("Agent2", "BUY", 0.2),   # Weight 0.1 -> 0.02
        AgentVote("Agent3", "SELL", 0.9),  # Weight 0.4 -> 0.36
    ]
    
    final_vote, confidence, buy_score, sell_score = aggregator.aggregate(votes)
    
    import pytest
    assert final_vote == "BUY"
    assert buy_score == pytest.approx(0.42)
    assert sell_score == pytest.approx(0.36)

def test_vote_aggregator_empty():
    aggregator = VoteAggregator()
    final_vote, confidence, buy_score, sell_score = aggregator.aggregate([])
    assert final_vote == "WAIT"
    assert confidence == 0.0
