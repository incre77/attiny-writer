import cfg
import machine
import time
import utime
import uos
import sys
from comun import *


# --- Pin Definitions ---
SCK_PIN   = 4
MISO_PIN  = 5
MOSI_PIN  = 6
RESET_PIN = 7

l_graba = 0

# --- ISP Timing ---
SCK_DELAY_US = 1    #50   # ~100 kHz SCK

BYTES_PER_RECORD = 16 # Bytes por línea para el archivo HEX (Intel HEX)

# ATtiny13 parameters - CORRECTED VALUES
ATTINY13_SIGNATURE = [0x1E, 0x90, 0x07] # 30, 144, 7
FLASH_SIZE = 1024  # 1K bytes total
ATTINY13_PAGE_SIZE = 32   # ATtiny13 has 16 words = 32 bytes per page
ATTINY13_WORDS_PER_PAGE = 16  # 16 words per page
ATTINY13_TOTAL_PAGES = 32     # 32 pages total (32 * 32 = 1024 bytes)

# --- ATtiny13 Fuse Bit Settings for 9.6 MHz internal clock ---
# SAFE FUSE SETTINGS - CAREFULLY VERIFIED TO AVOID BRICKING THE CHIP!

# Low Fuse: 0x7A for 9.6 MHz (default factory is 0x6A for 1.2MHz)
# Bit 7: CKDIV8  = 0 (disable clock division by 8 - gives full 9.6MHz)
# Bit 6: CKOUT   = 1 (disable clock output on PB4)
# Bit 5-4: SUT   = 01 (14CK + 64ms startup time - safe default)
# Bit 3-0: CKSEL = 1010 (internal RC oscillator - 9.6MHz when CKDIV8=0)
ATTINY13_LOW_FUSE_9_6MHZ = 0x7A

# High Fuse: 0xFF (SAFE DEFAULT - keeps all dangerous bits disabled)
# Bit 7: RSTDISBL = 1 (RESET PIN ENABLED - CRITICAL FOR ISP!)
# Bit 6: BODLEVEL = 1 (brown-out detection disabled)
# Bit 5: BODEN    = 1 (brown-out detection disabled)
# Bit 4: -        = 1 (reserved, keep as 1)
# Bit 3: -        = 1 (reserved, keep as 1)
# Bit 2: -        = 1 (reserved, keep as 1)
# Bit 1: SPIEN    = 1 (SPI PROGRAMMING ENABLED - CRITICAL FOR ISP!)
# Bit 0: -        = 1 (reserved, keep as 1)
ATTINY13_HIGH_FUSE = 0xFF

# Factory default fuses for reference and recovery
ATTINY13_FACTORY_LOW_FUSE = 0x6A   # 1.2MHz (9.6MHz/8)
ATTINY13_FACTORY_HIGH_FUSE = 0xFF  # All safe defaults

# --- Initialize Pins ---
sck   = machine.Pin(SCK_PIN, machine.Pin.OUT)
mosi  = machine.Pin(MOSI_PIN, machine.Pin.OUT)
miso  = machine.Pin(MISO_PIN, machine.Pin.IN, machine.Pin.PULL_UP)
reset = machine.Pin(RESET_PIN, machine.Pin.OUT)

# ------------------------
# Low-level helpers
# ------------------------

def transfer_byte(byte):
    read_val = 0
    for i in range(8):
        mosi.value((byte >> (7 - i)) & 0x01)
        time.sleep_us(SCK_DELAY_US) # Necesario para SCK LOW time
        sck.value(1) # Ascendente
        read_val = (read_val << 1) | miso.value()
        time.sleep_us(SCK_DELAY_US) # Necesario para SCK HIGH time
        sck.value(0) # Descendente
    return read_val

def send_cmd(a, b, c, d):
    r1 = transfer_byte(a)
    r2 = transfer_byte(b)
    r3 = transfer_byte(c)
    r4 = transfer_byte(d)
    #print(f"CMD [{a:02X} {b:02X} {c:02X} {d:02X}] -> RESP [{r1:02X} {r2:02X} {r3:02X} {r4:02X}]")
    return r3, r4

