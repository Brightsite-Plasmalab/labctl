import { readFile, writeFile } from "node:fs/promises";
import { basename, dirname, extname, join } from "node:path";

import { SerialPort } from "serialport";

import type {
  ChannelState,
  LabctlState,
  LogEntry,
  ScriptState,
  SerialPortOption,
  StatusMessage,
  StatusTone,
} from "$lib/types";

import { getElectronServerApi } from "./electron";

const CHANNEL_COLORS = ["#f59e0b", "#8b5cf6", "#10b981"] as const;
const CHANNEL_LABELS = [
  "Serial connection 0",
  "Serial connection 1",
  "Serial connection 2",
] as const;
const DEFAULT_BAUD_RATES = [38400, 9600, 9600] as const;
const LOG_RETENTION_LIMIT = 1000;
const SCRIPT_SEND_DELAY_MS = 50;
const SCRIPT_QUERY_TIMEOUT_MS = 1000;
const SERIAL_NEWLINE = "\n";

interface PendingLineWaiter {
  reject: (error: Error) => void;
  resolve: (line: string) => void;
  timer: ReturnType<typeof setTimeout>;
}

interface ChannelRuntime extends ChannelState {
  buffer: string;
  detachListeners: (() => void) | null;
  isDisconnecting: boolean;
  pendingLines: string[];
  pendingWaiters: PendingLineWaiter[];
  port: SerialPort | null;
}

interface ScriptRuntime extends ScriptState {
  abortController: AbortController | null;
  logCapture: string[] | null;
}

class LabctlManager {
  private readonly channels: ChannelRuntime[] = CHANNEL_LABELS.map(
    (label, index) => ({
      baudRate: DEFAULT_BAUD_RATES[index],
      buffer: "",
      color: CHANNEL_COLORS[index],
      detachListeners: null,
      index,
      isConnected: false,
      isDisconnecting: false,
      label,
      lastError: null,
      pendingLines: [],
      pendingWaiters: [],
      port: null,
      portPath: null,
    }),
  );

  private availablePorts: SerialPortOption[] = [];
  private ensureReadyPromise: Promise<void> | null = null;
  private logs: LogEntry[] = [];
  private nextLogId = 1;
  private script: ScriptRuntime = {
    abortController: null,
    currentChannel: 0,
    filePath: null,
    isRunning: false,
    lineNumber: 0,
    logCapture: null,
    startedAt: null,
  };
  private status: StatusMessage | null = null;

  async ensureReady() {
    this.ensureReadyPromise ??= this.refreshPorts()
      .then(() => undefined)
      .catch((error) => {
        this.ensureReadyPromise = null;
        throw error;
      });
    await this.ensureReadyPromise;
  }

  getState(): LabctlState {
    return {
      availablePorts: this.availablePorts.map((port) => ({ ...port })),
      channels: this.channels.map((channel) => ({
        baudRate: channel.baudRate,
        color: channel.color,
        index: channel.index,
        isConnected: channel.isConnected,
        label: channel.label,
        lastError: channel.lastError,
        portPath: channel.portPath,
      })),
      logs: this.logs.map((entry) => ({ ...entry })),
      maxLogEntries: LOG_RETENTION_LIMIT,
      script: {
        currentChannel: this.script.currentChannel,
        filePath: this.script.filePath,
        isRunning: this.script.isRunning,
        lineNumber: this.script.lineNumber,
        startedAt: this.script.startedAt,
      },
      server: {
        node: process.version,
        pid: process.pid,
        platform: process.platform,
      },
      status: this.status ? { ...this.status } : null,
    };
  }

  async refreshPorts(updateStatus = true) {
    const ports = await SerialPort.list();
    this.availablePorts = ports
      .map((port) => ({
        friendlyName:
          [port.path, port.manufacturer].filter(Boolean).join(" - ") ||
          port.path,
        manufacturer: port.manufacturer ?? null,
        path: port.path,
        productId: port.productId ?? null,
        serialNumber: port.serialNumber ?? null,
        vendorId: port.vendorId ?? null,
      }))
      .sort((left, right) => left.path.localeCompare(right.path));

    if (updateStatus) {
      this.setStatus(
        this.availablePorts.length === 0
          ? "No serial ports detected."
          : `Detected ${this.availablePorts.length} serial port(s).`,
        "info",
      );
    }

    return this.getState();
  }

