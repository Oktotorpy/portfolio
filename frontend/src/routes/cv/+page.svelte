<script>
  import { formatDate, formatDateRange } from '$lib/utils.js';

  export let data;

  $: contact = data.contact || {};
  $: jobs = (data.jobs || [])
    .slice()
    .sort((a, b) => (b.date_start || '').localeCompare(a.date_start || ''));

  $: roles = data.roles || [];

  // Build role index per job for tags (same logic as timeline)
  $: rolesByJob = (() => {
    const byJob = {};
    for (const r of roles) {
      if (!r.job_id) continue;
      if (!byJob[r.job_id]) byJob[r.job_id] = [];
      byJob[r.job_id].push(r);
    }
    // Sort each group by date_start ascending (earliest first)
    for (const jobId of Object.keys(byJob)) {
      byJob[jobId].sort((a, b) => (a.date_start || '').localeCompare(b.date_start || ''));
    }
    return byJob;
  })();

  function getRoleTag(role) {
    const group = rolesByJob[role.job_id];
    if (!group) return '';
    const idx = group.indexOf(role);
    if (idx === -1) {
      // Find by id if reference doesn't match
      const i = group.findIndex(r => r.id === role.id);
      if (i === -1) return '';
      return i === 0 ? 'New role' : 'Promotion';
    }
    return idx === 0 ? 'New role' : 'Promotion';
  }

  function getJobRoles(jobId) {
    return (rolesByJob[jobId] || []).slice().reverse(); // newest first for display
  }

  function splitAccolades(text) {
    if (!text) return [];
    return text.split('\n').map(s => s.trim()).filter(s => s.length > 0);
  }

  function goBack() {
    if (typeof window !== 'undefined') history.back();
  }

  function printCV() {
    if (typeof window !== 'undefined') window.print();
  }
</script>

<svelte:head>
  <title>CV — {contact.name || 'Portfolio'}</title>
</svelte:head>

