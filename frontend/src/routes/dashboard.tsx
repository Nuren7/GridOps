import { createFileRoute, useNavigate } from "@tanstack/react-router";
import { useQuery } from "@tanstack/react-query";
import { useEffect, useMemo, useState } from "react";
import { CartesianGrid, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { clearToken, getSensorSummary, isLoggedIn, isMock, type SensorStatus } from "@/lib/api";

export const Route = createFileRoute("/dashboard")({
  head: () => ({
    meta: [
      { title: "Dashboard — Plantview IoT" },
      { name: "description", content: "Live sensor status, time series and device inventory for the factory floor." },
      { property: "og:title", content: "Dashboard — Plantview IoT" },
      { property: "og:description", content: "Live sensor status, time series and device inventory." },
    ],
  }),
  component: Dashboard,
});

const statusText: Record<SensorStatus, string> = { ok: "Normal", warning: "Warning", critical: "Critical", offline: "Offline" };
const statusDot: Record<SensorStatus, string> = { ok: "bg-ok", warning: "bg-warn", critical: "bg-crit", offline: "bg-offline" };
const statusBar: Record<SensorStatus, string> = { ok: "border-l-ok", warning: "border-l-warn", critical: "border-l-crit", offline: "border-l-offline" };

function StatusBadge({ s }: { s: SensorStatus }) {
  return (
    <span className="inline-flex items-center gap-1.5 text-xs">
      <span className={`h-2 w-2 rounded-full ${statusDot[s]}`} />
      {statusText[s]}
    </span>
  );
}

const hhmm = (iso: string) => new Date(iso).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });

function Dashboard() {
  const navigate = useNavigate();
  const [authed, setAuthed] = useState(false);
  const [q, setQ] = useState("");

  useEffect(() => {
    if (!isLoggedIn()) navigate({ to: "/" });
    else setAuthed(true);
  }, [navigate]);

  const { data, error, dataUpdatedAt } = useQuery({
    queryKey: ["sensor-summary"],
    queryFn: getSensorSummary,
    enabled: authed,
    refetchInterval: 10_000,
  });

  useEffect(() => {
    if (error?.message === "Unauthorized") navigate({ to: "/" });
  }, [error, navigate]);

  const devices = useMemo(() => {
    const term = q.trim().toLowerCase();
    if (!data) return [];
    if (!term) return data.devices;
    return data.devices.filter((d) => Object.values(d).some((v) => String(v).toLowerCase().includes(term)));
  }, [data, q]);

  const counts = useMemo(() => {
    const c = { ok: 0, warning: 0, critical: 0, offline: 0 } as Record<SensorStatus, number>;
    data?.sensors.forEach((s) => c[s.status]++);
    return c;
  }, [data]);

  if (!authed) return null;

  return (
    <div className="min-h-screen bg-background">
      <header className="flex h-11 items-center justify-between bg-header px-4 text-header-foreground">
        <div className="flex items-center gap-2">
          <div className="h-4 w-4 rounded-sm bg-primary" />
          <span className="text-sm font-semibold tracking-tight">PLANTVIEW</span>
          <span className="text-xs opacity-60">/ Plant 1 · Overview</span>
        </div>
        <div className="flex items-center gap-4 text-xs">
          {isMock && <span className="rounded-sm border border-warn px-1.5 py-0.5 text-warn">MOCK DATA</span>}
          <span className="num opacity-70">Updated {dataUpdatedAt ? new Date(dataUpdatedAt).toLocaleTimeString() : "—"}</span>
          <button onClick={() => { clearToken(); navigate({ to: "/" }); }} className="opacity-80 hover:opacity-100">Sign out</button>
        </div>
      </header>

      <main className="mx-auto max-w-[1400px] space-y-4 p-4">
        {error && error.message !== "Unauthorized" && (
          <div className="rounded-sm border border-crit/40 bg-crit/5 px-3 py-2 text-xs text-crit">Failed to load data: {error.message}</div>
        )}

        {/* KPI strip */}
        <div className="grid grid-cols-2 border bg-card md:grid-cols-5">
          <Kpi label="Sensors" value={data?.sensors.length ?? "—"} />
          <Kpi label="Normal" value={counts.ok} tone="text-ok" />
          <Kpi label="Warning" value={counts.warning} tone="text-warn" />
          <Kpi label="Critical" value={counts.critical} tone="text-crit" />
          <Kpi label="Offline" value={counts.offline} tone="text-offline" />
        </div>

        {/* Sensor status grid */}
        <Section title="Sensor status" meta={`${data?.sensors.length ?? 0} active`}>
          <div className="grid grid-cols-2 gap-px bg-border sm:grid-cols-3 lg:grid-cols-6">
            {data?.sensors.map((s) => (
              <div key={s.id} className={`border-l-[3px] bg-card px-3 py-2.5 ${statusBar[s.status]}`}>
                <div className="flex items-center justify-between">
                  <span className="num text-[11px] text-muted-foreground">{s.id}</span>
                  <StatusBadge s={s.status} />
                </div>
                <div className="mt-1 truncate text-xs font-medium">{s.machine} · {s.name}</div>
                <div className={`num mt-1 text-xl font-semibold ${s.status === "critical" ? "text-crit" : ""}`}>
                  {s.status === "offline" ? "—" : s.value}
                  <span className="ml-1 text-xs font-normal text-muted-foreground">{s.unit}</span>
                </div>
              </div>
            ))}
          </div>
        </Section>

        {/* Charts */}
        <div className="grid gap-4 lg:grid-cols-2">
          <ChartPanel title="Temperature · CNC hall avg" unit="°C" dataKey="temperature" color="var(--chart-1)" data={data?.timeseries ?? []} />
          <ChartPanel title="Relative humidity · Hall A" unit="%" dataKey="humidity" color="var(--chart-2)" data={data?.timeseries ?? []} />
        </div>

        {/* Device table */}
        <Section
          title="Devices"
          meta={`${devices.length} of ${data?.devices.length ?? 0}`}
          action={
            <input
              value={q} onChange={(e) => setQ(e.target.value)} placeholder="Search id, host, model, IP…"
              className="h-7 w-64 rounded-sm border border-input bg-card px-2 text-xs outline-none focus:border-ring"
            />
          }
        >
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs">
              <thead className="border-b bg-muted text-muted-foreground">
                <tr>{["Status", "Device ID", "Hostname", "Model", "Firmware", "Location", "IP", "Last seen"].map((h) => (
                  <th key={h} className="px-3 py-2 font-medium uppercase tracking-wide text-[10px]">{h}</th>
                ))}</tr>
              </thead>
              <tbody>
                {devices.map((d) => (
                  <tr key={d.id} className="border-b last:border-0 hover:bg-accent">
                    <td className="px-3 py-2"><StatusBadge s={d.status} /></td>
                    <td className="num px-3 py-2 font-medium">{d.id}</td>
                    <td className="num px-3 py-2">{d.hostname}</td>
                    <td className="px-3 py-2">{d.model}</td>
                    <td className="num px-3 py-2">{d.firmware}</td>
                    <td className="px-3 py-2">{d.location}</td>
                    <td className="num px-3 py-2">{d.ip}</td>
                    <td className="num px-3 py-2 text-muted-foreground">{hhmm(d.lastSeen)}</td>
                  </tr>
                ))}
                {devices.length === 0 && (
                  <tr><td colSpan={8} className="px-3 py-6 text-center text-muted-foreground">No devices match.</td></tr>
                )}
              </tbody>
            </table>
          </div>
        </Section>
      </main>
    </div>
  );
}

