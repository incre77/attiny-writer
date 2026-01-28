import uos
import utime
import gc
import sys
import cfg
from machine import reset

# Variables de configuración
# NOTA: Estas variables deberían cargarse o definirse en tu main.py y pasarse.
# Se mantienen aquí solo para que el módulo sea funcional, asumiendo cfg.carga_config() existe.
config = cfg.carga_config()
ROMS_PATH = "/roms"
MENU_ITEMS = ["GRABAR", "BORRAR"] 
DEBOUNCE_DELAY = 200

# --- VARIABLES DE MARQUESINA LOCALES ---
marquee_offset = 0
last_marquee_time = 0
MARQUEE_DELAY_MS = 1500 # Esperar 1.5s antes de empezar a mover
MARQUEE_SPEED_MS = 100  # Tiempo entre cada desplazamiento de 1 pixel
MARQUEE_MAX_WIDTH = 120 # Espacio disponible para el texto del menú (128 - 8 de margen)
marquee_direction = 1   # 1: izquierda, -1: derecha (ping-pong)


def read_button(pin):
    if pin.value() == 0:
        utime.sleep_ms(20) # Pequeño debounce inicial
        if pin.value() == 0:
            start_time = utime.ticks_ms()
            timeout = 100
            while pin.value() == 0 and utime.ticks_diff(utime.ticks_ms(), start_time) < timeout:
                utime.sleep_ms(10) 
            return True
            
    return False

# --- LÓGICA DE ACTUALIZACIÓN DE MARQUESINA CORREGIDA ---
def update_marquee(item):
    """Actualiza el desplazamiento de la marquesina."""
    global marquee_offset, last_marquee_time, marquee_direction, MARQUEE_SPEED_MS, MARQUEE_DELAY_MS, MARQUEE_MAX_WIDTH
    
    current_time = utime.ticks_ms()
    text_width = len(item) * 8
    
    # Calcular el desplazamiento máximo. Se asume un espacio de 8 píxeles inicial.
    max_scroll = text_width - MARQUEE_MAX_WIDTH + 8 # +8 píxeles del "> " y espacio inicial
    
    if max_scroll <= 0:
        # No necesita desplazamiento
        return 0

    # 1. Control del Retraso Inicial (Antes de empezar el primer movimiento)
    if marquee_offset == 0 and marquee_direction == 1:
        if utime.ticks_diff(current_time, last_marquee_time) < MARQUEE_DELAY_MS:
            return 0 # Esperar el tiempo de retardo inicial

    # 2. Control de la Cadencia de Movimiento
    # Mover el texto cada MARQUEE_SPEED_MS
    if utime.ticks_diff(current_time, last_marquee_time) > MARQUEE_SPEED_MS:
        
        # Aplicar desplazamiento en la dirección actual
        marquee_offset += marquee_direction
        
        # Actualizar el tiempo para el PRÓXIMO movimiento
        last_marquee_time = current_time 
        
        # 3. Lógica para invertir la dirección (Efecto Ping-Pong)
        if marquee_offset >= max_scroll:
            marquee_direction = -1 # Cambia a dirección de vuelta (derecha)
            marquee_offset = max_scroll 
            last_marquee_time = current_time + MARQUEE_DELAY_MS # Espera extra en el límite final
        
        elif marquee_offset <= 0:
            marquee_direction = 1 # Cambia a dirección normal (izquierda)
            marquee_offset = 0 
            last_marquee_time = current_time + MARQUEE_DELAY_MS # Espera extra en el límite inicial
            
    # Devolver el desplazamiento negativo para el dibujo (mover el texto hacia la izquierda)
    return -marquee_offset


# --- Funciones Auxiliares de Dibujo ---