  async connectChannel(index: number, portPath: string, baudRate: number) {
    const channel = this.getChannel(index);

    if (!portPath.trim()) {
      throw new Error("Select a serial port before connecting.");
    }

    if (!Number.isInteger(baudRate) || baudRate <= 0) {
      throw new Error("Baud rate must be a positive integer.");
    }

    const inUseBy = this.channels.find(
      (candidate) =>
        candidate.index !== index &&
        candidate.isConnected &&
        candidate.portPath === portPath,
    );
    if (inUseBy) {
      throw new Error(
        `"${portPath}" is already connected on channel ${inUseBy.index}.`,
      );
    }

    if (channel.isConnected) {
      await this.disconnectChannel(index, false);
    }

    const port = new SerialPort({
      autoOpen: false,
      baudRate,
      path: portPath,
    });

    await new Promise<void>((resolve, reject) => {
      port.open((error) => {
        if (error) {
          reject(error);
          return;
        }

        resolve();
      });
    });

    const onData = (chunk: Buffer) => {
      this.handleIncomingData(channel, chunk);
    };
    const onError = (error: Error) => {
      channel.lastError = error.message;
      this.appendLog(`${channel.label} error: ${error.message}`, {
        channelIndex: channel.index,
        kind: "failure",
      });
      this.setStatus(`${channel.label} error: ${error.message}`, "error");
    };
    const onClose = () => {
      if (channel.isDisconnecting) {
        return;
      }

      this.detachChannel(channel);
      channel.isConnected = false;
      channel.port = null;
      this.rejectPendingWaiters(channel, `${channel.label} was disconnected.`);
      this.appendLog(`${channel.label} disconnected unexpectedly.`, {
        channelIndex: channel.index,
        kind: "failure",
      });
      this.setStatus(`${channel.label} disconnected unexpectedly.`, "error");
    };

    port.on("data", onData);
    port.on("error", onError);
    port.on("close", onClose);

    channel.baudRate = baudRate;
    channel.buffer = "";
    channel.detachListeners = () => {
      port.off("close", onClose);
      port.off("data", onData);
      port.off("error", onError);
    };
    channel.isConnected = true;
    channel.isDisconnecting = false;
    channel.lastError = null;
    channel.pendingLines = [];
    channel.port = port;
    channel.portPath = portPath;

    this.appendLog(
      `Connected ${channel.label} to ${portPath} @ ${baudRate} baud.`,
      {
        channelIndex: index,
        kind: "info",
      },
    );
    this.setStatus(`Connected ${channel.label} to ${portPath}.`, "success");
    await this.refreshPorts(false);

    return this.getState();
  }

  async disconnectChannel(index: number, announce = true) {
    const channel = this.getChannel(index);

    if (!channel.port || !channel.isConnected) {
      channel.isConnected = false;
      channel.port = null;
      return this.getState();
    }

    channel.isDisconnecting = true;
    const currentPort = channel.port;
    this.detachChannel(channel);

    await new Promise<void>((resolve, reject) => {
      currentPort.close((error) => {
        if (error && error.message !== "Port is not open") {
          reject(error);
          return;
        }

        resolve();
      });
    });

    channel.isConnected = false;
    channel.isDisconnecting = false;
    channel.port = null;
    this.rejectPendingWaiters(channel, `${channel.label} disconnected.`);

    if (announce) {
      this.appendLog(`Disconnected ${channel.label}.`, {
        channelIndex: index,
        kind: "info",
      });
      this.setStatus(`Disconnected ${channel.label}.`, "info");
    }

    await this.refreshPorts(false);

    return this.getState();
  }

