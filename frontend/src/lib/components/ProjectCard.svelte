<script>
  import { formatDate } from '$lib/utils.js';

  export let project;
  export let slug = '';

  let copied = false;

  function getYouTubeId(url) {
    if (!url) return null;
    const match = url.match(/(?:youtube\.com\/(?:watch\?v=|embed\/)|youtu\.be\/)([a-zA-Z0-9_-]{11})/);
    return match ? match[1] : null;
  }

  async function copyLink() {
    const url = `${window.location.origin}/${slug}#project-${project.id}`;
    try {
      await navigator.clipboard.writeText(url);
      copied = true;
      setTimeout(() => copied = false, 2000);
    } catch {}
  }

  $: hasMedia = project.content_type && project.content_value;
  $: youtubeId = project.content_type === 'youtube' ? getYouTubeId(project.content_value) : null;
  $: roleName = project.role?.name || '';
  $: jobName = project.role?.job?.name || '';
</script>

<article
  class="project-card"
  class:no-media={!hasMedia}
  id="project-{project.id}"
  data-role-id={project.role_id}
>
  {#if hasMedia}
    <div class="card-media">
      {#if project.content_type === 'image'}
        <img src={project.content_value} alt={project.name} loading="lazy" />
      {:else if project.content_type === 'video'}
        <video src={project.content_value} controls preload="metadata"></video>
      {:else if youtubeId}
        <iframe
          src="https://www.youtube-nocookie.com/embed/{youtubeId}"
          title={project.name}
          frameborder="0"
          allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture"
          allowfullscreen
        ></iframe>
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
        {roleName}{#if jobName} · {jobName}{/if}
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

    {#if project.skills?.length > 0}
      <div class="card-skills">
        {#each project.skills as skill}
          <span class="skill-tag">{skill.name}</span>
        {/each}
      </div>
    {/if}
  </div>
</article>

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

  .project-card:hover {
    border-color: #2a2d35;
  }

  .project-card.no-media {
    grid-template-columns: 1fr;
  }

  .card-media {
    position: relative;
    background: #0f1014;
    display: flex;
    align-items: center;
    justify-content: center;
    min-height: 200px;
  }

  .card-media img {
    width: 100%;
    height: 100%;
    object-fit: cover;
    display: block;
  }

  .card-media video {
    width: 100%;
    height: 100%;
    object-fit: contain;
    display: block;
  }

  .card-media iframe {
    width: 100%;
    aspect-ratio: 16/9;
    display: block;
  }

  .card-body {
    padding: 24px;
    display: flex;
    flex-direction: column;
    justify-content: space-between;
  }

  .card-content {
    flex: 1;
  }

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

  .copy-btn:hover {
    color: #6b6e7a;
    border-color: #2a2d35;
  }

  .copy-btn.copied {
    color: #4a9;
  }

  .card-meta {
    font-size: 13px;
    color: #6b6e7a;
    margin-bottom: 4px;
  }

  .card-date {
    font-size: 12px;
    color: #4e515c;
    margin-bottom: 12px;
  }

  .card-description {
    font-size: 13px;
    color: #8a8d98;
    line-height: 1.6;
    margin-bottom: 12px;
  }

  .card-link {
    font-size: 13px;
    color: #7a7faa;
    text-decoration: none;
    transition: color 0.2s;
  }

  .card-link:hover {
    color: #a0a4cc;
  }

  .card-skills {
    display: flex;
    flex-wrap: wrap;
    gap: 4px;
    padding-top: 16px;
    border-top: 1px solid #1e2028;
    margin-top: 16px;
  }

  .skill-tag {
    font-size: 11px;
    color: #5a5e6a;
    background: #111318;
    padding: 3px 8px;
    border-radius: 3px;
    border: 1px solid #1e2028;
  }

  @media (max-width: 768px) {
    .project-card {
      grid-template-columns: 1fr;
    }

    .card-media {
      min-height: 180px;
      max-height: 240px;
    }

    .card-body {
      padding: 16px;
    }
  }
</style>
