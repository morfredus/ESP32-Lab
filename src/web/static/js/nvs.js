/* ==========================================================================
   ESP32-Lab — analyse de la structure NVS

   Toutes les valeurs affichées proviennent du rapport d'analyse réel
   (data/analysis/reports/nvs_structure_analysis.json). Aucune donnée n'est
   inventée : on indique la présence d'une clé et sa valeur décodée
   lorsqu'elle est disponible, sinon « Non détecté » ou « Présent (non décodé) ».
   ========================================================================== */

const NVS_STATE_LABELS = {
    full: "Pleine",
    active: "Active",
    empty_or_uninitialized: "Non initialisée"
};

async function loadNvsAnalysis() {
    const button = document.getElementById("nvs-button");
    const container = document.getElementById("nvs-content");

    button.disabled = true;
    button.textContent = "Chargement...";

    try {
        const result = await apiGet("/api/nvs");
        const report = result.report || {};
        const pages = report.pages || [];

        const writtenEntries = pages.flatMap(page =>
            (page.entries || [])
                .filter(entry => entry.state
                    && entry.state.name === "written" && entry.decoded)
                .map(entry => entry.decoded)
        );

        container.innerHTML =
            renderNvsSummary(writtenEntries) +
            renderNvsMeta(report) +
            renderNvsPages(pages) +
            "<h3>Détail des entrées NVS</h3>" +
            renderNvsDetails(pages);

        container.querySelectorAll("details").forEach(detail => {
            detail.open = false;
        });
    } catch (error) {
        container.innerHTML =
            `<div class="empty">${escapeHtml(error.message)}</div>`;
    } finally {
        button.disabled = false;
        button.textContent = "Actualiser l'analyse NVS";
    }
}

function renderNvsSummary(entries) {
    const byKey = key => entries.find(entry => entry.key === key);
    const has = key => Boolean(byKey(key));

    /* Valeur brute (champ data hexadécimal) telle que stockée. */
    const raw = key => {
        const entry = byKey(key);
        if (!entry) {
            return "Non détecté";
        }
        return entry.data_hex ? entry.data_hex : "Présent";
    };

    /* Valeur lisible décodée selon le type de l'entrée. */
    const human = key => {
        const entry = byKey(key);
        return entry ? decodeNvsHuman(entry) : "Non détecté";
    };

    const secret = key =>
        has(key) ? "Présent (masqué)" : "Non détecté";

    /* [libellé, valeur brute, valeur lisible] */
    const definitions = [
        ["SSID Wi-Fi station", raw("sta.ssid"), human("sta.ssid")],
        ["SSID point d'accès", raw("ap.ssid"), human("ap.ssid")],
        ["Mot de passe station", secret("sta.pswd"), secret("sta.pswd")],
        ["Mot de passe point d'accès", secret("ap.passwd"), secret("ap.passwd")],
        ["Canal station", raw("sta.chan"), human("sta.chan")],
        ["Canal point d'accès", raw("ap.chan"), human("ap.chan")],
        ["Compteur de démarrages", raw("bl_boot_count"), human("bl_boot_count")],
        ["Compteur de crashs", raw("bl_crash_count"), human("bl_crash_count")],
        ["Version calibration", raw("cal_version"), human("cal_version")]
    ];

    const rows = definitions.map(([label, rawValue, humanValue]) => `
        <tr>
            <td>${escapeHtml(label)}</td>
            <td><code>${escapeHtml(rawValue)}</code></td>
            <td><strong>${escapeHtml(humanValue)}</strong></td>
        </tr>
    `).join("");

    return `
        <section class="nvs-summary" style="margin-bottom:24px;">
            <h3>Résumé des données détectées</h3>
            <p class="note">
                Valeurs issues du rapport d'analyse réel. La colonne
                « Valeur lisible » décode le type (entier, chaîne, binaire) ;
                les clés absentes du dump sont marquées « Non détecté ».
            </p>
            <table>
                <thead>
                    <tr>
                        <th>Paramètre</th>
                        <th>Valeur brute</th>
                        <th>Valeur lisible</th>
                    </tr>
                </thead>
                <tbody>${rows}</tbody>
            </table>
        </section>
    `;
}

