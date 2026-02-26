import argparse
import json
import logging
import signal
import socket
import threading
import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, Optional, Tuple


JsonDict = Dict[str, Any]


def _now_ms() -> int:
    return int(time.time() * 1000)


def _json_dumps(obj: Any) -> bytes:
    return (json.dumps(obj, ensure_ascii=False, separators=(",", ":")) + "\n").encode("utf-8")


def _safe_json_loads(line: str) -> Optional[JsonDict]:
    line = line.strip()
    if not line:
        return None
    try:
        data = json.loads(line)
        return data if isinstance(data, dict) else None
    except json.JSONDecodeError:
        return None


@dataclass
class ClientConnection:
    client_id: str
    sock: socket.socket
    addr: Tuple[str, int]
    created_at_ms: int = field(default_factory=_now_ms)
    last_seen_ms: int = field(default_factory=_now_ms)
    name: str = ""
    send_lock: threading.Lock = field(default_factory=threading.Lock, repr=False)
    closed: threading.Event = field(default_factory=threading.Event, repr=False)

    def send_json(self, payload: JsonDict) -> None:
        data = _json_dumps(payload)
        with self.send_lock:
            self.sock.sendall(data)

    def close(self) -> None:
        if self.closed.is_set():
            return
        self.closed.set()
        try:
            self.sock.shutdown(socket.SHUT_RDWR)
        except OSError:
            pass
        try:
            self.sock.close()
        except OSError:
            pass


