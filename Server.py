import socket
import threading
from wsgiref.handlers import format_date_time
from datetime import datetime
from time import mktime
import gzip

HOST = '127.0.0.1'  # Standard loopback interface address (localhost)
PORT = 8080  # Port to listen on (non-privileged ports are > 1023)

class Server:

    def get_time(self):
        now = datetime.now()
        stamp = mktime(now.timetuple())
        return format_date_time(stamp)

    def get_content(self, url, g):
        if url == "/":
            address = "Pages/main.html"
        elif "html" in url:
            address = "Pages" + url
        else:
            address = "." + url
        file = open(address, "rb")
        content = file.read()
        if g:
            content = gzip.compress(content)
        return content

    def response_maker(self, data_dict, request_details, status):
        message = ''
        if status is None:
            code = '200 OK'
        elif status == 400:
            code = '400 Bad Request'
            message = 'Wrong HTTP Request!'
        elif status == 404:
            code = '404 Not Found'
            message = 'Page Not Found:('
        elif status == 501:
            code = '501 Not Implement'
            message = 'Method Not Implemented:p'
        else:
            ##405
            code = 'Method Not Allowed'
            message = 'This Method Is Not Allowed.'
        response_str = request_details[2] + " "
        response_str += code + '\r\n'
        response_str += 'Connection: ' + data_dict['Connection'] + '\r\n'
        g = False
        if "gzip" in data_dict["Accept-Encoding"] and status is None:
            g = True
        if status is None:
            content = self.get_content(request_details[1], g)
        else:
            content = bytes(message)
        response_str += 'Content-Length: ' + str(len(content)) + '\r\n'
        response_str += 'Content-Type: text/html' + '\r\n'
        if g:
            response_str += 'Content-Encoding: gzip' + '\r\n'
        time = "[" + str(self.get_time()) + "]"
        if status == 405:
            response_str += 'Allow: GET\r\n'
        response_str += 'Date: ' + str(self.get_time()) + '\r\n'
        response_str += '\r\n'
        response_str = bytes(response_str, 'utf-8')
        response_str += content
        return response_str, time, code

    def client_handler(self, clnt, addr):
        try:
            with clnt:
                while True:
                    data = clnt.recv(1024).decode("utf-8")
                    if len(data) > 0:
                        data_split = data.split("\r\n")
                        data_request = data_split[0]
                        request_details = data_request.split(" ")
                        if request_details[1] == "/favicon.ico":
                            continue
                        data_dict = dict()
                        for i in range(1, len(data_split)):
                            if ":" in data_split[i]:
                                elements = data_split[i].split(":", 2)
                                data_dict[elements[0].strip()] = elements[1].strip()
                        response, time, code = self.response_maker(data_dict, request_details)
                        print(time, '"' + data_request + '"', '"' + code + '"')
                    if not data:
                        break
                    clnt.sendall(response)
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
