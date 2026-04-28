import uasyncio as asyncio
import usocket as socket

class Server:
    def __init__(self, port):
        self.port = port
        self.server = None # Referencia al objeto de servidor uasyncio
        self.sock = None   # Lo guardaremos para el cierre

    async def run(self, handler):
        
        # 1. Usar el método estándar de uasyncio para iniciar el servidor
        self.server = await asyncio.start_server(self._handle_client(handler), "0.0.0.0", self.port)
        
        # 2. 🚨 PASO CLAVE: Acceder al socket creado internamente y configurarlo
        # En muchas implementaciones de uasyncio, el objeto 'server' tiene un atributo .sock
        try:
            self.sock = self.server.sock 
            # 💡 Configurar la opción SO_REUSEADDR para solucionar EADDRINUSE
            self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            print("SO_REUSEADDR configurado en el socket del servidor.")
        except AttributeError:
            print("Advertencia: No se pudo acceder a self.server.sock para configurar SO_REUSEADDR.")
            # Si esto falla, dependemos de que asyncio.start_server lo haga correctamente.
        
        print(f"Servidor escuchando en puerto {self.port}...")
        
        # Mantener la tarea viva
        while True:
            await asyncio.sleep(1)

    def close(self):
        """Método explícito para cerrar el servidor y liberar el puerto."""
        if self.server:
            # 1. Cerrar el objeto de servidor de uasyncio
            self.server.close()
            self.server = None
        
        if self.sock:
            # 2. Cerrar el socket que configuramos (solo si existe y es necesario)
            self.sock.close()
            self.sock = None
    
    
    

    def guess_type(self, path):
        if path.endswith(".html"):
            return "text/html"
        elif path.endswith(".css"):
            return "text/css"
        elif path.endswith(".js"):
            return "application/javascript"
        elif path.endswith(".png"):
            return "image/png"
        elif path.endswith(".jpg") or path.endswith(".jpeg"):
            return "image/jpeg"
        elif path.endswith(".ico"):
            return "image/x-icon"
        else:
            return "text/plain"
            
    def _handle_client(self, handler):
        async def serve(reader, writer):
            # --- Configuración de Respuesta ---
            http_version = "HTTP/1.1"
            connection_header = "Connection: close\r\n" # La clave para evitar ALPN
            
            try:
                data = await reader.readline()
                if not data:
                    return

                request_line = data.decode().strip()
                method, path, _ = request_line.split()
                print("Solicitud:" + path)

                # --- Lógica de Lectura de Cabeceras (CRÍTICO para POST/Upload) ---
                headers = {}
                while True:
                    line = await reader.readline()
                    if line == b"\r\n" or line == b"":
                        break
                    
                    try:
                        # Leer y parsear las cabeceras
                        name, value = line.decode().strip().split(':', 1)
                        headers[name.strip()] = value.strip()
                    except ValueError:
                        # Si la línea es mal formada, la ignoramos y seguimos
                        pass
                # --- Fin de la lógica de Lectura de Cabeceras ---

                if path == "/":
                    path = "/web/index.html"

                # Pasar las cabeceras al handler
                response = await handler(path, method, reader, headers) 
                content_type = self.guess_type(path)
                
                if "redirect" in response:
                    location = response.split(" ")[1]
                    print(location)
                    # Respuesta 302
                    response_header = (
                        f"{http_version} 302 Found\r\n"
                        f"Location: {location}\r\n"
                        f"{connection_header}"
                        f"\r\n"
                    )
                    writer.write(response_header.encode())
                else:
                    # Respuesta 200 OK
                    response_header = (
                        f"{http_version} 200 OK\r\n"
                        f"Content-Type: {content_type}\r\n"
                        f"{connection_header}" # ¡Aquí la clave!
                        f"\r\n"
                    )
                    writer.write(response_header.encode())
                    
                    if isinstance(response, bytes):
                        writer.write(response)
                    else:
                        writer.write(str(response).encode())

                    await writer.drain()
            except Exception as e:
                # Manejo de errores con Connection: close
                print("Error en handle_client:", e)
                error_response = (
                    f"{http_version} 500 Internal Server Error\r\n"
                    f"{connection_header}"
                    f"\r\n"
                )
                writer.write(error_response.encode())
                await writer.drain()
            finally:
                await writer.aclose()
        return serve