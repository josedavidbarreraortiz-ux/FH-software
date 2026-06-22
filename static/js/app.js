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
function setupTableFilter(searchInputId, tableId, filters = [], rowsPerPage = 10) {
    const searchInput = document.getElementById(searchInputId);
    const table = document.getElementById(tableId);
    if (!searchInput || !table) return;

    const tbody = table.querySelector('tbody');
    const rows = Array.from(tbody.querySelectorAll('tr'));
    
    // Create pagination container if it doesn't exist
    let paginationContainer = table.nextElementSibling;
    if (!paginationContainer || !paginationContainer.classList.contains('pagination-fh')) {
        paginationContainer = document.createElement('div');
        paginationContainer.className = 'pagination-fh';
        table.parentNode.insertBefore(paginationContainer, table.nextSibling);
    }

    const filterSelects = filters.map(f => ({
        element: document.getElementById(f.selectId),
        colIndex: f.colIndex,
        exactMatch: f.exactMatch || false
    }));

    let currentPage = 1;
    let filteredRows = [];

    function renderPagination() {
        paginationContainer.innerHTML = '';
        const totalPages = Math.ceil(filteredRows.length / rowsPerPage);
        
        if (totalPages <= 1) return; // Hide pagination if only 1 page

        const createBtn = (text, disabled, onClick) => {
            const btn = document.createElement('button');
            btn.innerHTML = text;
            btn.className = disabled ? 'btn-page disabled' : 'btn-page';
            if (!disabled) {
                btn.addEventListener('click', (e) => {
                    e.preventDefault();
                    onClick();
                });
            }
            return btn;
        };

        const prevBtn = createBtn('<i class="fas fa-chevron-left"></i>', currentPage === 1, () => {
            currentPage--;
            displayRows();
        });
        paginationContainer.appendChild(prevBtn);

        const pageInfo = document.createElement('span');
        pageInfo.className = 'page-info';
        pageInfo.textContent = `Página ${currentPage} de ${totalPages}`;
        paginationContainer.appendChild(pageInfo);

        const nextBtn = createBtn('<i class="fas fa-chevron-right"></i>', currentPage === totalPages, () => {
            currentPage++;
            displayRows();
        });
        paginationContainer.appendChild(nextBtn);
    }

    function displayRows() {
        const startIndex = (currentPage - 1) * rowsPerPage;
        const endIndex = startIndex + rowsPerPage;

        // Hide all first
        rows.forEach(row => row.style.display = 'none');

        // Show only rows for current page
        const rowsToShow = filteredRows.slice(startIndex, endIndex);
        rowsToShow.forEach(row => row.style.display = '');

        renderPagination();
    }

    function filterTable() {
        const query = searchInput.value.toLowerCase();
        
        filteredRows = rows.filter(row => {
            if (row.querySelector('.empty-state')) return false;

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

            return textMatch && selectMatch;
        });

        // Show empty state if needed
        const emptyRow = rows.find(r => r.querySelector('.empty-state'));
        if (filteredRows.length === 0 && emptyRow) {
            emptyRow.style.display = '';
        } else if (emptyRow) {
            emptyRow.style.display = 'none';
        }

        currentPage = 1; // Reset to page 1 on filter
        displayRows();
    }

    searchInput.addEventListener('input', filterTable);
    filterSelects.forEach(f => {
        if (f.element) {
            f.element.addEventListener('change', filterTable);
        }
    });

    // Initial render
    filterTable();
}