function renderNvsMeta(report) {
    return `
        <div class="info-grid">
            <div><strong>Fichier :</strong> ${escapeHtml(report.file || PLACEHOLDER)}</div>
            <div><strong>Taille :</strong> ${escapeHtml(report.size_bytes ?? PLACEHOLDER)} octets</div>
            <div><strong>Taille page :</strong> ${escapeHtml(report.page_size_bytes ?? PLACEHOLDER)} octets</div>
            <div><strong>Nombre de pages :</strong> ${escapeHtml(report.page_count ?? PLACEHOLDER)}</div>
        </div>
    `;
}

function renderNvsPages(pages) {
    const rows = pages.map(page => {
        const counts = page.entry_counts || {};
        const stateLabel = NVS_STATE_LABELS[page.state_name]
            || page.state_name || PLACEHOLDER;

        const sequence =
            page.state_name === "empty_or_uninitialized"
                || page.sequence === 4294967295
                ? PLACEHOLDER : page.sequence;

        let crc = PLACEHOLDER;
        if (page.state_name === "empty_or_uninitialized") {
            crc = "Non initialisée";
        } else if (page.header_crc_match === true) {
            crc = "OK";
        } else if (page.header_crc_match === false) {
            crc = "Incohérent";
        }

        return `
            <tr>
                <td>${escapeHtml(page.page_index)}</td>
                <td>${escapeHtml(page.offset || PLACEHOLDER)}</td>
                <td>${escapeHtml(stateLabel)}</td>
                <td>${escapeHtml(sequence)}</td>
                <td>${escapeHtml(counts.written ?? PLACEHOLDER)}</td>
                <td>${escapeHtml(counts.erased ?? PLACEHOLDER)}</td>
                <td>${escapeHtml(counts.empty ?? PLACEHOLDER)}</td>
                <td>${escapeHtml(crc)}</td>
            </tr>
        `;
    }).join("");

    return `
        <div class="panel">
            <table>
                <thead>
                    <tr>
                        <th>Page</th><th>Offset</th><th>État</th><th>Séquence</th>
                        <th>Écrites</th><th>Effacées</th><th>Vides</th><th>CRC header</th>
                    </tr>
                </thead>
                <tbody>${rows}</tbody>
            </table>
        </div>
    `;
}

function renderNvsDetails(pages) {
    return pages.map(page => {
        const entries = (page.entries || []).filter(
            entry => entry.state && entry.state.name === "written");

        if (entries.length === 0) {
            return `
                <details class="nvs-page-details">
                    <summary>Page ${escapeHtml(page.page_index)} - aucune entrée exploitable</summary>
                </details>
            `;
        }

        const entryRows = entries.map(entry => {
            const decoded = entry.decoded || {};
            const crc = decoded.crc_match === true ? "OK"
                : decoded.crc_match === false ? "Incohérent" : PLACEHOLDER;

            return `
                <tr>
                    <td>${escapeHtml(entry.index ?? PLACEHOLDER)}</td>
                    <td>${escapeHtml(entry.offset || PLACEHOLDER)}</td>
                    <td>${escapeHtml(decoded.key || PLACEHOLDER)}</td>
                    <td>${escapeHtml(decoded.type_name || PLACEHOLDER)}</td>
                    <td>${escapeHtml(decoded.span ?? PLACEHOLDER)}</td>
                    <td>${escapeHtml(crc)}</td>
                    <td><code>${escapeHtml(decoded.data_hex || PLACEHOLDER)}</code></td>
                    <td><strong>${escapeHtml(decodeNvsHuman(decoded))}</strong></td>
                </tr>
            `;
        }).join("");

        return `
            <details class="nvs-page-details">
                <summary>Page ${escapeHtml(page.page_index)} - ${entries.length} entrée(s) écrite(s)</summary>
                <div class="table-container">
                    <table>
                        <thead>
                            <tr>
                                <th>Index</th><th>Offset</th><th>Clé</th><th>Type</th>
                                <th>Span</th><th>CRC</th><th>Données hexadécimales</th>
                                <th>Valeur lisible</th>
                            </tr>
                        </thead>
                        <tbody>${entryRows}</tbody>
                    </table>
                </div>
            </details>
        `;
    }).join("");
}
