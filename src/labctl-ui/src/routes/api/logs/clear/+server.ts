import { jsonError, jsonState } from '$lib/server/http';
import { getLabctlManager } from '$lib/server/labctl-manager';

export async function POST() {
	try {
		const manager = getLabctlManager();
		await manager.ensureReady();

		return jsonState(manager.clearLogs());
	} catch (error) {
		return jsonError(error);
	}
}