def send_cmd_r3(a, b, c, d):
    return send_cmd(a, b, c, d)[0]

def send_cmd_r4(a, b, c, d):
    return send_cmd(a, b, c, d)[1]

# ------------------------
# ISP interface
# ------------------------

def init_isp():
    sck.value(0)
    mosi.value(0)
    reset.value(1)
    time.sleep_ms(10)

def start_programming():
    reset.value(0)
    time.sleep_ms(20)  # Give chip time to enter reset
    r3 = send_cmd_r3(0xAC, 0x53, 0x00, 0x00)
    if r3 == 0x53:
        print("Programming mode entered successfully.")
        return True
    else:
        print(f"Failed to enter programming mode (got 0x{r3:02X}).")
        return False

def end_programming():
    reset.value(1)
    time.sleep_ms(1)

# ------------------------
# Fuse bit operations
# ------------------------

def read_low_fuse():
    """Read low fuse byte"""
    return send_cmd_r4(0x50, 0x00, 0x00, 0x00)

def read_high_fuse():
    """Read high fuse byte"""
    return send_cmd_r4(0x58, 0x08, 0x00, 0x00)

def read_lock_bits():
    """Read lock bits"""
    return send_cmd_r4(0x58, 0x00, 0x00, 0x00)

def write_low_fuse(fuse_value):
    """Write low fuse byte"""
    print(f"Writing low fuse: 0x{fuse_value:02X}")
    send_cmd_r4(0xAC, 0xA0, 0x00, fuse_value)
    time.sleep_ms(50)  # Wait for fuse write to complete

def write_high_fuse(fuse_value):
    """Write high fuse byte"""
    print(f"Writing high fuse: 0x{fuse_value:02X}")
    send_cmd_r4(0xAC, 0xA8, 0x00, fuse_value)
    time.sleep_ms(50)  # Wait for fuse write to complete

def program_fuses_for_9_6mhz():
    """Program fuses for 9.6 MHz internal clock - SAFETY CHECKED"""
    print("\n=== Programming Fuses for 9.6 MHz Internal Clock ===")
    print("⚠️  SAFETY: Fuse settings verified to keep RESET and SPI programming enabled!")

    # Read current fuse settings
    low_fuse = read_low_fuse()
    high_fuse = read_high_fuse()
    print(f"Current Low Fuse:  0x{low_fuse:02X}")
    print(f"Current High Fuse: 0x{high_fuse:02X}")

    # CRITICAL SAFETY CHECK: Never allow dangerous high fuse values!
    if ATTINY13_HIGH_FUSE != 0xFF:
        print("❌ SAFETY ERROR: High fuse setting is not 0xFF (safe default)")
        print("❌ This could disable RESET pin or SPI programming - ABORTING!")
        return False

    # Additional safety check on the low fuse bits that matter for clock
    expected_cksel = ATTINY13_LOW_FUSE_9_6MHZ & 0x0F  # Should be 0x0A for internal RC
    if expected_cksel != 0x0A:
        print(f"❌ SAFETY WARNING: CKSEL bits are 0x{expected_cksel:X}, expected 0x0A for internal RC")
        print("❌ This may not be a valid internal RC setting - ABORTING!")
        return False

    # Write new fuse settings if different
    if low_fuse != ATTINY13_LOW_FUSE_9_6MHZ:
        print(f"Setting Low Fuse to 0x{ATTINY13_LOW_FUSE_9_6MHZ:02X} for 9.6 MHz internal clock...")
        write_low_fuse(ATTINY13_LOW_FUSE_9_6MHZ)

        # Verify the write
        new_low_fuse = read_low_fuse()
        if new_low_fuse == ATTINY13_LOW_FUSE_9_6MHZ:
            print(f"✅ Low fuse successfully set to 0x{new_low_fuse:02X}")
        else:
            print(f"❌ Low fuse write failed! Got 0x{new_low_fuse:02X}, expected 0x{ATTINY13_LOW_FUSE_9_6MHZ:02X}")
            return False
    else:
        print("Low fuse already set correctly for 9.6 MHz")

    # For high fuse, we should NOT change it from 0xFF (safe default)
    if high_fuse != ATTINY13_HIGH_FUSE:
        print(f"⚠️  Current High Fuse (0x{high_fuse:02X}) differs from safe default (0x{ATTINY13_HIGH_FUSE:02X})")
        if high_fuse == 0xFE:  # 0xFE would disable RSTDISBL - VERY DANGEROUS!
            print("❌ CRITICAL DANGER: High fuse 0xFE would disable RESET pin!")
            print("❌ This would make the chip unprogrammable via ISP - ABORTING!")
            return False
        elif high_fuse & 0x02 == 0:  # SPIEN bit cleared - also dangerous
            print("❌ CRITICAL DANGER: SPIEN bit is disabled!")
            print("❌ This would make the chip unprogrammable via SPI - ABORTING!")
            return False
        else:
            print("ℹ️  High fuse looks safe, keeping current value rather than changing it")
    else:
        print("High fuse already set to safe default (0xFF)")

    print("=== Fuse Programming Complete ===\n")
    return True

