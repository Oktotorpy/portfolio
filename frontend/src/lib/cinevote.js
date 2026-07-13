// CineVote API client (cookie-based auth, same-origin).
async function req(method, path, body) {
	const opts = { method, headers: {}, credentials: 'include' };
	if (body) {
		opts.headers['Content-Type'] = 'application/json';
		opts.body = JSON.stringify(body);
	}
	const res = await fetch(`/api/cinevote${path}`, opts);
	const data = await res.json().catch(() => ({}));
	if (!res.ok) throw new Error(data.error || `Request failed (${res.status})`);
	return data;
}

export const cinevote = {
	me: () => req('GET', '/me'),
	register: (username, password) => req('POST', '/register', { username, password }),
	login: (username, password) => req('POST', '/login', { username, password }),
	logout: () => req('POST', '/logout'),

	search: (q) => req('GET', `/search?q=${encodeURIComponent(q)}`),
	movie: (tmdbId) => req('GET', `/movie/${tmdbId}`),
	flipCoin: () => req('POST', '/flip-coin'),

	event: () => req('GET', '/event'),
	createEvent: (data) => req('POST', '/events', data),
	addPick: (movie) => req('POST', '/pick', movie),
	deletePick: () => req('DELETE', '/pick'),
	toggleWatched: (pick_id) => req('POST', '/watched', { pick_id }),
	vote: (pick_id) => req('POST', '/vote', { pick_id }),
	startVoting: () => req('POST', '/start-voting'),
	revert: () => req('POST', '/revert'),
	history: () => req('GET', '/history'),

	// admin (CMS-auth)
	adminEvents: () => req('GET', '/admin/events'),
	adminCreate: (data) => req('POST', '/admin/events', data),
	adminUpdate: (id, data) => req('PUT', `/admin/events/${id}`, data),
	adminDelete: (id) => req('DELETE', `/admin/events/${id}`),
	adminEventPicks: (id) => req('GET', `/admin/events/${id}/picks`),
	adminStartVoting: (id) => req('POST', `/admin/events/${id}/start-voting`),
	adminConclude: (id) => req('POST', `/admin/events/${id}/conclude`),
	adminDeletePick: (pickId) => req('DELETE', `/admin/picks/${pickId}`)
};

export function imdbUrl(pick) {
	if (pick.imdb_id) return `https://www.imdb.com/title/${pick.imdb_id}/`;
	if (pick.tmdb_id) return `https://www.themoviedb.org/movie/${pick.tmdb_id}`;
	return '#';
}
