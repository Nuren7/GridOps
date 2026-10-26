export type SensorStatus = "ok" | "warning" | "critical" | "offline";

export interface Sensor {
  id: string;
  name: string;
  machine: string;
  type: "temperature" | "humidity" | "vibration" | "pressure";
  value: number;
  unit: string;
  status: SensorStatus;
}

export interface Device {
  id: string;
  hostname: string;
  model: string;
  firmware: string;
  location: string;
  ip: string;
  lastSeen: string;
  status: SensorStatus;
}

export interface TimePoint {
  time: string;
  temperature: number;
  humidity: number;
}

export interface SensorSummary {
  sensors: Sensor[];
  devices: Device[];
  timeseries: TimePoint[];
}

const BASE_URL = (import.meta.env["VITE_API_URL"] as string | undefined)?.replace(/\/$/, "");
const USE_MOCK = !BASE_URL || import.meta.env["VITE_USE_MOCK"] === "true";
export const TOKEN_KEY = "iot_token";
export const AUTH_KEY = "isLoggedIn";

export const isMock = USE_MOCK;

export function getToken() {
  return typeof window === "undefined" ? null : localStorage.getItem(TOKEN_KEY);
}
export function isLoggedIn() {
  return (
    typeof window !== "undefined" &&
    (localStorage.getItem(AUTH_KEY) === "true" || getToken() !== null)
  );
}
export function setLoggedIn() {
  localStorage.setItem(AUTH_KEY, "true");
}
export function clearToken() {
  localStorage.removeItem(TOKEN_KEY);
  localStorage.removeItem(AUTH_KEY);
}

export class ApiError extends Error {
  constructor(
    public readonly status: number,
    message: string,
  ) {
    super(message);
    this.name = "ApiError";
  }
}

async function request<T>(path: string, init: RequestInit = {}): Promise<T> {
  const token = getToken();
  const res = await fetch(`${BASE_URL}${path}`, {
    ...init,
    headers: {
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
      ...init.headers,
    },
  });
  if (!res.ok) {
    const body = (await res.json().catch(() => null)) as { detail?: string } | null;
    throw new ApiError(res.status, body?.detail ?? `API request failed (${res.status})`);
  }
  return res.json() as Promise<T>;
}

export async function login(username: string, password: string): Promise<void> {
  if (USE_MOCK) {
    await new Promise((r) => setTimeout(r, 400));
    if (!username || password.length < 4) throw new Error("Invalid username or password");
  } else {
    await request<{ authenticated: boolean; username: string }>("/api/v1/auth/login", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ username, password }),
    });
  }
  setLoggedIn();
}

export async function register(username: string, password: string): Promise<void> {
  if (USE_MOCK) {
    await new Promise((r) => setTimeout(r, 400));
    if (!username || !password) throw new Error("Username and password are required");
    return;
  }
  await request<{ registered: boolean; username: string }>("/api/v1/auth/register", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ username, password }),
  });
}

// GET /api/v1/sensors/summary
export async function getSensorSummary(): Promise<SensorSummary> {
  if (USE_MOCK) return mockSummary();
  try {
    return await request<SensorSummary>("/api/v1/sensors/summary");
  } catch (error) {
    if (error instanceof ApiError && error.status === 401) {
      clearToken();
      throw new Error("Unauthorized");
    }
    throw error;
  }
}

