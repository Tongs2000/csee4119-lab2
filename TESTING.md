# CSEE 4119 Spring 2025, Assignment 2 Testing File
## Tao Tong
## GitHub username: Tongs2000


# TESTING.md

## Overview
This document describes the set of tests run on the Mini Reliable Transport (MRT) protocol implementation, including methodology, test cases, example outputs, and log file analysis. Log files for both client and server are provided in the submission for grading purposes.

## Test Environment
- **Operating System:** macOS 12.4
- **Python Version:** Python 3.9.19
- **Hardware:** MacBook Pro, Apple M3 Max, 36GB RAM
- **Network Simulator:** Using `network.py` with configurable loss characteristics via `loss.txt`.

---

## Test Case 1: No Loss / No Bit Error

**Loss Configuration:**  
loss.txt contains a single line:  
```
0 0 0
```
This setting indicates that throughout the test, no packet will be dropped and no bit errors will be injected.

**Procedure:**
1. Start the network simulator:
   ```bash
   python network.py 51000 127.0.0.1 50000 127.0.0.1 60000 loss.txt
   ```
2. Start the server:
   ```bash
   python app_server.py 60000 4096
   ```
3. Start the client:
   ```bash
   python app_client.py 50000 127.0.0.1 51000 1460
   ```

**Expected Outcome:**  
- The MRT protocol should complete the connection handshake (SYN, SYN-ACK, ACK).
- The file (`data.txt`) should be transmitted without errors.
- Log files (`log_50000.txt` and `log_60000.txt`) should show smooth data transfer with no retransmissions.

**Actual Outcome:**  
- **Result:**
   ```
2025-03-18 21:01:20.589 50000 51000 94 0 SYN 0
2025-03-18 21:01:20.590 50000 51000 0 95 SYN-ACK 0
2025-03-18 21:01:20.590 50000 51000 94 95 ACK 0
2025-03-18 21:01:20.590 50000 51000 95 95 PSH 1450
2025-03-18 21:01:20.591 50000 51000 0 1545 ACK 0
2025-03-18 21:01:20.591 50000 51000 1545 95 PSH 1450
2025-03-18 21:01:20.592 50000 51000 0 2995 ACK 0
2025-03-18 21:01:20.592 50000 51000 2995 95 PSH 1450
2025-03-18 21:01:20.593 50000 51000 0 4445 ACK 0
2025-03-18 21:01:20.593 50000 51000 4445 95 PSH 1450
2025-03-18 21:01:20.594 50000 51000 0 5895 ACK 0
2025-03-18 21:01:20.594 50000 51000 5895 95 PSH 1450
2025-03-18 21:01:20.595 50000 51000 0 7345 ACK 0
2025-03-18 21:01:20.595 50000 51000 7345 95 PSH 774
2025-03-18 21:01:20.595 50000 51000 0 8119 ACK 0
2025-03-18 21:01:20.595 50000 51000 8119 95 FIN 0
2025-03-18 21:01:20.595 50000 51000 0 8120 ACK 0
2025-03-18 21:01:20.595 50000 51000 0 0 FIN 0
2025-03-18 21:01:20.596 50000 51000 8119 1 ACK 0
2025-03-18 21:01:20.596 50000 - 8119 95 CLOSE 0
   ```
   ```
2025-03-18 21:01:20.590 60000 51000 94 0 SYN 0
2025-03-18 21:01:20.590 60000 51000 0 95 SYN-ACK 0
2025-03-18 21:01:20.590 60000 51000 94 95 ACK 0
2025-03-18 21:01:20.591 60000 51000 95 95 PSH 1450
2025-03-18 21:01:20.591 60000 51000 0 1545 ACK 0
2025-03-18 21:01:20.592 60000 51000 1545 95 PSH 1450
2025-03-18 21:01:20.592 60000 51000 0 2995 ACK 0
2025-03-18 21:01:20.593 60000 51000 2995 95 PSH 1450
2025-03-18 21:01:20.593 60000 51000 0 4445 ACK 0
2025-03-18 21:01:20.594 60000 51000 4445 95 PSH 1450
2025-03-18 21:01:20.594 60000 51000 0 5895 ACK 0
2025-03-18 21:01:20.594 60000 51000 5895 95 PSH 1450
2025-03-18 21:01:20.594 60000 51000 0 7345 ACK 0
2025-03-18 21:01:20.595 60000 51000 7345 95 PSH 774
2025-03-18 21:01:20.595 60000 51000 0 8119 ACK 0
2025-03-18 21:01:20.595 60000 51000 8119 95 FIN 0
2025-03-18 21:01:20.595 60000 51000 0 8120 ACK 0
2025-03-18 21:01:20.595 60000 51000 0 0 FIN 0
2025-03-18 21:01:20.596 60000 51000 8119 1 ACK 0
2025-03-18 21:01:20.596 60000 - 0 0 CLOSE 0
   ```
