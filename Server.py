import socket
import threading

HOST = '127.0.0.1'  # Standard loopback interface address (localhost)
PORT = 8080        # Port to listen on (non-privileged ports are > 1023)


class Server:

    def client_handler(self, clnt, addr):
        with clnt:
            print('Connected by', addr)
            print(type(clnt))
            while True:
                data = clnt.recv(1024)
                if not data:
                    break
                clnt.sendall(data)

    def listen(self):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.bind((HOST, PORT))
            s.listen()
            while (True):
                clnt, addr = s.accept()
                handler = threading.Thread(target=self.client_handler, args=(clnt, addr, ),daemon=False)
                handler.start()


server = Server()
server.listen()
