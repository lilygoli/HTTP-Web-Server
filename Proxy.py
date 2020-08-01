import socket
import threading
from datetime import datetime
from time import mktime
from wsgiref.handlers import format_date_time

client_port = 8090
command_port = 8091
HOST = '127.0.0.1'


class Proxy:

    def get_time(self):
        now = datetime.now()
        stamp = mktime(now.timetuple())
        return format_date_time(stamp)

    def client_handler(self, clnt, addr):
        try:
            with clnt:
                data = clnt.recv(1024).decode("utf-8")
                if len(data) > 0:
                    data = data.replace("Connection: keep-alive", "Connection: close")
                    data_split = data.split("\r\n")
                    data_request = data_split[0]
                    request_type = data_request.split(" ")[0]
                    port, web_server = self.parse_request(data_request)
                    print("Request:", "[" + self.get_time() + "]", "[" + addr[0] + ":" + str(addr[1]) + "]",
                          "[" + web_server + ":" + str(port) + "]", '"' + data_request + '"')
                    if request_type == "GET":
                        data = bytes(data, 'utf-8')
                        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                            s.connect((web_server, port))
                            s.sendall(data)
                            while True:
                                answer = s.recv(1024)
                                a = answer.decode('utf-8', errors='replace')
                                if a.startswith("HTTP"):
                                    http_status = a.split("\n")[0]
                                    print("Response:", "[" + self.get_time() + "]",
                                          "[" + addr[0] + ":" + str(addr[1]) + "]",
                                          "[" + web_server + ":" + str(port) + "]", '"'+http_status[:-1]+'" for '+'"' + data_request + '"')
                                if len(answer) > 0:
                                    clnt.sendall(answer)
                                else:
                                    break
                        s.close()
                    clnt.close()
        except ConnectionResetError:
            clnt.close()

    def parse_request(self, data_request):
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
        return port, web_server

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
