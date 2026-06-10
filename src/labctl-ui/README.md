# LabCTL Desktop

This directory contains the LabCTL desktop GUI rebuilt as a SvelteKit + Electron application, based on the architecture from `mruijzendaal/sveltekit-electron-template`.

## Features

- Three independent serial channels
- Serial port refresh, connect, disconnect, and manual command send
- Live serial monitor and event log
- `.labctl` script execution with `#WAIT`, `#SELSER`, `#BEEP`, and `#TEST`
- Native file picker through Electron preload

## Stack

- SvelteKit running server-side logic with `@sveltejs/adapter-node`
- Electron hosting the SvelteKit server in-process
- `serialport` for serial communication
- shadcn-svelte for the desktop UI

## Development

```sh
cd src/labctl-ui
npm install
npm run dev
```

## Checks

```sh
cd src/labctl-ui
npm run check
npm run build
```

## Packaging

```sh
cd src/labctl-ui
npm run package:mac
npm run package:win
```
