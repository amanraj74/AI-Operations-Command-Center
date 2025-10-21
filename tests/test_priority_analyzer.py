"""
Test suite for priority analyzer
"""
import pytest
from src.utils.simple_priority import calculate_priority

def test_critical_keywords():
    """Test critical keyword detection"""
    signal = {
        'subject': 'EMERGENCY: System DOWN',
        'content': 'Critical issue affecting production',
        'sender': 'user@example.com',
        'metadata': {}
    }
    score, summary, reasoning, action = calculate_priority(signal)
    assert score >= 9.0, f"Expected high priority for critical keywords, got {score}"

def test_financial_impact():
    """Test financial impact scoring"""
    signal = {
        'subject': 'Issue reported',
        'content': 'We are losing revenue',
        'sender': 'user@example.com',
        'metadata': {'revenue_loss_per_hour': 10000}
    }
    score, _, _, _ = calculate_priority(signal)
    assert score >= 7.0, "High revenue loss should increase priority"

def test_executive_escalation():
    """Test executive escalation detection"""
    signal = {
        'subject': 'Urgent matter',
        'content': 'Need immediate attention',
        'sender': 'ceo@company.com',
        'metadata': {}
    }
    score, _, _, _ = calculate_priority(signal)
    assert score >= 6.0, "CEO emails should have higher priority"

def test_low_priority():
    """Test low priority signals"""
    signal = {
        'subject': 'General inquiry',
        'content': 'Just wondering about pricing',
        'sender': 'user@example.com',
        'metadata': {}
    }
    score, _, _, _ = calculate_priority(signal)
    assert score <= 6.0, "General inquiries should be low priority"

def test_combined_factors():
    """Test multiple priority factors"""
    signal = {
        'subject': 'URGENT EMERGENCY: System completely down!',
        'content': 'Critical outage! 500 users affected. Unacceptable!',
        'sender': 'cto@enterprise.com',
        'metadata': {
            'affected_users': 500,
            'revenue_loss_per_hour': 20000,
            'escalation_level': 'executive'
        }
    }
    score, _, _, _ = calculate_priority(signal)
    assert score == 10.0, f"Maximum factors should give priority 10, got {score}"

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
