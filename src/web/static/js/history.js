/* ==========================================================================
   ESP32-Lab — historique des inventaires et comparaison
   ========================================================================== */

async function loadHistory() {
    try {
        const result = await apiGet("/api/inventory/history");
        historyData = result.history || [];
        historyByMac = {};

        historyData.forEach(entry => {
            const info = (entry.inventory || {}).identification || {};
            const mac = (info.mac || "inconnu").toLowerCase();
            (historyByMac[mac] = historyByMac[mac] || []).push(entry);
        });

        const uniqueDevices = Object.entries(historyByMac).map(
            ([mac, entries]) => {
                entries.sort((a, b) =>
                    new Date(b.recorded_at) - new Date(a.recorded_at));
                return { mac, latest: entries[0] };
            }
        );

        if (uniqueDevices.length === 0) {
            historyContent.innerHTML =
                '<div class="empty">Aucun inventaire disponible.</div>';
            updateSelectionInfo();
            return;
        }

        const rows = uniqueDevices.map(device => {
            const inventory = device.latest.inventory || {};
            const info = inventory.identification || {};
            const historyIndex = historyData.indexOf(device.latest);
            const isChecked = selectedHistoryIndexes.has(historyIndex)
                ? "checked" : "";

            return `
                <tr>
                    <td class="checkbox-cell">
                        <input type="checkbox" class="history-selection-checkbox"
                               data-history-index="${historyIndex}" ${isChecked}
                               onchange="handleHistorySelection(Number(this.dataset.historyIndex), this.checked)">
                    </td>
                    <td><strong>${escapeHtml(deviceName(info.mac || device.mac) || "Sans nom")}</strong></td>
                    <td>${escapeHtml(formatDateTime(device.latest.recorded_at))}</td>
                    <td>${escapeHtml(info.chip || PLACEHOLDER)}</td>
                    <td>${escapeHtml(info.mac || device.mac)}</td>
                    <td>${escapeHtml(formatUnit(info.flash_size_mb, "Mo"))}</td>
                    <td>${escapeHtml(formatUnit(info.psram_size_mb, "Mo"))}</td>
                    <td>${escapeHtml(inventory.port || PLACEHOLDER)}</td>
                    <td>
                        <button class="history-details-button"
                                onclick="showDeviceHistory('${escapeHtml(device.mac)}')">
                            Voir l'historique
                        </button>
                    </td>
                </tr>
            `;
        }).join("");

        historyContent.innerHTML = `
            <table>
                <thead>
                    <tr>
                        <th class="checkbox-cell">Choix</th>
                        <th>Nom</th>
                        <th>Dernière détection</th>
                        <th>ESP32</th>
                        <th>MAC</th>
                        <th>Flash</th>
                        <th>PSRAM</th>
                        <th>Port</th>
                        <th>Historique</th>
                    </tr>
                </thead>
                <tbody>${rows}</tbody>
            </table>
        `;

        updateSelectionInfo();
    } catch (error) {
        historyContent.innerHTML =
            `<div class="empty">${escapeHtml(error.message)}</div>`;
    }
}

function updateSelectionInfo() {
    const count = selectedHistoryIndexes.size;
    selectionInfo.textContent = `${count}/2 inventaire(s) sélectionné(s)`;
    compareButton.disabled = count !== 2;
    compareButton.setAttribute("aria-disabled", count !== 2 ? "true" : "false");
}

function handleHistorySelection(index, checked) {
    if (checked) {
        if (selectedHistoryIndexes.size >= 2) {
            const checkbox = document.querySelector(
                `input[data-history-index="${index}"]`);
            if (checkbox) {
                checkbox.checked = false;
            }
            setStatus("Tu peux sélectionner seulement deux inventaires.", true);
            return;
        }
        selectedHistoryIndexes.add(index);
    } else {
        selectedHistoryIndexes.delete(index);
    }
    updateSelectionInfo();
}

/* --- Modale historique par carte ----------------------------------------- */

