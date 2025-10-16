"""
Rule-based priority calculator - Fast, reliable, explainable
"""
from src.config.logging_config import logger

def calculate_priority(signal_data: dict) -> tuple:
    """
    Calculate priority using intelligent rules
    Returns: (score, summary, reasoning, action)
    """
    subject = signal_data.get('subject', '').lower()
    content = signal_data.get('content', '').lower()
    sender = signal_data.get('sender', '').lower()
    metadata = signal_data.get('metadata', {})
    
    score = 5.0  # Base score
    reasons = []
    
    # CRITICAL KEYWORDS (+ 4 points)
    critical_words = ['emergency', 'critical', 'down', 'outage', 'crash', 'failed']
    if any(word in subject or word in content for word in critical_words):
        score += 4
        reasons.append("Critical system issue detected")
    
    # URGENT KEYWORDS (+3 points)
    urgent_words = ['urgent', 'asap', 'immediate', 'escalation']
    if any(word in subject or word in content for word in urgent_words):
        score += 3
        reasons.append("Urgent action required")
    
    # NEGATIVE SENTIMENT (+2 points)
    negative_words = ['angry', 'unacceptable', 'disappointed', 'terrible', 'awful', 'frustrated']
    if any(word in subject or word in content for word in negative_words):
        score += 2
        reasons.append("Negative customer sentiment")
    
    # FINANCIAL IMPACT (+2 points)
    if metadata.get('revenue_loss_per_hour', 0) > 5000:
        score += 2
        reasons.append(f"High revenue impact: ${metadata['revenue_loss_per_hour']}/hour")
    
    # EXECUTIVE ESCALATION (+1 point)
    if metadata.get('escalation_level') == 'executive' or 'ceo' in sender or 'cto' in sender:
        score += 1
        reasons.append("Executive escalation")
    
    # MULTIPLE USERS AFFECTED (+1 point)
    if metadata.get('affected_users', 0) > 100:
        score += 1
        reasons.append(f"{metadata['affected_users']} users affected")
    
    # REPEAT ISSUE (+1 point)
    if metadata.get('complaint_count', 0) > 2:
        score += 1
        reasons.append("Repeat complaint")
    
    # Cap at 10
    score = min(score, 10.0)
    
    # Generate summary and action
    if score >= 9:
        summary = f"CRITICAL: {subject[:100]}"
        action = "Immediate executive escalation and emergency response required"
    elif score >= 7:
        summary = f"HIGH PRIORITY: {subject[:100]}"
        action = "Urgent team action required within 1 hour"
    elif score >= 5:
        summary = f"MEDIUM: {subject[:100]}"
        action = "Standard response required within 4 hours"
    else:
        summary = f"LOW: {subject[:100]}"
        action = "Standard review and response"
    
    reasoning = " | ".join(reasons) if reasons else "Standard priority based on content analysis"
    
    logger.info(f"✓ Priority calculated: {score}/10 - {reasoning}")
    
    return score, summary, reasoning, action
