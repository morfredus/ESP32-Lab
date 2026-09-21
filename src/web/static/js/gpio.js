/* ==========================================================================
   ESP32-Lab - GPIO Inspector : cartographie GPIO au niveau puce
   ========================================================================== */

/* Libellés lisibles des statuts d'usage (niveau puce). */
const GPIO_STATUS = {
    available: { label: "Disponible", cls: "gpio-available" },
    restricted: { label: "Disponible avec restrictions", cls: "gpio-restricted" },
    avoid: { label: "A eviter / reserve", cls: "gpio-avoid" }
};

/* État courant des filtres (par catégorie). */
const gpioFilters = {
    strapping: false,
    flash: false,
    special: false,
    input: false,
    exposed: false
};

let lastGpioReport = null;

/* --------------------------- Base Espressif ---------------------------- */

/** Charge et affiche l'état de la base de références Espressif locale. */
async function loadEspressifStatus() {
    const container = document.getElementById("espressif-status");
    if (!container) {
        return;
    }

    try {
        const status = await apiGet("/api/espressif/status");
        renderEspressifStatus(status);
    } catch (error) {
        container.innerHTML =
            `<div class="empty">${escapeHtml(error.message)}</div>`;
    }
}

function renderEspressifStatus(status) {
    const container = document.getElementById("espressif-status");

    const synced = status.synced_at
        ? formatDateTime(status.synced_at)
        : "jamais (base livrée avec l'application)";

    const offline = status.offline_available
        ? '<span class="badge gpio-available">disponible hors ligne</span>'
        : '<span class="badge gpio-avoid">indisponible</span>';

    const integrity = status.integrity_ok
        ? '<span class="badge gpio-available">intègre</span>'
        : '<span class="badge gpio-restricted">à vérifier</span>';

    const families = (status.families || [])
        .map(f => escapeHtml(f.label))
        .join(", ");

    container.innerHTML = `
        <h3>Base Espressif locale</h3>
        <div class="espressif-grid">
            <div><span class="espressif-key">Version du jeu</span>
                <strong>${escapeHtml(orPlaceholder(status.dataset_version))}</strong></div>
            <div><span class="espressif-key">Dernière synchronisation</span>
                ${escapeHtml(synced)}</div>
            <div><span class="espressif-key">Source</span>
                ${escapeHtml(orPlaceholder(status.source))}</div>
            <div><span class="espressif-key">Familles couvertes</span>
                ${families || PLACEHOLDER}</div>
            <div><span class="espressif-key">Statut</span> ${offline} ${integrity}</div>
        </div>
        <div class="espressif-actions">
            <button id="gpio-button" onclick="loadGpio()">
                Utiliser les données locales
            </button>
            <button id="espressif-refresh-button" onclick="refreshEspressif()">
                Actualiser depuis Espressif
            </button>
        </div>
    `;
}

/** Met à jour la base depuis le canal projet (action manuelle). */
async function refreshEspressif() {
    const button = document.getElementById("espressif-refresh-button");
    if (button) {
        button.disabled = true;
        button.textContent = "Actualisation...";
    }

    try {
        const result = await apiPost("/api/espressif/refresh", { force: true });
        setStatus(result.message || "Base Espressif mise à jour.");
    } catch (error) {
        // Échec réseau/intégrité : la base locale reste utilisable.
        setStatus(
            "Mise à jour impossible : " + error.message +
            " La base locale est conservée.",
            true
        );
    } finally {
        if (button) {
            button.disabled = false;
            button.textContent = "Actualiser depuis Espressif";
        }
        await loadEspressifStatus();
    }
}

/* ------------------------------- GPIO ---------------------------------- */

/** Affiche la cartographie GPIO de la carte scannée. */
async function loadGpio() {
    const container = document.getElementById("gpio-content");

    const chip = currentInventory
        && currentInventory.identification
        && currentInventory.identification.chip_family;

    if (!chip) {
        container.innerHTML =
            '<div class="empty">Scanne d\'abord une carte (onglet Général) ' +
            'pour connaître la famille de la puce.</div>';
        return;
    }

    const mac = currentInventory.identification.mac;

    try {
        // Cartes disponibles pour cette famille + carte mémorisée pour cette MAC.
        let boards = [];
        try {
            const list = await apiGet(
                "/api/boards?family=" + encodeURIComponent(chip));
            boards = list.boards || [];
        } catch (error) { /* catalogue absent : on continue sans cartes */ }

        let selectedBoard = "";
        if (mac) {
            try {
                const info = await apiGet(
                    "/api/device?mac=" + encodeURIComponent(mac));
                selectedBoard = (info.device && info.device.board_profile) || "";
            } catch (error) { /* fiche absente : pas de carte mémorisée */ }
        }

        let url = "/api/gpio?chip=" + encodeURIComponent(chip);
        if (selectedBoard) {
            url += "&board=" + encodeURIComponent(selectedBoard);
        }
        // Taille PSRAM detectee : garde-fou de compatibilite (Octal vs quad).
        const psram = currentInventory.identification.psram_size_mb;
        if (psram) {
            url += "&psram=" + encodeURIComponent(psram);
        }

        const report = await apiGet(url);
        lastGpioReport = report;
        renderGpio(report, boards, selectedBoard);
        setStatus("Cartographie GPIO calculée pour " + chip + ".");
    } catch (error) {
        container.innerHTML =
            `<div class="empty">${escapeHtml(error.message)}</div>`;
        setStatus(error.message, true);
    }
}

