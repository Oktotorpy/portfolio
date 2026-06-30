<script>
	import { onMount } from 'svelte';
	import { cinevote } from '$lib/cinevote.js';

	let events = [];
	let history = [];
	let message = '';
	let messageType = '';
	let newName = '';
	let newDate = '';
	let expanded = null; // event id whose picks are shown
	let picks = [];

	onMount(load);

	async function load() {
		try {
			events = await cinevote.adminEvents();
			history = await cinevote.history();
		} catch (e) {
			flash(e.message, 'error');
		}
	}
	function flash(m, t) {
		message = m;
		messageType = t;
		setTimeout(() => (message = ''), 4000);
	}

	async function create() {
		if (!newDate) return flash('Pick a date', 'error');
		try {
			await cinevote.adminCreate({ name: newName, event_date: newDate });
			newName = '';
			newDate = '';
			await load();
			flash('Event created', 'success');
		} catch (e) {
			flash(e.message, 'error');
		}
	}
	async function saveDate(ev) {
		try {
			await cinevote.adminUpdate(ev.id, { name: ev.name, event_date: ev.event_date });
			await load();
			flash('Updated', 'success');
		} catch (e) {
			flash(e.message, 'error');
		}
	}
	async function startVoting(ev) {
		try {
			await cinevote.adminStartVoting(ev.id);
			await load();
			flash('Voting opened', 'success');
		} catch (e) {
			flash(e.message, 'error');
		}
	}
	async function conclude(ev) {
		if (!confirm('Conclude voting now with the current tally?')) return;
		try {
			await cinevote.adminConclude(ev.id);
			await load();
			flash('Concluded', 'success');
		} catch (e) {
			flash(e.message, 'error');
		}
	}
	async function del(ev) {
		if (!confirm(`Delete event "${ev.name || ev.event_date}"? This removes its picks and votes.`)) return;
		try {
			await cinevote.adminDelete(ev.id);
			await load();
			flash('Deleted', 'success');
		} catch (e) {
			flash(e.message, 'error');
		}
	}
	async function managePicks(ev) {
		if (expanded === ev.id) {
			expanded = null;
			return;
		}
		expanded = ev.id;
		picks = await cinevote.adminEventPicks(ev.id);
	}
	async function removePick(p) {
		if (!confirm(`Remove ${p.owner_name}'s pick "${p.title}"?`)) return;
		try {
			await cinevote.adminDeletePick(p.id);
			picks = await cinevote.adminEventPicks(expanded);
			await load();
		} catch (e) {
			flash(e.message, 'error');
		}
	}
</script>

<h1>CineVote — Events</h1>

