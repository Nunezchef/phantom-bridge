import { createStore } from "/js/AlpineStore.js";

async function api(endpoint, body = {}) {
    const { callJsonApi } = await import("/js/api.js");
    return await callJsonApi(`plugins/phantom_bridge/${endpoint}`, body);
}

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
            const status = await api("bridge", { action: "status" });
            this.running = status.running || false;
            this.connectUrl = status.connect_url || "";

            const auth = await api("bridge", { action: "auth_registry" });
            const registry = auth.registry || {};
            this.authEntries = Object.entries(registry).map(([domain, entry]) => ({
                domain,
                authenticated: entry.authenticated,
                expires: entry.expires_at ? `expires ${new Date(entry.expires_at).toLocaleDateString()}` : "no expiry",
            }));
            this.authCount = this.authEntries.length;

            const sm = await api("bridge", { action: "sitemaps" });
            const sitemaps = sm.sitemaps || {};
            this.sitemapEntries = Object.entries(sitemaps).map(([domain, s]) => ({
                domain,
                features: Object.keys(s.features || {}).length,
            }));
            this.sitemapCount = this.sitemapEntries.length;

            const pb = await api("bridge", { action: "playbooks" });
            this.playbooks = pb.playbooks || [];
            this.playbookCount = this.playbooks.length;
        } catch (e) {
            // API not ready yet
        }
    },

    async startBridge() {
        try {
            await api("bridge", { action: "start" });
            await this.fetchStatus();
        } catch (e) {
            console.error("Failed to start bridge:", e);
        }
    },

    async stopBridge() {
        try {
            await api("bridge", { action: "stop" });
            this.running = false;
            await this.fetchStatus();
        } catch (e) {
            console.error("Failed to stop bridge:", e);
        }
    },

    openBridge() {
        window.open("/usr/plugins/phantom_bridge/webui/bridge.html", "_blank");
    },
});
