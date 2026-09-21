<script>
	import { onMount, onDestroy } from 'svelte';
	import { cinevote, imdbUrl } from '$lib/cinevote.js';
	import { MODES, ACCENTS, loadTheme, applyTheme, clearTheme } from '$lib/cinevoteTheme.js';

	let me = null;
	let state = null;
	let loading = true;
	let error = '';

	// theme
	let mode = 'dark';
	let accent = 'amber';

	// auth
	let authMode = 'login';
	let authUser = '';
	let authPass = '';
	let authError = '';
	let authBusy = false;

	// search
	let q = '';
	let results = [];
	let searching = false;
	let searchTimer;
	let busy = false;

	// clock
	let tick = Date.now();
	let clockTimer;
	let serverOffset = 0; // server clock minus browser clock
	let expiredAt = null; // deadline we already reloaded for

	// reveal (slot machine)
	let revealing = false;
	let reelActive = false;
	let reelIndex = 0;
	let confettiCanvas;
	let poll;

	// info modal
	let infoOpen = false;
	let infoLoading = false;
	let infoData = null;

	// coin flip
	let coinFlipping = false;
	let coinFaces = [];
	let coinDeg = 0;

	$: phase = state?.event ? state.phase : null;
	$: picks = state?.picks ?? [];
	$: myPick = picks.find((p) => p.is_mine);
	$: myVotes = state?.my_vote_pick_ids ?? [];
	$: myVoteMax = state?.my_vote_max ?? 0;
	$: votingDone = (phase === 'voting' || phase === 'runoff') && myVoteMax > 0 && myVotes.length >= myVoteMax;
	$: if (phase !== 'concluded' && revealing && !coinFlipping) revealing = false;

	// --- schedule ---------------------------------------------------------
	$: deadlineMs = state?.phase_deadline ? Date.parse(state.phase_deadline) : null;
	$: msLeft = deadlineMs === null ? null : deadlineMs - (tick + serverOffset);
	$: if (msLeft !== null && msLeft <= 0 && expiredAt !== deadlineMs && !busy) {
		expiredAt = deadlineMs;
		loadEvent();
	}

	onMount(async () => {
		const t = loadTheme();
		mode = t.mode;
		accent = t.accent;
		applyTheme(mode, accent);

		try {
			me = await cinevote.me();
		} catch {}
		if (me) await loadEvent();
		loading = false;
		clockTimer = setInterval(() => (tick = Date.now()), 1000);
		poll = setInterval(() => {
			if (me && !revealing && !coinFlipping && !busy && document.visibilityState === 'visible') loadEvent();
		}, 4000);
	});
	onDestroy(() => {
		clearInterval(poll);
		clearInterval(clockTimer);
		clearTheme();
	});

	function setMode(m) {
		mode = m;
		applyTheme(mode, accent);
	}
	function setAccent(a) {
		accent = a;
		applyTheme(mode, accent);
	}

	async function loadEvent() {
		try {
			state = await cinevote.event();
			if (state?.server_now) serverOffset = Date.parse(state.server_now) - Date.now();
		} catch (e) {
			error = e.message;
		}
	}

	async function doAuth() {
		authBusy = true;
		authError = '';
		try {
			me = authMode === 'login' ? await cinevote.login(authUser, authPass) : await cinevote.register(authUser, authPass);
			authPass = '';
			await loadEvent();
		} catch (e) {
			authError = e.message;
		} finally {
			authBusy = false;
		}
	}
	async function doLogout() {
		await cinevote.logout();
		me = null;
		state = null;
	}

	function onSearchInput() {
		clearTimeout(searchTimer);
		const term = q.trim();
		if (!term) return (results = []);
		searchTimer = setTimeout(async () => {
			searching = true;
			try {
				results = await cinevote.search(term);
			} catch (e) {
				error = e.message;
			} finally {
				searching = false;
			}
		}, 350);
	}
	async function pickMovie(m) {
		busy = true;
		error = '';
		try {
			state = await cinevote.addPick(m);
			q = '';
			results = [];
		} catch (e) {
			error = e.message;
		} finally {
			busy = false;
		}
	}
	async function removePick() {
		busy = true;
		try {
			state = await cinevote.deletePick();
		} catch (e) {
			error = e.message;
		} finally {
			busy = false;
		}
	}
	async function castVote(p) {
		busy = true;
		error = '';
		try {
			state = await cinevote.vote(p.id);
		} catch (e) {
			error = e.message;
		} finally {
			busy = false;
		}
	}
	async function toggleWatched(p) {
		try {
			state = await cinevote.toggleWatched(p.id);
		} catch (e) {
			error = e.message;
		}
	}

	function votable(p) {
		return (phase === 'voting' || phase === 'runoff') && !p.is_mine && (phase !== 'runoff' || p.in_runoff);
	}
	function posterClick(p) {
		if (votable(p)) {
			if (myVotes.includes(p.id) || myVotes.length < myVoteMax) return castVote(p);
			return openInfo(p); // at max, can't add — show info instead
		}
		openInfo(p);
	}

	async function openInfo(p) {
		infoOpen = true;
		infoLoading = true;
		infoData = { title: p.title, year: p.year, poster_url: p.poster_url, imdb_id: p.imdb_id, tmdb_id: p.tmdb_id };
		try {
			infoData = await cinevote.movie(p.tmdb_id);
		} catch (e) {
			error = e.message;
		} finally {
			infoLoading = false;
		}
	}
	function closeInfo() {
		infoOpen = false;
		infoData = null;
	}

	const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

	async function revealWinner() {
		if (!state?.results || picks.length === 0) return;
		const winIdx = picks.findIndex((p) => p.id === state.results.winner_pick_id);
		if (winIdx < 0) return;
		revealing = true;
		reelActive = true;
		const spins = picks.length * 4 + winIdx;
		let delay = 85;
		for (let step = 0; step <= spins; step++) {
			reelIndex = step % picks.length;
			await sleep(delay);
			if (step > spins - picks.length * 1.5) delay += 38;
		}
		reelIndex = winIdx;
		reelActive = false;
		fireConfetti();
	}

	async function flipCoin() {
		const ids = state?.coinflip_pick_ids ?? [];
		coinFaces = ids.map((id) => picks.find((p) => p.id === id)).filter(Boolean).slice(0, 2);
		coinFlipping = true;
		busy = true;
		error = '';
		let res;
		try {
			res = await cinevote.flipCoin();
		} catch (e) {
			error = e.message;
			coinFlipping = false;
			busy = false;
			return;
		}
		const winnerId = res.results.winner_pick_id;
		const winnerIsFace0 = coinFaces[0] && coinFaces[0].id === winnerId;
		coinDeg = 360 * 8 + (winnerIsFace0 ? 0 : 180);
		await sleep(2700);
		state = res;
		revealing = true;
		reelActive = false;
		reelIndex = picks.findIndex((p) => p.id === winnerId);
		if (reelIndex < 0) reelIndex = 0;
		fireConfetti();
		coinFlipping = false;
		busy = false;
	}

	function fireConfetti() {
		const canvas = confettiCanvas;
		if (!canvas) return;
		const ctx = canvas.getContext('2d');
		canvas.width = canvas.offsetWidth;
		canvas.height = canvas.offsetHeight;
		// confetti follows the active theme
		const css = getComputedStyle(document.documentElement);
		const tok = (name, fallback) => (css.getPropertyValue(name) || '').trim() || fallback;
		const colors = [
			tok('--cv-accent', '#d8a72e'),
			tok('--cv-ok', '#63a56e'),
			tok('--cv-warn', '#c9a13f'),
			tok('--cv-err', '#cf6157'),
			tok('--cv-fg', '#d3d8de')
		];
		const parts = Array.from({ length: 150 }, () => ({
			x: canvas.width / 2, y: canvas.height / 3,
			vx: Math.cos(Math.random() * Math.PI * 2) * (3 + Math.random() * 7),
			vy: -6 - Math.random() * 8, s: 4 + Math.random() * 6,
			c: colors[(Math.random() * colors.length) | 0], rot: Math.random() * Math.PI, vr: (Math.random() - 0.5) * 0.3
		}));
		const start = performance.now();
		function frame(now) {
			const t = now - start;
			ctx.clearRect(0, 0, canvas.width, canvas.height);
			for (const p of parts) {
				p.vy += 0.22; p.x += p.vx; p.y += p.vy; p.rot += p.vr;
				ctx.save();
				ctx.globalAlpha = Math.max(0, 1 - t / 2800);
				ctx.translate(p.x, p.y); ctx.rotate(p.rot);
				ctx.fillStyle = p.c;
				ctx.fillRect(-p.s / 2, -p.s / 2, p.s, p.s * 1.6);
				ctx.restore();
			}
			if (t < 2800) requestAnimationFrame(frame);
			else ctx.clearRect(0, 0, canvas.width, canvas.height);
		}
		requestAnimationFrame(frame);
	}

	function observeCenter(node) {
		if (typeof window === 'undefined' || !window.matchMedia('(hover: none)').matches) return;
		const io = new IntersectionObserver(
			(entries) => entries.forEach((e) => e.target.classList.toggle('centered', e.isIntersecting)),
			{ rootMargin: '-45% 0px -45% 0px', threshold: 0 }
		);
		node.querySelectorAll('.poster').forEach((c) => io.observe(c));
		return { destroy: () => io.disconnect() };
	}

	// --- phase presentation ------------------------------------------------
	const STAGES = [
		{ key: 'pick', label: 'PICK', phases: ['picking'] },
		{ key: 'vote', label: 'VOTE', phases: ['voting', 'runoff', 'coinflip'] },
		{ key: 'result', label: 'RESULT', phases: ['concluded'] }
	];

	const PHASE = {
		picking: {
			title: 'PICKING',
			tag: null,
			desc: 'Search and lock in one movie each. A film can only be picked once per night, and you can swap yours until picking closes.',
			clock: 'picking closes in'
		},
		voting: {
			title: 'VOTING',
			tag: null,
			desc: "Two votes each, on two different movies, never your own. Flag what you have already seen: unseen is worth 2 points, seen 1.",
			clock: 'voting closes in'
		},
		runoff: {
			title: 'VOTING',
			tag: 'TIE-BREAK',
			desc: 'Dead heat at the top. One vote each, only between the tied movies below.',
			clock: 'voting closes in'
		},
		coinflip: {
			title: 'VOTING',
			tag: 'COIN FLIP',
			desc: 'Still tied after the tie-break. The coin decides — flip it.',
			clock: 'voting closes in'
		},
		concluded: {
			title: 'DECIDED',
			tag: null,
			desc: 'The vote is in. The winner is below — see you at the premiere.',
			clock: null
		}
	};

	$: stageIndex = STAGES.findIndex((s) => s.phases.includes(phase));
	$: info = PHASE[phase] ?? null;

	function stageState(i) {
		if (stageIndex < 0) return 'todo';
		if (i < stageIndex) return 'done';
		if (i === stageIndex) return 'now';
		return 'todo';
	}

	function fmtLeft(ms) {
		if (ms === null) return '';
		if (ms <= 0) return '00:00:00';
		const total = Math.floor(ms / 1000);
		const d = Math.floor(total / 86400);
		const h = Math.floor((total % 86400) / 3600);
		const m = Math.floor((total % 3600) / 60);
		const s = total % 60;
		const pad = (n) => String(n).padStart(2, '0');
		return `${d > 0 ? d + 'd ' : ''}${pad(h)}:${pad(m)}:${pad(s)}`;
	}

	function fmtPrague(iso) {
		if (!iso) return '';
		try {
			return new Intl.DateTimeFormat('en-GB', {
				weekday: 'short', day: '2-digit', month: 'short',
				hour: '2-digit', minute: '2-digit', hour12: false, timeZone: 'Europe/Prague'
			}).format(new Date(iso));
		} catch {
			return iso.slice(0, 16).replace('T', ' ');
		}
	}
