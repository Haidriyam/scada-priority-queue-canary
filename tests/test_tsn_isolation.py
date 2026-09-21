import unittest
from shaper.qbv_scheduler import TimeAwareShaper, TrafficClass, Packet
from shaper.traffic_canary import SubstationTrafficCanary


class TestTSNTrafficIsolation(unittest.TestCase):

    def setUp(self):
        self.shaper = TimeAwareShaper(cycle_time_us=10000.0)

    def test_gcl_window_scheduling(self):
        # 0 - 2000 us: GOOSE
        self.assertEqual(self.shaper.get_open_gate(500.0), TrafficClass.CRITICAL_GOOSE)
        # 2000 - 6000 us: PMU
        self.assertEqual(self.shaper.get_open_gate(3500.0), TrafficClass.PMU_STREAM)
        # 6000 - 10000 us: Best Effort
        self.assertEqual(self.shaper.get_open_gate(8000.0), TrafficClass.BEST_EFFORT)

    def test_critical_goose_isolation_under_dos_flood(self):
        # 1. Inject a massive flood of Best-Effort traffic (Queue 1)
        for i in range(250):
            be_pkt = Packet(
                packet_id=i,
                traffic_class=TrafficClass.BEST_EFFORT,
                size_bytes=1000,
                arrival_time_us=100.0,
                max_latency_us=500000.0,
            )
            self.shaper.enqueue(be_pkt)

        # 2. Interleave 5 critical IEC 61850 GOOSE trip packets (Queue 7)
        # IEC 61850 mandates sub-4ms (4000 us) delivery deadline
        for j in range(5):
            goose_pkt = Packet(
                packet_id=1000 + j,
                traffic_class=TrafficClass.CRITICAL_GOOSE,
                size_bytes=128,
                arrival_time_us=200.0 + (j * 1000.0),
                max_latency_us=4000.0,
            )
            self.shaper.enqueue(goose_pkt)

        # 3. Simulate transmission loop
        records = []
        for _ in range(60):
            res = self.shaper.transmit_next()
            if res:
                records.append(res)

        # 4. Audit metrics via the canary
        audit = SubstationTrafficCanary.audit_telemetry_stream(records)

        self.assertGreater(audit["goose_packets_processed"], 0)
        # 100% of GOOSE trip packets must meet their deadline despite the DoS flood
        self.assertEqual(audit["goose_deadline_adherence_pct"], 100.0)
        self.assertLessEqual(audit["max_goose_latency_us"], 4000.0)


if __name__ == "__main__":
    unittest.main()