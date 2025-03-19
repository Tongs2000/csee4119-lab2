# Columbia University - CSEE 4119 Computer Networks
# Assignment 2 - Mini Reliable Transport Protocol
#
# mrt_server.py - defining server APIs of the mini reliable transport protocol

import socket # for UDP connection
import time
import threading
import queue

#
# Server
#
class Connection:
    def __init__(self, client_addr):
        self.client_addr = client_addr
        self.expected_seq = 0
        self.buffer = b""

class Server:
    def init(self, src_port, receive_buffer_size):
        """
        initialize the server, create the UDP connection, and configure the receive buffer

        arguments:
        src_port -- the port the server is using to receive segments
        receive_buffer_size -- the maximum size of the receive buffer
        """
        self.src_port = src_port
        self.receive_buffer_size = receive_buffer_size
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.bind(("", src_port))
        self.client_conn = None  # Will hold the Connection instance once a client connects
        # Open log file for recording behaviors (log_<port>.txt)
        self.log = open(f"log_{src_port}.txt", "w")
        self.running = True
        self.segment_queue = queue.Queue()
        self.data_cond = threading.Condition()
        self.handshake_cond = threading.Condition()
        self.handshake_done = False
        self.rcv_thread = threading.Thread(target=self.rcv_handler, daemon=True)
        self.sgmnt_thread = threading.Thread(target=self.sgmnt_handler, daemon=True)
        self.rcv_thread.start()
        self.sgmnt_thread.start()

    def log_event(self, time_str, src_port, dst_port, seq, ack, seg_type, payload_length):
        # Log format: <time> <src_port> <dst_port> <seq> <ack> <type> <payload_length>
        line = f"{time_str} {src_port} {dst_port} {seq} {ack} {seg_type} {payload_length}\n"
        self.log.write(line)
        self.log.flush()

    def current_time(self):
        # Return current UTC time in the required format (YYYY-MM-DD HH:MM:SS.mmm)
        t = time.gmtime()
        ms = int((time.time() % 1) * 1000)
        return time.strftime("%Y-%m-%d %H:%M:%S", t) + f".{ms:03d}"

    def create_segment(self, seq, ack, seg_type, payload):
        # Create a segment in the format: seq|ack|type|checksum|payload
        checksum = sum(payload) % 256
        header = f"{seq}|{ack}|{seg_type}|{checksum}|".encode()
        return header + payload

    def parse_segment(self, data):
        # Parse a segment formatted as: seq|ack|type|checksum|payload
        try:
            parts = data.split(b'|', 4)
            seq = int(parts[0].decode())
            ack = int(parts[1].decode())
            seg_type = parts[2].decode()
            checksum = int(parts[3].decode())
            payload = b""
            if len(parts) == 5:
                payload = parts[4]
            if checksum != (sum(payload) % 256):
                return None
            return {"seq": seq, "ack": ack, "type": seg_type, "payload": payload}
        except Exception:
            return None

    def rcv_handler(self):
        while self.running:
            try:
                data, addr = self.sock.recvfrom(4096)
            except:
                continue
            self.segment_queue.put((data, addr))

    def sgmnt_handler(self):
        while self.running:
            try:
                data, addr = self.segment_queue.get(timeout=1)
            except queue.Empty:
                continue
            segment = self.parse_segment(data)
            if not segment:
                continue
            if not self.handshake_done:
                if segment["type"] == "SYN":
                    self.log_event(self.current_time(), self.src_port, addr[1], segment["seq"], segment["ack"], segment["type"], len(segment["payload"]))
                    conn = Connection(addr)
                    conn.expected_seq = segment["seq"] + 1  # Assuming SYN occupies one sequence number
                    self.client_conn = conn
                    syn_ack = self.create_segment(0, conn.expected_seq, "SYN-ACK", b"")
                    self.sock.sendto(syn_ack, addr)
                    self.log_event(self.current_time(), self.src_port, addr[1], 0, conn.expected_seq, "SYN-ACK", 0)
                elif segment["type"] == "ACK" and self.client_conn and not self.handshake_done:
                    self.log_event(self.current_time(), self.src_port, addr[1], segment["seq"], segment["ack"], segment["type"], len(segment["payload"]))
                    with self.handshake_cond:
                        self.handshake_done = True
                        self.handshake_cond.notify_all()
            else:
                if segment["type"] == "PSH":
                    self.log_event(self.current_time(), self.src_port, addr[1], segment["seq"], segment["ack"], segment["type"], len(segment["payload"]))
                    if segment["seq"] == self.client_conn.expected_seq:
                        with self.data_cond:
                            self.client_conn.buffer += segment["payload"]
                            self.client_conn.expected_seq += len(segment["payload"])
                            self.data_cond.notify_all()
                        ack_seg = self.create_segment(0, self.client_conn.expected_seq, "ACK", b"")
                        self.sock.sendto(ack_seg, self.client_conn.client_addr)
                        self.log_event(self.current_time(), self.src_port, self.client_conn.client_addr[1], 0, self.client_conn.expected_seq, "ACK", 0)
                    else:
                        ack_seg = self.create_segment(0, self.client_conn.expected_seq, "ACK", b"")
                        self.sock.sendto(ack_seg, self.client_conn.client_addr)
                        self.log_event(self.current_time(), self.src_port, self.client_conn.client_addr[1], 0, self.client_conn.expected_seq, "ACK", 0)
                elif segment["type"] == "FIN":
                    self.log_event(self.current_time(), self.src_port, addr[1], segment["seq"], segment["ack"], segment["type"], len(segment["payload"]))
                    ack_seg = self.create_segment(0, segment["seq"] + 1, "ACK", b"")
                    self.sock.sendto(ack_seg, addr)
                    self.log_event(self.current_time(), self.src_port, addr[1], 0, segment["seq"] + 1, "ACK", 0)
                    fin_seg = self.create_segment(0, 0, "FIN", b"")
                    self.sock.sendto(fin_seg, addr)
                    self.log_event(self.current_time(), self.src_port, addr[1], 0, 0, "FIN", 0)
                    self.running = False
                    end_time = time.time() + 5
                    ack_received = False
                    while time.time() < end_time:
                        try:
                            self.sock.settimeout(0.5)
                            data, addr_final = self.sock.recvfrom(4096)
                            segment_final = self.parse_segment(data)
                            if segment_final and segment_final["type"] == "ACK":
                                self.log_event(self.current_time(), self.src_port, addr_final[1], segment_final["seq"], segment_final["ack"], segment_final["type"], len(segment_final["payload"]))
                                ack_received = True
                                break
                        except socket.timeout:
                            continue
                    if not ack_received:
                        self.log_event(self.current_time(), self.src_port, addr[1], 0, 0, "TIMEOUT_ACK", 0)
                    self.client_conn = None

    def accept(self):
        """
        accept a client request
        blocking until a client is accepted

        it should support protection against segment loss/corruption/reordering 

        return:
        the connection to the client 
        """
        with self.handshake_cond:
            while not self.handshake_done:
                self.handshake_cond.wait()
        return self.client_conn

    def receive(self, conn, length):
        """
        receive data from the given client
        blocking until the requested amount of data is received
        
        it should support protection against segment loss/corruption/reordering 
        the client should never overwhelm the server given the receive buffer size

        arguments:
        conn -- the connection to the client
        length -- the number of bytes to receive

        return:
        data -- the bytes received from the client, guaranteed to be in its original order
        """
        data_buffer = b""
        with self.data_cond:
            while len(conn.buffer) < length:
                self.data_cond.wait(timeout=1.0)
            data = conn.buffer[:length]
            conn.buffer = conn.buffer[length:]
            return data

    def close(self):
        """
        close the server and the client if it is still connected
        blocking until the connection is closed
        """
        start_time = time.time()
        while self.running and time.time() - start_time < 10:
            time.sleep(0.1)
        self.running = False
        self.rcv_thread.join(timeout=2)
        self.sgmnt_thread.join(timeout=2)
        self.sock.close()
        self.log_event(self.current_time(), self.src_port, "-", 0, 0, "CLOSE", 0)
        self.log.close()
