<script>
	import { onMount, onDestroy } from 'svelte';
	import { cinevote, imdbUrl } from '$lib/cinevote.js';

	let me = null;
	let state = null;
	let loading = true;
	let error = '';

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

	// create event
	let newName = '';
	let newDate = '';

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

	onMount(async () => {
		try {
			me = await cinevote.me();
		} catch {}
		if (me) await loadEvent();
		loading = false;
		poll = setInterval(() => {
			if (me && !revealing && !coinFlipping && !busy && document.visibilityState === 'visible') loadEvent();
		}, 4000);
	});
	onDestroy(() => clearInterval(poll));

	async function loadEvent() {
		try {
			state = await cinevote.event();
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
	async function startVoting() {
		busy = true;
		error = '';
		try {
			state = await cinevote.startVoting();
		} catch (e) {
			error = e.message;
		} finally {
			busy = false;
		}
	}
	async function revert() {
		busy = true;
		error = '';
		try {
			state = await cinevote.revert();
		} catch (e) {
			error = e.message;
		} finally {
			busy = false;
		}
	}
	async function createEvent() {
		if (!newDate) return;
		busy = true;
		error = '';
		try {
			state = await cinevote.createEvent({ name: newName, event_date: newDate });
			newName = '';
			newDate = '';
		} catch (e) {
			error = e.message;
		} finally {
			busy = false;
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
		const colors = ['#5b6abf', '#d4af37', '#3daa6d', '#e66060', '#6e7dd4', '#f0d060'];
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

	const RULES = {
		picking:
			'Pick a movie you want to watch — one each. Voting begins when everyone has picked and the "All movies picked" button is pressed.',
		voting:
			"Pick two movies. You can't vote for your own. Tap the eye for movies you've already seen — unseen movies are worth 2 points, seen movies 1 point.",
		runoff: "It's a tie! Vote again — only between the tied movies below.",
		coinflip: 'Still tied after the runoff. Flip a coin to decide.'
	};
</script>

<svelte:head><title>CineVote</title></svelte:head>

<div class="cv">
	<header class="cv-head">
		<a class="brand" href="/cinevote">🎬 CineVote</a>
		{#if me}
			<div class="who"><span>{me.username}</span><button class="ghost" on:click={doLogout}>Log out</button></div>
		{/if}
	</header>

	{#if loading}
		<p class="dim center">Loading…</p>
	{:else if !me}
		<div class="card-box">
			<h1>{authMode === 'login' ? 'Log in' : 'Create account'}</h1>
			{#if authError}<div class="err">{authError}</div>{/if}
			<form on:submit|preventDefault={doAuth}>
				<input placeholder="Username" bind:value={authUser} autocomplete="username" />
				<input type="password" placeholder="Password" bind:value={authPass} autocomplete={authMode === 'login' ? 'current-password' : 'new-password'} />
				<button class="primary" disabled={authBusy}>{authBusy ? '…' : authMode === 'login' ? 'Log in' : 'Register'}</button>
			</form>
			<p class="dim">
				{authMode === 'login' ? 'No account?' : 'Have an account?'}
				<button class="link" on:click={() => (authMode = authMode === 'login' ? 'register' : 'login')}>{authMode === 'login' ? 'Register' : 'Log in'}</button>
			</p>
		</div>
	{:else if !state?.event}
		<div class="card-box">
			<h1>Start a movie night</h1>
			<p class="dim">No event scheduled — create one:</p>
			{#if error}<div class="err">{error}</div>{/if}
			<form on:submit|preventDefault={createEvent}>
				<input placeholder="Name (optional)" bind:value={newName} />
				<input type="date" bind:value={newDate} />
				<button class="primary" disabled={busy || !newDate}>{busy ? '…' : 'Create movie night'}</button>
			</form>
		</div>
	{:else}
		<div class="event-bar">
			<div>
				<h1>{state.event.name || 'Movie Night'}</h1>
				<p class="dim">{state.event.event_date}</p>
			</div>
			<div class="event-actions">
				<span class="phase phase-{phase}">
					{phase === 'picking' ? 'Picking' : phase === 'voting' ? 'Voting' : phase === 'runoff' ? 'Runoff' : phase === 'coinflip' ? 'Coin flip' : 'Concluded'}
				</span>
				{#if phase === 'picking'}
					<button class="primary sm" on:click={startVoting} disabled={busy || picks.length < 2} title={picks.length < 2 ? 'Need at least 2 picks' : 'Open voting'}>All movies picked →</button>
				{:else if phase === 'voting'}
					<button class="ghost sm" on:click={revert} disabled={busy}>↩ Revert to picking</button>
				{:else if phase === 'runoff' || phase === 'concluded' || phase === 'coinflip'}
					<button class="ghost sm" on:click={revert} disabled={busy}>↩ Revert to voting</button>
				{/if}
			</div>
		</div>

		{#if error}<div class="err">{error}</div>{/if}

		<!-- per-phase rules -->
		{#if RULES[phase]}
			<div class="rules">{RULES[phase]}</div>
		{/if}

		<div class="layout">
			<main>
				<!-- tie-breaker banner -->
				{#if phase === 'runoff' || phase === 'coinflip'}
					<div class="tiebreaker">
						<div class="tb-title">TIE-BREAKER</div>
						<div class="tb-sub">Votes split evenly between those movies. {phase === 'runoff' ? 'Vote again to decide.' : ''}</div>
					</div>
				{/if}

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
							<button class="primary big" on:click={flipCoin} disabled={busy}>🪙 Flip a coin</button>
						{/if}
					</div>
				{/if}

				<!-- SEARCH (picking) -->
				{#if phase === 'picking'}
					<div class="search" class:greyed={!!myPick}>
						<input placeholder={myPick ? 'You already picked — delete it to choose another' : 'Search a movie…'} bind:value={q} on:input={onSearchInput} disabled={!!myPick || busy} />
						{#if searching}<span class="dim sm">searching…</span>{/if}
					</div>
					{#if results.length && !myPick}
						<div class="grid results">
							{#each results as m (m.tmdb_id)}
								<button class="poster pick-result" on:click={() => pickMovie(m)} disabled={busy} title="Pick this">
									<img src={m.poster_url} alt={m.title} loading="lazy" />
									<span class="cap">{m.title}{#if m.year} <em>({m.year})</em>{/if}</span>
								</button>
							{/each}
						</div>
						<hr />
					{/if}
				{/if}

				<!-- PICKS GRID -->
				{#if picks.length}
					<div class="grid" use:observeCenter>
						{#each picks as p (p.id)}
							<div class="poster" class:voted={myVotes.includes(p.id)} class:greyed={votingDone && !myVotes.includes(p.id)} class:winner={phase === 'concluded' && p.id === state.results?.winner_pick_id} class:dim-out={phase === 'runoff' && !p.in_runoff}>
								<div class="poster-img" on:click={() => posterClick(p)} on:keydown={(e) => e.key === 'Enter' && posterClick(p)} role="button" tabindex="0" title={votable(p) ? 'Click to vote' : 'Click for info'}>
									{#if p.poster_url}
										<img src={p.poster_url} alt={p.title} loading="lazy" />
									{:else}
										<div class="noposter">{p.title}</div>
									{/if}
									{#if p.is_mine && phase === 'picking'}
										<button class="corner del" on:click|stopPropagation={removePick} title="Remove your pick" disabled={busy}>✕</button>
									{/if}
									{#if myVotes.includes(p.id)}<span class="vote-flag">✓</span>{/if}
								</div>

								<div class="cap">
									{p.title}{#if p.year} <em>({p.year})</em>{/if}
									<small class="dim">· {p.owner_name}</small>
								</div>

								<div class="card-actions">
									<button class="act" on:click={() => openInfo(p)} title="Movie info">ℹ Info</button>
									<button class="act" class:active={p.watched_by_me} on:click={() => toggleWatched(p)} title="Mark as seen">👁 Seen</button>
								</div>
							</div>
						{/each}
					</div>
				{:else}
					<p class="dim">No picks yet{phase === 'picking' ? ' — be the first.' : '.'}</p>
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
								{#if !reelActive}<div class="winner-tag">🏆 Winner!</div>{/if}
							{:else}
								<button class="primary big" on:click={revealWinner}>🎰 Reveal the winner</button>
							{/if}
						</div>
						{#if revealing && !reelActive}
							<table class="ranking">
								<tbody>
									{#each state.results.ranking as r, i (r.pick_id)}
										<tr class:win={r.pick_id === state.results.winner_pick_id}>
											<td class="rank">{i + 1}</td>
											<td>{r.title}</td>
											<td class="pts">{r.points} pt{r.points === 1 ? '' : 's'}</td>
										</tr>
									{/each}
								</tbody>
							</table>
							{#if state.results.had_runoff}<p class="dim sm">Decided by runoff.</p>{/if}
						{/if}
					</section>
				{/if}
			</main>

			<aside class="panel">
				<h3>Who picked</h3>
				{#if state.participants.length}
					<ul>
						{#each state.participants as part (part.user_id)}
							<li>
								{#if phase === 'voting' || phase === 'runoff'}
									<span class="dot" class:voted={part.has_voted}></span>
								{:else}
									<span class="dot picked"></span>
								{/if}
								{part.username}
							</li>
						{/each}
					</ul>
					{#if phase === 'voting' || phase === 'runoff'}
						<p class="dim sm">{state.participants.filter((p) => p.has_voted).length}/{state.participants.length} voted</p>
					{/if}
				{:else}
					<p class="dim sm">Nobody yet.</p>
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
					<h2>{infoData?.title}{#if infoData?.year} <span class="dim">({infoData.year})</span>{/if}</h2>
					{#if infoData?.rating}<div class="rating">★ {infoData.rating}<span class="dim"> / 10</span></div>{/if}
					{#if infoData?.director}<p class="meta"><span class="dim">Director:</span> {infoData.director}</p>{/if}
					{#if infoData?.imdb_id}<a class="imdb-link" href={imdbUrl(infoData)} target="_blank" rel="noopener">View on IMDb ↗</a>{/if}
				</div>
			</div>
			{#if infoLoading}
				<p class="dim">Loading…</p>
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
	.cv {
		max-width: 1100px;
		margin: 0 auto;
		padding: 1.25rem 1rem 4rem;
		color: var(--text);
		font-family: 'Century Gothic', 'Futura', 'URW Gothic', 'Avant Garde', 'Trebuchet MS', sans-serif;
	}
	.cv-head { display: flex; justify-content: space-between; align-items: center; margin-bottom: 1.5rem; }
	.brand { font-size: 1.5rem; font-weight: 700; color: var(--text-heading); text-decoration: none; letter-spacing: 0.02em; }
	.who { display: flex; gap: 0.75rem; align-items: center; color: var(--text-dim); }
	.center { text-align: center; margin-top: 3rem; }
	.dim { color: var(--text-dim); }
	.sm { font-size: 0.8rem; }
	h1 { color: var(--text-heading); margin: 0 0 0.25rem; font-size: 1.6rem; }
	h3 { color: var(--text-heading); margin: 0 0 0.75rem; font-size: 1rem; }

	.err { background: rgba(217, 79, 79, 0.12); border: 1px solid var(--danger); color: #f0b4b4; padding: 0.6rem 0.8rem; border-radius: var(--radius-sm); margin: 0.75rem 0; }

	input { width: 100%; padding: 0.6rem 0.8rem; background: var(--bg-input); border: 1px solid var(--border); border-radius: var(--radius-sm); color: var(--text); font: inherit; }
	input:focus { outline: none; border-color: var(--border-focus); }

	button { cursor: pointer; font: inherit; }
	.primary { background: var(--accent); color: #fff; border: none; padding: 0.6rem 1rem; border-radius: var(--radius-sm); font-weight: 600; }
	.primary:hover { background: var(--accent-hover); }
	.primary:disabled { opacity: 0.5; cursor: default; }
	.primary.big { font-size: 1.15rem; padding: 0.85rem 1.7rem; }
	.primary.sm, .ghost.sm { padding: 0.4rem 0.8rem; font-size: 0.85rem; }
	.ghost { background: transparent; border: 1px solid var(--border); color: var(--text-dim); padding: 0.4rem 0.8rem; border-radius: var(--radius-sm); }
	.ghost:hover { background: var(--bg-hover); color: var(--text); }
	.link { background: none; border: none; color: var(--accent-soft); text-decoration: underline; padding: 0; }

	.card-box { max-width: 360px; margin: 3rem auto; background: var(--bg-card); border: 1px solid var(--border); border-radius: var(--radius); padding: 1.5rem; }
	.card-box form { display: flex; flex-direction: column; gap: 0.7rem; margin: 1rem 0; }

	.event-bar { display: flex; justify-content: space-between; align-items: flex-start; border-bottom: 1px solid var(--border); padding-bottom: 1rem; margin-bottom: 1rem; gap: 1rem; }
	.event-actions { display: flex; flex-direction: column; align-items: flex-end; gap: 0.5rem; }
	.phase { padding: 0.3rem 0.7rem; border-radius: 999px; font-size: 0.8rem; font-weight: 600; }
	.phase-picking { background: var(--tag-new-bg); color: var(--tag-new-text); }
	.phase-voting { background: var(--tag-current-bg); color: var(--tag-current-text); }
	.phase-runoff, .phase-coinflip { background: var(--tag-promo-bg); color: var(--tag-promo-text); }
	.phase-concluded { background: var(--bg-hover); color: var(--text-dim); }

	.rules { background: var(--bg-card); border: 1px solid var(--border); border-left: 3px solid var(--accent); border-radius: var(--radius-sm); padding: 0.7rem 1rem; margin-bottom: 1.25rem; color: var(--text-secondary); font-size: 0.92rem; line-height: 1.4; }

	.layout { display: grid; grid-template-columns: 1fr 220px; gap: 1.5rem; align-items: start; }

	.search { display: flex; align-items: center; gap: 0.6rem; margin-bottom: 1rem; }
	.search.greyed input { opacity: 0.55; }

	/* 4 per line on desktop, bigger posters */
	.grid { display: grid; grid-template-columns: repeat(2, 1fr); gap: 1.1rem; }
	@media (min-width: 640px) { .grid { grid-template-columns: repeat(3, 1fr); } }
	@media (min-width: 900px) { .grid { grid-template-columns: repeat(4, 1fr); } }
	.results { margin-bottom: 1rem; }
	hr { border: none; border-top: 1px solid var(--border); margin: 1.25rem 0; }

	.poster { position: relative; background: var(--bg-card); border: 1px solid var(--border); border-radius: var(--radius); overflow: hidden; display: flex; flex-direction: column; transition: transform 0.12s, border-color 0.12s, opacity 0.2s; }
	.poster.greyed { opacity: 0.32; filter: grayscale(0.6); }
	.poster.voted { border-color: var(--success); box-shadow: 0 0 0 2px rgba(61, 170, 109, 0.4); opacity: 1; filter: none; }
	.poster.winner { border-color: var(--star-color); box-shadow: 0 0 0 2px var(--star-glow); }
	.poster.dim-out { opacity: 0.35; }
	.poster-img { position: relative; cursor: pointer; }
	.poster-img img { width: 100%; aspect-ratio: 2/3; object-fit: cover; display: block; }
	.poster-img:hover img { filter: brightness(1.08); }
	.noposter { aspect-ratio: 2/3; display: flex; align-items: center; justify-content: center; text-align: center; padding: 0.5rem; color: var(--text-dim); }

	.cap { padding: 0.5rem 0.6rem 0.35rem; font-size: 0.9rem; line-height: 1.25; flex: 1; }
	.cap em { color: var(--text-dim); font-style: normal; }
	.pick-result { padding: 0; border: 1px solid var(--border); text-align: left; color: var(--text); background: var(--bg-card); }
	.pick-result:hover { border-color: var(--accent); }
	.pick-result .cap { padding: 0.5rem 0.6rem; }

	.card-actions { display: flex; border-top: 1px solid var(--border); }
	.act { flex: 1; background: transparent; border: none; color: var(--text-dim); padding: 0.5rem; font-size: 0.82rem; border-right: 1px solid var(--border); }
	.act:last-child { border-right: none; }
	.act:hover { background: var(--bg-hover); color: var(--text); }
	.act.active { color: var(--accent-soft); background: rgba(91, 106, 191, 0.12); }

	.corner { position: absolute; top: 8px; left: 8px; width: 28px; height: 28px; border-radius: 50%; border: none; display: flex; align-items: center; justify-content: center; font-size: 0.85rem; z-index: 3; background: var(--danger); color: #fff; box-shadow: 0 2px 8px rgba(0, 0, 0, 0.6), 0 0 0 2px rgba(0, 0, 0, 0.25); }
	.corner:hover { background: var(--danger-hover); }
	.vote-flag { position: absolute; top: 8px; right: 8px; width: 28px; height: 28px; border-radius: 50%; background: var(--success); color: #fff; display: flex; align-items: center; justify-content: center; font-weight: 700; z-index: 3; box-shadow: 0 2px 8px rgba(0, 0, 0, 0.5); }

	.panel { background: var(--bg-card); border: 1px solid var(--border); border-radius: var(--radius); padding: 1rem; position: sticky; top: 1rem; }
	.panel ul { list-style: none; margin: 0; padding: 0; display: flex; flex-direction: column; gap: 0.5rem; }
	.panel li { display: flex; align-items: center; gap: 0.55rem; font-size: 0.9rem; }
	.dot { width: 11px; height: 11px; border-radius: 50%; background: var(--border-strong); flex-shrink: 0; }
	.dot.picked { background: var(--accent-soft); }
	.dot.voted { background: var(--success); box-shadow: 0 0 6px var(--success); }

	/* tie-breaker */
	.tiebreaker { text-align: center; margin: 1rem 0 1.5rem; }
	.tb-title { font-size: 2.4rem; font-weight: 800; letter-spacing: 0.08em; color: var(--star-color); text-shadow: 0 0 20px var(--star-glow); }
	.tb-sub { color: var(--text-secondary); margin-top: 0.25rem; }

	/* coin */
	.coin-section { text-align: center; margin: 1rem 0 2rem; min-height: 60px; }
	.coin-stage { perspective: 800px; margin: 0 auto 1.5rem; width: 170px; height: 170px; }
	.coin { width: 170px; height: 170px; position: relative; transform-style: preserve-3d; }
	.coin-face { position: absolute; inset: 0; border-radius: 50%; overflow: hidden; backface-visibility: hidden; border: 5px solid var(--star-color); box-shadow: 0 0 25px var(--star-glow); background: var(--bg-card); }
	.coin-face img { width: 100%; height: 100%; object-fit: cover; }
	.coin-face.back { transform: rotateY(180deg); }

	.results { margin-top: 2rem; }
	.reel-wrap { position: relative; text-align: center; margin: 1.5rem 0; min-height: 320px; display: flex; align-items: center; justify-content: center; }
	.confetti { position: absolute; inset: 0; width: 100%; height: 100%; pointer-events: none; z-index: 5; }
	.reel { display: inline-flex; flex-direction: column; align-items: center; gap: 0.5rem; }
	.reel img { width: 200px; aspect-ratio: 2/3; object-fit: cover; border-radius: var(--radius); border: 2px solid var(--star-color); box-shadow: 0 0 18px var(--star-glow); }
	.reel.spin img { filter: blur(1px) brightness(0.85); border-color: var(--accent); box-shadow: none; }
	.reel-cap { font-weight: 600; color: var(--text-heading); }
	.winner-tag { position: absolute; top: 0; font-size: 1.4rem; font-weight: 700; color: var(--star-color); }

	.ranking { width: 100%; border-collapse: collapse; margin-top: 1rem; }
	.ranking td { padding: 0.5rem 0.6rem; border-bottom: 1px solid var(--border); }
	.ranking .rank { color: var(--text-dim); width: 2rem; }
	.ranking .pts { text-align: right; color: var(--text-dim); white-space: nowrap; }
	.ranking tr.win td { color: var(--star-color); font-weight: 600; }

	/* info modal */
	.modal-back { position: fixed; inset: 0; background: rgba(0, 0, 0, 0.7); display: flex; align-items: center; justify-content: center; padding: 1rem; z-index: 50; }
	.modal { background: var(--bg-card); border: 1px solid var(--border); border-radius: var(--radius); max-width: 640px; width: 100%; max-height: 88vh; overflow-y: auto; padding: 1.5rem; position: relative; font-family: 'Century Gothic', 'Futura', sans-serif; }
	.modal-x { position: absolute; top: 0.75rem; right: 0.75rem; background: var(--bg-hover); border: none; color: var(--text); width: 30px; height: 30px; border-radius: 50%; }
	.modal-head { display: flex; gap: 1rem; margin-bottom: 1rem; }
	.modal-poster { width: 120px; aspect-ratio: 2/3; object-fit: cover; border-radius: var(--radius-sm); flex-shrink: 0; }
	.modal h2 { color: var(--text-heading); margin: 0 0 0.4rem; font-size: 1.3rem; }
	.rating { color: var(--star-color); font-weight: 700; font-size: 1.1rem; margin-bottom: 0.4rem; }
	.meta { margin: 0.2rem 0; font-size: 0.9rem; }
	.imdb-link { color: var(--accent-soft); font-size: 0.85rem; text-decoration: none; }
	.imdb-link:hover { text-decoration: underline; }
	.overview { color: var(--text-secondary); line-height: 1.5; font-size: 0.92rem; }
	.cast { display: grid; grid-template-columns: repeat(4, 1fr); gap: 0.75rem; margin-top: 1rem; }
	.actor { text-align: center; }
	.actor img, .noface { width: 100%; aspect-ratio: 1; object-fit: cover; border-radius: var(--radius-sm); }
	.noface { display: flex; align-items: center; justify-content: center; background: var(--bg-input); color: var(--text-dim); font-size: 1.5rem; }
	.actor-name { font-size: 0.8rem; margin-top: 0.3rem; color: var(--text); }
	.actor-char { font-size: 0.72rem; }

	@media (max-width: 760px) {
		.layout { grid-template-columns: 1fr; }
		.panel { position: static; order: -1; }
		.cast { grid-template-columns: repeat(3, 1fr); }
		.modal-head { flex-direction: column; }
		.modal-poster { width: 100px; }
	}
</style>