/** Mémorise la carte choisie (par MAC) puis recharge la cartographie. */
async function selectBoard(boardId) {
    const mac = currentInventory && currentInventory.identification
        && currentInventory.identification.mac;

    if (mac) {
        try {
            await apiPost("/api/device/board", { mac: mac, board: boardId });
        } catch (error) {
            setStatus("Choix de carte non enregistré : " + error.message, true);
        }
    }

    await loadGpio();
}

function gpioStatusBadge(status) {
    const info = GPIO_STATUS[status] || GPIO_STATUS.available;
    return `<span class="badge ${info.cls}">${escapeHtml(info.label)}</span>`;
}

/** Cellule « Sur la carte » (uniquement si un profil de carte est actif). */
function gpioBoardCell(pin) {
    const board = pin.board;
    if (!board) {
        return "";
    }
    if (board.exposure === "onboard") {
        return `<td><span class="badge gpio-onboard">${escapeHtml(
            board.label || board.role || "Fonction carte")}</span></td>`;
    }
    if (board.exposure === "not_exposed") {
        return '<td><span class="gpio-notexposed">Non exposée</span></td>';
    }
    return '<td><span class="gpio-header-pin">Exposée (connecteur)</span></td>';
}

/** Ligne de tableau pour une broche, avec attributs de filtrage. */
function gpioRow(pin, hasBoard) {
    const functions = (pin.functions || [])
        .map(f => `<span class="gpio-chip">${escapeHtml(f)}</span>`)
        .join(" ");

    const note = pin.note
        ? `<div class="gpio-note">${escapeHtml(pin.note)}</div>`
        : "";

    const caveat = pin.boot_caveat
        ? `<div class="gpio-caveat">${escapeHtml(pin.boot_caveat)}</div>`
        : "";

    const exposure = pin.board ? pin.board.exposure : "";

    return `
        <tr data-strapping="${pin.strapping}"
            data-flash="${pin.flash_psram}"
            data-special="${!!(pin.usb_jtag || pin.adc || pin.dac)}"
            data-input="${pin.input_only}"
            data-exposure="${escapeHtml(exposure)}"
            data-status="${escapeHtml(pin.status)}">
            <td class="gpio-num">GPIO${pin.gpio}</td>
            <td>${escapeHtml(pin.classification)}</td>
            <td>${gpioStatusBadge(pin.status)}</td>
            ${hasBoard ? gpioBoardCell(pin) : ""}
            <td>${functions || PLACEHOLDER}</td>
            <td>${note}${caveat}</td>
        </tr>
    `;
}

/** Section repliable d'avertissement (parties à développer). */
function gpioWarningSection(title, text, pins, predicate) {
    const matching = pins.filter(predicate);
    if (!matching.length) {
        return "";
    }

    const list = matching
        .map(p => `<span class="gpio-chip">GPIO${p.gpio}</span>`)
        .join(" ");

    return `
        <details class="efuse-category gpio-section">
            <summary>${escapeHtml(title)} - ${matching.length} broche(s)</summary>
            <div class="gpio-warning">${escapeHtml(text)}</div>
            <div class="gpio-pinlist">${list}</div>
        </details>
    `;
}

/** Sélecteur de carte + contexte d'exposition. */
function gpioBoardSelector(report, boards, selectedBoard) {
    const options = ['<option value="">(carte non définie)</option>']
        .concat((boards || []).map(board =>
            `<option value="${escapeHtml(board.id)}"${
                board.id === selectedBoard ? " selected" : ""
            }>${escapeHtml(board.name)}</option>`))
        .join("");

    let context;
    const exposure = report.board_exposure;
    if (exposure && typeof exposure === "object") {
        const source = exposure.source_url
            ? ` &middot; <a href="${escapeHtml(exposure.source_url)}"
                 target="_blank" rel="noopener">source</a>`
            : "";
        const revision = exposure.revision_note
            ? `<div class="gpio-note">${escapeHtml(exposure.revision_note)}</div>`
            : "";
        const notes = exposure.notes
            ? `<div class="gpio-note">${escapeHtml(exposure.notes)}</div>`
            : "";
        const warning = exposure.warning
            ? `<div class="gpio-board-warning">⚠ ${escapeHtml(
                exposure.warning)}</div>`
            : "";
        context = `<div class="gpio-board-context">
            <strong>${escapeHtml(exposure.name)}</strong>${source}
            ${revision}${notes}${warning}
        </div>`;
    } else {
        context = `<div class="gpio-note">${escapeHtml(
            report.board_exposure_note || "")}</div>`;
    }

    const filter = boards && boards.length
        ? ""
        : `<div class="gpio-note">Aucun profil de carte pour cette famille
             dans la base.</div>`;

    return `
        <div class="gpio-board-select">
            <label>Carte :
                <select onchange="selectBoard(this.value)">${options}</select>
            </label>
            ${context}
            ${filter}
        </div>`;
}

