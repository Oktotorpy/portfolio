<script>
  export let options = [];
  export let selected = [];
  export let label = '';

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