def display_fuse_settings():
    """Display current fuse settings with interpretation"""
    print("\n=== Current Fuse Settings ===")
    low_fuse = read_low_fuse()
    high_fuse = read_high_fuse()
    lock_bits = read_lock_bits()

    print(f"Low Fuse:  0x{low_fuse:02X}")
    print(f"High Fuse: 0x{high_fuse:02X}")
    print(f"Lock Bits: 0x{lock_bits:02X}")

    # Interpret low fuse bits
    cksel = low_fuse & 0x0F
    sut = (low_fuse >> 4) & 0x03
    ckout = (low_fuse >> 6) & 0x01
    ckdiv8 = (low_fuse >> 7) & 0x01

    # Interpret high fuse bits (safety-critical!)
    spien = (high_fuse >> 1) & 0x01
    rstdisbl = (high_fuse >> 7) & 0x01

    print(f"\nLow Fuse Interpretation:")
    print(f"  CKSEL[3:0]: 0x{cksel:X} ", end="")
    if cksel == 0x0A:
        print("(Internal RC oscillator - 9.6MHz calibrated)")
    elif cksel == 0x02:
        print("(Internal RC oscillator - 4.8MHz)")
    elif cksel >= 0x08 and cksel != 0x0A:
        print("(External clock/crystal)")
    else:
        print("(other/unknown clock source)")

    print(f"  SUT[1:0]:   0x{sut:X} (startup time)")
    print(f"  CKOUT:      {ckout} ({'clock output enabled on PB4' if ckout == 0 else 'no clock output'})")
    print(f"  CKDIV8:     {ckdiv8} ({'clock divided by 8' if ckdiv8 == 0 else 'no clock division'})")

    print(f"\nHigh Fuse Interpretation (SAFETY CRITICAL):")
    print(f"  RSTDISBL:   {rstdisbl} ({'RESET PIN DISABLED - DANGER!' if rstdisbl == 0 else 'RESET pin enabled ✅'})")
    print(f"  SPIEN:      {spien} ({'SPI programming disabled - DANGER!' if spien == 0 else 'SPI programming enabled ✅'})")

    if cksel == 0x0A and ckdiv8 == 1:
        expected_freq = "9.6 MHz"
    elif cksel == 0x0A and ckdiv8 == 0:
        expected_freq = "1.2 MHz (9.6MHz ÷ 8 - factory default)"
    elif cksel == 0x02 and ckdiv8 == 1:
        expected_freq = "4.8 MHz"
    elif cksel == 0x02 and ckdiv8 == 0:
        expected_freq = "0.6 MHz (4.8MHz ÷ 8)"
    else:
        expected_freq = "unknown"

    print(f"  → Expected CPU frequency: {expected_freq}")

    # Safety warnings
    if rstdisbl == 0:
        print("⚠️  ⚠️  ⚠️  CRITICAL WARNING: RESET is disabled! Chip may be unrecoverable via ISP!")
    if spien == 0:
        print("⚠️  ⚠️  ⚠️  CRITICAL WARNING: SPI programming disabled! Chip may be unrecoverable!")
    print("================================\n")

