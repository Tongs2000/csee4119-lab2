# Columbia University - CSEE 4119 Computer Networks
# Assignment 2 - Mini Reliable Transport Protocol
#
# mrt_client.py - defining client APIs of the mini reliable transport protocol
#

import socket # for UDP connection
import time
import random
import threading

class Client:
    def init(self, src_port, dst_addr, dst_port, segment_size):
        """
        initialize the client and create the client UDP channel

        arguments:
        src_port -- the port the client is using to send segments
        dst_addr -- the address of the server/network simulator
        dst_port -- the port of the server/network simulator
        segment_size -- the maximum size of a segment (including the header)
        """
        self.src_port = src_port
        self.dst_addr = dst_addr
        self.dst_port = dst_port
        self.segment_size = segment_size
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.bind(("", src_port))
        self.sock.settimeout(1.0)
        self.log = open(f"log_{src_port}.txt", "w")
        self.seq = random.randint(0, 1000)
        self.ack = 0
        self.connected = False
        self.handshake_event = threading.Event()
        self.ack_cond = threading.Condition()
        self.last_ack = 0
        self.fin_event = threading.Event()
        self.running = True
        self.rcv_thread = threading.Thread(target=self.rcv_handler, daemon=True)
        self.rcv_thread.start()

    def current_time(self):
        t = time.gmtime()
        ms = int((time.time() % 1) * 1000)
        return time.strftime("%Y-%m-%d %H:%M:%S", t) + f".{ms:03d}"

    def log_event(self, time_str, src_port, dst_port, seq, ack, seg_type, payload_length):
        line = f"{time_str} {src_port} {dst_port} {seq} {ack} {seg_type} {payload_length}\n"
        self.log.write(line)
        self.log.flush()

    def create_segment(self, seq, ack, seg_type, payload):
        header = f"{seq}|{ack}|{seg_type}|".encode()
        return header + payload

    def parse_segment(self, data):
        try:
            parts = data.split(b'|', 3)
            seq = int(parts[0].decode())
            ack = int(parts[1].decode())
            seg_type = parts[2].decode()
            payload = b""
            if len(parts) == 4:
                payload = parts[3]
            return {"seq": seq, "ack": ack, "type": seg_type, "payload": payload}
        except Exception:
            return None

    def rcv_handler(self):
        while self.running:
            try:
                data, addr = self.sock.recvfrom(4096)
            except socket.timeout:
                continue
            segment = self.parse_segment(data)
            if not segment:
                continue
            if segment["type"] == "SYN-ACK" and not self.handshake_event.is_set():
                self.log_event(self.current_time(), self.src_port, self.dst_port, segment["seq"], segment["ack"], segment["type"], len(segment["payload"]))
                with self.ack_cond:
                    self.last_ack = segment["ack"]
                self.handshake_event.set()
            elif segment["type"] == "ACK":
                self.log_event(self.current_time(), self.src_port, self.dst_port, segment["seq"], segment["ack"], segment["type"], len(segment["payload"]))
                with self.ack_cond:
                    self.last_ack = segment["ack"]
                    self.ack_cond.notify_all()
            elif segment["type"] == "FIN":
                self.log_event(self.current_time(), self.src_port, self.dst_port, segment["seq"], segment["ack"], segment["type"], len(segment["payload"]))
                with self.ack_cond:
                    self.last_ack = segment["ack"]
                    self.ack_cond.notify_all()
                self.fin_event.set()

    def connect(self):
        """
        connect to the server
        blocking until the connection is established

        it should support protection against segment loss/corruption/reordering 
        """
        syn_segment = self.create_segment(self.seq, 0, "SYN", b"")
        self.sock.sendto(syn_segment, (self.dst_addr, self.dst_port))
        self.log_event(self.current_time(), self.src_port, self.dst_port, self.seq, 0, "SYN", 0)
        while not self.handshake_event.wait(timeout=1.0):
            self.sock.sendto(syn_segment, (self.dst_addr, self.dst_port))
            self.log_event(self.current_time(), self.src_port, self.dst_port, self.seq, 0, "SYN-REXMIT", 0)
        with self.ack_cond:
            self.ack = self.last_ack
        ack_segment = self.create_segment(self.seq, self.ack, "ACK", b"")
        self.sock.sendto(ack_segment, (self.dst_addr, self.dst_port))
        self.log_event(self.current_time(), self.src_port, self.dst_port, self.seq, self.ack, "ACK", 0)
        self.seq += 1
        self.connected = True

    def send(self, data):
        """
        send a chunk of data of arbitrary size to the server
        blocking until all data is sent

        it should support protection against segment loss/corruption/reordering and flow control

        arguments:
        data -- the bytes to be sent to the server
        """
        if not self.connected:
            return 0
        total_sent = 0
        sample_header = f"{self.seq}|{self.ack}|PSH|".encode()
        header_len = len(sample_header)
        max_payload = self.segment_size - header_len
        segments = [data[i:i+max_payload] for i in range(0, len(data), max_payload)]
        for payload in segments:
            segment = self.create_segment(self.seq, self.ack, "PSH", payload)
            sent = False
            while not sent:
                self.sock.sendto(segment, (self.dst_addr, self.dst_port))
                self.log_event(self.current_time(), self.src_port, self.dst_port, self.seq, self.ack, "PSH", len(payload))
                with self.ack_cond:
                    self.ack_cond.wait(timeout=1.0)
                    if self.last_ack >= self.seq + len(payload):
                        self.log_event(self.current_time(), self.src_port, self.dst_port, 0, self.last_ack, "ACK", 0)
                        self.seq = self.last_ack
                        total_sent += len(payload)
                        sent = True
                    else:
                        self.sock.sendto(segment, (self.dst_addr, self.dst_port))
                        self.log_event(self.current_time(), self.src_port, self.dst_port, self.seq, self.ack, "PSH-REXMIT", len(payload))
            self.ack = self.last_ack
        return total_sent

    def close(self):
        """
        request to close the connection with the server
        blocking until the connection is closed
        """
        if not self.connected:
            return
        fin_segment = self.create_segment(self.seq, self.ack, "FIN", b"")
        self.sock.sendto(fin_segment, (self.dst_addr, self.dst_port))
        self.log_event(self.current_time(), self.src_port, self.dst_port, self.seq, self.ack, "FIN", 0)
        while not self.fin_event.wait(timeout=1.0):
            self.sock.sendto(fin_segment, (self.dst_addr, self.dst_port))
            self.log_event(self.current_time(), self.src_port, self.dst_port, self.seq, self.ack, "FIN-REXMIT", 0)
        final_ack = self.create_segment(self.seq, self.last_ack + 1, "ACK", b"")
        self.sock.sendto(final_ack, (self.dst_addr, self.dst_port))
        self.log_event(self.current_time(), self.src_port, self.dst_port, self.seq, self.last_ack + 1, "ACK", 0)
        self.connected = False
        self.running = False
        self.rcv_thread.join()
        self.sock.close()
        self.log_event(self.current_time(), self.src_port, "-", self.seq, self.ack, "CLOSE", 0)
        self.log.close()
