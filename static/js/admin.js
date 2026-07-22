document.addEventListener('DOMContentLoaded', () => {
    cargarTurnos();

    const btnRefrescar = document.getElementById('btnRefrescar');
    if (btnRefrescar) {
        btnRefrescar.addEventListener('click', cargarTurnos);
    }
});

async function cargarTurnos() {
    const tablaBody = document.getElementById('tablaTurnosBody');
    if (!tablaBody) return;

    tablaBody.innerHTML = '<tr><td colspan="7">Cargando turnos...</td></tr>';

    try {
        const res = await fetch('/api/turnos');
        const turnos = await res.json();

        if (!res.ok) {
            tablaBody.innerHTML = `<tr><td colspan="7" style="color: red;">Error: ${turnos.error || 'No se pudieron cargar los datos'}</td></tr>`;
            return;
        }

        if (!Array.isArray(turnos) || turnos.length === 0) {
            tablaBody.innerHTML = '<tr><td colspan="7">No hay turnos registrados por ahora.</td></tr>';
            return;
        }

        tablaBody.innerHTML = '';
        turnos.forEach(turno => {
            const tr = document.createElement('tr');
            tr.innerHTML = `
                <td>#${turno.id}</td>
                <td><strong>${turno.cliente}</strong></td>
                <td>${turno.telefono}</td>
                <td>${turno.servicio}</td>
                <td>${turno.fecha_hora_inicio} hs</td>
                <td>$${turno.precio}</td>
                <td>
                    <button class="btn-eliminar" onclick="eliminarTurno(${turno.id})">Cancelar / Eliminar</button>
                </td>
            `;
            tablaBody.appendChild(tr);
        });
    } catch (error) {
        console.error('Error al cargar turnos:', error);
        tablaBody.innerHTML = '<tr><td colspan="7" style="color: red;">Error de conexión con el servidor.</td></tr>';
    }
}

async function eliminarTurno(id) {
    if (!confirm(`¿Estás seguro de que querés eliminar el turno #${id}?`)) return;

    try {
        const res = await fetch(`/api/turnos/${id}`, {
            method: 'DELETE'
        });
        const data = await res.json();

        if (res.ok) {
            alert(data.mensaje);
            cargarTurnos();
        } else {
            alert(data.error || 'No se pudo eliminar el turno');
        }
    } catch (error) {
        console.error('Error al eliminar turno:', error);
        alert('Error al conectar con el servidor.');
    }
}