  async sendManualCommand(index: number, rawInput: string) {
    const channel = this.getChannel(index);
    const commands = rawInput
      .split("#")[0]
      .split("|")
      .map((command) => command.trim())
      .filter(Boolean);

    if (commands.length === 0) {
      throw new Error("Enter a command before sending.");
    }

    for (const command of commands) {
      await this.writeToChannel(channel, command);
      this.appendLog(command, { channelIndex: index, kind: "device" });
    }

    this.setStatus(
      `Sent ${commands.length} command(s) through ${channel.label}.`,
      "success",
    );
    return this.getState();
  }

  async startScript(filePath: string) {
    if (this.script.isRunning) {
      throw new Error("A script is already running.");
    }

    if (!filePath.trim()) {
      throw new Error("Choose a script file before starting.");
    }

    const scriptContent = await readFile(filePath, "utf8");
    const lines = scriptContent.split(/\r?\n/);

    this.script.abortController = new AbortController();
    this.script.currentChannel = 0;
    this.script.filePath = filePath;
    this.script.isRunning = true;
    this.script.lineNumber = 0;
    this.script.logCapture = [];
    this.script.startedAt = new Date().toISOString();
    this.appendLog(`Started script ${basename(filePath)}.`, { kind: "meta" });
    this.setStatus(`Running script ${basename(filePath)}.`, "info");

    void this.runScript(filePath, lines, this.script.abortController.signal);

    return this.getState();
  }

  stopScript() {
    if (!this.script.isRunning || !this.script.abortController) {
      throw new Error("No script is currently running.");
    }

    this.script.abortController.abort();
    this.setStatus("Stopping script...", "info");
    return this.getState();
  }

  clearLogs() {
    this.logs = [];
    this.setStatus("Cleared log output.", "info");
    return this.getState();
  }

  private appendLog(
    message: string,
    options: {
      channelIndex?: number | null;
      kind?: LogEntry["kind"];
    } = {},
  ) {
    const entry: LogEntry = {
      channelIndex: options.channelIndex ?? null,
      id: `log-${this.nextLogId++}`,
      kind: options.kind ?? "info",
      message,
      timestamp: new Date().toISOString(),
    };

    this.logs = [...this.logs, entry].slice(-LOG_RETENTION_LIMIT);
    this.script.logCapture?.push(`${entry.timestamp} | ${entry.message}`);
  }

  private detachChannel(channel: ChannelRuntime) {
    channel.detachListeners?.();
    channel.detachListeners = null;
    channel.buffer = "";
    channel.pendingLines = [];
  }

  private getChannel(index: number) {
    const channel = this.channels[index];

    if (!channel) {
      throw new Error(`Channel ${index} does not exist.`);
    }

    return channel;
  }

  private handleIncomingData(channel: ChannelRuntime, chunk: Buffer) {
    channel.buffer += chunk.toString("utf8");
    const lines = channel.buffer.split(/\r?\n/);
    channel.buffer = lines.pop() ?? "";

    for (const line of lines) {
      const trimmed = line.trim();
      if (!trimmed) {
        continue;
      }

      const waiter = channel.pendingWaiters.shift();
      if (waiter) {
        clearTimeout(waiter.timer);
        waiter.resolve(trimmed);
      } else {
        channel.pendingLines.push(trimmed);
      }

      this.appendLog(trimmed, {
        channelIndex: channel.index,
        kind: "device",
      });
    }
  }

  private rejectPendingWaiters(channel: ChannelRuntime, message: string) {
    const error = new Error(message);
    for (const waiter of channel.pendingWaiters) {
      clearTimeout(waiter.timer);
      waiter.reject(error);
    }

    channel.pendingWaiters = [];
    channel.pendingLines = [];
  }

