import socket
import threading

HOST = '127.0.0.1'  # Standard loopback interface address (localhost)
PORT = 8080  # Port to listen on (non-privileged ports are > 1023)


class Server:

    def response_maker(self, data_dict, request_details):
        pass


    def client_handler(self, clnt, addr):
        try:
            with clnt:
                print('Connected by', addr)
                print(type(clnt))
                while True:
                    data = clnt.recv(1024).decode("utf-8")
                    if len(data) > 0:
                        data_split = data.split("\r\n")
                        data_request = data_split[0]
                        request_details = data_request.split(" ")
                        print(request_details)
                        data_dict = dict()
                        for i in range(1, len(data_split)):
                            if ":" in data_split[i]:
                                elements = data_split[i].split(":", 2)
                                data_dict[elements[0].strip()] = elements[1].strip()
                        self.response_maker(data_dict, request_details)
                        #print(data_dict)
                    if not data:
                        break
                    #clnt.sendall(data)
        except ConnectionResetError:
            clnt.close()

    def listen(self):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.bind((HOST, PORT))
            s.listen()
            while True:
                clnt, addr = s.accept()
                handler = threading.Thread(target=self.client_handler, args=(clnt, addr,), daemon=False)
                handler.start()


def main():
    server = Server()
    server.listen()


if __name__ == "__main__":
    main()
