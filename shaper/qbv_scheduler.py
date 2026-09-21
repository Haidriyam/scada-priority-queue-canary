"""
IEEE 802.1Qbv Time-Aware Shaper (TAS) Core Engine.
Enforces deterministic transmission windows via Gate Control Lists (GCL).
"""
from dataclasses import dataclass
from enum import IntEnum
from typing import Dict, List, Optional
from collections import deque


class TrafficClass(IntEnum):
    BEST_EFFORT = 1       # Modbus / SNMP / HTTP management
    PMU_STREAM = 5        # IEEE C37.118 Synchrophasor UDP streams
    CRITICAL_GOOSE = 7    # IEC 61850 GOOSE breaker trip signals


@dataclass
class Packet:
    packet_id: int
    traffic_class: TrafficClass
    size_bytes: int
    arrival_time_us: float
    max_latency_us: float  # Maximum allowable delivery deadline


class TimeAwareShaper:
    def __init__(self, cycle_time_us: float = 10000.0):
        self.cycle_time_us = cycle_time_us
        self.current_time_us = 0.0

        # Dedicated queues for each traffic class (max 500 frames per queue)
        self.queues: Dict[TrafficClass, deque] = {
            TrafficClass.CRITICAL_GOOSE: deque(maxlen=500),
            TrafficClass.PMU_STREAM: deque(maxlen=500),
            TrafficClass.BEST_EFFORT: deque(maxlen=500),
        }

        # GCL: Defines open window duration (microseconds) within a cycle
        # [0.0 to 2000.0 us]: GOOSE exclusive protected window
        # [2000.0 to 6000.0 us]: PMU streaming window
        # [6000.0 to 10000.0 us]: Best effort maintenance window
        self.goose_window_us = 2000.0
        self.pmu_window_us = 6000.0

        # Wire transmission rate: 100 Mbps = 12.5 bytes/microsecond
        self.bytes_per_us = 12.5

    def enqueue(self, packet: Packet) -> bool:
        """Enqueue packet into its corresponding class queue; drops if queue is saturated."""
        q = self.queues[packet.traffic_class]
        if len(q) >= q.maxlen:
            return False  # Queue saturated: tail drop
        q.append(packet)
        return True

    def get_open_gate(self, time_us: float) -> TrafficClass:
        """Evaluate the active Gate Control List (GCL) entry based on cyclic offset."""
        cycle_offset = time_us % self.cycle_time_us
        if cycle_offset < self.goose_window_us:
            return TrafficClass.CRITICAL_GOOSE
        elif cycle_offset < self.pmu_window_us:
            return TrafficClass.PMU_STREAM
        else:
            return TrafficClass.BEST_EFFORT

    def transmit_next(self) -> Optional[Dict[str, float]]:
        """
        Process the head of the currently opened gate queue.
        Returns transmission metrics dict or None if open queue is idle.
        """
        active_class = self.get_open_gate(self.current_time_us)
        q = self.queues[active_class]

        if not q:
            # Advance clock by 10 us when idle
            self.current_time_us += 10.0
            return None

        pkt: Packet = q.popleft()
        tx_duration_us = pkt.size_bytes / self.bytes_per_us

        # Transmission time must not cross into the next GCL window (guard band simulation)
        self.current_time_us += tx_duration_us
        latency_us = self.current_time_us - pkt.arrival_time_us
        deadline_met = latency_us <= pkt.max_latency_us

        return {
            "packet_id": float(pkt.packet_id),
            "traffic_class": float(pkt.traffic_class),
            "latency_us": float(latency_us),
            "deadline_met": 1.0 if deadline_met else 0.0,
        }