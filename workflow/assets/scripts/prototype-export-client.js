/**
 * 原型 / PRD 頁面裡的匯出客戶端。
 *
 * 連接埠不再固定：由 pm-runtime-config.js 下發（該檔案在每次連接埠變化時被服務端重寫），
 * 所以這裡必須動態載入它，不能把連接埠寫死。
 *
 * 所有報錯文案只指向「雙擊專案根目錄的啟動腳本」——那是兩個平台上唯一保證
 * 存在於專案裡的東西。歷史文案裡出現過的 scripts/initialize.py、python3 命令
 * 在使用者的專案里根本不存在（前者從不安裝進專案，後者在 Windows 上沒有）。
 */
(function () {
  'use strict';

  const IS_WINDOWS = /Windows/i.test(navigator.userAgent);
  const ENTRY = IS_WINDOWS ? '「啟動原型匯出服務.bat」' : '「啟動原型匯出服務.command」';
  const HOW_TO_START = '請雙擊專案根目錄的' + ENTRY + '，保持那個視窗開著，再點一次匯出。';
  // 升級路徑：雙擊入口在兩個平台上都必然可用，所以它留給上面那條文案。
  // 這裡是「雙擊了也不行」時的下一步，面向已經開啟終端機的人。macOS 多給一條
  // 重註冊命令：那邊點匯出本該自動起服務，走到這一步通常是註冊掉了。
  const HOW_TO_DIAGNOSE = IS_WINDOWS
    ? '若仍不行，在專案目錄執行：py -3 scripts\\start_service.py --doctor'
    : '若仍不行，在專案目錄執行：bash scripts/install_launcher.sh 重新註冊自動啟動，'
      + '或 python3 scripts/start_service.py --doctor 看體檢報告';

  let cfg = window.PM_RUNTIME || {};
  let server = cfg.server;
  let launcher = cfg.launcher;
  const clientScriptSrc = document.currentScript && document.currentScript.src;
  let configLoadPromise = null;
  let readyPromise = null;
  let exporting = false;
  const revisions = new Map();

  const path = () => decodeURIComponent(location.pathname || '');

  const sleep = (ms) => new Promise((resolve) => setTimeout(resolve, ms));

  function configured() {
    return !!(server && cfg.projectId && cfg.token);
  }

  function loadRuntimeConfig() {
    if (configured()) return Promise.resolve();
    if (!clientScriptSrc) {
      return Promise.reject(new Error('缺少專案執行配置。' + HOW_TO_START));
    }
    // 失敗後不快取 promise：使用者按提示啟動服務後，下一次點選應當能重新載入到配置。
    if (!configLoadPromise) {
      configLoadPromise = new Promise((resolve, reject) => {
        const script = document.createElement('script');
        script.src = new URL('pm-runtime-config.js', clientScriptSrc).href
          + '?ts=' + Date.now();  // 連接埠換過之後不能吃瀏覽器快取裡的舊配置
        script.onload = () => {
          cfg = window.PM_RUNTIME || {};
          server = cfg.server;
          launcher = cfg.launcher;
          configured() ? resolve() : reject(new Error('專案執行配置不完整。' + HOW_TO_START));
        };
        script.onerror = () => reject(new Error('讀不到專案執行配置。' + HOW_TO_START));
        document.head.appendChild(script);
      }).catch((error) => {
        configLoadPromise = null;
        throw error;
      });
    }
    return configLoadPromise;
  }

  function configCheck() {
    if (cfg.readOnly) throw new Error('當前是隻讀分享模式，匯出需要在本地專案裡操作。');
    if (!configured()) throw new Error('專案執行配置缺失。' + HOW_TO_START);
  }

  async function request(url, payload) {
    const controller = new AbortController();
    const timer = setTimeout(() => controller.abort(), 120000);
    try {
      const response = await fetch(url, {
        method: payload === undefined ? 'GET' : 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-PM-Project': cfg.projectId,
          'X-PM-Token': cfg.token
        },
        body: payload === undefined ? undefined : JSON.stringify(payload),
        cache: 'no-store',
        signal: controller.signal
      });
      const data = await response.json().catch(() => ({}));
      if (!response.ok || data.error) throw new Error(data.error || ('HTTP ' + response.status));
      return data;
    } finally {
      clearTimeout(timer);
    }
  }

  async function health() {
    const response = await fetch(server + '/api/health', {
      cache: 'no-store', signal: AbortSignal.timeout(3000)
    });
    if (response.status === 404) {
      // 老版本服務沒有 /api/health。它還佔著連接埠，所以必須先讓使用者停掉它。
      const error = new Error('這個連接埠上是舊版匯出服務。請關掉它的終端機視窗（或重啟電腦），再'
        + HOW_TO_START);
      error.identity = true;
      throw error;
    }
    if (!response.ok) throw new Error('匯出服務健康檢查失敗（HTTP ' + response.status + '）');
    const state = await response.json();
    if (state.project_id !== cfg.projectId) {
      const error = new Error('這個連接埠被另一個專案的匯出服務佔著。請關掉它，再' + HOW_TO_START);
      error.identity = true;
      throw error;
    }
    if (state.read_only) {
      const error = new Error('當前服務是隻讀模式，不能匯出或寫回檔案。');
      error.identity = true;
      throw error;
    }
    return state;
  }

  async function ensureReady() {
    await loadRuntimeConfig();
    configCheck();
    if (readyPromise) return readyPromise;
    // 成功後保留快取：PRD「一鍵複製全文」會對每個 iframe 各調一次，不該每次都重新體檢。
    readyPromise = (async () => {
      try {
        return await health();
      } catch (error) {
        if (error.identity) throw error;  // 連接埠上有東西但不是我們要的，喚起也沒用
      }
      // 服務沒在跑。macOS 上若裝過常駐啟動器，它能幫我們拉起來；沒裝就直接給指引。
      let launch;
      try {
        launch = await request(launcher + '/api/launch', {});
      } catch (error) {
        throw new Error('匯出服務沒有啟動。' + HOW_TO_START);
      }
      if (!launch.ok) throw new Error(launch.error || ('匯出服務啟動失敗。' + HOW_TO_START));
      // 首次啟動要裝依賴、冷啟動瀏覽器，給足 45s
      const deadline = Date.now() + 45000;
      while (Date.now() < deadline) {
        try {
          return await health();
        } catch (error) {
          if (error.identity) throw error;
        }
        await sleep(600);
      }
      throw new Error('匯出服務啟動超時。' + HOW_TO_DIAGNOSE);
    })().catch((error) => {
      readyPromise = null;  // 只在失敗時清空，讓使用者修好問題後能重試
      throw error;
    });
    return readyPromise;
  }

  async function api(route, payload) {
    await ensureReady();
    return request(server + route, payload);
  }

  // ── 瀏覽器內編輯寫回 ─────────────────────────────────────────────
  async function revision(file) {
    const target = file || path();
    const data = await api('/api/revision', { path: target });
    revisions.set(target, data.revision);
    return data.revision;
  }

  async function save(content, file) {
    const target = file || path();
    if (!revisions.has(target)) throw new Error('尚未讀取檔案版本，請重新載入頁面後再儲存');
    const data = await api('/api/save-html', {
      path: target, content, revision: revisions.get(target)
    });
    revisions.set(target, data.revision);
    return data;
  }

  // ── 單頁取圖：給 PRD「一鍵複製全文」把原型 iframe 換成 base64 圖片 ──
  // file:// 下瀏覽器既不能 fetch 本地 PNG、canvas 也會被汙染，base64 只能由本地服務下發。
  async function snapshot(src, opts) {
    if (!src) throw new Error('缺少 iframe src');
    opts = opts || {};
    return api('/api/snapshot', {
      src, base: opts.base || path(), scale: opts.scale || 2,
      viewport: opts.viewport, force: !!opts.force
    });
  }

  // 本地 <img>（詳細方案「原型」列的截圖版）→ base64，同樣只能由服務下發
  async function asset(src, opts) {
    if (!src) throw new Error('缺少 img src');
    return api('/api/asset', { src, base: (opts || {}).base || path() });
  }

  // ── 匯出按鈕 ────────────────────────────────────────────────────
  // 按鈕識別沿用舊版的寬匹配：已經生成出去的原型裡，有的只有文案沒有 id/class。
  function isExportButton(target) {
    if (!target || target.nodeType !== 1) return null;
    const button = target.closest('button, [role="button"], a');
    if (!button) return null;
    const text = (button.textContent || '').trim();
    const matched = button.id === 'exportFab'
      || button.classList.contains('export-fab')
      || button.classList.contains('export-btn')
      || text.indexOf('一鍵匯出所有截圖') !== -1
      || text.indexOf('匯出PNG截圖') !== -1;
    return matched ? button : null;
  }

  function findExportButton() {
    return document.getElementById('exportFab')
      || document.querySelector('.export-fab, .export-btn')
      || Array.from(document.querySelectorAll('button')).find(isExportButton);
  }

  // 不用 button.disabled：匯出按鈕可能是 <a> 或 [role=button]，那上面 disabled 無效。
  function setButton(button, text, background, busy) {
    if (!button) return;
    button.textContent = text;
    if (background !== undefined) button.style.background = background;
    button.style.opacity = busy ? '0.75' : '1';
    button.style.pointerEvents = busy ? 'none' : '';
  }

  function notifyParent(message) {
    if (window.parent && window.parent !== window) window.parent.postMessage(message, '*');
  }

  async function exportAll(button) {
    if (exporting) return;
    exporting = true;
    const originalText = button ? button.textContent : '';
    const originalBackground = button ? button.style.background : '';
    const restore = () => setTimeout(
      () => setButton(button, originalText, originalBackground, false), 2600);

    try {
      setButton(button, '正在連線匯出服務…', undefined, true);
      const job = await api('/api/screenshot', {
        path: path(),
        viewport: {
          width: Math.max(1, Math.round(innerWidth || 1440)),
          height: Math.max(1, Math.round(innerHeight || 900))
        }
      });
      if (!job.started) throw new Error('匯出任務沒有啟動');

      const deadline = Date.now() + 300000;
      while (Date.now() < deadline) {
        const state = await request(server + '/api/status');
        if (state.job_id !== job.job_id) throw new Error('匯出任務已切換，請重新確認結果');
        setButton(button, '正在匯出 ' + state.progress + '/' + state.total, undefined, true);
        if (state.done) {
          setButton(button, '已匯出 ' + state.success_count + '/' + state.total + ' 張 PNG',
            '#22c55e', false);
          notifyParent('export-success');
          restore();
          return state;
        }
        await sleep(700);
      }
      throw new Error('匯出等待超時，請檢視專案裡的 .pm-workflow/service.log');
    } catch (error) {
      console.error('[prototype export]', error);
      setButton(button, '匯出失敗', '#ef4444', false);
      window.alert(error.message);
      notifyParent('export-error');
      restore();
    } finally {
      exporting = false;
    }
  }

  document.addEventListener('click', (event) => {
    const button = isExportButton(event.target);
    if (!button) return;
    event.preventDefault();
    event.stopPropagation();
    event.stopImmediatePropagation();
    exportAll(button);
  }, true);

  window.addEventListener('message', (event) => {
    if (event.data !== 'trigger-export') return;
    exportAll(findExportButton());
  }, true);

  window.PMService = { revision, save, api, health };
  window.exportPrototypeViaServer = exportAll;
  window.snapshotPrototypeViaServer = snapshot;
  window.inlineAssetViaServer = asset;
  window.ensureExportServerReady = ensureReady;
})();
