# main.py - Gestor de Menú y Carga Perezosa (Lazy Loading) con Marquesina

import machine
import utime
import gc # Recolector de basura
import framebuf
import random
import math
import sys # Importante para liberar módulos
import cfg

# --- CONFIGURACIÓN DE PINES Y PERIFÉRICOS ---
I2C_SDA = 8 # 5
I2C_SCL = 9 # 6

PIN_UP = 10
PIN_DOWN = 20
PIN_SELECT = 21
PIN_BACK = 0


OLED_WIDTH = 128
OLED_HEIGHT = 64
OLED_ADDR = 0x3c

config = cfg.carga_config()

# --- ESTRUCTURA DEL MENÚ ---
menu_items = [
    "Listar roms",
    "Subir rom", # Texto largo para probar marquesina
    "Leer rom", # Texto largo para probar marquesina
    "Reiniciar" # Texto largo para probar marquesina
]

menu_files = [ # Mapeo de item a archivo
    "listar", "miserver","leerom","reset"
]


if config["lastrom"]:
    menu_items.insert(0, "Grabar:" + config["lastrom"])
    menu_files.insert(0, "grabarom"),
    

# Definición de Estados
STATE_MENU = 0
current_state = STATE_MENU

menu_index = 0
menu_top_item = 0
MAX_VISIBLE_ITEMS = 5

# --- VARIABLES DE MARQUESINA ---
marquee_offset = 0
last_marquee_time = 0
MARQUEE_DELAY_MS = 100 # Esperar 1.5s antes de empezar a mover
MARQUEE_SPEED_MS = 100 # Tiempo entre cada desplazamiento de 1 pixel
MARQUEE_MAX_WIDTH = OLED_WIDTH - 20 # Espacio disponible para el texto del menú (aprox)
marquee_direction = 1 # 1: izquierda, -1: derecha (ping-pong)



# --- INICIALIZACIÓN DE I2C Y PANTALLA ---
try:
    i2c = machine.I2C(0, sda=machine.Pin(I2C_SDA), scl=machine.Pin(I2C_SCL))
    import ssd1306 
    oled = ssd1306.SSD1306_I2C(OLED_WIDTH, OLED_HEIGHT, i2c, addr=OLED_ADDR)
    """
    oled.fill(0)
    oled.text("Cargando...", 0, 0)
    oled.show()
    utime.sleep(1)
    """
    print("OLED inicializado correctamente.")
except Exception as e:
    print(f"Error al inicializar I2C/OLED: {e}")
    oled = None
  
  
if not config["fastboot"]:
    # --------------------  CARGAR LOGO -----------------------------------------------------
    module = __import__("logo") 
    module.run(oled)
    if "logo" in sys.modules:
        del sys.modules["logo"] # Desreferencia el módulo del sistema
    del module # Elimina la referencia local
    gc.collect() # Ejecuta el recolector de basura
else:   
    config["fastboot"] = False
    cfg.guarda_config(config)

# --- INICIALIZACIÓN DE BOTONES ---
up_btn = machine.Pin(PIN_UP, machine.Pin.IN, machine.Pin.PULL_UP)
down_btn = machine.Pin(PIN_DOWN, machine.Pin.IN, machine.Pin.PULL_UP)
select_btn = machine.Pin(PIN_SELECT, machine.Pin.IN, machine.Pin.PULL_UP)
back_btn = machine.Pin(PIN_BACK, machine.Pin.IN, machine.Pin.PULL_UP)
last_press_time = 0
debounce_delay = 200

# --- MANEJO DE ENTRADA Y NAVEGACIÓN ---
def read_button(pin):
    global last_press_time
    current_time = utime.ticks_ms()
    if pin.value() == 0 and utime.ticks_diff(current_time, last_press_time) > debounce_delay:
        last_press_time = current_time
        return True
    return False

