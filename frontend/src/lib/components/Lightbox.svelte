<script>
  export let images = [];  // [{media_value}]
  export let startIndex = 0;
  export let show = false;

  let current = 0;

  $: if (show) current = startIndex;

  function close() { show = false; }
  function prev() { current = (current - 1 + images.length) % images.length; }
  function next() { current = (current + 1) % images.length; }

  function handleKey(e) {
    if (!show) return;
    if (e.key === 'Escape') close();
    if (e.key === 'ArrowLeft') prev();
    if (e.key === 'ArrowRight') next();
  }
</script>

<svelte:window on:keydown={handleKey} />

{#if show && images.length > 0}
  <!-- svelte-ignore a11y-click-events-have-key-events -->
  <!-- svelte-ignore a11y-no-static-element-interactions -->
  <div class="lightbox-backdrop" on:click={close}>
    <div class="lightbox-content" on:click|stopPropagation>
      <img src={images[current].media_value} alt="Enlarged view" />
    </div>

    <button class="lightbox-close" on:click={close}>×</button>

    {#if images.length > 1}
      <button class="lightbox-nav lightbox-prev" on:click|stopPropagation={prev}>‹</button>
      <button class="lightbox-nav lightbox-next" on:click|stopPropagation={next}>›</button>
      <div class="lightbox-counter">{current + 1} / {images.length}</div>
    {/if}
  </div>
{/if}

<style>
  .lightbox-backdrop {
    position: fixed; inset: 0; z-index: 1000;
    background: rgba(0, 0, 0, 0.92);
    display: flex; align-items: center; justify-content: center;
    cursor: zoom-out;
  }

  .lightbox-content {
    max-width: 90vw; max-height: 90vh;
    display: flex; align-items: center; justify-content: center;
    cursor: default;
  }

  .lightbox-content img {
    max-width: 90vw; max-height: 90vh;
    object-fit: contain; border-radius: 4px;
  }

  .lightbox-close {
    position: fixed; top: 16px; right: 20px;
    background: none; border: none; color: #888; font-size: 32px;
    cursor: pointer; z-index: 1001; line-height: 1;
    transition: color 0.2s;
  }
  .lightbox-close:hover { color: #fff; }

  .lightbox-nav {
    position: fixed; top: 50%; transform: translateY(-50%);
    background: rgba(255,255,255,0.08); border: none; color: #aaa;
    font-size: 36px; width: 48px; height: 64px; cursor: pointer;
    border-radius: 6px; z-index: 1001; transition: all 0.2s;
    display: flex; align-items: center; justify-content: center;
  }
  .lightbox-nav:hover { background: rgba(255,255,255,0.15); color: #fff; }
  .lightbox-prev { left: 16px; }
  .lightbox-next { right: 16px; }

  .lightbox-counter {
    position: fixed; bottom: 20px; left: 50%; transform: translateX(-50%);
    color: #888; font-size: 14px; z-index: 1001;
  }
</style>