function Kpi({ label, value, tone = "" }: { label: string; value: number | string; tone?: string }) {
  return (
    <div className="border-r px-4 py-3 last:border-r-0">
      <div className="text-[10px] font-medium uppercase tracking-wide text-muted-foreground">{label}</div>
      <div className={`num mt-0.5 text-2xl font-semibold ${tone}`}>{value}</div>
    </div>
  );
}

function Section({ title, meta, action, children }: { title: string; meta?: string; action?: React.ReactNode; children: React.ReactNode }) {
  return (
    <section className="rounded-sm border bg-card">
      <div className="flex items-center justify-between border-b px-3 py-2">
        <div className="flex items-baseline gap-2">
          <h2 className="text-xs font-semibold uppercase tracking-wide">{title}</h2>
          {meta && <span className="num text-[11px] text-muted-foreground">{meta}</span>}
        </div>
        {action}
      </div>
      {children}
    </section>
  );
}

function ChartPanel({ title, unit, dataKey, color, data }: {
  title: string; unit: string; dataKey: "temperature" | "humidity"; color: string; data: { time: string; temperature: number; humidity: number }[];
}) {
  const last = data.at(-1)?.[dataKey];
  return (
    <Section title={title} meta={`last 60 min · ${last ?? "—"} ${unit}`}>
      <div className="h-60 p-2">
        <ResponsiveContainer width="100%" height="100%">
          <LineChart data={data} margin={{ top: 8, right: 12, bottom: 0, left: -12 }}>
            <CartesianGrid stroke="var(--border)" vertical={false} />
            <XAxis dataKey="time" tickFormatter={hhmm} tick={{ fontSize: 10, fill: "var(--muted-foreground)" }} stroke="var(--border)" minTickGap={40} />
            <YAxis tick={{ fontSize: 10, fill: "var(--muted-foreground)" }} stroke="var(--border)" domain={["auto", "auto"]} />
            <Tooltip
              labelFormatter={(v) => hhmm(String(v))}
              formatter={(v) => [`${v} ${unit}`, dataKey]}
              contentStyle={{ fontSize: 11, borderRadius: 2, border: "1px solid var(--border)", background: "var(--card)" }}
            />
            <Line type="linear" dataKey={dataKey} stroke={color} strokeWidth={1.5} dot={false} isAnimationActive={false} />
          </LineChart>
        </ResponsiveContainer>
      </div>
    </Section>
  );
}
