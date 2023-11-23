import socket
import threading
import pickle
from typing import Tuple
from typing import Dict
from typing import List

class ChatRoom:
    def __init__(self, title: str, max_participants: int) -> None:
        self.title: str = title
        self.max_participants: int = max_participants
        self.host_key: str = None
        self.participants: List[str] = []

    def add_participant(self, client_address: Tuple[str, int]) -> bool:
        if len(self.participants) < self.max_participants:
            client_key: str = f"{client_address[0]}:{client_address[1]}"
            self.participants.append(client_key)

            # 作成者はホストとして登録
            if len(self.participants) == 1:
                self.host_key = client_key

            return True
        else:
            return False

class ChatServer:
    def __init__(self, server_address: str, server_port: int) -> None:
        self.server_address: str = server_address
        self.server_port: int = server_port
        self.server_tcp_socket: socket.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_tcp_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1) # already in useの回避
        self.chat_rooms: Dict[str, ChatRoom] = {}
        self.server_udp_socket: socket.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

    def start_tcp_server(self) -> None:
        try:
            self.setup_socket()
            print("Server is listening connection from client...")

            while True:
                self.receive_tcp_client()

        except KeyboardInterrupt:
            print("\nStopped by KeyboardInterrupt.")
        finally:
            # クライアントの接続待ちを終了
            print("\nServer stopped.")
            self.server_tcp_socket.close()

    def setup_socket(self) -> None:
        self.server_tcp_socket.bind((self.server_address, self.server_port))
        self.server_udp_socket.bind((self.server_address, self.server_port))
        self.server_tcp_socket.listen(5)

    def receive_tcp_client(self) -> None:
        # クライアントの受け付けはメインスレッドで行う
        client_connection, client_address = self.server_tcp_socket.accept()
        print(f"Received request from {client_address}.")

        # クライアントとの接続が確立した後は、クライアントごとに別々のスレッドで処理
        client_thread: threading.Thread = threading.Thread(target=self.handle_tcp_client, args=(client_connection, client_address))
        client_thread.daemon = True
        client_thread.start()

    def create_new_room(self, room_name: str, title: str, max_participants: str, client_connection: socket.socket) -> None:
        self.chat_rooms[room_name] = ChatRoom(title, int(max_participants))
        message = "Successfully created chat room."
        print(f"{message}")
        print(f"Room name: {room_name}")
        print(f"Title: {title}")
        print(f"Max partifipants: {max_participants}")
        client_connection.send(message.encode("utf-8"))

    def send_room_list(self, client_connection: socket.socket) -> None:
        client_connection.send(pickle.dumps(self.chat_rooms))

    def receive_udp_client(self, room_name: str) -> None:
        chat_room: ChatRoom = self.chat_rooms[room_name]
        data, client_address = self.server_udp_socket.recvfrom(1024)

        if chat_room.add_participant(client_address):
            print(f"Success: {chat_room.participants}")
        else:
            print(f"Failed: {chat_room.participants}")

    def broadcast_message(self) -> None:
        while True:
            data, client_address = self.server_udp_socket.recvfrom(1024)

            if data:
                parts: List[str] = data.decode("utf-8").split(":")
                room_name: str = parts[0]
                message: str = parts[2]
                chat_room: ChatRoom = self.chat_rooms[room_name]
                sender: str = f"{client_address[0]}:{client_address[1]}"
                print(f"{chat_room.participants}")

                # 送信者以外にメッセージを送信する
                for participant in chat_room.participants:
                    client_address = participant.split(":")[0]
                    client_port = int(participant.split(":")[1])
                    if not participant == sender:
                        self.server_udp_socket.sendto(f"From {sender}\n>>> {message}".encode("utf-8"), (client_address, client_port))

    # TCPで受信するクライアントからのコマンドを処理
    def handle_tcp_client(self, client_connection: socket.socket, client_address: Tuple[str, int]) -> None:
        try:
            while True:
                data: str = client_connection.recv(1024).decode("utf-8")

                print(f"From client {client_address}: {data}")
                parts: List[str] = data.split(":")
                command: str = parts[1]

                # コマンドに応じた処理
                if command == "create":
                    self.create_new_room(parts[0], parts[2], parts[3], client_connection)

                elif command == "show":
                    self.send_room_list(client_connection)

                elif command == "join":
                    self.receive_udp_client(parts[0])
                    self.broadcast_message()
        finally:
            print("\nClient disconnected.")
            client_connection.close()

if __name__ == "__main__":
    server = ChatServer("localhost", 8888)
    server.start_tcp_server()
