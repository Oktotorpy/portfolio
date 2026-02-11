<script>
  import { formatDate } from '$lib/utils.js';
  import Lightbox from './Lightbox.svelte';

  export let project;
  export let slug = '';

  let copied = false;
  let showLightbox = false;
  let lightboxIndex = 0;

  // Video carousel state (for regular videos/embeds)
  let currentVideoIndex = 0;
  // Shorts carousel state (pairs of 2)
  let currentShortsPage = 0;
  // Click-to-play state for uploaded videos
  let activeVideoId = null;

  /* ── Helpers ─────────────────────────────────────────── */

  function getYouTubeId(url) {
    if (!url) return null;
    const m = url.match(/(?:youtube\.com\/(?:watch\?v=|embed\/|shorts\/)|youtu\.be\/)([a-zA-Z0-9_-]{11})/);
    return m ? m[1] : null;
  }

  function isShorts(url) {
    return /youtube\.com\/shorts\//i.test(url || '');
  }

  function slugify(text) {
    return text.toLowerCase().trim().replace(/[^\w\s-]/g, '').replace(/[\s_]+/g, '-').replace(/-+/g, '-');
  }

  /* ── Copy project link ───────────────────────────────── */

  async function copyLink() {
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

  /* ── Lightbox ────────────────────────────────────────── */

  function openImage(index) {
    lightboxIndex = index;
    showLightbox = true;
  }

  /* ── Video carousel (regular, non-Shorts) ────────────── */

  function prevVideo() {
    currentVideoIndex = (currentVideoIndex - 1 + regularVideoMedia.length) % regularVideoMedia.length;
    activeVideoId = null;
  }
  function nextVideo() {
    currentVideoIndex = (currentVideoIndex + 1) % regularVideoMedia.length;
    activeVideoId = null;
  }

  /* ── Shorts carousel (pairs of 2) ───────────────────── */

  function prevShortsPage() {
    currentShortsPage = (currentShortsPage - 1 + shortsTotalPages) % shortsTotalPages;
  }
  function nextShortsPage() {
    currentShortsPage = (currentShortsPage + 1) % shortsTotalPages;
  }

  /* ── Click-to-play for uploaded videos ───────────────── */

  function playVideo(id) {
    activeVideoId = id;
  }

  /* ── Media classification ────────────────────────────── */

  $: imageMedia = (project.media || []).filter(m => m.media_type === 'image');

  // YouTube Shorts: portrait embeds
  $: shortsMedia = (project.media || []).filter(m =>
    m.media_type === 'youtube' && isShorts(m.media_value)
  );

  // Regular videos + non-Shorts YouTube
  $: regularVideoMedia = (project.media || []).filter(m =>
    m.media_type === 'video' || (m.media_type === 'youtube' && !isShorts(m.media_value))
  );

  $: hasImages = imageMedia.length > 0;
  $: hasRegularVideo = regularVideoMedia.length > 0;
  $: hasShorts = shortsMedia.length > 0;
  $: hasMedia = hasImages || hasRegularVideo || hasShorts;

  // Shorts pagination: 2 per page
  $: shortsTotalPages = Math.ceil(shortsMedia.length / 2);
  $: shortsCurrentPair = shortsMedia.slice(currentShortsPage * 2, currentShortsPage * 2 + 2);

  // Image grid columns based on count
  $: imageGridCols = imageMedia.length === 1 ? 1
    : imageMedia.length === 2 ? 2
    : imageMedia.length === 4 ? 2
    : 3;

  $: roleName = project.role?.name || '';
  $: department = project.role?.department || '';
  $: jobName = project.role?.job?.name || '';

  // Reset carousel states when project changes
  $: if (project.id) {
    currentVideoIndex = 0;
    currentShortsPage = 0;
    activeVideoId = null;
  }
</script>

<article
  class="project-card"
  class:no-media={!hasMedia}
  id="project-{project.id}"
  data-role-id={project.role_id}
>
  {#if hasMedia}
    <div class="card-media">

      <!-- ═══ IMAGES: always on top ═══ -->
      {#if hasImages}
        <div class="image-section">
          {#if imageMedia.length === 1}
            <!-- svelte-ignore a11y-click-events-have-key-events -->
            <!-- svelte-ignore a11y-no-noninteractive-element-interactions -->
            <img
              src={imageMedia[0].media_value}
              alt={project.name}
              loading="lazy"
              class="single-img clickable-img"
              on:click={() => openImage(0)}
            />
          {:else}
            <div class="mosaic cols-{imageGridCols}">
              {#each imageMedia as img, i}
                <!-- svelte-ignore a11y-click-events-have-key-events -->
                <!-- svelte-ignore a11y-no-noninteractive-element-interactions -->
                <img
                  src={img.media_value}
                  alt="{project.name} {i+1}"
                  loading="lazy"
                  class="mosaic-img clickable-img"
                  on:click={() => openImage(i)}
                />
              {/each}
            </div>
          {/if}
        </div>
      {/if}

      <!-- ═══ REGULAR VIDEOS / YOUTUBE (non-Shorts): below images ═══ -->
      {#if hasRegularVideo}
        
          {@const currentMedia = regularVideoMedia[currentVideoIndex]}
			<div class="video-section">
          {#if currentMedia.media_type === 'video'}
            <!-- Uploaded video: click-to-play -->
            {#if activeVideoId === (currentMedia.id || currentVideoIndex)}
              <video
                src={currentMedia.media_value}
                controls
                autoplay
                preload="auto"
                class="video-player"
              ></video>
            {:else}
              <!-- svelte-ignore a11y-click-events-have-key-events -->
              <!-- svelte-ignore a11y-no-static-element-interactions -->
              <div class="video-poster" on:click={() => playVideo(currentMedia.id || currentVideoIndex)}>
                <div class="poster-placeholder">
                  <div class="play-btn">▶</div>
                  <span class="poster-label">Click to play</span>
                </div>
              </div>
            {/if}
          {:else}
            <!-- YouTube embed (regular, landscape) -->
            {@const ytId = getYouTubeId(currentMedia.media_value)}
            {#if ytId}
              <iframe
                src="https://www.youtube-nocookie.com/embed/{ytId}"
                title={project.name}
                frameborder="0"
                allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture"
                allowfullscreen
                class="yt-landscape"
              ></iframe>
            {/if}
          {/if}

          {#if regularVideoMedia.length > 1}
            <button class="video-nav video-prev" on:click={prevVideo}>‹</button>
            <button class="video-nav video-next" on:click={nextVideo}>›</button>
            <div class="video-counter">{currentVideoIndex + 1}/{regularVideoMedia.length}</div>
          {/if}
        </div>
      {/if}

      <!-- ═══ YOUTUBE SHORTS: pairs, carousel ═══ -->
      {#if hasShorts}
        <div class="shorts-section">
          <div class="shorts-pair">
            {#each shortsCurrentPair as short}
              {@const ytId = getYouTubeId(short.media_value)}
              {#if ytId}
                <iframe
                  src="https://www.youtube-nocookie.com/embed/{ytId}"
                  title={project.name}
                  frameborder="0"
                  allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture"
                  allowfullscreen
                  class="yt-short"
                ></iframe>
              {/if}
            {/each}
          </div>

          {#if shortsTotalPages > 1}
            <button class="video-nav shorts-prev" on:click={prevShortsPage}>‹</button>
            <button class="video-nav shorts-next" on:click={nextShortsPage}>›</button>
            <div class="shorts-counter">{currentShortsPage + 1}/{shortsTotalPages}</div>
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
  /* ── Card layout ────────────────────────────────── */

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

  /* ── Media container ────────────────────────────── */

  .card-media {
    background: #0f1014;
    display: flex;
    flex-direction: column;
    justify-content: center;
  }

  /* ── Image section ──────────────────────────────── */

  .image-section {
    display: flex;
    align-items: center;
    justify-content: center;
    overflow: hidden;
  }

  .single-img {
    width: 100%;
    max-height: 400px;
    object-fit: cover;
    display: block;
  }

  .clickable-img { cursor: zoom-in; transition: opacity 0.2s; }
  .clickable-img:hover { opacity: 0.85; }

  /* ── Mosaic grid (all images visible) ───────────── */

  .mosaic {
    display: grid;
    width: 100%;
    gap: 2px;
  }

  .mosaic.cols-1 { grid-template-columns: 1fr; }
  .mosaic.cols-2 { grid-template-columns: 1fr 1fr; }
  .mosaic.cols-3 { grid-template-columns: 1fr 1fr 1fr; }

  .mosaic-img {
    width: 100%;
    aspect-ratio: 16 / 10;
    object-fit: cover;
    display: block;
  }

  /* ── Video section (regular / landscape YT) ─────── */

  .video-section {
    position: relative;
    width: 100%;
  }

  .video-player {
    width: 100%;
    display: block;
    background: #000;
  }

  .yt-landscape {
    width: 100%;
    aspect-ratio: 16 / 9;
    display: block;
    border: none;
  }

  /* Click-to-play poster */
  .video-poster {
    position: relative;
    cursor: pointer;
    width: 100%;
  }

  .poster-placeholder {
    width: 100%;
    aspect-ratio: 16 / 9;
    background: #111318;
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    gap: 10px;
    transition: background 0.2s;
  }

  .video-poster:hover .poster-placeholder {
    background: #181b22;
  }

  .play-btn {
    width: 56px;
    height: 56px;
    border-radius: 50%;
    background: rgba(255, 255, 255, 0.08);
    color: #8a8d98;
    font-size: 22px;
    display: flex;
    align-items: center;
    justify-content: center;
    padding-left: 4px;
    transition: transform 0.2s, background 0.2s, color 0.2s;
  }

  .video-poster:hover .play-btn {
    transform: scale(1.1);
    background: rgba(255, 255, 255, 0.12);
    color: #e0e2e8;
  }

  .poster-label {
    font-size: 12px;
    color: #4e515c;
    transition: color 0.2s;
  }

  .video-poster:hover .poster-label { color: #6b6e7a; }

  /* Video navigation arrows */
  .video-nav {
    position: absolute;
    top: 50%;
    transform: translateY(-50%);
    background: rgba(0, 0, 0, 0.55);
    border: none;
    color: #ccc;
    font-size: 24px;
    width: 36px;
    height: 36px;
    border-radius: 50%;
    cursor: pointer;
    z-index: 2;
    display: flex;
    align-items: center;
    justify-content: center;
    transition: all 0.2s;
  }
  .video-nav:hover { background: rgba(0, 0, 0, 0.85); color: #fff; }
  .video-prev, .shorts-prev { left: 8px; }
  .video-next, .shorts-next { right: 8px; }

  .video-counter, .shorts-counter {
    position: absolute;
    bottom: 8px;
    right: 8px;
    background: rgba(0, 0, 0, 0.6);
    color: #aaa;
    font-size: 11px;
    padding: 2px 8px;
    border-radius: 3px;
  }

  /* ── Shorts section (portrait, pairs of 2) ──────── */

  .shorts-section {
    position: relative;
    width: 100%;
    padding: 4px;
  }

  .shorts-pair {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 4px;
  }

  .yt-short {
    width: 100%;
    aspect-ratio: 9 / 16;
    border: none;
    border-radius: 4px;
    display: block;
  }

  /* Single short on last page: center it */
  .shorts-pair :global(:only-child) {
    grid-column: 1 / -1;
    max-width: 50%;
    justify-self: center;
  }

  .shorts-prev, .shorts-next { top: 50%; }

  /* ── Card body ──────────────────────────────────── */

  .card-body {
    padding: 24px;
    display: flex;
    flex-direction: column;
    justify-content: space-between;
  }

  .card-content { flex: 1; }

  .card-header {
    display: flex;
    align-items: flex-start;
    justify-content: space-between;
    gap: 12px;
    margin-bottom: 6px;
  }

  .card-title {
    font-size: 16px;
    font-weight: 600;
    color: #e0e2e8;
    letter-spacing: -0.01em;
    line-height: 1.3;
  }

  .copy-btn {
    background: none;
    border: 1px solid transparent;
    color: #3a3d48;
    font-size: 18px;
    cursor: pointer;
    padding: 2px 6px;
    border-radius: 4px;
    transition: all 0.2s;
    flex-shrink: 0;
    line-height: 1;
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
    font-size: 11px;
    color: #5a5e6a;
    background: #111318;
    padding: 3px 8px;
    border-radius: 3px;
    border: 1px solid #1e2028;
  }

  .tool-tag {
    font-size: 11px;
    color: #7a7faa;
    background: rgba(122, 127, 170, 0.08);
    padding: 3px 8px;
    border-radius: 3px;
    border: 1px solid rgba(122, 127, 170, 0.2);
  }

  /* ── Mobile ─────────────────────────────────────── */

  @media (max-width: 768px) {
    .project-card { grid-template-columns: 1fr; }
    .card-media { min-height: auto; }
    .card-body { padding: 16px; }
    .single-img { max-height: 280px; }
  }
</style>
