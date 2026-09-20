from pathlib import Path

path = Path("src/web/static/index.html")
html = path.read_text(encoding="utf-8")

if "flash-partition-view" in html:
    print("[INFO] Vue du partitionnement déjà présente.")
    raise SystemExit(0)

css = r"""
<style>
#flash-partition-view {
    margin-top: 24px;
}

.flash-partition-bar {
    display: flex;
    width: 100%;
    height: 58px;
    border-radius: 8px;
    overflow: hidden;
    border: 1px solid #cbd5e1;
    background: #e5e7eb;
}

.flash-partition-segment {
    display: flex;
    align-items: center;
    justify-content: center;
    min-width: 2px;
    overflow: hidden;
    border-right: 1px solid white;
    color: #111827;
    font-size: 11px;
    font-weight: 600;
    text-align: center;
    cursor: default;
}

.flash-partition-segment span {
    padding: 3px;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
}

.flash-partition-legend {
    width: 100%;
    border-collapse: collapse;
    margin-top: 14px;
    font-size: 12px;
}

.flash-partition-legend th,
.flash-partition-legend td {
    padding: 7px 8px;
    border-bottom: 1px solid #e5e7eb;
    text-align: left;
}

.flash-partition-color {
    display: inline-block;
    width: 12px;
    height: 12px;
    border-radius: 3px;
    vertical-align: middle;
    margin-right: 6px;
}
</style>
"""

section = r"""
<section id="flash-partition-view">
    <h2>Partitionnement de la mémoire Flash</h2>
    <p>
        ESP32-S3 - Flash détectée : <strong>16 MiB</strong>.
        Représentation basée sur la table des partitions lue à l'adresse <code>0x8000</code>.
    </p>

    <div class="flash-partition-bar" id="flash-partition-bar"></div>

    <table class="flash-partition-legend">
        <thead>
            <tr>
                <th>Partition</th>
                <th>Adresse</th>
                <th>Taille</th>
                <th>Type</th>
                <th>Fin</th>
            </tr>
        </thead>
        <tbody id="flash-partition-rows"></tbody>
    </table>
</section>

<script>
(function renderFlashPartitionView() {
    const partitions = [
        {
            name: "NVS",
            address: 0x9000,
            size: 0x5000,
            type: "Données",
            subtype: "nvs",
            color: "#93c5fd"
        },
        {
            name: "otadata",
            address: 0xE000,
            size: 0x2000,
            type: "Données",
            subtype: "ota",
            color: "#c4b5fd"
        },
        {
            name: "app0",
            address: 0x10000,
            size: 0x640000,
            type: "Application",
            subtype: "ota_0",
            color: "#86efac"
        },
        {
            name: "app1",
            address: 0x650000,
            size: 0x640000,
            type: "Application",
            subtype: "ota_1",
            color: "#4ade80"
        },
        {
            name: "spiffs",
            address: 0xC90000,
            size: 0x360000,
            type: "Données",
            subtype: "spiffs / LittleFS",
            color: "#fcd34d"
        },
        {
            name: "coredump",
            address: 0xFF0000,
            size: 0x10000,
            type: "Données",
            subtype: "coredump",
            color: "#fca5a5"
        }
    ];

    const flashSize = 0x1000000;
    const bar = document.getElementById("flash-partition-bar");
    const rows = document.getElementById("flash-partition-rows");

    if (!bar || !rows) {
        return;
    }

    const formatHex = value =>
        "0x" + value.toString(16).toUpperCase().padStart(6, "0");

    const formatSize = bytes => {
        if (bytes >= 1024 * 1024) {
            return (bytes / (1024 * 1024)).toFixed(3).replace(".", ",") + " MiB";
        }

        return Math.round(bytes / 1024) + " KiB";
    };

    partitions.forEach(partition => {
        const end = partition.address + partition.size;
        const width = (partition.size / flashSize) * 100;

        const segment = document.createElement("div");
        segment.className = "flash-partition-segment";
        segment.style.width = width + "%";
        segment.style.backgroundColor = partition.color;
        segment.title =
            partition.name + " - " +
            formatHex(partition.address) + " - " +
            formatSize(partition.size);

        const label = document.createElement("span");
        label.textContent = partition.name;
        segment.appendChild(label);
        bar.appendChild(segment);

        const row = document.createElement("tr");
        row.innerHTML = `
            <td>
                <span class="flash-partition-color"
                      style="background:${partition.color}"></span>
                ${partition.name}
            </td>
            <td><code>${formatHex(partition.address)}</code></td>
            <td>${formatSize(partition.size)}</td>
            <td>${partition.type} (${partition.subtype})</td>
            <td><code>${formatHex(end)}</code></td>
        `;

        rows.appendChild(row);
    });
})();
</script>
"""

html = html.replace("</head>", css + "\n</head>", 1)
html = html.replace("</body>", section + "\n</body>", 1)

path.write_text(html, encoding="utf-8")
print("[OK] Vue du partitionnement ajoutée.")