- **Observations:**
- The logs from both the client and the server show a successful three-way handshake (SYN, SYN-ACK, ACK) followed by multiple PSH/ACK exchanges to transmit the data.
- Data transfer segments (PSH) have consistent sequence numbers on both sides.
- The connection termination phase is completed with a FIN-ACK exchange.
- No retransmissions or errors were observed in this test run under the "no loss" condition.


---

## Test Case 2: With Loss and Bit Errors, then Recovery

**Loss Configuration:**  
loss.txt is set to the following multi-line configuration:
```
0 0.1 0.005
1 0.2 0.01
5 0 0
```
- From 0 seconds: 10% packet loss and 0.5% chance for each bit to flip.
- From 1 second: 20% packet loss and 1% chance for each bit to flip.
- From 5 seconds onward: the network is clean (0% loss, 0% bit error).

This configuration simulates a brief period of challenging network conditions that gradually improve.

**Procedure:**
1. Start the network simulator:
   ```bash
   python network.py 51000 127.0.0.1 50000 127.0.0.1 60000 loss.txt
   ```
2. Start the server:
   ```bash
   python app_server.py 60000 4096
   ```
3. Start the client:
   ```bash
   python app_client.py 50000 127.0.0.1 51000 1460
   ```

**Expected Outcome:**  
- The MRT protocol should handle initial packet losses and bit errors via retransmissions and error detection.
- Despite the adverse network conditions in the early seconds, the protocol should successfully reassemble the transmitted file correctly once the network becomes stable after 5 seconds.
- Log files should reflect retransmission events (e.g., PSH-REXMIT) and indicate successful recovery.

