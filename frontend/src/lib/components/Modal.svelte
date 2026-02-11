<script>
  export let show = false;
  export let title = '';

  function close() {
    show = false;
  }

  function handleBackdrop(e) {
    if (e.target === e.currentTarget) close();
  }

  function handleKey(e) {
    if (e.key === 'Escape') close();
  }
</script>

<svelte:window on:keydown={handleKey} />

{#if show}
  <div class="modal-backdrop" on:click={handleBackdrop}>
    <div class="modal">
      <h2>{title}</h2>
      <slot />
    </div>
  </div>
{/if}
