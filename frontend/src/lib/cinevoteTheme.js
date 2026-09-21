// CineVote theme: base mode (dark/light) + one of six accent colours.
// Both are set as attributes on <html> so the page CSS can resolve them, and
// both are remembered per browser. Only the CineVote pages set these, so the
// rest of the site is untouched.

export const MODES = ['dark', 'light'];

export const ACCENTS = ['amber', 'blue', 'green', 'magenta', 'cyan', 'red'];

const KEY_MODE = 'cv.theme.mode';
const KEY_ACCENT = 'cv.theme.accent';

export function loadTheme() {
	let mode = 'dark';
	let accent = 'amber';
	try {
		const m = localStorage.getItem(KEY_MODE);
		const a = localStorage.getItem(KEY_ACCENT);
		if (MODES.includes(m)) mode = m;
		if (ACCENTS.includes(a)) accent = a;
	} catch {
		/* private mode / blocked storage — fall back to the defaults */
	}
	return { mode, accent };
}

export function applyTheme(mode, accent) {
	if (typeof document === 'undefined') return;
	document.documentElement.setAttribute('data-cv-theme', mode);
	document.documentElement.setAttribute('data-cv-accent', accent);
	try {
		localStorage.setItem(KEY_MODE, mode);
		localStorage.setItem(KEY_ACCENT, accent);
	} catch {
		/* not persisting is fine — the page still renders in the chosen theme */
	}
}

export function clearTheme() {
	if (typeof document === 'undefined') return;
	document.documentElement.removeAttribute('data-cv-theme');
	document.documentElement.removeAttribute('data-cv-accent');
}
