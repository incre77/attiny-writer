    const fileInput = document.getElementById('fileInput');
    const uploadButton = document.getElementById('uploadButton');
    const buttonText = document.getElementById('buttonText');
    const spinner = document.getElementById('spinner');
    const uploadMessageArea = document.getElementById('uploadMessageArea');
    const uploadMessageText = document.getElementById('uploadMessageText');
    
    const ssidInput = document.getElementById('ssidInput');
    const passwordInput = document.getElementById('passwordInput');
    const saveButton = document.getElementById('saveButton');
    const configMessageArea = document.getElementById('configMessageArea');
    const configMessageText = document.getElementById('configMessageText');
    
    const romWriteCard = document.getElementById('romWriteCard');
    const writeRomButton = document.getElementById('writeRomButton');
    const romMessageArea = document.getElementById('romMessageArea');
    const romMessageText = document.getElementById('romMessageText');
    
    const deleteButton = document.getElementById('deleteButton');
    
    // --- Constantes para colapsar ---
    const toggleConfigButton = document.getElementById('toggleConfigButton');
    const configContent = document.getElementById('configContent');

    // --- Constantes para Drag and Drop ---
    const dropArea = document.getElementById('dropArea');
    const fileNameDisplay = document.getElementById('fileNameDisplay');


    function setLoading(isLoading, button, defaultText) {
        if (button === uploadButton) {
            button.disabled = isLoading || fileInput.files.length === 0;
            spinner.classList.toggle('hidden', !isLoading);
            buttonText.textContent = isLoading ? 'Procesando...' : defaultText;
        }
        else if (button === saveButton) {
            alert("Se guardaran los cambios. Reconecta a la nueva red y recarga esta página")
        }
        else if (button === writeRomButton) {
            const textSpan = button.querySelector('span');
            button.disabled = isLoading;
            if (textSpan) {
                 textSpan.textContent = isLoading ? 'Procesando...' : defaultText;
            }
            return;
        }
        else {
            const textSpan = button.querySelector('span');
            button.disabled = isLoading;
            if (textSpan) {
                 textSpan.textContent = isLoading ? 'Procesando...' : defaultText;
            }
        }
        hideMessage(uploadMessageArea);
        hideMessage(configMessageArea);
        hideMessage(romMessageArea); 
    }

    function showMessage(areaElement, textElement, text, classes) {
        console.log(areaElement)
        console.log(textElement)
        console.log(text)
        areaElement.className = `message-area ${classes}`;
        areaElement.classList.remove('hidden');
        textElement.textContent = text;
    }
    
    function hideMessage(areaElement) {
        areaElement.classList.add('hidden');
    }
    
    function showElement(element) {
        element.classList.remove('hidden');
    }
    
    function hideElement(element) {
        element.classList.add('hidden');
        
    }

    // --- Funciones de Drag and Drop y manejo de archivos ---
    function handleFiles(files) {
        // La asignación directa sigue siendo la mejor práctica para inputs.
        fileInput.files = files; 

        const file = fileInput.files[0];
        if (file) {
            fileNameDisplay.textContent = `Archivo seleccionado: ${file.name}`;
            uploadButton.disabled = false;
            hideMessage(uploadMessageArea);
        } else {
            fileNameDisplay.textContent = 'Arrastra y suelta el archivo aquí o haz clic para seleccionar';
            uploadButton.disabled = true;
            hideElement(romWriteCard);
        }
    }

    // Eventos para el input file (por si se usa el clic en vez de drag)
    fileInput.addEventListener('change', () => {
        handleFiles(fileInput.files);
        hideElement(romWriteCard); 
    });

    // Eventos de Drag and Drop
    ['dragenter', 'dragover', 'dragleave', 'drop'].forEach(eventName => {
        dropArea.addEventListener(eventName, preventDefaults, false);
    });

    function preventDefaults(e) {
        e.preventDefault();
        e.stopPropagation();
    }

    ['dragenter', 'dragover'].forEach(eventName => {
        dropArea.addEventListener(eventName, highlight, false);
    });

    ['dragleave', 'drop'].forEach(eventName => {
        dropArea.addEventListener(eventName, unhighlight, false);
    });

    function highlight(e) {
        dropArea.classList.add('highlight');
    }

    function unhighlight(e) {
        dropArea.classList.remove('highlight');
    }

    dropArea.addEventListener('drop', handleDrop, false);

    function handleDrop(e) {
        // Asegúrate de que el navegador no limpie los datos antes de leerlos
        e.preventDefault(); 
        
        let dt = e.dataTransfer;
        let files;
        
        // Intenta usar DataTransfer.files primero (el estándar)
        if (dt.files && dt.files.length > 0) {
            files = dt.files;
        } else if (dt.items) {
            // Intenta construir el FileList desde dt.items
            const dataTransfer = new DataTransfer();
            for (let i = 0; i < dt.items.length; i++) {
                // Solo acepta archivos (kind 'file')
                if (dt.items[i].kind === 'file') {
                    const file = dt.items[i].getAsFile();
                    if (file) {
                        dataTransfer.items.add(file);
                    }
                }
            }
            files = dataTransfer.files;
        }
        
        if (!files || files.length === 0) {
            showMessage(uploadMessageArea, uploadMessageText, 'No se pudo leer el archivo. Intenta seleccionarlo haciendo clic.', 'msg-red');
            return;
        }

        // Limita a un archivo y llama a la función de manejo
        if (files.length > 1) {
            showMessage(uploadMessageArea, uploadMessageText, 'Solo puedes subir un archivo a la vez.', 'msg-yellow');
            handleFiles(new DataTransfer().files); 
        } else {
            handleFiles(files);
        }
        hideElement(romWriteCard); 
    }

    // El área de clic en el div debe activar el input file oculto
    dropArea.addEventListener('click', () => {
        fileInput.click();
    });
    // --- Fin de funciones de Drag and Drop ---


    uploadButton.addEventListener('click', async () => {
        const file = fileInput.files[0];
        if (!file) {
            showMessage(uploadMessageArea, uploadMessageText, 'Por favor, selecciona un archivo primero.', 'msg-yellow');
            return;
        }

        setLoading(true, uploadButton, 'Subir Archivo');

        try {
            // Usamos FormData para asegurar la subida correcta.
            const formData = new FormData();
            formData.append('file', file, file.name); 

            const response = await fetch('/upload', {
                method: 'POST',
                body: formData 
            });

            if (response.ok) {
                showMessage(uploadMessageArea, uploadMessageText, `¡Archivo "${file.name}" subido con éxito! Listo para flashear.`, 'msg-green');
                
                showElement(romWriteCard);
                hideMessage(romMessageArea);
            } else {
                const errorBody = await response.text();
                showMessage(uploadMessageArea, uploadMessageText, `Error: ${response.status}. Servidor: ${errorBody || 'Sin cuerpo de error.'}`, 'msg-red');
                hideElement(romWriteCard);
            }

        } catch (error) {
            console.error('Error de red:', error);
            showMessage(uploadMessageArea, uploadMessageText, `Error de red: ${error.message}`, 'msg-red');
            hideElement(romWriteCard);
        } finally {
            setLoading(false, uploadButton, 'Subir Archivo');
        }
    });
    /*
    deleteButton.addEventListener('click', async () => {
        
        setLoading(true, deleteButton, 'Borrando...');

        try {
            const response = await fetch('/deleterom', {
                method: 'GET'
            });

            if (response.ok) {
                resultado = await response.text()
                console.log(resultado)
                if (resultado.trim() == "true") {
                    romWriteCard.classList.add('hidden');
                    showMessage(romMessageArea, romMessageText, `✅ Rom borrada con éxito de la memoria.`, 'msg-green');
                    handleFiles(new DataTransfer().files); // Limpia la selección de archivo
                }else{
                    showMessage(romMessageArea, romMessageText, `❌ Error borrando la Rom.`, 'msg-red');
                }
                
            } else {
                const errorBody = await response.text();
                showMessage(romMessageArea, romMessageText, `❌ Error en el servidor (${response.status}) al borrar la Rom.`, 'msg-red');
            }
        } catch (error) {
            console.error('Error de red al configurar:', error);
            showMessage(romMessageArea, romMessageText, `❌ Error de red al borrar la Rom.`, 'msg-red');
        } finally {
            setLoading(false, deleteButton, 'Borrar rom de la memoria');
        }
    }); 
    */	 	

    saveButton.addEventListener('click', async () => {
        const ssid = ssidInput.value.trim();
        const password = passwordInput.value.trim();
        
        if (!ssid) {
            showMessage(configMessageArea, configMessageText, 'El SSID no puede estar vacío.', 'msg-yellow');
            return;
        }

        const body = `ssid=${encodeURIComponent(ssid)}&pwd=${encodeURIComponent(password)}`;
        
        setLoading(true, saveButton, 'Guardando...');

        try {
            const response = await fetch('/info', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/x-www-form-urlencoded',
                    'Content-Length': body.length
                },
                body: body
            });

            if (response.ok) {
                showMessage(configMessageArea, configMessageText, `✅ Configuración guardada para SSID: ${ssid}. (El dispositivo puede reiniciarse)`, 'msg-green');
            } else {
                const errorBody = await response.text();
                showMessage(configMessageArea, configMessageText, `❌ Error al guardar: ${response.status}. Servidor: ${errorBody || 'Sin cuerpo de error.'}`, 'msg-red');
            }
        } catch (error) {
            console.error('Error de red al configurar:', error);
            showMessage(configMessageArea, configMessageText, `Error de red: ${error.message}`, 'msg-red');
        } finally {
            setLoading(false, saveButton, 'Guardar Configuración');
        }
    });
    /*
    
    writeRomButton.addEventListener('click', async () => {
        
        setLoading(true, writeRomButton, 'Grabar Archivo en ROM');
        hideMessage(romMessageArea);
        
        
        try {
            const response = await fetch('/writerom', {
                method: 'POST',
                headers: { 'Content-Length': 0 } 
            });
            
            const responseText = await response.text();

            if (response.ok) {
                if (responseText.toLowerCase().trim() === 'true') {
                    showMessage(romMessageArea, romMessageText, 
                        `✅ Flasheo de ROM exitoso. El dispositivo se reiniciará.`, 
                        'msg-green');
                } else {
                    console.log("error")
                    showMessage(romMessageArea, romMessageText, 
                        `❌ Falló la grabación en ROM. Revise el log del servidor.`, 
                        'msg-red');    
                }
            } else {
                showMessage(romMessageArea, romMessageText, 
                    `Error HTTP (${response.status}) durante el flasheo. Servidor: ${responseText}`, 
                    'msg-red');
            }
            
        } catch (error) {
            console.error('Error de red al flashear:', error);
            showMessage(romMessageArea, romMessageText, 
                `Error de red: No se pudo contactar al servidor. (${error.message})`, 
                'msg-red');
        } finally {
            setLoading(false, writeRomButton, 'Grabar Archivo en ROM');
        }
        
    });
    */
    
    
    
    // --- Lógica para Colapsar/Expandir la Tarjeta de Configuración ---
    toggleConfigButton.classList.add('collapsed'); 
    
    toggleConfigButton.addEventListener('click', () => {
        const isCollapsed = configContent.classList.contains('collapsed-content');
        
        if (isCollapsed) {
            configContent.classList.remove('collapsed-content');
            toggleConfigButton.classList.remove('collapsed');
        } else {
            configContent.classList.add('collapsed-content');
            toggleConfigButton.classList.add('collapsed');
        }
    });
    
    
    
    