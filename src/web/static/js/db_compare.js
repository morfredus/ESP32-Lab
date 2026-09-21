/* ==========================================================================
   ESP32-Lab - comparaison complète de deux cartes (base de données)
   ========================================================================== */

/* --- Export / Import de la base ------------------------------------------- */

async function exportDatabase() {
    try {
        const data = await apiGet("/api/db/export");
        const blob = new Blob([JSON.stringify(data, null, 2)],
            { type: "application/json" });
        const url = URL.createObjectURL(blob);
        const link = document.createElement("a");

        link.href = url;
        link.download =
            `esp32lab-export-${new Date().toISOString().slice(0, 10)}.json`;
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
        URL.revokeObjectURL(url);

        setStatus(
            `Base exportée : ${data.devices.length} carte(s), ` +
            `${data.readings.length} lecture(s).`
        );
    } catch (error) {
        setStatus("Export impossible : " + error.message, true);
    }
}

function showMaintenanceMessage(html, isError = false) {
    const container = document.getElementById("db-maintenance-content");
    if (container) {
        const cls = isError ? "error" : "status";
        container.innerHTML = `<div class="${cls}" style="margin-top:12px;">${html}</div>`;
    }
}

async function importDatabase(input) {
    const file = input.files && input.files[0];
    if (!file) {
        return;
    }

    showMaintenanceMessage(
        `Import de « ${escapeHtml(file.name)} » ` +
        `(${escapeHtml(formatBytes(file.size))}) en cours...`
    );
    setStatus("Import de la base en cours...");

    let text;
    try {
        text = await file.text();
    } catch (error) {
        showMaintenanceMessage(
            "Lecture du fichier impossible : " + escapeHtml(error.message), true);
        input.value = "";
        return;
    }

    let payload;
    try {
        payload = JSON.parse(text);
    } catch (error) {
        showMaintenanceMessage(
            "Le fichier n'est pas un JSON valide : " + escapeHtml(error.message),
            true);
        input.value = "";
        return;
    }

    try {
        const result = await apiPost("/api/db/import", payload);
        const summary = result.summary || {};
        const updated = summary.devices_updated || 0;
        const message =
            `Import terminé : <strong>${summary.devices_added || 0}</strong> ` +
            `carte(s) ajoutée(s)` +
            (updated
                ? `, <strong>${updated}</strong> fiche(s) complétée(s)`
                : "") +
            ` et <strong>${summary.readings_added || 0}</strong> ` +
            `lecture(s) ajoutée(s).`;
        showMaintenanceMessage(message);
        setStatus("Import terminé.");
        await loadHistory();
        await loadDevices();
        // Rafraîchit la fiche affichée pour que les noms importés apparaissent.
        if (typeof showInventoryForSelectedPort === "function") {
            await showInventoryForSelectedPort();
        }
    } catch (error) {
        showMaintenanceMessage(
            "Import refusé : " + escapeHtml(error.message), true);
        setStatus("Import impossible : " + error.message, true);
    } finally {
        input.value = "";
    }
}

async function verifyDatabase() {
    const container = document.getElementById("db-maintenance-content");
    container.innerHTML = '<div class="empty">Vérification...</div>';

    try {
        const v = await apiGet("/api/db/verify");
        const sections = Object.entries(v.readings_by_section || {})
            .map(([s, n]) => `${escapeHtml(s)} : ${n}`).join(" · ") || "aucune";

        container.innerHTML = `
            <div class="panel">
                <p>Intégrité :
                    <span class="badge ${v.healthy ? "badge-on" : "badge-off"}">
                        ${v.healthy ? "OK" : escapeHtml(v.integrity)}</span>
                </p>
                <p>Cartes : <strong>${v.devices}</strong> ·
                   Lectures : <strong>${v.readings_total}</strong>
                   (${sections})</p>
                <p>Fichier : <code>${escapeHtml(v.db_path)}</code>
                   (${escapeHtml(formatBytes(v.db_size_bytes))})</p>
            </div>`;
        setStatus("Base vérifiée.");
    } catch (error) {
        container.innerHTML =
            `<div class="empty">${escapeHtml(error.message)}</div>`;
        setStatus("Vérification impossible : " + error.message, true);
    }
}

