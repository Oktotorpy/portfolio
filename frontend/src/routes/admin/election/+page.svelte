<script>
  import { onMount } from 'svelte';
  import { api } from '$lib/api.js';

  // config
  let sourceMode = 'manual';
  let apiUrl = '';
  let apiProxy = '';
  let apiHeaders = '';
  let apiTimeout = 30;

  // manual editor
  let manualText = '';

  // ui state
  let savingConfig = false;
  let savingManual = false;
  let testing = false;
  let testResult = null;
  let cfgMsg = '';
  let cfgMsgType = '';
  let manualMsg = '';
  let manualMsgType = '';

  onMount(async () => {
    try {
      const c = await api.getElectionConfig();
      sourceMode = c.source_mode || 'manual';
      apiUrl = c.api_url || '';
      apiProxy = c.api_proxy || '';
      apiHeaders = c.api_headers || '';
      apiTimeout = c.api_timeout || 30;
    } catch (err) {
      cfgMsg = err.message;
      cfgMsgType = 'error';
    }
    try {
      const m = await api.getElectionManual();
      manualText = JSON.stringify(m, null, 2);
    } catch (err) {
      manualMsg = err.message;
      manualMsgType = 'error';
    }
  });

  async function saveConfig() {
    savingConfig = true;
    cfgMsg = '';
    try {
      const c = await api.updateElectionConfig({
        source_mode: sourceMode,
        api_url: apiUrl,
        api_proxy: apiProxy,
        api_headers: apiHeaders,
        api_timeout: apiTimeout
      });
      sourceMode = c.source_mode;
      apiHeaders = c.api_headers || '';
      apiTimeout = c.api_timeout;
      cfgMsg = 'Settings saved';
      cfgMsgType = 'success';
    } catch (err) {
      cfgMsg = err.message;
      cfgMsgType = 'error';
    } finally {
      savingConfig = false;
    }
  }

  async function testConnection() {
    testing = true;
    testResult = null;
    try {
      testResult = await api.testElectionApi({
        api_url: apiUrl,
        api_proxy: apiProxy,
        api_headers: apiHeaders,
        api_timeout: apiTimeout
      });
    } catch (err) {
      testResult = { ok: false, error: err.message };
    } finally {
      testing = false;
    }
  }

  async function saveManual() {
    savingManual = true;
    manualMsg = '';
    let parties;
    try {
      parties = JSON.parse(manualText);
    } catch {
      manualMsg = 'Invalid JSON — fix the syntax before saving';
      manualMsgType = 'error';
      savingManual = false;
      return;
    }
    try {
      const res = await api.updateElectionManual(parties);
      manualText = JSON.stringify(parties, null, 2);
      manualMsg = `Saved ${res.count} parties to the manual file`;
      manualMsgType = 'success';
    } catch (err) {
      manualMsg = err.message;
      manualMsgType = 'error';
    } finally {
      savingManual = false;
    }
  }
</script>

<h1>Election Data Source</h1>

<p style="color: var(--text-dim); max-width: 60ch;">
  Controls what <code>/election</code> serves. <strong>Manual</strong> uses the JSON you edit
  below; <strong>API</strong> uses the latest snapshot fetched by the 4-minute poller.
</p>

<!-- Source mode + API config -->
<div class="card">
  {#if cfgMsg}
    <div class="msg msg-{cfgMsgType}">{cfgMsg}</div>
  {/if}

  <div class="form-group">
    <label>Source mode</label>
    <select bind:value={sourceMode}>
      <option value="manual">Manual — serve the edited JSON file</option>
      <option value="api">API — serve the latest polled snapshot</option>
    </select>
  </div>

  <fieldset class="api-fields" disabled={sourceMode !== 'api'}>
    <div class="form-group">
      <label>API URL</label>
      <input type="url" bind:value={apiUrl} placeholder="https://.../results.json" />
    </div>

    <div class="form-group">
      <label>Proxy / VPN egress</label>
      <input type="text" bind:value={apiProxy} placeholder="socks5h://127.0.0.1:25344  (empty = direct)" />
      <small style="color: var(--text-dim);">
        Routes the request through Armenia. A provider proxy (<code>socks5://…</code>) goes here directly;
        for Surfshark/WireGuard, run <code>wireproxy</code> and point this at its local SOCKS address.
      </small>
    </div>

    <div class="form-group">
      <label>Extra headers (JSON object)</label>
      <textarea bind:value={apiHeaders} rows="2" placeholder={'{"Authorization": "Bearer ..."}'}></textarea>
    </div>

    <div class="form-group">
      <label>Timeout (seconds)</label>
      <input type="number" bind:value={apiTimeout} min="1" max="300" style="max-width: 120px;" />
    </div>
  </fieldset>

  <div class="btn-group">
    <button class="btn btn-primary" on:click={saveConfig} disabled={savingConfig}>
      {savingConfig ? 'Saving...' : 'Save settings'}
    </button>
    <button class="btn btn-ghost" on:click={testConnection} disabled={testing || !apiUrl}>
      {testing ? 'Testing...' : 'Test connection'}
    </button>
  </div>

  {#if testResult}
    <div class="msg msg-{testResult.ok ? 'success' : 'error'}" style="margin-top: 1rem;">
      {#if testResult.ok}
        OK — HTTP {testResult.status} via {testResult.via}, {testResult.count} parties returned.
      {:else if testResult.status}
        Failed — HTTP {testResult.status} via {testResult.via}. {testResult.error || ''}
      {:else}
        Failed — {testResult.error}
      {/if}
    </div>
    {#if testResult.sample}
      <pre class="sample">{JSON.stringify(testResult.sample, null, 2)}</pre>
    {/if}
  {/if}
</div>

<!-- Manual JSON editor -->
<h2 style="margin-top: 2rem;">Manual JSON</h2>
<p style="color: var(--text-dim);">
  Served when source mode is <strong>Manual</strong>. Saved to the file on the server; also
  updatable via SSH.
</p>

<div class="card">
  {#if manualMsg}
    <div class="msg msg-{manualMsgType}">{manualMsg}</div>
  {/if}

  <div class="form-group">
    <label>Parties array</label>
    <textarea bind:value={manualText} rows="16" spellcheck="false"
      style="font-family: var(--font-mono, monospace); font-size: 0.85rem;"></textarea>
  </div>

  <div class="btn-group">
    <button class="btn btn-primary" on:click={saveManual} disabled={savingManual}>
      {savingManual ? 'Saving...' : 'Save manual JSON'}
    </button>
  </div>
</div>

<style>
  .api-fields {
    border: none;
    padding: 0;
    margin: 0;
    transition: opacity 0.15s;
  }
  .api-fields[disabled] {
    opacity: 0.45;
  }
  .sample {
    margin-top: 0.75rem;
    padding: 0.75rem;
    background: var(--bg-elevated, #1a1d24);
    border: 1px solid var(--border, #2a2d35);
    border-radius: 6px;
    overflow-x: auto;
    font-size: 0.8rem;
    color: var(--text-dim);
  }
</style>
