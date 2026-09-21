![SCADA Priority Queue Canary CI](https://github.com/Haidriyam/scada-priority-queue-canary/actions/workflows/devsecops-ci.yml/badge.svg)

# IEEE 802.1Qbv Time-Aware Substation Telemetry Shaper

A deterministic traffic shaping and telemetry queueing testbed emulating an IEEE 802.1Qbv Time-Aware Shaper (TAS). Built to model mixed-criticality communication within smart grid substations, it guarantees that critical protection trip signals (IEC 61850 GOOSE) maintain strict sub-4ms delivery bounds in the presence of line-rate Denial-of-Service (DoS) floods on lower-priority Modbus TCP and maintenance streams.

```text
[ IEC 61850 GOOSE (Queue 7) ] ──┐
[ IEEE C37.118 PMU (Queue 5) ]  ──┼──► [ 802.1Qbv Gate Control List (GCL) ] ──► [ Wire Tx ]
[ Best Effort DoS (Queue 1) ]  ──┘                 │
                                                   ▼
                                     (Guaranteed Isolated Windows)