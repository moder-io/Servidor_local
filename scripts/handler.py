from http.server import SimpleHTTPRequestHandler
from email.parser import BytesParser
from email.policy import default
import os
import mimetypes
import logging
import shutil
import json
import urllib.parse
import threading

SHOPPING_LIST_FILE = "shopping_list.json"
CALENDAR_FILE = "calendar.json"

ALLOWED_EXTENSIONS = {
    "txt", "pdf", "doc", "docx", "xls", "xlsx", "ppt", "pptx",
    "png", "jpg", "jpeg", "gif", "bmp", "tiff", "svg",
    "mp4", "avi", "mov", "wmv", "flv", "mkv", "webm",
    "mp3", "wav", "ogg", "aac",
    "zip", "rar", "7z", "tar", "gz",
    "css", "js", "html", "json"
}

MAX_FILE_SIZE = 1 * 1024 * 1024 * 1024  # 1 GB
LOG_FILE = "server.log"

file_lock = threading.Lock()
shopping_lock = threading.Lock()
calendar_lock = threading.Lock()

logging.basicConfig(
    filename=LOG_FILE,
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)


def is_allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


def is_allowed_mime_type(filename):
    mime_type, _ = mimetypes.guess_type(filename)
    return bool(mime_type)


def sanitize_filename(filename):
    return "".join(c for c in filename if c.isalnum() or c in (" ", ".", "_", "-")).strip()


def check_disk_space(file_size, path):
    _, _, free = shutil.disk_usage(path)
    return free > file_size


def safe_json_load(path):
    if not os.path.exists(path):
        return []
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return []


def safe_json_write(path, data):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


