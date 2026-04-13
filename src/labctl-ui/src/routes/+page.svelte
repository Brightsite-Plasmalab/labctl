<script lang="ts">
  import { onMount } from "svelte";
  import { ArrowRight, CircleHelp, Cable, Plug2, Unplug } from "@lucide/svelte";

  import {
    Alert,
    AlertDescription,
    AlertTitle,
  } from "$lib/components/ui/alert/index.js";
  import { Badge } from "$lib/components/ui/badge/index.js";
  import { Button } from "$lib/components/ui/button/index.js";
  import {
    Card,
    CardContent,
    CardDescription,
    CardFooter,
    CardHeader,
    CardTitle,
  } from "$lib/components/ui/card/index.js";
  import { Input } from "$lib/components/ui/input/index.js";
  import { Separator } from "$lib/components/ui/separator/index.js";
  import type { LabctlState, LogEntry } from "$lib/types.js";

  import type { PageData } from "./$types";

  const BAUD_RATE_OPTIONS = [9600, 19200, 38400, 115200];
  const POLL_INTERVAL_MS = 1000;
  const SELECT_CLASS =
    "border-input bg-background ring-offset-background placeholder:text-muted-foreground focus-visible:ring-ring flex h-10 w-full rounded-md border px-3 py-2 text-sm focus-visible:ring-2 focus-visible:ring-offset-2 focus-visible:outline-none disabled:cursor-not-allowed disabled:opacity-50";
  const CHANNEL_STYLES = [
    {
      accent: "from-amber-400/20 via-amber-400/10 to-transparent",
      badge: "border-amber-400/30 bg-amber-400/10 text-amber-200",
      dot: "bg-amber-300",
      log: "text-amber-300",
    },
    {
      accent: "from-violet-400/20 via-violet-400/10 to-transparent",
      badge: "border-violet-400/30 bg-violet-400/10 text-violet-200",
      dot: "bg-violet-300",
      log: "text-violet-300",
    },
    {
      accent: "from-emerald-400/20 via-emerald-400/10 to-transparent",
      badge: "border-emerald-400/30 bg-emerald-400/10 text-emerald-200",
      dot: "bg-emerald-300",
      log: "text-emerald-300",
    },
  ] as const;

  type ChannelForm = {
    baudRate: string;
    portPath: string;
  };

  let { data }: { data: PageData } = $props();
  const initialState = data.initialState;

  let electronApp: Window["electronApp"] | undefined = $state(undefined);
  let pendingAction: string | null = $state(null);
  let requestError: string | null = $state(null);
  let scriptFileInput: HTMLInputElement | null = $state(null);
  let scriptPath: string = $state(initialState.script.filePath ?? "");
  let uploadedScriptPath: string | null = $state(null);
  let dashboard: LabctlState = $state(initialState);
  let commandDrafts: string[] = $state(initialState.channels.map(() => ""));
  let channelForms: ChannelForm[] = $state(
    initialState.channels.map((channel) => ({
      baudRate: String(channel.baudRate),
      portPath: channel.portPath ?? "",
    })),
  );

  function applyState(nextState: LabctlState) {
    dashboard = nextState;
    channelForms = nextState.channels.map((channel, index) => ({
      baudRate: String(
        channel.baudRate ||
          Number.parseInt(channelForms[index]?.baudRate ?? "", 10) ||
          9600,
      ),
      portPath: channel.isConnected
        ? (channel.portPath ?? "")
        : channelForms[index]?.portPath ||
          channel.portPath ||
          nextState.availablePorts[0]?.path ||
          "",
    }));

    if (nextState.script.filePath) {
      if (!uploadedScriptPath || nextState.script.filePath !== uploadedScriptPath) {
        scriptPath = nextState.script.filePath;
      }
    }
  }

  function formatTimestamp(value: string) {
    return new Intl.DateTimeFormat(undefined, {
      hour: "2-digit",
      minute: "2-digit",
      second: "2-digit",
    }).format(new Date(value));
  }

  function getLogClass(entry: LogEntry) {
    switch (entry.kind) {
      case "success":
        return "text-emerald-400";
      case "failure":
        return "text-rose-400";
      case "meta":
        return "text-fuchsia-300";
      case "device":
        return getChannelStyle(entry.channelIndex ?? 0).log;
      default:
        return "text-foreground";
    }
  }

  function getChannelStyle(index: number) {
    return CHANNEL_STYLES[index] ?? CHANNEL_STYLES[0];
  }

  function isPortReserved(channelIndex: number, portPath: string) {
    return dashboard.channels.some(
      (channel: LabctlState["channels"][number]) =>
        channel.index !== channelIndex &&
        channel.isConnected &&
        channel.portPath === portPath,
    );
  }

  async function fetchJson<T extends object>(
    input: string,
    init?: RequestInit,
  ) {
    const response = await fetch(input, {
      ...init,
      headers: {
        "content-type": "application/json",
        ...(init?.headers ?? {}),
      },
    });
    const payload = (await response.json()) as T | { message: string };

    if (!response.ok) {
      throw new Error(
        "message" in payload ? payload.message : "Request failed.",
      );
    }

    return payload as T;
  }

  async function refreshState() {
    try {
      const payload = await fetchJson<{ state: LabctlState }>("/api/state");
      applyState(payload.state);
    } catch (error) {
      requestError =
        error instanceof Error ? error.message : "Failed to refresh state.";
    }
  }

  async function runAction(
    actionKey: string,
    input: string,
    init?: RequestInit,
  ) {
    pendingAction = actionKey;
    requestError = null;

    try {
      const payload = await fetchJson<{ state: LabctlState }>(input, init);
      applyState(payload.state);
    } catch (error) {
      requestError = error instanceof Error ? error.message : "Action failed.";
    } finally {
      pendingAction = null;
    }
  }

  async function refreshPorts() {
    await runAction("refresh-ports", "/api/ports/refresh", {
      body: "{}",
      method: "POST",
    });
  }

  async function connectChannel(index: number) {
    const form = channelForms[index];
    await runAction(`connect-${index}`, `/api/channels/${index}`, {
      body: JSON.stringify({
        action: "connect",
        baudRate: Number.parseInt(form.baudRate, 10),
        path: form.portPath,
      }),
      method: "POST",
    });
  }

  async function disconnectChannel(index: number) {
    await runAction(`disconnect-${index}`, `/api/channels/${index}`, {
      body: JSON.stringify({ action: "disconnect" }),
      method: "POST",
    });
  }

  async function sendCommand(index: number) {
    const command = commandDrafts[index]?.trim() ?? "";
    if (!command) {
      requestError = `Enter a command for channel ${index} before sending.`;
      return;
    }

    await runAction(`send-${index}`, `/api/channels/${index}`, {
      body: JSON.stringify({
        action: "send",
        command,
      }),
      method: "POST",
    });

    commandDrafts[index] = "";
  }

  async function browseScript() {
    requestError = null;

    try {
      if (electronApp?.pickScriptFile) {
        const selectedPath = await electronApp.pickScriptFile();
        if (selectedPath) {
          uploadedScriptPath = null;
          scriptPath = selectedPath;
        }
        return;
      }

      scriptFileInput?.click();
    } catch (error) {
      requestError =
        error instanceof Error
          ? error.message
          : "Failed to open the script picker.";
    }
  }

  async function handleScriptFileSelected(event: Event) {
    const target = event.currentTarget;
    if (!(target instanceof HTMLInputElement)) {
      return;
    }

    const file = target.files?.[0];
    if (!file) {
      return;
    }

    pendingAction = "upload-script";
    requestError = null;

    try {
      const formData = new FormData();
      formData.set("script", file);

      const response = await fetch("/api/script/upload", {
        body: formData,
        method: "POST",
      });
      const payload = (await response.json()) as
        | { fileName: string; path: string }
        | { message: string };

      if (!response.ok || !("path" in payload)) {
        throw new Error("message" in payload ? payload.message : "Failed to upload the script.");
      }

      uploadedScriptPath = payload.path;
      scriptPath = payload.fileName;
    } catch (error) {
      requestError =
        error instanceof Error ? error.message : "Failed to upload the script.";
    } finally {
      target.value = "";
      pendingAction = null;
    }
  }

  async function toggleScript() {
    if (dashboard.script.isRunning) {
      await runAction("stop-script", "/api/script", {
        body: JSON.stringify({ action: "stop" }),
        method: "POST",
      });
      return;
    }

    await runAction("start-script", "/api/script", {
      body: JSON.stringify({
        action: "start",
        path: uploadedScriptPath ?? scriptPath,
      }),
      method: "POST",
    });
  }

  async function clearLogs() {
    await runAction("clear-logs", "/api/logs/clear", {
      body: "{}",
      method: "POST",
    });
  }

  onMount(() => {
    electronApp = window.electronApp;
    void refreshState();

    const timer = window.setInterval(() => {
      void refreshState();
    }, POLL_INTERVAL_MS);

    return () => window.clearInterval(timer);
  });
