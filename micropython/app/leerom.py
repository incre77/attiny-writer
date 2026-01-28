from attiny import *

def run(oled, back_btn, OLED_WIDTH, OLED_HEIGHT, utime, math, random, framebuf):
    """
    Función de alto nivel para leer la ROM del chip y guardarla en un archivo Intel HEX.
    """
    filename=None
    
    # 1. Comandos de Inicialización en OLED
    oled.fill(0)
    oled.text("Leyendo rom", 0, 1, 1)
    oled.text("Iniciando ISP", 0, 9, 1)
    oled.show()  
    
    # 2. Leer la ROM
    rom_data = read_rom_to_hex(oled, pinta_barra)

    if rom_data is None:
        # Si falla al leer (ej. start_programming falla)
        oled.fill(0)
        oled.text("❌ LECTURA FALLIDA", 0, 1, 1)
        oled.text("Verificar chip/fuses.", 0, 15, 1)
        oled.show()
        utime.sleep(2)
        return False
        
    # 3. Generar el nombre del archivo
    if filename is None:
        t = utime.localtime()
        
        # Formato: YYMMDD_HHMMSS
        timestamp = "{:02}{:02}{:02}_{:02}{:02}{:02}".format(t[0]%100, t[1], t[2], t[3], t[4], t[5])
        filename = f"/roms/{timestamp}.hex"
        
    # 4. Guardar en Archivo
    try:
        # Asegúrate de que el directorio /roms exista
        with open(filename, 'w') as f:
            f.write(rom_data)
        
        # 5. Mostrar éxito
        oled.fill(0)
        oled.text("ROM GUARDADA", 0, 1, 1)
        mostrar_texto_multilinea(oled,filename, 0, 17, 1)
        oled.text("4-Salir", 0, 55, 1)
        oled.show()
        
        while back_btn.value() != 0:
            utime.sleep_ms(50) # Espera pequeña para ahorrar CPU
            pass
        
        return True
        
    except OSError as e:
        # 5. Mostrar fallo de escritura
        oled.fill(0)
        oled.text("❌ ERROR ESCRITURA", 0, 1, 1)
        oled.text(str(e), 0, 15, 1)
        oled.show()
        utime.sleep(2)
        print(f"❌ Error de escritura de archivo: {e}")
        return False
        
    # 6. Bucle de espera (solo espera a que se suelte el botón BACK)
    while back_btn.value() != 0:
        pass