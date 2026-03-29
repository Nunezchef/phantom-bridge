import { createStore } from "/js/AlpineStore.js";

async function api(endpoint, body = {}) {
    const { callJsonApi } = await import("/js/api.js");
    return await callJsonApi(`plugins/phantom_bridge/${endpoint}`, body);
}

export const store = createStore("phantomBridge", {
    running: false,
    novncUrl: "",
    novncReady: false,
    novncPort: 6080,
    authEntries: [],
    authCount: 0,
    cookieDomains: [],
    cookieTotal: 0,
    sitemapEntries: [],
    sitemapCount: 0,
    playbooks: [],
    playbookCount: 0,

    _pollInterval: null,

    init() {},

    async onOpen() {
        await this.fetchStatus();
        this._pollInterval = setInterval(() => this.fetchStatus(), 5000);
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
            this.novncReady = status.novnc_running || false;
            this.novncUrl = status.novnc_url || "";
            this.novncPort = status.novnc_port || 6080;

            // Auto-export cookies to get fresh counts
            if (this.running) {
                await api("bridge", { action: "export_cookies" });
            }

            // Cookie domains
            const cookieData = await api("bridge", { action: "cookies" });
            const cookies = cookieData.cookies || {};
            this.cookieDomains = Object.entries(cookies).map(([domain, info]) => ({
                domain,
                count: info.count || 0,
            })).sort((a, b) => b.count - a.count);
            this.cookieTotal = this.cookieDomains.reduce((sum, d) => sum + d.count, 0);

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
            const { toastFrontendInfo } = await import("/components/notifications/notification-store.js");
            toastFrontendInfo("Starting bridge...", "Phantom Bridge");
            await api("bridge", { action: "start" });
            await this.fetchStatus();
        } catch (e) {
            const { toastFrontendError } = await import("/components/notifications/notification-store.js");
            toastFrontendError("Failed to start bridge: " + e.message, "Phantom Bridge");
        }
    },

    async stopBridge() {
        try {
            await api("bridge", { action: "stop" });
            this.running = false;
            this.novncReady = false;
            await this.fetchStatus();
        } catch (e) {
            const { toastFrontendError } = await import("/components/notifications/notification-store.js");
            toastFrontendError("Failed to stop bridge: " + e.message, "Phantom Bridge");
        }
    },

    async deleteAllCookies() {
        try {
            const { toastFrontendInfo, toastFrontendSuccess } = await import("/components/notifications/notification-store.js");
            toastFrontendInfo("Deleting all cookies...", "Phantom Bridge");
            await api("bridge", { action: "delete_cookies" });
            toastFrontendSuccess("All cookies deleted", "Phantom Bridge");
            await this.fetchStatus();
        } catch (e) {
            const { toastFrontendError } = await import("/components/notifications/notification-store.js");
            toastFrontendError("Failed to delete cookies: " + e.message, "Phantom Bridge");
        }
    },

    openBridge() {
        const host = location.hostname || "localhost";
        const url = `http://${host}:${this.novncPort}/vnc.html?autoconnect=true&resize=scale&reconnect=true`;
        window.open(url, "phantom-bridge");
    },
});