def handle_menu_input():
    global menu_index, menu_top_item, current_state, marquee_offset, last_marquee_time, marquee_direction
    
    # Reiniciar la marquesina al cambiar de elemento
    input_received = False
    
    # Navegación hacia arriba
    if read_button(up_btn):
        # Manejo del índice con wrap-around (vuelve al final si está en 0)
        menu_index = (menu_index - 1)
        if menu_index < 0:
            menu_index = len(menu_items) - 1
            
        # Manejo del scroll de la pantalla
        if menu_index < menu_top_item:
            menu_top_item = menu_index
        elif menu_index == len(menu_items) - 1:
            menu_top_item = menu_index - MAX_VISIBLE_ITEMS + 1
            if menu_top_item < 0: menu_top_item = 0 # Asegura que no sea negativo
            
        input_received = True
        utime.sleep_ms(100)
        
    # Navegación hacia abajo
    elif read_button(down_btn):
        # Manejo del índice con wrap-around (vuelve a 0 si está en el final)
        menu_index = (menu_index + 1) % len(menu_items)
        
        # Manejo del scroll de la pantalla
        if menu_index >= menu_top_item + MAX_VISIBLE_ITEMS: 
            menu_top_item = menu_index - MAX_VISIBLE_ITEMS + 1
        elif menu_index == 0:
            menu_top_item = 0
            
        input_received = True
        utime.sleep_ms(100)
        
    # Selección
    elif read_button(select_btn):
        current_state = menu_index + 1
        input_received = True
        utime.sleep_ms(200)

    # Si se detecta cualquier entrada, reiniciar el estado de la marquesina
    if input_received:
        marquee_offset = 0
        marquee_direction = 1 # Restablecer dirección a izquierda (inicio)
        last_marquee_time = utime.ticks_ms()
        #print(f"Index: {menu_index}, Top: {menu_top_item}, Items: {len(menu_items)}")
        
def draw_menu():
    oled.fill(0)
    oled.text(" ATTINY  WRITER", 0, 0, 1)
    oled.hline(0, 15, 128, 1) # Separador
    
    # Indicadores de scroll
    if menu_top_item > 0: oled.text("^", OLED_WIDTH - 8, 10, 1)
    if menu_top_item + MAX_VISIBLE_ITEMS < len(menu_items): oled.text("v", OLED_WIDTH - 8, OLED_HEIGHT - 8, 1)
    
    for i in range(MAX_VISIBLE_ITEMS):
        item_index = menu_top_item + i
        if item_index >= len(menu_items): break
            
        item = menu_items[item_index]
        y_pos = 16 + i * 9
        
        text_width = len(item) * 8
        x_pos = 5 # Posición inicial del texto
        
        if item_index == menu_index:
            # Opción Seleccionada (Fondo blanco, texto negro)
            oled.fill_rect(0, y_pos - 1, OLED_WIDTH - 10, 9, 1)
            
            # Lógica de Marquesina
            if text_width > MARQUEE_MAX_WIDTH:
                # Aplicar desplazamiento (el offset es negativo)
                x_pos -= marquee_offset
                
                # Dibujar texto negro sobre el fondo blanco
                #oled.text("> " + item, x_pos, y_pos, 0)
                oled.text(item, x_pos, y_pos, 0)
            else:
                # Texto corto, sin desplazamiento
                #oled.text("> " + item, x_pos, y_pos, 0)
                oled.text(item, x_pos, y_pos, 0)
                
        else:
            # Opción NO Seleccionada (Fondo negro, texto blanco)
            #oled.text("  " + item, x_pos, y_pos, 1)
            oled.text(item, x_pos, y_pos, 1)
            
    oled.show()

# --- BUCLE PRINCIPAL (EL GESTOR DE CARGA Y MARQUESINA) ---

