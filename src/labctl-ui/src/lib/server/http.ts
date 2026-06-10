import { json } from '@sveltejs/kit';

import type { LabctlState } from '$lib/types';

export function jsonState(state: LabctlState) {
	return json({ state });
}

export function jsonError(error: unknown, status = 400) {
	return json(
		{
			message: error instanceof Error ? error.message : 'Unexpected server error.'
		},
		{ status }
	);
}
