<script>
  import { api } from '$lib/api.js';

  export let value = null;
  export let label = 'File';
  export let accept = 'image/*';

  let uploading = false;
  let error = '';

  async function handleFile(e) {
    const file = e.target.files?.[0];
    if (!file) return;

    uploading = true;
    error = '';
    try {
      const result = await api.upload(file);
      value = result.path;
    } catch (err) {
      error = err.message;
    } finally {
      uploading = false;
    }
  }

  function clear() {
    value = null;
  }

  $: isImage = value && /\.(jpg|jpeg|png|gif|webp|svg)$/i.test(value);
</script>

<div class="form-group">
  <label>{label}</label>

  {#if value}
    <div style="display: flex; align-items: center; gap: 12px; margin-bottom: 8px;">
      {#if isImage}
        <img src={value} alt="Preview" style="max-width: 120px; max-height: 80px; object-fit: contain; border-radius: 4px; background: var(--bg-input);" />
      {/if}
      <div style="flex: 1; min-width: 0;">
        <code style="font-size: 12px; color: var(--text-dim); word-break: break-all;">{value}</code>
      </div>
      <button type="button" class="btn btn-sm btn-ghost" on:click={clear}>Remove</button>
    </div>
  {/if}

  <input type="file" {accept} on:change={handleFile} disabled={uploading} />

  {#if uploading}
    <p style="font-size: 13px; color: var(--text-dim); margin-top: 4px;">Uploading...</p>
  {/if}
  {#if error}
    <p class="msg msg-error" style="margin-top: 4px;">{error}</p>
  {/if}
</div>
