"""Metrics collection utilities"""
from typing import Dict, List
from datetime import datetime, timedelta
from collections import defaultdict


class MetricsCollector:
    """Collects and aggregates metrics for the onboarding system"""
    
    def __init__(self):
        self.metrics = defaultdict(list)
        self.counters = defaultdict(int)
        self.timers = {}
    
    def increment(self, metric: str, value: int = 1):
        """Increment a counter metric"""
        self.counters[metric] += value
    
    def record(self, metric: str, value: float):
        """Record a value for aggregation"""
        self.metrics[metric].append({
            'value': value,
            'timestamp': datetime.now()
        })
    
    def start_timer(self, timer_name: str):
        """Start a timer"""
        self.timers[timer_name] = datetime.now()
    
    def stop_timer(self, timer_name: str) -> float:
        """Stop a timer and return duration in seconds"""
        if timer_name not in self.timers:
            return 0.0
        
        duration = (datetime.now() - self.timers[timer_name]).total_seconds()
        del self.timers[timer_name]
        
        # Record the duration
        self.record(f"{timer_name}_duration", duration)
        
        return duration
    
    def get_summary(self) -> Dict:
        """Get metrics summary"""
        summary = {
            'counters': dict(self.counters),
            'aggregates': {}
        }
        
        # Calculate aggregates
        for metric, values in self.metrics.items():
            if values:
                nums = [v['value'] for v in values]
                summary['aggregates'][metric] = {
                    'count': len(nums),
                    'sum': sum(nums),
                    'avg': sum(nums) / len(nums),
                    'min': min(nums),
                    'max': max(nums)
                }
        
        return summary
    
    def get_success_rate(self, success_metric: str, total_metric: str) -> float:
        """Calculate success rate from counters"""
        total = self.counters.get(total_metric, 0)
        if total == 0:
            return 0.0
        
        success = self.counters.get(success_metric, 0)
        return success / total


# Global metrics instance
metrics = MetricsCollector()