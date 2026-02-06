from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from email.parser import BytesParser
from email.policy import default
import os
import mimetypes
import logging
import shutil
import json
import urllib.parse
import threading

UPLOAD_DIR = "uploads"
SHOPPING_LIST_FILE = 'shopping_list.json'
CALENDAR_FILE = 'calendar.json'

ALLOWED_EXTENSIONS = {
    'txt', 'pdf', 'doc', 'docx', 'xls', 'xlsx', 'ppt', 'pptx',
    'png', 'jpg', 'jpeg', 'gif', 'bmp', 'tiff', 'svg',
    'mp4', 'avi', 'mov', 'wmv', 'flv', 'mkv', 'webm',
    'mp3', 'wav', 'ogg', 'aac',
    'zip', 'rar', '7z', 'tar', 'gz',
    'css', 'js', 'html', 'json'
}

MAX_FILE_SIZE = 1 * 1024 * 1024 * 1024  # 1 GB
LOG_FILE = 'server.log'

file_lock = threading.Lock()
shopping_lock = threading.Lock()
calendar_lock = threading.Lock()

logging.basicConfig(
    filename=LOG_FILE,
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

def is_allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def is_allowed_mime_type(filename):
    mime_type, _ = mimetypes.guess_type(filename)
    return bool(mime_type)

def sanitize_filename(filename):
    return "".join(c for c in filename if c.isalnum() or c in (' ', '.', '_')).strip()

def check_disk_space(file_size, path):
    total, used, free = shutil.disk_usage(path)
    return free > file_size

def safe_json_load(path):
    if not os.path.exists(path):
        return []
    with open(path, 'r', encoding='utf-8') as f:
        return json.load(f)

def safe_json_write(path, data):
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

class CustomHTTPRequestHandler(SimpleHTTPRequestHandler):
    server_version = "ServidorSeguro/1.1"
    sys_version = ""

    def log_message(self, format, *args):
        client_ip = self.client_address[0]
        user_agent = self.headers.get('User-Agent', 'Desconocido')
        logging.info(f"{client_ip} - {user_agent} - {format % args}")

    # ================== GET ==================

    def do_GET(self):
        if self.path.startswith('/shopping_list'):
            self.handle_shopping_list_get()
            return

        if self.path.startswith('/calendar'):
            self.handle_calendar_get()
            return

        path = self.translate_path(self.path)
        if os.path.isfile(path):
            filename = sanitize_filename(os.path.basename(path))

            if not is_allowed_file(filename):
                self.send_error(403, "Archivo no permitido")
                return

            mime_type = mimetypes.guess_type(path)[0] or 'application/octet-stream'
            self.send_response(200)
            self.send_header('Content-Type', mime_type)
            self.send_header('Content-Length', str(os.path.getsize(path)))
            self.send_header('Content-Disposition', f'attachment; filename="{filename}"')
            self.end_headers()

            with open(path, 'rb') as f:
                shutil.copyfileobj(f, self.wfile)
            return

        super().do_GET()

    # ================== POST ==================

    def do_POST(self):
        if self.path == '/add_item':
            self.handle_add_item_post()
            return

        if self.path == '/add_event':
            self.handle_add_event_post()
            return

        content_length = int(self.headers.get('Content-Length', 0))
        if content_length > MAX_FILE_SIZE:
            self.send_error(413, "Archivo demasiado grande")
            return

        content_type = self.headers.get('Content-Type', '')
        body = self.rfile.read(content_length)

        if not content_type.startswith('multipart/form-data'):
            self.send_error(400, "Formato inválido")
            return

        raw_message = (
            f"Content-Type: {content_type}\r\n"
            f"MIME-Version: 1.0\r\n\r\n"
        ).encode() + body

        msg = BytesParser(policy=default).parsebytes(raw_message)

        os.makedirs(UPLOAD_DIR, exist_ok=True)
        file_saved = False

        for part in msg.iter_parts():
            raw_filename = part.get_param('filename', header='Content-Disposition')
            if not raw_filename:
                continue

            raw_filename = str(raw_filename)
            filename = sanitize_filename(os.path.basename(raw_filename))

            if not is_allowed_file(filename) or not is_allowed_mime_type(filename):
                self.send_error(400, "Archivo no permitido")
                return

            if not check_disk_space(content_length, UPLOAD_DIR):
                self.send_error(507, "Espacio insuficiente")
                return

            data = part.get_payload(decode=True)

            if not isinstance(data, (bytes, bytearray)):
                continue

            file_path = os.path.join(UPLOAD_DIR, filename)

            with file_lock:
                with open(file_path, 'wb') as f:
                    f.write(data)
                os.chmod(file_path, 0o644)


        if file_saved:
            self.send_response(200)
            self.end_headers()
            self.wfile.write(b'Archivo subido exitosamente')
        else:
            self.send_error(400, "Error en la subida")

    # ================== DELETE ==================

    def do_DELETE(self):
        if self.path.startswith('/remove_item'):
            self.handle_remove_item_delete()
            return

        if self.path.startswith('/delete_file'):
            self.handle_delete_file()
            return

        if self.path == '/delete_event':
            self.handle_delete_event()
            return

        self.send_error(404)

    # ================== API ==================

    def handle_shopping_list_get(self):
        with shopping_lock:
            data = safe_json_load(SHOPPING_LIST_FILE)

        self.send_response(200)
        self.send_header('Content-Type', 'application/json')
        self.end_headers()
        self.wfile.write(json.dumps(data).encode())

    def handle_add_item_post(self):
        length = int(self.headers.get('Content-Length', 0))
        item = json.loads(self.rfile.read(length)).get('name', '').strip()

        if not item:
            self.send_error(400, "Nombre vacío")
            return

        with shopping_lock:
            data = safe_json_load(SHOPPING_LIST_FILE)
            data.append(item)
            safe_json_write(SHOPPING_LIST_FILE, data)

        self.send_response(200)
        self.end_headers()
        self.wfile.write(b'Item agregado')

    def handle_remove_item_delete(self):
        item = sanitize_filename(self.path.split('/')[-1])

        with shopping_lock:
            data = [i for i in safe_json_load(SHOPPING_LIST_FILE) if i != item]
            safe_json_write(SHOPPING_LIST_FILE, data)

        self.send_response(200)
        self.end_headers()
        self.wfile.write(b'Item eliminado')

    def handle_calendar_get(self):
        parsed = urllib.parse.urlparse(self.path)
        params = urllib.parse.parse_qs(parsed.query)

        try:
            month = int(params['month'][0])
            year = int(params['year'][0])
        except Exception:
            self.send_error(400, "Parámetros inválidos")
            return

        with calendar_lock:
            events = [
                e for e in safe_json_load(CALENDAR_FILE)
                if int(e['date'][:4]) == year and int(e['date'][5:7]) == month
            ]

        self.send_response(200)
        self.send_header('Content-Type', 'application/json')
        self.end_headers()
        self.wfile.write(json.dumps(events).encode())

    def handle_add_event_post(self):
        length = int(self.headers.get('Content-Length', 0))
        data = json.loads(self.rfile.read(length))

        if not data.get('date') or not data.get('title'):
            self.send_error(400, "Datos inválidos")
            return

        with calendar_lock:
            events = safe_json_load(CALENDAR_FILE)
            events.append(data)
            safe_json_write(CALENDAR_FILE, events)

        self.send_response(200)
        self.end_headers()
        self.wfile.write(b'Evento agregado')

    def handle_delete_file(self):
        filename = sanitize_filename(self.path.split('/')[-1])
        file_path = os.path.join(UPLOAD_DIR, filename)

        if not os.path.isfile(file_path):
            self.send_error(404, "Archivo no encontrado")
            return

        with file_lock:
            os.remove(file_path)

        self.send_response(200)
        self.end_headers()
        self.wfile.write(b'Archivo eliminado')

    def handle_delete_event(self):
        length = int(self.headers.get('Content-Length', 0))
        target = json.loads(self.rfile.read(length))

        with calendar_lock:
            events = [
                e for e in safe_json_load(CALENDAR_FILE)
                if not (e['date'] == target.get('date') and e['title'] == target.get('title'))
            ]
            safe_json_write(CALENDAR_FILE, events)

        self.send_response(200)
        self.end_headers()
        self.wfile.write(b'Evento eliminado')

def run(port=8080):
    server = ThreadingHTTPServer(('', port), CustomHTTPRequestHandler)
    print(f"Servidor HTTP corriendo en el puerto {port}")
    server.serve_forever()

if __name__ == "__main__":
    run()