class CustomHTTPRequestHandler(SimpleHTTPRequestHandler):
    server_version = "ServidorSeguro/1.1"
    sys_version = ""

    def __init__(self, *args, directory=None, **kwargs):
        self.base_dir = os.path.abspath(directory or os.getcwd())
        self.upload_dir = os.path.join(self.base_dir, "uploads")
        self.shopping_list_file = os.path.join(self.base_dir, SHOPPING_LIST_FILE)
        self.calendar_file = os.path.join(self.base_dir, CALENDAR_FILE)
        super().__init__(*args, directory=directory, **kwargs)

    def log_message(self, format, *args):
        client_ip = self.client_address[0]
        user_agent = self.headers.get("User-Agent", "Desconocido")
        logging.info(f"{client_ip} - {user_agent} - {format % args}")

    def send_json(self, payload, status=200):
        data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def send_text(self, message, status=200):
        data = message.encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "text/plain; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    # ================== GET ==================

    def do_GET(self):
        if self.path.startswith("/shopping_list"):
            self.handle_shopping_list_get()
            return

        if self.path.startswith("/calendar"):
            self.handle_calendar_get()
            return

        path = self.translate_path(self.path)
        if os.path.isfile(path):
            filename = sanitize_filename(os.path.basename(path))

            if not is_allowed_file(filename):
                self.send_error(403, "Archivo no permitido")
                return

            mime_type = mimetypes.guess_type(path)[0] or "application/octet-stream"
            self.send_response(200)
            self.send_header("Content-Type", mime_type)
            self.send_header("Content-Length", str(os.path.getsize(path)))
            self.send_header("Content-Disposition", f'attachment; filename="{filename}"')
            self.end_headers()

            with open(path, "rb") as f:
                shutil.copyfileobj(f, self.wfile)
            return

        super().do_GET()

    # ================== POST ==================

    def do_POST(self):
        if self.path == "/add_item":
            self.handle_add_item_post()
            return

        if self.path == "/add_event":
            self.handle_add_event_post()
            return

        try:
            content_length = int(self.headers.get("Content-Length", 0))
        except ValueError:
            self.send_error(411, "Longitud inválida")
            return

        if content_length > MAX_FILE_SIZE:
            self.send_error(413, "Archivo demasiado grande")
            return

        content_type = self.headers.get("Content-Type", "")
        body = self.rfile.read(content_length)

        if not content_type.startswith("multipart/form-data"):
            self.send_error(400, "Formato inválido")
            return

        raw_message = (
            f"Content-Type: {content_type}\r\n"
            f"MIME-Version: 1.0\r\n\r\n"
        ).encode() + body

        msg = BytesParser(policy=default).parsebytes(raw_message)

        os.makedirs(self.upload_dir, exist_ok=True)
        file_saved = False

        for part in msg.iter_parts():
            raw_filename = part.get_param("filename", header="Content-Disposition")
            if not raw_filename:
                continue

            raw_filename = str(raw_filename)
            filename = sanitize_filename(os.path.basename(raw_filename))

            if not is_allowed_file(filename) or not is_allowed_mime_type(filename):
                self.send_error(400, "Archivo no permitido")
                return

            data = part.get_payload(decode=True)
            if not isinstance(data, (bytes, bytearray)):
                continue

            if len(data) > MAX_FILE_SIZE:
                self.send_error(413, "Archivo demasiado grande")
                return

            if not check_disk_space(len(data), self.upload_dir):
                self.send_error(507, "Espacio insuficiente")
                return

            file_path = os.path.join(self.upload_dir, filename)

            with file_lock:
                with open(file_path, "wb") as f:
                    f.write(data)
                os.chmod(file_path, 0o644)
                file_saved = True

        if file_saved:
            self.send_text("Archivo subido exitosamente", status=200)
        else:
            self.send_error(400, "Error en la subida")

    # ================== DELETE ==================

    def do_DELETE(self):
        if self.path.startswith("/remove_item"):
            self.handle_remove_item_delete()
            return

        if self.path.startswith("/delete_file"):
            self.handle_delete_file()
            return

        if self.path == "/delete_event":
            self.handle_delete_event()
            return

        self.send_error(404)

    # ================== API ==================

    def handle_shopping_list_get(self):
        with shopping_lock:
            data = safe_json_load(self.shopping_list_file)

        self.send_json(data)

    def handle_add_item_post(self):
        length = int(self.headers.get("Content-Length", 0))
        try:
            payload = json.loads(self.rfile.read(length))
        except json.JSONDecodeError:
            self.send_error(400, "JSON inválido")
            return

        item = str(payload.get("name", "")).strip()
        if not item:
            self.send_error(400, "Nombre vacío")
            return

        with shopping_lock:
            data = safe_json_load(self.shopping_list_file)
            data.append(item)
            safe_json_write(self.shopping_list_file, data)

        self.send_text("Item agregado", status=200)

    def handle_remove_item_delete(self):
        parsed = urllib.parse.urlparse(self.path)
        item = sanitize_filename(urllib.parse.unquote(parsed.path.split("/")[-1]))

        with shopping_lock:
            data = [i for i in safe_json_load(self.shopping_list_file) if i != item]
            safe_json_write(self.shopping_list_file, data)

        self.send_text("Item eliminado", status=200)

    def handle_calendar_get(self):
        parsed = urllib.parse.urlparse(self.path)
        params = urllib.parse.parse_qs(parsed.query)

        try:
            month = int(params["month"][0])
            year = int(params["year"][0])
        except Exception:
            self.send_error(400, "Parámetros inválidos")
            return

        with calendar_lock:
            events = [
                e for e in safe_json_load(self.calendar_file)
                if int(e["date"][:4]) == year and int(e["date"][5:7]) == month
            ]

        self.send_json(events)

    def handle_add_event_post(self):
        length = int(self.headers.get("Content-Length", 0))
        try:
            data = json.loads(self.rfile.read(length))
        except json.JSONDecodeError:
            self.send_error(400, "JSON inválido")
            return

        if not data.get("date") or not data.get("title"):
            self.send_error(400, "Datos inválidos")
            return

        with calendar_lock:
            events = safe_json_load(self.calendar_file)
            events.append(data)
            safe_json_write(self.calendar_file, events)

        self.send_text("Evento agregado", status=200)

    def handle_delete_file(self):
        parsed = urllib.parse.urlparse(self.path)
        filename = sanitize_filename(urllib.parse.unquote(parsed.path.split("/")[-1]))
        file_path = os.path.join(self.upload_dir, filename)

        if not os.path.isfile(file_path):
            self.send_error(404, "Archivo no encontrado")
            return

        with file_lock:
            os.remove(file_path)

        self.send_text("Archivo eliminado", status=200)

    def handle_delete_event(self):
        length = int(self.headers.get("Content-Length", 0))
        try:
            target = json.loads(self.rfile.read(length))
        except json.JSONDecodeError:
            self.send_error(400, "JSON inválido")
            return

        with calendar_lock:
            events = [
                e for e in safe_json_load(self.calendar_file)
                if not (e["date"] == target.get("date") and e["title"] == target.get("title"))
            ]
            safe_json_write(self.calendar_file, events)

        self.send_text("Evento eliminado", status=200)
