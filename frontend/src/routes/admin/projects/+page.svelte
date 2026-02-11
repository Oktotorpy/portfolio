<script>
  import { onMount } from 'svelte';
  import { api } from '$lib/api.js';
  import { lookups } from '$lib/stores.js';
  import Modal from '$lib/components/Modal.svelte';
  import MultiSelect from '$lib/components/MultiSelect.svelte';
  import MediaManager from '$lib/components/MediaManager.svelte';

  let projects = [];
  let roles = [];
  let jobs = [];
  let showModal = false;
  let editing = null;
  let message = '';
  let messageType = '';
  let saving = false;
  let filterRoleId = '';

  // Form fields
  let formName = '';
  let formRoleId = '';
  let formDescription = '';
  let formDateOfCreation = '';
  let formLink = '';
  let formWeightId = '';
  let formSkillIds = [];
  let formWorkTypeIds = [];
  let formToolIds = [];
  let formMedia = [];

  onMount(async () => {
    jobs = await api.getJobs();
    roles = await api.getRoles();
    await loadProjects();
  });

  async function loadProjects() {
    try {
      projects = await api.getProjects(filterRoleId || null);
    } catch (err) {
      message = err.message;
      messageType = 'error';
    }
  }

  function openCreate() {
    editing = null;
    formName = '';
    formRoleId = roles.length > 0 ? roles[0].id : '';
    formDescription = '';
    formDateOfCreation = '';
    formLink = '';
    formWeightId = '';
    formSkillIds = [];
    formWorkTypeIds = [];
    formToolIds = [];
    formMedia = [];
    showModal = true;
  }

  function openEdit(project) {
    editing = project;
    formName = project.name;
    formRoleId = project.role_id;
    formDescription = project.description || '';
    formDateOfCreation = project.date_of_creation || '';
    formLink = project.link || '';
    formWeightId = project.weight_id || '';
    formSkillIds = project.skills.map(s => s.id);
    formWorkTypeIds = project.work_types.map(wt => wt.id);
    formToolIds = project.tools.map(t => t.id);
    formMedia = (project.media || []).map(m => ({ media_type: m.media_type, media_value: m.media_value }));
    showModal = true;
  }

  async function save() {
    saving = true;
    message = '';
    try {
      const data = {
        name: formName,
        role_id: parseInt(formRoleId),
        description: formDescription,
        date_of_creation: formDateOfCreation || null,
        link: formLink || null,
        weight_id: formWeightId ? parseInt(formWeightId) : null,
        skill_ids: formSkillIds,
        work_type_ids: formWorkTypeIds,
        tool_ids: formToolIds,
        media: formMedia
      };

      if (editing) {
        await api.updateProject(editing.id, data);
      } else {
        await api.createProject(data);
      }

      showModal = false;
      await loadProjects();
      message = editing ? 'Project updated' : 'Project created';
      messageType = 'success';
    } catch (err) {
      message = err.message;
      messageType = 'error';
    } finally {
      saving = false;
    }
  }

  async function deleteProject(project) {
    if (!confirm(`Delete "${project.name}"?`)) return;
    try {
      await api.deleteProject(project.id);
      await loadProjects();
      message = 'Project deleted';
      messageType = 'success';
    } catch (err) {
      message = err.message;
      messageType = 'error';
    }
  }

  function getRoleName(roleId) {
    const role = roles.find(r => r.id === roleId);
    if (!role) return '—';
    const job = jobs.find(j => j.id === role.job_id);
    return `${role.name} @ ${job ? job.name : '?'}`;
  }

  function getWeightName(weightId) {
    const w = ($lookups.weights || []).find(w => w.id === weightId);
    return w ? w.name : '';
  }

  $: if (filterRoleId !== undefined) loadProjects();

  $: rolesByJob = jobs.map(j => ({
    job: j,
    roles: roles.filter(r => r.job_id === j.id)
  })).filter(g => g.roles.length > 0);
</script>

<div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 24px;">
  <h1 style="margin-bottom: 0;">Projects</h1>
  <button class="btn btn-primary" on:click={openCreate} disabled={roles.length === 0}>+ Add Project</button>
</div>

