import { jsonError, jsonState } from '$lib/server/http.js';
import { getLabctlManager } from '$lib/server/labctl-manager.js';

import type { RequestHandler } from './$types';

export const POST: RequestHandler = async ({ request }) => {
	try {
		const manager = getLabctlManager();
		await manager.ensureReady();

		const payload = (await request.json()) as
			| { action: 'start'; path: string }
			| { action: 'stop' };

		switch (payload.action) {
			case 'start':
				return jsonState(await manager.startScript(payload.path));
			case 'stop':
				return jsonState(manager.stopScript());
			default:
				throw new Error('Unsupported script action.');
		}
	} catch (error) {
		return jsonError(error);
	}
};
