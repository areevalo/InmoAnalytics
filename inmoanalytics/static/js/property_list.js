// Devuelve true si hay algún filtro activo
function hasActiveFilters() {
    const form = document.getElementById('filters-form');
    for (const el of form.elements) {
        if (
            el.name &&
            !["submit", "button", "reset", "hidden"].includes(el.type)
        ) {
            if (el.type === "checkbox" && el.checked) return true;
            if (el.id === "price_min" && Number(el.value) > 0) return true;
            if (el.id === "price_max" && Number(el.value) < 1000000) return true;
            if (
                el.type !== "checkbox" &&
                el.id !== "price_min" &&
                el.id !== "price_max" &&
                el.value !== "" &&
                el.value !== "0"
            ) return true;
        }
    }
    return false;
}

// Al hacer clic en el botón de "Exportar a Excel", se envía el formulario y aparece un mensaje de carga
document.getElementById('export-excel-btn').addEventListener('click', function(e) {
    e.preventDefault();

    if (!hasActiveFilters()) {
        alert("Por favor, aplica al menos un filtro antes de exportar para evitar descargas masivas.");
        return;
    }

    var loadingModal = new bootstrap.Modal(document.getElementById('loadingModal'));
    loadingModal.show();

    const form = document.querySelector('form');
    const max = 1000000;
    const priceMaxInput = document.getElementById('price_max');
    let originalName = priceMaxInput.getAttribute('name');
    if (parseInt(priceMaxInput.value) === max) {
        priceMaxInput.removeAttribute('name');
    }

    const formData = new FormData(form);

    // Restaurar el name después de crear el FormData
    if (!priceMaxInput.hasAttribute('name') && originalName) {
        priceMaxInput.setAttribute('name', originalName);
    }

    fetch(exportUrl + "?" + new URLSearchParams(formData), {
        method: 'GET',
        headers: {
            'X-Requested-With': 'XMLHttpRequest'
        }
    })
    .then(response => response.blob())
    .then(blob => {
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = "propiedades.xlsx";
        document.body.appendChild(a);
        a.click();
        a.remove();
        window.URL.revokeObjectURL(url);
        loadingModal.hide();
    })
    .catch(() => {
        loadingModal.hide();
        alert("Error: la generación del Excel ha sido interrumpida. Por favor, " +
            "vuelve a intentarlo en unos instantes y no recargues la página mientras tanto.");
    })
    .finally(() => {
        loadingModal.hide();
    });
});

// Al hacer clic en el botón de "Quitar filtros" se restablecen los filtros
document.getElementById('clear-filters-btn').addEventListener('click', function(e) {
    e.preventDefault();
    const form = document.querySelector('form');
    form.reset();

    // Restablece todos los selects a su primer valor
    form.querySelectorAll('select').forEach(function(select) {
        select.selectedIndex = 0;
        // Si es el select de barrio, deshabilítalo y pon la opción por defecto
        if (select.id === 'id_neighborhood') {
            select.innerHTML = '<option value="">Introduce un municipio</option>';
            select.disabled = true;
        }
    });

    // Desmarca todos los checkboxes
    form.querySelectorAll('input[type="checkbox"]').forEach(function(checkbox) {
        checkbox.checked = false;
    });

    // Restaura los rangos de precio y superficie
    document.getElementById('min_area').value = '';
    document.getElementById('price_min').value = 0;
    document.getElementById('price_max').value = 1000000;
    updatePriceVals();

    // Limpia la URL
    window.history.replaceState({}, document.title, window.location.pathname);
});

