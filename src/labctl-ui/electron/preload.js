import { contextBridge, ipcRenderer } from 'electron';

contextBridge.exposeInMainWorld('electronApp', {
	platform: process.platform,
	pickScriptFile: () => ipcRenderer.invoke('labctl:pick-script-file'),
	versions: {
		chrome: process.versions.chrome,
		electron: process.versions.electron,
		node: process.versions.node
	}
});
