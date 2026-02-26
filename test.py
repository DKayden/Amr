import socket
import threading
import time
from typing import Tuple

from config import SOCKET_HOST, SOCKET_PORT
from socket_server import SocketServer


def _run_test_client(server_addr: Tuple[str, int]) -> None:
    """Client test: kết nối tới server và in ra mọi message nhận được."""
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(5.0)
    print(f"[CLIENT] Connecting to {server_addr[0]}:{server_addr[1]} ...")
    sock.connect(server_addr)
    print("[CLIENT] Connected, waiting for messages from server ...")

    try:
        buf = ""
        while True:
            chunk = sock.recv(4096)
            if not chunk:
                print("[CLIENT] Server closed connection.")
                break
            buf += chunk.decode("utf-8", errors="replace")
            while True:
                nl = buf.find("\n")
                if nl < 0:
                    break
                line = buf[:nl]
                buf = buf[nl + 1 :]
                if not line.strip():
                    continue
                print(f"[CLIENT] Received line: {line}")
    except socket.timeout:
        print("[CLIENT] Timeout waiting for data from server.")
    finally:
        sock.close()
        print("[CLIENT] Socket closed.")


def test_server_client_do_message() -> None:
    """
    Hàm test:
    - Start server socket (dùng SocketServer đã viết).
    - Tạo 1 client kết nối tới server.
    - Server gửi message {"DO":[0,0,0,0]} tới client.
    """
    # Server bind vào SOCKET_HOST (thường là "0.0.0.0" để lắng nghe trên mọi interface)
    server = SocketServer(host=SOCKET_HOST, port=SOCKET_PORT)
    server.start()
    print(f"[TEST] Server started on {SOCKET_HOST}:{SOCKET_PORT}")

    # Client KHÔNG được connect vào "0.0.0.0".
    # Nếu SOCKET_HOST = "0.0.0.0" thì dùng "127.0.0.1" để test local.
    client_host = "127.0.0.1" if SOCKET_HOST == "0.0.0.0" else SOCKET_HOST

    client_thread = threading.Thread(
        target=_run_test_client,
        args=((client_host, SOCKET_PORT),),
        daemon=True,
    )
    client_thread.start()

    # Đợi client connect vào server
    time.sleep(1.0)

    # Vòng lặp nhập từ bàn phím để gửi DO.
    # - Gõ: 4 số (0/1) cách nhau bởi dấu cách, ví dụ: "1 0 0 1"  -> gửi cho TẤT CẢ client (broadcast)
    # - Gõ: "cid:<client_id> 1 0 0 1"                           -> gửi CHỈ cho 1 client cụ thể
    # - Gõ: "list"                                              -> in danh sách client_id đang kết nối
    # - Gõ: "exit"                                              -> thoát
    try:
        while True:
            user_inp = input(
                'Nhập DO ("1 0 0 1" / "cid:<client_id> 1 0 0 1" / "list" / "exit"): '
            ).strip()
            if not user_inp:
                continue
            if user_inp.lower() == "exit":
                print("[TEST] Exit command received. Stopping server...")
                break
            if user_inp.lower() == "list":
                # In danh sách client đang kết nối
                from socket_server import SocketServer as _SS  # tránh cảnh báo import không dùng
                # Truy cập danh sách client hiện tại
                try:
                    clients_repr = []
                    # type: ignore[attr-defined] do đây là test script, chấp nhận truy cập nội bộ
                    with server._clients_lock:  # type: ignore[attr-defined]
                        for cid, c in server._clients.items():  # type: ignore[attr-defined]
                            clients_repr.append(f"{cid} ({c.addr[0]}:{c.addr[1]})")
                    if not clients_repr:
                        print("  -> Chưa có client nào kết nối.")
                    else:
                        print("  -> Danh sách client_id đang kết nối:")
                        for item in clients_repr:
                            print("     -", item)
                except Exception as exc:  # phòng trường hợp thay đổi internal
                    print(f"  -> Không đọc được danh sách client: {exc}")
                continue

            target_client_id: str | None = None

            # Cú pháp gửi riêng cho 1 client: cid:<client_id> 1 0 0 1
            if user_inp.lower().startswith("cid:"):
                first, *rest = user_inp.split(maxsplit=1)
                target_client_id = first[4:]  # phần sau "cid:"
                if not target_client_id:
                    print("  -> Thiếu client_id sau 'cid:'. Ví dụ: cid:abcd1234 1 0 0 1")
                    continue
                if not rest:
                    print("  -> Thiếu dữ liệu DO. Ví dụ: cid:abcd1234 1 0 0 1")
                    continue
                do_part = rest[0]
            else:
                # Mặc định: broadcast tới tất cả client
                do_part = user_inp

            parts = do_part.replace(",", " ").split()
            if len(parts) != 4 or any(p not in {"0", "1"} for p in parts):
                print("  -> Giá trị không hợp lệ. Vui lòng nhập đúng 4 số 0/1.")
                continue

            do_values = [int(p) for p in parts]
            payload = {"DO": do_values}

            if target_client_id is None:
                # Gửi broadcast
                sent = server.broadcast(payload)
                print(f"[TEST] Server broadcast {payload} to {sent} client(s).")
            else:
                # Gửi chỉ tới một client cụ thể
                ok = server.send(target_client_id, payload)
                if ok:
                    print(f"[TEST] Server sent {payload} to client {target_client_id}.")
                else:
                    print(f"[TEST] Không tìm thấy hoặc gửi không được tới client_id={target_client_id}.")
    finally:
        server.stop()
        print("[TEST] Server stopped.")


