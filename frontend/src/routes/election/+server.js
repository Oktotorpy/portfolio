// GET /election — serves the published election results as JSON (downloads as election.json).
//
// The backend decides the source by the CMS 'source_mode' setting:
//   manual -> the admin-edited JSON file, api -> the latest polled snapshot.
// We just proxy /api/election/published and fall back to PLACEHOLDER if the
// backend is unreachable or the selected source has no data yet, so the URL
// never breaks. Never cached, so changes show immediately.

const INTERNAL_API_URL = process.env.INTERNAL_API_URL || 'http://localhost:8000';

const PLACEHOLDER = [
	{ name: 'ԱԱԱ կուսակցություն', nameEn: 'AAA PARTY', prefix: 'ԱԱԱ', prefixEn: 'AAA', votes: 3913, total: 1281497, sumSubDistricts: 2008, percent: 0.31 },
	{ name: 'ԲԲԲ կուսակցությունների դաշինք', nameEn: 'BBB ALLIANCE OF PARTIES', prefix: 'ԲԲԲ', prefixEn: 'BBB', votes: 19648, total: 1281497, sumSubDistricts: 2008, percent: 1.54 },
	{ name: 'ԳԳԳ կուսակցություն', nameEn: 'GGG PARTY', prefix: 'ԳԳԳ', prefixEn: 'GGG', votes: 688598, total: 1281497, sumSubDistricts: 2008, percent: 53.91 }
];

export async function GET({ fetch }) {
	let parties = PLACEHOLDER;
	try {
		const res = await fetch(`${INTERNAL_API_URL}/api/election/published`);
		if (res.ok) {
			const data = await res.json();
			if (Array.isArray(data) && data.length) parties = data;
		}
	} catch {
		// backend down — keep placeholder
	}

	const body = JSON.stringify(parties, null, 4);
	return new Response(body, {
		headers: {
			'content-type': 'application/json; charset=utf-8',
			'content-disposition': 'attachment; filename="election.json"',
			'cache-control': 'no-store'
		}
	});
}
