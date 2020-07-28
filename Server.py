import gzip
import socket
import threading
from datetime import datetime
from time import mktime
from wsgiref.handlers import format_date_time
import time
import multiprocessing as mp

HOST = '127.0.0.1'  # Standard loopback interface address (localhost)
PORT = 8080  # Port to listen on (non-privileged ports are > 1023)
ALLOWED_URLS = ['/first.html', '/', '/second.html', '/media/night.png', '/media/sea.jpg', '/media/stars.jpeg', '/media/license.txt']
content_types = {'/':'text/html', '/first.html':'text/html', '/second.html':'text/html',
                 '/media/night.png':'image/png', '/media/stars.jpeg':'image/jpeg',
                 '/media/sea.jpg':'image/jpg', '/media/license.txt':'text/plain'}
time_threads = dict()
time_lock = mp.Lock()


def make_time_thread(clnt, t, key):
    time.sleep(t)
    clnt.close()

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
        elif status == 404:
            code = '404 Not Found'
        elif status == 501:
            code = '501 Not Implement'
        else:
            # 405
            code = 'Method Not Allowed'
        response_str = request_details[2] + " "
        response_str += code + '\r\n'
        response_str += 'Connection: ' + data_dict['Connection'] + '\r\n'
        g = False
        if "Accept-Encoding" in data_dict.keys() and "gzip" in data_dict["Accept-Encoding"] and status is None:
            g = True
        if status is None:
            content = self.get_content(request_details[1], g)
        else:
            address = "Errors/"+str(status)+".html"
            file = open(address, "rb")
            content = file.read()
        response_str += 'Content-Length: ' + str(len(content)) + '\r\n'
        if status is not None:
            content_type = 'text/html'
        else:
            content_type = content_types[request_details[1]]
        response_str += 'Content-Type: '+ content_type + '\r\n'
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

    def check_error_header(self, request_details, data_split):
        error = None
        if len(request_details) != 3:
            error = 400
        elif not str(request_details[2]).startswith("HTTP"):
            error = 400
        for i in data_split[1:]:
            if i != '' and i is not None and ':' not in i:
                error = 400
        if error:
            return error
        elif request_details[0] not in ['PUT', 'POST', 'HEAD', 'GET', 'DELETE']:
            error = 501
        elif request_details[0] != 'GET':
            error = 405
        elif request_details[1] not in ALLOWED_URLS:
            error = 404
        return error

    def client_handler(self, clnt, addr):
        key = addr[1]
        try:
            with clnt:
                while True:
                    data = clnt.recv(1024).decode("utf-8")
                    if len(data) > 0:
                        data_split = data.split("\r\n")
                        data_request = data_split[0]
                        request_details = data_request.split(" ")
                        if len(request_details) > 1 and request_details[1] == "/favicon.ico":
                            continue
                        error = self.check_error_header(request_details, data_split)
                        data_dict = dict()
                        for i in range(1, len(data_split)):
                            if ":" in data_split[i]:
                                elements = data_split[i].split(":", 2)
                                data_dict[elements[0].strip()] = elements[1].strip()
                        response, time, code = self.response_maker(data_dict, request_details, error)
                        print(time, '"' + data_request + '"', '"' + code + '"')
                        clnt.sendall(response)
                        if "Connection" not in data_dict or data_dict["Connection"] == "close":
                            clnt.close()
                        else:
                            time = 60
                            if "Keep-Alive" in data_dict:
                                try:
                                    time = int(data_dict["Keep-Alive"])
                                    if time < 0:
                                        time = 60
                                except ValueError:
                                    time = 60
                            time_thread = mp.Process(target=make_time_thread, args=(clnt, time, key, ), daemon=False)
                            time_lock.acquire()
                            if key in time_threads:
                                time_threads[key].terminate()
                            time_threads[key] = time_thread
                            time_lock.release()
                            time_thread.start()
                    if not data:
                        continue
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
