import socket
import pickle
import threading
from server import ChatRoom
from typing import Dict

class ChatClient:
    def __init__(self, server_address: str, server_port: int) -> None:
        self.server_address: str = server_address
        self.server_port: int = server_port
        self.client_tcp_socket: socket.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.client_udp_socket: socket.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.belonging_room_name = None

    def connect_to_tcp_server(self) -> None:
        self.client_tcp_socket.connect((self.server_address, self.server_port))
        print(f"Successfully connected to {self.server_address}:{self.server_port}.")

    def create_new_room(self, room_name: str, title: str, max_participants: str) -> None:
        data: str = f"{room_name}:create:{title}:{max_participants}"
        self.client_tcp_socket.send(data.encode("utf-8"))
        received_message: str = self.client_tcp_socket.recv(1024).decode("utf-8")
        print(f"{received_message}")

        self.join_room(room_name)

    def connect_to_chat_room(self) -> None:
        # UDP接続のためにクライアントのアドレス情報を最初に渡す
        # initial_message: str = "Hello!"
        initial_message: str = "Hello!"
        initial_message_size: str = len(initial_message.encode("utf-8"))
        sent_message: bytes = f"{self.belonging_room_name}:{initial_message_size}:{initial_message}".encode("utf-8")
        self.client_udp_socket.sendto(sent_message, (self.server_address, self.server_port))

    def listen_message(self) -> None:
        while True:
            data, _ = self.client_udp_socket.recvfrom(1024)
            message: str = data.decode("utf-8")
            print(f"\n{message}")

    def show_all_rooms(self) -> None:
        data: str = f"_:show"
        self.client_tcp_socket.send(data.encode("utf-8"))

        # 既存のチャットルーム情報を受信、表示
        chat_rooms: Dict[str, ChatRoom] = pickle.loads(self.client_tcp_socket.recv(1024))

        if len(chat_rooms) > 0:
            print("Room List:")
            for room_name, chat_room in chat_rooms.items():
                print(f" - {room_name}")
                print(f"   - Host: TBD")
                print(f"   - Title: {chat_room.title}")
                print(f"   - Participants: {len(chat_room.participants)} / {chat_room.max_participants}")
        else:
            print("No room created yet.")

    def join_room(self, room_name: str) -> None:
        # connect_to_chat_room(), listen_message()を呼び出す
        # listen_message()は別スレッド
        self.belonging_room_name = room_name
        data: str = f"{room_name}:join"
        self.client_tcp_socket.send(data.encode("utf-8"))

        self.connect_to_chat_room()
        print(f"You're in '{room_name}'")
        listen_thread: threading.Thread = threading.Thread(target=self.listen_message)
        listen_thread.daemon = True
        listen_thread.start()
        self.send_message()

    def send_message(self) -> None:
        while True:
            message: str = input()
            message_size: str = len(message.encode("utf-8"))
            sent_message: bytes = f"{self.belonging_room_name}:{message_size}:{message}".encode("utf-8")
            self.client_udp_socket.sendto(sent_message, (self.server_address, self.server_port))

    def handle_command(self) -> None:
        try:
            while True:
                command: str = input("Enter command 'create/show/join/exit': ")

                if command == "create":
                    room_name: str = input("Enter room name: ")
                    title: str = input("Enter title: ")
                    max_participants: str = input("Enter max participants: ")
                    self.create_new_room(room_name, title, max_participants)

                elif command == "show":
                    self.show_all_rooms()

                elif command == "join":
                    if self.belonging_room_name:
                        print(f"You're already in '{self.belonging_room_name}'")
                    else:
                        room_name: str = input("Enter room name: ")
                        self.join_room(room_name)

                # elif command == "exit":
                #     print("Bye")
                #     break

                # else:
                #     print("Please enter 'create/join/exit'")

        except KeyboardInterrupt:
            print("\nStopped by KeyboardInterrupt.")

if __name__ == "__main__":
    client = ChatClient("127.0.0.1", 8888)
    client.connect_to_tcp_server()
    client.handle_command()

    print("\nClose client socket.")
    client.client_tcp_socket.close()

# クライアントが最初にチャットルームにUDP接続した際に、サーバーはクライアントのアドレス情報を取得する
