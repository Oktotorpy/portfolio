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

  // Split accolades text into individual cards (one per line)
  $: accoladeCards = displayRole?.accolades
    ? displayRole.accolades.split('\n').map(s => s.trim()).filter(s => s.length > 0)
    : [];

  // Job color for divider, fallback to default
  $: jobColor = displayJob?.color || '#3a3d48';
</script>

<aside class="sidebar-public">
  <div class="sidebar-contact">
    {#if contact.name}
      <h1 class="contact-name">{contact.name}</h1>
    {/if}
    {#if contact.email}
      <a href="mailto:{contact.email}" class="contact-link">{contact.email}</a>
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
      <!-- Colored divider using job color -->
      <div class="role-divider" style="background: {jobColor};"></div>

      <!-- Job logo -->
      {#if displayJob?.logo}
        <div class="role-logo-wrap">
          <img src={displayJob.logo} alt={displayJob.name} class="role-logo" />
        </div>
      {/if}

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

      <!-- Accolades as individual cards -->
      {#if accoladeCards.length > 0}
        <div class="accolades-section">
          <span class="accolades-label">Achievements</span>
          <div class="accolades-list">
            {#each accoladeCards as accolade}
              <div class="accolade-card" style="border-left-color: {jobColor};">
                <p class="accolade-text">{accolade}</p>
              </div>
            {/each}
          </div>
        </div>
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

  /* Hide scrollbar but keep scrollable */
  .sidebar-public::-webkit-scrollbar { width: 0; }
  .sidebar-public { scrollbar-width: none; }

  .sidebar-contact { margin-bottom: 8px; }
  .contact-name {
    font-size: 20px; font-weight: 600; color: var(--text);
    margin-bottom: 10px; letter-spacing: -0.02em;
  }
  .contact-link {
    display: block; font-size: 13px; color: var(--text-faint);
    text-decoration: none; margin-bottom: 4px; transition: color 0.2s;
  }
  .contact-link:hover { color: var(--text-dim); }

  .sidebar-role {
    transition: opacity 0.18s ease, transform 0.18s ease;
    will-change: opacity, transform;
  }

  /* ── Colored divider ────────────────────────── */
  .role-divider {
    width: 36px;
    height: 3px;
    border-radius: 2px;
    margin: 24px 0;
    transition: background 0.3s ease;
  }

  /* ── Job logo ───────────────────────────────── */
  .role-logo-wrap {
    margin-bottom: 14px;
  }

  .role-logo {
    max-width: 240px;
    max-height: 80px;
    object-fit: contain;
    display: block;
    opacity: 0.85;
    transition: opacity 0.2s;
  }

  .role-logo:hover { opacity: 1; }

  /* ── Role info ──────────────────────────────── */
  .role-title {
    font-size: 15px; font-weight: 600; color: var(--text);
    margin-bottom: 4px; letter-spacing: -0.01em;
  }
  .role-company { font-size: 13px; color: var(--text-faint); margin-bottom: 4px; }
  .role-department { font-size: 12px; color: var(--text-muted); margin-bottom: 4px; }
  .role-dates { font-size: 12px; color: var(--text-muted); margin-bottom: 12px; }
  .role-description { font-size: 13px; color: var(--text-dim); line-height: 1.6; margin-bottom: 12px; }

  .role-proficiencies { display: flex; flex-wrap: wrap; gap: 4px; margin-bottom: 12px; }
  .proficiency-tag {
    font-size: 11px; color: var(--text-faint); background: var(--bg-surface);
    padding: 3px 8px; border-radius: 3px; border: 1px solid var(--border);
  }

  /* ── Accolades section ──────────────────────── */
  .accolades-section {
    margin-top: 16px;
    padding-top: 14px;
    border-top: 1px solid var(--border-subtle);
  }

  .accolades-label {
    display: block;
    font-size: 10px;
    font-weight: 600;
    color: var(--text-muted);
    text-transform: uppercase;
    letter-spacing: 0.08em;
    margin-bottom: 10px;
  }

  .accolades-list {
    display: flex;
    flex-direction: column;
    gap: 8px;
  }

  .accolade-card {
    background: var(--highlight);
    border: 1px solid var(--border-subtle);
    border-left: 3px solid var(--border-strong);
    border-radius: 0 5px 5px 0;
    padding: 10px 12px;
    transition: border-left-color 0.3s, background 0.2s;
  }

  .accolade-card:hover {
    background: var(--highlight-hover);
  }

  .accolade-text {
    font-size: 12.5px;
    color: var(--text-secondary);
    line-height: 1.5;
    margin: 0;
  }
</style>
