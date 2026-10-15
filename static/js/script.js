setTimeout(() => {
    document.querySelectorAll('.alert').forEach(el => {
        el.style.transition = 'opacity 0.5s';
        el.style.opacity = '0';
        setTimeout(() => el.remove(), 500);
    });
}, 4000);

document.querySelectorAll('input[type="date"]').forEach(inp => {
    if (!inp.min) inp.min = new Date().toISOString().split('T')[0];
});

document.querySelectorAll('.btn-danger').forEach(btn => {
    btn.addEventListener('click', e => {
        if (!confirm('Are you sure?')) e.preventDefault();
    });
});