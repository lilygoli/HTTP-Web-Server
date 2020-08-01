import socket
import threading
client_port = 8090
command_port = 8091
HOST = '127.0.0.1'


class Proxy:

    def client_handler(self, clnt, addr):
        try:
            with clnt:
                data = clnt.recv(1024).decode("utf-8")
                if len(data) > 0:
                    data = data.replace("Connection: keep-alive", "Connection: close")
                    data_split = data.split("\r\n")
                    data_request = data_split[0]
                    request_type = data_request.split(" ")[0]
                    if request_type == "GET" or request_type == "CONNECT":
                        print(data_request)
                        url = data_request.split(" ")[1]
                        http_pos = url.find("://")
                        if http_pos == -1:
                            temp = url
                        else:
                            temp = url[(http_pos + 3):]
                        port_pos = temp.find(":")
                        web_server_pos = temp.find("/")
                        if web_server_pos == -1:
                            web_server_pos = len(temp)
                        if port_pos == -1 or web_server_pos < port_pos:
                            port = 80
                            web_server = temp[:web_server_pos]
                        else:
                            port = int((temp[(port_pos + 1):])[:web_server_pos - port_pos - 1])
                            web_server = temp[:port_pos]
                        data = bytes(data, 'utf-8')
                        print(web_server, port)
                        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                            s.connect((web_server, port))
                            print("connected")
                            s.sendall(data)
                            while True:
                                answer = s.recv(1024)
                                if len(answer) > 0:
                                    clnt.sendall(answer)
                                else:
                                    break
                        s.close()
                    clnt.close()
        except ConnectionResetError:
            clnt.close()


    def client_listen(self):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.bind((HOST, client_port))
            s.listen()
            while True:
                clnt, addr = s.accept()
                handler = threading.Thread(target=self.client_handler, args=(clnt, addr,), daemon=False)
                handler.start()

def main():
    proxy = Proxy()
    proxy.client_listen()


if __name__ == "__main__":
    main()
