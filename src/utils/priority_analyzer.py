"""
Priority analysis using rule-based system
"""
from typing import Dict, Tuple
from src.config.logging_config import logger
from src.utils.simple_priority import calculate_priority


class PriorityAnalyzer:
    """Analyzes operational signals and assigns priority scores"""
    
    def __init__(self):
        logger.info("PriorityAnalyzer initialized (Rule-based mode)")
    
    def analyze_signal(self, signal_data: Dict) -> Tuple[float, str, str, str]:
        """
        Analyze signal and return priority information
        
        Returns:
            (priority_score, summary, reasoning, recommended_action)
        """
        try:
            return calculate_priority(signal_data)
        except Exception as e:
            logger.error(f"Priority analysis error: {str(e)}")
            return 5.0, "Analysis error", str(e), "Manual review required"


# Global analyzer instance
priority_analyzer = PriorityAnalyzer()
