import { getLabctlManager } from '$lib/server/labctl-manager';

import { jsonState } from '$lib/server/http';

export async function GET() {
	const manager = getLabctlManager();
	await manager.ensureReady();

	return jsonState(manager.getState());
}
