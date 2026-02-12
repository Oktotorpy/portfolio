<script>
  import { onMount, onDestroy, tick } from 'svelte';
  import { currentRoleId } from '$lib/stores.js';
  import { formatDate, formatDateRange } from '$lib/utils.js';
  import PublicShell from '$lib/components/PublicShell.svelte';

  export let data;

  let isMobile = false;
  let timelineEl;
  let observer;

  let selectedProject = null;
  let selectedRole = null;
  let popupStyle = '';

  function checkMobile() {
    isMobile = typeof window !== 'undefined' && window.innerWidth <= 768;
  }

  onMount(() => {
    checkMobile();
    window.addEventListener('resize', onResize);
    tick().then(setupObserver);
  });

  onDestroy(() => {
    if (typeof window !== 'undefined') window.removeEventListener('resize', onResize);
    if (observer) observer.disconnect();
  });

  function onResize() {
    checkMobile();
    closePopup();
  }

  // Desktop only: hovering near a role marker previews that role in sidebar
  function onRoleProximity(role) {
    if (isMobile) return;
    if (role?.id) $currentRoleId = role.id;
  }

  $: segMonths = isMobile ? 3 : 12;
  $: rows = buildRows(data.jobs, data.roles, data.projects, segMonths);

  function buildRows(jobs, roles, projects, seg) {
    if (!jobs?.length) return [];

    const now = new Date();
    let minDate = new Date(now);
    let maxDate = new Date(0);

    for (const job of jobs) {
      const s = job.date_start ? new Date(job.date_start) : now;
      const e = job.date_end ? new Date(job.date_end) : now;
      if (s < minDate) minDate = new Date(s);
      if (e > maxDate) maxDate = new Date(e);
    }

    let cursor;
    if (seg === 12) {
      cursor = new Date(maxDate.getFullYear(), 0, 1);
    } else {
      const q = Math.floor(maxDate.getMonth() / seg) * seg;
      cursor = new Date(maxDate.getFullYear(), q, 1);
    }

    const endBound = new Date(minDate.getFullYear(), Math.floor(minDate.getMonth() / seg) * seg, 1);
    const result = [];
    let idx = 0;

    while (cursor >= endBound) {
      const pStart = new Date(cursor);
      const pEnd = new Date(cursor);
      pEnd.setMonth(pEnd.getMonth() + seg);
      pEnd.setDate(pEnd.getDate() - 1);

      const activeJobs = jobs.filter(j => {
        const js = j.date_start ? new Date(j.date_start) : now;
        const je = j.date_end ? new Date(j.date_end) : now;
        return js <= pEnd && je >= pStart;
      });

      const segments = buildSegments(pStart, pEnd, activeJobs, now);

      const jobStarts = [];
      for (const job of jobs) {
        const js = job.date_start ? new Date(job.date_start) : null;
        if (js && js >= pStart && js <= pEnd) {
          const countries = job.countries?.map(c => c.name).join(', ') || '';
          jobStarts.push({ position: datePos(js, pStart, pEnd), name: job.name, country: countries, jobId: job.id });
        }
      }

      const roleStarts = [];
      for (const role of roles) {
        const rs = role.date_start ? new Date(role.date_start) : null;
        if (rs && rs >= pStart && rs <= pEnd) {
          const job = jobs.find(j => j.id === role.job_id);
          roleStarts.push({ position: datePos(rs, pStart, pEnd), role: { ...role, job } });
        }
      }

      const dots = projects
        .filter(p => {
          if (!p.date_of_creation) return false;
          const d = new Date(p.date_of_creation);
          return d >= pStart && d <= pEnd;
        })
        .map(p => ({ ...p, position: datePos(new Date(p.date_of_creation), pStart, pEnd) }))
        .sort((a, b) => a.position - b.position);

      let label;
      if (seg === 12) {
        label = pStart.getFullYear().toString();
      } else {
        const m = pStart.toLocaleString('en-US', { month: 'short' });
        label = `${m} '${String(pStart.getFullYear()).slice(2)}`;
      }

      const primaryRole = activeJobs.length > 0
        ? roles.filter(r => activeJobs.some(j => j.id === r.job_id))
            .sort((a, b) => (b.date_start || '').localeCompare(a.date_start || ''))[0] || null
        : null;

      result.push({ label, segments, jobStarts, roleStarts, dots, primaryRole, rowIndex: idx });
      cursor.setMonth(cursor.getMonth() - seg);
      idx++;
    }

    return result;
  }

  function buildSegments(pStart, pEnd, activeJobs, now) {
    const total = pEnd.getTime() - pStart.getTime();
    if (total <= 0 || activeJobs.length === 0) return [{ start: 0, end: 1, type: 'dashed' }];

    const intervals = [];
    for (const job of activeJobs) {
      const js = Math.max(pStart.getTime(), (job.date_start ? new Date(job.date_start) : now).getTime());
      const je = Math.min(pEnd.getTime(), (job.date_end ? new Date(job.date_end) : now).getTime());
      intervals.push({ start: (js - pStart.getTime()) / total, end: (je - pStart.getTime()) / total });
    }

    intervals.sort((a, b) => a.start - b.start);
    const merged = [intervals[0]];
    for (let i = 1; i < intervals.length; i++) {
      const last = merged[merged.length - 1];
      if (intervals[i].start <= last.end + 0.001) {
        last.end = Math.max(last.end, intervals[i].end);
      } else {
        merged.push(intervals[i]);
      }
    }

    const segs = [];
    let pos = 0;
    for (const m of merged) {
      if (m.start > pos + 0.001) segs.push({ start: pos, end: m.start, type: 'dashed' });
      segs.push({ start: m.start, end: m.end, type: 'solid' });
      pos = m.end;
    }
    if (pos < 0.999) segs.push({ start: pos, end: 1, type: 'dashed' });
    return segs;
  }

  function datePos(date, start, end) {
    const total = end.getTime() - start.getTime();
    if (total <= 0) return 0.5;
    return Math.max(0.02, Math.min(0.98, (date.getTime() - start.getTime()) / total));
  }

  function openProjectPopup(project, event) {
    selectedRole = null;
    selectedProject = project;
    positionPopup(event);
  }

  function openRolePopup(roleData, event) {
    selectedProject = null;
    selectedRole = roleData;
    if (roleData.id) $currentRoleId = roleData.id;
    positionPopup(event);
  }

  function positionPopup(event) {
    const rect = event.currentTarget.getBoundingClientRect();
    const viewW = window.innerWidth;
    const viewH = window.innerHeight;
    const popupW = Math.min(360, viewW - 32);

    let left = rect.left + rect.width / 2;
    left = Math.max(popupW / 2 + 16, Math.min(viewW - popupW / 2 - 16, left));

    let top = rect.top - 12;
    if (top < 320) {
      popupStyle = `top: ${rect.bottom + 12}px; left: ${left}px; transform: translateX(-50%); max-width: ${popupW}px;`;
    } else {
      popupStyle = `bottom: ${viewH - top}px; left: ${left}px; transform: translateX(-50%); max-width: ${popupW}px;`;
    }
  }

  function closePopup() {
    selectedProject = null;
    selectedRole = null;
  }

  function getYouTubeId(url) {
    if (!url) return null;
    const m = url.match(/(?:youtube\.com\/(?:watch\?v=|embed\/)|youtu\.be\/)([a-zA-Z0-9_-]{11})/);
    return m ? m[1] : null;
  }

  function setupObserver() {
    if (observer) observer.disconnect();
    if (!timelineEl) return;

    observer = new IntersectionObserver(
      (entries) => {
        const visible = entries.filter(e => e.isIntersecting)
          .sort((a, b) => a.boundingClientRect.top - b.boundingClientRect.top);
        if (visible.length > 0) {
          const rid = parseInt(visible[0].target.dataset.primaryRoleId);
          if (rid && !isNaN(rid)) $currentRoleId = rid;
        }
      },
      { rootMargin: '-20% 0px -60% 0px', threshold: 0 }
    );

    const rowEls = timelineEl.querySelectorAll('.tl-row');
    rowEls.forEach(el => observer.observe(el));
  }

  $: if (rows.length && timelineEl) {
    tick().then(setupObserver);
  }
