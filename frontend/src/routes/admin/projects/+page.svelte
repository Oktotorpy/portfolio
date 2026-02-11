<script>
  import { onMount } from 'svelte';
  import { api } from '$lib/api.js';
  import { lookups } from '$lib/stores.js';
  import Modal from '$lib/components/Modal.svelte';
  import MultiSelect from '$lib/components/MultiSelect.svelte';
  import FileUpload from '$lib/components/FileUpload.svelte';

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
  let formContentType = '';
  let formContentValue = '';
  let formSkillIds = [];
  let formWorkTypeIds = [];

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
    formContentType = '';
    formContentValue = '';
    formSkillIds = [];
    formWorkTypeIds = [];
    showModal = true;
  }

  function openEdit(project) {
    editing = project;
    formName = project.name;
    formRoleId = project.role_id;
    formDescription = project.description || '';
    formDateOfCreation = project.date_of_creation || '';
    formLink = project.link || '';
    formContentType = project.content_type || '';
    formContentValue = project.content_value || '';
    formSkillIds = project.skills.map(s => s.id);
    formWorkTypeIds = project.work_types.map(wt => wt.id);
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
        content_type: formContentType || null,
        content_value: formContentValue || null,
        skill_ids: formSkillIds,
        work_type_ids: formWorkTypeIds
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

  function handleContentUpload(e) {
    formContentValue = e;
  }

  $: if (filterRoleId !== undefined) loadProjects();

  // Group roles by job for the selector
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
          <div class="item-name">{project.name}</div>
          <div class="item-meta">
            {getRoleName(project.role_id)}
            {#if project.date_of_creation} · {project.date_of_creation}{/if}
            {#if project.content_type} · {project.content_type}{/if}
          </div>
          <div style="margin-top: 4px;">
            {#each project.work_types as wt}
              <span class="tag">{wt.name}</span>
            {/each}
            {#each project.skills as skill}
              <span class="tag" style="background: rgba(61,170,109,0.15); color: var(--success);">{skill.name}</span>
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
      <MultiSelect
        label="Work Types"
        options={$lookups.work_types}
        bind:selected={formWorkTypeIds}
      />
    </div>

    <div class="form-group">
      <MultiSelect
        label="Skills"
        options={$lookups.skills}
        bind:selected={formSkillIds}
      />
    </div>

    <h3 style="margin-top: 20px;">Content</h3>

    <div class="form-group">
      <label>Content Type</label>
      <select bind:value={formContentType}>
        <option value="">None</option>
        <option value="image">Image</option>
        <option value="video">Video</option>
        <option value="youtube">YouTube Embed</option>
      </select>
    </div>

    {#if formContentType === 'image'}
      <FileUpload bind:value={formContentValue} label="Image" accept="image/*" />
    {:else if formContentType === 'video'}
      <FileUpload bind:value={formContentValue} label="Video" accept="video/*" />
    {:else if formContentType === 'youtube'}
      <div class="form-group">
        <label>YouTube URL</label>
        <input type="url" bind:value={formContentValue} placeholder="https://www.youtube.com/watch?v=..." />
      </div>
    {/if}

    <div class="btn-group">
      <button type="submit" class="btn btn-primary" disabled={saving}>
        {saving ? 'Saving...' : editing ? 'Update' : 'Create'}
      </button>
      <button type="button" class="btn btn-ghost" on:click={() => showModal = false}>Cancel</button>
    </div>
  </form>
</Modal>
