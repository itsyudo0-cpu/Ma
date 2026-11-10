/**
 * Mio Ads Telegram Mini App - Core Client Engine
 * Integrates Telegram WebApp API, Dynamic Watermark Theme Adaptor,
 * Persistent PNG Bottom Navigation, and All Ads Ecosystem Modules.
 */

const MioApp = {
  state: {
    user: {
      telegram_id: 100200300,
      username: "crypto_trader_in",
      first_name: "Arjun Sharma",
      role: "user",
      preferred_currency: "USDT",
      language: "en",
      wallet_balance_usdt: 85.50,
      wallet_balance_inr: 6840.00,
      referral_code: "ARJUN77",
      total_referral_clicks: 42,
      is_affiliate_approved: false
    },
    system: {
      platform_fee_percent: 15.0,
      usdt_to_inr_rate: 80.0,
      affiliate_click_rate_usdt: 0.005,
      default_dwell_time_seconds: 60,
      db_status: {}
    },
    activeView: "home",
    theme: "light",
    channels: [],
    campaigns: [],
    tickets: [],
    invoices: [],
    leaderboard: [],
    lockLedger: []
  },

  async init() {
    console.log("[MioApp] Initializing Telegram Mini App Ecosystem...");
    
    // Telegram WebApp SDK initialization if running inside Telegram
    if (window.Telegram && window.Telegram.WebApp) {
      window.Telegram.WebApp.ready();
      window.Telegram.WebApp.expand();
      if (window.Telegram.WebApp.initDataUnsafe && window.Telegram.WebApp.initDataUnsafe.user) {
        const tgUser = window.Telegram.WebApp.initDataUnsafe.user;
        this.state.user.telegram_id = tgUser.id;
        this.state.user.username = tgUser.username || `user_${tgUser.id}`;
        this.state.user.first_name = tgUser.first_name || "Telegram User";
      }
    }

    // Check URL parameters for view or referral
    const urlParams = new URLSearchParams(window.location.search);
    if (urlParams.has("view")) {
      const targetView = urlParams.get("view");
      this.state.activeView = targetView;
    }

    // Load initial data
    await this.fetchUserProfile();
    await this.fetchSystemSettings();
    await this.fetchChannels();
    await this.fetchCampaigns();
    await this.fetchLeaderboard();

    // Render localized UI
    this.applyTheme(this.state.theme);
    this.renderLanguageCards();
    this.switchView(this.state.activeView);
    this.setupEventListeners();

    console.log("[MioApp] Initialized successfully for user:", this.state.user.telegram_id);
  },

  dismissOpeningView() {
    const splash = document.getElementById("opening-view");
    if (splash) {
      splash.classList.add("hidden");
    }
  },

  applyTheme(theme) {
    this.state.theme = theme;
    document.documentElement.setAttribute("data-theme", theme);
    const themeBtn = document.getElementById("theme-toggle-text");
    if (themeBtn) {
      themeBtn.innerText = theme === "dark" ? "☀️ Light" : "🌙 Dark";
    }
  },

  toggleTheme() {
    const nextTheme = this.state.theme === "light" ? "dark" : "light";
    this.applyTheme(nextTheme);
  },

  switchView(viewName) {
    if (viewName === "admin" && (this.state.user.role !== "admin" || !this.adminSession())) {
      this.showAdminLogin();
      viewName = "home";
    }
    this.state.activeView = viewName;

    // Toggle view containers
    document.querySelectorAll(".view-section").forEach(sec => sec.classList.remove("active"));
    const targetSection = document.getElementById(`view-${viewName}`);
    if (targetSection) {
      targetSection.classList.add("active");
    }

    // Toggle persistent bottom nav icons
    document.querySelectorAll(".nav-item").forEach(item => {
      const target = item.getAttribute("data-view");
      const iconImg = item.querySelector(".nav-icon-png");
      if (target === viewName) {
        item.classList.add("active");
        if (iconImg) iconImg.src = `/static/images/icons/${target}_active.png`;
      } else {
        item.classList.remove("active");
        if (iconImg) iconImg.src = `/static/images/icons/${target}.png`;
      }
    });

    // Refresh specific view data
    if (viewName === "stats") this.renderAnalytics();
    if (viewName === "admin") this.renderAdminPanel();
    if (viewName === "support") {
      this.renderTickets();
      const u = document.getElementById("sup-username");
      if (u && !u.value && this.state.user.username) u.value = "@" + this.state.user.username;
    }
    if (viewName === "wallet") this.renderInvoices();
  },

  async fetchUserProfile() {
    try {
      const res = await fetch(`/api/v1/user/profile?telegram_id=${this.state.user.telegram_id}`);
      if (res.ok) {
        const data = await res.json();
        this.state.user = { ...this.state.user, ...data };
        this.updateProfileUI();
      }
    } catch (e) {
      console.warn("[MioApp] Profile fetch fallback:", e);
      this.updateProfileUI();
    }
  },

  async fetchSystemSettings() {
    try {
      const res = await fetch("/api/v1/system/settings");
      if (res.ok) {
        this.state.system = await res.json();
        this.updateSystemUI();
      }
    } catch (e) {
      console.warn("[MioApp] Settings fetch fallback:", e);
    }
  },

  async fetchChannels() {
    try {
      const res = await fetch(`/api/v1/channels/list?telegram_id=${this.state.user.telegram_id}`);
      if (res.ok) {
        this.state.channels = await res.json();
        this.renderChannels();
      }
    } catch (e) {
      console.warn("[MioApp] Channels fetch fallback:", e);
    }
  },

  async fetchCampaigns() {
    try {
      const res = await fetch("/api/v1/campaigns/list");
      if (res.ok) {
        this.state.campaigns = await res.json();
        this.renderCampaigns();
      }
    } catch (e) {
      console.warn("[MioApp] Campaigns fetch fallback:", e);
    }
  },

  async fetchLeaderboard() {
    try {
      const res = await fetch("/api/v1/channels/leaderboard");
      if (res.ok) {
        this.state.leaderboard = await res.json();
        this.renderLeaderboard();
      }
    } catch (e) {
      console.warn("[MioApp] Leaderboard fetch fallback:", e);
    }
  },

  updateProfileUI() {
    const usdtEls = document.querySelectorAll(".val-usdt-balance");
    const inrEls = document.querySelectorAll(".val-inr-balance");
    const idEls = document.querySelectorAll(".val-telegram-id");
    const userEls = document.querySelectorAll(".val-username");
    const refCodeEls = document.querySelectorAll(".val-referral-code");
    const refClicksEls = document.querySelectorAll(".val-referral-clicks");

    usdtEls.forEach(el => el.innerText = `$${parseFloat(this.state.user.wallet_balance_usdt || 0).toFixed(2)} USDT`);
    inrEls.forEach(el => el.innerText = `₹${parseFloat(this.state.user.wallet_balance_inr || 0).toLocaleString('en-IN', { minimumFractionDigits: 2 })} INR`);
    idEls.forEach(el => el.innerText = this.state.user.telegram_id);
    userEls.forEach(el => el.innerText = this.state.user.first_name || this.state.user.username);
    refCodeEls.forEach(el => el.innerText = this.state.user.referral_code || `REF${this.state.user.telegram_id}`);
    refClicksEls.forEach(el => el.innerText = this.state.user.total_referral_clicks || 0);

    const refInput = document.getElementById("referral-url-input");
    if (refInput) {
      refInput.value = `${window.location.origin}/r/${this.state.user.referral_code || this.state.user.telegram_id}`;
    }

    // Role switcher indicator
    const roleBadge = document.getElementById("user-role-badge");
    if (roleBadge) {
      roleBadge.innerText = this.state.user.role.toUpperCase();
      roleBadge.className = this.state.user.role === "admin" ? "brand-tag" : "wallet-rate-badge";
    }

    // Show/hide admin bottom nav tab
    const adminNav = document.querySelector('.nav-item[data-view="admin"]');
    if (adminNav) {
      adminNav.style.display = this.state.user.role === "admin" ? "flex" : "none";
    }
  },

  updateSystemUI() {
    const feeEls = document.querySelectorAll(".val-platform-fee");
    const rateEls = document.querySelectorAll(".val-exchange-rate");
    const affEls = document.querySelectorAll(".val-affiliate-rate");

    feeEls.forEach(el => el.innerText = `${this.state.system.platform_fee_percent}%`);
    rateEls.forEach(el => el.innerText = `1 USDT = ₹${this.state.system.usdt_to_inr_rate} INR`);
    affEls.forEach(el => el.innerText = `$${this.state.system.affiliate_click_rate_usdt} / click`);
    document.querySelectorAll(".val-next-payout").forEach(el => el.innerText = this.state.system.next_payout_date || "—");
  },

  renderCampaigns() {
    const container = document.getElementById("campaigns-list");
    if (!container) return;

    if (!this.state.campaigns.length) {
      container.innerHTML = `<p style="color:var(--text-muted);font-size:0.85rem;text-align:center;padding:20px;">No active campaigns found.</p>`;
      return;
    }

    container.innerHTML = this.state.campaigns.map((c, idx) => {
      const words = String(c.narrative || "").split(/\s+/).filter(Boolean);
      const short = words.slice(0, 7).join(" ") + (words.length > 7 ? "…" : "");
      return `
      <div class="campaign-card">
        <div class="ad-card-title-row">
          <div class="campaign-title">${c.title}</div>
          <span class="campaign-badge ${c.model === 'CPC' ? 'badge-cpc' : 'badge-cpm'}">${c.model} • $${c.bid_usdt}</span>
        </div>
        <p class="ad-card-desc">${short}</p>
        <div class="dwell-timer-box" style="display:none;">
          <div class="dwell-timer-text" id="dwell-notice-text"></div>
          <div class="dwell-countdown-badge" id="dwell-countdown-badge">${c.dwell_time_seconds || 60}s</div>
        </div>
        <button class="ad-click-direct-btn" style="width:100%;" onclick="MioApp.clickAdDirectly('${c.campaign_id}', '${c.target_url}')">
          <span>🚀 Visit Ad</span>
        </button>
      </div>`;
    }).join("");

    // Initialize dwell timer for first ad if present
    if (this.state.campaigns.length > 0 && window.dwellTracker) {
      const first = this.state.campaigns[0];
      window.dwellTracker.initTimer(first.campaign_id, null, first.dwell_time_seconds || 60);
    }
  },

  clickAdDirectly(campaignId, targetUrl) {
    if (window.dwellTracker) {
      window.dwellTracker.clickAdDirectly();
    }
    if (targetUrl) {
      setTimeout(() => {
        window.open(targetUrl, "_blank");
      }, 500);
    }
  },

  fmtNum(n) {
    n = Number(n || 0);
    if (n >= 1e6) return (n / 1e6).toFixed(1).replace(/\.0$/, "") + "M";
    if (n >= 1e3) return (n / 1e3).toFixed(1).replace(/\.0$/, "") + "K";
    return String(n);
  },

  channelCardHTML(c) {
    const idx = this.state.channels.indexOf(c);
    const initial = String(c.title || "?").trim().charAt(0).toUpperCase();
    const st = c.status === "approved" ? "badge-approved" : "badge-pending";
    return `
      <div class="ch-card" onclick="MioApp.openChannelAnalytics(${idx})">
        <div class="ch-avatar">${initial}</div>
        <div class="ch-info">
          <div class="ch-title">${c.title}</div>
          <div class="ch-user">${c.username}</div>
          <span class="${st} ch-status">${String(c.status || "pending").toUpperCase()}</span>
        </div>
        <div class="ch-subs"><b>${this.fmtNum(c.subscribers)}</b><span>subscribers</span></div>
      </div>`;
  },

  renderChannels() {
    const monetizationContainer = document.getElementById("monetization-channels-list");
    const promotionContainer = document.getElementById("promotion-channels-list");
    const mon = this.state.channels.filter(c => c.type === "monetization");
    const pro = this.state.channels.filter(c => c.type === "promotion");
    if (monetizationContainer) {
      monetizationContainer.innerHTML = mon.length ? mon.map(c => this.channelCardHTML(c)).join("")
        : `<p style="color:var(--text-muted);font-size:0.85rem;padding:12px;">No monetization channels linked yet.</p>`;
    }
    if (promotionContainer) {
      promotionContainer.innerHTML = pro.length ? pro.map(c => this.channelCardHTML(c)).join("")
        : `<p style="color:var(--text-muted);font-size:0.85rem;padding:12px;">No promotion channels linked yet.</p>`;
    }
  },

  dailyTableHTML(rows) {
    if (!rows || !rows.length) return `<div class="daily-table"><div class="daily-row"><span>No data yet</span></div></div>`;
    return `<div class="daily-table">${rows.map(r => `<div class="daily-row"><span>${r.label}</span><b>${r.clicks} clicks · ${r.views} views</b></div>`).join("")}</div>`;
  },

  async openChannelAnalytics(idx) {
    const c = this.state.channels[idx];
    if (!c) return;
    document.getElementById("ca-title").innerText = c.title;
    const head = `
      <div style="font-size:0.8rem;color:var(--text-secondary);">${c.username} • ${c.category || ""}</div>
      <div class="stat-grid">
        <div class="stat-tile"><div class="l">Subscribers</div><div class="v">${(c.subscribers || 0).toLocaleString()}</div></div>
        <div class="stat-tile"><div class="l">Total Clicks</div><div class="v">${c.total_clicks || 0}</div></div>
        <div class="stat-tile"><div class="l">Total Views</div><div class="v">${(c.total_views || 0).toLocaleString()}</div></div>
        <div class="stat-tile"><div class="l">Earned</div><div class="v">$${(c.earnings_usdt || 0).toFixed(2)}</div></div>
      </div>
      <h4 style="font-size:0.9rem;font-weight:700;margin:6px 0;">Date-wise Clicks (last 7 days)</h4>`;
    const body = document.getElementById("ca-body");
    body.innerHTML = head + `<div class="daily-table"><div class="daily-row"><span>Loading…</span></div></div>`;
    this.openModal("modal-channel-analytics");
    let rows = [];
    try {
      const res = await fetch(`/api/v1/stats/daily?telegram_id=${this.state.user.telegram_id}&channel_id=${encodeURIComponent(c.channel_id || "")}&days=7`);
      if (res.ok) rows = (await res.json()).days;
    } catch (e) { console.warn("channel daily stats failed:", e); }
    body.innerHTML = head + this.dailyTableHTML(rows);
  },

  renderLeaderboard() {
    const tbody = document.getElementById("leaderboard-body");
    if (!tbody) return;

    if (!this.state.leaderboard.length) {
      tbody.innerHTML = `<tr><td colspan="4" style="text-align:center;padding:16px;color:var(--text-muted);">No rankings available yet.</td></tr>`;
      return;
    }

    // Preserving privacy: Channel Name & Logo only (no external links)
    tbody.innerHTML = this.state.leaderboard.map((item, index) => `
      <tr>
        <td style="font-weight:700;color:var(--accent-cyan);">#${index + 1}</td>
        <td>
          <div style="display:flex;align-items:center;gap:8px;">
            <img src="/static/images/logo.png" style="width:24px;height:24px;border-radius:6px;object-fit:cover;" />
            <span style="font-weight:600;">${item.title}</span>
          </div>
        </td>
        <td>${item.category || 'General'}</td>
        <td style="font-weight:700;">${(item.total_views || 0).toLocaleString()}</td>
      </tr>
    `).join("");
  },

  async renderAnalytics() {
    const container = document.getElementById("publisher-analytics-cards");
    if (!container) return;

    const userChannels = this.state.channels.filter(c => c.type === "monetization");
    const totalViews = userChannels.reduce((sum, c) => sum + (c.total_views || 0), 0);
    const totalEarnings = userChannels.reduce((sum, c) => sum + (c.earnings_usdt || 0), 0);

    let daily = { days: [], today: 0, week: 0, month: 0 };
    try {
      const res = await fetch(`/api/v1/stats/daily?telegram_id=${this.state.user.telegram_id}&days=14`);
      if (res.ok) daily = await res.json();
    } catch (e) { console.warn("daily stats failed:", e); }

    container.innerHTML = `
      <div class="quick-grid">
        <div class="action-card">
          <div class="action-card-desc">Daily Clicks</div>
          <div class="action-card-title" style="color:var(--accent-cyan);font-size:1.3rem;">${daily.today}</div>
        </div>
        <div class="action-card">
          <div class="action-card-desc">Weekly Clicks</div>
          <div class="action-card-title" style="color:var(--accent-cyan);font-size:1.3rem;">${daily.week}</div>
        </div>
        <div class="action-card">
          <div class="action-card-desc">Monthly Clicks</div>
          <div class="action-card-title" style="color:var(--accent-cyan);font-size:1.3rem;">${daily.month}</div>
        </div>
        <div class="action-card">
          <div class="action-card-desc">Total Views</div>
          <div class="action-card-title" style="color:var(--accent-emerald);font-size:1.3rem;">${totalViews.toLocaleString()}</div>
        </div>
      </div>
      <div class="wallet-card" style="margin-top:14px;">
        <div class="wallet-label">Publisher Net Earnings (Post-Fee)</div>
        <div class="wallet-amount-usdt">$${totalEarnings.toFixed(2)} USDT</div>
        <div class="wallet-amount-inr">₹${(totalEarnings * this.state.system.usdt_to_inr_rate).toLocaleString('en-IN', { minimumFractionDigits: 2 })} INR</div>
      </div>
      <h3 style="font-size:0.95rem;font-weight:700;margin:18px 0 6px;">Date-wise Clicks (last 14 days)</h3>
      ${this.dailyTableHTML(daily.days)}
    `;
  },

  // Spec: "Settings UI features flag indicators; active selected language displays in Dark Theme, while inactive languages remain Light Theme."
  renderLanguageCards() {
    const container = document.getElementById("language-cards-grid");
    if (!container || !window.I18N) return;

    const currentLang = this.state.user.language || "en";
    const langs = window.I18N.languages;

    container.innerHTML = Object.keys(langs).map(code => {
      const item = langs[code];
      const isActive = code === currentLang;
      return `
        <div class="lang-card ${isActive ? 'active-lang' : ''}" onclick="MioApp.selectLanguage('${code}')">
          <span class="lang-flag">${item.flag}</span>
          <div>
            <div class="lang-name">${item.native}</div>
            <div class="lang-region">${item.region} • ${item.name}</div>
          </div>
        </div>
      `;
    }).join("");
  },

  async selectLanguage(code) {
    this.state.user.language = code;
    this.renderLanguageCards();
    this.showToast(`Language updated to ${window.I18N.languages[code].name}`);

    // Update on backend
    try {
      await fetch("/api/v1/user/settings/language", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ telegram_id: this.state.user.telegram_id, language: code })
      });
    } catch (e) {
      console.warn("Language update failed:", e);
    }
  },

  async renderInvoices() {
    const list = document.getElementById("invoices-history-list");
    if (!list) return;

    try {
      const res = await fetch(`/api/v1/invoices/list?user_id=${this.state.user.telegram_id}`);
      if (res.ok) {
        const invoices = await res.json();
        if (!invoices.length) {
          list.innerHTML = `<p style="color:var(--text-muted);font-size:0.8rem;text-align:center;padding:12px;">No generated invoices yet.</p>`;
          return;
        }
        list.innerHTML = invoices.map(inv => `
          <div style="display:flex;align-items:center;justify-content:space-between;padding:10px;border-bottom:1px solid var(--border-light);font-size:0.85rem;">
            <div>
              <div style="font-weight:700;">${inv.invoice_id}</div>
              <div style="font-size:0.75rem;color:var(--text-muted);">${inv.date} • ${inv.tx_type}</div>
            </div>
            <div style="text-align:right;">
              <div style="font-weight:700;color:var(--accent-cyan);">$${inv.net_amount_usdt} USDT</div>
              <a href="${inv.web_url}" target="_blank" style="font-size:0.75rem;color:var(--accent-blue);text-decoration:none;">📄 Download PDF</a>
            </div>
          </div>
        `).join("");
      }
    } catch (e) {
      console.warn("Invoice list fetch failed:", e);
    }
  },

  async renderTickets() {
    const list = document.getElementById("tickets-list");
    if (!list) return;

    try {
      const res = await fetch(`/api/v1/support/tickets?user_id=${this.state.user.telegram_id}`);
      if (res.ok) {
        const tickets = await res.json();
        if (!tickets.length) {
          list.innerHTML = `<p style="color:var(--text-muted);font-size:0.8rem;text-align:center;padding:14px;">No support tickets open.</p>`;
          return;
        }
        list.innerHTML = tickets.map(t => {
          // Calculate remaining 24-hour response SLA
          const now = Date.now() / 1000;
          const deadline = t.created_at + (24 * 3600);
          const hoursLeft = Math.max(0, Math.round((deadline - now) / 3600));

          return `
            <div class="campaign-card">
              <div class="campaign-header">
                <div>
                  <div class="campaign-title">Ticket #${t.ticket_id}</div>
                  <div style="font-size:0.75rem;color:var(--text-muted);">${t.gmail}</div>
                </div>
                <span class="${t.status === 'resolved' ? 'badge-approved' : 'badge-pending'}">${t.status.toUpperCase()}</span>
              </div>
              <div class="sla-badge-24h">
                <span>⏱ 24h SLA Countdown: <b>${hoursLeft}h remaining</b></span>
              </div>
              <p class="campaign-body">${t.narrative}</p>
              ${t.attachments && t.attachments.length ? `
                <div style="font-size:0.75rem;color:var(--accent-cyan);">📎 ${t.attachments.length} attachment(s) uploaded</div>
              ` : ''}
            </div>
          `;
        }).join("");
      }
    } catch (e) {
      console.warn("Tickets render failed:", e);
    }
  },


  // ---------- Admin session & login ----------
  adminSession() { try { return sessionStorage.getItem("mio_admin_session") || ""; } catch (e) { return ""; } },

  async adminFetch(url, opts = {}) {
    opts.headers = Object.assign({}, opts.headers, { "X-Admin-Session": this.adminSession() });
    const res = await fetch(url, opts);
    if (res.status === 401 || res.status === 403) {
      try { sessionStorage.removeItem("mio_admin_session"); } catch (e) {}
      if (res.status === 403) { this.state.user.role = "user"; this.updateProfileUI(); this.switchView("home"); }
      else this.showAdminLogin();
    }
    return res;
  },

  showAdminLogin() {
    const idEl = document.getElementById("admin-login-id");
    if (idEl && !idEl.value) idEl.value = this.state.user.telegram_id;
    document.getElementById("admin-login-error").innerText = "";
    this.openModal("modal-admin-login");
  },

  async submitAdminLogin() {
    const tid = parseInt(document.getElementById("admin-login-id").value);
    const token = document.getElementById("admin-login-token").value;
    const errEl = document.getElementById("admin-login-error");
    try {
      const res = await fetch("/api/v1/admin/login", {
        method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ telegram_id: tid, token: token })
      });
      const data = await res.json();
      if (!res.ok) { errEl.innerText = data.detail || "Login failed"; return; }
      try { sessionStorage.setItem("mio_admin_session", data.session_id); } catch (e) {}
      document.getElementById("admin-login-token").value = "";
      this.closeModal("modal-admin-login");
      this.state.user.telegram_id = tid;
      await this.fetchUserProfile();
      this.switchView("admin");
      this.showToast("Admin login successful");
    } catch (e) { errEl.innerText = "Network error"; }
  },

  async renderAdminList() {
    const box = document.getElementById("admin-admins-list");
    if (!box) return;
    const res = await this.adminFetch("/api/v1/admin/admins");
    if (!res.ok) return;
    const admins = await res.json();
    box.innerHTML = admins.map(a => `
      <div style="display:flex;align-items:center;justify-content:space-between;padding:6px 0;border-bottom:1px solid var(--border-light);font-size:0.8rem;">
        <div><b>${a.first_name || a.username || "User"}</b><div style="color:var(--text-muted);font-size:0.72rem;">ID: ${a.telegram_id}</div></div>
        ${a.telegram_id === this.state.user.telegram_id ? '<span class="brand-tag">YOU</span>' :
          `<button class="btn-secondary" style="padding:4px 10px;font-size:0.75rem;color:#EF4444;" onclick="AdminActions.removeAdmin(${a.telegram_id})">Remove</button>`}
      </div>`).join("");
  },

  async renderAdminPanel() {
    if (this.state.user.role !== "admin") return;

    // MongoDB URL list with live status
    try {
      const res = await this.adminFetch("/api/v1/admin/database/status");
      if (res.ok) {
        const st = await res.json();
        const box = document.getElementById("admin-db-status-container");
        if (box) {
          box.innerHTML = (st.is_mock ? `<div style="font-size:0.8rem;color:#F59E0B;margin-bottom:8px;">⚠️ No live MongoDB connected. Temporary memory DB in use.</div>` : "") +
            st.urls.map(u => `
            <div style="display:flex;align-items:center;gap:8px;padding:8px 0;border-bottom:1px solid var(--border-light);">
              <div style="flex:1;min-width:0;">
                <div style="font-size:0.78rem;word-break:break-all;">${u.uri}</div>
                <div style="font-size:0.72rem;color:var(--text-muted);margin-top:2px;">
                  ${u.connected ? '<span style="color:#10B981;">● Connected</span>' : '<span style="color:#EF4444;">● Failed</span>'}
                  ${u.latency_ms ? ' • ' + u.latency_ms + ' ms' : ''}${u.active ? ' • <b style="color:var(--accent-cyan);">ACTIVE</b>' : ''}
                </div>
              </div>
              <button class="btn-secondary" style="padding:4px 10px;font-size:0.75rem;color:#EF4444;" onclick="AdminActions.removeDb('${u.db_id}')">Remove</button>
            </div>`).join("");
        }
      }
    } catch (e) { console.warn("Admin DB status failed:", e); }

    this.renderAdminList();
    // Fetch moderation queues
    this.fetchAdminPendingChannels();
    this.fetchAdminPendingWithdrawals();
    this.fetchAdminLockLedger();
  },

  async fetchAdminPendingChannels() {
    const list = document.getElementById("admin-pending-channels-list");
    if (!list) return;

    try {
      const res = await this.adminFetch("/api/v1/admin/channels/pending");
      if (res.ok) {
        const pending = await res.json();
        if (!pending.length) {
          list.innerHTML = `<p style="color:var(--text-muted);font-size:0.8rem;padding:8px;">No channels awaiting moderation.</p>`;
          return;
        }
        list.innerHTML = pending.map(c => `
          <div class="campaign-card">
            <div class="campaign-header">
              <div>
                <div class="campaign-title">${c.title}</div>
                <div style="font-size:0.75rem;color:var(--text-muted);">${c.username} • Type: ${c.type}</div>
              </div>
              <span class="badge-pending">PENDING</span>
            </div>
            <div style="display:flex;gap:8px;margin-top:10px;">
              <button class="btn-primary" style="flex:1;padding:6px;font-size:0.8rem;" onclick="MioApp.moderateChannel('${c.channel_id}', 'approved')">Approve Channel</button>
              <button class="btn-secondary" style="flex:1;padding:6px;font-size:0.8rem;background:rgba(239,68,68,0.2);color:#EF4444;" onclick="MioApp.moderateChannel('${c.channel_id}', 'rejected')">Reject</button>
            </div>
          </div>
        `).join("");
      }
    } catch (e) {
      console.warn(e);
    }
  },

  async moderateChannel(channelId, action) {
    try {
      const res = await this.adminFetch("/api/v1/admin/channels/moderate", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          admin_id: this.state.user.telegram_id,
          channel_id: channelId,
          action: action
        })
      });
      if (res.ok) {
        this.showToast(`Channel ${action.toUpperCase()} successfully.`);
        this.fetchAdminPendingChannels();
        this.fetchChannels();
      }
    } catch (e) {
      this.showToast("Moderation action failed.");
    }
  },

  async fetchAdminPendingWithdrawals() {
    const list = document.getElementById("admin-pending-withdrawals-list");
    if (!list) return;

    try {
      const res = await this.adminFetch("/api/v1/admin/withdrawals/pending");
      if (res.ok) {
        const withdrawals = await res.json();
        if (!withdrawals.length) {
          list.innerHTML = `<p style="color:var(--text-muted);font-size:0.8rem;padding:8px;">No withdrawals awaiting weekly payout.</p>`;
          return;
        }
        list.innerHTML = withdrawals.map(w => `
          <div class="campaign-card">
            <div class="campaign-header">
              <div>
                <div class="campaign-title">$${w.amount} USDT</div>
                <div style="font-size:0.75rem;color:var(--text-muted);">User ID: ${w.user_id}</div>
              </div>
              <div class="sla-badge-48h" style="margin:0;">Weekly Payout</div>
            </div>
            <div style="font-size:0.75rem;word-break:break-all;margin-top:6px;color:var(--text-secondary);">Address: ${w.destination_address}</div>
            <div style="display:flex;gap:8px;margin-top:10px;">
              <button class="btn-primary" style="flex:1;padding:6px;font-size:0.8rem;" onclick="MioApp.moderateWithdrawal('${w.tx_id}', 'approved')">Approve Payout</button>
              <button class="btn-secondary" style="flex:1;padding:6px;font-size:0.8rem;color:#EF4444;" onclick="MioApp.moderateWithdrawal('${w.tx_id}', 'rejected')">Reject</button>
            </div>
          </div>
        `).join("");
      }
    } catch (e) {
      console.warn(e);
    }
  },

  async moderateWithdrawal(txId, action) {
    try {
      const res = await this.adminFetch("/api/v1/admin/withdrawals/moderate", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          admin_id: this.state.user.telegram_id,
          tx_id: txId,
          action: action
        })
      });
      if (res.ok) {
        this.showToast(`Withdrawal ${action.toUpperCase()}`);
        this.fetchAdminPendingWithdrawals();
      }
    } catch (e) {
      this.showToast("Withdrawal moderation failed.");
    }
  },

  async fetchAdminLockLedger() {
    const list = document.getElementById("admin-lock-ledger-list");
    if (!list) return;

    try {
      const res = await this.adminFetch("/api/v1/admin/lock-ledger/logs");
      if (res.ok) {
        const logs = await res.json();
        list.innerHTML = logs.map(l => `
          <div style="font-size:0.75rem;padding:8px 0;border-bottom:1px solid var(--border-light);line-height:1.4;">
            <div style="display:flex;justify-content:space-between;">
              <b style="color:var(--accent-cyan);">${l.event_type}</b>
              <span style="color:var(--text-muted);">${new Date((l.timestamp || Date.now() / 1000) * 1000).toLocaleTimeString()}</span>
            </div>
            <div style="color:var(--text-secondary);word-break:break-all;">${l.invoice_id || l.ticket_id || l.channel_title || 'Mirrored to Lock Channel'}</div>
          </div>
        `).join("");
      }
    } catch (e) {
      console.warn(e);
    }
  },

  // Global Command Bar Parser
  executeCommand(cmdText) {
    if (!cmdText) return;
    const cmd = cmdText.trim().toLowerCase();
    console.log("[MioApp] Parsing Global Navigation Command:", cmd);

    if (cmd.startsWith("/start")) {
      this.switchView("home");
      this.showToast("Welcome to Mio Ads!");
    } else if (cmd.startsWith("/wallet")) {
      this.switchView("wallet");
    } else if (cmd.startsWith("/channels")) {
      this.switchView("channels");
    } else if (cmd.startsWith("/stats")) {
      this.switchView("stats");
    } else if (cmd.startsWith("/help") || cmd.startsWith("/support")) {
      this.switchView("support");
    } else if (cmd.startsWith("/admin")) {
      if (this.state.user.role === "admin" && this.adminSession()) {
        this.switchView("admin");
      } else {
        this.showAdminLogin();
      }
    } else if (cmd.startsWith("/deposit")) {
      this.openModal("modal-deposit");
    } else if (cmd.startsWith("/withdraw")) {
      this.openModal("modal-withdraw");
    } else {
      this.showToast(`Command ${cmd} parsed.`);
    }
  },

  // Modal Handlers
  openModal(modalId) {
    const modal = document.getElementById(modalId);
    if (modal) modal.classList.add("open");
  },

  closeModal(modalId) {
    const modal = document.getElementById(modalId);
    if (modal) modal.classList.remove("open");
  },

  showToast(message) {
    let toast = document.getElementById("app-toast");
    if (!toast) {
      toast = document.createElement("div");
      toast.id = "app-toast";
      toast.style.cssText = "position:fixed;bottom:80px;left:50%;transform:translateX(-50%);background:#0B192C;color:#FFFFFF;border:1px solid #00B4D8;padding:10px 18px;border-radius:20px;font-size:0.85rem;font-weight:600;z-index:99;box-shadow:0 4px 15px rgba(0,0,0,0.4);transition:opacity 0.3s ease;";
      document.body.appendChild(toast);
    }
    toast.innerText = message;
    toast.style.opacity = "1";
    setTimeout(() => {
      toast.style.opacity = "0";
    }, 2500);
  },

  setupEventListeners() {
    // Command input enter key
    const cmdInput = document.getElementById("global-command-input");
    if (cmdInput) {
      cmdInput.addEventListener("keydown", (e) => {
        if (e.key === "Enter") {
          this.executeCommand(cmdInput.value);
          cmdInput.value = "";
        }
      });
    }

  }
};

window.MioApp = MioApp;
document.addEventListener("DOMContentLoaded", () => MioApp.init());
