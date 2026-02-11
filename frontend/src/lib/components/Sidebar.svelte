<script>
  import { currentRoleId } from '$lib/stores.js';
  import { formatDateRange } from '$lib/utils.js';

  export let contact = {};
  export let roles = [];

  let displayRole = null;
  let displayJob = null;
  let roleOpacity = 1;
  let roleTranslate = 0;
  let prevRoleId = null;

  $: activeRole = roles.find(r => r.id === $currentRoleId) || null;
  $: activeJob = activeRole?.job || null;

  $: if ($currentRoleId !== prevRoleId) {
    if (prevRoleId !== null && activeRole) {
      roleOpacity = 0;
      roleTranslate = -16;
      setTimeout(() => {
        displayRole = activeRole;
        displayJob = activeJob;
        prevRoleId = $currentRoleId;
        roleTranslate = 16;
        requestAnimationFrame(() => {
          requestAnimationFrame(() => {
            roleOpacity = 1;
            roleTranslate = 0;
          });
        });
      }, 180);
    } else {
      displayRole = activeRole;
      displayJob = activeJob;
      prevRoleId = $currentRoleId;
    }
  }
</script>

<aside class="sidebar-public">
  <div class="sidebar-contact">
    {#if contact.name}
      <h1 class="contact-name">{contact.name}</h1>
    {/if}
    {#if contact.email}
      <a href="/cdn-cgi/l/email-protection#a9d2cac6c7ddc8cadd87ccc4c8c0c5d4" class="contact-link">{contact.email}</a>
    {/if}
    {#if contact.linkedin}
      <a href={contact.linkedin} target="_blank" rel="noopener" class="contact-link">LinkedIn ↗</a>
    {/if}
  </div>

  {#if displayRole}
    <div
      class="sidebar-role"
      style="opacity: {roleOpacity}; transform: translateX({roleTranslate}px);"
    >
      <div class="role-divider"></div>
      <h2 class="role-title">{displayRole.name}</h2>
      {#if displayJob}
        <p class="role-company">{displayJob.name}</p>
      {/if}
      {#if displayRole.department}
        <p class="role-department">{displayRole.department}</p>
      {/if}
      {#if formatDateRange(displayRole.date_start, displayRole.date_end)}
        <p class="role-dates">{formatDateRange(displayRole.date_start, displayRole.date_end)}</p>
      {/if}
      {#if displayRole.description}
        <p class="role-description">{displayRole.description}</p>
      {/if}
      {#if displayRole.proficiencies?.length > 0}
        <div class="role-proficiencies">
          {#each displayRole.proficiencies as prof}
            <span class="proficiency-tag">{prof.name}</span>
          {/each}
        </div>
      {/if}
      {#if displayRole.accolades}
        <p class="role-accolades">{displayRole.accolades}</p>
      {/if}
    </div>
  {/if}
</aside>

<style>
  .sidebar-public {
    position: sticky;
    top: 48px;
    padding-right: 40px;
    max-height: calc(100vh - 96px);
    overflow-y: auto;
    overflow-x: hidden;
  }
  .sidebar-contact { margin-bottom: 8px; }
  .contact-name {
    font-size: 20px; font-weight: 600; color: #e0e2e8;
    margin-bottom: 10px; letter-spacing: -0.02em;
  }
  .contact-link {
    display: block; font-size: 13px; color: #6b6e7a;
    text-decoration: none; margin-bottom: 4px; transition: color 0.2s;
  }
  .contact-link:hover { color: #a0a3ae; }

  .sidebar-role {
    transition: opacity 0.18s ease, transform 0.18s ease;
    will-change: opacity, transform;
  }
  .role-divider { width: 24px; height: 1px; background: #2a2d35; margin: 24px 0; }
  .role-title { font-size: 15px; font-weight: 600; color: #e0e2e8; margin-bottom: 4px; letter-spacing: -0.01em; }
  .role-company { font-size: 13px; color: #6b6e7a; margin-bottom: 4px; }
  .role-department { font-size: 12px; color: #4e515c; margin-bottom: 4px; }
  .role-dates { font-size: 12px; color: #4e515c; margin-bottom: 12px; }
  .role-description { font-size: 13px; color: #8a8d98; line-height: 1.6; margin-bottom: 12px; }
  .role-proficiencies { display: flex; flex-wrap: wrap; gap: 4px; margin-bottom: 12px; }
  .proficiency-tag {
    font-size: 11px; color: #6b6e7a; background: #1a1c22;
    padding: 3px 8px; border-radius: 3px; border: 1px solid #2a2d35;
  }
  .role-accolades { font-size: 12px; color: #6b6e7a; font-style: italic; line-height: 1.5; }
</style>