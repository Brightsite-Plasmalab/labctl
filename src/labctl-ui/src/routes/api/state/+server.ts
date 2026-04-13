import { getLabctlManager } from '$lib/server/labctl-manager.js';

import { jsonState } from '$lib/server/http.js';

export async function GET() {
	const manager = getLabctlManager();
	await manager.ensureReady();

	return jsonState(manager.getState());
}
