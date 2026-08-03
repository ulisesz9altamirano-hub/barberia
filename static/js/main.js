document.addEventListener('DOMContentLoaded', () => {
    // Seteamos la fecha mínima como HOY
    const fechaInput = document.getElementById('fecha');
    const servicioSelect = document.getElementById('servicio');

    if (fechaInput) {
        const hoy = new Date().toISOString().split('T')[0];
        fechaInput.min = hoy;
        fechaInput.value = hoy;

        // Escuchamos el cambio de fecha para actualizar horarios automáticamente
        fechaInput.addEventListener('change', actualizarHorarios);
    }

    if (servicioSelect) {
        // Escuchamos el cambio de servicio para actualizar horarios
        servicioSelect.addEventListener('change', actualizarHorarios);
    }

    // Interceptamos el envío del formulario de reserva
    const turnoForm = document.getElementById('turnoform');
    if (turnoForm) {
        turnoForm.addEventListener('submit', guardarTurno);
    }
});

// 1. Cambiar entre las pestañas "Solicitar Turno" y "Mis Turnos"
function mostrarSeccion(seccion) {
    const secReserva = document.getElementById('sec-reserva');
    const secMisTurnos = document.getElementById('sec-misturnos');
    const btnTabReserva = document.getElementById('btnTabReserva');
    const btnTabMisTurnos = document.getElementById('btnTabMisTurnos');

    if (seccion === 'reserva') {
        secReserva.classList.remove('hidden');
        secMisTurnos.classList.add('hidden');
        btnTabReserva.classList.add('active');
        btnTabMisTurnos.classList.remove('active');
    } else {
        secReserva.classList.add('hidden');
        secMisTurnos.classList.remove('hidden');
        btnTabReserva.classList.remove('active');
        btnTabMisTurnos.classList.add('active');
    }
}

// 2. Consultar horarios disponibles según servicio y fecha seleccionados
async function actualizarHorarios() {
    const servicioSelect = document.getElementById('servicio');
    const fechaInput = document.getElementById('fecha');
    const contenedor = document.getElementById('contenedor-horarios');
    const btnReservar = document.getElementById('btnReservar');
    const inputFechaHoraInicio = document.getElementById('fecha_hora_inicio');

    if (!servicioSelect || !fechaInput || !contenedor) return;

    // Reseteamos la selección previa
    if (inputFechaHoraInicio) inputFechaHoraInicio.value = "";
    if (btnReservar) btnReservar.disabled = true;

    const servicioOption = servicioSelect.options[servicioSelect.selectedIndex];
    
    // Si la opción no tiene data-duracion, tomamos 30 por defecto
    const duracion = servicioOption ? (servicioOption.getAttribute('data-duracion') || 30) : 30;
    const fecha = fechaInput.value;

    if (!servicioSelect.value || !fecha) {
        contenedor.innerHTML = '<p style="font-size: 0.9em; opacity: 0.7;">Seleccioná un servicio y una fecha para ver las horas disponibles.</p>';
        return;
    }

    contenedor.innerHTML = '<p style="font-size: 0.9em; opacity: 0.7;">Buscando disponibilidad...</p>';

    try {
        // CORREGIDO: Llamada a /disponibilidad en lugar de /api/disponibilidad
        const response = await fetch(`/disponibilidad?fecha=${fecha}&duracion=${duracion}`);
        const data = await response.json();

        if (!response.ok) {
            throw new Error(data.error || 'Error al obtener la disponibilidad.');
        }

        contenedor.innerHTML = '';

        if (!data.horarios_disponibles || data.horarios_disponibles.length === 0) {
            contenedor.innerHTML = '<p style="color: #e74c3c; font-size: 0.9em;">No hay horarios disponibles para esta fecha. Intentá con otro día.</p>';
            return;
        }

        // Renderizamos cada horario como un botón interactivo
        data.horarios_disponibles.forEach(horario => {
            const btn = document.createElement('button');
            btn.type = 'button';
            btn.className = 'btn-horario';
            btn.style.cssText = 'padding: 8px 12px; cursor: pointer; border-radius: 6px; border: 1px solid #444; background: #222; color: #fff; margin: 3px;';
            btn.innerText = `${horario} hs`;

            btn.onclick = () => seleccionarHorario(btn, fecha, horario);
            contenedor.appendChild(btn);
        });

    } catch (error) {
        contenedor.innerHTML = `<p style="color: #e74c3c; font-size: 0.9em;">${error.message}</p>`;
    }
}

// 3. Marcar el horario elegido y llenar el input oculto
function seleccionarHorario(botonSeleccionado, fecha, horario) {
    // Desmarcamos los demás botones
    const botones = document.querySelectorAll('.btn-horario');
    botones.forEach(b => {
        b.style.background = '#222';
        b.style.borderColor = '#444';
        b.style.color = '#fff';
    });

    // Destacamos el seleccionado
    botonSeleccionado.style.background = '#f39c12';
    botonSeleccionado.style.borderColor = '#f39c12';
    botonSeleccionado.style.color = '#000';

    // Formateamos para el backend: YYYY-MM-DD HH:MM:SS
    const fechaHoraCompleta = `${fecha} ${horario}:00`;
    const inputFechaHora = document.getElementById('fecha_hora_inicio');
    if (inputFechaHora) inputFechaHora.value = fechaHoraCompleta;

    // Habilitamos el botón de confirmación
    const btnReservar = document.getElementById('btnReservar');
    if (btnReservar) btnReservar.disabled = false;
}

