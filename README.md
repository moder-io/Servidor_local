# Proyecto de Servidor Simple

Este proyecto implementa un servidor HTTP simple con funcionalidades de gestión de archivos, lista de compras y calendario.

## Características

- Carga y descarga de archivos
- Gestión de lista de compras
- Gestión de eventos de calendario
- Medidas básicas de seguridad

## Componentes

1. `server.py`: Script principal del servidor
2. `handler.py`: Manejador personalizado de solicitudes HTTP
3. `index.html`: Interfaz frontend

## Configuración y Ejecución

1. Asegúrese de tener Python 3.x instalado.
2. Clone este repositorio:
   ```
   git clone <url-del-repositorio>
   cd <directorio-del-repositorio>
   ```
3. Ejecute el servidor:
   ```
   python server.py
   ```
4. Acceda a la interfaz web en `http://<su-ip>:8080`

## Funcionalidad

### Gestión de Archivos

- Subir archivos al directorio `uploads/`
- Descargar archivos del servidor
- Eliminar archivos del servidor

### Lista de Compras

- Agregar artículos a la lista de compras
- Eliminar artículos de la lista de compras
- Ver la lista de compras actual

### Calendario

- Agregar eventos al calendario
- Ver eventos por mes y año
- Eliminar eventos del calendario

## Medidas de Seguridad

- Verificaciones de extensión de archivo y tipo MIME
- Sanitización de nombres de archivo
- Límite de tamaño máximo de archivo (1GB)
- Verificación de espacio en disco antes de la carga de archivos

## Registro

Las actividades del servidor se registran en `server.log`.