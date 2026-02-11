<script>
  import { onMount } from 'svelte';
  import { api } from '$lib/api.js';

  let files = [];
  let activeTab = 'image';
  let message = '';
  let messageType = '';
  let uploading = false;

  onMount(loadFiles);

  async function loadFiles() {
    try {
      files = await api.listFiles();
    } catch (err) {
      message = err.message;
      messageType = 'error';
    }
  }

  async function handleUpload(e) {
    const fileList = e.target.files;
    if (!fileList?.length) return;
    uploading = true;
    message = '';
    let count = 0;
    try {
      for (const file of fileList) {
        await api.upload(file);
        count++;
      }
      await loadFiles();
      message = `${count} file${count > 1 ? 's' : ''} uploaded`;
      messageType = 'success';
    } catch (err) {
      message = err.message;
      messageType = 'error';
    } finally {
      uploading = false;
      e.target.value = '';
    }
  }

  async function deleteFile(file) {
    if (!confirm(`Delete "${file.filename}"? This cannot be undone.`)) return;
    try {
      await api.deleteFile(file.filename);
      await loadFiles();
      message = 'File deleted';
      messageType = 'success';
    } catch (err) {
      message = err.message;
      messageType = 'error';
    }
  }

  function formatSize(bytes) {
    if (bytes < 1024) return bytes + ' B';
    if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB';
    return (bytes / (1024 * 1024)).toFixed(1) + ' MB';
  }

  $: filtered = files.filter(f => f.type === activeTab);
  $: imageCount = files.filter(f => f.type === 'image').length;
  $: videoCount = files.filter(f => f.type === 'video').length;
</script>

<div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 24px;">
  <h1 style="margin-bottom: 0;">Files</h1>
  <label class="btn btn-primary" style="cursor: pointer;">
    {uploading ? 'Uploading...' : '+ Upload Files'}
    <input type="file" accept="image/*,video/*" multiple on:change={handleUpload} disabled={uploading} hidden />
  </label>
</div>

<div class="tabs">
  <button class="tab" class:active={activeTab === 'image'} on:click={() => activeTab = 'image'}>
    Images ({imageCount})
  </button>
  <button class="tab" class:active={activeTab === 'video'} on:click={() => activeTab = 'video'}>
    Videos ({videoCount})
  </button>
</div>

{#if message}
  <div class="msg msg-{messageType}">{message}</div>
{/if}

{#if filtered.length === 0}
  <div class="empty">No {activeTab}s uploaded yet.</div>
{:else}
  <div class="file-grid">
    {#each filtered as file}
      <div class="file-card">
        <div class="file-preview">
          {#if file.type === 'image'}
            <img src={file.path} alt={file.filename} />
          {:else}
            <video src={file.path} preload="metadata"></video>
          {/if}
        </div>
        <div class="file-info">
          <span class="file-name" title={file.filename}>{file.filename}</span>
          <span class="file-size">{formatSize(file.size)}</span>
        </div>
        <div class="file-actions">
          <button class="btn btn-sm btn-danger" on:click={() => deleteFile(file)}>Delete</button>
        </div>
      </div>
    {/each}
  </div>
{/if}

<style>
  .file-grid {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(180px, 1fr));
    gap: 12px;
  }

  .file-card {
    background: var(--bg-card);
    border: 1px solid var(--border);
    border-radius: var(--radius);
    overflow: hidden;
  }

  .file-preview {
    width: 100%;
    height: 140px;
    background: var(--bg-input);
    display: flex;
    align-items: center;
    justify-content: center;
    overflow: hidden;
  }

  .file-preview img {
    width: 100%;
    height: 100%;
    object-fit: cover;
  }

  .file-preview video {
    width: 100%;
    height: 100%;
    object-fit: contain;
  }

  .file-info {
    padding: 8px 10px 4px;
  }

  .file-name {
    display: block;
    font-size: 11px;
    color: var(--text-dim);
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  .file-size {
    display: block;
    font-size: 10px;
    color: var(--text-dim);
    opacity: 0.6;
    margin-top: 2px;
  }

  .file-actions {
    padding: 4px 10px 10px;
  }
</style>
