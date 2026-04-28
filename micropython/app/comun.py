def mostrar_texto_multilinea(oled, texto, x, y, color):
    ANCHO_CARACTER = 8
    max_chars_por_linea = 128 // ANCHO_CARACTER
    linea1 = texto[:max_chars_por_linea]
    linea2 = texto[max_chars_por_linea:]
    ALTURA_LINEA = 9 
    oled.text(linea1, x, y, color)
    if linea2:
        oled.text(linea2, x, y + ALTURA_LINEA, color)
        
    
def pinta_barra(oled,p,txt,graba):
    x, y = 1, 20
    w, h = 126, 20
    #txt = "Grabando   " if graba else "Verificando"
    
    fill_w = int((p / 100) * (w - 2)) - 2
    if not graba:
        oled.fill_rect(x + 2, y + 2, fill_w, h - 4, 1)     
    else:
        mi_barra(oled,x + 2, y + 2, fill_w, h - 4)
        
    if p < 10:
        oled.rect(x, y, w, h, 1)
        oled.fill_rect(x, y + h , w, 15, 0) # Borrar la línea de texto anterior
        oled.text(f"{txt}  {round(p)}%", x, y + h + 2, 1)
    else:
        oled.fill_rect(90, y + h , 38, 15, 0) # Borrar la línea de texto anterior
        oled.text(f" {round(p)}%", 90, y + h + 2, 1)   
    
    oled.show()
    
def mi_barra(oled,x,y,w,h):
    for i in range(x, x + w):
        for j in range(y, y + h):
            if (i + j) % 2 == 0: # Si la suma de las coordenadas es par, enciende el píxel
                oled.pixel(i, j, 1) # 1 para encendido
            else:
                oled.pixel(i, j, 0) # 0 para apagado (o simplemente no dibujarlo si ya está apagado)
    oled.show() # Actualiza la pantalla para mostrar los cambios


