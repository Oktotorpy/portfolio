<script>
  import { formatDate } from '$lib/utils.js';
  import Lightbox from './Lightbox.svelte';

  export let project;
  export let slug = '';

  let copied = false;
  let showLightbox = false;
  let lightboxIndex = 0;
  let currentVideoIndex = 0;

  function getYouTubeId(url) {
    if (!url) return null;
    const match = url.match(/(?:youtube\.com\/(?:watch\?v=|embed\/)|youtu\.be\/)([a-zA-Z0-9_-]{11})/);
    return match ? match[1] : null;
  }

  function slugify(text) {
    return text.toLowerCase().trim().replace(/[^\w\s-]/g, '').replace(/[\s_]+/g, '-').replace(/-+/g, '-');
  }

  async function copyLink() {
    // Derive slug from project's first work type if no slug provided
    const s = slug || (project.work_types?.[0] ? slugify(project.work_types[0].name) : '');
    const url = s
      ? `${window.location.origin}/${s}#project-${project.id}`
      : `${window.location.origin}/#project-${project.id}`;
    try {
      await navigator.clipboard.writeText(url);
      copied = true;
      setTimeout(() => copied = false, 2000);
    } catch {}
  }

  function openImage(index) {
    lightboxIndex = index;
    showLightbox = true;
  }

  function prevVideo() {
    currentVideoIndex = (currentVideoIndex - 1 + videoMedia.length) % videoMedia.length;
  }
  function nextVideo() {
    currentVideoIndex = (currentVideoIndex + 1) % videoMedia.length;
  }

  // Group media by type
  $: imageMedia = (project.media || []).filter(m => m.media_type === 'image');
  $: videoMedia = (project.media || []).filter(m => m.media_type === 'video' || m.media_type === 'youtube');
  $: hasMedia = imageMedia.length > 0 || videoMedia.length > 0;
  $: roleName = project.role?.name || '';
  $: department = project.role?.department || '';
  $: jobName = project.role?.job?.name || '';
  // Reset video index when project changes
  $: if (project.id) currentVideoIndex = 0;
</script>

<article
  class="project-card"
  class:no-media={!hasMedia}
  id="project-{project.id}"
  data-role-id={project.role_id}
