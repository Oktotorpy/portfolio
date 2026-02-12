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
  let hoveredJobId = null;

  // Popup media state
  let popupVideoIndex = 0;
  let popupShortsPage = 0;

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

  function onRoleProximity(role) {
    if (isMobile) return;
    if (role?.id) $currentRoleId = role.id;
  }

  $: segMonths = isMobile ? 3 : 12;
  $: rows = buildRows(data.jobs, data.roles, data.projects, segMonths);

  /* ── Weight → visual config ──────────────────────────────────────── */

  function getWeightClass(weight) {
    if (!weight?.name) return 'weight-small';
    const n = weight.name.toLowerCase();
    if (n === 'landmark') return 'weight-landmark';
    if (n === 'continuous') return 'weight-continuous';
    if (n === 'big') return 'weight-big';
    if (n === 'medium') return 'weight-medium';
    return 'weight-small';
  }

  /* ── YouTube helpers ─────────────────────────────────────────────── */

  function getYouTubeId(url) {
    if (!url) return null;
    const m = url.match(/(?:youtube\.com\/(?:watch\?v=|embed\/|shorts\/)|youtu\.be\/)([a-zA-Z0-9_-]{11})/);
    return m ? m[1] : null;
  }

  function isShorts(url) {
    return /youtube\.com\/shorts\//i.test(url || '');
  }

  /* ── Build rows ──────────────────────────────────────────────────── */

  function buildRows(jobs, roles, projects, seg) {
    if (!jobs?.length) return [];

    // Pre-compute role index per job (for New role / Promotion tags)
    const roleIndexMap = {};
    if (roles?.length) {
      const byJob = {};
      for (const r of roles) {
        if (!r.job_id) continue;
        if (!byJob[r.job_id]) byJob[r.job_id] = [];
        byJob[r.job_id].push(r);
      }
      for (const jobId of Object.keys(byJob)) {
        byJob[jobId].sort((a, b) => (a.date_start || '').localeCompare(b.date_start || ''));
        byJob[jobId].forEach((r, i) => { roleIndexMap[r.id] = i; });
      }
    }

    function getRoleTag(roleId) {
      const idx = roleIndexMap[roleId];
      if (idx === undefined) return '';
      return idx === 0 ? 'New role' : 'Promotion';
    }

    // Build a map of role_id → job_id for quick lookup
    const roleJobMap = {};
    for (const r of roles) {
      if (r.job_id) roleJobMap[r.id] = r.job_id;
    }

    // Build a map of job date_start → position (for snapping roles to same position)
    const jobDateMap = {};
    for (const job of jobs) {
      if (job.date_start) jobDateMap[job.id] = job.date_start;
    }

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
          jobStarts.push({ position: datePos(js, pStart, pEnd), name: job.name, country: countries, jobId: job.id, dateStr: job.date_start });
        }
      }

      const roleStarts = [];
      for (const role of roles) {
        const rs = role.date_start ? new Date(role.date_start) : null;
        if (rs && rs >= pStart && rs <= pEnd) {
          const job = jobs.find(j => j.id === role.job_id);
          const tag = getRoleTag(role.id);

          // Snap to job position if role date_start matches job date_start
          let pos = datePos(rs, pStart, pEnd);
          if (job && jobDateMap[job.id] === role.date_start) {
            pos = datePos(new Date(jobDateMap[job.id]), pStart, pEnd);
          }

          roleStarts.push({ position: pos, role: { ...role, job }, tag });
        }
      }

      const dots = projects
        .filter(p => {
          if (!p.date_of_creation) return false;
          const d = new Date(p.date_of_creation);
          return d >= pStart && d <= pEnd;
        })
        .map(p => ({
          ...p,
          position: datePos(new Date(p.date_of_creation), pStart, pEnd),
          weightClass: getWeightClass(p.weight),
          jobId: roleJobMap[p.role_id] || null,
        }))
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

    // Add a single "Currently" marker to the first row for all open-ended roles
    if (result.length > 0 && roles?.length) {
      const firstRow = result[0];
      const currentRoles = roles.filter(r => !r.date_end && r.date_start);
      const unshownCurrentRoles = currentRoles.filter(
        r => !firstRow.roleStarts.some(rs => rs.role.id === r.id)
      );
      if (unshownCurrentRoles.length > 0) {
        const currentJobs = unshownCurrentRoles.map(r => {
          const job = jobs.find(j => j.id === r.job_id);
          return { role: r, job };
        });
        firstRow.roleStarts.push({
          position: 0.95,
          role: { ...unshownCurrentRoles[0], job: currentJobs[0].job },
          tag: 'Currently',
          currentJobs,
        });
      }
    }

    return result;
  }

  /* ── Build colored, stackable segments ───────────────────────────── */

  function buildSegments(pStart, pEnd, activeJobs, now) {
    const total = pEnd.getTime() - pStart.getTime();
    if (total <= 0 || activeJobs.length === 0) return [{ start: 0, end: 1, type: 'dashed', color: null, stackIndex: 0, stackCount: 1 }];

    const sortedJobs = [...activeJobs].sort((a, b) =>
      (a.date_start || '').localeCompare(b.date_start || '')
    );

    const jobIntervals = sortedJobs.map(job => {
      const js = Math.max(pStart.getTime(), (job.date_start ? new Date(job.date_start) : now).getTime());
      const je = Math.min(pEnd.getTime(), (job.date_end ? new Date(job.date_end) : now).getTime());
      return {
        start: (js - pStart.getTime()) / total,
        end: (je - pStart.getTime()) / total,
        color: job.color || '#3a3d48',
        jobId: job.id,
      };
    });

    const segments = [];
    for (let i = 0; i < jobIntervals.length; i++) {
      const iv = jobIntervals[i];
      let stackIndex = 0;
      let stackCount = 0;
      for (let j = 0; j < jobIntervals.length; j++) {
        if (jobIntervals[j].start < iv.end && jobIntervals[j].end > iv.start) {
          if (j < i) stackIndex++;
          stackCount++;
        }
      }
      segments.push({ start: iv.start, end: iv.end, type: 'solid', color: iv.color, jobId: iv.jobId, stackIndex, stackCount });
    }

    const allStarts = jobIntervals.map(iv => iv.start);
    const allEnds = jobIntervals.map(iv => iv.end);
    const coveredStart = Math.min(...allStarts);
    const coveredEnd = Math.max(...allEnds);

    if (coveredStart > 0.001) segments.push({ start: 0, end: coveredStart, type: 'dashed', color: null, stackIndex: 0, stackCount: 1 });
    if (coveredEnd < 0.999) segments.push({ start: coveredEnd, end: 1, type: 'dashed', color: null, stackIndex: 0, stackCount: 1 });

    const points = new Set();
    for (const iv of jobIntervals) { points.add(iv.start); points.add(iv.end); }
    const sorted = [...points].sort((a, b) => a - b);
    for (let i = 0; i < sorted.length - 1; i++) {
      const mid = (sorted[i] + sorted[i + 1]) / 2;
      const covered = jobIntervals.some(iv => iv.start <= mid && iv.end >= mid);
      if (!covered && sorted[i + 1] - sorted[i] > 0.001) {
        segments.push({ start: sorted[i], end: sorted[i + 1], type: 'dashed', color: null, stackIndex: 0, stackCount: 1 });
      }
    }

    return segments;
  }

  function datePos(date, start, end) {
    const total = end.getTime() - start.getTime();
    if (total <= 0) return 0.5;
    return Math.max(0.02, Math.min(0.98, (date.getTime() - start.getTime()) / total));
  }

  /* ── Popup helpers ───────────────────────────────────────────────── */

  function openProjectPopup(project, event) {
    selectedRole = null;
    selectedProject = project;
    popupVideoIndex = 0;
    popupShortsPage = 0;
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

    if (isMobile) {
      // Mobile: fixed at bottom center
      popupStyle = `position: fixed; bottom: 68px; left: 50%; transform: translateX(-50%); max-width: ${popupW}px;`;
    } else {
      // Desktop: absolute, scrolls with page
      const scrollY = window.scrollY || window.pageYOffset;
      const scrollX = window.scrollX || window.pageXOffset;
      const pageX = rect.left + rect.width / 2 + scrollX;
      const pageY = rect.top + scrollY;

      let left = pageX;
      left = Math.max(popupW / 2 + 16, Math.min(viewW + scrollX - popupW / 2 - 16, left));

      const viewTop = rect.top;
      if (viewTop < 320) {
        const top = pageY + rect.height + 12;
        popupStyle = `position: absolute; top: ${top}px; left: ${left}px; transform: translateX(-50%); max-width: ${popupW}px;`;
      } else {
        const top = pageY - 12;
        popupStyle = `position: absolute; top: ${top}px; left: ${left}px; transform: translate(-50%, -100%); max-width: ${popupW}px;`;
      }
    }
  }

  function closePopup() {
    selectedProject = null;
    selectedRole = null;
  }

  /* ── Popup media classification (same rules as ProjectCard) ──────── */

  function getPopupImages(media) {
    return (media || []).filter(m => m.media_type === 'image');
  }
  function getPopupRegularVideos(media) {
    return (media || []).filter(m => m.media_type === 'video' || (m.media_type === 'youtube' && !isShorts(m.media_value)));
  }
  function getPopupShorts(media) {
    return (media || []).filter(m => m.media_type === 'youtube' && isShorts(m.media_value));
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
              {#if seg.type === 'dashed'}
                <div class="tl-segment tl-seg-dashed"
                  style="left: {seg.start * 100}%; width: {(seg.end - seg.start) * 100}%;"></div>
              {:else}
                <div class="tl-segment tl-seg-solid" class:tl-dimmed={hoveredJobId && seg.jobId !== hoveredJobId}
                  style="left: {seg.start * 100}%; width: {(seg.end - seg.start) * 100}%; background: {seg.color};{seg.stackCount > 1 ? ` height: ${4 / seg.stackCount}px; top: ${(seg.stackIndex * 4) / seg.stackCount}px;` : ''}"></div>
              {/if}
            {/each}

            <!-- ═══ JOB START MARKERS (with vertical tick connecting to line) ═══ -->
            {#each row.jobStarts as js}
              <!-- svelte-ignore a11y-no-static-element-interactions -->
              <div class="tl-job-marker" class:tl-dimmed={hoveredJobId && js.jobId !== hoveredJobId}
                style="left: {js.position * 100}%;"
                on:mouseenter={() => { hoveredJobId = js.jobId; }}
                on:mouseleave={() => { hoveredJobId = null; }}>
                <div class="tl-job-tick"></div>
                <div class="tl-job-info">
                  <span class="tl-job-name">{js.name}</span>
                  {#if js.country}<span class="tl-job-country">{js.country}</span>{/if}
                </div>
              </div>
            {/each}

            <!-- ═══ ROLE MARKERS ═══ -->
            {#each row.roleStarts as rs}
              <button class="tl-role-marker" class:tl-dimmed={hoveredJobId && (rs.role.job_id || rs.role.job?.id) !== hoveredJobId}
                style="left: {rs.position * 100}%;"
                on:click|stopPropagation={(e) => openRolePopup(rs.role, e)}
                on:mouseenter={() => { onRoleProximity(rs.role); if (!rs.currentJobs) hoveredJobId = rs.role.job_id || rs.role.job?.id; }}
                on:mouseleave={() => { hoveredJobId = null; }}
                title={rs.role.name}>
                {#if rs.currentJobs}
                  <span class="tl-currently-jobs">
                    <span class="tl-role-tag currently">{rs.tag}</span>
                    {#each rs.currentJobs as cj}
                      <span class="tl-currently-job-name">{cj.job?.name || cj.role.name}</span>
                    {/each}
                  </span>
                {:else}
                  {#if rs.tag}
                    <span class="tl-role-tag" class:promotion={rs.tag === 'Promotion'} class:currently={rs.tag === 'Currently'}>{rs.tag}</span>
                  {/if}
                  <span class="tl-role-name">{rs.role.name}</span>
                {/if}
                <span class="tl-role-icon">◆</span>
              </button>
            {/each}

            <!-- ═══ PROJECT DOTS (weight-based) ═══ -->
            {#each row.dots as dot, di}
              <button class="tl-dot {dot.weightClass}" class:active={selectedProject?.id === dot.id} class:tl-dimmed={hoveredJobId && dot.jobId !== hoveredJobId}
                style="left: {dot.position * 100}%;"
                on:click|stopPropagation={(e) => openProjectPopup(dot, e)}
                on:mouseenter={() => onRoleProximity(dot.role)}
                title={dot.name}>
                {#if dot.weightClass === 'weight-landmark'}
                  <span class="tl-dot-icon tl-dot-star">★</span>
                {:else if dot.weightClass === 'weight-continuous'}
                  <span class="tl-dot-icon tl-dot-infinity-wrap">
                    <span class="tl-dot-infinity-box">∞</span>
                  </span>
                {:else}
                  <span class="tl-dot-circle"></span>
                {/if}
                <span class="tl-dot-label" class:above={di % 2 === 0} class:below={di % 2 !== 0}>{dot.name}</span>
              </button>
            {/each}
          </div>
        </div>
      {/each}
    </div>
  {/if}

  <!-- ═══ PROJECT POPUP (full media like ProjectCard) ═══ -->
  {#if selectedProject}
    <!-- svelte-ignore a11y-click-events-have-key-events -->
    <!-- svelte-ignore a11y-no-static-element-interactions -->
    <div class="popup-backdrop" on:click={closePopup}></div>
    <div class="popup-card" style={popupStyle} on:click|stopPropagation>
      <button class="popup-close" on:click={closePopup}>×</button>

      {#if selectedProject.media?.length > 0}
        <div class="popup-media-container">
          <!-- Images: mosaic at top -->
          {#each [getPopupImages(selectedProject.media)] as images}
            {#if images.length === 1}
              <div class="popup-media">
                <img src={images[0].media_value} alt={selectedProject.name} />
              </div>
            {:else if images.length > 1}
              <div class="popup-mosaic cols-{Math.min(images.length, 3)}">
                {#each images as img}
                  <img src={img.media_value} alt={selectedProject.name} />
                {/each}
              </div>
            {/if}
          {/each}

          <!-- Regular videos / landscape YouTube -->
          {#each [getPopupRegularVideos(selectedProject.media)] as videos}
            {#if videos.length > 0}
              {#each [videos[popupVideoIndex] || videos[0]] as currentVid}
                <div class="popup-media popup-video-wrap">
                  {#if currentVid.media_type === 'video'}
                    <video src={currentVid.media_value} controls preload="metadata"></video>
                  {:else}
                    {#each [getYouTubeId(currentVid.media_value)] as ytId}
                      {#if ytId}
                        <iframe src="https://www.youtube-nocookie.com/embed/{ytId}"
                          title={selectedProject.name} frameborder="0"
                          allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture" allowfullscreen></iframe>
                      {/if}
                    {/each}
                  {/if}
                  {#if videos.length > 1}
                    <div class="popup-vid-nav">
                      <button on:click|stopPropagation={() => { popupVideoIndex = (popupVideoIndex - 1 + videos.length) % videos.length; }}>‹</button>
                      <span>{popupVideoIndex + 1}/{videos.length}</span>
                      <button on:click|stopPropagation={() => { popupVideoIndex = (popupVideoIndex + 1) % videos.length; }}>›</button>
                    </div>
                  {/if}
                </div>
              {/each}
            {/if}
          {/each}

          <!-- Shorts: pairs -->
          {#each [getPopupShorts(selectedProject.media)] as shorts}
            {#if shorts.length > 0}
              <div class="popup-shorts-pair">
                {#each shorts.slice(popupShortsPage * 2, popupShortsPage * 2 + 2) as short}
                  {#each [getYouTubeId(short.media_value)] as ytId}
                    {#if ytId}
                      <iframe src="https://www.youtube-nocookie.com/embed/{ytId}"
                        title={selectedProject.name} frameborder="0"
                        allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture" allowfullscreen
                        class="popup-short-iframe"></iframe>
                    {/if}
                  {/each}
                {/each}
              </div>
              {#if Math.ceil(shorts.length / 2) > 1}
                <div class="popup-vid-nav">
                  <button on:click|stopPropagation={() => { popupShortsPage = (popupShortsPage - 1 + Math.ceil(shorts.length / 2)) % Math.ceil(shorts.length / 2); }}>‹</button>
                  <span>{popupShortsPage + 1}/{Math.ceil(shorts.length / 2)}</span>
                  <button on:click|stopPropagation={() => { popupShortsPage = (popupShortsPage + 1) % Math.ceil(shorts.length / 2); }}>›</button>
                </div>
              {/if}
            {/if}
          {/each}
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

  .tl-track { flex: 1; position: relative; height: 4px; align-self: center; }

  /* ── Segments ────────────────────────────────────── */
  .tl-segment { position: absolute; }

  .tl-seg-solid {
    height: 4px;
    top: 0;
    border-radius: 2px;
    transition: background 0.3s;
  }

  .tl-seg-dashed {
    top: 1px;
    height: 0;
    border-top: 2px dashed #222530;
  }

  /* ── Job markers (vertical line connecting to track) ── */
  .tl-job-marker {
    position: absolute;
    top: 50%;
    transform: translateX(-50%);
    z-index: 4;
    display: flex;
    flex-direction: column;
    align-items: center;
  }

  .tl-job-tick {
    width: 2px;
    height: 32px;
    background: #4e515c;
    border-radius: 1px;
  }

  .tl-job-info {
    display: flex;
    flex-direction: column;
    align-items: center;
    margin-top: 6px;
    white-space: nowrap;
  }
  .tl-job-name { font-size: 13px; font-weight: 600; color: #8a8d98; }
  .tl-job-country { font-size: 11px; color: #4e515c; margin-top: 1px; }

  /* ── Role markers ────────────────────────────────── */
  .tl-role-marker {
    position: absolute;
    top: 0;
    transform: translate(-50%, 0);
    z-index: 5;
    background: none;
    border: none;
    cursor: pointer;
    display: flex;
    flex-direction: column;
    align-items: center;
    padding: 16px 24px;
    margin: -16px -24px;
  }

  .tl-role-tag {
    position: absolute;
    bottom: calc(100% + 28px);
    font-size: 9px;
    font-weight: 700;
    color: #e0e2e8;
    background: #2a5a3a;
    padding: 3px 10px;
    border-radius: 3px;
    white-space: nowrap;
    letter-spacing: 0.04em;
    text-transform: uppercase;
  }

  .tl-role-tag.promotion {
    background: #b8a46c;
    color: #111114;
  }

  .tl-role-tag.currently {
    background: #3a5a8a;
    color: #e0e2e8;
  }

  .tl-role-name {
    font-size: 12px;
    font-weight: 600;
    color: #6b6e7a;
    white-space: nowrap;
    position: absolute;
    bottom: calc(100% + 10px);
    transition: color 0.15s;
    padding-bottom: 3px;
    border-bottom: 1px solid #3a3d48;
  }

  .tl-role-icon {
    font-size: 12px;
    color: #4e515c;
    line-height: 1;
    display: flex;
    align-items: center;
    justify-content: center;
    width: 14px;
    height: 14px;
    transform: translateY(-5px);
    transition: color 0.15s;
  }

  .tl-currently-jobs {
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: 4px;
    position: absolute;
    bottom: calc(100% + 10px);
    white-space: nowrap;
  }

  .tl-currently-jobs .tl-role-tag {
    position: static;
    margin-bottom: 2px;
  }

  .tl-currently-job-name {
    font-size: 12px;
    font-weight: 600;
    color: #6b6e7a;
    transition: color 0.15s;
    padding-bottom: 2px;
    border-bottom: 1px solid #3a3d48;
    line-height: 1.3;
  }

  .tl-role-marker:hover .tl-role-name,
  .tl-role-marker:hover .tl-currently-job-name { color: #e0e2e8; border-bottom-color: #6b6e7a; }
  .tl-role-marker:hover .tl-role-icon { color: #8a8d98; }

  /* ── Hover dimming ─────────────────────────────────── */
  .tl-dimmed { opacity: 0.2; transition: opacity 0.2s; }
  .tl-seg-solid, .tl-job-marker, .tl-role-marker, .tl-dot { transition: opacity 0.2s; }

  /* ── Project dots: base ──────────────────────────── */
  .tl-dot {
    position: absolute;
    top: 0;
    transform: translate(-50%, -50%);
    z-index: 6;
    background: none;
    border: none;
    cursor: pointer;
    padding: 10px;
    display: flex;
    flex-direction: column;
    align-items: center;
  }

  .tl-dot-circle {
    border-radius: 50%;
    background: #6b6e7a;
    border: 2px solid #111114;
    transition: all 0.15s;
    display: block;
  }

  .tl-dot-icon {
    display: flex;
    align-items: center;
    justify-content: center;
    transition: all 0.15s;
  }

  /* Weight: Small */
  .weight-small .tl-dot-circle { width: 8px; height: 8px; }
  /* Weight: Medium */
  .weight-medium .tl-dot-circle { width: 12px; height: 12px; }
  /* Weight: Big */
  .weight-big .tl-dot-circle { width: 16px; height: 16px; }

  /* Weight: Landmark (star + glow) */
  .weight-landmark .tl-dot-star {
    font-size: 22px;
    color: #d4af37;
    filter: drop-shadow(0 0 6px rgba(212, 175, 55, 0.5));
    transform: translateY(-1px);
  }

  .weight-landmark:hover .tl-dot-star,
  .weight-landmark.active .tl-dot-star {
    color: #f0d060;
    filter: drop-shadow(0 0 10px rgba(240, 208, 96, 0.7));
    transform: translateY(-1px) scale(1.2);
  }

  /* Weight: Continuous (infinity in a box) */
  .tl-dot-infinity-wrap {
    display: flex;
    align-items: center;
    justify-content: center;
  }

  .tl-dot-infinity-box {
    display: flex;
    align-items: center;
    justify-content: center;
    width: 22px;
    height: 22px;
    border: 1.5px solid #4e515c;
    border-radius: 4px;
    background: #111114;
    font-size: 15px;
    color: #7a7faa;
    font-weight: 700;
    line-height: 1;
    transition: all 0.15s;
  }

  .weight-continuous:hover .tl-dot-infinity-box,
  .weight-continuous.active .tl-dot-infinity-box {
    border-color: #7a7faa;
    color: #a0a4cc;
    background: #16181e;
    transform: scale(1.1);
  }

  /* Dot hover (circle variants) */
  .tl-dot:hover .tl-dot-circle,
  .tl-dot.active .tl-dot-circle {
    background: #e0e2e8;
    transform: scale(1.3);
  }

  /* Dot labels */
  .tl-dot-label {
    position: absolute;
    font-size: 12px;
    color: #4e515c;
    white-space: nowrap;
    max-width: 140px;
    overflow: hidden;
    text-overflow: ellipsis;
    transition: color 0.15s;
    pointer-events: none;
  }
  .tl-dot-label.above { bottom: calc(100% - 4px); }
  .tl-dot-label.below { top: calc(100% - 4px); }
  .tl-dot:hover .tl-dot-label { color: #a0a3ae; }

  /* ── Popups ──────────────────────────────────────── */
  .popup-backdrop { position: fixed; inset: 0; z-index: 90; background: rgba(0, 0, 0, 0.35); }
  .popup-card {
    z-index: 91; background: #1a1c22;
    border: 1px solid #2a2d35; border-radius: 10px;
    overflow: hidden; overflow-y: auto;
    width: 360px; max-height: 80vh;
    box-shadow: 0 16px 48px rgba(0, 0, 0, 0.5);
  }
  .popup-close { position: absolute; top: 8px; right: 8px; z-index: 2; background: rgba(17, 17, 20, 0.7); border: none; color: #6b6e7a; width: 28px; height: 28px; border-radius: 50%; font-size: 18px; cursor: pointer; display: flex; align-items: center; justify-content: center; transition: color 0.15s; line-height: 1; }
  .popup-close:hover { color: #e0e2e8; }

  /* Popup media container */
  .popup-media-container { display: flex; flex-direction: column; }

  .popup-media { width: 100%; overflow: hidden; background: #0f1014; }
  .popup-media img { width: 100%; max-height: 200px; object-fit: cover; display: block; }
  .popup-media video { width: 100%; max-height: 200px; object-fit: contain; display: block; }
  .popup-media iframe { width: 100%; aspect-ratio: 16/9; display: block; border: none; }

  /* Popup mosaic */
  .popup-mosaic {
    display: grid; gap: 1px; background: #0f1014;
  }
  .popup-mosaic.cols-2 { grid-template-columns: 1fr 1fr; }
  .popup-mosaic.cols-3 { grid-template-columns: 1fr 1fr 1fr; }
  .popup-mosaic img { width: 100%; aspect-ratio: 16/10; object-fit: cover; display: block; }

  /* Popup video wrap */
  .popup-video-wrap { position: relative; }

  .popup-vid-nav {
    display: flex; align-items: center; justify-content: center;
    gap: 12px; padding: 6px 0; background: #111318;
  }
  .popup-vid-nav button {
    background: none; border: 1px solid #2a2d35; color: #8a8d98;
    width: 26px; height: 26px; border-radius: 50%;
    cursor: pointer; font-size: 14px;
    display: flex; align-items: center; justify-content: center;
    transition: all 0.15s;
  }
  .popup-vid-nav button:hover { border-color: #4e515c; color: #e0e2e8; }
  .popup-vid-nav span { font-size: 11px; color: #4e515c; }

  /* Popup shorts */
  .popup-shorts-pair {
    display: grid; grid-template-columns: 1fr 1fr;
    gap: 2px; background: #0f1014;
  }
  .popup-short-iframe {
    width: 100%; aspect-ratio: 9/16; display: block; border: none;
  }

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

  /* ── Mobile ──────────────────────────────────────── */
  @media (max-width: 768px) {
    .tl-row { padding: 36px 0; }
    .tl-label { width: 52px; font-size: 12px; }
    .tl-dot-label { font-size: 10px; max-width: 90px; }
    .tl-job-name { font-size: 11px; }
    .tl-job-country { font-size: 9px; }
    .tl-role-name { font-size: 10px; }
    .tl-role-tag { font-size: 8px; }
    .popup-card { width: calc(100vw - 32px); max-width: 360px; }
  }
</style>