// Al cambiar el municipio, actualiza los barrios
document.getElementById('id_municipality').addEventListener('change', function() {
    const municipio = this.querySelector('select, input').value;
    const barrio = document.getElementById('id_neighborhood');
    barrio.innerHTML = '';
    if (municipio) {
        fetch(`/ajax/get_neighborhoods/?municipality=${encodeURIComponent(municipio)}`)
            .then(response => response.json())
            .then(data => {
                barrio.disabled = false;
                barrio.innerHTML = '<option value="">Cualquiera</option>';
                data.neighborhoods.forEach(function(n) {
                    barrio.innerHTML += `<option value="${n}">${n}</option>`;
                });
            });
    } else {
        barrio.disabled = true;
        barrio.innerHTML = '<option value="">Introduce un municipio</option>';
    }
});

// Actualiza los valores mostrados de los rangos de precio mínimo y máximo
function updatePriceVals() {
    const max = 1000000;
    const minVal = document.getElementById('price_min').value;
    const maxVal = document.getElementById('price_max').value;
    const formatOpts = { style: 'currency', currency: 'EUR', minimumFractionDigits: 0, maximumFractionDigits: 0 };
    document.getElementById('min_price_val').textContent = new Intl.NumberFormat('es-ES', formatOpts).format(minVal);
    document.getElementById('max_price_val').textContent = maxVal >= max ? "Sin límite" : new Intl.NumberFormat('es-ES', formatOpts).format(maxVal);
}

// Ejecuta al cargar
document.addEventListener('DOMContentLoaded', function() {
    updatePriceVals();

    // Inicializa los selects de municipio y barrio
    const municipioSelect = document.querySelector('#id_municipality select, #id_municipality input');
    const barrio = document.getElementById('id_neighborhood');
    if (municipioSelect && municipioSelect.value) {
        fetch(`/ajax/get_neighborhoods/?municipality=${encodeURIComponent(municipioSelect.value)}`)
            .then(response => response.json())
            .then(data => {
                barrio.disabled = false;
                barrio.innerHTML = '<option value="">Cualquiera</option>';
                data.neighborhoods.forEach(function(n) {
                    barrio.innerHTML += `<option value="${n}">${n}</option>`;
                });
                // Selecciona el barrio si ya estaba seleccionado
                if (barrio.dataset.selected) {
                    barrio.value = barrio.dataset.selected;
                }
            });
    }

    // Restaura el estado del acordeón al cargar la página
    if (localStorage.getItem('accordionBooleanOpen') === 'true') {
        const bsCollapse = new bootstrap.Collapse(collapseBoolean, { show: true, toggle: false });
        bsCollapse.show();
    }

    // Si hay un parámetro 'page' en la URL, desplaza la vista al inicio de la tabla
    if (window.location.search.includes('page=')) {
        const table = document.getElementById('property-list-table');
        if (table) {
            table.scrollIntoView({ behavior: 'smooth', block: 'start' });
        }
    }
});

// Controla que el precio mínimo no supere al máximo y viceversa
document.getElementById('price_min').addEventListener('input', function() {
    const min = Number(this.value);
    const maxInput = document.getElementById('price_max');
    let max = Number(maxInput.value);
    if (min > max) {
        maxInput.value = min;
        updatePriceVals();
    }
});

// Controla que el precio máximo no sea menor al mínimo y viceversa
document.getElementById('price_max').addEventListener('input', function() {
    const max = Number(this.value);
    const minInput = document.getElementById('price_min');
    let min = Number(minInput.value);
    if (max < min) {
        minInput.value = max;
        updatePriceVals();
    }
});

// Al enviar el formulario, si el valor es el máximo, vacía el campo
document.querySelector('form').addEventListener('submit', function(e) {
    const max = 1000000;
    const priceMaxInput = document.getElementById('price_max');
    if (parseInt(priceMaxInput.value) === max) {
        priceMaxInput.removeAttribute('name');
    }
});

// Guardar el estado del acordeón en localStorage
const collapseBoolean = document.getElementById('collapseBoolean');
collapseBoolean.addEventListener('show.bs.collapse', function () {
    localStorage.setItem('accordionBooleanOpen', 'true');
});
collapseBoolean.addEventListener('hide.bs.collapse', function () {
    localStorage.setItem('accordionBooleanOpen', 'false');
});
