import { jsonError, jsonState } from '$lib/server/http.js';
import { getLabctlManager } from '$lib/server/labctl-manager.js';

import type { RequestHandler } from './$types';

function parseChannelIndex(value: string) {
	const index = Number.parseInt(value, 10);
	if (!Number.isInteger(index)) {
		throw new Error(`Invalid channel index "${value}".`);
	}

	return index;
}

export const POST: RequestHandler = async ({ params, request }) => {
	try {
		const manager = getLabctlManager();
		await manager.ensureReady();

		const index = parseChannelIndex(params.index);
		const payload = (await request.json()) as
			| { action: 'connect'; baudRate: number; path: string }
			| { action: 'disconnect' }
			| { action: 'send'; command: string };

		switch (payload.action) {
			case 'connect':
				return jsonState(await manager.connectChannel(index, payload.path, payload.baudRate));
			case 'disconnect':
				return jsonState(await manager.disconnectChannel(index));
			case 'send':
				return jsonState(await manager.sendManualCommand(index, payload.command));
			default:
				throw new Error('Unsupported channel action.');
		}
	} catch (error) {
		return jsonError(error);
	}
};
