# CSEE 4119 Spring 2025, Assignment 2 Design File
## Tao Tong
## GitHub username: Tongs2000

## Overview
In this document, I'll explain how I designed my Mini Reliable Transport (MRT) protocol. My MRT protocol is built on top of UDP and aims to provide reliable, in-order delivery of data while handling common issues like packet loss, data corruption, out-of-order delivery, high link latency, and flow control. I got some inspiration from TCP but simplified things to meet the lab requirements.

## Message Types
I've defined a few message types to handle connection setup, data transfer, and closing the connection:

- **SYN**: Starts a connection request from the client.
- **SYN-ACK**: Sent by the server in response to the SYN, acknowledging the request and sending back its own acknowledgement.
- **ACK**: Acknowledges the receipt of segments. It's used during the handshake, data transfer, and connection termination.
- **PSH**: Marks a data segment that carries part of the file payload.
- **FIN**: Indicates that one side wants to terminate the connection.
- **FIN-ACK**: (Handled implicitly as an ACK for FIN) Completes the connection termination handshake.

## Handling Segment Loss
- **Retransmission Timer:** Each segment I send from the client is paired with a timer. If I don't receive the corresponding ACK before the timer expires, I retransmit the segment.
- **ACK-based Confirmation:** The sender relies on receiving ACKs for each segment. If an ACK is missing, that's my cue to resend the segment.
- **Network Simulator Integration:** The network simulator (network.py) can drop segments based on its configuration. My retransmission mechanism makes sure that dropped segments are eventually resent.

## Handling Data Corruption
- **Checksum/Hash Verification:** Although it's not as advanced as TCP's checksum, each segment includes a simple checksum (or hash) to verify data integrity.
- **Corruption Detection:** When a segment arrives, the receiver calculates the checksum and compares it with the transmitted one. If they don't match, the segment is discarded and the sender will eventually retransmit it.
- **Retransmission upon Error:** If corrupted data is detected, the receiver doesn't update its expected sequence number, which causes the sender to resend the correct segment.

## Handling Out-of-Order Delivery
- **Sequence Numbers:** Each segment carries a sequence number that indicates its position within the overall file.
- **Expected Sequence Number:** The server keeps track of the next expected sequence number. If a segment's sequence number matches this value, the data is accepted and added to the buffer.
- **Re-Acknowledgment:** If a segment arrives out of order, the server just resends an ACK for the last correctly received byte, prompting the sender to retransmit any missing segments.

## Handling High Link Latency
- **Timeout Adjustments:** I use retransmission timers to detect lost or delayed segments. In high latency scenarios, the timeout might need tweaking, but for this lab I used a fixed value that works well.
- **Non-Stop Transmission:** Instead of a strict stop-and-wait protocol, my design (or future improvements) might use a sliding window so that multiple segments can be sent before waiting for ACKs. For now, I send one segment and wait for its ACK before moving on.
- **ACK Aggregation:** ACKs can cumulatively confirm multiple segments, which helps reduce the impact of latency on throughput.

## Data Transfer and Segmentation
- **Segmentation:** When sending large files, I break them into segments according to the maximum segment size (including headers) specified by the user. Each segment carries a chunk of the data along with its sequence number.
- **Reassembly:** The server reassembles the file by concatenating the segments in the correct order, as determined by the sequence numbers.
- **Payload Management:** My design ensures that even if the file doesn't perfectly divide into segments, the last segment carries the remaining bytes.

## Flow Control
- **Buffer Size Awareness:** The server is set up with a receive buffer size, and the protocol ensures that the sender doesn't overwhelm the receiver’s buffer.
- **ACK Feedback Loop:** I manage flow control by monitoring the ACKs. If ACKs are delayed, the sender slows down to prevent buffer overflow at the receiver.
- **Future Improvements:** In a more advanced version, I might implement a sliding window protocol that adjusts the transmission rate based on network conditions and the receiver's capacity.

## Multithreading Integration
- **Server Side:** I use two dedicated threads on the server. One thread (`rcv_handler`) continuously listens for incoming UDP segments and places them into a thread-safe queue. The other thread (`sgmnt_handler`) processes segments from the queue, handling connection setup, data reassembly, and connection termination. This way, the server can quickly capture incoming data without getting held up by processing tasks.
- **Client Side:** On the client side, I launch a dedicated receiving thread (`rcv_handler`) that listens for incoming segments like SYN-ACK, ACK, and FIN. I use events and condition variables to synchronize between this thread and the main sending thread. This design allows the client to process responses concurrently with sending data.

## Summary
My MRT protocol design brings basic reliability to UDP by incorporating a handshake mechanism, sequence numbering, retransmission for lost or corrupted segments, and simple flow control. The use of multithreading on both the server and client lets me handle sending, receiving, and processing of segments at the same time. While the design is inspired by TCP, it's simplified for this lab and lays the groundwork for more advanced transport protocols.