// ---------- mock ----------
function mockSummary(): SensorSummary {
  const now = Date.now();
  const timeseries: TimePoint[] = Array.from({ length: 60 }, (_, i) => {
    const t = new Date(now - (59 - i) * 60_000);
    return {
      time: t.toISOString(),
      temperature: +(62 + Math.sin(i / 6) * 4 + Math.random() * 1.5).toFixed(1),
      humidity: +(41 + Math.cos(i / 9) * 5 + Math.random() * 1.2).toFixed(1),
    };
  });
  const s = (
    id: string,
    name: string,
    machine: string,
    type: Sensor["type"],
    value: number,
    unit: string,
    status: SensorStatus,
  ): Sensor => ({ id, name, machine, type, value, unit, status });
  const jitter = (v: number, d = 1) => +(v + (Math.random() - 0.5) * d).toFixed(1);
  const sensors: Sensor[] = [
    s("S-101", "Spindle temp", "CNC-01", "temperature", jitter(64.2), "°C", "ok"),
    s("S-102", "Spindle vib.", "CNC-01", "vibration", jitter(2.1, 0.3), "mm/s", "ok"),
    s("S-201", "Motor temp", "CNC-02", "temperature", jitter(88.7), "°C", "critical"),
    s("S-202", "Coolant pres.", "CNC-02", "pressure", jitter(3.4, 0.2), "bar", "warning"),
    s("S-301", "Ambient RH", "Hall A", "humidity", jitter(43.5), "%", "ok"),
    s("S-302", "Ambient temp", "Hall A", "temperature", jitter(21.8), "°C", "ok"),
    s("S-401", "Hydraulic pres.", "PRESS-01", "pressure", jitter(182, 4), "bar", "ok"),
    s("S-402", "Frame vib.", "PRESS-01", "vibration", jitter(6.8, 0.5), "mm/s", "warning"),
    s("S-501", "Oven temp", "OVEN-01", "temperature", 0, "°C", "offline"),
    s("S-601", "Belt temp", "CONV-01", "temperature", jitter(34.1), "°C", "ok"),
    s("S-602", "Ambient RH", "Hall B", "humidity", jitter(51.2), "%", "ok"),
    s("S-603", "Drive vib.", "CONV-01", "vibration", jitter(1.4, 0.2), "mm/s", "ok"),
  ];
  const ago = (m: number) => new Date(now - m * 60_000).toISOString();
  const devices: Device[] = [
    {
      id: "GW-0001",
      hostname: "gw-hall-a-01",
      model: "Siemens IOT2050",
      firmware: "1.4.2",
      location: "Hall A",
      ip: "10.20.1.11",
      lastSeen: ago(0),
      status: "ok",
    },
    {
      id: "GW-0002",
      hostname: "gw-hall-a-02",
      model: "Siemens IOT2050",
      firmware: "1.4.2",
      location: "Hall A",
      ip: "10.20.1.12",
      lastSeen: ago(1),
      status: "ok",
    },
    {
      id: "GW-0003",
      hostname: "gw-hall-b-01",
      model: "Moxa UC-8112",
      firmware: "3.1.0",
      location: "Hall B",
      ip: "10.20.2.11",
      lastSeen: ago(0),
      status: "warning",
    },
    {
      id: "PLC-0010",
      hostname: "plc-cnc-02",
      model: "Beckhoff CX9020",
      firmware: "4.0.7",
      location: "Hall A",
      ip: "10.20.1.40",
      lastSeen: ago(2),
      status: "critical",
    },
    {
      id: "PLC-0011",
      hostname: "plc-press-01",
      model: "Beckhoff CX9020",
      firmware: "4.0.7",
      location: "Hall B",
      ip: "10.20.2.40",
      lastSeen: ago(0),
      status: "ok",
    },
    {
      id: "EDG-0020",
      hostname: "edge-oven-01",
      model: "Raspberry Pi CM4",
      firmware: "2.2.1",
      location: "Hall C",
      ip: "10.20.3.21",
      lastSeen: ago(47),
      status: "offline",
    },
    {
      id: "EDG-0021",
      hostname: "edge-conv-01",
      model: "Raspberry Pi CM4",
      firmware: "2.2.1",
      location: "Hall C",
      ip: "10.20.3.22",
      lastSeen: ago(0),
      status: "ok",
    },
    {
      id: "SNS-0100",
      hostname: "rh-hall-a",
      model: "Vaisala HMT120",
      firmware: "1.0.9",
      location: "Hall A",
      ip: "10.20.1.90",
      lastSeen: ago(0),
      status: "ok",
    },
  ];
  return { sensors, devices, timeseries };
}
