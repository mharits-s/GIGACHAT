# chat.py
import funcchatv2
import os

def main():
    os.system('cls')
    role = int(input("1. Server\n2. Client\nChoose Role:"))
    host = '10.217.22.253'  # Change this to your server IP
    port = 12345

    chat = funcchatv2.FuncChat(host, port)

    if role == 1:
        chat.start_server()
    elif role == 2:
        chat.start_client()
    else:
        print("Invalid role selection. Choose either 1 or 2.")

if __name__ == "__main__":
    main()
