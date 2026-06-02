<script>
  import { onMount } from 'svelte';
  import { api } from '$lib/api.js';

  let name = '';
  let email = '';
  let linkedin = '';
  let description = '';
  let saving = false;
  let message = '';
  let messageType = '';

  onMount(async () => {
    try {
      const data = await api.getContact();
      name = data.name;
      email = data.email;
      linkedin = data.linkedin;
      description = data.description || '';
    } catch (err) {
      message = err.message;
      messageType = 'error';
    }
  });

  async function save() {
    saving = true;
    message = '';
    try {
      const data = await api.updateContact({ name, email, linkedin, description });
      name = data.name;
      email = data.email;
      linkedin = data.linkedin;
      description = data.description || '';
      message = 'Saved successfully';
      messageType = 'success';
    } catch (err) {
      message = err.message;
      messageType = 'error';
    } finally {
      saving = false;
    }
  }
</script>

<h1>Contact Information</h1>

{#if message}
  <div class="msg msg-{messageType}">{message}</div>
{/if}

<div class="card">
  <form on:submit|preventDefault={save}>
    <div class="form-group">
      <label>Full Name</label>
      <input type="text" bind:value={name} placeholder="Your name" />
    </div>

    <div class="form-group">
      <label>Email</label>
      <input type="email" bind:value={email} placeholder="you@example.com" />
    </div>

    <div class="form-group">
      <label>LinkedIn URL</label>
      <input type="url" bind:value={linkedin} placeholder="https://linkedin.com/in/..." />
    </div>

    <div class="form-group">
      <label>Description</label>
      <textarea bind:value={description} placeholder="A short bio or description..." rows="4"></textarea>
    </div>

    <div class="btn-group">
      <button type="submit" class="btn btn-primary" disabled={saving}>
        {saving ? 'Saving...' : 'Save'}
      </button>
    </div>
  </form>
</div>
