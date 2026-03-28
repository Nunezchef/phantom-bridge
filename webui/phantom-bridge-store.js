import { createStore } from "/js/AlpineStore.js";

export const store = createStore("phantomBridge", {
    running: false,
    connectUrl: "",
    authEntries: [],
    authCount: 0,
    sitemapEntries: [],
    sitemapCount: 0,
    playbooks: [],
    playbookCount: 0,

    _pollInterval: null,

    init() {},

    async onOpen() {
        await this.fetchStatus();
        this._pollInterval = setInterval(() => this.fetchStatus(), 10000);
    },

    cleanup() {
        if (this._pollInterval) {
            clearInterval(this._pollInterval);
            this._pollInterval = null;
        }
    },

    async fetchStatus() {
        try {
            // Bridge status
            const statusResp = await fetch("/plugin/phantom_bridge/api/bridge", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ action: "status" }),
            });
            if (statusResp.ok) {
                const data = await statusResp.json();
                this.running = data.running || false;
                this.connectUrl = data.connect_url || "";
            }

            // Auth registry
            const authResp = await fetch("/plugin/phantom_bridge/api/bridge", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ action: "auth_registry" }),
            });
            if (authResp.ok) {
                const data = await authResp.json();
                const registry = data.registry || {};
                this.authEntries = Object.entries(registry).map(([domain, entry]) => ({
                    domain,
                    authenticated: entry.authenticated,
                    expires: entry.expires_at ? `expires ${new Date(entry.expires_at).toLocaleDateString()}` : "no expiry",
                }));
                this.authCount = this.authEntries.length;
            }

            // Sitemaps
            const smResp = await fetch("/plugin/phantom_bridge/api/bridge", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ action: "sitemaps" }),
            });
            if (smResp.ok) {
                const data = await smResp.json();
                const sitemaps = data.sitemaps || {};
                this.sitemapEntries = Object.entries(sitemaps).map(([domain, sm]) => ({
                    domain,
                    features: Object.keys(sm.features || {}).length,
                }));
                this.sitemapCount = this.sitemapEntries.length;
            }

            // Playbooks
            const pbResp = await fetch("/plugin/phantom_bridge/api/bridge", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ action: "playbooks" }),
            });
            if (pbResp.ok) {
                const data = await pbResp.json();
                this.playbooks = data.playbooks || [];
                this.playbookCount = this.playbooks.length;
            }
        } catch (e) {
            // API not ready yet
        }
    },

    async startBridge() {
        try {
            const resp = await fetch("/plugin/phantom_bridge/api/bridge", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ action: "start" }),
            });
            if (resp.ok) {
                await this.fetchStatus();
            }
        } catch (e) {
            console.error("Failed to start bridge:", e);
        }
    },

    async stopBridge() {
        try {
            const resp = await fetch("/plugin/phantom_bridge/api/bridge", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ action: "stop" }),
            });
            if (resp.ok) {
                this.running = false;
                await this.fetchStatus();
            }
        } catch (e) {
            console.error("Failed to stop bridge:", e);
        }
    },

    openBridge() {
        // Open CDP inspect page in new tab
        // Uses the host's port mapping — user needs 9222 exposed
        // or we proxy through A0's port
        const url = this.connectUrl || "http://localhost:9222";
        window.open(url, "_blank");
    },
});
