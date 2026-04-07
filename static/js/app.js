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