>
  {#if hasMedia}
    <div class="card-media">
      <!-- Images: mosaic if multiple, single if one -->
      {#if imageMedia.length === 1}
        <!-- svelte-ignore a11y-click-events-have-key-events -->
        <!-- svelte-ignore a11y-no-noninteractive-element-interactions -->
        <img src={imageMedia[0].media_value} alt={project.name} loading="lazy"
          class="clickable-img" on:click={() => openImage(0)} />
      {:else if imageMedia.length > 1}
        <div class="mosaic" class:mosaic-2={imageMedia.length === 2} class:mosaic-3={imageMedia.length === 3} class:mosaic-4={imageMedia.length >= 4}>
          {#each imageMedia.slice(0, 4) as img, i}
            <!-- svelte-ignore a11y-click-events-have-key-events -->
            <!-- svelte-ignore a11y-no-noninteractive-element-interactions -->
            <img src={img.media_value} alt="{project.name} {i+1}" loading="lazy"
              class="clickable-img mosaic-img" on:click={() => openImage(i)} />
          {/each}
          {#if imageMedia.length > 4}
            <!-- svelte-ignore a11y-click-events-have-key-events -->
            <!-- svelte-ignore a11y-no-static-element-interactions -->
            <div class="mosaic-more" on:click={() => openImage(4)}>+{imageMedia.length - 4}</div>
          {/if}
        </div>
      {/if}

      <!-- Videos: with arrow navigation -->
      {#if videoMedia.length > 0}
        <div class="video-container">
          {#if videoMedia[currentVideoIndex].media_type === 'video'}
            <video src={videoMedia[currentVideoIndex].media_value} controls preload="metadata"></video>
          {:else}
            {@const ytId = getYouTubeId(videoMedia[currentVideoIndex].media_value)}
            {#if ytId}
              <iframe
                src="https://www.youtube-nocookie.com/embed/{ytId}"
                title={project.name}
                frameborder="0"
                allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture"
                allowfullscreen
              ></iframe>
            {/if}
          {/if}

          {#if videoMedia.length > 1}
            <button class="video-nav video-prev" on:click={prevVideo}>‹</button>
            <button class="video-nav video-next" on:click={nextVideo}>›</button>
            <div class="video-counter">{currentVideoIndex + 1}/{videoMedia.length}</div>
          {/if}
        </div>
      {/if}
    </div>
  {/if}

  <div class="card-body">
    <div class="card-content">
      <div class="card-header">
        <h3 class="card-title">{project.name}</h3>
        <button
          class="copy-btn"
          class:copied
          on:click={copyLink}
          title="Copy link to project"
        >
          {copied ? '✓' : '⎘'}
        </button>
      </div>

      <p class="card-meta">
        {roleName}{#if department} · {department}{/if}{#if jobName} · {jobName}{/if}
      </p>

      {#if project.date_of_creation}
        <p class="card-date">{formatDate(project.date_of_creation)}</p>
      {/if}

      {#if project.description}
        <p class="card-description">{project.description}</p>
      {/if}

      {#if project.link}
        <a href={project.link} target="_blank" rel="noopener" class="card-link">
          View project ↗
        </a>
      {/if}
    </div>

    <div class="card-tags">
      {#if project.skills?.length > 0}
        <div class="tag-row">
          {#each project.skills as skill}
            <span class="skill-tag">{skill.name}</span>
          {/each}
        </div>
      {/if}
      {#if project.tools?.length > 0}
        <div class="tag-row">
          {#each project.tools as tool}
            <span class="tool-tag">{tool.name}</span>
          {/each}
        </div>
      {/if}
    </div>
  </div>
</article>

<Lightbox images={imageMedia} startIndex={lightboxIndex} bind:show={showLightbox} />

<style>
  .project-card {
    display: grid;
    grid-template-columns: 1fr 1fr;
    background: #16181e;
    border: 1px solid #1e2028;
    border-radius: 8px;
    overflow: hidden;
    transition: border-color 0.2s;
  }

  .project-card:hover { border-color: #2a2d35; }
  .project-card.no-media { grid-template-columns: 1fr; }

  .card-media {
    position: relative;
    background: #0f1014;
    display: flex;
    flex-direction: column;
    min-height: 200px;
  }

  .card-media > img {
    width: 100%; height: 100%; object-fit: cover; display: block;
  }

  .clickable-img { cursor: zoom-in; transition: opacity 0.2s; }
  .clickable-img:hover { opacity: 0.85; }

  /* Mosaic layouts */
  .mosaic { display: grid; width: 100%; height: 100%; min-height: 200px; gap: 2px; }
  .mosaic-2 { grid-template-columns: 1fr 1fr; }
  .mosaic-3 { grid-template-columns: 1fr 1fr; grid-template-rows: 1fr 1fr; }
  .mosaic-3 .mosaic-img:first-child { grid-row: 1 / 3; }
  .mosaic-4 { grid-template-columns: 1fr 1fr; grid-template-rows: 1fr 1fr; }
  .mosaic-img { width: 100%; height: 100%; object-fit: cover; display: block; }
  .mosaic-more {
    position: absolute; bottom: 8px; right: 8px; background: rgba(0,0,0,0.7);
    color: #ddd; font-size: 13px; padding: 4px 10px; border-radius: 4px; cursor: pointer;
  }

  /* Video container with arrows */
  .video-container { position: relative; width: 100%; }
  .video-container video { width: 100%; display: block; }
  .video-container iframe { width: 100%; aspect-ratio: 16/9; display: block; }

  .video-nav {
    position: absolute; top: 50%; transform: translateY(-50%);
    background: rgba(0,0,0,0.6); border: none; color: #ccc;
    font-size: 24px; width: 36px; height: 36px; border-radius: 50%;
    cursor: pointer; z-index: 2; display: flex; align-items: center; justify-content: center;
    transition: all 0.2s;
  }
  .video-nav:hover { background: rgba(0,0,0,0.85); color: #fff; }
  .video-prev { left: 8px; }
  .video-next { right: 8px; }

  .video-counter {
    position: absolute; bottom: 8px; right: 8px; background: rgba(0,0,0,0.6);
    color: #aaa; font-size: 11px; padding: 2px 8px; border-radius: 3px;
  }

  /* Card body */
  .card-body {
    padding: 24px;
    display: flex;
    flex-direction: column;
    justify-content: space-between;
  }

  .card-content { flex: 1; }

  .card-header {
    display: flex; align-items: flex-start; justify-content: space-between;
    gap: 12px; margin-bottom: 6px;
  }

  .card-title {
    font-size: 16px; font-weight: 600; color: #e0e2e8;
    letter-spacing: -0.01em; line-height: 1.3;
  }

  .copy-btn {
    background: none; border: 1px solid transparent; color: #3a3d48;
    font-size: 18px; cursor: pointer; padding: 2px 6px; border-radius: 4px;
    transition: all 0.2s; flex-shrink: 0; line-height: 1;
  }
  .copy-btn:hover { color: #6b6e7a; border-color: #2a2d35; }
  .copy-btn.copied { color: #4a9; }

  .card-meta { font-size: 13px; color: #6b6e7a; margin-bottom: 4px; }
  .card-date { font-size: 12px; color: #4e515c; margin-bottom: 12px; }
  .card-description { font-size: 13px; color: #8a8d98; line-height: 1.6; margin-bottom: 12px; }

  .card-link { font-size: 13px; color: #7a7faa; text-decoration: none; transition: color 0.2s; }
  .card-link:hover { color: #a0a4cc; }

  .card-tags {
    padding-top: 16px;
    border-top: 1px solid #1e2028;
    margin-top: 16px;
    display: flex;
    flex-direction: column;
    gap: 6px;
  }

  .tag-row { display: flex; flex-wrap: wrap; gap: 4px; }

  .skill-tag {
    font-size: 11px; color: #5a5e6a; background: #111318;
    padding: 3px 8px; border-radius: 3px; border: 1px solid #1e2028;
  }

  .tool-tag {
    font-size: 11px; color: #7a7faa; background: rgba(122, 127, 170, 0.08);
    padding: 3px 8px; border-radius: 3px; border: 1px solid rgba(122, 127, 170, 0.2);
  }

  @media (max-width: 768px) {
    .project-card { grid-template-columns: 1fr; }
    .card-media { min-height: 180px; max-height: 300px; }
    .card-body { padding: 16px; }
    .mosaic { min-height: 180px; }
  }
</style>