async function resetDatabase() {
    const confirmed = window.confirm(
        "Effacer DÉFINITIVEMENT toutes les cartes et toutes les lectures de la " +
        "base ? Cette action est irréversible.\n\n" +
        "Conseil : exporte la base d'abord."
    );
    if (!confirmed) {
        return;
    }

    try {
        await apiPost("/api/db/reset");
        setStatus("Base remise à zéro.");
        document.getElementById("db-maintenance-content").innerHTML = "";
        await loadHistory();
        await loadDevices();
    } catch (error) {
        setStatus("Remise à zéro impossible : " + error.message, true);
    }
}

function populateCompareSelectors() {
    const selectA = document.getElementById("compare-card-a");
    const selectB = document.getElementById("compare-card-b");

    if (!selectA || !selectB) {
        return;
    }

    const previousA = selectA.value;
    const previousB = selectB.value;

    const options = Object.values(devicesData || {}).map(device => {
        const label = device.name
            ? `${device.name} (${device.mac})`
            : device.mac;
        return `<option value="${escapeHtml(device.mac)}">${escapeHtml(label)}</option>`;
    }).join("");

    const placeholder = '<option value="">- choisir une carte -</option>';
    selectA.innerHTML = placeholder + options;
    selectB.innerHTML = placeholder + options;

    selectA.value = previousA;
    selectB.value = previousB;
}

async function compareTwoCards() {
    const macA = document.getElementById("compare-card-a").value;
    const macB = document.getElementById("compare-card-b").value;
    const container = document.getElementById("compare-cards-content");

    if (!macA || !macB) {
        container.innerHTML =
            '<div class="empty">Choisis deux cartes à comparer.</div>';
        return;
    }

    if (macA === macB) {
        container.innerHTML =
            '<div class="empty">Choisis deux cartes différentes.</div>';
        return;
    }

    container.innerHTML = '<div class="empty">Comparaison en cours...</div>';

    try {
        const result = await apiGet(
            "/api/db/compare?mac_a=" + encodeURIComponent(macA) +
            "&mac_b=" + encodeURIComponent(macB)
        );
        renderCardComparison(result);
    } catch (error) {
        container.innerHTML =
            `<div class="empty">${escapeHtml(error.message)}</div>`;
    }
}

const SECTION_LABELS = {
    inventory: "Identification",
    efuse: "eFuses",
    sfdp: "SFDP",
    partitions: "Partitions",
    nvs: "NVS"
};

function capturedBadges(captured) {
    return Object.keys(SECTION_LABELS).map(section => {
        const has = captured && captured[section];
        return `<span class="badge ${has ? "badge-on" : "badge-off"}">
            ${escapeHtml(SECTION_LABELS[section])}</span>`;
    }).join(" ");
}

/* --- Détection de changement de secrets (empreintes HMAC) ----------------- */

const SECRET_STATUS = {
    changed: { label: "Changé", cls: "different" },
    added: { label: "Nouveau", cls: "different" },
    removed: { label: "Disparu", cls: "different" },
    indeterminable: { label: "Indéterminable", cls: "" },
    unchanged: { label: "Inchangé", cls: "same" }
};

async function detectSecretChanges(mac) {
    const container = document.getElementById("secret-changes-content");
    if (!container) {
        return;
    }
    container.innerHTML = '<div class="empty">Analyse des empreintes...</div>';

    try {
        const result = await apiGet(
            "/api/db/changes?mac=" + encodeURIComponent(mac));
        renderSecretChanges(result, container);
    } catch (error) {
        container.innerHTML =
            `<div class="empty">${escapeHtml(error.message)}</div>`;
    }
}

