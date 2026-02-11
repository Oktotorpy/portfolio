<script>
  import { onMount } from 'svelte';
  import { api } from '$lib/api.js';
  import { lookups } from '$lib/stores.js';

  let activeTab = 'skills';
  let message = '';
  let messageType = '';

  // Inline edit state
  let editingId = null;
  let editingName = '';
  let newName = '';

  const tabs = [
    { key: 'skills', label: 'Skills' },
    { key: 'work_types', label: 'Work Types' },
    { key: 'countries', label: 'Countries' }
  ];

  function switchTab(key) {
    activeTab = key;
    editingId = null;
    editingName = '';
    newName = '';
    message = '';
  }

  $: items = $lookups[activeTab] || [];

  async function refreshLookups() {
    $lookups = await api.getLookups();
  }

  async function addItem() {
    if (!newName.trim()) return;
    message = '';
    try {
      await api.addLookup(activeTab, newName.trim());
      newName = '';
      await refreshLookups();
      message = 'Item added';
      messageType = 'success';
    } catch (err) {
      message = err.message;
      messageType = 'error';
    }
  }

  function startEdit(item) {
    editingId = item.id;
    editingName = item.name;
  }

  function cancelEdit() {
    editingId = null;
    editingName = '';
  }

  async function saveEdit() {
    if (!editingName.trim()) return;
    message = '';
    try {
      await api.updateLookup(activeTab, editingId, editingName.trim());
      editingId = null;
      editingName = '';
      await refreshLookups();
      message = 'Item updated';
      messageType = 'success';
    } catch (err) {
      message = err.message;
      messageType = 'error';
    }
  }

  async function deleteItem(item) {
    if (!confirm(`Delete "${item.name}"? This may fail if the item is currently in use.`)) return;
    message = '';
    try {
      await api.deleteLookup(activeTab, item.id);
      await refreshLookups();
      message = 'Item deleted';
      messageType = 'success';
    } catch (err) {
      message = err.message;
      messageType = 'error';
    }
  }

  function handleKeydown(e) {
    if (e.key === 'Enter') {
      if (editingId) saveEdit();
      else addItem();
    }
    if (e.key === 'Escape' && editingId) cancelEdit();
  }
</script>

<h1>Settings</h1>

<div class="tabs">
  {#each tabs as tab}
    <button
      class="tab"
      class:active={activeTab === tab.key}
      on:click={() => switchTab(tab.key)}
    >
      {tab.label}
    </button>
  {/each}
</div>

{#if message}
  <div class="msg msg-{messageType}">{message}</div>
{/if}

<!-- Add new item -->
<div class="card" style="display: flex; gap: 8px; align-items: end; margin-bottom: 24px;">
  <div class="form-group" style="flex: 1; margin-bottom: 0;">
    <label>Add new {activeTab === 'work_types' ? 'work type' : activeTab === 'skills' ? 'skill' : 'country'}</label>
    <input
      type="text"
      bind:value={newName}
      on:keydown={handleKeydown}
      placeholder="Enter name..."
    />
  </div>
  <button class="btn btn-primary" on:click={addItem} disabled={!newName.trim()}>Add</button>
</div>

<!-- Item list -->
{#if items.length === 0}
  <div class="empty">No items yet.</div>
{:else}
  <div class="item-list">
    {#each items as item}
      <div class="item-row">
        {#if editingId === item.id}
          <input
            type="text"
            bind:value={editingName}
            on:keydown={handleKeydown}
            style="flex: 1; margin-right: 8px;"
            autofocus
          />
          <div class="item-actions">
            <button class="btn btn-sm btn-primary" on:click={saveEdit}>Save</button>
            <button class="btn btn-sm btn-ghost" on:click={cancelEdit}>Cancel</button>
          </div>
        {:else}
          <div class="item-info">
            <div class="item-name">{item.name}</div>
          </div>
          <div class="item-actions">
            <button class="btn btn-sm btn-ghost" on:click={() => startEdit(item)}>Edit</button>
            <button class="btn btn-sm btn-danger" on:click={() => deleteItem(item)}>Delete</button>
          </div>
        {/if}
      </div>
    {/each}
  </div>
{/if}
