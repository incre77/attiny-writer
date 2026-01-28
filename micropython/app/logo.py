import framebuf, utime

FONT_4X6_DATA = bytearray([
    # Metadatos de la fuente
    4, # 0: Ancho de los caracteres (W)
    6, # 1: Alto de los caracteres (H)
    # 1. Espacio Tradicional (Glifo en índice 2)
    0x00, 0x00, 0x00, 0x00, 
    # 2. █ Bloque completo (Glifo en índice 6)
    0x3F, 0x3F, 0x3F, 0x3F, 
    # 3. ▀ Medio bloque superior (Glifo en índice 10)
    0x38, 0x38, 0x38, 0x38, 
    # 4. ▄ Medio bloque inferior (Glifo en índice 14)
    0x07, 0x07, 0x07, 0x07, 
    # 5. ░ Sombreado ligero (Glifo en índice 18)
    0x2A, 0x15, 0x2A, 0x15, 
])

CHAR_MAP = {
    ord(' '):  0, # Espacio tradicional
    ord('█'): 1,
    ord('▀'): 3,
    ord('▄'): 2,
    ord('░'): 4,
}

# Constantes de la Fuente
FONT_WIDTH = FONT_4X6_DATA[0]
FONT_HEIGHT = FONT_4X6_DATA[1]
BYTES_PER_GLYPH = FONT_WIDTH
HEADER_SIZE = 2 # Ancho + Alto

def run(oled):
    
    for i in range(4):
        x,y = 6,17
        draw_text_custom(oled, "█▀█░▀█▀░▀█▀░▀█▀░█▀█░█░█", x, y)
        y += 6
        draw_text_custom(oled, "█▀█░░█░░░█░░░█░░█░█░░█░", x, y)
        y += 6
        draw_text_custom(oled, "▀░▀░░▀░░░▀░░▀▀▀░▀░▀░░▀░", x, y)
        
        y += 8
        draw_text_custom(oled, "█░█░█▀▄░▀█▀░▀█▀░█▀▀░█▀▄", x,y)
        y += 6
        draw_text_custom(oled, "█▄█░█▀▄░░█░░░█░░█▀▀░█▀▄", x, y)
        y += 6
        draw_text_custom(oled, "▀░▀░▀░▀░▀▀▀░░▀░░▀▀▀░▀░▀", x, y)
        
        y = 17
        draw_text_custom(oled, "█▀█ ▀█▀ ▀█▀ ▀█▀ █▀█ █ █", x, y)
        y += 6
        draw_text_custom(oled, "█▀█  █   █   █  █ █  █ ", x, y)
        y += 6
        draw_text_custom(oled, "▀ ▀  ▀   ▀  ▀▀▀ ▀ ▀  ▀ ", x, y)
        
        y += 8
        draw_text_custom(oled, "█ █ █▀▄ ▀█▀ ▀█▀ █▀▀ █▀▄", x,y)
        y += 6
        draw_text_custom(oled, "█▄█ █▀▄  █   █  █▀▀ █▀▄", x, y)
        y += 6
        draw_text_custom(oled, "▀ ▀ ▀ ▀ ▀▀▀  ▀  ▀▀▀ ▀ ▀", x, y)
        
    utime.sleep_ms(2000)

def draw_text_custom(display, text, start_x, start_y):
    """
    Imprime una cadena en la pantalla usando la fuente de mapa de bits personalizada,
    borrando el área del glifo antes de dibujarlo.
    
    :param display: Objeto de visualización (ej: SSD1306)
    :param text: La cadena a imprimir (ej: "░█▀█...")
    :param start_x: Coordenada X inicial
    :param start_y: Coordenada Y inicial
    """
    current_x = start_x
    
    for char in text:
        char_code = ord(char)
        
        # 1. Borrar el área del glifo actual (incluyendo el espacio de separación)
        # Borra un rectángulo de (FONT_WIDTH + 1) de ancho y FONT_HEIGHT de alto.
        # Esto asegura que el área del glifo y el píxel de separación a la derecha se limpien.
        try:
            display.fill_rect(current_x, start_y, FONT_WIDTH + 1, FONT_HEIGHT, 0)
        except AttributeError:
            # Manejar el caso si 'fill_rect' no existe (ej. si solo existe 'fill')
            pass
        
        # Comprobar si el carácter está mapeado (si es un glifo real)
        if char_code not in CHAR_MAP:
            # Si el carácter no está en la fuente, simplemente avanza
            current_x += FONT_WIDTH + 1
            continue

        # 2. Calcular la posición de inicio del glifo en FONT_4X6_DATA
        # Nota: Asume que FONT_WIDTH, FONT_HEIGHT, CHAR_MAP, etc., están definidos globalmente.
        glyph_map_index = CHAR_MAP[char_code]
        data_start = glyph_map_index * BYTES_PER_GLYPH + HEADER_SIZE
        
        # 3. Recorrer y pintar las 4 columnas del glifo
        for col in range(FONT_WIDTH):
            if current_x + col >= 128:
                break # Salir si está fuera del límite X
                
            # Obtiene el byte de la columna (que tiene 6 bits de datos de píxel)
            col_byte = FONT_4X6_DATA[data_start + col]
            
            # Recorre los 6 píxeles de la columna
            for row in range(FONT_HEIGHT):
                if start_y + row >= 64:
                    break # Salir si está fuera del límite Y
                    
                # El píxel se pinta (color 1) si el bit 'row' está en 1
                if (col_byte >> row) & 0x01:
                    display.pixel(current_x + col, start_y + row, 1)
        
        # 4. Mover la posición X para el siguiente carácter
        current_x += FONT_WIDTH + 1 
        
    display.show() # Actualiza la pantalla para mostrar los cambios