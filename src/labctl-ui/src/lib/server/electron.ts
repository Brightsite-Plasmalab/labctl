import type { PowerMonitor, Shell } from 'electron';

export interface ElectronServerApi {
  powerMonitor: PowerMonitor;
  shell: Shell;
}

declare global {
  var __electronServer: ElectronServerApi | undefined;
}

export function getElectronServerApi(): ElectronServerApi {
  const electronServerApi = globalThis.__electronServer;

  if (!electronServerApi) {
    throw new Error(
      'Electron APIs are unavailable because the SvelteKit server is not running inside the Electron process.',
    );
  }

  return electronServerApi;
}