// 4. Enviar el formulario por POST (Reserva de Turno) + Botón de WhatsApp
async function guardarTurno(event) {
    event.preventDefault();

    const form = event.target;
    const mensajeDiv = document.getElementById('mensaje');
    const formData = new FormData(form);

    // Número de teléfono de la barbería (formato internacional sin '+' ni espacios, ej: 549261XXXXXXX)
    const telefonoBarberia = "2617111500"; // <-- Cambiá este número por el tuyo

    try {
        const response = await fetch('/api/turnos', {
            method: 'POST',
            body: formData
        });

        const data = await response.json();

        if (response.ok) {
            // Extraemos datos del servicio seleccionado para el mensaje
            const servicioSelect = document.getElementById('servicio');
            const servicioNombre = servicioSelect.options[servicioSelect.selectedIndex].text;
            const fechaHora = document.getElementById('fecha_hora_inicio').value;

            // Preparamos el texto de WhatsApp
            const textoMensaje = `¡Hola! Acabo de reservar un turno en Faded Shop \n\n` +
                                 ` *Nombre:* ${formData.get('nombre')}\n` +
                                 ` *Servicio:* ${servicioNombre}\n` +
                                 ` *Fecha y hora:* ${fechaHora} hs\n\n` +
                                 `¿Me confirman la recepción? ¡Muchas gracias!`;

            const urlWhatsapp = `https://wa.me/${telefonoBarberia}?text=${encodeURIComponent(textoMensaje)}`;

            // Renderizamos la respuesta con el botón directo a WhatsApp
            mensajeDiv.className = 'mensaje exito';
            mensajeDiv.innerHTML = `
                <p style="margin: 0 0 10px 0; font-weight: bold; color: #2ecc71;">¡Turno reservado con éxito!</p>
                <a href="${urlWhatsapp}" target="_blank" class="btn-whatsapp">
                    <i class="fab fa-whatsapp"></i> Confirmar reserva por WhatsApp
                </a>
            `;
            mensajeDiv.classList.remove('hidden');

            form.reset();
            actualizarHorarios(); // Refrescamos la lista de horarios
        } else {
            throw new Error(data.error || 'No se pudo agendar el turno.');
        }
    } catch (error) {
        mensajeDiv.className = 'mensaje error';
        mensajeDiv.style.color = '#e74c3c';
        mensajeDiv.innerText = error.message;
        mensajeDiv.classList.remove('hidden');
    }
}

// 5. Consultar "Mis Turnos" por teléfono
async function consultarMisTurnos() {
    const telefonoInput = document.getElementById('buscar_telefono');
    const contenedor = document.getElementById('lista-mis-turnos');

    if (!telefonoInput || !telefonoInput.value.trim()) {
        alert('Por favor, ingresá tu número de teléfono.');
        return;
    }

    const telefono = telefonoInput.value.trim();
    contenedor.innerHTML = '<p style="font-size: 0.9em; opacity: 0.7;">Buscando tus turnos...</p>';

    try {
        const response = await fetch(`/api/mis-turnos?telefono=${telefono}`);
        const turnos = await response.json();

        if (!response.ok) {
            throw new Error(turnos.error || 'Error al buscar los turnos.');
        }

        contenedor.innerHTML = '';

        if (turnos.length === 0) {
            contenedor.innerHTML = '<p style="font-size: 0.9em; opacity: 0.7;">No tenés turnos agendados con este número.</p>';
            return;
        }

        turnos.forEach(t => {
            const tarjeta = document.createElement('div');
            tarjeta.style.cssText = 'padding: 12px; margin-bottom: 10px; border: 1px solid #333; border-radius: 8px; background: #1a1a1a; display: flex; justify-content: space-between; align-items: center;';
            tarjeta.innerHTML = `
                <div>
                    <h4 style="margin: 0; color: #f39c12;">${t.servicio}</h4>
                    <p style="margin: 4px 0 0; font-size: 0.85em; opacity: 0.8;">📅 ${t.fecha_hora_inicio} hs</p>
                    <p style="margin: 2px 0 0; font-size: 0.85em; color: #2ecc71;">$${t.precio}</p>
                </div>
                <div>
                    <span style="padding: 4px 8px; border-radius: 4px; font-size: 0.75em; text-transform: uppercase; background: #222; border: 1px solid #555;">${t.estado}</span>
                </div>
            `;
            contenedor.appendChild(tarjeta);
        });

    } catch (error) {
        contenedor.innerHTML = `<p style="color: #e74c3c; font-size: 0.9em;">${error.message}</p>`;
    }
}