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
        self.sock.settimeout(0.5)
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
        # Return current UTC time in the format: YYYY-MM-DD HH:MM:SS.mmm
        t = time.gmtime()
        ms = int((time.time() % 1) * 1000)
        return time.strftime("%Y-%m-%d %H:%M:%S", t) + f".{ms:03d}"

    def log_event(self, time_str, src_port, dst_port, seq, ack, seg_type, payload_length):
        # Log format: <time> <src_port> <dst_port> <seq> <ack> <type> <payload_length>
        line = f"{time_str} {src_port} {dst_port} {seq} {ack} {seg_type} {payload_length}\n"
        self.log.write(line)
        self.log.flush()

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
        base_seq = self.seq
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
        window_size = 4
        sample_header = f"{self.seq}|{self.ack}|PSH|".encode()
        header_len = len(sample_header) + len(str(0)) + 1
        max_payload = self.segment_size - header_len
        segments = []
        seq_start = self.seq
        temp_seq = self.seq
        for i in range(0, len(data), max_payload):
            payload = data[i:i+max_payload]
            segments.append((temp_seq, payload))
            temp_seq += len(payload)
        total_data_length = temp_seq - seq_start
        base_index = 0
        next_index = 0
        outstanding = {}
        timeout = 1.0
        total_sent = 0
        while base_index < len(segments):
            while next_index < len(segments) and next_index - base_index < window_size:
                seg_seq, payload = segments[next_index]
                segment = self.create_segment(seg_seq, self.ack, "PSH", payload)
                self.sock.sendto(segment, (self.dst_addr, self.dst_port))
                self.log_event(self.current_time(), self.src_port, self.dst_port, seg_seq, self.ack, "PSH", len(payload))
                outstanding[next_index] = (segment, time.time())
                next_index += 1
            with self.ack_cond:
                self.ack_cond.wait(timeout=0.1)
            with self.ack_cond:
                new_base = base_index
                for i in range(base_index, len(segments)):
                    seg_seq, payload = segments[i]
                    if self.last_ack >= seg_seq + len(payload):
                        new_base = i + 1
                    else:
                        break
                if new_base > base_index:
                    for i in range(base_index, new_base):
                        total_sent += len(segments[i][1])
                        if i in outstanding:
                            del outstanding[i]
                    base_index = new_base
            if outstanding:
                oldest_index = min(outstanding.keys())
                _, send_time = outstanding[oldest_index]
                if time.time() - send_time > timeout:
                    for i in range(base_index, next_index):
                        seg_seq, payload = segments[i]
                        segment = self.create_segment(seg_seq, self.ack, "PSH", payload)
                        self.sock.sendto(segment, (self.dst_addr, self.dst_port))
                        self.log_event(self.current_time(), self.src_port, self.dst_port, seg_seq, self.ack, "PSH-REXMIT", len(payload))
                        outstanding[i] = (segment, time.time())
        self.ack = self.last_ack
        self.seq = seq_start + total_data_length
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
        start_time = time.time()
        while not self.fin_event.wait(timeout=1.0):
            if time.time() - start_time > 10:
                break
            self.sock.sendto(fin_segment, (self.dst_addr, self.dst_port))
            self.log_event(self.current_time(), self.src_port, self.dst_port, self.seq, self.ack, "FIN-REXMIT", 0)
        self.seq += 1
        final_ack = self.create_segment(self.seq, self.last_ack + 1, "ACK", b"")
        for _ in range(3):
            self.sock.sendto(final_ack, (self.dst_addr, self.dst_port))
            self.log_event(self.current_time(), self.src_port, self.dst_port, self.seq, self.last_ack + 1, "ACK", 0)
            time.sleep(0.5)
        self.sock.sendto(final_ack, (self.dst_addr, self.dst_port))
        self.log_event(self.current_time(), self.src_port, self.dst_port, self.seq, self.last_ack + 1, "ACK", 0)
        self.connected = False
        self.running = False
        self.rcv_thread.join()
        self.sock.close()
        self.log_event(self.current_time(), self.src_port, "-", self.seq, self.ack, "CLOSE", 0)
        self.log.close()
