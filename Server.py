import socket

HOST = '127.0.0.1'  # Standard loopback interface address (localhost)
PORT = 8080        # Port to listen on (non-privileged ports are > 1023)

with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
    s.bind((HOST, PORT))
    s.listen()
    clnt, addr = s.accept()
    with clnt:
        print('Connected by', addr)
        while True:
            data = clnt.recv(1024)
            if not data:
                break
            clnt.sendall(data)