function showDeviceHistory(mac) {
    const entries = historyByMac[mac.toLowerCase()] || [];
    const modal = document.getElementById("history-modal");
    const title = document.getElementById("history-modal-title");
    const content = document.getElementById("history-modal-content");

    const label = deviceName(mac);
    title.textContent = label
        ? `Historique - ${label} (${mac})`
        : "Historique - " + mac;

    const rows = entries.map(entry => {
        const inventory = entry.inventory || {};
        const info = inventory.identification || {};
        const historyIndex = historyData.indexOf(entry);
        const isChecked = historyModalSelectedIndexes.has(historyIndex)
            ? "checked" : "";

        return `
            <tr>
                <td>
                    <input type="checkbox" class="history-modal-checkbox"
                           data-history-index="${historyIndex}" ${isChecked}
                           onchange="updateHistoryModalSelection(${historyIndex}, this.checked)">
                </td>
                <td>${escapeHtml(formatDateTime(entry.recorded_at))}</td>
                <td>${escapeHtml(info.chip || PLACEHOLDER)}</td>
                <td>${escapeHtml(inventory.port || PLACEHOLDER)}</td>
                <td>${escapeHtml(info.revision || PLACEHOLDER)}</td>
                <td>${escapeHtml(formatUnit(info.flash_size_mb, "Mo"))}</td>
                <td>${escapeHtml(formatUnit(info.psram_size_mb, "Mo"))}</td>
            </tr>
        `;
    }).join("");

    content.innerHTML = `
        <p>${entries.length} détection(s) enregistrée(s).</p>
        <button id="compare-history-selections" class="primary-button" disabled
                onclick="compareSelectedHistoryEntries()">
            Comparer les deux détections sélectionnées
        </button>
        <table>
            <thead>
                <tr>
                    <th>Choix</th><th>Date</th><th>ESP32</th><th>Port</th>
                    <th>Révision</th><th>Flash</th><th>PSRAM</th>
                </tr>
            </thead>
            <tbody>${rows}</tbody>
        </table>
    `;

    modal.style.display = "block";
}

function updateHistoryModalSelection(index, checked) {
    if (checked) {
        if (historyModalSelectedIndexes.size >= 2) {
            const first = historyModalSelectedIndexes.values().next().value;
            historyModalSelectedIndexes.delete(first);
        }
        historyModalSelectedIndexes.add(index);
    } else {
        historyModalSelectedIndexes.delete(index);
    }

    const button = document.getElementById("compare-history-selections");
    if (button) {
        button.disabled = historyModalSelectedIndexes.size !== 2;
    }
}

function compareSelectedHistoryEntries() {
    if (historyModalSelectedIndexes.size !== 2) {
        return;
    }

    selectedHistoryIndexes = new Set(historyModalSelectedIndexes);

    document.querySelectorAll(".history-selection-checkbox").forEach(checkbox => {
        const index = Number(checkbox.dataset.historyIndex);
        checkbox.checked = selectedHistoryIndexes.has(index);
    });

    updateSelectionInfo();
    closeDeviceHistory();
    showTab("inventory");
    compareInventories();
}

function closeDeviceHistory() {
    document.getElementById("history-modal").style.display = "none";
}

/* --- Comparaison ---------------------------------------------------------- */

function toggleDifferencesOnly() {
    showDifferencesOnly = document.getElementById("differences-only").checked;
    if (selectedHistoryIndexes.size === 2) {
        compareInventories();
    }
}

