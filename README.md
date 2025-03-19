
# CSEE 4119 Spring 2025, Assignment 2
## Tao Tong
## GitHub username: Tongs2000

# Mini Reliable Transport (MRT) Protocol

This repository contains my implementation of a mini reliable transport (MRT) protocol built on top of UDP. The MRT protocol is designed to provide reliable, in-order delivery of data over an unreliable transport by handling issues like packet loss, bit errors, segmentation, and flow control.

---

## Repository Structure

- **mrt_client.py**  
  Implements the MRT client APIs. It handles connection establishment (three-way handshake), data segmentation and transmission (with retransmissions), and connection termination.

- **mrt_server.py**  
  Implements the MRT server APIs. It manages connection acceptance, reassembling received segments (ensuring in-order delivery), sending ACKs, and gracefully terminating connections.

- **app_client.py**  
  A simple application client that uses the MRT client APIs to read a file (e.g., `data.txt`) and send its contents to the server.

- **app_server.py**  
  A simple application server that uses the MRT server APIs to accept a connection, receive data from the client, compare it with the original file, and report whether the transmission was successful.

- **network.py**  
  A network simulator that sits between the client and the server. It simulates network conditions by introducing packet loss and bit errors based on a configuration file (`loss.txt`).

- **loss.txt**  
  A configuration file specifying the network loss characteristics. Each line defines a time (in seconds), a packet loss rate, and a bit error rate. For example:
  ```
  0 0.1 0.005
  ```
  means that starting from 0 seconds, packets are dropped with a 10% probability and each bit has a 0.5% chance of being flipped.

- **TESTING.md**  
  A document describing the tests I performed on the MRT protocol implementation along with sample outputs and log files.

- **DESIGN.md**  
  A document describing the design of the MRT protocol, including the message types (SYN, SYN-ACK, ACK, PSH, FIN, etc.), and how I handle segment loss, data corruption, and flow control.

---

## Compilation and Usage

Since this project is implemented in Python, there is no compilation step. Make sure you have Python 3.9 installed. All files should be in the same directory.

### Running the Network Simulator

The network simulator forwards data between the client and the server while applying loss and error injection based on `loss.txt`.

```bash
python network.py <networkPort> <clientAddr> <clientPort> <serverAddr> <serverPort> <lossFile>
```

**Example:**
```bash
python network.py 51000 127.0.0.1 50000 127.0.0.1 60000 loss.txt
```

### Running the Server

Start the server application. The server listens for incoming connections and receives data.

```bash
python app_server.py <server_port> <buffer_size>
```

**Example:**
```bash
python app_server.py 60000 4096
```

### Running the Client

Start the client application. The client reads data from a file (e.g., `data.txt`), establishes a connection to the server via the network simulator, and sends the file.

```bash
python app_client.py <client_port> <network_addr> <network_port> <segment_size>
```

**Example:**
```bash
python app_client.py 50000 127.0.0.1 51000 1460
```

---

## Description of the MRT Protocol

The MRT protocol is designed to overcome the limitations of UDP by adding several reliability features:

1. **Connection Establishment and Termination:**  
   MRT uses a three-way handshake similar to TCP:
   - **SYN:** The client starts the connection.
   - **SYN-ACK:** The server acknowledges the SYN and responds.
   - **ACK:** The client completes the handshake.
   For connection termination, a FIN-ACK sequence is used so that both sides can close the connection gracefully.

2. **Reliable Data Transfer:**  
   Data is segmented into manageable chunks. Each segment is sent with a sequence number and is acknowledged by the receiver. If an ACK is not received within a timeout period, the segment is retransmitted.

3. **Data Integrity and In-Order Delivery:**  
   Although UDP does not guarantee data ordering or integrity, the MRT protocol adds:
   - **Checksums (or a simple hash function):** to detect data corruption.
   - **Sequence Numbers:** to reassemble the data in the correct order, even if segments arrive out-of-order.

4. **Flow Control:**  
   MRT includes basic flow control mechanisms to prevent the sender from overwhelming the receiver's buffer. This is managed by controlling the window of outstanding (unacknowledged) data.

5. **Handling Network Conditions:**  
   The protocol is tested using a network simulator (`network.py`) that simulates various network conditions including packet loss and bit errors. The parameters for these conditions are specified in `loss.txt`.

---

## Assumptions

- **Single Connection:**  
  The protocol is implemented for a single client-server connection. Handling multiple simultaneous connections is not supported.

- **Data File:**  
  The client expects a file named `data.txt` in the same directory for transmission.

- **Simplified Protocol:**  
  While inspired by TCP, some features (such as advanced congestion control) are simplified or omitted to focus on reliability and error recovery.

- **Logging:**  
  Both client and server record protocol events in log files (`log_<port>.txt`), which are essential for debugging and grading.