import { existsSync } from 'node:fs';
import { createServer as createHttpServer } from 'node:http';
import { createServer as createNetServer } from 'node:net';
import { join } from 'node:path';
import { pathToFileURL } from 'node:url';

import { app, BrowserWindow, dialog, ipcMain, powerMonitor, shell } from 'electron';

const HOST = '127.0.0.1';
const SERVER_START_TIMEOUT_MS = 15_000;
const SYSTEM_IDLE_THRESHOLD = 60;
const IS_DEV = process.argv.includes('--dev');

let appServer;
let serverUrlPromise;
let viteServer;
let isQuitting = false;

function getBuildHandlerEntry() {
	return join(app.getAppPath(), 'build', 'handler.js');
}

function getPreloadPath() {
	return join(app.getAppPath(), 'electron', 'preload.js');
}

function getAvailablePort() {
	return new Promise((resolve, reject) => {
		const server = createNetServer();

		server.unref();
		server.on('error', reject);
		server.listen(0, HOST, () => {
			const address = server.address();

			if (!address || typeof address === 'string') {
				reject(new Error('Could not determine an open port for the SvelteKit server.'));
				return;
			}

			server.close(() => resolve(address.port));
		});
	});
}

function sleep(ms) {
	return new Promise((resolve) => setTimeout(resolve, ms));
}

function registerPowerMonitorEvents() {
	// Power monitor events are tracked by the powerMonitor API itself.
}

function registerIpcHandlers() {
	ipcMain.handle('labctl:pick-script-file', async () => {
		const [window] = BrowserWindow.getAllWindows();
		const result = await dialog.showOpenDialog(window, {
			properties: ['openFile'],
			filters: [
				{ name: 'LabCTL scripts', extensions: ['labctl'] },
				{ name: 'All files', extensions: ['*'] }
			]
		});

		if (result.canceled) {
			return null;
		}

		return result.filePaths[0] ?? null;
	});
}

function exposeElectronApis() {
	globalThis.__electronServer = {
		powerMonitor,
		shell
	};
}

async function waitForServer(url) {
	const deadline = Date.now() + SERVER_START_TIMEOUT_MS;

	while (Date.now() < deadline) {
		try {
			const response = await fetch(url);

			if (response.ok || response.status < 500) {
				return;
			}
		} catch {
			// Keep polling until the server is reachable or we time out.
		}

		await sleep(250);
	}

	throw new Error(`Timed out waiting for the SvelteKit server at ${url}.`);
}

async function stopAppServer() {
	const stopTasks = [];

	if (viteServer) {
		stopTasks.push(viteServer.close());
		viteServer = undefined;
	}

	if (appServer) {
		stopTasks.push(
			new Promise((resolve, reject) => {
				appServer.close((error) => {
					if (error) {
						reject(error);
						return;
					}

					resolve(undefined);
				});
			})
		);
		appServer = undefined;
	}

	serverUrlPromise = undefined;
	await Promise.all(stopTasks);
}

async function startDevelopmentServer(port) {
	const { createServer } = await import('vite');

	viteServer = await createServer({
		clearScreen: false,
		root: app.getAppPath(),
		server: {
			host: HOST,
			port,
			strictPort: true
		}
	});

	await viteServer.listen();
}

async function startProductionServer(port) {
	const buildHandlerEntry = getBuildHandlerEntry();

	if (!existsSync(buildHandlerEntry)) {
		throw new Error(
			'SvelteKit build output was not found. Run "npm run build" before "npm run start".'
		);
	}

	const { handler } = await import(pathToFileURL(buildHandlerEntry).href);

	appServer = createHttpServer((request, response) => {
		handler(request, response);
	});

	await new Promise((resolve, reject) => {
		appServer.once('error', reject);
		appServer.listen(port, HOST, resolve);
	});
}

async function startAppServer() {
	const port = await getAvailablePort();
	const origin = `http://${HOST}:${port}`;

	if (IS_DEV) {
		await startDevelopmentServer(port);
	} else {
		await startProductionServer(port);
	}

	await waitForServer(origin);

	return origin;
}

function getAppUrl() {
	serverUrlPromise ??= startAppServer();
	return serverUrlPromise;
}

async function createMainWindow() {
	const window = new BrowserWindow({
		width: 1200,
		height: 820,
		minWidth: 960,
		minHeight: 640,
		title: 'LabCTL',
		webPreferences: {
			contextIsolation: true,
			nodeIntegration: false,
			preload: getPreloadPath()
		}
	});

	const appUrl = await getAppUrl();
	await window.loadURL(appUrl);

	if (IS_DEV) {
		window.webContents.openDevTools({ mode: 'detach' });
	}
}

async function boot() {
	try {
		await createMainWindow();
	} catch (error) {
		console.error(error);
		app.quit();
	}
}

app.on('before-quit', () => {
	isQuitting = true;
	void stopAppServer();
});

app.on('window-all-closed', () => {
	app.quit();
});

app.whenReady().then(async () => {
	registerPowerMonitorEvents();
	registerIpcHandlers();
	exposeElectronApis();
	await boot();

	app.on('activate', async () => {
		if (BrowserWindow.getAllWindows().length === 0 && !isQuitting) {
			await boot();
		}
	});
});
