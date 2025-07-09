/**
 * Equipment Management JavaScript
 * Handles AJAX data loading, pagination, search
 */

document.addEventListener("DOMContentLoaded", function() {
  // Store current state
  const state = {
    currentPage: 1,
    itemsPerPage: 20,
    searchTerm: "",
    totalPages: 1,
  };

  // DOM Elements
  const searchInput = document.getElementById("searchEquipment");
  const searchButton = searchInput.nextElementSibling;
  const equipmentTable = document.querySelector("table tbody");
  const paginationContainer = document.querySelector(".pagination");
  const itemsPerPageSelect = document.querySelector(".show-entries select");

  // Initialize
  loadEquipmentData();
  setupEventListeners();

  /**
   * Fetch equipment data from the server
   */
  function loadEquipmentData() {
    const url = `${URLs.getEquipmentData}?page=${encodeURIComponent(
      state.currentPage
    )}&items_per_page=${encodeURIComponent(
      state.itemsPerPage
    )}&search_term=${encodeURIComponent(state.searchTerm)}`;

    fetch(url)
      .then(response => response.json())
      .then(data => {
        if (data.status === "success") {
          renderEquipmentTable(data.equipment);
          updatePagination(data.pagination);
          state.totalPages = data.pagination.total_pages;
        } else {
          showMessage("Error loading equipment data", "error");
        }
      })
      .catch(error => {
        console.error("Error fetching equipment data:", error);
        showMessage("Failed to load equipment data", "error");
      });
  }

  /**
   * Render equipment data in the table
   */
  function renderEquipmentTable(equipmentList) {
    equipmentTable.innerHTML = "";

    if (equipmentList.length === 0) {
      // Show no results message
      const row = document.createElement("tr");
      const cell = document.createElement("td");
      cell.colSpan = fields.length;
      cell.textContent = "No equipment found";
      cell.className = "text-center";
      row.appendChild(cell);
      equipmentTable.appendChild(row);
      return;
    }

    equipmentList.forEach(equipment => {
      const row = document.createElement("tr");
      row.dataset.id = equipment.id;
      row.style.cursor = "pointer"; // Add pointer cursor to indicate clickable

      // Add a click event to the row to view details
      row.addEventListener("click", () => {
        window.location.href = `${URLs.detailsPrefix}/${equipment.id}`;
      });

      fields.forEach(field => {
        const cell = document.createElement("td");

        // Handle special case for category which is a reference
        if (field === "category" && equipment.category_name) {
          cell.textContent = equipment.category_name;
        } else {
          cell.textContent = equipment[field] || "";
        }

        row.appendChild(cell);
      });

      equipmentTable.appendChild(row);
    });
  }

  /**
   * Update pagination controls
   */
  function updatePagination(pagination) {
    const { total_pages, current_page } = pagination;
    const ul = paginationContainer;
    ul.innerHTML = "";

    // Previous button
    addPaginationItem(ul, "&lt;", current_page > 1, () => {
      if (current_page > 1) {
        state.currentPage = current_page - 1;
        loadEquipmentData();
      }
    });

    // Calculate which page numbers to show
    let startPage = Math.max(1, current_page - 2);
    let endPage = Math.min(total_pages, startPage + 4);

    // Adjust if we're near the end
    if (endPage - startPage < 4 && startPage > 1) {
      startPage = Math.max(1, endPage - 4);
    }

    // First page if not included in range
    if (startPage > 1) {
      addPaginationItem(ul, "1", true, () => {
        state.currentPage = 1;
        loadEquipmentData();
      });
      if (startPage > 2) {
        addPaginationItem(ul, "...", false);
      }
    }

    // Page numbers
    for (let i = startPage; i <= endPage; i++) {
      addPaginationItem(
        ul,
        i.toString(),
        true,
        () => {
          state.currentPage = i;
          loadEquipmentData();
        },
        i === current_page
      );
    }

    // Last page if not included in range
    if (endPage < total_pages) {
      if (endPage < total_pages - 1) {
        addPaginationItem(ul, "...", false);
      }
      addPaginationItem(ul, total_pages.toString(), true, () => {
        state.currentPage = total_pages;
        loadEquipmentData();
      });
    }

    // Next button
    addPaginationItem(ul, "&gt;", current_page < total_pages, () => {
      if (current_page < total_pages) {
        state.currentPage = current_page + 1;
        loadEquipmentData();
      }
    });
  }

  /**
   * Helper to create pagination items
   */
  function addPaginationItem(
    parent,
    text,
    clickable,
    clickHandler,
    isActive = false
  ) {
    const li = document.createElement("li");
    li.className = `page-item ${isActive ? "active" : ""} ${
      !clickable ? "disabled" : ""
    }`;

    const a = document.createElement("a");
    a.className = "page-link";
    a.innerHTML = text;
    a.href = clickable ? "#" : "javascript:void(0)";

    if (clickable && clickHandler) {
      a.addEventListener("click", (e) => {
        e.preventDefault();
        clickHandler();
      });
    }

    li.appendChild(a);
    parent.appendChild(li);
  }

  /**
   * Set up event listeners
   */
  function setupEventListeners() {
    // Search input
    searchInput.addEventListener("keyup", (e) => {
      if (e.key === "Enter") {
        state.searchTerm = searchInput.value;
        state.currentPage = 1; // Reset to first page when searching
        loadEquipmentData();
      }
    });

    searchButton.addEventListener("click", () => {
      state.searchTerm = searchInput.value;
      state.currentPage = 1;
      loadEquipmentData();
    });

    // Items per page selector
    itemsPerPageSelect.addEventListener("change", () => {
      state.itemsPerPage = parseInt(itemsPerPageSelect.value);
      state.currentPage = 1; // Reset to first page when changing items per page
      loadEquipmentData();
    });
  }

  /**
   * Display a message to the user
   */
  function showMessage(message, type = "info") {
    // Create alert element
    const alertDiv = document.createElement("div");
    alertDiv.className = `alert alert-${type} alert-dismissible fade show`;
    alertDiv.role = "alert";
    alertDiv.innerHTML = `
      ${message}
      <button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button>
    `;

    // Find container to show message
    const container = document.querySelector(".equipment-overview-container");
    container.insertBefore(alertDiv, container.firstChild);

    // Auto-dismiss after 5 seconds
    setTimeout(() => {
      const alert = bootstrap.Alert.getOrCreateInstance(alertDiv);
      alert.close();
    }, 5000);
  }
});
