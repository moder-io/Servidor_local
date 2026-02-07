from http.server import ThreadingHTTPServer
from functools import partial
from handler import CustomHTTPRequestHandler
import argparse
import os
import socket
import sys


def resolve_web_dir(path):
    if path:
        return os.path.abspath(path)
    return os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "server"))


def get_local_ip():
    try:
        hostname = socket.gethostname()
        return socket.gethostbyname(hostname)
    except OSError:
        return "127.0.0.1"


def run(host="0.0.0.0", port=8080, web_dir=None):
    web_dir = resolve_web_dir(web_dir)
    if not os.path.isdir(web_dir):
        raise FileNotFoundError(f"Directorio web no encontrado: {web_dir}")

    handler_cls = partial(CustomHTTPRequestHandler, directory=web_dir)
    httpd = ThreadingHTTPServer((host, port), handler_cls)

    local_ip = get_local_ip()
    print(f"Servidor iniciado en http://{local_ip}:{port} (dir: {web_dir})")
    httpd.serve_forever()


def main(argv=None):
    parser = argparse.ArgumentParser(description="Servidor HTTP local")
    parser.add_argument("--host", default="0.0.0.0", help="Host de escucha")
    parser.add_argument("--port", type=int, default=8080, help="Puerto de escucha")
    parser.add_argument("--web-dir", default=None, help="Directorio de archivos estaticos")
    args = parser.parse_args(argv)

    run(host=args.host, port=args.port, web_dir=args.web_dir)


if __name__ == "__main__":
    main(sys.argv[1:])
