# Refactorización del código original en un módulo para MicroPython

from machine import Pin, reset
import time
import network
import ujson as json
import uos as os
import sys, random
import uasyncio as asyncio
import ure as re
import gc
import cfg

localip =""
roms_files = os.listdir("/roms")

# Nota: Se asumen que 'Server', 'led_ok', 'led_rom' y 'comprueba_rom'
# son definidos/importados en su entorno. Agregamos placeholders.
# Si 'server.py' contiene la clase Server, debe estar en el mismo directorio.
try:
    from server import Server
except ImportError:
    # Placeholder si la clase Server no está disponible para probar
    class Server:
        def __init__(self, port):
            print("Server class placeholder initialized.")
        async def run(self, handler):
            print("Server running placeholder.")
            await asyncio.sleep(86400) # Dormir indefinidamente

config = cfg.carga_config()

# Variables constantes
CHUNK_SIZE = 1024 

# --- Funciones de Red ---

def wifi_reset():
    network.WLAN(network.STA_IF).active(False)
    time.sleep(0.2)
    do_connect(config["wifi"]["ssid"],config["wifi"]["pwd"])
    

def do_connect(ssid, pwd, hard_reset=True):
    """Conecta al WiFi, intentando re-conectar si es necesario."""
    global localip
    network.hostname("ATTINY_PROGRAMMER")
    interface = network.WLAN(network.STA_IF)
    
    try:
        interface.active(True)
        interface.connect(ssid, pwd)
    except Exception as e:
        print(f"Error inicial al intentar conectar WiFi: {e}")

    # Stage zero: if credential are null disconnect
    if not pwd or not ssid:
        print('Disconnecting')
        interface.active(False)
        return None, interface

    # Stage one: check for default connection
    for t in range(1, 40): # 40 * 200ms = 8s
        if interface.isconnected():
            print('- Wifi conectada a', ssid)
            localip, subnet, gateway, dns = interface.ifconfig()
            print(f'- IP asignada: {localip}')
            return True, interface
        time.sleep_ms(200)
        if t % 20 == 0 and hard_reset: 
            print('Reintentando conexión...')
            interface.active(False)
            interface.active(True)
            interface.connect(ssid, pwd)

    print('Cant connect to ', ssid)
    return False, interface


def create_access_point(wlan):
    """Crea un punto de acceso (AP)."""
    print("* Creando punto de acceso")
    wlan.active(False)
    network.hostname("ATTINY_WRITER")
    wlan = network.WLAN(network.AP_IF)
    wlan.active(True)
    wlan.config(essid="ATTINY_WRITER", hidden = False)
    print("Punto de acceso 'ATTINY_WRITER_192.168.4.1' creado.")


# --- Funciones de Configuración Asíncronas ---


async def guarda_info(datos):
    """Actualiza la configuración global y la guarda."""
    global config
    if "ssid" in datos:
        config["wifi"]["ssid"] = datos["ssid"]
    if "pwd" in datos:
        config["wifi"]["pwd"] = datos["pwd"]
    cfg.guarda_config(config)
    reset()
    return

# --- Funciones de Utilidad HTTP ---

def render_template(template_str, context):
    """Remplaza placeholders {{...}} en una plantilla."""
    def replacer(match):
        expr = match.group(1).strip()
        try:
            return str(eval(expr, {"config": config, "os": os, "sys": sys}, context))
        except Exception as e:
            print("Error evaluando:", expr, "->", e)
            return ''
    
    return re.sub(r'\{\{(.*?)\}\}', replacer, template_str)

def parse_form_data(body):
    """Convierte un cuerpo de formulario URL-encoded a un diccionario."""
    data = {}
    for pair in body.split('&'):
        if '=' in pair:
            k, v = pair.split('=', 1)
            data[k] = v.replace('+', ' ').strip()
    return data


# --- HTTP Handler (El núcleo de tu lógica de subida de archivo) ---