# ------------------------
# High-level operations
# ------------------------

def chip_erase():
    print("Performing chip erase...")
    send_cmd_r4(0xAC, 0x80, 0x00, 0x00)
    time.sleep_ms(100)  # Wait for erase to complete
    print("Chip erase complete.")

def read_signature_bytes():
    sig = []
    for addr in [0x00, 0x01, 0x02]:
        val = send_cmd_r4(0x30, 0x00, addr, 0x00)
        sig.append(val)
    return sig

def program_flash_page(page_address, data_bytes):
    """Write a page to ATtiny13 flash. ATtiny13 has 16 words (32 bytes) per page."""
    global l_graba
    # Load page buffer - ATtiny13 has 16 words per page
    
    print(range(ATTINY13_WORDS_PER_PAGE))
    
    for word_index in range(ATTINY13_WORDS_PER_PAGE):
        
        byte_index = word_index * 2

        # Get low and high bytes
        if byte_index < len(data_bytes):
            low_byte = data_bytes[byte_index]
        else:
            low_byte = 0xFF

        if byte_index + 1 < len(data_bytes):
            high_byte = data_bytes[byte_index + 1]
        else:
            high_byte = 0xFF
            
        #l_graba.value(0)
        # Load program memory page (low byte)
        send_cmd_r4(0x40, 0x00, word_index, low_byte)
        # Load program memory page (high byte)
        #l_graba.value(1)
        send_cmd_r4(0x48, 0x00, word_index, high_byte)

    # Write program memory page
    # The page address should be the word address of the page start
    page_word_addr = page_address // 2
    high_addr = (page_word_addr >> 8) & 0xFF
    low_addr = page_word_addr & 0xFF

    print(f"Writing page at word address 0x{page_word_addr:04X} (byte addr 0x{page_address:04X})")
    send_cmd_r4(0x4C, high_addr, low_addr, 0x00)
    time.sleep_ms(50)  # Wait for page write to complete

def parse_hex_file(hex_content):
    data = {}
    for line in hex_content.strip().splitlines():
        if not line.startswith(':'):
            continue
        byte_count = int(line[1:3], 16)
        addr       = int(line[3:7], 16)
        record_type= int(line[7:9], 16)
        if record_type == 0:  # Data record
            for i in range(byte_count):
                data[addr + i] = int(line[9 + i*2: 11 + i*2], 16)
        elif record_type == 1:  # EOF
            break
    return data

def read_flash_byte(addr):
    word_addr = addr >> 1
    high_low  = addr & 0x01
    cmd = 0x28 if high_low else 0x20
    return send_cmd_r4(cmd, (word_addr >> 8) & 0xFF, word_addr & 0xFF, 0x00)

def verify_flash(parsed_data,oled):
    print("Verifying flash contents...")
    errors = 0
    i =  0
    total = len(list(parsed_data.keys()))
    for addr, expected in parsed_data.items():
        i+=1
        actual = read_flash_byte(addr)
        
        percent = i*100/total
        pinta_barra(oled,percent,False)
        
        if actual != expected:
            print(f"Mismatch at 0x{addr:04X}: expected 0x{expected:02X}, got 0x{actual:02X}")
            errors += 1
            if errors >= 20:  # Show more errors for debugging
                print(f"... stopping after 20 errors")
                break
    if errors == 0:
        print("Verification PASSED ✅")
        return True
    else:
        print(f"Verification FAILED ❌ with {errors}+ errors")
        return False
    
def read_flash_word(word_addr):
    """Lee una palabra (low byte, high byte) de la memoria flash."""
    
    high_addr = (word_addr >> 8) & 0xFF
    low_addr = word_addr & 0xFF
    
    # Comando 0x20 para leer el Byte Bajo (Low Byte)
    low_byte = send_cmd_r4(0x20, high_addr, low_addr, 0x00)
    
    # Comando 0x28 para leer el Byte Alto (High Byte)
    high_byte = send_cmd_r4(0x28, high_addr, low_addr, 0x00)
    
    return low_byte, high_byte
    
    
