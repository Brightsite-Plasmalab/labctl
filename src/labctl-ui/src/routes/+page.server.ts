import { getLabctlManager } from '$lib/server/labctl-manager.js';

import type { PageServerLoad } from './$types';

export const load = (async () => {
	const manager = getLabctlManager();
	await manager.ensureReady();

	return {
		initialState: manager.getState()
	};
}) satisfies PageServerLoad;