</script>

<svelte:head>
  <title>Timeline — Portfolio</title>
</svelte:head>

<PublicShell contact={data.contact} roles={data.roles} workTypes={data.workTypes}>
  {#if rows.length === 0}
    <div class="tl-empty">No timeline data yet</div>
  {:else}
    <!-- svelte-ignore a11y-click-events-have-key-events -->
    <!-- svelte-ignore a11y-no-static-element-interactions -->
    <div class="timeline" bind:this={timelineEl} on:click={closePopup}>
      {#each rows as row (row.rowIndex)}
        <div class="tl-row" data-primary-role-id={row.primaryRole?.id || ''}>
          <div class="tl-label">{row.label}</div>
          <div class="tl-track">
            {#each row.segments as seg}
              <div class="tl-segment" class:dashed={seg.type === 'dashed'}
                style="left: {seg.start * 100}%; width: {(seg.end - seg.start) * 100}%;"></div>
            {/each}

            {#each row.jobStarts as js}
              <div class="tl-job-marker" style="left: {js.position * 100}%;">
                <div class="tl-job-tick"></div>
                <div class="tl-job-info">
                  <span class="tl-job-name">{js.name}</span>
                  {#if js.country}<span class="tl-job-country">{js.country}</span>{/if}
                </div>
              </div>
            {/each}

            {#each row.roleStarts as rs}
              <button class="tl-role-marker" style="left: {rs.position * 100}%;"
                on:click|stopPropagation={(e) => openRolePopup(rs.role, e)}
                on:mouseenter={() => onRoleProximity(rs.role)}
                title={rs.role.name}>
                <span class="tl-role-name">{rs.role.name}</span>
                <span class="tl-role-arrow">▲</span>
                <span class="tl-role-square"></span>
              </button>
            {/each}

            {#each row.dots as dot, di}
              <button class="tl-dot" class:active={selectedProject?.id === dot.id}
                style="left: {dot.position * 100}%;"
                on:click|stopPropagation={(e) => openProjectPopup(dot, e)}
                on:mouseenter={() => onRoleProximity(dot.role)}
                title={dot.name}>
                <span class="tl-dot-circle"></span>
                <span class="tl-dot-label" class:above={di % 2 === 0} class:below={di % 2 !== 0}>{dot.name}</span>
              </button>
            {/each}
          </div>
        </div>
      {/each}
    </div>
  {/if}

  <!-- PROJECT POPUP -->
  {#if selectedProject}
    <!-- svelte-ignore a11y-click-events-have-key-events -->
    <!-- svelte-ignore a11y-no-static-element-interactions -->
    <div class="popup-backdrop" on:click={closePopup}></div>
    <div class="popup-card" style={popupStyle} on:click|stopPropagation>
      <button class="popup-close" on:click={closePopup}>×</button>
      {#if selectedProject.media?.length > 0}
        {@const firstMedia = selectedProject.media[0]}
        <div class="popup-media">
          {#if firstMedia.media_type === 'image'}
            <img src={firstMedia.media_value} alt={selectedProject.name} />
          {:else if firstMedia.media_type === 'video'}
            <video src={firstMedia.media_value} controls preload="metadata"></video>
          {:else if getYouTubeId(firstMedia.media_value)}
            <iframe src="https://www.youtube-nocookie.com/embed/{getYouTubeId(firstMedia.media_value)}"
              title={selectedProject.name} frameborder="0"
              allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope" allowfullscreen></iframe>
          {/if}
        </div>
      {/if}
      <div class="popup-body">
        <h3 class="popup-title">{selectedProject.name}</h3>
        <p class="popup-meta">
          {selectedProject.role?.name || ''}
          {#if selectedProject.role?.department} · {selectedProject.role.department}{/if}
          {#if selectedProject.role?.job?.name} · {selectedProject.role.job.name}{/if}
        </p>
        {#if selectedProject.date_of_creation}<p class="popup-date">{formatDate(selectedProject.date_of_creation)}</p>{/if}
        {#if selectedProject.description}<p class="popup-desc">{selectedProject.description}</p>{/if}
        {#if selectedProject.link}<a href={selectedProject.link} target="_blank" rel="noopener" class="popup-link">View project ↗</a>{/if}
        {#if selectedProject.skills?.length > 0 || selectedProject.tools?.length > 0}
          <div class="popup-skills">
            {#each selectedProject.skills || [] as skill}<span class="popup-skill">{skill.name}</span>{/each}
            {#each selectedProject.tools || [] as tool}<span class="popup-skill popup-tool">{tool.name}</span>{/each}
          </div>
        {/if}
      </div>
    </div>
  {/if}

  <!-- ROLE POPUP -->
  {#if selectedRole}
    <!-- svelte-ignore a11y-click-events-have-key-events -->
    <!-- svelte-ignore a11y-no-static-element-interactions -->
    <div class="popup-backdrop" on:click={closePopup}></div>
    <div class="popup-card" style={popupStyle} on:click|stopPropagation>
      <button class="popup-close" on:click={closePopup}>×</button>
      <div class="popup-body">
        <h3 class="popup-title">{selectedRole.name}</h3>
        {#if selectedRole.job}<p class="popup-meta">{selectedRole.job.name}</p>{/if}
        {#if selectedRole.department}<p class="popup-dept">{selectedRole.department}</p>{/if}
        {#if formatDateRange(selectedRole.date_start, selectedRole.date_end)}<p class="popup-date">{formatDateRange(selectedRole.date_start, selectedRole.date_end)}</p>{/if}
        {#if selectedRole.description}<p class="popup-desc">{selectedRole.description}</p>{/if}
        {#if selectedRole.proficiencies?.length > 0}
          <div class="popup-skills" style="margin-top: 8px;">{#each selectedRole.proficiencies as prof}<span class="popup-skill">{prof.name}</span>{/each}</div>
        {/if}
        {#if selectedRole.accolades}<p class="popup-accolades">{selectedRole.accolades}</p>{/if}
      </div>
    </div>
  {/if}
</PublicShell>

<style>
  .timeline { padding: 24px 0 100px; }
  .tl-empty { display: flex; align-items: center; justify-content: center; padding: 120px 0; color: #2a2d35; font-size: 16px; }
  .tl-row { display: flex; align-items: stretch; padding: 44px 0; position: relative; }
  .tl-label { width: 72px; flex-shrink: 0; font-size: 15px; font-weight: 700; color: #3a3d48; display: flex; align-items: center; letter-spacing: 0.01em; user-select: none; }
  .tl-track { flex: 1; position: relative; height: 2px; align-self: center; }
  .tl-segment { position: absolute; top: 0; height: 2px; background: #3a3d48; border-radius: 1px; }
  .tl-segment.dashed { background: none; border-top: 2px dashed #222530; height: 0; }

  .tl-job-marker { position: absolute; top: 0; transform: translateX(-50%); z-index: 4; }
  .tl-job-tick { width: 1px; height: 28px; background: #4e515c; margin: 0 auto; }
  .tl-job-info { display: flex; flex-direction: column; align-items: center; margin-top: 6px; white-space: nowrap; }
  .tl-job-name { font-size: 13px; font-weight: 600; color: #8a8d98; }
  .tl-job-country { font-size: 11px; color: #4e515c; margin-top: 1px; }

  .tl-role-marker { position: absolute; top: 0; transform: translate(-50%, 0); z-index: 5; background: none; border: none; cursor: pointer; display: flex; flex-direction: column; align-items: center; padding: 16px 24px; margin: -16px -24px; }
  .tl-role-name { font-size: 12px; font-weight: 600; color: #6b6e7a; white-space: nowrap; position: absolute; bottom: calc(100% + 2px); transition: color 0.15s; }
  .tl-role-arrow { font-size: 7px; color: #4e515c; line-height: 1; position: absolute; bottom: 10px; transition: color 0.15s; }
  .tl-role-square { width: 10px; height: 10px; border: 2px solid #4e515c; border-radius: 2px; background: #111114; display: block; transform: translateY(-4px); transition: all 0.15s; }
  .tl-role-marker:hover .tl-role-name { color: #e0e2e8; }
  .tl-role-marker:hover .tl-role-arrow { color: #8a8d98; }
  .tl-role-marker:hover .tl-role-square { border-color: #8a8d98; background: #1a1c22; }

  .tl-dot { position: absolute; top: 0; transform: translate(-50%, -50%); z-index: 6; background: none; border: none; cursor: pointer; padding: 10px; display: flex; flex-direction: column; align-items: center; }
  .tl-dot-circle { width: 10px; height: 10px; border-radius: 50%; background: #6b6e7a; border: 2px solid #111114; transition: all 0.15s; display: block; }
  .tl-dot:hover .tl-dot-circle, .tl-dot.active .tl-dot-circle { background: #e0e2e8; transform: scale(1.4); }
  .tl-dot-label { position: absolute; font-size: 12px; color: #4e515c; white-space: nowrap; max-width: 140px; overflow: hidden; text-overflow: ellipsis; transition: color 0.15s; pointer-events: none; }
  .tl-dot-label.above { bottom: calc(100% - 4px); }
  .tl-dot-label.below { top: calc(100% - 4px); }
  .tl-dot:hover .tl-dot-label { color: #a0a3ae; }

  .popup-backdrop { position: fixed; inset: 0; z-index: 90; background: rgba(0, 0, 0, 0.35); }
  .popup-card { position: fixed; z-index: 91; background: #1a1c22; border: 1px solid #2a2d35; border-radius: 10px; overflow: hidden; width: 360px; box-shadow: 0 16px 48px rgba(0, 0, 0, 0.5); }
  .popup-close { position: absolute; top: 8px; right: 8px; z-index: 2; background: rgba(17, 17, 20, 0.7); border: none; color: #6b6e7a; width: 28px; height: 28px; border-radius: 50%; font-size: 18px; cursor: pointer; display: flex; align-items: center; justify-content: center; transition: color 0.15s; line-height: 1; }
  .popup-close:hover { color: #e0e2e8; }
  .popup-media { width: 100%; max-height: 200px; overflow: hidden; background: #0f1014; }
  .popup-media img { width: 100%; height: 200px; object-fit: cover; display: block; }
  .popup-media video { width: 100%; max-height: 200px; object-fit: contain; display: block; }
  .popup-media iframe { width: 100%; aspect-ratio: 16/9; display: block; }
  .popup-body { padding: 18px; }
  .popup-title { font-size: 16px; font-weight: 600; color: #e0e2e8; margin-bottom: 4px; letter-spacing: -0.01em; padding-right: 28px; }
  .popup-meta { font-size: 14px; color: #6b6e7a; margin-bottom: 3px; }
  .popup-date { font-size: 13px; color: #4e515c; margin-bottom: 12px; }
  .popup-desc { font-size: 14px; color: #8a8d98; line-height: 1.6; margin-bottom: 12px; }
  .popup-link { font-size: 14px; color: #7a7faa; text-decoration: none; display: inline-block; margin-bottom: 12px; }
  .popup-link:hover { color: #a0a4cc; }
  .popup-skills { display: flex; flex-wrap: wrap; gap: 5px; padding-top: 12px; border-top: 1px solid #1e2028; }
  .popup-skill { font-size: 12px; color: #5a5e6a; background: #111318; padding: 3px 9px; border-radius: 3px; border: 1px solid #1e2028; }
  .popup-tool { color: #7a7faa; background: rgba(122, 127, 170, 0.08); border-color: rgba(122, 127, 170, 0.2); }
  .popup-dept { font-size: 13px; color: #4e515c; margin-bottom: 3px; }
  .popup-accolades { font-size: 13px; color: #6b6e7a; font-style: italic; line-height: 1.5; margin-top: 12px; padding-top: 12px; border-top: 1px solid #1e2028; }

  @media (max-width: 768px) {
    .tl-row { padding: 36px 0; }
    .tl-label { width: 52px; font-size: 12px; }
    .tl-dot-label { font-size: 10px; max-width: 90px; }
    .tl-job-name { font-size: 11px; }
    .tl-job-country { font-size: 9px; }
    .tl-role-name { font-size: 10px; }
    .popup-card { width: calc(100vw - 32px); max-width: 360px; left: 50% !important; transform: translateX(-50%) !important; top: auto !important; bottom: 68px !important; }
  }
</style>