{#if roles.length === 0}
  <div class="msg msg-error">No roles exist yet. Create a job and role first before adding projects.</div>
{/if}

<div class="form-group" style="max-width: 300px; margin-bottom: 20px;">
  <label>Filter by Role</label>
  <select bind:value={filterRoleId}>
    <option value="">All Roles</option>
    {#each rolesByJob as group}
      <optgroup label={group.job.name}>
        {#each group.roles as role}
          <option value={role.id}>{role.name}</option>
        {/each}
      </optgroup>
    {/each}
  </select>
</div>

{#if message}
  <div class="msg msg-{messageType}">{message}</div>
{/if}

{#if projects.length === 0}
  <div class="empty">No projects found.</div>
{:else}
  <div class="item-list">
    {#each projects as project}
      <div class="item-row">
        <div class="item-info">
          <div class="item-name">
            {project.name}
            {#if project.weight}
              <span class="weight-badge">{project.weight.name}</span>
            {/if}
          </div>
          <div class="item-meta">
            {getRoleName(project.role_id)}
            {#if project.date_of_creation} · {project.date_of_creation}{/if}
            {#if project.media?.length > 0} · {project.media.length} media{/if}
          </div>
          <div style="margin-top: 4px;">
            {#each project.work_types as wt}
              <span class="tag">{wt.name}</span>
            {/each}
            {#each project.skills as skill}
              <span class="tag" style="background: rgba(61,170,109,0.15); color: var(--success);">{skill.name}</span>
            {/each}
            {#each project.tools as tool}
              <span class="tag" style="background: rgba(122,127,170,0.15); color: #7a7faa;">{tool.name}</span>
            {/each}
          </div>
        </div>
        <div class="item-actions">
          <button class="btn btn-sm btn-ghost" on:click={() => openEdit(project)}>Edit</button>
          <button class="btn btn-sm btn-danger" on:click={() => deleteProject(project)}>Delete</button>
        </div>
      </div>
    {/each}
  </div>
{/if}

<Modal bind:show={showModal} title={editing ? 'Edit Project' : 'New Project'}>
  <form on:submit|preventDefault={save}>
    <div class="form-group">
      <label>Name *</label>
      <input type="text" bind:value={formName} required />
    </div>

    <div class="form-group">
      <label>Role *</label>
      <select bind:value={formRoleId} required>
        <option value="" disabled>Select a role...</option>
        {#each rolesByJob as group}
          <optgroup label={group.job.name}>
            {#each group.roles as role}
              <option value={role.id}>{role.name}</option>
            {/each}
          </optgroup>
        {/each}
      </select>
    </div>

    <div class="form-group">
      <label>Description</label>
      <textarea bind:value={formDescription} rows="3"></textarea>
    </div>

    <div class="form-row">
      <div class="form-group">
        <label>Date of Creation</label>
        <input type="date" bind:value={formDateOfCreation} />
      </div>
      <div class="form-group">
        <label>Link</label>
        <input type="url" bind:value={formLink} placeholder="https://..." />
      </div>
    </div>

    <div class="form-group">
      <label>Weight</label>
      <select bind:value={formWeightId}>
        <option value="">None</option>
        {#each $lookups.weights as w}
          <option value={w.id}>{w.name}</option>
        {/each}
      </select>
    </div>

    <div class="form-group">
      <MultiSelect
        label="Work Types"
        options={$lookups.work_types}
        bind:selected={formWorkTypeIds}
        lookupTable="work_types"
      />
    </div>

    <div class="form-group">
      <MultiSelect
        label="Skills"
        options={$lookups.skills}
        bind:selected={formSkillIds}
        lookupTable="skills"
      />
    </div>

    <div class="form-group">
      <MultiSelect
        label="Tools"
        options={$lookups.tools}
        bind:selected={formToolIds}
        lookupTable="tools"
      />
    </div>

    <h3 style="margin-top: 20px;">Media</h3>
    <MediaManager bind:media={formMedia} />

    <div class="btn-group">
      <button type="submit" class="btn btn-primary" disabled={saving}>
        {saving ? 'Saving...' : editing ? 'Update' : 'Create'}
      </button>
      <button type="button" class="btn btn-ghost" on:click={() => showModal = false}>Cancel</button>
    </div>
  </form>
</Modal>

<style>
  .weight-badge {
    display: inline-block;
    font-size: 11px;
    padding: 1px 7px;
    background: rgba(212,162,46,0.15);
    color: var(--warning);
    border-radius: 3px;
    margin-left: 6px;
    font-weight: 400;
    vertical-align: middle;
  }
</style>
