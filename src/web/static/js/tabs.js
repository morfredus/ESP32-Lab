/* ==========================================================================
   ESP32-Lab - navigation par onglets
   ========================================================================== */

function showTab(tabId) {
    document.querySelectorAll(".tabs button").forEach(button => {
        button.classList.toggle("active", button.dataset.tab === tabId);
    });

    document.querySelectorAll(".tab-panel").forEach(panel => {
        panel.classList.toggle("active", panel.dataset.panel === tabId);
    });
}

function initTabs() {
    document.querySelectorAll(".tabs button").forEach(button => {
        button.addEventListener("click", () => showTab(button.dataset.tab));
    });

    const first = document.querySelector(".tabs button");
    if (first) {
        showTab(first.dataset.tab);
    }
}