async def handler(path, method, reader, headers):
    """Manejador principal de peticiones web."""
    
    content_length = 0
    content_type = headers.get('content-type', '')
    #print(headers)
    if 'Content-Length' in headers:
        try:
            content_length = int(headers['Content-Length'])
        except ValueError:
            pass 
            
    # print(f"Handling {method} {path}. Content-Length: {content_length}")
    
    if path == '/upload' and method == 'POST':
        try:
            print(">> Iniciando subida de archivo (Multipart)..",content_length)
            
            if content_length <= 0:
                return "error: Content-Length requerido o inválido"
                
            bytes_skipped = 0
            
            # Intento de parsear el boundary
            boundary_bytes = None
            if content_type.startswith('multipart/form-data') and 'boundary=' in content_type:
                boundary = content_type.split('boundary=')[1].strip()
                boundary_bytes = b'--' + boundary.encode()
            
            # 1. Consumir el primer boundary
            first_boundary_line = await reader.readline()
            bytes_skipped += len(first_boundary_line)
            
            # 2. Consumir las 3 líneas de cabecera del archivo
            filename = 'rom.hex' # por si acaso no lee el nombre del archivo
            for _ in range(3):
                line = (await reader.readline()).decode('utf-8').strip()
                if line.startswith('Content-Disposition'):
                    match = re.search(r'filename="([^"]+)"', line)
                    if match:
                        filename = match.group(1)
                bytes_skipped += len(line)
                
            print(f"Saltado envoltorio multipart ({bytes_skipped} bytes).")

            # --- LÓGICA DE LECTURA DE ARCHIVO ---
            bytes_to_read_total = content_length - bytes_skipped
            
            # Restar el tamaño aproximado del footer (boundary final)
            footer_size_approx = len(boundary_bytes) + 6 if boundary_bytes else 50
            bytes_to_read_file_data = bytes_to_read_total - footer_size_approx
            
            if bytes_to_read_file_data <= 0:
                 return "error: Formato Multipart inválido o archivo vacío"

            # Preparación para guardar
            
            try:
                os.mkdir('roms')
            except OSError:
                pass 

            filepath = 'roms/' + filename
            print(f"Guardando {bytes_to_read_file_data} bytes en: {filepath}")

            total_read = 0

            with open(filepath, 'wb') as f:
                bytes_to_read = bytes_to_read_file_data
                while bytes_to_read > 0:
                    chunk_size = min(CHUNK_SIZE, bytes_to_read) 
                    chunk = await reader.read(chunk_size) 
                    
                    if not chunk:
                        print("🔴 ERROR: Cliente cerró la conexión prematuramente.")
                        break 

                    f.write(chunk)
                    
                    bytes_read_in_chunk = len(chunk)
                    total_read += bytes_read_in_chunk
                    bytes_to_read -= bytes_read_in_chunk

                # Consumir el FOOTER multipart restante del stream
                footer_remaining = bytes_to_read_total - total_read
                if footer_remaining > 0:
                    await reader.read(footer_remaining)

            if total_read == bytes_to_read_file_data:
                print(f"✅ Archivo guardado correctamente ({total_read} bytes)")
                return "ok"
            else:
                print(f"❌ Subida incompleta. Recibidos: {total_read} de {bytes_to_read_file_data} bytes.")
                return "error: carga incompleta"

        except Exception as e:
            sys.print_exception(e)
            print(f"🔴 ERROR durante la subida: {e}")
            return "error interno"
        finally:
             pass
    
    # --- Otros manejadores POST ---
    if path == '/info' and method == 'POST':
        raw_body = await reader.read(content_length) if content_length > 0 else await reader.read(1024)
        body = raw_body.decode()
        form = parse_form_data(body) 
        await guarda_info(form)
        return "redirect /reset"
    
    # --- Manejador de archivos estáticos (GET) ---
    modo = 'rb' if path.endswith((".jpg", ".jpeg", ".png", ".ico", ".svg",".hex")) else 'r'
    file_path = path[1:]
    if not file_path:
        file_path = "web/index.html" # Ruta por defecto
    
    try:
        if not file_path.startswith("static/") and not file_path.startswith("web/") and not file_path.startswith("roms/"):
             file_path = "web/" + file_path
        
        if file_path.endswith((".html", ".htm")):
            with open(file_path, modo) as f:
                 template_content = f.read()
                 context = {"data": config, "roms": roms_files}
                 return render_template(template_content, context)
        else:
            print("entregando",file_path)
            with open(file_path, modo) as f:
                return f.read()
                
    except OSError as e:
        print(f"Error al servir archivo {file_path}: {e}")
        return "Archivo no encontrado", 404


