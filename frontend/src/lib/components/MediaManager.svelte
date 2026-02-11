<script>
  import { api } from '$lib/api.js';

  export let media = [];  // [{media_type, media_value}]

  let showPicker = false;
  let serverFiles = [];
  let pickerTab = 'image';
  let uploading = false;
  let uploadError = '';

  // Add YouTube URL
  let youtubeUrl = '';

  function addItem(type, value) {
    media = [...media, { media_type: type, media_value: value }];
  }

  function removeItem(index) {
    media = media.filter((_, i) => i !== index);
  }

  function moveUp(index) {
    if (index <= 0) return;
    const arr = [...media];
    [arr[index - 1], arr[index]] = [arr[index], arr[index - 1]];
    media = arr;
  }

  function moveDown(index) {
    if (index >= media.length - 1) return;
    const arr = [...media];
    [arr[index], arr[index + 1]] = [arr[index + 1], arr[index]];
    media = arr;
  }

  async function handleUpload(e) {
    const file = e.target.files?.[0];
    if (!file) return;
    uploading = true;
    uploadError = '';
    try {
      const result = await api.upload(file);
      addItem(result.type, result.path);
    } catch (err) {
      uploadError = err.message;
    } finally {
      uploading = false;
      e.target.value = '';
    }
  }

  async function openPicker() {
    try {
      serverFiles = await api.listFiles();
    } catch {}
    showPicker = true;
  }

  function pickFile(file) {
    addItem(file.type, file.path);
    showPicker = false;
  }

  function addYoutube() {
    if (!youtubeUrl.trim()) return;
    addItem('youtube', youtubeUrl.trim());
    youtubeUrl = '';
  }

  function formatSize(bytes) {
    if (bytes < 1024) return bytes + ' B';
    if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB';
    return (bytes / (1024 * 1024)).toFixed(1) + ' MB';
  }

  $: pickerFiles = serverFiles.filter(f => f.type === pickerTab);
  $: isImage = (val) => /\.(jpg|jpeg|png|gif|webp|svg)$/i.test(val);
</script>

