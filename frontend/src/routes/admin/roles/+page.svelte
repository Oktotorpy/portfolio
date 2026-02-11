<script>
  import { onMount } from 'svelte';
  import { api } from '$lib/api.js';
  import { lookups } from '$lib/stores.js';
  import Modal from '$lib/components/Modal.svelte';
  import MultiSelect from '$lib/components/MultiSelect.svelte';

  let roles = [];
  let jobs = [];
  let showModal = false;
  let editing = null;
  let message = '';
  let messageType = '';
  let saving = false;
  let filterJobId = '';

  // Form fields
  let formName = '';
  let formJobId = '';
  let formDescription = '';
  let formAccolades = '';
  let formDateStart = '';
  let formDateEnd = '';
  let formProficiencyIds = [];

  onMount(async () => {
    jobs = await api.getJobs();
    await loadRoles();
  });

  async function loadRoles() {
    try {
      roles = await api.getRoles(filterJobId || null);
    } catch (err) {
      message = err.message;
      messageType = 'error';
    }
  }

  function openCreate() {
    editing = null;
    formName = '';
    formJobId = jobs.length > 0 ? jobs[0].id : '';
    formDescription = '';
    formAccolades = '';
    formDateStart = '';
    formDateEnd = '';
    formProficiencyIds = [];
    showModal = true;
  }

  function openEdit(role) {
    editing = role;
    formName = role.name;
    formJobId = role.job_id;
    formDescription = role.description || '';
    formAccolades = role.accolades || '';
    formDateStart = role.date_start || '';
    formDateEnd = role.date_end || '';
    formProficiencyIds = role.proficiencies.map(p => p.id);
    showModal = true;
  }

  async function save() {
    saving = true;
    message = '';
    try {
      const data = {
        name: formName,
        job_id: parseInt(formJobId),
        description: formDescription,
        accolades: formAccolades,
        date_start: formDateStart || null,
        date_end: formDateEnd || null,
        proficiency_ids: formProficiencyIds
      };

      if (editing) {
        await api.updateRole(editing.id, data);
      } else {
        await api.createRole(data);
      }

      showModal = false;
      await loadRoles();
      message = editing ? 'Role updated' : 'Role created';
      messageType = 'success';
    } catch (err) {
      message = err.message;
      messageType = 'error';
    } finally {
      saving = false;
    }
  }

  async function deleteRole(role) {
    if (!confirm(`Delete "${role.name}"? This will also delete all associated projects.`)) return;
    try {
      await api.deleteRole(role.id);
      await loadRoles();
      message = 'Role deleted';
      messageType = 'success';
    } catch (err) {
      message = err.message;
      messageType = 'error';
    }
  }

  function getJobName(jobId) {
    const job = jobs.find(j => j.id === jobId);
    return job ? job.name : '—';
  }

  function formatDate(d) {
    if (!d) return '—';
    return new Date(d).toLocaleDateString('en-US', { month: 'short', year: 'numeric' });
  }

  $: if (filterJobId !== undefined) loadRoles();
</script>

<div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 24px;">
  <h1 style="margin-bottom: 0;">Roles</h1>
  <button class="btn btn-primary" on:click={openCreate} disabled={jobs.length === 0}>+ Add Role</button>
</div>

{#if jobs.length === 0}
  <div class="msg msg-error">No jobs exist yet. Create a job first before adding roles.</div>
{/if}

<div class="form-group" style="max-width: 300px; margin-bottom: 20px;">
  <label>Filter by Job</label>
  <select bind:value={filterJobId}>
    <option value="">All Jobs</option>
    {#each jobs as job}
      <option value={job.id}>{job.name}</option>
    {/each}
  </select>
</div>

{#if message}
  <div class="msg msg-{messageType}">{message}</div>
{/if}

{#if roles.length === 0}
  <div class="empty">No roles found.</div>
{:else}
  <div class="item-list">
    {#each roles as role}
      <div class="item-row">
        <div class="item-info">
          <div class="item-name">{role.name}</div>
          <div class="item-meta">
            {getJobName(role.job_id)} · {formatDate(role.date_start)} — {formatDate(role.date_end)}
          </div>
          {#if role.proficiencies.length > 0}
            <div style="margin-top: 4px;">
              {#each role.proficiencies as prof}
                <span class="tag">{prof.name}</span>
              {/each}
            </div>
          {/if}
        </div>
        <div class="item-actions">
          <button class="btn btn-sm btn-ghost" on:click={() => openEdit(role)}>Edit</button>
          <button class="btn btn-sm btn-danger" on:click={() => deleteRole(role)}>Delete</button>
        </div>
      </div>
    {/each}
  </div>
{/if}

<Modal bind:show={showModal} title={editing ? 'Edit Role' : 'New Role'}>
  <form on:submit|preventDefault={save}>
    <div class="form-group">
      <label>Name *</label>
      <input type="text" bind:value={formName} required />
    </div>

    <div class="form-group">
      <label>Job *</label>
      <select bind:value={formJobId} required>
        <option value="" disabled>Select a job...</option>
        {#each jobs as job}
          <option value={job.id}>{job.name}</option>
        {/each}
      </select>
    </div>

    <div class="form-group">
      <label>Description</label>
      <textarea bind:value={formDescription} rows="3"></textarea>
    </div>

    <div class="form-group">
      <label>Accolades</label>
      <textarea bind:value={formAccolades} rows="2" placeholder="Awards, achievements..."></textarea>
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
        label="Proficiencies"
        options={$lookups.proficiencies}
        bind:selected={formProficiencyIds}
      />
    </div>

    <div class="btn-group">
      <button type="submit" class="btn btn-primary" disabled={saving}>
        {saving ? 'Saving...' : editing ? 'Update' : 'Create'}
      </button>
      <button type="button" class="btn btn-ghost" on:click={() => showModal = false}>Cancel</button>
    </div>
  </form>
</Modal>
