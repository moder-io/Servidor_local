let currentMonth = new Date().getMonth();
let currentYear = new Date().getFullYear();

document.getElementById('fileInput').addEventListener('change', function(e) {
    var fileName = e.target.files[0].name;
    document.getElementById('fileName').textContent = fileName;
});

document.addEventListener("DOMContentLoaded", () => {
    fetchFileList();
    loadShoppingList();
    loadCalendar(currentMonth, currentYear);
});

function fetchFileList() {
    fetch('/uploads/')
        .then(response => response.text())
        .then(data => {
            const parser = new DOMParser();
            const htmlDocument = parser.parseFromString(data, "text/html");
            const fileLinks = Array.from(htmlDocument.querySelectorAll("a"))
                .filter(link => !link.href.endsWith('/'))
                .map(link => {
                    return link.href.replace(window.location.origin, '') || '/uploads/' + link.href.split('/').pop();
                });

            const fileList = document.getElementById('fileList');
            fileList.innerHTML = '';
            fileLinks.forEach(file => {
                const fileName = file.split('/').pop();
                const listItem = document.createElement('li');
                const link = document.createElement('a');
                link.href = "uploads" + file;
                link.textContent = fileName;
                link.setAttribute('download', fileName);

                const deleteButton = document.createElement('button');
                deleteButton.textContent = 'Eliminar';
                deleteButton.onclick = () => deleteFile(file);

                listItem.appendChild(link);
                listItem.appendChild(deleteButton);
                fileList.appendChild(listItem);
            });
        })
        .catch(error => console.error('Error al obtener la lista de archivos:', error));
}

function uploadFiles() {
    const input = document.getElementById('fileInput');
    const files = input.files;
    if (files.length === 0) {
        alert('Por favor, selecciona al menos un archivo para subir.');
        return;
    }

    const formData = new FormData();
    for (const file of files) {
        formData.append('file', file);
    }

    fetch('/', {
        method: 'POST',
        body: formData
    })
    .then(response => {
        if (!response.ok) {
            throw new Error('Error en la subida de archivos');
        }
        return response.text();
    })
    .then(data => {
        alert('Archivos subidos con éxito.');
        fetchFileList();
    })
    .catch(error => {
        console.error('Error al subir los archivos:', error);
        alert('Hubo un problema al subir los archivos.');
    });
}

function loadShoppingList() {
    fetch('/shopping_list')
        .then(response => response.json())
        .then(data => {
            const listElement = document.getElementById('shoppingList');
            listElement.innerHTML = '';
            data.forEach(item => {
                const listItem = document.createElement('li');
                listItem.textContent = item;
                const removeButton = document.createElement('button');
                removeButton.textContent = 'Eliminar';
                removeButton.onclick = () => {
                    removeItem(item);
                };
                listItem.appendChild(removeButton);
                listElement.appendChild(listItem);
            });
        })
        .catch(error => console.error('Error al cargar la lista de compras:', error));
}

function addItem() {
    const input = document.getElementById('itemInput');
    const item = input.value.trim();
    if (item) {
        fetch('/add_item', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ name: item })
        })
        .then(response => {
            if (!response.ok) {
                throw new Error('Error al agregar el ítem');
            }
            input.value = '';
            loadShoppingList();
        })
        .catch(error => {
            console.error('Error al agregar el ítem:', error);
        });
    } else {
        alert('Por favor, ingrese un ítem.');
    }
}

function removeItem(item) {
    fetch(`/remove_item/${item}`, {
        method: 'DELETE'
    })
    .then(response => {
        if (!response.ok) {
            throw new Error('Error al eliminar el ítem');
        }
        loadShoppingList();
    })
    .catch(error => {
        console.error('Error al eliminar el ítem:', error);
    });
}

function loadCalendar(month = currentMonth, year = currentYear) {
    fetch(`/calendar?month=${month + 1}&year=${year}`)
        .then(response => response.json())
        .then(data => {
            const calendarElement = document.getElementById('calendar');
            calendarElement.innerHTML = '';

            const monthYearElement = document.getElementById('monthYear');
            const date = new Date(year, month);
            const monthName = date.toLocaleString('es-ES', { month: 'long' });
            monthYearElement.textContent = `${monthName} ${year}`;

            const table = document.createElement('table');
            const headerRow = table.insertRow();
            ['Domingo', 'Lunes', 'Martes', 'Miércoles', 'Jueves', 'Viernes', 'Sábado'].forEach(day => {
                const th = document.createElement('th');
                th.textContent = day;
                headerRow.appendChild(th);
            });

            date.setDate(1);
            let firstDay = date.getDay();
            let daysInMonth = new Date(year, month + 1, 0).getDate();

            let day = 1;
            for (let i = 0; i < 6; i++) {
                const row = table.insertRow();
                for (let j = 0; j < 7; j++) {
                    if (i === 0 && j < firstDay) {
                        row.insertCell();
                    } else if (day > daysInMonth) {
                        break;
                    } else {
                        const cell = row.insertCell();
                        cell.textContent = day;
                        const formattedDate = `${year}-${String(month + 1).padStart(2, '0')}-${String(day).padStart(2, '0')}`;
                        const events = data.filter(event => event.date === formattedDate);
                        events.forEach(event => {
                            const eventElement = document.createElement('div');
                            eventElement.className = 'event';
                            eventElement.textContent = event.title;

                            const deleteButton = document.createElement('button');
                            deleteButton.textContent = 'Eliminar';
                            deleteButton.onclick = () => deleteEvent(formattedDate, event.title);

                            eventElement.appendChild(deleteButton);
                            cell.appendChild(eventElement);
                        });
                        day++;
                    }
                }
            }

            calendarElement.appendChild(table);
        })
        .catch(error => console.error('Error al cargar el calendario:', error));
}

function addEvent() {
    const date = document.getElementById('eventDate').value;
    const title = document.getElementById('eventTitle').value.trim();
    if (date && title) {
        fetch('/add_event', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ date, title })
        })
        .then(response => {
            if (!response.ok) {
                throw new Error('Error al agregar el evento');
            }
            document.getElementById('eventDate').value = '';
            document.getElementById('eventTitle').value = '';
            loadCalendar(currentMonth, currentYear); 
        })
        .catch(error => {
            console.error('Error al agregar el evento:', error);
        });
    } else {
        alert('Por favor, ingrese una fecha y un título para el evento.');
    }
}

function prevMonth() {
    currentMonth--;
    if (currentMonth < 0) {
        currentMonth = 11;
        currentYear--;
    }
    loadCalendar(currentMonth, currentYear);
}

function nextMonth() {
    currentMonth++;
    if (currentMonth > 11) {
        currentMonth = 0;
        currentYear++;
    }
    loadCalendar(currentMonth, currentYear);
}

function deleteFile(file) {
    const fileName = file.split('/').pop();
    fetch(`/delete_file/${fileName}`, {
        method: 'DELETE'
    })
    .then(response => {
        if (!response.ok) {
            throw new Error('Error al eliminar el archivo');
        }
        fetchFileList();
    })
    .catch(error => {
        console.error('Error al eliminar el archivo:', error);
    });
}

function deleteEvent(date, title) {
    fetch(`/delete_event`, {
        method: 'DELETE',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ date, title })
    })
    .then(response => {
        if (!response.ok) {
            throw new Error('Error al eliminar el evento');
        }
        loadCalendar(currentMonth, currentYear);
    })
    .catch(error => {
        console.error('Error al eliminar el evento:', error);
    });
}