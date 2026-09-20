from pathlib import Path

path = Path("src/web/static/index.html")
html = path.read_text(encoding="utf-8")

marker = '<style id="esp32-tabs-style">'

if marker in html:
    print("[INFO] Le système d'onglets est déjà installé.")
    raise SystemExit(0)

injection = r'''
<style id="esp32-tabs-style">
#esp32-tab-layout {
    width: 100%;
    max-width: 100%;
    margin: 24px 0 0;
}

#esp32-tab-nav {
    position: sticky;
    top: 0;
    z-index: 1000;
    display: flex;
    flex-wrap: wrap;
    gap: 6px;
    padding: 12px 0;
    margin-bottom: 18px;
    background: #f3f4f6;
    border-bottom: 1px solid #d1d5db;
}

.esp32-tab-button {
    border: 1px solid #cbd5e1;
    border-radius: 7px;
    padding: 10px 18px;
    background: #e5e7eb;
    color: #1f2937;
    font-size: 14px;
    font-weight: 600;
    cursor: pointer;
}

.esp32-tab-button:hover {
    background: #dbeafe;
}

.esp32-tab-button.active {
    background: #2563eb;
    border-color: #2563eb;
    color: white;
}

.esp32-tab-panel {
    display: none;
    width: 100%;
    max-width: 100%;
    min-width: 0;
}

.esp32-tab-panel.active {
    display: block;
}

.esp32-tab-panel > * {
    max-width: 100%;
    box-sizing: border-box;
}

#esp32-tab-layout table {
    max-width: 100%;
}

@media (max-width: 700px) {
    #esp32-tab-nav {
        gap: 4px;
    }

    .esp32-tab-button {
        flex: 1 1 auto;
        padding: 9px 10px;
        font-size: 12px;
    }
}
</style>

<script id="esp32-tabs-script">
(function installEsp32Tabs() {
    function setup() {
        if (document.getElementById("esp32-tab-layout")) {
            return;
        }

        const main = document.querySelector("main");
        if (!main) {
            return;
        }

        const headings = Array.from(main.children)
            .filter(element => element.tagName === "H2");

        function findHeading(text) {
            return headings.find(heading =>
                heading.textContent.trim()
                    .toLowerCase()
                    .includes(text.toLowerCase())
            );
        }

        const inventoryHeading =
            findHeading("Inventaire matériel actuel");

        const nvsHeading =
            findHeading("Analyse NVS");

        const historyHeading =
            findHeading("Historique des inventaires");

        if (!inventoryHeading || !nvsHeading || !historyHeading) {
            console.error(
                "Impossible de construire les onglets : titres introuvables."
            );
            return;
        }

        const children = Array.from(main.children);

        function getRange(startElement, endElement) {
            const startIndex = children.indexOf(startElement);
            const endIndex = endElement
                ? children.indexOf(endElement)
                : children.length;

            if (startIndex < 0) {
                return [];
            }

            return children.slice(
                startIndex,
                endIndex >= 0 ? endIndex : children.length
            );
        }

        const generalElements = getRange(
            inventoryHeading,
            nvsHeading
        );

        const nvsElements = getRange(
            nvsHeading,
            historyHeading
        );

        const historyElements = getRange(
            historyHeading,
            null
        );

        const layout = document.createElement("div");
        layout.id = "esp32-tab-layout";

        const nav = document.createElement("nav");
        nav.id = "esp32-tab-nav";
        nav.setAttribute("aria-label", "Navigation ESP32-Lab");

        const panels = document.createElement("div");
        panels.id = "esp32-tab-panels";

        const definitions = [
            {
                id: "general",
                label: "Général",
                elements: generalElements
            },
            {
                id: "memory",
                label: "Mémoire & Flash",
                elements: []
            },
            {
                id: "nvs",
                label: "NVS",
                elements: nvsElements
            },
            {
                id: "history",
                label: "Historique",
                elements: historyElements
            }
        ];

        function activateTab(tabId) {
            document.querySelectorAll(".esp32-tab-button")
                .forEach(button => {
                    const active = button.dataset.tab === tabId;
                    button.classList.toggle("active", active);
                    button.setAttribute("aria-selected", String(active));
                });

            document.querySelectorAll(".esp32-tab-panel")
                .forEach(panel => {
                    panel.classList.toggle(
                        "active",
                        panel.dataset.panel === tabId
                    );
                });
        }

        definitions.forEach((definition, index) => {
            const button = document.createElement("button");
            button.type = "button";
            button.className = "esp32-tab-button";
            button.dataset.tab = definition.id;
            button.textContent = definition.label;
            button.setAttribute("role", "tab");

            button.addEventListener("click", () => {
                activateTab(definition.id);
            });

            nav.appendChild(button);

            const panel = document.createElement("section");
            panel.className = "esp32-tab-panel";
            panel.dataset.panel = definition.id;
            panel.setAttribute("role", "tabpanel");

            definition.elements.forEach(element => {
                panel.appendChild(element);
            });

            panels.appendChild(panel);
        });

        const flashPartition = document.getElementById(
            "flash-partition-view"
        );

        if (flashPartition) {
            const memoryPanel = panels.querySelector(
                '[data-panel="memory"]'
            );

            if (memoryPanel) {
                memoryPanel.appendChild(flashPartition);
            }
        }

        const firstGeneralElement = generalElements[0];

        if (firstGeneralElement) {
            main.insertBefore(layout, firstGeneralElement);
        } else {
            main.appendChild(layout);
        }

        layout.appendChild(nav);
        layout.appendChild(panels);

        activateTab("general");

        document.querySelectorAll("button").forEach(button => {
            if (
                button.textContent.trim() ===
                "Actualiser l'inventaire"
            ) {
                button.textContent = "Scanner la carte";
            }
        });

        console.log("[OK] Navigation par onglets installée.");
    }

    if (document.readyState === "loading") {
        document.addEventListener("DOMContentLoaded", setup);
    } else {
        setup();
    }
})();
</script>
'''

html = html.replace("</head>", injection + "\n</head>", 1)

html = html.replace(
    "Actualiser l'inventaire",
    "Scanner la carte"
)

path.write_text(html, encoding="utf-8")

print("[OK] Navigation par onglets ajoutée.")
print("[OK] Bouton renommé en : Scanner la carte")
print("[OK] Sauvegarde effectuée avant modification.")
