"""
Substation Network Latency & Jitter Profiler.
Monitors deadline compliance for critical IEC 61850 trip messages under flood scenarios.
"""
from typing import Dict, List


class SubstationTrafficCanary:
    @staticmethod
    def audit_telemetry_stream(transmission_records: List[Dict[str, float]]) -> Dict[str, float]:
        """Aggregate jitter, deadline adherence, and delivery metrics."""
        goose_records = [r for r in transmission_records if r["traffic_class"] == 7.0]

        if not goose_records:
            return {
                "goose_packets_processed": 0.0,
                "goose_deadline_adherence_pct": 0.0,
                "max_goose_latency_us": 0.0,
            }

        latencies = [r["latency_us"] for r in goose_records]
        adherent = [r for r in goose_records if r["deadline_met"] == 1.0]

        adherence_pct = (len(adherent) / len(goose_records)) * 100.0
        max_lat = max(latencies)
        avg_lat = sum(latencies) / len(latencies)

        return {
            "goose_packets_processed": float(len(goose_records)),
            "goose_deadline_adherence_pct": float(adherence_pct),
            "max_goose_latency_us": float(max_lat),
            "avg_goose_latency_us": float(avg_lat),
        }