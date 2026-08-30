(function () {
  const root = document.documentElement;
  const themeToggle = document.getElementById("themeToggle");

  function applyTheme(theme) {
    root.setAttribute("data-bs-theme", theme);
    localStorage.setItem("theme", theme);
  }

  const savedTheme = localStorage.getItem("theme") || "dark";
  applyTheme(savedTheme);

  if (themeToggle) {
    themeToggle.addEventListener("click", () => {
      const current = root.getAttribute("data-bs-theme") || "dark";
      applyTheme(current === "dark" ? "light" : "dark");
    });
  }

  // Auto-dismiss Flash Alerts
  setTimeout(() => {
    const alerts = document.querySelectorAll('.alert-dismissible');
    alerts.forEach(alertElement => {
      if (typeof bootstrap !== 'undefined') {
        const bsAlert = new bootstrap.Alert(alertElement);
        bsAlert.close();
      } else {
        alertElement.remove();
      }
    });
  }, 500);

  // Luu y: toan bo logic upload/tien trinh nam trong inline script cua templates/index.html.
  // Truoc day file nay dang ky them mot submit handler nua tren cung form,
  // khien moi lan bam gui di 2 request /api/upload va tao 2 job.
})();