async def watchdog_task(back_btn):
    """Monitorea el botón de retroceso y detiene el bucle principal si se presiona."""
    print("Iniciando vigilancia de botón...")
    while True:
        # Verifica la condición de parada
        if back_btn.value() == 0:
            print("\n🚨 Botón de parada detectado. Deteniendo tareas.")
            # Forzar la salida de asyncio.run() levantando KeyboardInterrupt
            # Es el mecanismo más limpio para detener el bucle principal en uasyncio.
            raise KeyboardInterrupt 
            
        await asyncio.sleep_ms(50) # Espera 50ms para evitar el polling constante (desperdicio de CPU)

async def main_tasks(back_btn):
    server_instance = Server(port=80) 
    server_task = asyncio.create_task(server_instance.run(handler))
    button_task = asyncio.create_task(watchdog_task(back_btn))

    try:
        await asyncio.gather(server_task, button_task)
    
    except BaseException as e:
        print("Cerrando tareas y servidor...")
        # 1. Cancelar la tarea asíncrona (el run del servidor)
        server_task.cancel()
        button_task.cancel()
        
        # 2. Esperar a que la tarea cancelada termine (para limpieza interna)
        try:
            await server_task
        except asyncio.CancelledError:
            pass
            
        # 3. 🚨 PASO FINAL CRÍTICO: Llamar al método de cierre del Server
        # Esto desvincula el socket del puerto 80.
        server_instance.close()
        await asyncio.sleep_ms(200)
        
        # Propagamos la excepción para salir de asyncio.run()
        raise e

def run(oled, back_btn, OLED_WIDTH, OLED_HEIGHT, utime, math, random, framebuf):
    """Función de inicio que encapsula la lógica de conexión y el bucle principal."""
    # Intentar conexión WiFi / Crear AP
    print("--- Iniciando Attiny Programmer ---")
    oled.fill(0)
    oled.text("Cargando server...", 1, 0, 1)
    oled.show()
    connected, wlan = do_connect(config["wifi"]["ssid"], config["wifi"]["pwd"])
    if not connected:
        create_access_point(wlan)
        oled.fill(0)
        oled.text("Servidor activo:", 1, 0, 1)
        oled.text("Conecta a la red", 1, 16, 1)
        oled.text(f'ATTINY_WRITER', 1, 32, 1)
        oled.text(f'IP:192.168.4.1', 1, 48, 1)
        oled.show()
    else:
        oled.fill(0)
        oled.text("Servidor activo:", 1, 0, 1)
        oled.text("Red:"+config["wifi"]["ssid"], 1, 16, 1)
        oled.text(f'IP asignada:', 1, 32, 1)
        oled.text(f'{localip}', 1, 48, 1)
        oled.show()
        
    # Arrancar el bucle asíncrono
    try:
        asyncio.run(main_tasks(back_btn))
    except KeyboardInterrupt:
        print("Servidor detenido manualmente.")
        config["fastboot"] = True
        cfg.guarda_config(config)
        reset()
        
    except Exception as e:
        sys.print_exception(e)
        print("Error fatal en el bucle principal.")


