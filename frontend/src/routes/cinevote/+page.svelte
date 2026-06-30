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

	// create event (when none is live)
	let newName = '';
	let newDate = '';

	// reveal
	let revealing = false;
	let reelActive = false;
	let reelIndex = 0;
	let confettiCanvas;
	let poll;

	$: phase = state?.event ? state.phase : null;
	$: picks = state?.picks ?? [];
	$: myPick = picks.find((p) => p.is_mine);
	$: myVotes = state?.my_vote_pick_ids ?? [];
	$: myVoteMax = state?.my_vote_max ?? 0;
	$: winnerPick = state?.results ? picks.find((p) => p.id === state.results.winner_pick_id) : null;

	onMount(async () => {
		try {
			me = await cinevote.me();
		} catch {}
		if (me) await loadEvent();
		loading = false;
		poll = setInterval(() => {
			if (me && !revealing && document.visibilityState === 'visible') loadEvent();
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
			me =
				authMode === 'login'
					? await cinevote.login(authUser, authPass)
					: await cinevote.register(authUser, authPass);
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
		if (!term) {
			results = [];
			return;
		}
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
			if (step > spins - picks.length * 1.5) delay += 38; // decelerate — slower, dramatic tail
		}
		reelIndex = winIdx;
		reelActive = false;
		fireConfetti();
	}

	function fireConfetti() {
		const canvas = confettiCanvas;
		if (!canvas) return;
		const ctx = canvas.getContext('2d');
		canvas.width = canvas.offsetWidth;
		canvas.height = canvas.offsetHeight;
		const colors = ['#5b6abf', '#d4af37', '#3daa6d', '#e66060', '#6e7dd4', '#f0d060'];
		const parts = Array.from({ length: 140 }, () => ({
			x: canvas.width / 2,
			y: canvas.height / 3,
			vx: (Math.cos(Math.random() * Math.PI * 2)) * (3 + Math.random() * 7),
			vy: -6 - Math.random() * 8,
			s: 4 + Math.random() * 6,
			c: colors[(Math.random() * colors.length) | 0],
			rot: Math.random() * Math.PI,
			vr: (Math.random() - 0.5) * 0.3,
			life: 1
		}));
		let raf;
		const start = performance.now();
		function frame(now) {
			const t = now - start;
			ctx.clearRect(0, 0, canvas.width, canvas.height);
			for (const p of parts) {
				p.vy += 0.22;
				p.x += p.vx;
				p.y += p.vy;
				p.rot += p.vr;
				p.life = Math.max(0, 1 - t / 2600);
				ctx.save();
				ctx.globalAlpha = p.life;
				ctx.translate(p.x, p.y);
				ctx.rotate(p.rot);
				ctx.fillStyle = p.c;
				ctx.fillRect(-p.s / 2, -p.s / 2, p.s, p.s * 1.6);
				ctx.restore();
			}
			if (t < 2600) raf = requestAnimationFrame(frame);
			else ctx.clearRect(0, 0, canvas.width, canvas.height);
		}
		raf = requestAnimationFrame(frame);
	}

	// mobile: reveal controls on the poster nearest screen-center
	let gridEl;
	function observeCenter(node) {
		if (typeof window === 'undefined' || !window.matchMedia('(hover: none)').matches) return;
		const io = new IntersectionObserver(
			(entries) => {
				for (const e of entries) e.target.classList.toggle('centered', e.isIntersecting);
			},
			{ root: null, rootMargin: '-45% 0px -45% 0px', threshold: 0 }
		);
		for (const card of node.querySelectorAll('.poster')) io.observe(card);
		return { destroy: () => io.disconnect() };
	}
</script>

<svelte:head><title>CineVote</title></svelte:head>

<div class="cv">
	<header class="cv-head">
		<a class="brand" href="/cinevote">🎬 CineVote</a>
		{#if me}
			<div class="who">
				<span>{me.username}</span>
				<button class="ghost" on:click={doLogout}>Log out</button>
			</div>
		{/if}
	</header>

	{#if loading}
		<p class="dim center">Loading…</p>
	{:else if !me}
		<!-- AUTH -->
		<div class="auth">
			<h1>{authMode === 'login' ? 'Log in' : 'Create account'}</h1>
			{#if authError}<div class="err">{authError}</div>{/if}
			<form on:submit|preventDefault={doAuth}>
				<input placeholder="Username" bind:value={authUser} autocomplete="username" />
				<input
					type="password"
					placeholder="Password"
					bind:value={authPass}
					autocomplete={authMode === 'login' ? 'current-password' : 'new-password'}
				/>
				<button class="primary" disabled={authBusy}>
					{authBusy ? '…' : authMode === 'login' ? 'Log in' : 'Register'}
				</button>
			</form>
			<p class="dim">
				{authMode === 'login' ? 'No account?' : 'Have an account?'}
				<button class="link" on:click={() => (authMode = authMode === 'login' ? 'register' : 'login')}>
					{authMode === 'login' ? 'Register' : 'Log in'}
				</button>
			</p>
		</div>
	{:else if !state?.event}
		<div class="auth">
			<h1>Start a movie night</h1>
			<p class="dim">No event scheduled — create one:</p>
			{#if error}<div class="err">{error}</div>{/if}
			<form on:submit|preventDefault={createEvent}>
				<input placeholder="Name (optional)" bind:value={newName} />
				<input type="date" bind:value={newDate} />
				<button class="primary" disabled={busy || !newDate}>
					{busy ? '…' : 'Create movie night'}
				</button>
			</form>
		</div>
	{:else}
		<!-- EVENT -->
		<div class="event-bar">
			<div>
				<h1>{state.event.name || 'Movie Night'}</h1>
				<p class="dim">{state.event.event_date}</p>
			</div>
			<div class="event-actions">
				<span class="phase phase-{phase}">
					{phase === 'picking' ? 'Picking' : phase === 'voting' ? 'Voting' : phase === 'runoff' ? 'Runoff' : 'Concluded'}
				</span>
				{#if phase === 'picking'}
					<button class="primary sm" on:click={startVoting} disabled={busy || picks.length < 2} title={picks.length < 2 ? 'Need at least 2 picks' : 'Open voting'}>
						All movies picked →
					</button>
				{:else if phase === 'voting'}
					<button class="ghost sm" on:click={revert} disabled={busy} title="Someone wants in? Go back to picking (keeps picks & votes)">
						↩ Revert to picking
					</button>
				{/if}
			</div>
		</div>

		{#if error}<div class="err">{error}</div>{/if}

		<div class="layout">
			<main>
				{#if phase === 'voting' || phase === 'runoff'}
					<p class="vote-hint">
						{phase === 'runoff' ? '🥊 Runoff — pick the winner' : `Pick ${myVoteMax} movie${myVoteMax === 1 ? '' : 's'} to watch`}
						<span class="count">· {myVotes.length}/{myVoteMax} chosen</span>
					</p>
				{/if}

				<!-- SEARCH (picking only) -->
				{#if phase === 'picking'}
					<div class="search" class:greyed={!!myPick}>
						<input
							placeholder={myPick ? 'You already picked — delete it to choose another' : 'Search a movie…'}
							bind:value={q}
							on:input={onSearchInput}
							disabled={!!myPick || busy}
						/>
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
					<div class="grid" bind:this={gridEl} use:observeCenter>
						{#each picks as p (p.id)}
							<div class="poster" class:winner={winnerPick && p.id === winnerPick.id} class:dim-out={phase === 'runoff' && !p.in_runoff}>
								<a class="poster-link" href={imdbUrl(p)} target="_blank" rel="noopener">
									{#if p.poster_url}
										<img src={p.poster_url} alt={p.title} loading="lazy" />
									{:else}
										<div class="noposter">{p.title}</div>
									{/if}
								</a>

								<!-- top-left delete (own pick, picking) -->
								{#if p.is_mine && phase === 'picking'}
									<button class="corner del" on:click={removePick} title="Remove your pick" disabled={busy}>✕</button>
								{/if}
								{#if p.watched_by_me}<span class="watched-badge" title="You've watched this">👁</span>{/if}

								<span class="cap">
									{p.title}{#if p.year} <em>({p.year})</em>{/if}
									<small class="dim">· {p.owner_name}</small>
								</span>

								<!-- hover / mobile-center controls -->
								<div class="controls">
									{#if (phase === 'voting' || phase === 'runoff') && !p.is_mine && (phase !== 'runoff' || p.in_runoff)}
										<button
											class="ctl vote"
											class:active={myVotes.includes(p.id)}
											on:click={() => castVote(p)}
											disabled={busy || (!myVotes.includes(p.id) && myVotes.length >= myVoteMax)}
											title={p.watched_by_me ? 'Vote (1 pt — you watched it)' : 'Vote (2 pts — unseen)'}
										>{myVotes.includes(p.id) ? '✓ Picked' : 'Vote'}</button>
									{/if}
									<button
										class="ctl watch"
										class:active={p.watched_by_me}
										on:click={() => toggleWatched(p)}
										title="Mark watched"
									>👁 Watched</button>
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

			<!-- RIGHT PANEL: participants -->
			<aside class="panel">
				<h3>Who picked</h3>
				{#if state.participants.length}
					<ul>
						{#each state.participants as part (part.user_id)}
							<li>
								{#if phase === 'voting' || phase === 'runoff'}
									<span class="dot" class:voted={part.has_voted} title={part.has_voted ? 'Voted' : 'Not yet'}></span>
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

<style>
	.cv { max-width: 1100px; margin: 0 auto; padding: 1.25rem 1rem 4rem; color: var(--text); }
	.cv-head { display: flex; justify-content: space-between; align-items: center; margin-bottom: 1.5rem; }
	.brand { font-size: 1.4rem; font-weight: 700; color: var(--text-heading); text-decoration: none; }
	.who { display: flex; gap: 0.75rem; align-items: center; color: var(--text-dim); }
	.center { text-align: center; margin-top: 3rem; }
	.dim { color: var(--text-dim); }
	.sm { font-size: 0.8rem; }
	h1 { color: var(--text-heading); margin: 0 0 0.25rem; font-size: 1.5rem; }
	h3 { color: var(--text-heading); margin: 0 0 0.75rem; font-size: 1rem; }

	.err { background: rgba(217, 79, 79, 0.12); border: 1px solid var(--danger); color: #f0b4b4; padding: 0.6rem 0.8rem; border-radius: var(--radius-sm); margin: 0.75rem 0; }

	input { width: 100%; padding: 0.6rem 0.8rem; background: var(--bg-input); border: 1px solid var(--border); border-radius: var(--radius-sm); color: var(--text); font-size: 0.95rem; }
	input:focus { outline: none; border-color: var(--border-focus); }

	button { cursor: pointer; font: inherit; }
	.primary { background: var(--accent); color: #fff; border: none; padding: 0.6rem 1rem; border-radius: var(--radius-sm); font-weight: 600; }
	.primary:hover { background: var(--accent-hover); }
	.primary.big { font-size: 1.1rem; padding: 0.8rem 1.6rem; }
	.ghost { background: transparent; border: 1px solid var(--border); color: var(--text-dim); padding: 0.4rem 0.8rem; border-radius: var(--radius-sm); }
	.ghost:hover { background: var(--bg-hover); color: var(--text); }
	.link { background: none; border: none; color: var(--accent-soft); text-decoration: underline; padding: 0; }

	.auth { max-width: 340px; margin: 3rem auto; background: var(--bg-card); border: 1px solid var(--border); border-radius: var(--radius); padding: 1.5rem; }
	.auth form { display: flex; flex-direction: column; gap: 0.7rem; margin: 1rem 0; }

	.event-bar { display: flex; justify-content: space-between; align-items: flex-start; border-bottom: 1px solid var(--border); padding-bottom: 1rem; margin-bottom: 1rem; gap: 1rem; }
	.event-actions { display: flex; flex-direction: column; align-items: flex-end; gap: 0.5rem; }
	.primary.sm, .ghost.sm { padding: 0.4rem 0.8rem; font-size: 0.85rem; }
	.phase { padding: 0.3rem 0.7rem; border-radius: 999px; font-size: 0.8rem; font-weight: 600; }
	.phase-picking { background: var(--tag-new-bg); color: var(--tag-new-text); }
	.phase-voting { background: var(--tag-current-bg); color: var(--tag-current-text); }
	.phase-runoff { background: var(--tag-promo-bg); color: var(--tag-promo-text); }
	.phase-concluded { background: var(--bg-hover); color: var(--text-dim); }

	.layout { display: grid; grid-template-columns: 1fr 220px; gap: 1.5rem; align-items: start; }

	.vote-hint { background: var(--bg-card); border: 1px solid var(--border); border-radius: var(--radius-sm); padding: 0.6rem 0.9rem; margin-bottom: 1rem; font-weight: 600; color: var(--text-heading); }
	.vote-hint .count { color: var(--text-dim); font-weight: 400; }

	.search { display: flex; align-items: center; gap: 0.6rem; margin-bottom: 1rem; }
	.search.greyed input { opacity: 0.55; }

	.grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(140px, 1fr)); gap: 1rem; }
	.results { margin-bottom: 1rem; }
	hr { border: none; border-top: 1px solid var(--border); margin: 1.25rem 0; }

	.poster { position: relative; background: var(--bg-card); border: 1px solid var(--border); border-radius: var(--radius); overflow: hidden; display: flex; flex-direction: column; transition: transform 0.12s, border-color 0.12s; }
	.poster:hover { border-color: var(--border-focus); }
	.poster.winner { border-color: var(--star-color); box-shadow: 0 0 0 2px var(--star-glow); }
	.poster.dim-out { opacity: 0.4; }
	.poster img { width: 100%; aspect-ratio: 2/3; object-fit: cover; display: block; }
	.poster-link { display: block; }
	.noposter { aspect-ratio: 2/3; display: flex; align-items: center; justify-content: center; text-align: center; padding: 0.5rem; color: var(--text-dim); }
	.cap { padding: 0.5rem 0.6rem; font-size: 0.85rem; line-height: 1.25; }
	.cap em { color: var(--text-dim); font-style: normal; }
	.pick-result { padding: 0; border: 1px solid var(--border); text-align: left; color: var(--text); }
	.pick-result:hover { border-color: var(--accent); }

	.corner { position: absolute; top: 6px; left: 6px; width: 26px; height: 26px; border-radius: 50%; border: none; display: flex; align-items: center; justify-content: center; font-size: 0.85rem; z-index: 3; }
	.del { background: var(--danger); color: #fff; }
	.del:hover { background: var(--danger-hover); }
	.watched-badge { position: absolute; top: 6px; right: 6px; font-size: 0.9rem; z-index: 3; filter: drop-shadow(0 1px 2px #000); }

	.controls { position: absolute; left: 0; right: 0; bottom: 0; display: flex; gap: 0.4rem; padding: 0.5rem; background: linear-gradient(transparent, rgba(0,0,0,0.85)); opacity: 0; transition: opacity 0.15s; }
	.poster:hover .controls, .poster.centered .controls { opacity: 1; }
	.ctl { flex: 1; border: 1px solid rgba(255,255,255,0.25); background: rgba(0,0,0,0.5); color: #fff; padding: 0.35rem; border-radius: var(--radius-sm); font-size: 0.78rem; }
	.ctl.vote.active { background: var(--success); border-color: var(--success); }
	.ctl.watch.active { background: var(--accent); border-color: var(--accent); }

	.panel { background: var(--bg-card); border: 1px solid var(--border); border-radius: var(--radius); padding: 1rem; position: sticky; top: 1rem; }
	.panel ul { list-style: none; margin: 0; padding: 0; display: flex; flex-direction: column; gap: 0.5rem; }
	.panel li { display: flex; align-items: center; gap: 0.55rem; font-size: 0.9rem; }
	.dot { width: 11px; height: 11px; border-radius: 50%; background: var(--border-strong); flex-shrink: 0; }
	.dot.picked { background: var(--accent-soft); }
	.dot.voted { background: var(--success); box-shadow: 0 0 6px var(--success); }

	.results { margin-top: 2rem; }
	.reel-wrap { position: relative; text-align: center; margin: 1.5rem 0; min-height: 300px; display: flex; align-items: center; justify-content: center; }
	.confetti { position: absolute; inset: 0; width: 100%; height: 100%; pointer-events: none; z-index: 5; }
	.reel { display: inline-flex; flex-direction: column; align-items: center; gap: 0.5rem; }
	.reel img { width: 180px; aspect-ratio: 2/3; object-fit: cover; border-radius: var(--radius); border: 2px solid var(--star-color); box-shadow: 0 0 18px var(--star-glow); }
	.reel.spin img { filter: blur(1px) brightness(0.85); border-color: var(--accent); box-shadow: none; }
	.reel-cap { font-weight: 600; color: var(--text-heading); }
	.winner-tag { position: absolute; top: 0; font-size: 1.3rem; font-weight: 700; color: var(--star-color); }

	.ranking { width: 100%; border-collapse: collapse; margin-top: 1rem; }
	.ranking td { padding: 0.5rem 0.6rem; border-bottom: 1px solid var(--border); }
	.ranking .rank { color: var(--text-dim); width: 2rem; }
	.ranking .pts { text-align: right; color: var(--text-dim); white-space: nowrap; }
	.ranking tr.win td { color: var(--star-color); font-weight: 600; }

	@media (max-width: 760px) {
		.layout { grid-template-columns: 1fr; }
		.panel { position: static; order: -1; }
	}
</style>
