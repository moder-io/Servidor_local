from http.server import HTTPServer
from handler import CustomHTTPRequestHandler
import os
import threading
import socket

host = "0.0.0.0"
port = 8080
hostname = socket.gethostname()
ip = socket.gethostbyname(hostname)

web_dir = os.path.join(os.path.dirname(__file__), '../server')
os.chdir(web_dir)

server_address = (host, port) 
httpd = HTTPServer(server_address, CustomHTTPRequestHandler)

def start_server():
    try:
        print(f"Servidor iniciado en http://{ip}:{port}")
        httpd.serve_forever()
    except Exception as e:
        print(f"Error al iniciar el servidor: {e}")

server_thread = threading.Thread(target=start_server)
server_thread.start()