{#if message}<div class="msg msg-{messageType}">{message}</div>{/if}

<div class="card">
	<h2>New event</h2>
	<form on:submit|preventDefault={create} class="row">
		<div class="form-group">
			<label>Name (optional)</label>
			<input bind:value={newName} placeholder="Friday Movie Night" />
		</div>
		<div class="form-group">
			<label>Date</label>
			<input type="date" bind:value={newDate} />
		</div>
		<button class="btn btn-primary">Add event</button>
	</form>
</div>

<div class="card">
	<h2>Events</h2>
	{#if !events.length}
		<p style="color: var(--text-dim);">No events yet.</p>
	{:else}
		<table>
			<thead>
				<tr><th>Date</th><th>Name</th><th>Status</th><th>Picks</th><th></th></tr>
			</thead>
			<tbody>
				{#each events as ev (ev.id)}
					<tr>
						<td><input type="date" bind:value={ev.event_date} on:change={() => saveDate(ev)} /></td>
						<td><input bind:value={ev.name} on:blur={() => saveDate(ev)} placeholder="—" /></td>
						<td>
							<span class="badge badge-{ev.status}">{ev.status}</span>
							{#if ev.is_live}<span class="badge live">LIVE</span>{/if}
						</td>
						<td>{ev.picks}</td>
						<td class="actions">
							{#if ev.status === 'picking'}
								<button class="btn btn-sm btn-primary" on:click={() => startVoting(ev)} title="All people picked → open voting">All picked → Vote</button>
							{:else if ev.status === 'voting' || ev.status === 'runoff'}
								<button class="btn btn-sm" on:click={() => conclude(ev)}>Conclude</button>
							{/if}
							<button class="btn btn-sm" on:click={() => managePicks(ev)}>Picks</button>
							<button class="btn btn-sm btn-danger" on:click={() => del(ev)}>Delete</button>
						</td>
					</tr>
					{#if expanded === ev.id}
						<tr>
							<td colspan="5" class="picks-cell">
								{#if picks.length}
									<div class="pick-chips">
										{#each picks as p (p.id)}
											<span class="chip">
												{p.title} <em>· {p.owner_name}</em>
												<button class="x" on:click={() => removePick(p)} title="Remove this pick">✕</button>
											</span>
										{/each}
									</div>
								{:else}
									<span style="color: var(--text-dim);">No picks.</span>
								{/if}
							</td>
						</tr>
					{/if}
				{/each}
			</tbody>
		</table>
		<p style="color: var(--text-dim); font-size: 0.8rem; margin-top: 0.75rem;">
			The earliest non-concluded event is LIVE on /cinevote. Change a date to reorder.
		</p>
	{/if}
</div>

<div class="card">
	<h2>History</h2>
	{#if !history.length}
		<p style="color: var(--text-dim);">No concluded events yet.</p>
	{:else}
		{#each history as h (h.event.id)}
			<div class="hist">
				<div class="hist-head">
					<strong>{h.event.name || 'Movie Night'}</strong>
					<span style="color: var(--text-dim);">{h.event.event_date}</span>
				</div>
				<table class="hist-table">
					<tbody>
						{#each h.picks as p (p.title + p.owner_name)}
							<tr class:win={p.is_winner}>
								<td>{p.is_winner ? '🏆' : ''}</td>
								<td>{p.title} {#if p.year}<span style="color:var(--text-dim)">({p.year})</span>{/if}</td>
								<td style="color: var(--text-dim);">{p.owner_name}</td>
								<td style="text-align:right;">{p.points} pt{p.points === 1 ? '' : 's'}</td>
							</tr>
						{/each}
					</tbody>
				</table>
			</div>
		{/each}
	{/if}
</div>

<style>
	.row { display: flex; gap: 1rem; align-items: flex-end; flex-wrap: wrap; }
	table { width: 100%; border-collapse: collapse; }
	th { text-align: left; color: var(--text-dim); font-size: 0.8rem; padding: 0.4rem 0.5rem; border-bottom: 1px solid var(--border); }
	td { padding: 0.4rem 0.5rem; border-bottom: 1px solid var(--border); vertical-align: middle; }
	td input { width: 100%; min-width: 90px; }
	.actions { display: flex; gap: 0.35rem; flex-wrap: wrap; justify-content: flex-end; }
	.btn-sm { padding: 0.3rem 0.55rem; font-size: 0.8rem; }
	.btn-danger { background: var(--danger); color: #fff; border: none; }
	.btn-danger:hover { background: var(--danger-hover); }
	.badge { display: inline-block; padding: 0.15rem 0.5rem; border-radius: 999px; font-size: 0.72rem; }
	.badge-picking { background: var(--tag-new-bg); color: var(--tag-new-text); }
	.badge-voting { background: var(--tag-current-bg); color: var(--tag-current-text); }
	.badge-runoff { background: var(--tag-promo-bg); color: var(--tag-promo-text); }
	.badge-concluded { background: var(--bg-hover); color: var(--text-dim); }
	.badge.live { background: var(--success); color: #fff; margin-left: 0.3rem; }
	.picks-cell { background: var(--bg-inset); }
	.pick-chips { display: flex; flex-wrap: wrap; gap: 0.5rem; }
	.chip { background: var(--bg-card); border: 1px solid var(--border); border-radius: 999px; padding: 0.25rem 0.6rem; font-size: 0.85rem; }
	.chip em { color: var(--text-dim); font-style: normal; }
	.chip .x { background: none; border: none; color: var(--danger); cursor: pointer; margin-left: 0.3rem; }
	.hist { margin-bottom: 1.25rem; }
	.hist-head { display: flex; justify-content: space-between; margin-bottom: 0.4rem; }
	.hist-table tr.win td { color: var(--star-color); font-weight: 600; }
	h2 { font-size: 1.05rem; color: var(--text-heading); margin: 0 0 0.75rem; }
</style>