</script>

<svelte:head>
  <title>LabCTL Desktop</title>
</svelte:head>

<div
  class="min-h-screen bg-background bg-[radial-gradient(circle_at_top,_rgba(96,165,250,0.16),_transparent_38%),linear-gradient(180deg,transparent,transparent)]"
>
  <div class="mx-auto flex max-w-7xl flex-col gap-6 px-4 py-6 md:px-6">
    <section
      class="flex flex-col gap-4 rounded-3xl border border-primary/15 bg-card/75 p-5 shadow-sm shadow-primary/5 lg:flex-row lg:items-end lg:justify-between"
    >
      <div class="space-y-2">
        <div class="flex items-center gap-2">
          <Badge
            variant="outline"
            class="border-primary/25 bg-primary/8 text-primary"
          >
            Electron
          </Badge>
          <Badge variant="secondary">SvelteKit</Badge>
          <Badge variant="secondary">serialport</Badge>
        </div>
        <div class="space-y-1">
          <p
            class="text-xs font-medium uppercase tracking-[0.22em] text-primary/80"
          >
            Device control
          </p>
          <h1 class="text-3xl font-semibold tracking-tight">LabCTL Desktop</h1>
        </div>
        <p class="max-w-3xl text-sm leading-6 text-muted-foreground">
          Three-channel serial control, live monitor output, and LabCTL script
          execution in a desktop shell built from the SvelteKit-Electron
          template.
        </p>
      </div>

      <div class="flex flex-col gap-3 lg:min-w-[24rem]">
        <div class="grid grid-cols-2 gap-2 text-sm text-muted-foreground">
          <div
            class="rounded-2xl border border-primary/10 bg-background/80 p-3"
          >
            <p class="text-xs uppercase tracking-wide">Platform</p>
            <p class="mt-1 font-medium text-foreground">
              {electronApp?.platform ?? dashboard.server.platform}
            </p>
          </div>
          <div
            class="rounded-2xl border border-primary/10 bg-background/80 p-3"
          >
            <p class="text-xs uppercase tracking-wide">Runtime</p>
            <p class="mt-1 font-medium text-foreground">
              {electronApp?.versions.electron ?? dashboard.server.node}
            </p>
          </div>
        </div>
        <div
          class="flex items-center justify-between rounded-2xl border border-primary/10 bg-background/80 p-3"
        >
          <div class="space-y-1">
            <p class="text-xs uppercase tracking-wide text-muted-foreground">
              Serial ports
            </p>
            <p class="text-sm font-medium text-foreground">
              {dashboard.availablePorts.length} available
            </p>
          </div>
          <Button
            variant="secondary"
            disabled={pendingAction !== null}
            onclick={refreshPorts}
          >
            Refresh
          </Button>
        </div>
      </div>
    </section>

    {#if requestError}
      <Alert variant="destructive">
        <AlertTitle>Request failed</AlertTitle>
        <AlertDescription>{requestError}</AlertDescription>
      </Alert>
    {/if}

    {#if dashboard.status}
      <Alert
        variant={dashboard.status.tone === "error" ? "destructive" : "default"}
      >
        <AlertTitle>
          {dashboard.status.tone === "error"
            ? "Attention"
            : dashboard.status.tone === "success"
              ? "Ready"
              : "Status"}
        </AlertTitle>
        <AlertDescription>
          {dashboard.status.text}
          <span class="ml-2 text-xs text-muted-foreground">
            {formatTimestamp(dashboard.status.updatedAt)}
          </span>
        </AlertDescription>
      </Alert>
    {/if}

    <section class="grid gap-4 md:grid-cols-3">
      {#each dashboard.channels as channel, index}
        <Card
          class="relative overflow-hidden border-border/60 bg-card/85 shadow-md shadow-black/5"
        >
          <div
            class={`pointer-events-none absolute inset-x-0 top-0 h-16 bg-linear-to-b ${getChannelStyle(index).accent}`}
          ></div>
          <CardHeader>
            <div class="flex items-start justify-between gap-4">
              <div class="space-y-1">
                <div class="flex items-center gap-2">
                  <span
                    class={`h-2.5 w-2.5 rounded-full ${getChannelStyle(index).dot}`}
                  ></span>
                  <p
                    class="text-xs font-medium uppercase tracking-[0.18em] text-muted-foreground"
                  >
                    Channel {index}
                  </p>
                </div>
                <CardTitle>{channel.label}</CardTitle>
              </div>
              <Badge
                variant="outline"
                class={channel.isConnected
                  ? getChannelStyle(index).badge
                  : "border-border/70 bg-muted/60 text-muted-foreground"}
              >
                {channel.isConnected ? "Connected" : "Disconnected"}
              </Badge>
            </div>
          </CardHeader>
          <CardContent class="space-y-4">
            <div>
              <div class="flex items-center justify-between gap-3">
                <label class="text-sm font-medium" for={`port-${index}`}
                  >Port</label
                >
                <label class="text-sm font-medium" for={`port-${index}`}
                  >Baud rate</label
                >
              </div>

              <div class="flex flex-row gap-2">
                <select
                  id={`port-${index}`}
                  class="{SELECT_CLASS} grow"
                  bind:value={channelForms[index].portPath}
                  disabled={pendingAction !== null}
                >
                  <option value="">Select a serial port</option>
                  {#each dashboard.availablePorts as port}
                    <option
                      value={port.path}
                      disabled={isPortReserved(index, port.path)}
                    >
                      {port.friendlyName}
                    </option>
                  {/each}
                </select>

                <select
                  id={`baud-${index}`}
                  class={`${SELECT_CLASS} w-20!`}
                  bind:value={channelForms[index].baudRate}
                  disabled={pendingAction !== null}
                >
                  {#each BAUD_RATE_OPTIONS as baudRate}
                    <option value={String(baudRate)}>{baudRate}</option>
                  {/each}
                </select>
              </div>
            </div>

            <div>
              <div class="flex items-center justify-between gap-3">
                <label class="text-sm font-medium" for={`command-${index}`}
                  >Manual command</label
                >
                <Button
                  variant="ghost"
                  size="icon-sm"
                  class="text-muted-foreground"
                  title="Use | to queue multiple commands. Inline comments after # are ignored for manual sends."
                  aria-label="Command help"
                  disabled={pendingAction !== null}
                >
                  <CircleHelp />
                </Button>
              </div>
              <div class="flex items-center gap-2">
                <Input
                  id={`command-${index}`}
                  class="flex-1"
                  bind:value={commandDrafts[index]}
                  disabled={!channel.isConnected || pendingAction !== null}
                  onkeydown={(event) => {
                    if (event.key === "Enter") {
                      event.preventDefault();
                      void sendCommand(index);
                    }
                  }}
                  placeholder={channel.isConnected
                    ? "Enter a command"
                    : "Connect this channel to send commands"}
                />
                <Button
                  size="icon"
                  disabled={pendingAction !== null || !channel.isConnected}
                  onclick={() => sendCommand(index)}
                  aria-label={`Send command to channel ${index}`}
                  title={`Send command to channel ${index}`}
                >
                  <ArrowRight />
                </Button>
              </div>
            </div>

            {#if channel.lastError}
              <p class="text-sm text-rose-400">{channel.lastError}</p>
            {/if}
          </CardContent>
          <CardFooter
            class="flex items-center justify-between gap-3 border-t border-border/50 pt-4"
          >
            <div class="flex items-center gap-2 text-sm text-muted-foreground">
              <Cable class="size-4" />
              <span>{channel.portPath ?? "No active port"}</span>
            </div>
            <Button
              class="min-w-32"
              variant={channel.isConnected ? "secondary" : "default"}
              disabled={pendingAction !== null ||
                (!channel.isConnected && !channelForms[index].portPath)}
              onclick={() =>
                channel.isConnected
                  ? disconnectChannel(index)
                  : connectChannel(index)}
            >
              {#if channel.isConnected}
                <Unplug />
                Disconnect
              {:else}
                <Plug2 />
                Connect
              {/if}
            </Button>
          </CardFooter>
        </Card>
      {/each}
    </section>

    <section class="grid gap-4 xl:grid-cols-[1.15fr_1.85fr]">
      <Card class="border-border/60 bg-card/80">
        <CardHeader>
          <CardTitle>Script execution</CardTitle>
          <CardDescription>
            Run <code>.labctl</code> files with <code>#WAIT</code>,
            <code>#SELSER</code>,
            <code>#BEEP</code>, and <code>#TEST</code> meta commands.
          </CardDescription>
        </CardHeader>
        <CardContent class="space-y-4">
          <input
            bind:this={scriptFileInput}
            type="file"
            accept=".labctl"
            class="hidden"
            onchange={handleScriptFileSelected}
          />
          <div class="space-y-2">
            <label class="text-sm font-medium" for="script-path"
              >Script file</label
            >
            <Input
              id="script-path"
              bind:value={scriptPath}
              oninput={() => {
                uploadedScriptPath = null;
              }}
              disabled={dashboard.script.isRunning || pendingAction !== null}
              placeholder="/path/to/file.labctl"
            />
          </div>

          <div class="flex flex-col gap-2 sm:flex-row">
            <Button
              variant="secondary"
              disabled={dashboard.script.isRunning || pendingAction !== null}
              onclick={browseScript}
            >
              Browse
            </Button>
            <Button
              disabled={pendingAction !== null ||
                (!dashboard.script.isRunning && !scriptPath)}
              onclick={toggleScript}
            >
              {dashboard.script.isRunning ? "Stop script" : "Start script"}
            </Button>
            <Button
              variant="outline"
              disabled={pendingAction !== null || dashboard.logs.length === 0}
              onclick={clearLogs}
            >
              Clear log
            </Button>
          </div>

          <Separator />

          <div class="grid gap-3 text-sm md:grid-cols-2">
            <div
              class="rounded-xl border border-border/60 bg-background/70 p-3"
            >
              <p class="text-xs uppercase tracking-wide text-muted-foreground">
                Status
              </p>
              <p class="mt-1 font-medium text-foreground">
                {dashboard.script.isRunning ? "Running" : "Idle"}
              </p>
            </div>
            <div
              class="rounded-xl border border-border/60 bg-background/70 p-3"
            >
              <p class="text-xs uppercase tracking-wide text-muted-foreground">
                Selected serial
              </p>
              <p class="mt-1 font-medium text-foreground">
                {dashboard.script.currentChannel}
              </p>
            </div>
            <div
              class="rounded-xl border border-border/60 bg-background/70 p-3"
            >
              <p class="text-xs uppercase tracking-wide text-muted-foreground">
                Line
              </p>
              <p class="mt-1 font-medium text-foreground">
                {dashboard.script.lineNumber}
              </p>
            </div>
            <div
              class="rounded-xl border border-border/60 bg-background/70 p-3"
            >
              <p class="text-xs uppercase tracking-wide text-muted-foreground">
                File
              </p>
              <p class="mt-1 truncate font-medium text-foreground">
                {dashboard.script.filePath ?? "None selected"}
              </p>
            </div>
          </div>
        </CardContent>
      </Card>

      <Card class="border-border/60 bg-card/80">
        <CardHeader>
          <CardTitle>Serial monitor and log</CardTitle>
          <CardDescription>
            Live serial output, script progress, and test results are retained
            up to
            {dashboard.maxLogEntries} lines.
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div
            class="h-[32rem] overflow-auto rounded-xl border border-border/60 bg-background/70 p-4 font-mono text-sm leading-6"
          >
            {#if dashboard.logs.length === 0}
              <p class="text-muted-foreground">No serial activity yet.</p>
            {:else}
              <div class="space-y-1">
                {#each dashboard.logs as entry (entry.id)}
                  <div
                    class={`grid grid-cols-[5rem_1fr] gap-3 ${getLogClass(entry)}`}
                  >
                    <span class="text-xs text-muted-foreground">
                      {formatTimestamp(entry.timestamp)}
                    </span>
                    <span>{entry.message}</span>
                  </div>
                {/each}
              </div>
            {/if}
          </div>
        </CardContent>
      </Card>
    </section>
  </div>
</div>