class SocketServer:
    """
    TCP socket server để giao tiếp nhiều client.

    Giao thức: mỗi message là 1 JSON object trên 1 dòng (newline-delimited JSON).
    Ví dụ client gửi: {"type":"ping","id":"123"}
    Server trả: {"type":"pong","id":"123","ts":...}
    """

    def __init__(
        self,
        host: str = "0.0.0.0",
        port: int = 502,
        *,
        backlog: int = 128,
        recv_bufsize: int = 4096,
        client_socket_timeout_s: float = 1.0,
        logger: Optional[logging.Logger] = None,
    ) -> None:
        self.host = host
        self.port = port
        self.backlog = backlog
        self.recv_bufsize = recv_bufsize
        self.client_socket_timeout_s = client_socket_timeout_s
        self.log = logger or logging.getLogger("socket_server")

        self._server_sock: Optional[socket.socket] = None
        self._stop_event = threading.Event()

        self._clients: Dict[str, ClientConnection] = {}
        self._clients_lock = threading.Lock()

        self._state: Dict[str, Any] = {}
        self._state_lock = threading.Lock()

        self._accept_thread: Optional[threading.Thread] = None

    def start(self) -> None:
        if self._server_sock is not None:
            return

        server_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        server_sock.bind((self.host, self.port))
        server_sock.listen(self.backlog)
        server_sock.settimeout(1.0)

        self._server_sock = server_sock
        self._stop_event.clear()

        self._accept_thread = threading.Thread(target=self._accept_loop, name="accept_loop", daemon=True)
        self._accept_thread.start()

        self.log.info("Socket server listening on %s:%s", self.host, self.port)

    def stop(self) -> None:
        self._stop_event.set()

        if self._server_sock is not None:
            try:
                self._server_sock.close()
            except OSError:
                pass
            self._server_sock = None

        with self._clients_lock:
            clients = list(self._clients.values())
            self._clients.clear()

        for c in clients:
            c.close()

        if self._accept_thread and self._accept_thread.is_alive():
            self._accept_thread.join(timeout=2.0)

        self.log.info("Socket server stopped")

    def send(self, client_id: str, payload: JsonDict) -> bool:
        client = self._get_client(client_id)
        if not client:
            return False
        try:
            client.send_json(payload)
            return True
        except OSError:
            self._drop_client(client_id)
            return False

    def broadcast(self, payload: JsonDict, *, exclude_client_id: Optional[str] = None) -> int:
        with self._clients_lock:
            targets = [c for cid, c in self._clients.items() if cid != exclude_client_id]

        sent = 0
        for c in targets:
            try:
                c.send_json(payload)
                sent += 1
            except OSError:
                self._drop_client(c.client_id)
        return sent

    def _accept_loop(self) -> None:
        assert self._server_sock is not None
        while not self._stop_event.is_set():
            try:
                sock, addr = self._server_sock.accept()
            except socket.timeout:
                continue
            except OSError:
                break

            sock.settimeout(self.client_socket_timeout_s)
            client_id = uuid.uuid4().hex
            client = ClientConnection(client_id=client_id, sock=sock, addr=addr)
            with self._clients_lock:
                self._clients[client_id] = client

            self.log.info("Client connected id=%s addr=%s:%s", client_id, addr[0], addr[1])
            t = threading.Thread(
                target=self._client_loop,
                args=(client,),
                name=f"client_{client_id[:8]}",
                daemon=True,
            )
            t.start()

            try:
                client.send_json({"type": "welcome", "client_id": client_id, "ts": _now_ms()})
            except OSError:
                self._drop_client(client_id)

    def _client_loop(self, client: ClientConnection) -> None:
        buf = ""
        try:
            while not self._stop_event.is_set() and not client.closed.is_set():
                try:
                    chunk = client.sock.recv(self.recv_bufsize)
                except socket.timeout:
                    continue
                except OSError:
                    break

                if not chunk:
                    break

                try:
                    as_text = chunk.decode("utf-8", errors="replace")

                except Exception:
                    as_text = "<decode_error>"
                # Log mọi dữ liệu thô nhận được từ client (không phụ thuộc ký tự xuống dòng)
                # self.log.info(
                #     "RECV from %s %s:%s len=%d raw_hex=%s text=%s",
                #     client.client_id,
                #     client.addr[0],
                #     client.addr[1],
                #     len(chunk),
                #     chunk.hex(" "),
                #     as_text,
                # )
                if not hasattr(client, 'messages'):
                    client.messages = {}
                if not client.messages or client.messages != as_text:
                    client.messages = _safe_json_loads(as_text)
             
        finally:
            self._drop_client(client.client_id)

    def _handle_message(self, client: ClientConnection, msg: JsonDict) -> None:
        msg_type = str(msg.get("type") or "")
        req_id = msg.get("id")

        if msg_type == "ping":
            client.send_json({"type": "pong", "id": req_id, "ts": _now_ms()})
            return

        if msg_type == "hello":
            name = msg.get("name")
            if isinstance(name, str):
                client.name = name
            client.send_json({"type": "hello_ack", "id": req_id, "client_id": client.client_id, "ts": _now_ms()})
            return

        if msg_type == "set":
            key = msg.get("key")
            value = msg.get("value")
            if not isinstance(key, str) or not key:
                self._safe_send_error(client, "bad_request", req_id=req_id, details="key must be non-empty string")
                return
            with self._state_lock:
                self._state[key] = value
            client.send_json({"type": "set_ack", "id": req_id, "key": key, "ts": _now_ms()})
            return

        if msg_type == "get":
            key = msg.get("key")
            if not isinstance(key, str) or not key:
                self._safe_send_error(client, "bad_request", req_id=req_id, details="key must be non-empty string")
                return
            with self._state_lock:
                value = self._state.get(key)
            client.send_json({"type": "get_ack", "id": req_id, "key": key, "value": value, "ts": _now_ms()})
            return

        if msg_type == "broadcast":
            payload = msg.get("payload")
            if not isinstance(payload, dict):
                self._safe_send_error(client, "bad_request", req_id=req_id, details="payload must be JSON object")
                return
            count = self.broadcast(
                {"type": "signal", "from": client.client_id, "payload": payload, "ts": _now_ms()},
                exclude_client_id=client.client_id,
            )
            client.send_json({"type": "broadcast_ack", "id": req_id, "sent": count, "ts": _now_ms()})
            return

        # Bạn tùy biến xử lý business ở đây:
        # - parse dữ liệu thiết bị
        # - gọi PLC/Modbus/HTTP nội bộ
        # - và chủ động gửi tín hiệu cho client bằng self.send()/self.broadcast()
        self.log.info("Message from id=%s name=%s type=%s msg=%s", client.client_id, client.name, msg_type, msg)
        client.send_json({"type": "ack", "id": req_id, "received_type": msg_type, "ts": _now_ms()})

    def _safe_send_error(self, client: ClientConnection, code: str, *, req_id: Any = None, details: str = "") -> None:
        try:
            client.send_json({"type": "error", "id": req_id, "code": code, "details": details, "ts": _now_ms()})
        except OSError:
            self._drop_client(client.client_id)

    def _get_client(self, client_id: str) -> Optional[ClientConnection]:
        with self._clients_lock:
            return self._clients.get(client_id)

    def _drop_client(self, client_id: str) -> None:
        with self._clients_lock:
            client = self._clients.pop(client_id, None)
        if not client:
            return
        client.close()
        self.log.info("Client disconnected id=%s addr=%s:%s", client_id, client.addr[0], client.addr[1])

    def _get_client_id(self, client: 'ClientConnection') -> str:
        """
        Trả về client_id của một client connection.
        """
        return getattr(client, 'client_id', None)
        
    def get_client_id_by_ip(self, ip_addr: str) -> Optional[str]:
        """
        Trả về client_id ứng với địa chỉ IP truyền vào.
        Nếu không tìm thấy, trả về None.
        """
        with self._clients_lock:
            for client_id, client in self._clients.items():
                if getattr(client, 'addr', None) and client.addr[0] == ip_addr:
                    return client_id
        return None


    def get_messages_by_ip(self, ip_addr: str) -> dict:
        """
        Lấy message cuối cùng đã nhận từ client với địa chỉ IP cho trước,
        và cố gắng trả về dưới dạng dict.
        - Nếu không tìm thấy client với IP đó, trả về {}.
        - Nếu client không có thuộc tính/messages, trả về {}.
        - Nếu message là chuỗi JSON hợp lệ, parse và trả về dict.
        - Nếu message không phải JSON hợp lệ, trả về {"raw": <message>}.
        """
        with self._clients_lock:
            for client in self._clients.values():
                if getattr(client, "addr", None) and client.addr[0] == ip_addr:
                    msg = getattr(client, "messages", None)
                    if msg is None:
                        return {}
                    if isinstance(msg, dict):
                        return msg
                    if isinstance(msg, str):
                        parsed = _safe_json_loads(msg)
                        if parsed is not None:
                            return parsed
                        return {"raw": msg}
        return {}

def _configure_logging(level: str) -> None:
    logging.basicConfig(
        level=getattr(logging, level.upper(), logging.INFO),
        format="%(asctime)s %(levelname)s %(name)s - %(message)s",
    )
def main() -> int:
    parser = argparse.ArgumentParser(description="TCP Socket Server (newline-delimited JSON)")
    parser.add_argument("--host", default="0.0.0.0")
    parser.add_argument("--port", type=int, default=502)
    parser.add_argument("--log-level", default="INFO", choices=["DEBUG", "INFO", "WARNING", "ERROR"])
    args = parser.parse_args()

    _configure_logging(args.log_level)
    server = SocketServer(host=args.host, port=args.port)

    def _shutdown(*_: Any) -> None:
        server.stop()

    try:
        signal.signal(signal.SIGINT, _shutdown)
        signal.signal(signal.SIGTERM, _shutdown)
    except Exception:
        pass

    server.start()

    try:
        while True:
            time.sleep(0.5)
    except KeyboardInterrupt:
        pass
    finally:
        server.stop()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())