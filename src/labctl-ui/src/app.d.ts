interface ElectronAppApi {
	platform: NodeJS.Platform;
	pickScriptFile: () => Promise<string | null>;
	versions: {
		chrome: string;
		electron: string;
		node: string;
	};
}

// See https://svelte.dev/docs/kit/types#app.d.ts
// for information about these interfaces
declare global {
	interface Window {
		electronApp?: ElectronAppApi;
	}

	namespace App {
		// interface Error {}
		// interface Locals {}
		// interface PageState {}
		// interface Platform {}
	}
}

export {};