  private async queryChannel(
    index: number,
    command: string,
    timeoutMs: number,
  ) {
    const channel = this.getChannel(index);

    channel.pendingLines = [];
    await this.writeToChannel(channel, command);

    return await new Promise<string | null>((resolve, reject) => {
      const timer = setTimeout(() => {
        channel.pendingWaiters = channel.pendingWaiters.filter(
          (candidate) => candidate !== waiter,
        );
        resolve(null);
      }, timeoutMs);

      const waiter: PendingLineWaiter = {
        reject,
        resolve: (line) => resolve(line),
        timer,
      };

      channel.pendingWaiters.push(waiter);
    });
  }

  private async runScript(
    filePath: string,
    lines: string[],
    signal: AbortSignal,
  ) {
    let failureMessage: string | null = null;

    try {
      for (const [lineIndex, rawLine] of lines.entries()) {
        if (signal.aborted) {
          break;
        }

        this.script.lineNumber = lineIndex + 1;
        const trimmed = rawLine.trim();
        if (!trimmed) {
          continue;
        }

        if (trimmed.startsWith("#")) {
          await this.executeMetaCommand(trimmed, signal);
          continue;
        }

        const commandPart = rawLine.split("#")[0]?.trim() ?? "";
        const inlineCommentIndex = rawLine.indexOf("#");
        if (inlineCommentIndex >= 0) {
          const inlineComment = rawLine.slice(inlineCommentIndex + 1).trim();
          if (inlineComment) {
            this.appendLog(inlineComment, { kind: "info" });
          }
        }

        if (!commandPart) {
          continue;
        }

        const channel = this.getChannel(this.script.currentChannel);
        await this.writeToChannel(channel, commandPart);
        this.appendLog(commandPart, {
          channelIndex: channel.index,
          kind: "device",
        });
        await this.sleep(SCRIPT_SEND_DELAY_MS, signal);
      }
    } catch (error) {
      failureMessage =
        error instanceof Error ? error.message : "Unexpected script failure.";
      this.appendLog(`Script failed: ${failureMessage}`, { kind: "failure" });
    } finally {
      const wasAborted = signal.aborted;
      const logPath = await this.persistScriptLog(filePath);

      this.script.abortController = null;
      this.script.isRunning = false;
      this.script.lineNumber = 0;
      this.script.logCapture = null;
      this.script.startedAt = null;

      if (wasAborted) {
        this.appendLog("Script execution stopped.", { kind: "meta" });
        this.setStatus("Script execution stopped.", "info");
      } else if (failureMessage) {
        this.setStatus(`Script failed: ${failureMessage}`, "error");
      } else {
        this.appendLog("Script execution finished.", { kind: "meta" });
        this.setStatus("Script execution finished.", "success");
      }

      if (logPath) {
        this.appendLog(`Saved script log to ${logPath}.`, { kind: "info" });
      }
    }
  }

  private async executeMetaCommand(command: string, signal: AbortSignal) {
    if (command.startsWith("#WAIT")) {
      const milliseconds = Number.parseInt(command.slice(5).trim(), 10);
      if (!Number.isFinite(milliseconds) || milliseconds < 0) {
        throw new Error(
          `Invalid #WAIT value on line ${this.script.lineNumber}.`,
        );
      }

      this.appendLog(`Waiting for ${milliseconds} ms.`, { kind: "meta" });
      await this.sleep(milliseconds, signal);
      return;
    }

    if (command.startsWith("#SELSER")) {
      const index = Number.parseInt(command.slice(7).trim(), 10);
      if (
        !Number.isInteger(index) ||
        index < 0 ||
        index >= this.channels.length
      ) {
        throw new Error(
          `Invalid serial port index "${command.slice(7).trim()}" on line ${this.script.lineNumber}.`,
        );
      }

      this.script.currentChannel = index;
      this.appendLog(`Selected serial port ${index}.`, { kind: "meta" });
      return;
    }

    if (command === "#BEEP") {
      getElectronServerApi().shell.beep();
      this.appendLog("Beep!", { kind: "meta" });
      return;
    }

    if (command.startsWith("#TEST")) {
      await this.runTestCommand(command);
      return;
    }

    const comment = command.slice(1).trim();
    if (comment) {
      this.appendLog(comment, { kind: "info" });
    }
  }

