<script>
  import { api } from '$lib/api.js';
  import { lookups } from '$lib/stores.js';

  export let options = [];
  export let selected = [];
  export let label = '';
  export let lookupTable = '';  // e.g. 'skills', 'tools', 'countries', 'proficiencies'

  let newName = '';
  let creating = false;

  function toggle(id) {
    if (selected.includes(id)) {
      selected = selected.filter(s => s !== id);
    } else {
      selected = [...selected, id];
    }
  }

  function remove(id) {
    selected = selected.filter(s => s !== id);
  }

  async function createAndAdd() {
    if (!newName.trim() || !lookupTable) return;
    creating = true;
    try {
      const result = await api.addLookup(lookupTable, newName.trim());
      // Refresh lookups store
      const updated = await api.getLookups();
      $lookups = updated;
      // Add to selected
      if (!selected.includes(result.id)) {
        selected = [...selected, result.id];
      }
      newName = '';
    } catch (err) {
      console.error('Failed to create tag:', err);
    } finally {
      creating = false;
    }
  }

  function handleKeydown(e) {
    if (e.key === 'Enter') {
      e.preventDefault();
      createAndAdd();
    }
  }

  $: selectedItems = options.filter(o => selected.includes(o.id));
  $: availableItems = options.filter(o => !selected.includes(o.id));
</script>

{#if label}
  <label>{label}</label>
{/if}

<div class="multi-select">
  {#each selectedItems as item}
    <span class="chip">
      {item.name}
      <button type="button" on:click={() => remove(item.id)}>&times;</button>
    </span>
  {/each}
</div>

{#if availableItems.length > 0}
  <div class="multi-select-options">
    {#each availableItems as item}
      <button type="button" on:click={() => toggle(item.id)}>+ {item.name}</button>
    {/each}
  </div>
{/if}

{#if lookupTable}
  <div class="inline-create">
    <input
      type="text"
      bind:value={newName}
      on:keydown={handleKeydown}
      placeholder="Type to create new..."
      disabled={creating}
      class="inline-create-input"
    />
    {#if newName.trim()}
      <button type="button" class="inline-create-btn" on:click={createAndAdd} disabled={creating}>
        {creating ? '...' : '+ Create'}
      </button>
    {/if}
  </div>
{/if}

<style>
  .inline-create {
    display: flex;
    gap: 6px;
    margin-top: 6px;
    align-items: center;
  }

  .inline-create-input {
    flex: 1;
    padding: 5px 8px;
    background: var(--bg-input);
    border: 1px dashed var(--border);
    border-radius: var(--radius-sm);
    color: var(--text-dim);
    font-size: 12px;
    font-family: inherit;
  }

  .inline-create-input:focus {
    outline: none;
    border-color: var(--border-focus);
    border-style: solid;
    color: var(--text);
  }

  .inline-create-btn {
    padding: 5px 10px;
    background: var(--accent);
    border: none;
    border-radius: var(--radius-sm);
    color: white;
    font-size: 12px;
    cursor: pointer;
    font-family: inherit;
    white-space: nowrap;
  }

  .inline-create-btn:hover { opacity: 0.9; }
  .inline-create-btn:disabled { opacity: 0.5; }
</style>
