// GET /election — front-facing endpoint serving election results as JSON.
//
// PLACEHOLDER DATA: the array below is the static example. The real data
// infrastructure (live results feed / DB / cache) gets wired in here later —
// the public URL (/election) and response shape stay the same when it does.
//
// Response: formatted JSON, forced download as election.json, never cached.

const ELECTION_DATA = [
	{
		name: 'ԱԱԱ կուսակցություն',
		nameEn: 'AAA PARTY',
		prefix: 'ԱԱԱ',
		prefixEn: 'AAA',
		votes: 3913,
		total: 1281497,
		sumSubDistricts: 2008,
		percent: 0.31
	},
	{
		name: 'ԲԲԲ կուսակցությունների դաշինք',
		nameEn: 'BBB ALLIANCE OF PARTIES',
		prefix: 'ԲԲԲ',
		prefixEn: 'BBB',
		votes: 19648,
		total: 1281497,
		sumSubDistricts: 2008,
		percent: 1.54
	},
	{
		name: 'ԳԳԳ կուսակցություն',
		nameEn: 'GGG PARTY',
		prefix: 'ԳԳԳ',
		prefixEn: 'GGG',
		votes: 688598,
		total: 1281497,
		sumSubDistricts: 2008,
		percent: 53.91
	}
];

export async function GET() {
	const body = JSON.stringify(ELECTION_DATA, null, 4);
	return new Response(body, {
		headers: {
			'content-type': 'application/json; charset=utf-8',
			'content-disposition': 'attachment; filename="election.json"',
			'cache-control': 'no-store'
		}
	});
}