def draw_file_list(oled, files, current_index, height):
    """Dibuja la lista de archivos, marcando el actual."""
    height = height - 10
    oled.text("LISTADO DE ROMS", 0, 0)
    oled.hline(0, 15, 128, 1) # Separador
    start_display = max(0, current_index - (height // 10) + 2)
    
    # Reiniciar la marquesina si salimos del modo opción
    global marquee_offset, marquee_direction
    
    for i in range(start_display, len(files)):
        name = files[i]
        line = i - start_display + 2
        
        if line * 10 < height:
            color = 1 
            x_pos = 0
            
            if i == current_index:
                # 🚨 Aplicar marquesina SOLO al elemento seleccionado 🚨
                x_offset = update_marquee(name)
                x_pos += x_offset
                
                oled.fill_rect(0, line * 10 - 1, 128, 9, 1) # Fondo blanco
                color = 0 # Texto negro
                
                # Dibujar el texto. El ancho total del dibujo es 128.
                oled.fill_rect(0, line * 10 - 1, 128, 9, 1) # Repintar fondo
                #oled.text("> " + name, x_pos, line * 10, 0)
                oled.text(name, x_pos, line * 10, 0)
            else:
                #oled.text("  " + name, x_pos, line * 10, 1)
                oled.text( name, x_pos, line * 10, 1)

            
def draw_options_menu(oled, selected_file, options, current_index):
    """Dibuja el menú de opciones para el archivo seleccionado."""
    
    # 🚨 Aplicar marquesina al nombre del archivo en la cabecera del menú de opciones 🚨
    x_offset = update_marquee(selected_file)
    
    # Dibujar nombre del archivo (con marquesina)
    oled.fill_rect(0, 0, 128, 8, 0) # Limpiar área de cabecera
    
    oled.text(selected_file, x_offset, 0, 1)
    
    oled.hline(0, 15, 128, 1) # Separador
    
    # Dibujar opciones
    for i, option in enumerate(options):
        color = 1
        if i == current_index:
            oled.fill_rect(0, 20 + i * 10 - 1, 128, 9, 1) # Fondo blanco
            color = 0
            
        prefix = "> " if i == current_index else "  "
        oled.text(prefix + option, 0, 20 + i * 10, color)


def handle_option_selection(oled, files, file_index, options, option_index,  ROMS_PATH, back_btn, select_btn, OLED_WIDTH, OLED_HEIGHT, utime, math, random, framebuf):
    """Ejecuta la acción seleccionada."""
    global config # Acceder a la configuración global para guardarla
    selected_option = options[option_index]
    selected_file = files[file_index]
    
    # --- BORRAR ---
    if selected_option == "BORRAR":
        try:
            full_path = f"{ROMS_PATH}/{selected_file}"
            uos.remove(full_path)
            oled.fill(0)
            oled.text(f"Borrado: {selected_file}", 0, 0)
            oled.show()
            utime.sleep(1)
            if config["lastrom"] == selected_file:
                config["lastrom"] = ""
                config["fastboot"] = True
                cfg.guarda_config(config)
                reset()
            return "BORRAR" 
        except Exception as e:
            oled.text("Error borrando:", 0, 10)
            oled.text(str(e), 0, 20)
            oled.show()
            utime.sleep(2)
            return "ATRAS"
            
    # --- GRABAR ---
    elif selected_option == "GRABAR":
        oled.fill(0)
        oled.text(f"Grabando {selected_file}...", 0, 0)
        config["lastrom"] = selected_file
        cfg.guarda_config(config)
        oled.show()
        
        # Lógica de carga perezosa para el módulo de grabación
        try:
            modulo = __import__("grabarom") 
            # ASUMIMOS que grabarom.run usa el mismo protocolo de salida (KeyboardInterrupt)
            modulo.run(oled, back_btn, select_btn, OLED_WIDTH, OLED_HEIGHT, utime, math, random, framebuf)
        except Exception as e:
            # Manejo de error específico de la grabación
            oled.fill(0)
            oled.text(f"Error Grabando:", 0, 0)
            oled.text(str(e), 0, 10)
            oled.show()
            utime.sleep(2)
        finally:
            if "grabarom" in sys.modules:
                 del sys.modules["grabarom"]
            gc.collect()

        return "ATRAS" 

    # --- ATRAS ---
    elif selected_option == "<- ATRAS":
        return "ATRAS"
        
    return None

# --- Función Principal RUN ---

def run(oled, up_btn, down_btn, select_btn, back_btn, OLED_WIDTH, OLED_HEIGHT, utime, math, random, framebuf):
    """Función principal que maneja la interfaz de archivos."""
    
    gc.collect() 
    
    # --- Inicialización y Carga de Archivos ---
    files = []
    try:
        files = [f[0] for f in uos.ilistdir(ROMS_PATH) ]
    except OSError:
        try: uos.mkdir(ROMS_PATH)
        except: pass
        
    if not files:
        oled.fill(0)
        oled.text("No hay ROMs en /roms", 0, 0)
        oled.show()
        utime.sleep(1)
        raise KeyboardInterrupt 
        
    # --- Estado de la Interfaz ---
    current_file_index = 0
    option_mode = False  # False: Selección de archivo; True: Selección de opción
    current_option_index = 0
    
    SELECT_BTN_PIN = select_btn 
    UP_BTN_PIN = up_btn
    DOWN_BTN_PIN = down_btn

    # Reiniciar el estado de la marquesina al iniciar el módulo
    global marquee_offset, last_marquee_time, marquee_direction
    marquee_offset = 0
    marquee_direction = 1
    last_marquee_time = utime.ticks_ms()
    
    try:
        while True:
            # 1. Dibujar la Pantalla
            oled.fill(0)
            
            if not option_mode:
                draw_file_list(oled, files, current_file_index, OLED_HEIGHT)
            else:
                draw_options_menu(oled, files[current_file_index], MENU_ITEMS, current_option_index)
                
            oled.show()
            
            # 2. Manejar la Entrada de Botones (navegación y selección)
            
            # Botón BACK: Salir/Atrás de forma inmediata
            if read_button(back_btn):
                if option_mode:
                    # Si estás en el menú de opciones, vuelve a la lista
                    option_mode = False
                    # Reiniciar marquesina
                    marquee_offset = 0
                    marquee_direction = 1
                    last_marquee_time = utime.ticks_ms()
                else:
                    # Si estás en la lista, sal al menú principal
                    break # Sale del bucle, dispara KeyboardInterrupt

            # Botón UP
            elif read_button(UP_BTN_PIN):
                # Reiniciar marquesina al cambiar de selección
                marquee_offset = 0
                marquee_direction = 1
                last_marquee_time = utime.ticks_ms()
                
                if not option_mode:
                    current_file_index = (current_file_index - 1) % len(files)
                else:
                    current_option_index = (current_option_index - 1) % len(MENU_ITEMS)
                    
            # Botón DOWN
            elif read_button(DOWN_BTN_PIN):
                # Reiniciar marquesina al cambiar de selección
                marquee_offset = 0
                marquee_direction = 1
                last_marquee_time = utime.ticks_ms()
                
                if not option_mode:
                    current_file_index = (current_file_index + 1) % len(files)
                else:
                    current_option_index = (current_option_index + 1) % len(MENU_ITEMS)
                    
            # Botón SELECT
            elif read_button(SELECT_BTN_PIN): 
                
                if not option_mode:
                    # Modo Archivo: Entrar al menú de opciones
                    option_mode = True
                    current_option_index = 0
                    # Reiniciar marquesina para el nombre de la opción
                    marquee_offset = 0
                    marquee_direction = 1
                    last_marquee_time = utime.ticks_ms()
                else:
                    # Modo Opciones: Ejecutar acción
                    action = handle_option_selection(
                        oled, files, current_file_index, MENU_ITEMS, current_option_index,  ROMS_PATH,
                        back_btn, select_btn, OLED_WIDTH, OLED_HEIGHT, utime, math, random, framebuf
                    )
                    
                    if action == "BORRAR":
                        files = [f[0] for f in uos.ilistdir(ROMS_PATH)]
                        if not files:
                            raise KeyboardInterrupt
                        current_file_index = min(current_file_index, len(files) - 1)
                        option_mode = False 
                    elif action == "ATRAS":
                        option_mode = False 
                        # Reiniciar marquesina
                        marquee_offset = 0
                        marquee_direction = 1
                        last_marquee_time = utime.ticks_ms()
                        
            else:
                # Si no hay interacción, un pequeño sleep para no saturar el CPU
                utime.sleep_ms(10)
                
    except KeyboardInterrupt:
        # Re-lanzar para salir correctamente al main.py
        raise
    except Exception as e:
        sys.print_exception(e)
        oled.fill(0)
        oled.text("ERROR FATAL", 0, 0)
        oled.text(str(e), 0, 10)
        oled.show()
        utime.sleep(3)
        
    finally:
        gc.collect()