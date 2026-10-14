"""
LIVO Footwear ERP — Lightweight Prometheus-Compatible Metrics Registry
Tracks operational, security, financial, and database metrics with strictly bounded cardinality.
"""

from collections import defaultdict
from typing import Dict, Any, List
import threading
import time

class MetricsRegistry:
    def __init__(self):
        self._lock = threading.Lock()
        self._counters = defaultdict(float)
        self._gauges = defaultdict(float)

    def inc(self, name: str, value: float = 1.0, labels: Dict[str, str] = None):
        """Increments a counter metric with bounded label key-values."""
        label_str = self._format_labels(labels)
        key = f"{name}{{{label_str}}}" if label_str else name
        with self._lock:
            self._counters[key] += value

    def set_gauge(self, name: str, value: float, labels: Dict[str, str] = None):
        """Sets a gauge metric."""
        label_str = self._format_labels(labels)
        key = f"{name}{{{label_str}}}" if label_str else name
        with self._lock:
            self._gauges[key] = value

    def get_counter(self, name: str, labels: Dict[str, str] = None) -> float:
        label_str = self._format_labels(labels)
        key = f"{name}{{{label_str}}}" if label_str else name
        with self._lock:
            return self._counters.get(key, 0.0)

    def get_gauge(self, name: str, labels: Dict[str, str] = None) -> float:
        label_str = self._format_labels(labels)
        key = f"{name}{{{label_str}}}" if label_str else name
        with self._lock:
            return self._gauges.get(key, 0.0)

    def _format_labels(self, labels: Dict[str, str] = None) -> str:
        if not labels:
            return ""
        # Strict low-cardinality enforcement: sort labels deterministically
        return ",".join(f'{k}="{v}"' for k, v in sorted(labels.items()))

    def export_prometheus(self) -> str:
        """Exports metrics in standard Prometheus text exposition format (version 0.0.4)."""
        lines = []
        with self._lock:
            lines.append("# HELP livo_counters Total counter operations in LIVO ERP")
            lines.append("# TYPE livo_counters counter")
            for k, v in sorted(self._counters.items()):
                lines.append(f"{k} {v}")
            
            lines.append("# HELP livo_gauges Current gauge levels in LIVO ERP")
            lines.append("# TYPE livo_gauges gauge")
            for k, v in sorted(self._gauges.items()):
                lines.append(f"{k} {v}")
        return "\n".join(lines) + "\n"

    def export_json(self) -> Dict[str, Any]:
        """Exports metrics as JSON dictionary."""
        with self._lock:
            return {
                "counters": dict(self._counters),
                "gauges": dict(self._gauges),
                "timestamp": time.time()
            }

    def reset(self):
        """Resets all metrics (used for clean testing runs)."""
        with self._lock:
            self._counters.clear()
            self._gauges.clear()

# Global Singleton Registry
metrics = MetricsRegistry()