function compareInventories() {
    if (selectedHistoryIndexes.size !== 2) {
        setStatus("Sélectionne exactement deux inventaires.", true);
        return;
    }

    const indexes = [...selectedHistoryIndexes];
    const firstEntry = historyData[indexes[0]];
    const secondEntry = historyData[indexes[1]];
    const firstInventory = firstEntry.inventory;
    const secondInventory = secondEntry.inventory;
    const firstInfo = firstInventory.identification || {};
    const secondInfo = secondInventory.identification || {};
    const firstDate = formatDateTime(firstEntry.recorded_at);
    const secondDate = formatDateTime(secondEntry.recorded_at);
    const firstName = deviceLabel(firstInfo.mac);
    const secondName = deviceLabel(secondInfo.mac);

    function comparisonValue(info, inventory, key, formatter) {
        let value = key === null ? inventory.port : info[key];
        if (formatter) {
            value = formatter(value);
        }
        return (value === null || value === undefined || value === "")
            ? PLACEHOLDER : String(value);
    }

    const mhz = value => value == null ? null : `${value} MHz`;
    const mo = value => value == null ? null : `${value} Mo`;

    const fields = [
        ["Puce", "chip"],
        ["Révision", "revision"],
        ["Fonctionnalités", "features"],
        ["CPU", "cpu_frequency_mhz", mhz],
        ["Quartz", "crystal_frequency_mhz", mhz],
        ["PSRAM", "psram_size_mb", mo],
        ["PSRAM disponible", "psram"],
        ["Flash", "flash_size_mb", mo],
        ["Type Flash", "flash_type"],
        ["Tension Flash", "flash_voltage"],
        ["Fabricant Flash", "flash_manufacturer", flashManufacturerLabel],
        ["Référence Flash", "flash_device", flashDeviceLabel],
        ["MAC", "mac"],
        ["Port série", null]
    ];

    let differentCount = 0;
    let sameCount = 0;

    const rows = fields.map(([label, key, formatter]) => {
        const firstText = comparisonValue(firstInfo, firstInventory, key, formatter);
        const secondText = comparisonValue(secondInfo, secondInventory, key, formatter);
        const same = firstText === secondText;

        if (same) {
            sameCount++;
        } else {
            differentCount++;
        }

        if (showDifferencesOnly && same) {
            return "";
        }

        return `
            <tr class="comparison-row ${same ? "row-same" : "row-different"}">
                <td>${escapeHtml(label)}</td>
                <td>${escapeHtml(firstText)}</td>
                <td>${escapeHtml(secondText)}</td>
                <td class="${same ? "same" : "different"}">
                    ${same ? "Identique" : "Différent"}
                </td>
            </tr>
        `;
    }).join("");

    const visibleRows = rows.trim() ? rows : `
        <tr><td colspan="4" class="same">Aucune différence détectée.</td></tr>
    `;

    comparisonContent.classList.remove("empty");
    comparisonContent.innerHTML = `
        <div class="comparison-summary">
            <strong>Comparaison de deux inventaires</strong>
            <p>
                <strong>${escapeHtml(firstName)}</strong> : ${escapeHtml(firstDate)}<br>
                <strong>${escapeHtml(secondName)}</strong> : ${escapeHtml(secondDate)}
            </p>
            <div class="comparison-counts">
                <span class="comparison-count-different">${differentCount} différence(s)</span>
                <span class="comparison-count-same">${sameCount} caractéristique(s) identique(s)</span>
            </div>
        </div>
        <table class="comparison-table">
            <thead>
                <tr>
                    <th>Caractéristique</th>
                    <th>${escapeHtml(firstName)}<br><small>${escapeHtml(firstDate)}</small></th>
                    <th>${escapeHtml(secondName)}<br><small>${escapeHtml(secondDate)}</small></th>
                    <th>Résultat</th>
                </tr>
            </thead>
            <tbody>${visibleRows}</tbody>
        </table>
    `;

    comparisonContent.scrollIntoView({ behavior: "smooth", block: "start" });
}

/* --- Export CSV ----------------------------------------------------------- */

function exportHistoryCsv() {
    if (historyData.length === 0) {
        setStatus("Aucun inventaire disponible pour l'export.", true);
        return;
    }

    const headers = [
        "Date", "Port", "Puce", "Revision", "CPU MHz", "Quartz MHz",
        "PSRAM Mo", "Flash Mo", "Type Flash", "Tension Flash", "MAC",
        "Fabricant Flash", "Reference Flash"
    ];

    const rows = historyData.map(entry => {
        const inventory = entry.inventory;
        const info = inventory.identification;
        return [
            entry.recorded_at, inventory.port, info.chip, info.revision,
            info.cpu_frequency_mhz, info.crystal_frequency_mhz,
            info.psram_size_mb, info.flash_size_mb, info.flash_type,
            info.flash_voltage, info.mac, info.flash_manufacturer,
            info.flash_device
        ];
    });

    const csvValue = value => {
        if (value === null || value === undefined) {
            return "";
        }
        return `"${String(value).replace(/"/g, '""')}"`;
    };

    const csv = [
        headers.map(csvValue).join(";"),
        ...rows.map(row => row.map(csvValue).join(";"))
    ].join("\n");

    const blob = new Blob(["﻿" + csv], { type: "text/csv;charset=utf-8;" });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");

    link.href = url;
    link.download = `esp32-inventory-${new Date().toISOString().slice(0, 10)}.csv`;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    URL.revokeObjectURL(url);

    setStatus("Historique exporté au format CSV.");
}