def verify_flash(parsed_data, oled):
    """
    Verifica el contenido de la memoria flash del ATtiny13.
    Optimiza la velocidad al:
    1. Iterar solo sobre las direcciones que contienen datos (basado en parsed_data).
    2. Actualizar la barra de progreso solo una vez por página verificada.
    """
    print("Verificando flash contents (Optimizado por alcance y velocidad)...")
    errors = 0
    
    byte_addresses = sorted(parsed_data.keys())
    
    if not byte_addresses:
        print("No hay datos para verificar.")
        pinta_barra(oled, 100, False)
        return True

    # 1. Preparación para la iteración y el progreso
    
    # word_addr = byte_addr // 2. Genera una lista de direcciones de palabra únicas y ordenadas a leer.
    word_addresses_to_verify = sorted(list(set([addr // 2 for addr in byte_addresses])))
    
    # Calcular las páginas totales y el contador de progreso para la barra
    pages_to_verify_set = set([addr // ATTINY13_PAGE_SIZE for addr in byte_addresses])
    TOTAL_PAGES_TO_VERIFY = len(pages_to_verify_set)
    pages_verified_count = 0
    last_page_start = -1 
    
    # 2. Bucle de Verificación (Itera solo sobre las palabras necesarias)
    for word_addr in word_addresses_to_verify:
        
        # Calcular direcciones de byte
        byte_addr_low = word_addr * 2
        byte_addr_high = byte_addr_low + 1
        
        # Leer la palabra completa desde el chip
        low_byte_actual, high_byte_actual = read_flash_word(word_addr)
        
        # 3. Comparación de los bytes
        
        # Verificar el byte bajo
        if byte_addr_low in parsed_data:
            expected = parsed_data[byte_addr_low]
            actual = low_byte_actual
            
            if actual != expected:
                print(f"Mismatch at 0x{byte_addr_low:04X}: expected 0x{expected:02X}, got 0x{actual:02X}")
                errors += 1

        # Verificar el byte alto
        if byte_addr_high in parsed_data:
            expected = parsed_data[byte_addr_high]
            actual = high_byte_actual
            
            if actual != expected:
                print(f"Mismatch at 0x{byte_addr_high:04X}: expected 0x{expected:02X}, got 0x{actual:02X}")
                errors += 1
                
        # 4. Lógica de Parada Rápida por Error
        if errors > 0 and errors % 20 == 0:
            print(f"... stopping after {errors} errors")
            pinta_barra(oled, 100, False)
            return False

        # 5. Lógica de Barra de Progreso (Actualizar solo si se verifica una página nueva)
        current_page_start = byte_addr_low - (byte_addr_low % ATTINY13_PAGE_SIZE)
        
        # Comprueba si el inicio de la página es diferente al último procesado
        if current_page_start != last_page_start:
            last_page_start = current_page_start
            pages_verified_count += 1
            
            # Actualiza el progreso con base en las páginas verificadas
            percent = pages_verified_count * 100 / TOTAL_PAGES_TO_VERIFY
            pinta_barra(oled, percent, "Verificando", False)
        
    pinta_barra(oled, 100, "Verificando",False) # Asegura el 100% final

    # 6. Resultado Final
    if errors == 0:
        print("Verification PASSED ✅")
        return True
    else:
        print(f"Verification FAILED ❌ with {errors} errors")
        return False
    

def program_flash(hex_content, oled):
    """
    Programa la memoria flash del ATtiny13 basándose en el contenido del archivo HEX,
    optimizando el proceso al iterar solo sobre las páginas con datos.
    """
    
    # 1. Parsing y Comprobación Inicial
    parsed_data = parse_hex_file(hex_content)
    if not parsed_data:
        print("No valid data found in hex file.")
        return False

    min_addr = min(parsed_data.keys())
    max_addr = max(parsed_data.keys())
    
    print(f"Parsed {len(parsed_data)} bytes from hex file")
    print(f"Address range: 0x{min_addr:04X} to 0x{max_addr:04X}")

    # 2. Entrada al Modo de Programación
    if not start_programming():
        return False
    
    # ----------------------------------------------------
    # Usa try/finally para asegurar que end_programming() siempre se llama
    try:
        # 3. Comprobación de la Firma
        sig = read_signature_bytes()
        print(f"Read signature: {sig} (hex: {[hex(x) for x in sig]})")

        if sig != ATTINY13_SIGNATURE:
            print("Error: Detected chip is not an ATtiny13!")
            print(f"Expected: {[hex(x) for x in ATTINY13_SIGNATURE]}")
            print(f"Got: {sig} ({[hex(x) for x in sig]})")
            return False # Sale, y finally cierra la programación

        # 4. Programación de Fuses
        display_fuse_settings() # Mostrar antes
        
        if not program_fuses_for_9_6mhz():
            print("Failed to program fuses!")
            return False

        display_fuse_settings() # Mostrar después

        # 5. Borrado del Chip
        chip_erase()

        # 6. Cálculo del Rango de Páginas Optimizado (Basado en datos)
        
        # Calcular el inicio de la primera página con datos
        start_page_addr = min_addr - (min_addr % ATTINY13_PAGE_SIZE)
        
        # Calcular el final de la última página con datos
        # Esto nos da el byte que sigue al último byte de la última página
        bytes_to_end_page = ATTINY13_PAGE_SIZE - 1 - (max_addr % ATTINY13_PAGE_SIZE)
        end_page_addr = max_addr + bytes_to_end_page + 1 
        
        # Asegurarse de no exceder los límites físicos del chip
        if end_page_addr > FLASH_SIZE:
            end_page_addr = FLASH_SIZE
        
        # Pre-calcular el total de páginas a flashear para la barra de progreso
        TOTAL_PAGES_TO_FLASH = (end_page_addr - start_page_addr) // ATTINY13_PAGE_SIZE
        page_count = 0
        
        oled.text(str(len(parsed_data)) + " Bytes", 0, 55, 1)
        
        # 7. Bucle de Programación por Páginas (Optimizado)
        for page_start in range(start_page_addr, end_page_addr, ATTINY13_PAGE_SIZE):
            
            # Inicializar la página con 0xFF (vacío) - usar bytearray es más eficiente
            page_data = bytearray([0xFF] * ATTINY13_PAGE_SIZE)
            
            # Recorrer los bytes de la página para insertar los datos del HEX
            for i in range(ATTINY13_PAGE_SIZE):
                byte_addr = page_start + i
                
                if byte_addr in parsed_data:
                    page_data[i] = parsed_data[byte_addr]
                    
            print(f"Programming page {page_count} at address 0x{page_start:04X}...")
            program_flash_page(page_start, page_data)
                
            # Actualizar la barra de progreso
            page_count += 1
            percent = page_count * 100 / TOTAL_PAGES_TO_FLASH
            pinta_barra(oled, percent,"Grabando   ",True)

        #pinta_barra(oled, 100, "Grabando   ", True) # Asegura el 100% en la pantalla    
        print("Flash programming complete.")
        
        # 8. Verificación
        ok = verify_flash(parsed_data, oled)
        return ok
        
    finally:
        # Esto garantiza que el modo de programación SPI se cierre
        # incluso si ocurre un error en el medio.
        end_programming()

# -------------------------------------------------------------------
# Lectura y Formato HEX
# -------------------------------------------------------------------

def create_hex_record(address, data):
    """Genera una línea (registro) en formato Intel HEX."""
    length = len(data)
    checksum = length + (address >> 8) + (address & 0xFF) + 0x00  
    hex_data = ""
    
    for byte in data:
        hex_data += f"{byte:02X}"
        checksum += byte
        
    checksum = (~checksum + 1) & 0xFF
    
    # Formato: :LLAAAATTDD...DCC
    return f":{length:02X}{address:04X}00{hex_data}{checksum:02X}\n"
# Definir una constante para el límite de bytes vacíos consecutivos (Ya no es necesario, pero se mantiene la estructura)
# BLANK_SECTION_LIMIT = 128 

def read_rom_to_hex(oled, pinta_barra):
    """
    Lee TODA la memoria flash del chip, identifica el rango de datos, 
    y devuelve el contenido como HEX ACORTADO hasta la última dirección con datos.
    """
    print("\nIniciando lectura de la ROM (DUMP) de la Flash completa...")
    
    init_isp()
    if not start_programming():
        print("❌ Error: No se pudo entrar en modo programación.")
        return None

    # Estructura temporal para guardar todas las líneas HEX generadas
    raw_hex_records = [] 
    
    total_bytes = FLASH_SIZE
    current_addr = 0
    last_data_addr = -1    # Inicializado a -1. Si sigue siendo -1, el chip estaba borrado.
    
    try:
        while current_addr < total_bytes:
            data_record = []
            start_addr_for_record = current_addr
            
            # Leemos BYTES_PER_RECORD bytes (8 palabras)
            words_to_read = BYTES_PER_RECORD // 2
            
            # --- Lógica de Lectura ---
            for word_index in range(words_to_read):
                if current_addr >= total_bytes:
                    break
                
                word_addr = current_addr // 2
                low_byte, high_byte = read_flash_word(word_addr)
                
                bytes_read = []
                bytes_read.append(low_byte)
                
                if current_addr + 1 < total_bytes:
                    bytes_read.append(high_byte)
                
                # --- Lógica de Rastreo de Datos ---
                for byte_value in bytes_read:
                    
                    if byte_value != 0xFF:
                        # Si el byte no está vacío, actualizamos la última dirección de datos significativa.
                        last_data_addr = current_addr
                        
                    data_record.append(byte_value)
                    current_addr += 1 

            # Generar y almacenar el registro HEX temporalmente
            if data_record:
                hex_line = create_hex_record(start_addr_for_record, data_record).strip()
                raw_hex_records.append(hex_line)
            
            # Actualizar la barra de progreso
            percent = current_addr * 100 / total_bytes
                                        
            pinta_barra(oled, percent, "Leyendo    ", False)
        
        # -------------------------------------------------------------------
        # Generación del Archivo HEX Final (Acortado)
        # -------------------------------------------------------------------
        final_hex_content = ""
        
        if last_data_addr == -1:
            print("El chip parece estar completamente vacío (0xFF).")
        else:
            # 1. Iterar sobre los registros brutos generados
            for line in raw_hex_records:
                # Extraer la dirección de inicio del registro y la cuenta de bytes
                addr = int(line[3:7], 16)
                byte_count = int(line[1:3], 16)
                
                # Criterio de inclusión: Si el registro termina ANTES o EXACTAMENTE 
                # en la última dirección de datos significativa.
                if addr <= last_data_addr and addr + byte_count > last_data_addr:
                    # Caso 1: El registro contiene last_data_addr
                    # Cortamos el registro para que termine justo después de last_data_addr.
                    bytes_to_keep = (last_data_addr - addr) + 1
                    
                    # Recalculamos el registro HEX
                    data_slice = [int(line[9 + i*2: 11 + i*2], 16) for i in range(bytes_to_keep)]
                    final_hex_content += create_hex_record(addr, data_slice).strip() + "\n"
                    
                    # Una vez que se incluye la última dirección de datos, salimos del bucle.
                    break 

                elif addr + byte_count <= last_data_addr:
                    # Caso 2: El registro está completamente antes de last_data_addr
                    # Incluimos la línea completa.
                    final_hex_content += line + "\n"
            
            print(f"Lectura de ROM completa. Archivo HEX acortado hasta 0x{last_data_addr:04X}.")
            
        # Escribir el registro final (End Of File: EOF)
        final_hex_content += ":00000001FF\n" 
        
        return final_hex_content
        
    except Exception as e:
        print(f"❌ Error durante la lectura de la ROM: {e}")
        return None
        
    finally:
        end_programming()