function renderGpio(report, boards, selectedBoard) {
    const container = document.getElementById("gpio-content");

    if (report.family_supported === false) {
        container.innerHTML = `
            <div class="empty">
                ${escapeHtml(report.message || "Famille non couverte.")}
            </div>`;
        return;
    }

    const pins = report.pins || [];
    const summary = report.summary || {};
    const warnings = report.warnings || {};
    const hasBoard = report.board_exposure
        && typeof report.board_exposure === "object";

    const summaryCards = [
        ["available", "Disponibles", summary.available || 0],
        ["restricted", "Avec restrictions", summary.restricted || 0],
        ["avoid", "A éviter / réservés", summary.avoid || 0]
    ].map(([status, label, count]) => `
        <div class="gpio-summary-card ${GPIO_STATUS[status].cls}">
            <div class="gpio-summary-count">${count}</div>
            <div class="gpio-summary-label">${escapeHtml(label)}</div>
        </div>
    `).join("");

    const rows = pins.map(pin => gpioRow(pin, hasBoard)).join("");

    const sections =
        gpioWarningSection(
            "Broches de strapping",
            warnings.strapping || "", pins, p => p.strapping) +
        gpioWarningSection(
            "Broches Flash / PSRAM",
            warnings.flash_psram || "", pins, p => p.flash_psram) +
        gpioWarningSection(
            "Interfaces système (USB-JTAG)",
            warnings.system || "", pins, p => p.usb_jtag) +
        gpioWarningSection(
            "Broches en entrée seule",
            "Ces broches ne peuvent servir qu'en entrée (pas de sortie ni de " +
            "pull-up/pull-down logiciels).", pins, p => p.input_only);

    container.innerHTML = `
        <div class="panel">
            <div class="gpio-header">
                <div>
                    <strong>${escapeHtml(orPlaceholder(report.label
                        || report.chip_family))}</strong>
                    - ${report.gpio_count} GPIO
                </div>
                <div class="gpio-source">
                    Source : ${escapeHtml(orPlaceholder(report.source))}
                    (v${escapeHtml(orPlaceholder(report.dataset_version))})
                </div>
            </div>
            <div class="gpio-summary">${summaryCards}</div>
            ${gpioBoardSelector(report, boards, selectedBoard)}
        </div>

        <div class="panel">
            <div class="gpio-filters">
                <span class="gpio-filters-label">Filtres :</span>
                <label><input type="checkbox" onchange="toggleGpioFilter('strapping', this.checked)"> Strapping</label>
                <label><input type="checkbox" onchange="toggleGpioFilter('flash', this.checked)"> Flash / PSRAM</label>
                <label><input type="checkbox" onchange="toggleGpioFilter('special', this.checked)"> Fonctions spéciales</label>
                <label><input type="checkbox" onchange="toggleGpioFilter('input', this.checked)"> Entrée seule</label>
                ${hasBoard ? '<label><input type="checkbox" onchange="toggleGpioFilter(\'exposed\', this.checked)"> Exposées sur la carte</label>' : ""}
            </div>
            <div class="table-container">
                <table class="gpio-table">
                    <thead>
                        <tr>
                            <th>GPIO</th>
                            <th>Classification</th>
                            <th>Statut</th>
                            ${hasBoard ? "<th>Sur la carte</th>" : ""}
                            <th>Fonctions</th>
                            <th>Notes</th>
                        </tr>
                    </thead>
                    <tbody id="gpio-tbody">${rows}</tbody>
                </table>
            </div>
        </div>

        <div class="panel">
            <h3>Restrictions à connaître</h3>
            <p class="note">Sections à développer pour le détail.</p>
            ${sections}
        </div>
    `;

    container.querySelectorAll("details").forEach(detail => {
        detail.open = false;
    });
}

/** Active/désactive un filtre et réapplique l'affichage des lignes. */
function toggleGpioFilter(name, checked) {
    gpioFilters[name] = checked;

    // Filtres d'union (catégories du niveau puce) et filtre restrictif (carte).
    const unionNames = ["strapping", "flash", "special", "input"];
    const anyUnion = unionNames.some(key => gpioFilters[key]);
    const rows = document.querySelectorAll("#gpio-tbody tr");

    rows.forEach(row => {
        // Sans filtre d'union actif : tout est visible.
        let visible = !anyUnion;

        if (gpioFilters.strapping && row.dataset.strapping === "true") {
            visible = true;
        }
        if (gpioFilters.flash && row.dataset.flash === "true") {
            visible = true;
        }
        if (gpioFilters.special && row.dataset.special === "true") {
            visible = true;
        }
        if (gpioFilters.input && row.dataset.input === "true") {
            visible = true;
        }

        // Restrictif : masque les broches non exposées sur la carte.
        if (gpioFilters.exposed && row.dataset.exposure === "not_exposed") {
            visible = false;
        }

        row.style.display = visible ? "" : "none";
    });
}
