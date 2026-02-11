<script>
  import { onMount, onDestroy } from 'svelte';
  import { page } from '$app/stores';
  import { currentRoleId } from '$lib/stores.js';
  import { slugify, unslugify } from '$lib/utils.js';
  import PublicShell from '$lib/components/PublicShell.svelte';
  import ProjectCard from '$lib/components/ProjectCard.svelte';

  export let data;

  let observer;
  let cardContainer;

  $: slug = $page.params.slug;
  $: workType = unslugify(slug, data.workTypes || []);

  $: projects = workType
    ? data.projects
        .filter(p => p.work_types?.some(wt => wt.id === workType.id))
        .sort((a, b) => {
          const da = a.date_of_creation || '0000';
          const db = b.date_of_creation || '0000';
          return db.localeCompare(da);
        })
    : [];

  $: if (projects.length > 0 && projects[0].role_id) {
    $currentRoleId = projects[0].role_id;
  }

  onMount(() => { setupObserver(); });
  onDestroy(() => { if (observer) observer.disconnect(); });

  function setupObserver() {
    if (observer) observer.disconnect();
    observer = new IntersectionObserver(
      (entries) => {
        const visible = entries
          .filter(e => e.isIntersecting)
          .sort((a, b) => a.boundingClientRect.top - b.boundingClientRect.top);
        if (visible.length > 0) {
          const roleId = parseInt(visible[0].target.dataset.roleId);
          if (roleId) $currentRoleId = roleId;
        }
      },
      { rootMargin: '-10% 0px -70% 0px', threshold: 0 }
    );

    requestAnimationFrame(() => {
      if (cardContainer) {
        const cards = cardContainer.querySelectorAll('[data-role-id]');
        cards.forEach(card => observer.observe(card));
      }
    });
  }

  $: if (slug && cardContainer) {
    requestAnimationFrame(() => setupObserver());
  }
</script>

<svelte:head>
  {#if workType}
    <title>{workType.name} — Portfolio</title>
  {/if}
</svelte:head>

<PublicShell contact={data.contact} roles={data.roles} workTypes={data.workTypes}>
  {#if !workType}
    <div class="empty-state"><p>Page not found</p></div>
  {:else if projects.length === 0}
    <div class="empty-state"><p>No projects in {workType.name} yet</p></div>
  {:else}
    <div class="project-list" bind:this={cardContainer}>
      {#each projects as project (project.id)}
        <ProjectCard {project} {slug} />
      {/each}
    </div>
  {/if}
</PublicShell>

<style>
  .project-list { display: flex; flex-direction: column; gap: 16px; }
  .empty-state { display: flex; align-items: center; justify-content: center; padding: 120px 0; color: #2a2d35; font-size: 16px; }
</style>