</script>

<svelte:head>
	<title>cinevote</title>
	<link rel="preconnect" href="https://cdn.jsdelivr.net" crossorigin />
	<link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/@fontsource-variable/jetbrains-mono@5.3.0/index.css" />
</svelte:head>

<div class="cv">
	<header class="cv-head">
		<a class="brand" href="/cinevote"><span class="bar"></span>cinevote</a>

		<div class="head-right">
			<div class="theme" role="group" aria-label="Theme">
				<div class="modes">
					{#each MODES as m (m)}
						<button class="mode" class:on={mode === m} on:click={() => setMode(m)} title="{m} theme">{m}</button>
					{/each}
				</div>
				<div class="swatches">
					{#each ACCENTS as a (a)}
						<button class="swatch sw-{a}" class:on={accent === a} on:click={() => setAccent(a)} title="{a} accent" aria-label="{a} accent"></button>
					{/each}
				</div>
			</div>
			{#if me}
				<div class="who"><span class="uname">{me.username}</span><button class="ghost" on:click={doLogout}>log out</button></div>
			{/if}
		</div>
	</header>

	{#if loading}
		<p class="dim center">loading…</p>
	{:else if !me}
		<div class="panel-box">
			<h1><span class="prompt">&gt;</span>{authMode === 'login' ? 'log in' : 'create account'}</h1>
			{#if authError}<div class="err">{authError}</div>{/if}
			<form on:submit|preventDefault={doAuth}>
				<label class="field">
					<span>username</span>
					<input bind:value={authUser} autocomplete="username" />
				</label>
				<label class="field">
					<span>password</span>
					<input type="password" bind:value={authPass} autocomplete={authMode === 'login' ? 'current-password' : 'new-password'} />
				</label>
				<button class="primary" disabled={authBusy}>{authBusy ? '…' : authMode === 'login' ? 'log in' : 'register'}</button>
			</form>
			<p class="dim sm">
				{authMode === 'login' ? 'no account?' : 'have an account?'}
				<button class="link" on:click={() => (authMode = authMode === 'login' ? 'register' : 'login')}>{authMode === 'login' ? 'register' : 'log in'}</button>
			</p>
		</div>
	{:else if !state?.event}
		<div class="panel-box">
			<h1><span class="prompt">&gt;</span>no movie night scheduled</h1>
			<p class="dim sm">Nothing on the calendar yet. The next one is scheduled from the admin panel — picking opens six days before the premiere.</p>
		</div>
	{:else}
		<!-- ===== PHASE STAGE ===== -->
		<section class="stage">
			<div class="stage-rail">
				{#each STAGES as st, i (st.key)}
					<div class="rail-step" data-state={stageState(i)}>
						<span class="rail-n">{i + 1}</span>
						<span class="rail-label">{st.label}</span>
					</div>
					{#if i < STAGES.length - 1}<span class="rail-sep" data-state={stageState(i)}></span>{/if}
				{/each}
			</div>

			<div class="stage-body">
				<div class="stage-line">
					<h1 class="stage-title">{info?.title ?? phase}</h1>
					{#if info?.tag}<span class="stage-tag">{info.tag}</span>{/if}
					<span class="stage-meta">{state.event.name || 'movie night'} · {state.event.event_date}</span>
				</div>

				<p class="stage-desc">{info?.desc ?? ''}</p>

				{#if info?.clock && deadlineMs !== null}
					<div class="clock" class:urgent={msLeft !== null && msLeft < 6 * 3600 * 1000}>
						<span class="clock-label">{info.clock}</span>
						<span class="clock-value">{fmtLeft(msLeft)}</span>
						<span class="clock-abs">// {fmtPrague(state.phase_deadline)} Prague</span>
					</div>
				{/if}

				<p class="stage-foot">4 days to pick &middot; 2 days to vote &middot; decided at midnight on premiere day</p>
			</div>
		</section>

		{#if error}<div class="err">{error}</div>{/if}

		<div class="layout">
			<main>
				<!-- coin flip -->
				{#if phase === 'coinflip'}
					<div class="coin-section">
						{#if coinFlipping || coinFaces.length}
							<div class="coin-stage">
								<div class="coin" style="transform: rotateY({coinDeg}deg); transition: {coinFlipping ? 'transform 2.6s cubic-bezier(0.15,0.75,0.2,1)' : 'none'};">
									<div class="coin-face front">{#if coinFaces[0]?.poster_url}<img src={coinFaces[0].poster_url} alt="" />{/if}</div>
									<div class="coin-face back">{#if coinFaces[1]?.poster_url}<img src={coinFaces[1].poster_url} alt="" />{/if}</div>
								</div>
							</div>
						{/if}
						{#if !coinFlipping}
							<button class="primary big" on:click={flipCoin} disabled={busy}>flip the coin</button>
						{/if}
					</div>
				{/if}

				<!-- SEARCH (picking) -->
				{#if phase === 'picking'}
					<div class="search" class:greyed={!!myPick}>
						<span class="prompt">$</span>
						<input placeholder={myPick ? 'you already picked — remove it to choose another' : 'search a movie…'} bind:value={q} on:input={onSearchInput} disabled={!!myPick || busy} />
						{#if searching}<span class="dim sm">searching…</span>{/if}
					</div>
					{#if results.length && !myPick}
						<div class="grid results-grid">
							{#each results as m (m.tmdb_id)}
								<button class="poster pick-result" on:click={() => pickMovie(m)} disabled={busy} title="pick this">
									<div class="poster-img"><img src={m.poster_url} alt={m.title} loading="lazy" /></div>
									<span class="cap"><span class="title">{m.title}</span>{#if m.year} <em>{m.year}</em>{/if}</span>
								</button>
							{/each}
						</div>
						<div class="rule"></div>
					{/if}
				{/if}

				<!-- PICKS GRID -->
				{#if picks.length}
					<div class="grid" use:observeCenter>
						{#each picks as p (p.id)}
							<div class="poster" class:voted={myVotes.includes(p.id)} class:greyed={votingDone && !myVotes.includes(p.id)} class:winner={phase === 'concluded' && p.id === state.results?.winner_pick_id} class:dim-out={phase === 'runoff' && !p.in_runoff}>
								<div class="poster-img" on:click={() => posterClick(p)} on:keydown={(e) => e.key === 'Enter' && posterClick(p)} role="button" tabindex="0" title={votable(p) ? 'click to vote' : 'click for info'}>
									{#if p.poster_url}
										<img src={p.poster_url} alt={p.title} loading="lazy" />
									{:else}
										<div class="noposter">{p.title}</div>
									{/if}
									{#if p.is_mine && phase === 'picking'}
										<button class="corner" on:click|stopPropagation={removePick} title="remove your pick" disabled={busy}>✕</button>
									{/if}
									{#if myVotes.includes(p.id)}<span class="vote-flag">✓</span>{/if}
									{#if phase === 'concluded' && p.id === state.results?.winner_pick_id}<span class="win-flag">winner</span>{/if}
								</div>

								<div class="cap">
									<span class="title">{p.title}</span>{#if p.year} <em>{p.year}</em>{/if}
									<span class="owner">@{p.owner_name}</span>
								</div>

								<div class="card-actions">
									<button class="act" on:click={() => openInfo(p)} title="movie info">info</button>
									<button class="act" class:active={p.watched_by_me} on:click={() => toggleWatched(p)} title="mark as seen">{p.watched_by_me ? 'seen' : 'unseen'}</button>
								</div>
							</div>
						{/each}
					</div>
				{:else}
					<p class="dim">no picks yet{phase === 'picking' ? ' — be the first.' : '.'}</p>
				{/if}

				<!-- RESULTS -->
				{#if phase === 'concluded' && state.results}
					<section class="results">
						<div class="reel-wrap">
							<canvas bind:this={confettiCanvas} class="confetti"></canvas>
							{#if revealing}
								{#each [picks[reelIndex]] as r (reelIndex)}
									<div class="reel" class:spin={reelActive}>
										{#if r?.poster_url}<img src={r.poster_url} alt={r.title} />{/if}
										<div class="reel-cap">{r?.title}</div>
									</div>
								{/each}
								{#if !reelActive}<div class="winner-tag">winner</div>{/if}
							{:else}
								<button class="primary big" on:click={revealWinner}>reveal the winner</button>
							{/if}
						</div>
						{#if revealing && !reelActive}
							<table class="ranking">
								<tbody>
									{#each state.results.ranking as r, i (r.pick_id)}
										<tr class:win={r.pick_id === state.results.winner_pick_id}>
											<td class="rank">{String(i + 1).padStart(2, '0')}</td>
											<td>{r.title}</td>
											<td class="pts">{r.points} pt{r.points === 1 ? '' : 's'}</td>
										</tr>
									{/each}
								</tbody>
							</table>
							{#if state.results.had_runoff}<p class="dim sm">decided by tie-break.</p>{/if}
						{/if}
					</section>
				{/if}
			</main>

			<aside class="side">
				<h3>participants</h3>
				{#if state.participants.length}
					<ul>
						{#each state.participants as part (part.user_id)}
							<li>
								<span class="dot" class:voted={(phase === 'voting' || phase === 'runoff') && part.has_voted} class:picked={phase !== 'voting' && phase !== 'runoff'}></span>
								<span class="pname">{part.username}</span>
								{#if phase === 'voting' || phase === 'runoff'}
									<span class="pstate">{part.has_voted ? 'voted' : 'waiting'}</span>
								{/if}
							</li>
						{/each}
					</ul>
					{#if phase === 'voting' || phase === 'runoff'}
						<p class="dim sm counter">{state.participants.filter((p) => p.has_voted).length}/{state.participants.length} voted</p>
					{:else}
						<p class="dim sm counter">{state.participants.length} picked</p>
					{/if}
				{:else}
					<p class="dim sm">nobody yet.</p>
				{/if}
			</aside>
		</div>
	{/if}
</div>

<!-- INFO MODAL -->
{#if infoOpen}
	<div class="modal-back" on:click={closeInfo} on:keydown={(e) => e.key === 'Escape' && closeInfo()} role="button" tabindex="-1">
		<div class="modal" on:click|stopPropagation role="dialog" tabindex="0">
			<button class="modal-x" on:click={closeInfo}>✕</button>
			<div class="modal-head">
				{#if infoData?.poster_url}<img class="modal-poster" src={infoData.poster_url} alt={infoData.title} />{/if}
				<div>
					<h2>{infoData?.title}{#if infoData?.year} <span class="dim">{infoData.year}</span>{/if}</h2>
					{#if infoData?.rating}<div class="rating">{infoData.rating}<span class="dim">/10</span></div>{/if}
					{#if infoData?.director}<p class="meta"><span class="dim">dir.</span> {infoData.director}</p>{/if}
					{#if infoData?.imdb_id}<a class="imdb-link" href={imdbUrl(infoData)} target="_blank" rel="noopener">imdb ↗</a>{/if}
				</div>
			</div>
			{#if infoLoading}
				<p class="dim">loading…</p>
			{:else}
				{#if infoData?.overview}<p class="overview">{infoData.overview}</p>{/if}
				{#if infoData?.cast?.length}
					<div class="cast">
						{#each infoData.cast as c (c.name)}
							<div class="actor">
								{#if c.photo}<img src={c.photo} alt={c.name} loading="lazy" />{:else}<div class="noface">{c.name?.[0] ?? '?'}</div>{/if}
								<div class="actor-name">{c.name}</div>
								{#if c.character}<div class="actor-char dim">{c.character}</div>{/if}
							</div>
						{/each}
					</div>
				{/if}
			{/if}
		</div>
	</div>
{/if}

<style>
	/* ===================================================================
	   THEME TOKENS
	   Set as attributes on <html> by cinevoteTheme.js, so the modal (which
	   renders outside .cv) inherits them too. Only CineVote pages set them,
	   so the rest of the site keeps its own palette.
	   =================================================================== */
	:global(html[data-cv-theme='dark']),
	:global(html:not([data-cv-theme])) {
		--cv-bg: #0c0e11;
		--cv-surface: #131619;
		--cv-inset: #0f1215;
		--cv-line: #232830;
		--cv-line-hi: #333a45;
		--cv-fg: #d3d8de;
		--cv-fg-dim: #7c8590;
		--cv-fg-faint: #545c66;
		--cv-ok: #63a56e;
		--cv-warn: #c9a13f;
		--cv-err: #cf6157;
		--cv-shade: rgba(255, 255, 255, 0.025);

		--cv-a-amber: #d8a72e;
		--cv-a-blue: #4f9cf0;
		--cv-a-green: #5fb36a;
		--cv-a-magenta: #bd7ad4;
		--cv-a-cyan: #3fb5ad;
		--cv-a-red: #dc6a5c;
	}
	:global(html[data-cv-theme='light']) {
		--cv-bg: #f4f4f1;
		--cv-surface: #fbfbf9;
		--cv-inset: #ecece8;
		--cv-line: #d8d8d1;
		--cv-line-hi: #b9b9b0;
		--cv-fg: #21252a;
		--cv-fg-dim: #5d646c;
		--cv-fg-faint: #8b9199;
		--cv-ok: #2f7d3b;
		--cv-warn: #8a6510;
		--cv-err: #b53f32;
		--cv-shade: rgba(0, 0, 0, 0.02);

		--cv-a-amber: #96690a;
		--cv-a-blue: #1f66d6;
		--cv-a-green: #2a7a35;
		--cv-a-magenta: #8b3fa8;
		--cv-a-cyan: #0f7b74;
		--cv-a-red: #bc4033;
	}

	:global(html[data-cv-accent='amber']),
	:global(html:not([data-cv-accent])) { --cv-accent: var(--cv-a-amber); }
	:global(html[data-cv-accent='blue']) { --cv-accent: var(--cv-a-blue); }
	:global(html[data-cv-accent='green']) { --cv-accent: var(--cv-a-green); }
	:global(html[data-cv-accent='magenta']) { --cv-accent: var(--cv-a-magenta); }
	:global(html[data-cv-accent='cyan']) { --cv-accent: var(--cv-a-cyan); }
	:global(html[data-cv-accent='red']) { --cv-accent: var(--cv-a-red); }

	:global(html) {
		--cv-accent-bg: color-mix(in srgb, var(--cv-accent) 13%, transparent);
		--cv-accent-bg-hi: color-mix(in srgb, var(--cv-accent) 22%, transparent);
		--cv-accent-line: color-mix(in srgb, var(--cv-accent) 55%, transparent);
	}

	:global(html[data-cv-theme] body) {
		background: var(--cv-bg);
		color: var(--cv-fg);
	}

	/* ===================================================================
	   BASE — monospace, square corners, hairline rules
	   =================================================================== */
	.cv {
		--mono: 'JetBrains Mono Variable', 'JetBrains Mono', 'IBM Plex Mono', 'SFMono-Regular', Consolas,
			'DejaVu Sans Mono', 'Liberation Mono', Menlo, monospace;
		max-width: 1180px;
		margin: 0 auto;
		padding: 1.5rem 1.25rem 5rem;
		color: var(--cv-fg);
		background: var(--cv-bg);
		font-family: var(--mono);
		font-size: 0.875rem;
		line-height: 1.55;
		min-height: 100vh;
	}
	.cv :global(*) { border-radius: 0; }

	.dim { color: var(--cv-fg-dim); }
	.sm { font-size: 0.78rem; }
	.center { text-align: center; margin-top: 3rem; }
	.prompt { color: var(--cv-accent); margin-right: 0.45rem; }
	.rule { border-top: 1px solid var(--cv-line); margin: 1.5rem 0; }

	h1 { font-size: 1.05rem; font-weight: 600; letter-spacing: 0.02em; margin: 0 0 0.9rem; }
	h2 { font-size: 1rem; font-weight: 600; margin: 0 0 0.4rem; }
	h3 {
		font-size: 0.72rem; font-weight: 600; text-transform: uppercase;
		letter-spacing: 0.14em; color: var(--cv-fg-faint);
		margin: 0 0 0.75rem; padding-bottom: 0.5rem; border-bottom: 1px solid var(--cv-line);
	}

	/* --- header ------------------------------------------------------ */
	.cv-head {
		display: flex; justify-content: space-between; align-items: center; gap: 1rem;
		flex-wrap: wrap; padding-bottom: 0.9rem; border-bottom: 1px solid var(--cv-line);
		margin-bottom: 1.5rem;
	}
	.brand {
		display: inline-flex; align-items: center; gap: 0.5rem;
		font-size: 1.05rem; font-weight: 600; letter-spacing: 0.06em;
		color: var(--cv-fg); text-decoration: none;
	}
	.brand .bar { width: 4px; height: 1.05rem; background: var(--cv-accent); display: block; }
	.head-right { display: flex; align-items: center; gap: 1.25rem; flex-wrap: wrap; }

	.theme { display: flex; align-items: center; gap: 0.75rem; }
	.modes { display: flex; border: 1px solid var(--cv-line); }
	.mode {
		background: transparent; border: none; color: var(--cv-fg-faint);
		font: inherit; font-size: 0.72rem; padding: 0.22rem 0.55rem;
		letter-spacing: 0.06em;
	}
	.mode + .mode { border-left: 1px solid var(--cv-line); }
	.mode:hover { color: var(--cv-fg); background: var(--cv-shade); }
	.mode.on { background: var(--cv-accent-bg); color: var(--cv-accent); }

	.swatches { display: flex; gap: 0.3rem; }
	.swatch { width: 15px; height: 15px; border: 1px solid var(--cv-line-hi); padding: 0; display: block; }
	.swatch.on { box-shadow: 0 0 0 1px var(--cv-bg), 0 0 0 2px var(--cv-fg-dim); }
	.sw-amber { background: var(--cv-a-amber); }
	.sw-blue { background: var(--cv-a-blue); }
	.sw-green { background: var(--cv-a-green); }
	.sw-magenta { background: var(--cv-a-magenta); }
	.sw-cyan { background: var(--cv-a-cyan); }
	.sw-red { background: var(--cv-a-red); }

	.who { display: flex; align-items: center; gap: 0.7rem; }
	.uname { color: var(--cv-accent); font-size: 0.8rem; }

	/* --- controls ----------------------------------------------------- */
	button { cursor: pointer; font: inherit; }
	input {
		width: 100%; padding: 0.45rem 0.6rem; background: var(--cv-inset);
		border: 1px solid var(--cv-line); color: var(--cv-fg); font: inherit; font-size: 0.85rem;
	}
	input:focus { outline: none; border-color: var(--cv-accent); background: var(--cv-surface); }
	input:disabled { color: var(--cv-fg-faint); }

	.primary {
		background: var(--cv-accent-bg); color: var(--cv-accent);
		border: 1px solid var(--cv-accent-line); padding: 0.45rem 1rem;
		font-size: 0.82rem; letter-spacing: 0.05em;
	}
	.primary:hover:not(:disabled) { background: var(--cv-accent-bg-hi); }
	.primary:disabled { opacity: 0.4; cursor: default; }
	.primary.big { padding: 0.6rem 1.6rem; font-size: 0.9rem; }
	.ghost {
		background: transparent; border: 1px solid var(--cv-line); color: var(--cv-fg-dim);
		padding: 0.22rem 0.55rem; font-size: 0.72rem;
	}
	.ghost:hover { background: var(--cv-shade); color: var(--cv-fg); }
	.link { background: none; border: none; color: var(--cv-accent); text-decoration: underline; padding: 0; font-size: inherit; }

	.err {
		background: color-mix(in srgb, var(--cv-err) 10%, transparent);
		border: 1px solid color-mix(in srgb, var(--cv-err) 45%, transparent);
		border-left-width: 3px; color: var(--cv-err);
		padding: 0.5rem 0.75rem; margin: 0.9rem 0; font-size: 0.8rem;
	}

	.panel-box {
		max-width: 400px; margin: 3.5rem auto; background: var(--cv-surface);
		border: 1px solid var(--cv-line); padding: 1.5rem;
	}
	.panel-box form { display: flex; flex-direction: column; gap: 0.8rem; margin: 1.1rem 0; }
	.field { display: flex; flex-direction: column; gap: 0.25rem; }
	.field > span { font-size: 0.7rem; text-transform: uppercase; letter-spacing: 0.12em; color: var(--cv-fg-faint); }

	/* ===================================================================
	   PHASE STAGE
	   =================================================================== */
	.stage { border: 1px solid var(--cv-line); background: var(--cv-surface); margin-bottom: 1.75rem; }

	.stage-rail {
		display: flex; align-items: center; gap: 0.5rem;
		padding: 0.6rem 1rem; border-bottom: 1px solid var(--cv-line);
		background: var(--cv-inset); flex-wrap: wrap;
	}
	.rail-step {
		display: inline-flex; align-items: center; gap: 0.45rem;
		padding: 0.18rem 0.55rem; font-size: 0.72rem; letter-spacing: 0.12em;
		border: 1px solid transparent; color: var(--cv-fg-faint);
	}
	.rail-n { font-size: 0.66rem; opacity: 0.75; }
	.rail-step[data-state='done'] { color: var(--cv-fg-dim); }
	.rail-step[data-state='done'] .rail-label { text-decoration: line-through; text-decoration-thickness: 1px; }
	.rail-step[data-state='now'] {
		color: var(--cv-accent); background: var(--cv-accent-bg);
		border-color: var(--cv-accent-line);
	}
	.rail-sep { flex: 0 0 auto; width: 26px; height: 1px; background: var(--cv-line-hi); }
	.rail-sep[data-state='done'] { background: var(--cv-accent-line); }

	.stage-body { padding: 1.1rem 1rem 1rem; }
	.stage-line { display: flex; align-items: baseline; gap: 0.75rem; flex-wrap: wrap; }
	.stage-title {
		font-size: 1.45rem; font-weight: 700; letter-spacing: 0.1em;
		color: var(--cv-accent); margin: 0;
	}
	.stage-tag {
		font-size: 0.68rem; letter-spacing: 0.16em; padding: 0.15rem 0.5rem;
		background: color-mix(in srgb, var(--cv-warn) 16%, transparent);
		border: 1px solid color-mix(in srgb, var(--cv-warn) 50%, transparent);
		color: var(--cv-warn);
	}
	.stage-meta { margin-left: auto; font-size: 0.76rem; color: var(--cv-fg-faint); }
	.stage-desc { color: var(--cv-fg-dim); margin: 0.5rem 0 0; max-width: 74ch; font-size: 0.83rem; }

	.clock {
		display: flex; align-items: baseline; gap: 0.7rem; flex-wrap: wrap;
		margin-top: 0.9rem; padding: 0.5rem 0.75rem;
		background: var(--cv-inset); border: 1px solid var(--cv-line);
		border-left: 3px solid var(--cv-accent);
	}
	.clock-label { font-size: 0.68rem; text-transform: uppercase; letter-spacing: 0.14em; color: var(--cv-fg-faint); }
	.clock-value { font-size: 1.25rem; font-weight: 700; letter-spacing: 0.06em; font-variant-numeric: tabular-nums; color: var(--cv-fg); }
	.clock-abs { font-size: 0.74rem; color: var(--cv-fg-faint); }
	.clock.urgent { border-left-color: var(--cv-err); }
	.clock.urgent .clock-value { color: var(--cv-err); }

	.stage-foot {
		margin: 0.85rem 0 0; padding-top: 0.6rem; border-top: 1px solid var(--cv-line);
		font-size: 0.72rem; color: var(--cv-fg-faint); letter-spacing: 0.03em;
	}

	/* ===================================================================
	   LAYOUT / GRID
	   =================================================================== */
	.layout { display: grid; grid-template-columns: 1fr 210px; gap: 1.75rem; align-items: start; }

	.search { display: flex; align-items: center; gap: 0.5rem; margin-bottom: 1.1rem; }
	.search .prompt { margin: 0; }
	.search.greyed input { color: var(--cv-fg-faint); }

	.grid { display: grid; grid-template-columns: repeat(2, 1fr); gap: 1rem; }
	@media (min-width: 640px) { .grid { grid-template-columns: repeat(3, 1fr); } }
	@media (min-width: 900px) { .grid { grid-template-columns: repeat(4, 1fr); } }
	.results-grid { margin-bottom: 1rem; }

	.poster {
		position: relative; background: var(--cv-surface); border: 1px solid var(--cv-line);
		display: flex; flex-direction: column; transition: border-color 0.12s, opacity 0.2s;
		padding: 0; text-align: left; color: var(--cv-fg);
	}
	.poster:hover { border-color: var(--cv-line-hi); }
	.poster.greyed { opacity: 0.3; filter: grayscale(0.7); }
	.poster.voted { border-color: var(--cv-accent); background: var(--cv-accent-bg); opacity: 1; filter: none; }
	.poster.winner { border-color: var(--cv-warn); }
	.poster.dim-out { opacity: 0.32; }
	.poster-img { position: relative; cursor: pointer; overflow: hidden; }
	.poster-img img { width: 100%; aspect-ratio: 2/3; object-fit: cover; display: block; }
	.poster-img:hover img { filter: brightness(1.07); }
	.noposter {
		aspect-ratio: 2/3; display: flex; align-items: center; justify-content: center;
		text-align: center; padding: 0.5rem; color: var(--cv-fg-faint); background: var(--cv-inset);
	}

	.cap { padding: 0.5rem 0.6rem; font-size: 0.78rem; line-height: 1.35; flex: 1; display: block; }
	.cap .title { color: var(--cv-fg); }
	.cap em { color: var(--cv-fg-faint); font-style: normal; }
	.cap .owner { display: block; color: var(--cv-accent); font-size: 0.72rem; margin-top: 0.15rem; }
	.pick-result:hover { border-color: var(--cv-accent); }

	.card-actions { display: flex; border-top: 1px solid var(--cv-line); }
	.act {
		flex: 1; background: transparent; border: none; color: var(--cv-fg-faint);
		padding: 0.4rem; font-size: 0.72rem; letter-spacing: 0.06em;
		border-right: 1px solid var(--cv-line);
	}
	.act:last-child { border-right: none; }
	.act:hover { background: var(--cv-shade); color: var(--cv-fg); }
	.act.active { color: var(--cv-ok); background: color-mix(in srgb, var(--cv-ok) 12%, transparent); }

	.corner {
		position: absolute; top: 0; left: 0; width: 24px; height: 24px; border: none;
		display: flex; align-items: center; justify-content: center; font-size: 0.75rem; z-index: 3;
		background: var(--cv-err); color: #fff;
	}
	.vote-flag {
		position: absolute; top: 0; right: 0; width: 24px; height: 24px;
		background: var(--cv-accent); color: var(--cv-bg);
		display: flex; align-items: center; justify-content: center; font-weight: 700; z-index: 3;
	}
	.win-flag {
		position: absolute; bottom: 0; left: 0; right: 0; text-align: center;
		background: var(--cv-warn); color: var(--cv-bg);
		font-size: 0.68rem; letter-spacing: 0.16em; padding: 0.15rem 0;
	}

	/* --- side panel ---------------------------------------------------- */
	.side { border: 1px solid var(--cv-line); background: var(--cv-surface); padding: 0.9rem; position: sticky; top: 1rem; }
	.side ul { list-style: none; margin: 0; padding: 0; display: flex; flex-direction: column; gap: 0.4rem; }
	.side li { display: flex; align-items: center; gap: 0.5rem; font-size: 0.78rem; }
	.pname { color: var(--cv-fg); }
	.pstate { margin-left: auto; font-size: 0.68rem; color: var(--cv-fg-faint); letter-spacing: 0.06em; }
	.dot { width: 8px; height: 8px; background: var(--cv-line-hi); flex-shrink: 0; }
	.dot.picked { background: var(--cv-accent); }
	.dot.voted { background: var(--cv-ok); }
	.counter { margin-top: 0.7rem; padding-top: 0.6rem; border-top: 1px solid var(--cv-line); }

	/* --- coin ---------------------------------------------------------- */
	.coin-section { text-align: center; margin: 0.5rem 0 2rem; }
	.coin-stage { perspective: 800px; margin: 0 auto 1.5rem; width: 160px; height: 160px; }
	.coin { width: 160px; height: 160px; position: relative; transform-style: preserve-3d; }
	.coin-face {
		position: absolute; inset: 0; overflow: hidden; backface-visibility: hidden;
		border: 2px solid var(--cv-accent); background: var(--cv-surface);
	}
	.coin-face img { width: 100%; height: 100%; object-fit: cover; }
	.coin-face.back { transform: rotateY(180deg); }

	/* --- results -------------------------------------------------------- */
	.results { margin-top: 2.5rem; border-top: 1px solid var(--cv-line); padding-top: 1.5rem; }
	.reel-wrap { position: relative; text-align: center; margin: 1rem 0; min-height: 300px; display: flex; align-items: center; justify-content: center; }
	.confetti { position: absolute; inset: 0; width: 100%; height: 100%; pointer-events: none; z-index: 5; }
	.reel { display: inline-flex; flex-direction: column; align-items: center; gap: 0.6rem; }
	.reel img { width: 190px; aspect-ratio: 2/3; object-fit: cover; border: 1px solid var(--cv-warn); }
	.reel.spin img { filter: blur(1px) brightness(0.85); border-color: var(--cv-line-hi); }
	.reel-cap { font-size: 0.85rem; color: var(--cv-fg); }
	.winner-tag {
		position: absolute; top: 0; font-size: 0.78rem; letter-spacing: 0.22em;
		color: var(--cv-warn); text-transform: uppercase;
	}

	.ranking { width: 100%; border-collapse: collapse; margin-top: 1.25rem; font-size: 0.8rem; }
	.ranking td { padding: 0.4rem 0.6rem; border-bottom: 1px solid var(--cv-line); }
	.ranking .rank { color: var(--cv-fg-faint); width: 2.5rem; font-variant-numeric: tabular-nums; }
	.ranking .pts { text-align: right; color: var(--cv-fg-dim); white-space: nowrap; font-variant-numeric: tabular-nums; }
	.ranking tr.win td { color: var(--cv-warn); background: color-mix(in srgb, var(--cv-warn) 8%, transparent); }

	/* --- info modal ------------------------------------------------------ */
	.modal-back {
		position: fixed; inset: 0; background: rgba(0, 0, 0, 0.72);
		display: flex; align-items: center; justify-content: center; padding: 1rem; z-index: 50;
	}
	.modal {
		background: var(--cv-surface); border: 1px solid var(--cv-line-hi);
		max-width: 660px; width: 100%; max-height: 88vh; overflow-y: auto;
		padding: 1.5rem; position: relative; color: var(--cv-fg);
		font-family: 'JetBrains Mono Variable', 'JetBrains Mono', 'IBM Plex Mono', 'SFMono-Regular', Consolas, monospace;
		font-size: 0.82rem; line-height: 1.55;
	}
	.modal .dim { color: var(--cv-fg-dim); }
	.modal-x {
		position: absolute; top: 0; right: 0; background: var(--cv-inset);
		border: none; border-left: 1px solid var(--cv-line); border-bottom: 1px solid var(--cv-line);
		color: var(--cv-fg-dim); width: 28px; height: 28px;
	}
	.modal-x:hover { color: var(--cv-err); }
	.modal-head { display: flex; gap: 1.1rem; margin-bottom: 1rem; }
	.modal-poster { width: 115px; aspect-ratio: 2/3; object-fit: cover; flex-shrink: 0; border: 1px solid var(--cv-line); }
	.rating { color: var(--cv-warn); font-weight: 700; margin-bottom: 0.35rem; }
	.meta { margin: 0.15rem 0; }
	.imdb-link { color: var(--cv-accent); font-size: 0.78rem; text-decoration: none; }
	.imdb-link:hover { text-decoration: underline; }
	.overview { color: var(--cv-fg-dim); }
	.cast { display: grid; grid-template-columns: repeat(4, 1fr); gap: 0.7rem; margin-top: 1.1rem; }
	.actor { text-align: center; }
	.actor img, .noface { width: 100%; aspect-ratio: 1; object-fit: cover; border: 1px solid var(--cv-line); }
	.noface { display: flex; align-items: center; justify-content: center; background: var(--cv-inset); color: var(--cv-fg-faint); }
	.actor-name { font-size: 0.72rem; margin-top: 0.3rem; }
	.actor-char { font-size: 0.68rem; }

	@media (max-width: 760px) {
		.layout { grid-template-columns: 1fr; }
		.side { position: static; order: -1; }
		.cast { grid-template-columns: repeat(3, 1fr); }
		.modal-head { flex-direction: column; }
		.stage-meta { margin-left: 0; width: 100%; }
		.stage-title { font-size: 1.2rem; }
		.cv-head { gap: 0.75rem; }
	}
</style>