def test_get_client_id() -> None:
    """
    Kiểm tra function _get_client_id trong SocketServer:
    - Tạo server và 1 client kết nối tới.
    - Lấy một ClientConnection từ server._clients.
    - Gọi server._get_client_id(client) và so sánh với client.client_id.
    """
    server = SocketServer(host=SOCKET_HOST, port=SOCKET_PORT)
    server.start()
    print(f"[TEST_GET_ID] Server started on {SOCKET_HOST}:{SOCKET_PORT}")

    # Tạo một client TCP đơn giản chỉ để thiết lập kết nối
    client_host = "127.0.0.1" if SOCKET_HOST == "0.0.0.0" else SOCKET_HOST
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(5.0)
    sock.connect((client_host, SOCKET_PORT))
    print(f"[TEST_GET_ID] Client connected to {client_host}:{SOCKET_PORT}")

    # Đợi server chấp nhận kết nối và thêm vào _clients
    time.sleep(0.5)

    try:
        with server._clients_lock:  # type: ignore[attr-defined]
            clients = list(server._clients.values())  # type: ignore[attr-defined]
            print(f"[TEST_GET_ID] clients: {clients}")

        if not clients:
            print("[TEST_GET_ID] Không tìm thấy client nào trong server._clients.")
        else:
            # client = clients[0]
            # print(f"[TEST_GET_ID] client: {client}")
            # cid_attr = client.client_id
            # cid_func = server._get_client_id(client)  # type: ignore[attr-defined]
            # print(f"[TEST_GET_ID] client.client_id      = {cid_attr}")
            # print(f"[TEST_GET_ID] _get_client_id(client) = {cid_func}")
            # if cid_attr == cid_func:
            #     print("[TEST_GET_ID] OK: _get_client_id trả về đúng client_id.")
            # else:
            #     print("[TEST_GET_ID] FAIL: _get_client_id trả về sai client_id.")

            ip = "192.168.0.27"
            # Chờ cho đến khi có client + message từ IP này (tối đa 10s)
            timeout_s = 10.0
            interval_s = 0.5
            deadline = time.time() + timeout_s

            cid: str | None = None
            messages: dict = {}

            while time.time() < deadline:
                cid = server.get_client_id_by_ip(ip)
                messages = server.get_messages_by_ip(ip)
                if cid is not None and messages:
                    break
                time.sleep(interval_s)

            if cid is None:
                print(f"[TEST_GET_ID] Không tìm thấy client với IP {ip} trong {timeout_s} giây.")
            else:
                print(f"[TEST_GET_ID] client_id: {cid}")

            if not messages:
                print(f"[TEST_GET_ID] Không nhận được message nào từ {ip} trong {timeout_s} giây.")
            else:
                print(f"[TEST_GET_ID] messages: {messages}")
                di_data = messages.get("DI")
                print(f"[TEST_GET_ID] DI data: {di_data}")
                for i in range(len(di_data)):
                    print(f"[TEST_GET_ID] DI data {i}: {di_data[i]}")

    finally:
        try:
            sock.close()
        except OSError:
            pass
        server.stop()
        print("[TEST_GET_ID] Server stopped.")

if __name__ == "__main__":
    # Chạy test interactive gửi DO
    # test_server_client_do_message()
    test_get_client_id()