from http.server import SimpleHTTPRequestHandler, HTTPServer
from email.parser import BytesParser
from email.policy import default
import os
import mimetypes
import logging
import shutil
import json
import urllib.parse  



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



logging.basicConfig(filename=LOG_FILE, level=logging.INFO, 
                    format='%(asctime)s - %(levelname)s - %(message)s')

def is_allowed_file(filename):
    extension = filename.split('.')[-1].lower()
    return extension in ALLOWED_EXTENSIONS

def is_allowed_mime_type(filename):
    mime_type, _ = mimetypes.guess_type(filename)
    return mime_type and '/' in mime_type

def sanitize_filename(filename):
    return "".join(c for c in filename if c.isalnum() or c in (' ', '.', '_')).rstrip()

def log_activity(message, level="INFO"):
    if level == "INFO":
        logging.info(message)
    elif level == "WARNING":
        logging.warning(message)
    elif level == "ERROR":
        logging.error(message)

def check_disk_space(file_size, upload_dir):
    total, used, free = shutil.disk_usage(upload_dir)
    return free > file_size

class CustomHTTPRequestHandler(SimpleHTTPRequestHandler):
    server_version = "ServidorSeguro/1.0"
    sys_version = ""

    def log_message(self, format, *args):
        if hasattr(self, 'headers'):
            user_agent = self.headers.get('User-Agent', 'Desconocido')
        else:
            user_agent = 'Desconocido'

        client_ip = self.client_address[0]
        print(f"Solicitud de {client_ip} con User-Agent: {user_agent}")
        super().log_message(format, *args)

    def do_GET(self):
        if self.path.startswith('/shopping_list'):
            self.handle_shopping_list_get()
            return
        elif self.path.startswith('/calendar'):
            self.handle_calendar_get() 
            return

        path = self.translate_path(self.path)
        if os.path.isfile(path):
            if not is_allowed_file(os.path.basename(path)):
                self.send_response(403)
                self.send_header('Content-Type', 'text/plain; charset=utf-8')
                self.end_headers()
                self.wfile.write('Archivo no permitido para descarga.'.encode('utf-8'))
                return

            mime_type, _ = mimetypes.guess_type(path)
            if mime_type is None:
                mime_type = 'application/octet-stream'

            self.send_response(200)
            self.send_header('Content-Type', mime_type)
            self.send_header('Content-Length', str(os.path.getsize(path)))
            self.send_header('Content-Disposition', f'attachment; filename="{os.path.basename(path)}"')
            self.end_headers()

            with open(path, 'rb') as file:
                self.wfile.write(file.read())
            return

        super().do_GET()

    def do_POST(self):
        if self.path == '/add_item':
            self.handle_add_item_post()
            return
        elif self.path == '/add_event':
            self.handle_add_event_post()
            return

        content_type = self.headers.get('Content-Type', '')
        content_length = int(self.headers.get('Content-Length', 0))

        if content_length > MAX_FILE_SIZE:
            self.send_response(413)
            self.send_header('Content-Type', 'text/plain; charset=utf-8')
            self.end_headers()
            self.wfile.write('El archivo es demasiado grande.'.encode('utf-8'))
            return

        body = self.rfile.read(content_length)

        if content_type.startswith('multipart/form-data'):
            raw_message = (
                f"Content-Type: {content_type}\r\n"
                f"MIME-Version: 1.0\r\n"
                f"\r\n"
            ).encode('utf-8') + body

            msg = BytesParser(policy=default).parsebytes(raw_message)

            if not os.path.exists(UPLOAD_DIR):
                os.makedirs(UPLOAD_DIR)

            file_saved = False

            for part in msg.iter_parts():
                name = part.get_param('name', header='Content-Disposition')
                filename = part.get_param('filename', header='Content-Disposition')

                if not filename:
                    continue

                file_name = sanitize_filename(os.path.basename(filename))

                if not is_allowed_file(file_name):
                    self.send_response(400)
                    self.send_header('Content-Type', 'text/plain; charset=utf-8')
                    self.end_headers()
                    self.wfile.write('Extensión de archivo no permitida.'.encode('utf-8'))
                    return

                if not is_allowed_mime_type(file_name):
                    self.send_response(400)
                    self.send_header('Content-Type', 'text/plain; charset=utf-8')
                    self.end_headers()
                    self.wfile.write('Tipo de archivo no permitido.'.encode('utf-8'))
                    return

                if not check_disk_space(content_length, UPLOAD_DIR):
                    self.send_response(507)  # Insufficient Storage
                    self.send_header('Content-Type', 'text/plain; charset=utf-8')
                    self.end_headers()
                    self.wfile.write('No hay suficiente espacio en disco.'.encode('utf-8'))
                    return

                file_path = os.path.join(UPLOAD_DIR, file_name)

                try:
                    file_content = part.get_payload(decode=True)
                    with open(file_path, 'wb') as output_file:
                        output_file.write(file_content)
                    os.chmod(file_path, 0o644)
                    file_saved = True
                    log_activity(f"Archivo subido: {file_path}")

                except IOError as e:
                    self.send_response(500)
                    self.send_header('Content-Type', 'text/plain; charset=utf-8')
                    self.end_headers()
                    self.wfile.write('Error al guardar el archivo.'.encode('utf-8'))
                    log_activity(f"Error guardando el archivo {file_path}: {e}", level="ERROR")
                    return

            if file_saved:
                self.send_response(200)
                self.send_header('Content-Type', 'text/plain; charset=utf-8')
                self.end_headers()
                self.wfile.write('Archivo subido exitosamente.'.encode('utf-8'))
            else:
                self.send_response(400)
                self.send_header('Content-Type', 'text/plain; charset=utf-8')
                self.end_headers()
                self.wfile.write('Error en la subida del archivo.'.encode('utf-8'))

        else:
            self.send_response(400)
            self.send_header('Content-Type', 'text/plain; charset=utf-8')
            self.end_headers()
            self.wfile.write('Error en la subida del archivo.'.encode('utf-8'))


    def do_DELETE(self):
        if self.path.startswith('/remove_item'):
            self.handle_remove_item_delete()

        elif self.path.startswith('/delete_file'):
            self.handle_delete_file()

        elif self.path == '/delete_event':
            self.handle_delete_event()

        else:
            super().do_DELETE()


    def handle_shopping_list_get(self):
        self.send_response(200)
        self.send_header('Content-Type', 'application/json')
        self.end_headers()

        if os.path.exists(SHOPPING_LIST_FILE):
            with open(SHOPPING_LIST_FILE, 'r') as file:
                shopping_list = json.load(file)
        else:
            shopping_list = []
        self.wfile.write(json.dumps(shopping_list).encode())

    def handle_add_item_post(self):
        content_length = int(self.headers.get('Content-Length', 0))
        post_data = self.rfile.read(content_length).decode()
        item = json.loads(post_data).get('name', '').strip()
        if not item:
            self.send_response(400)
            self.send_header('Content-Type', 'text/plain; charset=utf-8')
            self.end_headers()
            self.wfile.write('Nombre del ítem vacío.'.encode('utf-8'))
            return

        if os.path.exists(SHOPPING_LIST_FILE):
            with open(SHOPPING_LIST_FILE, 'r') as file:
                shopping_list = json.load(file)
        else:
            shopping_list = []

        shopping_list.append(item)
        with open(SHOPPING_LIST_FILE, 'w') as file:
            json.dump(shopping_list, file)

        self.send_response(200)
        self.send_header('Content-Type', 'text/plain; charset=utf-8')
        self.end_headers()
        self.wfile.write('Ítem agregado exitosamente.'.encode('utf-8'))

    def handle_remove_item_delete(self):
        item_name = self.path.split('/')[-1]
        if os.path.exists(SHOPPING_LIST_FILE):
            with open(SHOPPING_LIST_FILE, 'r') as file:
                shopping_list = json.load(file)
        else:
            shopping_list = []

        shopping_list = [item for item in shopping_list if item != item_name]
        with open(SHOPPING_LIST_FILE, 'w') as file:
            json.dump(shopping_list, file)

        self.send_response(200)
        self.send_header('Content-Type', 'text/plain; charset=utf-8')
        self.end_headers()
        self.wfile.write('Ítem eliminado exitosamente.'.encode('utf-8'))

    def handle_calendar_get(self):
        parsed_url = urllib.parse.urlparse(self.path)
        query_params = urllib.parse.parse_qs(parsed_url.query)
        
        try:
            month = int(query_params.get('month', [None])[0])
            year = int(query_params.get('year', [None])[0])
        except (TypeError, ValueError):
            self.send_response(400)
            self.send_header('Content-Type', 'text/plain; charset=utf-8')
            self.end_headers()
            self.wfile.write('Mes o año no proporcionado correctamente.'.encode('utf-8'))
            return

        if month is None or year is None:
            self.send_response(400)
            self.send_header('Content-Type', 'text/plain; charset=utf-8')
            self.end_headers()
            self.wfile.write('Mes o año no proporcionado.'.encode('utf-8'))
            return

        if os.path.exists(CALENDAR_FILE):
            with open(CALENDAR_FILE, 'r') as file:
                calendar_events = json.load(file)
        else:
            calendar_events = []

        filtered_events = [
            event for event in calendar_events
            if int(event['date'].split('-')[1]) == month and int(event['date'].split('-')[0]) == year
        ]

        self.send_response(200)
        self.send_header('Content-Type', 'application/json')
        self.end_headers()
        self.wfile.write(json.dumps(filtered_events).encode())

    def handle_add_event_post(self):
        content_length = int(self.headers.get('Content-Length', 0))
        post_data = self.rfile.read(content_length).decode()
        event_data = json.loads(post_data)
        date = event_data.get('date', '').strip()
        title = event_data.get('title', '').strip()

        if not date or not title:
            self.send_response(400)
            self.send_header('Content-Type', 'text/plain; charset=utf-8')
            self.end_headers()
            self.wfile.write('Fecha o título del evento vacío.'.encode('utf-8'))
            return

        if os.path.exists(CALENDAR_FILE):
            with open(CALENDAR_FILE, 'r') as file:
                calendar_events = json.load(file)
        else:
            calendar_events = []

        calendar_events.append({'date': date, 'title': title})
        with open(CALENDAR_FILE, 'w') as file:
            json.dump(calendar_events, file)

        self.send_response(200)
        self.send_header('Content-Type', 'text/plain; charset=utf-8')
        self.end_headers()
        self.wfile.write('Evento agregado exitosamente.'.encode('utf-8'))

    def handle_delete_file(self):
        file_name = self.path.split('/')[-1]
        file_path = os.path.join(UPLOAD_DIR, file_name)

        if os.path.exists(file_path):
            os.remove(file_path)
            self.send_response(200)
            self.send_header('Content-Type', 'text/plain; charset=utf-8')
            self.end_headers()
            self.wfile.write('Archivo eliminado exitosamente.'.encode('utf-8'))
        else:
            self.send_response(404)
            self.send_header('Content-Type', 'text/plain; charset=utf-8')
            self.end_headers()
            self.wfile.write('Archivo no encontrado.'.encode('utf-8'))

    def handle_delete_event(self):
        content_length = int(self.headers.get('Content-Length', 0))
        post_data = self.rfile.read(content_length).decode()
        event_data = json.loads(post_data)
        date = event_data.get('date', '').strip()
        title = event_data.get('title', '').strip()

        if not date or not title:
            self.send_response(400)
            self.send_header('Content-Type', 'text/plain; charset=utf-8')
            self.end_headers()
            self.wfile.write('Fecha o título del evento vacío.'.encode('utf-8'))
            return

        if os.path.exists(CALENDAR_FILE):
            with open(CALENDAR_FILE, 'r') as file:
                calendar_events = json.load(file)
        else:
            calendar_events = []

        calendar_events = [event for event in calendar_events if not (event['date'] == date and event['title'] == title)]

        with open(CALENDAR_FILE, 'w') as file:
            json.dump(calendar_events, file)

        self.send_response(200)
        self.send_header('Content-Type', 'text/plain; charset=utf-8')
        self.end_headers()
        self.wfile.write('Evento eliminado exitosamente.'.encode('utf-8'))

 



def run(server_class=HTTPServer, handler_class=CustomHTTPRequestHandler, port=8080):
    server_address = ('', port)
    httpd = server_class(server_address, handler_class)
    print(f'Servidor HTTP corriendo en el puerto {port}...')
    httpd.serve_forever()




if __name__ == "__main__":
    run()