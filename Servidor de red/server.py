import http.server
import socketserver
import os
import json
import nmap
import socket
import psutil
import time
import subprocess
import platform

PORT = 80
DIRECTORY = "server1"
HOSTNAME = socket.gethostname()
IP = socket.gethostbyname(HOSTNAME)

class MyHandler(http.server.SimpleHTTPRequestHandler):
    def translate_path(self, path):
        path = super().translate_path(path)
        return os.path.join(DIRECTORY, os.path.relpath(path, os.path.dirname(path)))

    def do_GET(self):
        try:
            if self.path == "/":
                super().do_GET()
            elif self.path == "/scan":
                devices = self.scan_network()
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(json.dumps(devices).encode())
            elif self.path == "/bandwidth":
                bandwidth_usage = self.get_bandwidth_usage()
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(json.dumps(bandwidth_usage).encode())
            elif self.path == "/logs":
                try:
                    with open("network_log.txt", "r") as log_file:
                        logs = log_file.read()
                    self.send_response(200)
                    self.send_header("Content-Type", "text/plain")
                    self.end_headers()
                    self.wfile.write(logs.encode())
                except FileNotFoundError:
                    self.send_response(404)
                    self.end_headers()
                    self.wfile.write(b"Log file not found.")
            elif self.path == "/network_processes":
                processes = self.get_network_processes()
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(json.dumps(processes).encode())
            elif self.path == "/ping_latency":
                latency = self.get_ping_latency()
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(json.dumps(latency).encode())
            else:
                super().do_GET()
        except Exception as e:
            self.send_response(500)
            self.end_headers()
            self.wfile.write(f"Error: {str(e)}".encode())

    def scan_network(self):
        try:
            nm = nmap.PortScanner()
            nm.scan('192.168.1.0/24', arguments='-sn')  # Ajusta el rango de IP según tu red
            devices = []
            
            for host in nm.all_hosts():
                device_info = {
                    'ip': host,
                    'hostname': nm[host].hostname() if nm[host].hostname() else 'N/A',
                    'state': nm[host].state(),
                }
                # Agrega la dirección MAC si está disponible
                if 'addresses' in nm[host]:
                    device_info['mac'] = nm[host]['addresses'].get('mac', 'N/A')
                devices.append(device_info)
            
            return devices
        
        except nmap.PortScannerError as nmap_error:
            print(f"Error de Nmap: {str(nmap_error)}")
        except Exception as e:
            print(f"Error al escanear la red: {str(e)}")
        
        return []

    def get_bandwidth_usage(self):
        try:
            # Obtener estadísticas iniciales
            start_net_io = psutil.net_io_counters(pernic=True)
            time.sleep(1)  # Esperar 1 segundo para medir la velocidad
            # Obtener estadísticas finales
            end_net_io = psutil.net_io_counters(pernic=True)

            bandwidth_usage = {}
            for interface, end_stats in end_net_io.items():
                start_stats = start_net_io.get(interface)
                if start_stats:
                    # Calcular la velocidad de transferencia
                    bytes_sent = end_stats.bytes_sent - start_stats.bytes_sent
                    bytes_recv = end_stats.bytes_recv - start_stats.bytes_recv
                    packets_sent = end_stats.packets_sent - start_stats.packets_sent
                    packets_recv = end_stats.packets_recv - start_stats.packets_recv

                    bandwidth_usage[interface] = {
                        'bytes_sent': str(end_stats.bytes_sent),
                        'bytes_recv': str(end_stats.bytes_recv),
                        'packets_sent': str(end_stats.packets_sent),
                        'packets_recv': str(end_stats.packets_recv),
                        'send_speed_bps': str(bytes_sent * 8),
                        'recv_speed_bps': str(bytes_recv * 8),
                        'send_speed_mbps': str(round(bytes_sent * 8 / 1_000_000, 2)),
                        'recv_speed_mbps': str(round(bytes_recv * 8 / 1_000_000, 2)),
                        'packets_sent_per_sec': str(packets_sent),
                        'packets_recv_per_sec': str(packets_recv),
                        'errin': str(end_stats.errin),
                        'errout': str(end_stats.errout),
                        'dropin': str(end_stats.dropin),
                        'dropout': str(end_stats.dropout)
                    }

                    # Obtener información adicional de la interfaz
                    addrs = psutil.net_if_addrs().get(interface, [])
                    for addr in addrs:
                        if addr.family == socket.AF_INET:
                            bandwidth_usage[interface]['ip_address'] = addr.address
                        elif addr.family == psutil.AF_LINK:
                            bandwidth_usage[interface]['mac_address'] = addr.address

                    # Obtener estadísticas de la interfaz
                    stats = psutil.net_if_stats().get(interface)
                    if stats:
                        bandwidth_usage[interface]['is_up'] = str(stats.isup)
                        bandwidth_usage[interface]['speed_mb'] = str(stats.speed)
                        bandwidth_usage[interface]['mtu'] = str(stats.mtu)

            return bandwidth_usage
        except Exception as e:
            return {'error': str(e)}

    def get_network_processes(self):
        try:
            network_processes = []
            for conn in psutil.net_connections():
                try:
                    process = psutil.Process(conn.pid)
                    network_processes.append({
                        'pid': conn.pid,
                        'name': process.name(),
                        'status': conn.status,
                        'local_address': f"{conn.laddr.ip}:{conn.laddr.port}",
                        'remote_address': f"{conn.raddr.ip}:{conn.raddr.port}" if conn.raddr else "N/A",
                        'type': conn.type 
                    })
                except psutil.NoSuchProcess:
                    pass
            return network_processes
        except Exception as e:
            return {'error': str(e)}


    def ping(self, host):
        param = '-n' if platform.system().lower() == 'windows' else '-c'
        command = ['ping', param, '4', host]
        try:
            output = subprocess.check_output(command, stderr=subprocess.STDOUT).decode('latin-1').strip()
            print(f'Output for {host}: {output}')  # Imprimir la salida para depuración
            lines = output.split('\n')
            if platform.system().lower() == 'windows':
                for line in lines:
                    if 'Average' in line:
                        return line.split('=')[-1].strip().split()[0]  # Extrae el tiempo promedio
            else:
                for line in lines:
                    if 'avg' in line:
                        return line.split('=')[-1].split('/')[1].strip()  # Extrae el tiempo promedio
        except subprocess.CalledProcessError as e:
            return f'Error: {e.output.decode("latin-1").strip()}'
        except Exception as e:
            return 'Error: {}'.format(str(e))

    def get_ping_latency(self):
        hosts = ['google.com', 'facebook.com', 'amazon.com']
        results = {}
        for host in hosts:
            results[host] = self.ping(host)
        return results

with socketserver.TCPServer(("", PORT), MyHandler) as httpd:
    print(f"Servidor iniciado en http://{IP}:{PORT}")
    httpd.serve_forever()