if oled:
    while True:
        current_time = utime.ticks_ms()
        
        if current_state == STATE_MENU:
            # Lógica de actualización de la marquesina
            
            selected_item = menu_items[menu_index]
            text_width = len(selected_item) * 8
            # Calcular el desplazamiento máximo (incluye el "> " inicial)
            max_scroll = text_width - MARQUEE_MAX_WIDTH + 8
            
            # Solo si el texto es largo y ha pasado el tiempo de espera, mover
            if max_scroll > 0 and utime.ticks_diff(current_time, last_marquee_time) > MARQUEE_DELAY_MS:
                
                # Mover el texto cada MARQUEE_SPEED_MS
                if utime.ticks_diff(current_time, last_marquee_time) > (MARQUEE_DELAY_MS + MARQUEE_SPEED_MS - 100):
                    
                    # Aplicar desplazamiento en la dirección actual
                    marquee_offset += marquee_direction
                    last_marquee_time = current_time 
                    
                    # Lógica para invertir la dirección (Efecto Ping-Pong)
                    if marquee_offset >= max_scroll:
                        marquee_direction = -1 # Cambia a dirección de vuelta (derecha)
                        marquee_offset = max_scroll 
                        # Espera extra en el límite final para que se pueda leer
                        last_marquee_time = current_time + 1000
                    
                    elif marquee_offset <= 0:
                        marquee_direction = 1 # Cambia a dirección normal (izquierda)
                        marquee_offset = 0 
                        # Espera extra en el límite inicial para que se pueda leer
                        last_marquee_time = current_time + 1000
            
            draw_menu()
            handle_menu_input()
        
        elif current_state > STATE_MENU:
            # --- LÓGICA DE CARGA PEREZOSA (LAZY LOADING) ---
            fx_file = menu_files[current_state - 1]
            
            try:
                if fx_file == "reset":
                    machine.reset()

                print(f"Cargando {fx_file}. RAM libre antes: {gc.mem_free()}")
                effect_module = __import__(fx_file)
                #effect_module = __import__('app.' + fx_file, fromlist=[''])
                
                if fx_file == "listar":
                    effect_module.run(oled, up_btn, down_btn, select_btn, back_btn, OLED_WIDTH, OLED_HEIGHT, utime, math, random, framebuf)
                elif fx_file == "grabarom":
                    effect_module.run(oled, back_btn, select_btn, OLED_WIDTH, OLED_HEIGHT, utime, math, random, framebuf)
                else:
                    effect_module.run(oled, back_btn, OLED_WIDTH, OLED_HEIGHT, utime, math, random, framebuf)
                
            except KeyboardInterrupt:
                # 🔑 Capturamos la señal del servidor y volvemos al menú
                print("Regresando al menú principal...")
                current_state = STATE_MENU 
                # Aquí puedes añadir un pequeño delay para asegurar la liberación del puerto antes de
                # que el bucle principal de la aplicación se repita si es necesario.
                utime.sleep_ms(200) # (Solo si es absolutamente necesario)
                
            except Exception as e:
                oled.fill(0)
                oled.text(f"Error FX: {fx_file}", 0, 0)
                oled.text(str(e), 0, 10)
                oled.show()
                utime.sleep(2)
                print(f"Error al ejecutar {fx_file}: {e}")
            
            finally:
                oled.fill(0)
                oled.text("Liberando RAM...", 0, 0)
                oled.show()
                

                config = cfg.carga_config()
                if config["lastrom"]:
                    if(len(menu_items) > 3):
                        menu_items[0] = "Grabar:" + config["lastrom"]
                    else:
                        menu_items.insert(0, "Grabar:" + config["lastrom"])

                
                # Liberación explícita de memoria
                if fx_file in sys.modules:
                    del sys.modules[fx_file] # Desreferencia el módulo del sistema
                del effect_module # Elimina la referencia local
                
                gc.collect() # Ejecuta el recolector de basura
                print(f"RAM libre después de GC: {gc.mem_free()}")
                
                current_state = STATE_MENU
                marquee_offset = 0 # Reiniciar la marquesina al volver al menú
                marquee_direction = 1 # Reiniciar la dirección
                last_marquee_time = utime.ticks_ms()
                
        #utime.sleep_ms(100)
else:
    print("No se pudo inicializar el display OLED.")
    while True:
        utime.sleep(1)