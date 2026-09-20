from pathlib import Path

path = Path("src/web/static/index.html")
html = path.read_text(encoding="utf-8")

marker = '<!-- ESP32-LAB-TABS-V1 -->'

if marker in html:
    print("[INFO] Onglets déjà installés.")
    raise SystemExit(0)

injection = r'''
<!-- ESP32-LAB-TABS-V1 -->

<style>
    /* Navigation principale */
    #esp32-tabs-nav {
        position: sticky;
        top: 0;
        z-index: 1000;
        display: flex;
        flex-wrap: wrap;
        gap: 8px;
        padding: 12px 0;
        margin: 12px 0 24px;
        background: #f3f4f6;
        border-bottom: 1px solid #d1d5db;
    }

    .esp32-tab-button {
        border: 1px solid #cbd5e1;
        border-radius: 7px;
        padding: 10px 18px;
        background: #e5e7eb;
        color: #1f2937;
        cursor: pointer;
        font-size: 14px;
        font-weight: 600;
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
        min-width: 0;
        box-sizing: border-box;
    }

    .esp32-tab-panel.active {
        display: block;
    }

    .esp32-tab-panel > * {
        max-width: 100%;
        box-sizing: border-box;
    }

    @media (max-width: 700px) {
        #esp32-tabs-nav {
            gap: 5px;
        }

        .esp32-tab-button {
            flex: 1 1 auto;
            padding: 9px 10px;
            font-size: 12px;
        }
    }
</style>

<script>
(function installEsp32Tabs() {
    function setup() {
        const main = document.querySelector("main");

        if (!main || document.getElementById("esp32-tabs-nav")) {
            return;
        }

        const directChildren = Array.from(main.children);

        const headings = directChildren.filter(
            element => element.tagName === "H2"
        );

        const partitionSection = main.querySelector(
            "#flash-partition-view"
        );

        if (headings.length === 0) {
            console.error("ESP32-Lab : aucun titre H2 trouvé.");
            return;
        }

        const panels = {
            general: document.createElement("div"),
            nvs: document.createElement("div"),
            memory: document.createElement("div"),
            history: document.createElement("div")
        };

        panels.general.className = "esp32-tab-panel active";
        panels.nvs.className = "esp32-tab-panel";
        panels.memory.className = "esp32-tab-panel";
        panels.history.className = "esp32-tab-panel";

        panels.general.dataset.tabPanel = "general";
        panels.nvs.dataset.tabPanel = "nvs";
        panels.memory.dataset.tabPanel = "memory";
        panels.history.dataset.tabPanel = "history";

        function normalize(text) {
            return text
                .toLowerCase()
                .normalize("NFD")
                .replace(/[\\u0300-\\u036f]/g, "")
                .trim();
        }

        function targetPanel(title) {
            const value = normalize(title);

            if (
                value.includes("analyse nvs")
            ) {
                return panels.nvs;
            }

            if (
                value.includes("historique des inventaires") ||
                value.includes("comparaison")
            ) {
                return panels.history;
            }

            if (
                value.includes("partitionnement") ||
                value.includes("memoire flash")
            ) {
                return panels.memory;
            }

            return panels.general;
        }

        const ranges = [];

        headings.forEach((heading, index) => {
            const start = directChildren.indexOf(heading);
            const nextHeading = headings[index + 1];
            const end = nextHeading
                ? directChildren.indexOf(nextHeading)
                : directChildren.length;

            ranges.push({
                heading,
                nodes: directChildren.slice(start, end),
                panel: targetPanel(heading.textContent)
            });
        });

        const firstHeading = headings[0];

        const nav = document.createElement("nav");
        nav.id = "esp32-tabs-nav";
        nav.setAttribute("aria-label", "Navigation ESP32-Lab");

        const tabDefinitions = [
            ["general", "Général"],
            ["nvs", "NVS"],
            ["memory", "Mémoire Flash"],
            ["history", "Historique"]
        ];

        function activateTab(name) {
            Object.entries(panels).forEach(([key, panel]) => {
                panel.classList.toggle("active", key === name);
            });

            nav.querySelectorAll("button").forEach(button => {
                const active = button.dataset.tab === name;
                button.classList.toggle("active", active);
                button.setAttribute("aria-selected", active ? "true" : "false");
            });
        }

        tabDefinitions.forEach(([name, label]) => {
            const button = document.createElement("button");

            button.type = "button";
            button.className = "esp32-tab-button";
            button.dataset.tab = name;
            button.textContent = label;
            button.setAttribute("role", "tab");
            button.setAttribute("aria-selected", name === "general" ? "true" : "false");

            button.addEventListener("click", () => {
                activateTab(name);
            });

            nav.appendChild(button);
        });

        main.insertBefore(nav, firstHeading);

        Object.values(panels).forEach(panel => {
            main.insertBefore(panel, firstHeading);
        });

        ranges.forEach(range => {
            range.nodes.forEach(node => {
                if (node.parentElement === main) {
                    range.panel.appendChild(node);
                }
            });
        });

        if (partitionSection && partitionSection.parentElement === main) {
            panels.memory.appendChild(partitionSection);
        }

        activateTab("general");

        console.log("ESP32-Lab : navigation par onglets installée.");
    }

    if (document.readyState === "loading") {
        document.addEventListener("DOMContentLoaded", setup);
    } else {
        setup();
    }
})();
</script>
'''

html = html.replace("</body>", injection + "\n</body>")
path.write_text(html, encoding="utf-8")

print("[OK] Navigation par onglets installée.")
print("[OK] Sauvegarde : src/web/static/index.html.backup-tabs")