<div class="cv-page">
  <div class="cv-actions">
    <button class="cv-btn cv-btn-back" on:click={goBack}>← Back</button>
    <div class="cv-actions-right">
      <button class="cv-btn" on:click={printCV}>Print</button>
      <button class="cv-btn cv-btn-primary" on:click={printCV}>Save as PDF</button>
    </div>
  </div>

  <div class="cv-sheet">
    <!-- Contact Header -->
    <header class="cv-header">
      {#if contact.name}
        <h1 class="cv-name">{contact.name}</h1>
      {/if}
      {#if contact.description}
        <p class="cv-description">{contact.description}</p>
      {/if}
      <div class="cv-contact-links">
        {#if contact.email}
          <a href="mailto:{contact.email}">{contact.email}</a>
        {/if}
        {#if contact.linkedin}
          <a href={contact.linkedin} target="_blank" rel="noopener">LinkedIn</a>
        {/if}
        <a href="https://vitz.pro" target="_blank" rel="noopener">vitz.pro</a>
      </div>
    </header>

    <!-- Jobs & Roles -->
    <div class="cv-body">
      {#each jobs as job (job.id)}
        {@const jobRoles = getJobRoles(job.id)}
        {#if jobRoles.length > 0}
          <section class="cv-job" style="border-left-color: {job.color || '#3a3d48'};">
            <div class="cv-job-header">
              <div class="cv-job-left">
                {#if job.website}
                  <a href={job.website} target="_blank" rel="noopener" class="cv-job-name">{job.name}</a>
                {:else}
                  <span class="cv-job-name">{job.name}</span>
                {/if}
                {#if job.countries?.length > 0}
                  <span class="cv-job-countries">{job.countries.map(c => c.name).join(', ')}</span>
                {/if}
              </div>
              <span class="cv-job-dates">{formatDateRange(job.date_start, job.date_end)}</span>
            </div>
            {#if job.description}
              <p class="cv-job-description">{job.description}</p>
            {/if}

            <div class="cv-roles">
              {#each jobRoles as role (role.id)}
                {@const tag = getRoleTag(role)}
                <div class="cv-role">
                  <div class="cv-role-header">
                    <span class="cv-role-name">{role.name}</span>
                    {#if tag}
                      <span class="cv-role-tag" class:promotion={tag === 'Promotion'}>{tag}</span>
                    {/if}
                  </div>
                  <div class="cv-role-meta">
                    {#if role.department}
                      <span>{role.department}</span>
                    {/if}
                    {#if role.date_start}
                      <span>{formatDate(role.date_start)}{#if !role.date_end} — Present{/if}</span>
                    {/if}
                  </div>
                  {#if role.description}
                    <p class="cv-role-description">{role.description}</p>
                  {/if}
                  {#if splitAccolades(role.accolades).length > 0}
                    <ul class="cv-accolades">
                      {#each splitAccolades(role.accolades) as accolade}
                        <li>{accolade}</li>
                      {/each}
                    </ul>
                  {/if}
                  {#if role.proficiencies?.length > 0}
                    <div class="cv-proficiencies">
                      {#each role.proficiencies as prof}
                        <span class="cv-prof-tag">{prof.name}</span>
                      {/each}
                    </div>
                  {/if}
                </div>
              {/each}
            </div>
          </section>
        {/if}
      {/each}
    </div>
  </div>
</div>

<style>
  /* ── Force light mode, independent of system preference ── */
  .cv-page {
    font-family: 'Geist', -apple-system, BlinkMacSystemFont, system-ui, sans-serif;
    background: #e8eaed;
    min-height: 100vh;
    display: flex;
    flex-direction: column;
    align-items: center;
    padding: 24px 16px 64px;
    color: #1a1d27;
    color-scheme: light;
  }

  /* ── Action bar ── */
  .cv-actions {
    width: 100%;
    max-width: 210mm;
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 16px;
  }

  .cv-actions-right {
    display: flex;
    gap: 8px;
  }

  .cv-btn {
    padding: 8px 16px;
    border: 1px solid #d0d3d8;
    border-radius: 6px;
    background: #fff;
    color: #3a4050;
    font-size: 13px;
    font-weight: 500;
    cursor: pointer;
    font-family: inherit;
    transition: all 0.15s;
  }

  .cv-btn:hover {
    border-color: #a0a5b0;
    color: #1a1d27;
  }

  .cv-btn-primary {
    background: #3a4050;
    color: #fff;
    border-color: #3a4050;
  }

  .cv-btn-primary:hover {
    background: #2a2d3a;
    border-color: #2a2d3a;
  }

  .cv-btn-back {
    border: none;
    background: none;
    color: #6a7080;
    padding-left: 0;
  }

  .cv-btn-back:hover {
    color: #1a1d27;
  }

  /* ── A4 Sheet ── */
  .cv-sheet {
    width: 100%;
    max-width: 210mm;
    min-height: 297mm;
    background: #fff;
    border-radius: 4px;
    box-shadow: 0 2px 20px rgba(0, 0, 0, 0.1);
    padding: 40px 48px;
  }

  /* ── Contact Header ── */
  .cv-header {
    margin-bottom: 32px;
    padding-bottom: 24px;
    border-bottom: 2px solid #e4e7eb;
  }

  .cv-name {
    font-size: 28px;
    font-weight: 700;
    color: #1a1d27;
    letter-spacing: -0.02em;
    margin-bottom: 8px;
  }

  .cv-description {
    font-size: 14px;
    color: #5c6275;
    line-height: 1.6;
    margin-bottom: 12px;
    max-width: 500px;
  }

  .cv-contact-links {
    display: flex;
    flex-wrap: wrap;
    gap: 6px 16px;
  }

  .cv-contact-links a {
    font-size: 13px;
    color: #5b6abf;
    text-decoration: none;
    transition: color 0.15s;
  }

  .cv-contact-links a:hover {
    color: #4e5ca6;
  }

  /* ── Jobs ── */
  .cv-body {
    display: flex;
    flex-direction: column;
    gap: 28px;
  }

  .cv-job {
    border-left: 3px solid #3a3d48;
    padding-left: 20px;
  }

  .cv-job-header {
    display: flex;
    justify-content: space-between;
    align-items: baseline;
    flex-wrap: wrap;
    gap: 8px;
    margin-bottom: 4px;
  }

  .cv-job-left {
    display: flex;
    align-items: baseline;
    gap: 10px;
    flex-wrap: wrap;
  }

  .cv-job-name {
    font-size: 17px;
    font-weight: 700;
    color: #1a1d27;
    text-decoration: none;
  }

  a.cv-job-name:hover {
    color: #5b6abf;
  }

  .cv-job-countries {
    font-size: 12px;
    color: #8a90a0;
  }

  .cv-job-dates {
    font-size: 12px;
    color: #8a90a0;
    white-space: nowrap;
  }

  .cv-job-description {
    font-size: 13px;
    color: #5c6275;
    line-height: 1.5;
    margin-bottom: 16px;
  }

  /* ── Roles ── */
  .cv-roles {
    display: flex;
    flex-direction: column;
    gap: 18px;
  }

  .cv-role {
    padding: 12px 16px;
    background: #f8f9fb;
    border-radius: 6px;
    break-inside: avoid;
  }

  .cv-role-header {
    display: flex;
    align-items: center;
    gap: 8px;
    margin-bottom: 2px;
  }

  .cv-role-name {
    font-size: 15px;
    font-weight: 600;
    color: #1a1d27;
  }

  .cv-role-tag {
    font-size: 9px;
    font-weight: 700;
    color: #155724;
    background: #d4edda;
    padding: 2px 8px;
    border-radius: 3px;
    text-transform: uppercase;
    letter-spacing: 0.04em;
  }

  .cv-role-tag.promotion {
    background: #f0e6c0;
    color: #6b5b1e;
  }

  .cv-role-meta {
    display: flex;
    gap: 12px;
    font-size: 12px;
    color: #8a90a0;
    margin-bottom: 8px;
  }

  .cv-role-description {
    font-size: 13px;
    color: #3a4050;
    line-height: 1.6;
    margin-bottom: 8px;
  }

  .cv-accolades {
    list-style: none;
    margin-bottom: 8px;
  }

  .cv-accolades li {
    font-size: 12.5px;
    color: #3a4050;
    line-height: 1.5;
    padding-left: 16px;
    position: relative;
    margin-bottom: 2px;
  }

  .cv-accolades li::before {
    content: '★';
    position: absolute;
    left: 0;
    color: #b8960a;
    font-size: 10px;
    top: 2px;
  }

  .cv-proficiencies {
    display: flex;
    flex-wrap: wrap;
    gap: 4px;
  }

  .cv-prof-tag {
    font-size: 11px;
    color: #5c6275;
    background: #eef0f4;
    padding: 2px 8px;
    border-radius: 3px;
    border: 1px solid #e4e7eb;
  }

  /* ── Mobile ── */
  @media (max-width: 768px) {
    .cv-page {
      padding: 12px 8px 48px;
    }

    .cv-sheet {
      padding: 24px 20px;
      min-height: auto;
    }

    .cv-name {
      font-size: 22px;
    }

    .cv-job-header {
      flex-direction: column;
      gap: 2px;
    }

    .cv-actions {
      padding: 0 4px;
    }
  }

  /* ── Print ── */
  @media print {
    .cv-page {
      background: #fff;
      padding: 0;
      min-height: auto;
    }

    .cv-actions {
      display: none;
    }

    .cv-sheet {
      box-shadow: none;
      border-radius: 0;
      padding: 0;
      max-width: 100%;
    }

    .cv-role {
      background: none;
      padding: 8px 0;
      border-top: 1px solid #e4e7eb;
      border-radius: 0;
    }

    .cv-roles .cv-role:first-child {
      border-top: none;
    }

    @page {
      size: A4;
      margin: 15mm;
    }

    .cv-job {
      break-inside: avoid;
    }
  }
</style>
