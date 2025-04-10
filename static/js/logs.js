document.querySelectorAll('a[timestamp]').forEach(item => {
    const date = new Date(item.getAttribute('timestamp'));
    item.textContent = `${item.textContent} [${date.toLocaleString()}]`;
});

function doFilter() {
    const filter = document.getElementById('filterInput').value.toUpperCase();
    document.querySelectorAll('li.directory').forEach(item => {
        item.style.display = item.innerText.toUpperCase().indexOf(filter) > -1 ? '' : 'none';
    });
    localStorage.setItem('filter', filter);
}

const filterInput = document.getElementById('filterInput');
if (filterInput) {
    filterInput.value = localStorage.getItem('filter') || '';
    doFilter();
    filterInput.addEventListener('input', doFilter);
}