<div class="media-manager">
  <label>Media ({media.length})</label>

  {#if media.length > 0}
    <div class="media-list">
      {#each media as item, i}
        <div class="media-item">
          <div class="media-preview">
            {#if item.media_type === 'image'}
              <img src={item.media_value} alt="media" />
            {:else if item.media_type === 'video'}
              <div class="media-type-icon">🎬</div>
            {:else}
              <div class="media-type-icon">▶</div>
            {/if}
          </div>
          <div class="media-info">
            <span class="media-label">{item.media_type}</span>
            <code class="media-path">{item.media_value}</code>
          </div>
          <div class="media-actions">
            {#if i > 0}
              <button type="button" on:click={() => moveUp(i)} title="Move up">↑</button>
            {/if}
            {#if i < media.length - 1}
              <button type="button" on:click={() => moveDown(i)} title="Move down">↓</button>
            {/if}
            <button type="button" on:click={() => removeItem(i)} class="remove" title="Remove">×</button>
          </div>
        </div>
      {/each}
    </div>
  {/if}

  <div class="media-buttons">
    <label class="upload-btn">
      {uploading ? 'Uploading...' : '📁 Upload File'}
      <input type="file" accept="image/*,video/*" on:change={handleUpload} disabled={uploading} hidden />
    </label>
    <button type="button" class="picker-btn" on:click={openPicker}>📂 Server Files</button>
  </div>

  <div class="youtube-row">
    <input type="url" bind:value={youtubeUrl} placeholder="YouTube URL..." class="yt-input" />
    {#if youtubeUrl.trim()}
      <button type="button" class="yt-btn" on:click={addYoutube}>+ YouTube</button>
    {/if}
  </div>

  {#if uploadError}
    <p class="media-error">{uploadError}</p>
  {/if}
</div>

<!-- Server File Picker Modal -->
{#if showPicker}
  <!-- svelte-ignore a11y-click-events-have-key-events -->
  <!-- svelte-ignore a11y-no-static-element-interactions -->
  <div class="picker-backdrop" on:click={() => showPicker = false}>
    <div class="picker-modal" on:click|stopPropagation>
      <div class="picker-header">
        <h3>Select from server</h3>
        <button type="button" class="picker-close" on:click={() => showPicker = false}>×</button>
      </div>
      <div class="picker-tabs">
        <button type="button" class:active={pickerTab === 'image'} on:click={() => pickerTab = 'image'}>Images</button>
        <button type="button" class:active={pickerTab === 'video'} on:click={() => pickerTab = 'video'}>Videos</button>
      </div>
      <div class="picker-grid">
        {#if pickerFiles.length === 0}
          <p class="picker-empty">No {pickerTab}s found</p>
        {:else}
          {#each pickerFiles as file}
            <button type="button" class="picker-file" on:click={() => pickFile(file)}>
              {#if file.type === 'image'}
                <img src={file.path} alt={file.filename} />
              {:else}
                <div class="picker-video-icon">🎬</div>
              {/if}
              <span class="picker-name">{file.filename}</span>
              <span class="picker-size">{formatSize(file.size)}</span>
            </button>
          {/each}
        {/if}
      </div>
    </div>
  </div>
{/if}

<style>
  .media-manager { margin-bottom: 20px; }
  .media-manager > label {
    display: block; font-size: 13px; font-weight: 500; color: var(--text-dim);
    margin-bottom: 6px; text-transform: uppercase; letter-spacing: 0.5px;
  }

  .media-list { display: flex; flex-direction: column; gap: 6px; margin-bottom: 10px; }

  .media-item {
    display: flex; align-items: center; gap: 10px;
    padding: 8px 10px; background: var(--bg-card); border: 1px solid var(--border);
    border-radius: var(--radius-sm);
  }

  .media-preview {
    width: 48px; height: 36px; flex-shrink: 0; border-radius: 3px;
    overflow: hidden; background: var(--bg-input); display: flex;
    align-items: center; justify-content: center;
  }
  .media-preview img { width: 100%; height: 100%; object-fit: cover; }
  .media-type-icon { font-size: 18px; }

  .media-info { flex: 1; min-width: 0; }
  .media-label { font-size: 11px; color: var(--accent); text-transform: uppercase; font-weight: 500; }
  .media-path { display: block; font-size: 11px; color: var(--text-dim); word-break: break-all; }

  .media-actions { display: flex; gap: 4px; flex-shrink: 0; }
  .media-actions button {
    background: var(--bg-hover); border: 1px solid var(--border); border-radius: 3px;
    color: var(--text-dim); font-size: 14px; width: 26px; height: 26px;
    cursor: pointer; display: flex; align-items: center; justify-content: center;
    font-family: inherit; padding: 0;
  }
  .media-actions button:hover { color: var(--text); border-color: var(--text-dim); }
  .media-actions button.remove:hover { color: var(--danger); border-color: var(--danger); }

  .media-buttons { display: flex; gap: 8px; margin-bottom: 8px; }

  .upload-btn, .picker-btn {
    padding: 7px 14px; font-size: 13px; border-radius: var(--radius-sm);
    cursor: pointer; font-family: inherit; border: 1px solid var(--border);
    background: var(--bg-hover); color: var(--text-dim); transition: all 0.15s;
  }
  .upload-btn:hover, .picker-btn:hover { color: var(--text); border-color: var(--text-dim); }

  .youtube-row { display: flex; gap: 6px; }
  .yt-input { flex: 1; padding: 7px 10px; background: var(--bg-input); border: 1px solid var(--border);
    border-radius: var(--radius-sm); color: var(--text); font-size: 13px; font-family: inherit; }
  .yt-input:focus { outline: none; border-color: var(--border-focus); }
  .yt-btn { padding: 7px 12px; background: var(--accent); border: none; border-radius: var(--radius-sm);
    color: white; font-size: 13px; cursor: pointer; font-family: inherit; white-space: nowrap; }

  .media-error { font-size: 13px; color: var(--danger); margin-top: 6px; }

  /* Picker modal */
  .picker-backdrop {
    position: fixed; inset: 0; background: rgba(0,0,0,0.6);
    display: flex; align-items: center; justify-content: center; z-index: 200;
  }
  .picker-modal {
    background: var(--bg-card); border: 1px solid var(--border); border-radius: var(--radius);
    width: 90%; max-width: 640px; max-height: 80vh; display: flex; flex-direction: column;
  }
  .picker-header {
    display: flex; justify-content: space-between; align-items: center;
    padding: 16px 20px; border-bottom: 1px solid var(--border);
  }
  .picker-header h3 { font-size: 16px; font-weight: 600; color: var(--text-heading); margin: 0; }
  .picker-close { background: none; border: none; color: var(--text-dim); font-size: 22px; cursor: pointer; }

  .picker-tabs {
    display: flex; gap: 0; border-bottom: 1px solid var(--border); padding: 0 20px;
  }
  .picker-tabs button {
    padding: 10px 18px; background: none; border: none;
    border-bottom: 2px solid transparent; color: var(--text-dim);
    font-size: 14px; cursor: pointer; font-family: inherit;
  }
  .picker-tabs button.active { color: var(--accent); border-bottom-color: var(--accent); }

  .picker-grid {
    padding: 16px 20px; overflow-y: auto; display: grid;
    grid-template-columns: repeat(auto-fill, minmax(120px, 1fr)); gap: 10px;
  }
  .picker-empty { color: var(--text-dim); font-size: 14px; grid-column: 1 / -1; text-align: center; padding: 30px; }

  .picker-file {
    background: var(--bg-input); border: 1px solid var(--border); border-radius: var(--radius-sm);
    padding: 6px; cursor: pointer; text-align: center; transition: border-color 0.15s;
  }
  .picker-file:hover { border-color: var(--accent); }
  .picker-file img { width: 100%; height: 80px; object-fit: cover; border-radius: 3px; display: block; }
  .picker-video-icon { font-size: 28px; height: 80px; display: flex; align-items: center; justify-content: center; }
  .picker-name { display: block; font-size: 10px; color: var(--text-dim); margin-top: 4px;
    overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
  .picker-size { display: block; font-size: 10px; color: var(--text-dim); opacity: 0.6; }
</style>
