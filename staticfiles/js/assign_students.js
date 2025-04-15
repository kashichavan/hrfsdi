document.addEventListener('DOMContentLoaded', function() {
    // Toggle advanced filters
    const filterToggle = document.getElementById('filterToggle');
    const advancedFilters = document.getElementById('advancedFilters');
    
    filterToggle.addEventListener('click', function() {
        advancedFilters.classList.toggle('show');
        filterToggle.textContent = advancedFilters.classList.contains('show') 
            ? 'Hide Filters' 
            : 'Advanced Filters';
    });

    // Reset filters functionality
    document.getElementById('resetFilters').addEventListener('click', function() {
        const inputs = document.querySelectorAll('#filterForm input:not([name="mobile"]), #filterForm select');
        inputs.forEach(input => {
            if (input.type === 'checkbox') input.checked = false;
            else input.value = '';
        });
    });

    // Select all checkbox functionality
    const selectAll = document.getElementById('selectAll');
    const studentCheckboxes = document.querySelectorAll('.student-checkbox');
    
    selectAll.addEventListener('change', () => {
        studentCheckboxes.forEach(checkbox => checkbox.checked = selectAll.checked);
    });

    // Update selectAll state
    studentCheckboxes.forEach(checkbox => {
        checkbox.addEventListener('change', () => {
            const allChecked = [...studentCheckboxes].every(cb => cb.checked);
            const noneChecked = [...studentCheckboxes].every(cb => !cb.checked);
            selectAll.checked = allChecked;
            selectAll.indeterminate = !allChecked && !noneChecked;
        });
    });

    // Show active filters on load
    const urlParams = new URLSearchParams(window.location.search);
    let activeFilters = 0;
    
    urlParams.forEach((value, key) => {
        if (key !== 'mobile' && value) activeFilters++;
    });

    if (activeFilters > 0) {
        advancedFilters.classList.add('show');
        filterToggle.textContent = 'Hide Filters';
    }
});