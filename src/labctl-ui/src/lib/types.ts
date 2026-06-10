export type StatusTone = 'info' | 'success' | 'error';

export type LogKind = 'device' | 'meta' | 'success' | 'failure' | 'info';

export interface SerialPortOption {
	path: string;
	friendlyName: string;
	manufacturer: string | null;
	productId: string | null;
	serialNumber: string | null;
	vendorId: string | null;
}

export interface ChannelState {
	index: number;
	label: string;
	color: string;
	baudRate: number;
	isConnected: boolean;
	lastError: string | null;
	portPath: string | null;
}

export interface LogEntry {
	id: string;
	channelIndex: number | null;
	kind: LogKind;
	message: string;
	timestamp: string;
}

export interface StatusMessage {
	text: string;
	tone: StatusTone;
	updatedAt: string;
}

export interface ScriptState {
	currentChannel: number;
	filePath: string | null;
	isRunning: boolean;
	lineNumber: number;
	startedAt: string | null;
}

export interface LabctlState {
	availablePorts: SerialPortOption[];
	channels: ChannelState[];
	logs: LogEntry[];
	maxLogEntries: number;
	script: ScriptState;
	server: {
		node: string;
		pid: number;
		platform: NodeJS.Platform;
	};
	status: StatusMessage | null;
}
