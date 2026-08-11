'use strict';

/* ── State ──────────────────────────────────────────────────────────────── */
let ws            = null;
let phoneCodeHash = '';
let currentPhone  = '';
let totalInvites  = 0;
let doneInvites   = 0;

/* ── WebSocket ───────────────────────────────────────────────────────────── */
function initWS() {
    const proto = location.protocol === 'https:' ? 'wss' : 'ws';
    ws = new WebSocket(`${proto}://${location.host}/ws`);

    ws.onopen = () => {
        setStatus(true);
        log('[SYSTEM] Kết nối WebSocket tới server thành công!', 'ok');
    };

    ws.onmessage = ({ data }) => {
        try { handleEvent(JSON.parse(data)); } catch {}
    };

    ws.onclose = () => {
        setStatus(false);
        log('[SYSTEM] Mất kết nối, đang thử lại sau 3 giây...', 'warn');
        setTimeout(initWS, 3000);
    };
}

function handleEvent(ev) {
    switch (ev.type) {
        case 'log':
            classifyLog(ev.message);
            break;
        case 'progress':
            totalInvites = ev.total;
            doneInvites  = ev.added;
            updateProgress(ev.added, ev.total, ev.current || '');
            document.getElementById('valInvited').textContent = ev.added;
            break;
        case 'done':
            updateProgress(ev.added, ev.total, 'Hoàn tất!');
            document.getElementById('valInvited').textContent = ev.added;
            break;
        case 'scrape_done':
            document.getElementById('valScraped').textContent = ev.count;
            break;
        case 'invite_done':
            document.getElementById('valInvited').textContent = ev.added;
            break;
    }
}

/* ── UI Helpers ─────────────────────────────────────────────────────────── */
function setStatus(online) {
    const dot   = document.getElementById('dot');
    const label = document.getElementById('statusLabel');
    if (online) {
        dot.classList.add('online');
        label.textContent = 'Server đang hoạt động';
    } else {
        dot.classList.remove('online');
        label.textContent = 'Mất kết nối';
    }
}

function log(msg, cls = '') {
    const body = document.getElementById('logBody');
    const line = document.createElement('div');
    line.className = 'log-line ' + cls;
    line.textContent = msg;
    body.appendChild(line);
    body.scrollTop = body.scrollHeight;
}

function classifyLog(msg) {
    const m = msg.toLowerCase();
    if (m.includes('✅') || m.includes('thành công')) log(msg, 'ok');
    else if (m.includes('❌') || m.includes('lỗi') || m.includes('error') || m.includes('flood')) log(msg, 'err');
    else if (m.includes('⚠️') || m.includes('bỏ qua') || m.includes('chờ')) log(msg, 'warn');
    else log(msg);
}

function updateProgress(done, total, current) {
    const pct = total > 0 ? Math.round((done / total) * 100) : 0;
    document.getElementById('progressFill').style.width  = pct + '%';
    document.getElementById('progressPct').textContent   = pct + '%';
    document.getElementById('progressLabel').textContent =
        total > 0 ? `${done}/${total} mem${current ? ' — ' + current : ''}` : 'Đang xử lý...';
}

function showModal(show) {
    document.getElementById('otpModal').style.display = show ? 'flex' : 'none';
}

/* ── API Calls ───────────────────────────────────────────────────────────── */
async function api(endpoint, body) {
    const res = await fetch(endpoint, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body)
    });
    return res.json();
}

function getInputs() {
    return {
        apiId:         parseInt(document.getElementById('apiId').value.trim()),
        apiHash:       document.getElementById('apiHash').value.trim(),
        phone:         document.getElementById('phone').value.trim(),
        targetGroup:   document.getElementById('targetGroup').value.trim(),
        destGroup:     document.getElementById('destGroup').value.trim(),
        delaySeconds:  parseInt(document.getElementById('delaySeconds').value) || 35,
        maxInvites:    parseInt(document.getElementById('maxInvites').value) || 30,
        onlyActive:    document.getElementById('onlyActive').checked,
        onlyPhoto:     document.getElementById('onlyPhoto').checked,
    };
}

/* ── Login ───────────────────────────────────────────────────────────────── */
async function doLogin() {
    const { apiId, apiHash, phone } = getInputs();
    if (!apiId || !apiHash || !phone) {
        alert('Vui lòng điền đầy đủ API ID, API Hash và số điện thoại!'); return;
    }
    currentPhone = phone;
    const btn = document.getElementById('btnLogin');
    btn.textContent = '⏳ Đang đăng nhập...';
    btn.disabled = true;

    try {
        const res = await api('/api/login', { api_id: apiId, api_hash: apiHash, phone });
        if (res.status === 'otp_required') {
            phoneCodeHash = res.phone_code_hash;
            document.getElementById('otpMsg').textContent = res.message;
            showModal(true);
            log(`[AUTH] ${res.message}`, 'ok');
        } else if (res.status === 'authorized') {
            log(`[AUTH] ${res.message}`, 'ok');
            document.getElementById('statusLabel').textContent = res.message;
            document.getElementById('dot').classList.add('online');
        } else {
            log(`[AUTH] ❌ ${res.message}`, 'err');
            alert(res.message);
        }
    } catch (e) {
        log(`[AUTH] ❌ Lỗi kết nối: ${e.message}`, 'err');
    } finally {
        btn.textContent = '📱 Đăng Nhập Telegram';
        btn.disabled = false;
    }
}

