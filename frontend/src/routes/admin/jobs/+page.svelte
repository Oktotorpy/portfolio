<script>
  import { onMount } from 'svelte';
  import { api } from '$lib/api.js';
  import { lookups } from '$lib/stores.js';
  import Modal from '$lib/components/Modal.svelte';
  import MultiSelect from '$lib/components/MultiSelect.svelte';
  import FileUpload from '$lib/components/FileUpload.svelte';

  let jobs = [];
  let showModal = false;
  let editing = null;
  let message = '';
  let messageType = '';
  let saving = false;

  // Form fields
  let formName = '';
  let formWebsite = '';
  let formDescription = '';
  let formDateStart = '';
  let formDateEnd = '';
  let formCountryIds = [];
  let formLogo = null;
  let formColor = '#3a3d48';

  onMount(loadJobs);

  async function loadJobs() {
    try {
      jobs = await api.getJobs();
    } catch (err) {
      message = err.message;
      messageType = 'error';
    }
  }

  function openCreate() {
    editing = null;
    formName = '';
    formWebsite = '';
    formDescription = '';
    formDateStart = '';
    formDateEnd = '';
    formCountryIds = [];
    formLogo = null;
    formColor = '#3a3d48';
    showModal = true;
  }

  function openEdit(job) {
    editing = job;
    formName = job.name;
    formWebsite = job.website || '';
    formDescription = job.description || '';
    formDateStart = job.date_start || '';
    formDateEnd = job.date_end || '';
    formCountryIds = job.countries.map(c => c.id);
    formLogo = job.logo;
    formColor = job.color || '#3a3d48';
    showModal = true;
  }

  async function save() {
    saving = true;
    message = '';
    try {
      const data = {
        name: formName,
        website: formWebsite || null,
        description: formDescription,
        date_start: formDateStart || null,
        date_end: formDateEnd || null,
        country_ids: formCountryIds,
        color: formColor
      };

      let job;
      if (editing) {
        job = await api.updateJob(editing.id, data);
        if (formLogo !== editing.logo) {
          job = await api.updateJobLogo(editing.id, formLogo);
        }
      } else {
        job = await api.createJob(data);
        if (formLogo) {
          job = await api.updateJobLogo(job.id, formLogo);
        }
      }

      showModal = false;
      await loadJobs();
      message = editing ? 'Job updated' : 'Job created';
      messageType = 'success';
    } catch (err) {
      message = err.message;
      messageType = 'error';
    } finally {
      saving = false;
    }
  }

  async function deleteJob(job) {
    if (!confirm(`Delete "${job.name}"? This will also delete all associated roles and projects.`)) return;
    try {
      await api.deleteJob(job.id);
      await loadJobs();
      message = 'Job deleted';
      messageType = 'success';
    } catch (err) {
      message = err.message;
      messageType = 'error';
    }
  }

  function formatDate(d) {
    if (!d) return '—';
    return new Date(d).toLocaleDateString('en-US', { month: 'short', year: 'numeric' });
  }
</script>

<div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 24px;">
  <h1 style="margin-bottom: 0;">Jobs</h1>
  <button class="btn btn-primary" on:click={openCreate}>+ Add Job</button>
</div>

{#if message}
  <div class="msg msg-{messageType}">{message}</div>
{/if}

{#if jobs.length === 0}
  <div class="empty">No jobs yet. Click "Add Job" to create one.</div>
{:else}
  <div class="item-list">
    {#each jobs as job}
      <div class="item-row">
        <div style="display: flex; align-items: center; gap: 12px; flex: 1;">
          <div style="width: 4px; height: 40px; border-radius: 2px; background: {job.color || '#3a3d48'}; flex-shrink: 0;"></div>
          {#if job.logo}
            <img src={job.logo} alt="{job.name} logo" style="width: 48px; height: 48px; object-fit: contain; border-radius: 4px; background: var(--bg-input); flex-shrink: 0;" />
          {:else}
            <div style="width: 48px; height: 48px; display: flex; align-items: center; justify-content: center; font-size: 20px; background: var(--bg-input); border-radius: 4px; flex-shrink: 0;">🏢</div>
          {/if}
          <div class="item-info">
            <div class="item-name">{job.name}</div>
            <div class="item-meta">
              {formatDate(job.date_start)} — {formatDate(job.date_end)}
              {#if job.countries.length > 0}
                · {job.countries.map(c => c.name).join(', ')}
              {/if}
            </div>
          </div>
        </div>
        <div class="item-actions">
          <button class="btn btn-sm btn-ghost" on:click={() => openEdit(job)}>Edit</button>
          <button class="btn btn-sm btn-danger" on:click={() => deleteJob(job)}>Delete</button>
        </div>
      </div>
    {/each}
  </div>
{/if}

<Modal bind:show={showModal} title={editing ? 'Edit Job' : 'New Job'}>
  <form on:submit|preventDefault={save}>
    <div class="form-group">
      <label>Name *</label>
      <input type="text" bind:value={formName} required />
    </div>

    <FileUpload bind:value={formLogo} label="Logo" accept="image/*" />

    <div class="form-group">
      <label>Website</label>
      <input type="url" bind:value={formWebsite} placeholder="https://..." />
    </div>

    <div class="form-group">
      <label>Description</label>
      <textarea bind:value={formDescription} rows="3"></textarea>
    </div>

    <div class="form-row">
      <div class="form-group">
        <label>Start Date</label>
        <input type="date" bind:value={formDateStart} />
      </div>
      <div class="form-group">
        <label>End Date</label>
        <input type="date" bind:value={formDateEnd} />
      </div>
    </div>

    <div class="form-group">
      <MultiSelect
        label="Countries"
        options={$lookups.countries}
        bind:selected={formCountryIds}
        lookupTable="countries"
      />
    </div>

    <div class="form-group">
      <label>Color</label>
      <div class="color-picker-row">
        <input type="color" bind:value={formColor} class="color-input" />
        <input type="text" bind:value={formColor} placeholder="#3a3d48" class="color-text" />
      </div>
    </div>

    <div class="btn-group">
      <button type="submit" class="btn btn-primary" disabled={saving}>
        {saving ? 'Saving...' : editing ? 'Update' : 'Create'}
      </button>
      <button type="button" class="btn btn-ghost" on:click={() => showModal = false}>Cancel</button>
    </div>
  </form>
</Modal>

<style>
  .color-picker-row {
    display: flex;
    align-items: center;
    gap: 10px;
  }

  .color-input {
    width: 44px;
    height: 36px;
    padding: 2px;
    border: 1px solid var(--border);
    border-radius: var(--radius-sm);
    background: var(--bg-input);
    cursor: pointer;
  }

  .color-input::-webkit-color-swatch-wrapper {
    padding: 2px;
  }

  .color-input::-webkit-color-swatch {
    border: none;
    border-radius: 2px;
  }

  .color-text {
    flex: 1;
    font-family: monospace;
  }
</style>
