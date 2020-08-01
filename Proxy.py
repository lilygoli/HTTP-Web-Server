import socket
import threading
from datetime import datetime
from time import mktime
from wsgiref.handlers import format_date_time

client_port = 8090
command_port = 8091
HOST = '127.0.0.1'


class Proxy:

    def __init__(self):
        self.count_packet_server = 0
        self.squared_packets_server = 0
        self.squared_bodies = 0
        self.squared_packets_client = 0
        self.count_packet_client = 0
        self.server_packet_length = (0, 0)
        self.client_packet_length = (0, 0)
        self.server_body_length = (0, 0)
        self.cur_body_len = 0
        self.cur_header_len = 0
        self.types = {"text/html", "text/plain", "image/png", "image/jpg", "image/jpeg"}
        self.type_counts = {"text/html": 0, "text/plain": 0, "image/png": 0, "image/jpg": 0, "image/jpeg": 0}
        self.type_semaphore = threading.Semaphore()
        self.length_sema = threading.Semaphore()
        self.status_counts = {"200 OK": 0, "301 Moved Permanently": 0, "304 Not Modified": 0,
                              "400 Bad Request": 0, "404 Not Found": 0, "405 Method Not Allowed": 0,
                              "501 Not Implemented": 0}
        self.status_semaphore = threading.Semaphore()

    def update_lengths(self, packet, server):
        if server:
            if len(packet) > 0:
                if packet.startswith("HTTP"):

                    p = packet.split("\n")
                    index = p.index('\r')
                    body = p[index + 1]
                    body_length = len(body.encode('utf-8'))
                    self.cur_header_len = len(packet.encode('utf-8')) - body_length
                    self.cur_body_len += body_length
                else:
                    self.cur_body_len += len(packet.encode('utf-8'))
            else:
                new_mean_packet = self.server_packet_length[0] * self.count_packet_server + (
                        self.cur_header_len + self.cur_body_len)
                new_mean_body = self.server_body_length[0] * self.count_packet_server + self.cur_body_len
                self.squared_packets_server += (self.cur_body_len + self.cur_header_len) ** 2
                self.squared_bodies += self.cur_body_len ** 2
                self.squared_packets_server += (self.cur_body_len + self.cur_header_len) ** 2
                self.count_packet_server += 1
                new_mean_packet = new_mean_packet / self.count_packet_server
                new_mean_body = new_mean_body / self.count_packet_server
                new_body_std = (self.squared_bodies - ((
                         new_mean_body * self.count_packet_server) ** 2) / self.count_packet_server) / self.count_packet_server
                new_packet_std = (self.squared_packets_server - ((
                        new_mean_packet * self.count_packet_server) ** 2) / self.count_packet_server) / self.count_packet_server

                self.server_body_length = (new_mean_body, new_body_std ** (1/2))
                self.server_packet_length = (new_mean_packet, new_packet_std ** (1/2))
                self.cur_header_len = 0
                self.cur_body_len = 0
                # print(self.server_packet_length)
                # print(self.server_body_length)

        else:
            packet_len = len(packet.encode('utf-8'))
            new_mean = self.client_packet_length[0] * self.count_packet_client + packet_len
            self.squared_packets_client += packet_len ** 2
            self.count_packet_client += 1
            new_mean /= self.count_packet_client
            new_std = (self.squared_packets_client - ((new_mean * self.count_packet_client)**2)/self.count_packet_client)/self.count_packet_client
            self.client_packet_length = ( new_mean, new_std ** (1/2))
            # print(self.client_packet_length)

    def get_time(self):
        now = datetime.now()
        stamp = mktime(now.timetuple())
        return format_date_time(stamp)

    def find_type(self, answer):
        for x in answer:
            if isinstance(x, str) and x.startswith("Content-Type"):
                element = x.split(" ")[1]
                for t in self.types:
                    if element.startswith(t):
                        return t
        return None

    def update_type_counts(self, new_type):
        self.type_semaphore.acquire()
        self.type_counts[new_type] += 1
        self.type_semaphore.release()

    def update_status(self, http_status_line):
        status = http_status_line.split(" ", 1)[1].strip("\r")
        self.status_semaphore.acquire()
        if status in self.status_counts.keys():
            self.status_counts[status] += 1
        self.status_semaphore.release()

    def client_handler(self, clnt, addr):
        try:
            with clnt:
                data = clnt.recv(1024).decode("utf-8")
                self.length_sema.acquire()
                self.update_lengths(data, False)
                self.length_sema.release()
                if len(data) > 0:
                    data = data.replace("Connection: keep-alive", "Connection: close")
                    data_split = data.split("\r\n")
                    data_request = data_split[0]
                    request_type = data_request.split(" ")[0]
                    port, web_server = self.parse_request(data_request)
                    if request_type == "GET":
                        print("Request:", "[" + self.get_time() + "]", "[" + addr[0] + ":" + str(addr[1]) + "]",
                              "[" + web_server + ":" + str(port) + "]", '"' + data_request + '"')
                        data = bytes(data, 'utf-8')
                        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                            s.connect((web_server, port))
                            s.sendall(data)
                            while True:
                                answer = s.recv(1024)
                                a = answer.decode('utf-8', errors='replace')
                                self.length_sema.acquire()
                                self.update_lengths(a, True)
                                self.length_sema.release()
                                if a.startswith("HTTP"):
                                    answer_split = a.split("\n")
                                    http_status = answer_split[0]
                                    self.update_status(http_status)
                                    content_type = self.find_type(answer_split)
                                    if content_type is not None:
                                        self.update_type_counts(content_type)
                                    print("Response:", "[" + self.get_time() + "]",
                                          "[" + addr[0] + ":" + str(addr[1]) + "]",
                                          "[" + web_server + ":" + str(port) + "]",
                                          '"' + http_status[:-1] + '" for ' + '"' + data_request + '"')
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


class Telnet:
    def __init__(self, proxy):
        self.proxy = proxy

    def handler(self, clnt, addr):
        try:
            with clnt:
                command = ""
                while True:
                    data = clnt.recv(1024).decode("utf-8")
                    print(data)
                    if data == "\r\n":
                        print(command)
                        ##todo ifs
                        command = ""
                    else:
                        command += data


        except ConnectionResetError:
            clnt.close()

    def listen(self):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.bind((HOST, command_port))
            s.listen()
            while True:
                clnt, addr = s.accept()
                handler = threading.Thread(target=self.handler, args=(clnt, addr,), daemon=False)
                handler.start()


def main():
    proxy = Proxy()
    proxy.client_listen()
    telnet = Telnet(proxy)
    telnet.listen()


if __name__ == "__main__":
    main()
