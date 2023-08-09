# funcchat.py. Update v2: Send file uni multi broadcast
import socket
import threading
import os
import shutil
import time

class FuncChat:
    def __init__(self, host, port):
        self.host = host
        self.port = port
        self.client_socket = None
        self.username = None
        self.groupname = None
        self.server_socket = None
        self.clients = {}
        self.lock = threading.Lock()

    def receive_messages(self, client_socket):
        while True:
            try:
                data = client_socket.recv(1024)
                if not data:
                    break
                print(data.decode("utf-8"))
            except:
                break

    def send_file(self, file_path):
        file_type = file_path.split(".")[-1].lower()
        file_size = os.path.getsize(file_path)
        message = f"!file {file_type} {file_size}"
        self.client_socket.send(message.encode("utf-8"))

        with open(file_path, "rb") as file:
            while True:
                data = file.read(1024)
                if not data:
                    break
                self.client_socket.send(data)

        print(f"File {file_path} sent successfully.")

    def receive_file(self, client_socket):
        while True:
            try:
                data = client_socket.recv(1024)
                if not data:
                    break
                decoded = data.decode("utf-8")

                if decoded.startswith("[file] "):
                    # Jika pesan berisi file, kita akan mengidentifikasi nama file dan ukuran file
                    parts = decoded.split(" ", 3)
                    filename = parts[1]
                    file_size = int(parts[2])
                    timestamp = time.strftime("%Y%m%d_%H%M%S")
                    base_name, extension = os.path.splitext(filename)
                    new_filename = f"{base_name}_{timestamp}{extension}"

                    with open(os.path.join("received", new_filename), "wb") as file:
                        remaining_bytes = file_size
                        while remaining_bytes > 0:
                            file_data = client_socket.recv(min(remaining_bytes, 1024))
                            if not file_data:
                                break
                            file.write(file_data)
                            remaining_bytes -= len(file_data)

                    print(f"Received file {filename}.")
                else:
                    print(decoded)
            except:
                break


    def handle_client(self, client_socket, client_address):
        try:
            #client_socket.send("Input your username: ".encode("utf-8"))
            self.username = client_socket.recv(1024).decode("utf-8").strip()

            #client_socket.send("Input your group name: ".encode("utf-8"))
            self.groupname = client_socket.recv(1024).decode("utf-8").strip()
            client_socket.send("Ketik /help untuk bantuan".encode("utf-8"))
            print("User {} from group {} connected from {}:{}".format(self.username, self.groupname, client_address[0], client_address[1]))

            with self.lock:
                self.clients[self.username] = (client_socket, self.groupname)

            while True:
                data = client_socket.recv(1024)
                if not data:
                    break
                
                decoded = data.decode("utf-8")

                if decoded.lower() == "exit":
                    raise KeyboardInterrupt
                
                elif decoded.startswith("/pc-"):
                    parts = decoded.split(" ")
                    recipient = parts[0][4:]
                    message = ' '.join(parts[1:-1])
                    username = parts[-1]
                    if recipient in self.clients:
                        recipient_socket, _ = self.clients[recipient]
                        message = "[Chat {}]: {}".format(username, message)
                        recipient_socket.send(message.encode("utf-8"))

                elif decoded.startswith("/gc"):
                    parts = decoded.split(" ")
                    groupname = parts[-2]
                    username = parts[-1]
                    message = ' '.join(parts[1:-2])
                    message = "[Group {}, @{}]: {}".format(groupname, username, message)
                    with self.lock:
                        for client, client_group in self.clients.values():
                            if client_group == groupname:
                                client.send(message.encode("utf-8"))


                elif decoded.startswith("/bc"):
                    words = decoded.split()
                    username = words[-1]
                    message = " ".join(words[1:-1])
                    message = "[Broadcast @{}]: {}".format(username, message)
                    with self.lock:
                        for client, client_group in self.clients.values():
                            client.send(message.encode("utf-8"))

                elif decoded.startswith("/file."):
                    # Jika command /file- diterima, kita akan mengidentifikasi tujuan (unicast)
                    parts = decoded.split(" ", 4)
                    recipient = parts[0][6:]
                    filename = parts[1]
                    file_size = int(parts[2])
                    username = parts[3]

                    with open(os.path.join("database", filename), "wb") as file:
                        remaining_bytes = file_size
                        while remaining_bytes > 0:
                            file_data = client_socket.recv(min(remaining_bytes, 1024))
                            if not file_data:
                                break
                            file.write(file_data)
                            remaining_bytes -= len(file_data)
                    print(f"Received file {filename} from {username}")

                    if recipient in self.clients:
                        recipient_socket, _ = self.clients[recipient]
                        file_message = f"[file] {filename} {file_size}"
                        recipient_socket.send(file_message.encode("utf-8"))

                        with open(os.path.join("database", filename), "rb") as file:
                            while True:
                                data = file.read(1024)
                                if not data:
                                    break
                                recipient_socket.send(data)

                    else:
                        print("User not found!")
                        
                    if username in self.clients:
                        username_socket, _ = self.clients[username]
                        notification = (f"File sent to {recipient}")
                        username_socket.send(notification.encode("utf-8"))
                
                elif decoded.startswith("/files-gc"):
                    # Jika command /file-gc diterima, kita akan mengirim file ke seluruh klien dalam kelompok (groupchat)
                    parts = decoded.split(" ")
                    groupname = parts[0][9:]
                    filename = parts[1]
                    file_size = int(parts[2])
                    username = parts[3]

                    received_filepath = os.path.join("database", os.path.basename(filename))
                    with open(received_filepath, "wb") as file:
                        remaining_bytes = file_size
                        while remaining_bytes > 0:
                            file_data = client_socket.recv(min(remaining_bytes, 1024))
                            if not file_data:
                                break
                            file.write(file_data)
                            remaining_bytes -= len(file_data)

                    print(f"File '{filename}' received from {username} in group {groupname}.")

                    # file_message = f"[Group {groupname}, @{username}]: Sending file '{filename}'"
                    with self.lock:
                        for client, client_group in self.clients.values():
                            if client_group == groupname and client != username:
                                # client.send(file_message.encode("utf-8"))
                                file_size_message = f"[file] {filename} {file_size}"
                                client.send(file_size_message.encode("utf-8"))
                    
                                    # Kirim ulang file ke seluruh klien dalam kelompok (groupchat) kecuali pengirim
                                with open(received_filepath, "rb") as file:
                                    while True:
                                        data = file.read(1024)
                                        if not data:
                                            break
                                        client.send(data)

                elif decoded.startswith("/files-bc"):
                    # Jika command /file-bc diterima, kita akan mengirim file ke seluruh klien yang terhubung (broadcast chat)
                    parts = decoded.split(" ")
                    filename = parts[1]
                    file_size = int(parts[2])
                    username = parts[3]

                    received_filepath = os.path.join("database", os.path.basename(filename))
                    with open(received_filepath, "wb") as file:
                        remaining_bytes = file_size
                        while remaining_bytes > 0:
                            file_data = client_socket.recv(min(remaining_bytes, 1024))
                            if not file_data:
                                break
                            file.write(file_data)
                            remaining_bytes -= len(file_data)

                    print(f"File '{filename}' received from {username} for broadcast.")

                    # file_message = f"[Broadcast @{username}]: Sending file '{filename}'"
                    with self.lock:
                        for client in self.clients.values():
                            if client != username:
                                # client.send(file_message.encode("utf-8"))
                                file_size_message = f"[file] {filename} {file_size}"
                                client.send(file_size_message.encode("utf-8"))
                    
                                    # Kirim ulang file ke seluruh klien dalam kelompok (groupchat) kecuali pengirim
                                with open(received_filepath, "rb") as file:
                                    while True:
                                        data = file.read(1024)
                                        if not data:
                                            break
                                        client.send(data)

                elif decoded.startswith("/help"):
                    help_message = """
/show: Menampilkan daftar User terhubung
/help: Menampilkan Legenda
/exit: Keluar dari Program
/pc-[username-tujuan] [pesan]: Pesan Unicast
/gc [pesan]: Pesan Multicast
/bc [pesan]: Pesan Broadcast
/file.[username-tujuan] [file.extension]: Unicast Send File
/files-gc [file.extension]: Multicast Send File
/files-bc [file.extension]: Broadcast Send File
        """
                    client_socket.send(help_message.encode("utf-8"))

                elif decoded.startswith("/show"):
                    users = "\n".join(self.clients.keys())
                    message = "[Server]: Connected users:\n{}".format(users)
                    client_socket.send(message.encode("utf-8"))

                else:
                    pass

        except KeyboardInterrupt:
            print("Server is closing...")
        except:
            pass
        finally:
            with self.lock:
                if self.username in self.clients:
                    del self.clients[self.username]
            client_socket.close()

    def start_server(self):
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.server_socket.bind((self.host, self.port))
        self.server_socket.listen(5)
        print("Server listening on {}:{}".format(self.host, self.port))

        try:
            while True:
                client_socket, addr = self.server_socket.accept()
                client_thread = threading.Thread(target=self.handle_client, args=(client_socket, addr))
                client_thread.start()
        except KeyboardInterrupt:
            print("Closing all connections...")
            with self.lock:
                for client, _ in self.clients.values():
                    client.close()

        self.server_socket.close()
        print("Server is closed.")

    def start_client(self):
        self.client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.client_socket.connect((self.host, self.port))

        self.username = input("Input your username: ")
        self.client_socket.send(self.username.encode("utf-8"))

        self.groupname = input("Input your group name: ")
        self.client_socket.send(self.groupname.encode("utf-8"))

        receive_thread = threading.Thread(target=self.receive_messages, args=(self.client_socket,))
        receive_thread = threading.Thread(target=self.receive_file, args=(self.client_socket,))
        receive_thread.start()

        while True:
            message = input()

            if message == "/exit":
                self.client_socket.send(message.encode("utf-8"))
                break
            elif message.startswith("/pc-"):
                parts = message.split(" ", 1)
                recipient = parts[0][4:]
                message = parts[1]
                username = self.username
                full_message = "/pc-{} {} {}".format(recipient, message, username)

            elif message.startswith("/gc"):
                gc = self.groupname
                message = message[len("/gc") + 1:]
                username = self.username
                full_message = "/gc {} {} {}".format(message,gc, username)

            elif message.startswith("/bc"):
                username = self.username
                full_message = "/bc {} {}".format(message[4:], username) 

            elif message.startswith("/file."):
                parts = message.split(" ", 1)
                recipient = parts[0][6:]
                file = parts[1]
                file_size = os.path.getsize(file)
                username = self.username
                full_message = "/file.{} {} {} {}".format(recipient, os.path.basename(file), file_size, username)
                self.client_socket.send(full_message.encode("utf-8"))

                with open(file, "rb") as file:
                    while True:
                        data = file.read(1024)
                        if not data:
                            break
                        self.client_socket.send(data)
                print("File sent.")
                continue
            
            elif message.startswith("/files-gc"):
                parts = message.split(" ", 1)
                groupname = self.groupname
                file = parts[1]
                file_size = os.path.getsize(file)
                username = self.username

                # Membuat pesan lengkap dengan informasi file dan tujuan group
                full_message = "/files-gc{} {} {} {}".format(groupname, os.path.basename(file), file_size, username)
                self.client_socket.send(full_message.encode("utf-8"))

                # Mengirimkan isi file ke server
                with open(file, "rb") as file:
                    while True:
                        data = file.read(1024)
                        if not data:
                            break
                        self.client_socket.send(data)

                print("File sent to group {}.".format(groupname))
                continue

            
            elif message.startswith("/files-bc"):
                parts = message.split(" ", 1)
                file = parts[1]
                file_size = os.path.getsize(file)
                username = self.username

                # Membuat pesan lengkap dengan informasi file untuk broadcast
                full_message = "/files-bc {} {} {}".format(os.path.basename(file), file_size, username)
                self.client_socket.send(full_message.encode("utf-8"))

                # Mengirimkan isi file ke server
                with open(file, "rb") as file:
                    while True:
                        data = file.read(1024)
                        if not data:
                            break
                        self.client_socket.send(data)

                print("File broadcasted to all connected clients.")
                continue


            elif message == "/help":
                full_message = "/help"
            elif message == "/show":
                full_message = "/show"
            else:
                full_message = message

            self.client_socket.send(full_message.encode("utf-8"))

        self.client_socket.close()
