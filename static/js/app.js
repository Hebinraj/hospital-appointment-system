// Hospital Appointment System - Frontend Interactions

document.addEventListener("DOMContentLoaded", () => {
  // 1. Auto-dismiss alerts after 5 seconds
  const alerts = document.querySelectorAll(".alert");
  alerts.forEach((alert) => {
    setTimeout(() => {
      alert.style.transition = "opacity 0.4s ease";
      alert.style.opacity = "0";
      setTimeout(() => alert.remove(), 400);
    }, 5000);
  });

  // 2. Table search filtering
  const searchInputs = document.querySelectorAll(".search-input");
  searchInputs.forEach((input) => {
    input.addEventListener("input", (e) => {
      const query = e.target.value.toLowerCase().trim();
      const tableId = e.target.getAttribute("data-table");
      const table = document.getElementById(tableId);
      if (!table) return;

      const rows = table.querySelectorAll("tbody tr");
      rows.forEach((row) => {
        const text = row.textContent.toLowerCase();
        row.style.display = text.includes(query) ? "" : "none";
      });
    });
  });

  // 3. Modal close buttons
  document.querySelectorAll("[data-close-modal]").forEach((btn) => {
    btn.addEventListener("click", () => {
      const modal = btn.closest(".modal-backdrop");
      if (modal) {
        modal.classList.remove("show");
      }
    });
  });

  // Close modal when clicking backdrop
  document.querySelectorAll(".modal-backdrop").forEach((backdrop) => {
    backdrop.addEventListener("click", (e) => {
      if (e.target === backdrop) {
        backdrop.classList.remove("show");
      }
    });
  });

  // Close modal with Escape key
  document.addEventListener("keydown", (e) => {
    if (e.key === "Escape") {
      document.querySelectorAll(".modal-backdrop.show").forEach((m) => {
        m.classList.remove("show");
      });
    }
  });
});

// Helper to open a modal by ID
function openModal(modalId) {
  const modal = document.getElementById(modalId);
  if (modal) {
    modal.classList.add("show");
    // Focus first input if available
    const firstInput = modal.querySelector("input, select, textarea");
    if (firstInput) {
      firstInput.focus();
    }
  }
}

// Helper to close a modal by ID
function closeModal(modalId) {
  const modal = document.getElementById(modalId);
  if (modal) {
    modal.classList.remove("show");
  }
}

// Helper to open delete confirmation
function confirmDelete(formAction, itemName) {
  const modal = document.getElementById("deleteConfirmModal");
  if (!modal) return;
  const form = document.getElementById("deleteForm");
  const nameSpan = document.getElementById("deleteItemName");
  if (form) form.action = formAction;
  if (nameSpan) nameSpan.textContent = itemName || "this record";
  openModal("deleteConfirmModal");
}
