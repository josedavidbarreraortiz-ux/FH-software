// FH Store — App JavaScript

// Auto-dismiss alerts after 4 seconds
document.addEventListener('DOMContentLoaded', function() {
    const alerts = document.querySelectorAll('.alert-fh');
    alerts.forEach(alert => {
        setTimeout(() => {
            alert.style.opacity = '0';
            alert.style.transform = 'translateY(-10px)';
            setTimeout(() => alert.remove(), 300);
        }, 4000);
    });
});

// Confirm delete actions
function confirmDelete(form, name) {
    if (confirm(`¿Estás seguro de eliminar "${name}"? Esta acción no se puede deshacer.`)) {
        form.submit();
    }
    return false;
}

// Quantity input controls
function updateQuantity(input, delta) {
    let val = parseInt(input.value) || 1;
    val += delta;
    if (val < 1) val = 1;
    const max = parseInt(input.getAttribute('max')) || 999;
    if (val > max) val = max;
    input.value = val;
}

// Table Filtering Logic
function setupTableFilter(searchInputId, tableId, filters = []) {
    const searchInput = document.getElementById(searchInputId);
    const table = document.getElementById(tableId);
    if (!searchInput || !table) return;

    const tbody = table.querySelector('tbody');
    const rows = tbody.querySelectorAll('tr');

    const filterSelects = filters.map(f => ({
        element: document.getElementById(f.selectId),
        colIndex: f.colIndex,
        exactMatch: f.exactMatch || false
    }));

    function filterTable() {
        const query = searchInput.value.toLowerCase();
        
        rows.forEach(row => {
            // Skip empty state row
            if (row.querySelector('.empty-state')) return;

            let textMatch = row.textContent.toLowerCase().includes(query);
            let selectMatch = true;

            filterSelects.forEach(f => {
                if (f.element && f.element.value !== "") {
                    const cell = row.cells[f.colIndex];
                    if (cell) {
                        const cellText = cell.textContent.replace(/\s+/g, ' ').trim().toLowerCase();
                        const filterVal = f.element.value.toLowerCase();
                        
                        if (f.exactMatch) {
                            if (cellText !== filterVal) selectMatch = false;
                        } else {
                            if (!cellText.includes(filterVal)) selectMatch = false;
                        }
                    }
                }
            });

            if (textMatch && selectMatch) {
                row.style.display = '';
            } else {
                row.style.display = 'none';
            }
        });
    }

    searchInput.addEventListener('input', filterTable);
    filterSelects.forEach(f => {
        if (f.element) {
            f.element.addEventListener('change', filterTable);
        }
    });
}