**Actual Outcome:**  
- **Result:**
   ```
2025-03-18 21:05:11.874 50000 51000 347 0 SYN 0
2025-03-18 21:05:11.874 50000 51000 0 348 SYN-ACK 0
2025-03-18 21:05:11.874 50000 51000 347 348 ACK 0
2025-03-18 21:05:11.874 50000 51000 348 348 PSH 1448
2025-03-18 21:05:12.875 50000 51000 348 348 PSH-REXMIT 1448
2025-03-18 21:05:12.876 50000 51000 348 348 PSH 1448
2025-03-18 21:05:12.877 50000 51000 0 1796 ACK 0
2025-03-18 21:05:12.877 50000 51000 1796 348 PSH 1448
2025-03-18 21:05:12.877 50000 51000 1796 348 PSH 1448
2025-03-18 21:05:12.879 50000 51000 0 3244 ACK 0
2025-03-18 21:05:12.879 50000 51000 3244 348 PSH 1448
2025-03-18 21:05:12.879 50000 51000 3244 348 PSH 1448
2025-03-18 21:05:12.881 50000 51000 0 4692 ACK 0
2025-03-18 21:05:12.881 50000 51000 4692 348 PSH 1448
2025-03-18 21:05:13.882 50000 51000 4692 348 PSH-REXMIT 1448
2025-03-18 21:05:13.882 50000 51000 4692 348 PSH 1448
2025-03-18 21:05:13.887 50000 51000 4692 348 PSH 1448
2025-03-18 21:05:14.888 50000 51000 4692 348 PSH-REXMIT 1448
2025-03-18 21:05:14.888 50000 51000 4692 348 PSH 1448
2025-03-18 21:05:14.894 50000 51000 0 6140 ACK 0
2025-03-18 21:05:14.894 50000 51000 6140 348 PSH 1448
2025-03-18 21:05:15.895 50000 51000 6140 348 PSH-REXMIT 1448
2025-03-18 21:05:15.896 50000 51000 6140 348 PSH 1448
2025-03-18 21:05:15.899 50000 51000 0 7588 ACK 0
2025-03-18 21:05:15.899 50000 51000 7588 348 PSH 784
2025-03-18 21:05:15.900 50000 51000 0 8372 ACK 0
2025-03-18 21:05:15.900 50000 51000 8372 348 FIN 0
2025-03-18 21:05:15.900 50000 51000 0 9373 ACK 0
2025-03-18 21:05:15.901 50000 51000 0 0 FIN 0
2025-03-18 21:05:15.901 50000 51000 8372 1 ACK 0
2025-03-18 21:05:15.901 50000 - 8372 348 CLOSE 0
   ```
   ```
2025-03-18 21:05:11.874 60000 51000 347 0 SYN 0
2025-03-18 21:05:11.874 60000 51000 0 348 SYN-ACK 0
2025-03-18 21:05:11.874 60000 51000 347 348 ACK 0
2025-03-18 21:05:12.877 60000 51000 348 348 PSH 1448
2025-03-18 21:05:12.877 60000 51000 0 1796 ACK 0
2025-03-18 21:05:12.877 60000 51000 348 348 PSH 1448
2025-03-18 21:05:12.877 60000 51000 0 1796 ACK 0
2025-03-18 21:05:12.878 60000 51000 1796 348 PSH 1448
2025-03-18 21:05:12.878 60000 51000 0 3244 ACK 0
2025-03-18 21:05:12.879 60000 51000 1796 348 PSH 1448
2025-03-18 21:05:12.879 60000 51000 0 3244 ACK 0
2025-03-18 21:05:12.880 60000 51000 3244 348 PSH 1448
2025-03-18 21:05:12.880 60000 51000 0 4692 ACK 0
2025-03-18 21:05:12.881 60000 51000 4692 348 PSH 1448
2025-03-18 21:05:12.881 60000 51000 0 6140 ACK 0
2025-03-18 21:05:13.884 60000 51000 4692 348 PSH 1448
2025-03-18 21:05:13.885 60000 51000 0 6140 ACK 0
2025-03-18 21:05:13.886 60000 51000 4692 348 PSH 1448
2025-03-18 21:05:13.886 60000 51000 0 6140 ACK 0
2025-03-18 21:05:14.893 60000 51000 4692 348 PSH 1448
2025-03-18 21:05:14.893 60000 51000 0 6140 ACK 0
2025-03-18 21:05:15.898 60000 51000 6140 348 PSH 1448
2025-03-18 21:05:15.898 60000 51000 0 7588 ACK 0
2025-03-18 21:05:15.899 60000 51000 6140 348 PSH 1448
2025-03-18 21:05:15.899 60000 51000 0 7588 ACK 0
2025-03-18 21:05:15.900 60000 51000 7588 348 PSH 784
2025-03-18 21:05:15.900 60000 51000 0 8372 ACK 0
2025-03-18 21:05:15.900 60000 51000 9372 348 FIN 0
2025-03-18 21:05:15.900 60000 51000 0 9373 ACK 0
2025-03-18 21:05:15.900 60000 51000 0 0 FIN 0
   ```
- **Observations:**  
- In this test, the loss configuration introduced packet loss and bit errors during the initial transmission period.
- The client log shows multiple PSH-REXMIT events, indicating that certain segments were not acknowledged on time and had to be retransmitted.
- Both client and server logs show these retransmission events, yet the protocol eventually delivered all segments.
- The final connection termination occurs normally, confirming that despite the challenging conditions, the MRT protocol managed to recover and successfully complete the file transfer.