/* ── OTP ─────────────────────────────────────────────────────────────────── */
async function doOTP() {
    const code     = document.getElementById('otpCode').value.trim();
    const password = document.getElementById('twoFaPassword').value.trim();
    if (!code) { alert('Nhập mã OTP!'); return; }

    const res = await api('/api/verify-otp', {
        phone: currentPhone, code, phone_code_hash: phoneCodeHash, password: password || null
    });

    if (res.status === 'authorized') {
        showModal(false);
        log(`[AUTH] ✅ ${res.message}`, 'ok');
        document.getElementById('statusLabel').textContent = res.message;
    } else if (res.status === '2fa_required') {
        document.getElementById('twoFaWrap').style.display = 'block';
        alert('Vui lòng nhập mật khẩu 2FA ở bên dưới rồi bấm Xác Nhận lại.');
    } else {
        log(`[AUTH] ❌ ${res.message}`, 'err');
        alert(res.message);
    }
}

/* ── Scrape ──────────────────────────────────────────────────────────────── */
async function doScrape() {
    const { targetGroup, onlyActive, onlyPhoto } = getInputs();
    if (!targetGroup) { alert('Nhập link nhóm đối thủ!'); return; }
    log(`[SCRAPE] Bắt đầu cào mem từ: ${targetGroup}`);
    document.getElementById('valScraped').textContent = '...';
    await api('/api/scrape', { target_group: targetGroup, only_active: onlyActive, only_photo: onlyPhoto });
}

/* ── Invite ──────────────────────────────────────────────────────────────── */
async function doInvite() {
    const { destGroup, delaySeconds, maxInvites } = getInputs();
    if (!destGroup) { alert('Nhập link nhóm của bạn!'); return; }
    log(`[INVITE] Bắt đầu ép mem vào: ${destGroup}`);
    updateProgress(0, maxInvites, 'Đang khởi động...');
    await api('/api/invite', { dest_group: destGroup, delay_seconds: delaySeconds, max_invites: maxInvites });
}

/* ── Full Pipeline ───────────────────────────────────────────────────────── */
async function doPipeline() {
    const { targetGroup, destGroup, delaySeconds, maxInvites, onlyActive, onlyPhoto } = getInputs();
    if (!targetGroup) { alert('Nhập link nhóm ĐỐI THỦ!'); return; }
    if (!destGroup)   { alert('Nhập link nhóm CỦA BẠN!'); return; }

    // Reset UI
    document.getElementById('valScraped').textContent  = '0';
    document.getElementById('valInvited').textContent  = '0';
    updateProgress(0, maxInvites, 'Đang khởi chạy pipeline...');
    log('');
    log(`[PIPELINE] 🔥 Khởi chạy 1-Click: ${targetGroup} ➔ ${destGroup}`);

    await api('/api/pipeline', {
        target_group:   targetGroup,
        dest_group:     destGroup,
        delay_seconds:  delaySeconds,
        max_invites:    maxInvites,
        only_active:    onlyActive,
        only_photo:     onlyPhoto
    });
}

/* ── Stop ────────────────────────────────────────────────────────────────── */
async function doStop() {
    await api('/api/stop', {});
    log('[SYSTEM] 🛑 Đã gửi lệnh dừng tới server.', 'warn');
}

/* ── Logout / Switch Account ─────────────────────────────────────────────── */
async function doLogout() {
    if (!confirm('Bạn muốn đăng xuất và đổi sang tài khoản khác?')) return;

    const btn = document.getElementById('btnLogout');
    btn.textContent = '⏳ Đang đăng xuất...';
    btn.disabled = true;

    try {
        const res = await fetch('/api/logout', { method: 'POST' });
        const data = await res.json();

        // Reset auth state
        currentPhone  = '';
        phoneCodeHash = '';

        // Clear login fields so user can enter a new account
        document.getElementById('phone').value   = '';
        document.getElementById('apiId').value   = '';
        document.getElementById('apiHash').value = '';

        // Reset status indicator
        document.getElementById('statusLabel').textContent = 'Chưa đăng nhập';
        document.getElementById('dot').classList.remove('online');

        log(`[AUTH] 🔄 ${data.message || 'Đã đăng xuất. Nhập tài khoản mới và đăng nhập lại.'}`, 'warn');
        alert('Đã đăng xuất! Bạn có thể nhập tài khoản khác và đăng nhập lại.');
    } catch (e) {
        log(`[AUTH] ❌ Lỗi đăng xuất: ${e.message}`, 'err');
    } finally {
        btn.textContent = '🔄 Đăng Xuất / Đổi Nick';
        btn.disabled = false;
    }
}

/* ── Init ────────────────────────────────────────────────────────────────── */
window.addEventListener('load', initWS);
