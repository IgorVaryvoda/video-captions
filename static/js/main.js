/**
 * Main JavaScript for Video Captions App
 */

document.addEventListener('DOMContentLoaded', function () {
  // Add current year to footer
  document.querySelectorAll('footer .container').forEach(footer => {
    const yearSpan = document.createElement('span');
    yearSpan.textContent = new Date().getFullYear();
    footer.innerHTML = footer.innerHTML.replace('{{ now.year }}', yearSpan.textContent);
  });

  // Enable Bootstrap tooltips
  const tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
  tooltipTriggerList.map(function (tooltipTriggerEl) {
    return new bootstrap.Tooltip(tooltipTriggerEl);
  });

  // Enable file input validation
  const fileInputs = document.querySelectorAll('input[type="file"]');
  fileInputs.forEach(input => {
    input.addEventListener('change', function () {
      const maxSize = 500 * 1024 * 1024; // 500MB
      const file = this.files[0];

      if (file && file.size > maxSize) {
        alert('Error: File size exceeds the 500MB limit.');
        this.value = '';
      }
    });
  });

  // Highlight active navigation link
  const currentPath = window.location.pathname;
  document.querySelectorAll('.navbar-nav .nav-link').forEach(link => {
    const href = link.getAttribute('href');
    if (href === currentPath ||
      (href !== '/' && currentPath.startsWith(href))) {
      link.classList.add('active');
    }
  });
});