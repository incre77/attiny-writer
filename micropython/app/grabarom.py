from attiny import *


def run(oled, back_btn, select_btn, w, h, utime, math, random, framebuf):
    should_run = True 
    while should_run:
        
        # --- Lógica de Grabación (El cuerpo de tu código original) ---
        config = cfg.carga_config()
        oled.fill(0)
        
        oled.text("Grabando", 0, 1, 1)
        oled.text(config["lastrom"], 0, 9, 1)
        
        result = flashea_attiny("/roms/"+config["lastrom"],oled)
        
        if result:
            oled.fill(0)
            mostrar_texto_multilinea(oled, config["lastrom"], 0, 17, 1)
            oled.text("ha sido grabada", 0, 35, 1)
                         
            oled.text("3-Repite 4-Salir", 0, 55, 1)
        else:
            oled.fill(0)
            oled.text("Error Grabando:", 0, 20, 1)
            oled.text("No hay chip", 0, 30, 1)
            oled.text("3-Repite 4-Salir", 0, 55, 1)

        
        oled.show()
        # -------------------------------------------------------------
        
        # 2. Bucle de Espera de Botón
        # Espera a que se pulse un botón antes de continuar o salir
        while back_btn.value() != 0 and select_btn.value() != 0:
            utime.sleep_ms(50) # Espera pequeña para ahorrar CPU
            pass
            
        # 3. Lógica de Salida/Reinicio
        if back_btn.value() == 0:
            # El botón BACK se pulsó: sale de la función, terminando el bucle 'while should_run'
            while back_btn.value() == 0:
                utime.sleep_ms(50)
            should_run = False
            
        elif select_btn.value() == 0:
            # El botón SELECT se pulsó: el bucle 'while should_run' se repite, iniciando la grabación de nuevo
            oled.fill(0)
            oled.text("Reiniciando...", 0, 20, 1)
            oled.show()
            # Esperar a que el botón se suelte para evitar la doble pulsación rápida
            while select_btn.value() == 0:
                utime.sleep_ms(50) 
            # El bucle 'should_run' se repite (go back to step 1)

    # Limpieza final al salir de la función
    oled.fill(0)
    oled.show()
    
    
def flashea_attiny(filepath,oled):
    global hex_file_content
    
    with open(filepath, 'r') as f:
        hex_file_content = f.read()
    init_isp()
    print("Starting ATtiny13 programming with 9.6 MHz clock configuration...")
    if program_flash(hex_file_content,oled):
        print("ATtiny13 programming + verification successful!")
        print("Chip is now configured to run at 9.6 MHz internal clock.")
        return True
    else:
        print("ATtiny13 programming failed or verification failed.")
        return False