function renderSecretChanges(result, container) {
    const sections = (result.sections || []).map(section => {
        if (!section.available) {
            return `
                <h3>${escapeHtml(section.label)}</h3>
                <div class="empty">${escapeHtml(section.message)}</div>`;
        }

        if (section.changes.length === 0) {
            return `
                <h3>${escapeHtml(section.label)}</h3>
                <div class="empty">Aucun secret suivi sur cette carte.</div>`;
        }

        const rows = section.changes.map(change => {
            const meta = SECRET_STATUS[change.status]
                || { label: change.status, cls: "" };
            return `
                <tr class="${meta.cls ? "row-" + meta.cls : ""}">
                    <td>${escapeHtml(change.key)}</td>
                    <td class="${meta.cls}">${escapeHtml(meta.label)}</td>
                </tr>`;
        }).join("");

        return `
            <h3>${escapeHtml(section.label)}
                <small>${escapeHtml(formatDateTime(section.old.recorded_at))}
                → ${escapeHtml(formatDateTime(section.new.recorded_at))}</small>
            </h3>
            <table class="comparison-table">
                <thead><tr><th>Secret (clé)</th><th>État</th></tr></thead>
                <tbody>${rows}</tbody>
            </table>`;
    }).join("");

    const totals = result.totals || {};
    const alert = (totals.changed || 0) + (totals.added || 0)
        + (totals.removed || 0);
    const banner = alert > 0
        ? `<span class="comparison-count-different">${alert} changement(s) détecté(s)</span>`
        : `<span class="comparison-count-same">Aucun changement de secret</span>`;

    container.innerHTML = `
        <div class="comparison-summary" style="margin-top:12px;">
            <strong>Suivi des secrets - ${escapeHtml(result.name)}</strong>
            <div class="comparison-counts">${banner}</div>
            <p class="selection-info" style="margin-top:8px;">
                Comparaison des deux dernières analyses, par empreinte HMAC.
                Les secrets ne sont jamais stockés ; seule l'empreinte permet
                de repérer un changement.
            </p>
        </div>
        ${sections}
    `;
}

function renderCardComparison(result) {
    const container = document.getElementById("compare-cards-content");

    const groups = result.groups.map(group => {
        const rows = group.rows.map(row => {
            let cls = "";
            let verdict = "-";
            if (row.comparable) {
                cls = row.same ? "row-same" : "row-different";
                verdict = row.same
                    ? '<span class="same">Identique</span>'
                    : '<span class="different">Différent</span>';
            }
            return `
                <tr class="${cls}">
                    <td>${escapeHtml(row.label)}</td>
                    <td>${escapeHtml(row.a)}</td>
                    <td>${escapeHtml(row.b)}</td>
                    <td>${verdict}</td>
                </tr>
            `;
        }).join("");

        return `
            <h3>${escapeHtml(group.title)}
                <small>(${group.different} diff. / ${group.same} idem)</small>
            </h3>
            <table class="comparison-table">
                <thead>
                    <tr>
                        <th>Caractéristique</th>
                        <th>${escapeHtml(result.a.name)}</th>
                        <th>${escapeHtml(result.b.name)}</th>
                        <th>Résultat</th>
                    </tr>
                </thead>
                <tbody>${rows}</tbody>
            </table>
        `;
    }).join("");

    container.innerHTML = `
        <div class="comparison-summary">
            <strong>Comparaison de deux cartes</strong>
            <div class="comparison-counts">
                <span class="comparison-count-different">
                    ${result.summary.different} différence(s)
                </span>
                <span class="comparison-count-same">
                    ${result.summary.same} caractéristique(s) identique(s)
                </span>
            </div>
            <p class="selection-info" style="margin-top:10px;">
                ${escapeHtml(result.a.name)} - données : ${capturedBadges(result.a.captured)}<br>
                ${escapeHtml(result.b.name)} - données : ${capturedBadges(result.b.captured)}
            </p>
        </div>
        ${groups}
    `;
}