  private async runTestCommand(command: string) {
    const match = command.match(/^#TEST(?<limit>\d*)\s+(?<body>.+)$/);
    if (!match?.groups?.body) {
      throw new Error(
        `Invalid #TEST syntax on line ${this.script.lineNumber}.`,
      );
    }

    const charLimit = match.groups.limit
      ? Number.parseInt(match.groups.limit, 10)
      : null;
    const separatorIndex = match.groups.body.indexOf("==");
    if (separatorIndex < 0) {
      throw new Error(
        `Invalid #TEST comparison on line ${this.script.lineNumber}.`,
      );
    }

    const queryCommand = match.groups.body.slice(0, separatorIndex).trim();
    let expectedSection = match.groups.body.slice(separatorIndex + 2).trim();
    let comment = "";
    const commentIndex = expectedSection.indexOf("#");
    if (commentIndex >= 0) {
      comment = expectedSection.slice(commentIndex + 1).trim();
      expectedSection = expectedSection.slice(0, commentIndex).trim();
    }

    this.appendLog(`Checking: ${queryCommand}`, {
      channelIndex: this.script.currentChannel,
      kind: "meta",
    });
    const response = await this.queryChannel(
      this.script.currentChannel,
      queryCommand,
      SCRIPT_QUERY_TIMEOUT_MS,
    );
    const label = comment ? ` (${comment})` : "";

    if (response === null) {
      this.appendLog(`Failure${label}: No response received.`, {
        kind: "failure",
      });
      this.setStatus(
        `Verification failed${label}: No response received.`,
        "error",
      );
      return;
    }

    const compared = charLimit ? response.slice(0, charLimit) : response;
    if (compared === expectedSection) {
      this.appendLog(`Success${label}: ${compared} == ${expectedSection}`, {
        kind: "success",
      });
      return;
    }

    this.appendLog(`Failure${label}: ${compared} != ${expectedSection}`, {
      kind: "failure",
    });
    this.setStatus(
      `Verification failed${label}: ${compared} != ${expectedSection}`,
      "error",
    );
  }

  private async persistScriptLog(filePath: string) {
    const capture = this.script.logCapture;
    if (!capture || capture.length === 0) {
      return null;
    }

    const timestamp = new Date()
      .toISOString()
      .replaceAll(":", "_")
      .replace(/\..+$/, "");
    const targetPath = join(
      dirname(filePath),
      `${basename(filePath, extname(filePath))}_log_${timestamp}.txt`,
    );
    await writeFile(targetPath, capture.join("\n"), "utf8");
    return targetPath;
  }

  private async sleep(milliseconds: number, signal: AbortSignal) {
    if (milliseconds === 0) {
      return;
    }

    if (signal.aborted) {
      throw new Error("Script execution aborted.");
    }

    await new Promise<void>((resolve, reject) => {
      const timer = setTimeout(() => {
        signal.removeEventListener("abort", onAbort);
        resolve();
      }, milliseconds);

      const onAbort = () => {
        clearTimeout(timer);
        reject(new Error("Script execution aborted."));
      };

      signal.addEventListener("abort", onAbort, { once: true });
    });
  }

  private setStatus(text: string, tone: StatusTone) {
    this.status = {
      text,
      tone,
      updatedAt: new Date().toISOString(),
    };
  }

  private async writeToChannel(channel: ChannelRuntime, command: string) {
    if (!channel.port || !channel.isConnected) {
      throw new Error(`${channel.label} is not connected.`);
    }

    await new Promise<void>((resolve, reject) => {
      channel.port?.write(`${command}${SERIAL_NEWLINE}`, "utf8", (error) => {
        if (error) {
          reject(error);
          return;
        }

        channel.port?.drain((drainError) => {
          if (drainError) {
            reject(drainError);
            return;
          }

          resolve();
        });
      });
    });
  }
}

let manager: LabctlManager | undefined;

export function getLabctlManager() {
  manager ??= new LabctlManager();
  return manager;
}
