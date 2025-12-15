import { useEffect, useMemo, useState } from "react";
import axios from "axios";
import "./index.css";

type Org = { id: string; name: string };
type Project = { id: string; name: string; organization_id: string; autopilot_enabled?: boolean };
type Plan = { id: string; slot_date: string; slot_index: number; status: string; approved: boolean; locked: boolean };
type CalendarSlot = { date: string; slots: Plan[] };
type Metric = { metric: string; value: number; created_at: string };
type Credential = { id: string; provider: string; name: string; version: number };
type JobRun = { status: string; message?: string; created_at: string };
type Job = { id: string; type: string; status: string; created_at: string; runs?: JobRun[] };
type VideoAsset = {
  id: string;
  plan_id?: string | null;
  project_id?: string;
  status: string;
  created_at?: string;
  publish_response?: string | null;
  signed_thumbnail_url?: string | null;
  signed_video_url?: string | null;
  video_path: string;
  thumbnail_path: string;
};
type UsageSnapshot = { [metric: string]: number };

const api = axios.create({ baseURL: "/api" });

function App() {
  const [email, setEmail] = useState("demo@codex.dev");
  const [password, setPassword] = useState("demopass123");
  const [token, setToken] = useState("");
  const [orgs, setOrgs] = useState<Org[]>([]);
  const [orgId, setOrgId] = useState("");
  const [projects, setProjects] = useState<Project[]>([]);
  const [projectId, setProjectId] = useState("");
  const [calendar, setCalendar] = useState<CalendarSlot[]>([]);
  const [metrics, setMetrics] = useState<Metric[]>([]);
  const [credentials, setCredentials] = useState<Credential[]>([]);
  const [jobs, setJobs] = useState<Job[]>([]);
  const [assets, setAssets] = useState<VideoAsset[]>([]);
  const [usage, setUsage] = useState<UsageSnapshot>({});
  const [status, setStatus] = useState<string>("");
  const [activeView, setActiveView] = useState<
    "dashboard" | "calendar" | "library" | "analytics" | "credentials" | "queue" | "youtube"
  >("dashboard");
  const [autopilot, setAutopilot] = useState<boolean>(false);

  const headers = useMemo(() => (token ? { Authorization: `Bearer ${token}` } : {}), [token]);

  const login = async () => {
    try {
      const resp = await api.post("/auth/login", { email, password });
      setToken(resp.data.access_token);
      api.defaults.headers.common["Authorization"] = `Bearer ${resp.data.access_token}`;
      await loadOrgs();
      setActiveView("dashboard");
      setStatus("Eingeloggt");
    } catch (e: any) {
      setStatus(e?.response?.data?.detail || "Login fehlgeschlagen");
    }
  };

  const loadOrgs = async () => {
    const o = await api.get("/orgs", { headers });
    setOrgs(o.data);
    if (o.data.length > 0) {
      const first = o.data[0].id;
      setOrgId(first);
      await loadProjects(first);
    }
  };

  const loadProjects = async (oid: string) => {
    const p = await api.get(`/projects/${oid}`, { headers });
    setProjects(p.data);
    if (p.data.length > 0) {
      const pid = p.data[0].id;
      setProjectId(pid);
      await refreshData(pid, oid);
    }
  };

  const refreshData = async (pid: string, oid: string) => {
    if (!pid || !oid) return;
    const [cal, metricsResp, creds, jobsResp, assetsResp, usageResp] = await Promise.all([
      api.get(`/plans/calendar/${pid}`, { headers }),
      api.get(`/analytics/metrics/${pid}`, { headers }),
      api.get(`/credentials/${oid}`, { headers }),
      api.get(`/jobs/${pid}`, { headers }),
      api.get(`/video/assets/project/${pid}`, { headers }),
      api.get(`/usage/${oid}`, { headers }),
    ]);
    setCalendar(cal.data);
    setMetrics(metricsResp.data.metrics || []);
    setCredentials(creds.data);
    setJobs(jobsResp.data.jobs || []);
    setAssets(assetsResp.data || []);
    setUsage(usageResp.data.usage || {});
    const proj = projects.find((p) => p.id === pid);
    if (proj && typeof proj.autopilot_enabled !== "undefined") {
      setAutopilot(!!proj.autopilot_enabled);
    }
  };

  useEffect(() => {
    login().catch(() => {
      setStatus("Auto-Login fehlgeschlagen, bitte manuell einloggen.");
    });
  }, []);

  const generatePlanMonth = async () => {
    if (!projectId) return;
    await api.post(`/plans/generate/${projectId}`, null, { headers });
    await refreshData(projectId, orgId);
    setStatus("Monatsplan erstellt");
  };

  const generateAssets = async (planId: string) => {
    if (!projectId) return;
    await api.post(`/video/generate/${projectId}/${planId}`, null, { headers });
    setStatus("Assets-Job gestartet");
    await refreshData(projectId, orgId);
  };

  const publishNow = async (assetId: string) => {
    await api.post(`/video/publish/${assetId}`, { use_stored_token: true }, { headers });
    setStatus("Publish-Job gestartet");
    await refreshData(projectId, orgId);
  };

  const refreshPublishStatus = async (assetId: string) => {
    try {
      const resp = await api.get(`/video/status/${assetId}`, { headers });
      setStatus(`Publish-Status: ${resp.data.status}`);
      await refreshData(projectId, orgId);
    } catch (e: any) {
      setStatus(e?.response?.data?.detail || "Status-Check fehlgeschlagen");
    }
  };

  const addCredential = async () => {
    await api.post(
      `/credentials/${orgId}`,
      { provider: "openrouter", name: "openrouter_default", secret: "change-me" },
      { headers }
    );
    await refreshData(projectId, orgId);
  };

  const connectTikTok = async () => {
    const start = await api.get(`/tiktok/oauth/start?org_id=${orgId}`, { headers });
    setStatus("TikTok OAuth URL bereit: " + start.data.redirect_url);
    window.open(start.data.redirect_url, "_blank");
  };

  const logout = () => {
    setToken("");
    setProjects([]);
    setProjectId("");
    setOrgs([]);
    setOrgId("");
    setCalendar([]);
    setMetrics([]);
    setCredentials([]);
    setJobs([]);
    setAssets([]);
    setStatus("Abgemeldet");
  };

  const refreshMetrics = async () => {
    await api.post(`/analytics/metrics/${projectId}/refresh`, null, { headers });
    setStatus("Metrics-Job gestartet");
    await refreshData(projectId, orgId);
  };

  const transcribe = async () => {
    try {
      await api.post(`/youtube/transcribe`, { url: "https://youtu.be/demo", target_language: "de" }, { headers });
    } catch (e: any) {
      setStatus(e?.response?.data?.detail || "Transcribe nicht verfügbar");
    }
  };

  const approvePlan = async (planId: string) => {
    await api.post(`/plans/approve/${planId}`, null, { headers });
    await refreshData(projectId, orgId);
  };

  const lockPlan = async (planId: string) => {
    await api.post(`/plans/lock/${planId}`, null, { headers });
    await refreshData(projectId, orgId);
  };

  const toggleAutopilot = async (enabled: boolean) => {
    await api.post(`/projects/toggle/${projectId}?enabled=${enabled}`, null, { headers });
    setAutopilot(enabled);
  };

  const latestAssetForPlan = (planId: string) => assets.find((a) => a.plan_id === planId);

  return (
    <div className="min-h-screen bg-slate-950 text-white p-6 space-y-4">
      <header className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h1 className="text-2xl font-bold">Codex TikTok Studio</h1>
          <p className="text-xs text-slate-400">Offizielle TikTok API, Multi-Tenant, Docker ready</p>
        </div>
        <div className="flex flex-wrap gap-2 text-sm">
          {["dashboard", "calendar", "library", "analytics", "credentials", "queue", "youtube"].map((v) => (
            <button
              key={v}
              onClick={() => setActiveView(v as any)}
              className={`px-3 py-1 rounded ${activeView === v ? "bg-indigo-600" : "bg-slate-800"} hover:bg-indigo-500`}
            >
              {v}
            </button>
          ))}
        </div>
      </header>

      <div className="bg-slate-900 p-3 rounded text-xs text-amber-300">{status}</div>
      <div className="bg-slate-900 p-3 rounded text-xs text-slate-200 flex items-center gap-6 flex-wrap">
        <div className="flex items-center gap-2">
          <span>Autopilot:</span>
          <button
            className={`px-3 py-1 rounded ${autopilot ? "bg-emerald-600" : "bg-slate-700"}`}
            onClick={() => toggleAutopilot(!autopilot)}
            disabled={!projectId}
          >
            {autopilot ? "aktiv" : "inaktiv"}
          </button>
        </div>
        <div className="flex items-center gap-2">
          <span>Usage:</span>
          <div className="flex gap-2 flex-wrap">
            {Object.entries(usage).map(([k, v]) => (
              <span key={k} className="px-2 py-1 bg-slate-800 rounded">{k}: {v}</span>
            ))}
          </div>
        </div>
      </div>

      {activeView === "dashboard" && (
        <div className="grid md:grid-cols-2 gap-4">
          <div className="bg-slate-900 p-4 rounded space-y-3">
            <h2 className="font-semibold">Auth / Org / Project</h2>
            <div className="flex gap-2 items-center">
              <input className="bg-slate-800 px-2 py-1 rounded text-sm w-56" value={email} onChange={(e) => setEmail(e.target.value)} />
              <input
                className="bg-slate-800 px-2 py-1 rounded text-sm w-40"
                value={password}
                type="password"
                onChange={(e) => setPassword(e.target.value)}
              />
              <button className="px-3 py-1 bg-emerald-600 rounded text-sm" onClick={login}>
                Login
              </button>
              <button className="px-3 py-1 bg-slate-700 rounded text-sm" onClick={logout}>
                Logout
              </button>
            </div>
            <div className="flex gap-2 items-center">
              <select
                className="bg-slate-800 px-2 py-1 rounded text-sm"
                value={orgId}
                onChange={(e) => {
                  setOrgId(e.target.value);
                  loadProjects(e.target.value);
                }}
              >
                {orgs.map((o) => (
                  <option key={o.id} value={o.id}>
                    {o.name}
                  </option>
                ))}
              </select>
              <select
                className="bg-slate-800 px-2 py-1 rounded text-sm"
                value={projectId}
                onChange={(e) => {
                  setProjectId(e.target.value);
                  refreshData(e.target.value, orgId);
                }}
              >
                {projects.map((p) => (
                  <option key={p.id} value={p.id}>
                    {p.name}
                  </option>
                ))}
              </select>
              <button className="px-3 py-1 bg-blue-600 rounded text-sm" onClick={generatePlanMonth}>
                30x3 Plan
              </button>
              <button className="px-3 py-1 bg-slate-700 rounded text-sm" onClick={() => refreshData(projectId, orgId)}>
                Refresh
              </button>
            </div>
            <div className="text-xs text-slate-400">Token: {token ? "aktiv" : "-"} | Org: {orgId} | Project: {projectId}</div>
          </div>
          <div className="bg-slate-900 p-4 rounded space-y-3">
            <h2 className="font-semibold">TikTok Connect</h2>
            <p className="text-sm text-slate-300">OAuth starten; Callback im Backend. Danach kann Publish genutzt werden.</p>
            <button className="px-3 py-1 bg-purple-600 rounded text-sm" onClick={connectTikTok}>
              TikTok verbinden
            </button>
            <p className="text-xs text-slate-400">Hinweis: Tokens werden verschlüsselt gespeichert.</p>
          </div>
        </div>
      )}

      {activeView === "calendar" && (
        <div className="bg-slate-900 p-4 rounded">
          <h2 className="font-semibold mb-2">Calendar (30x3)</h2>
          <div className="grid md:grid-cols-3 gap-3 max-h-[520px] overflow-auto">
            {calendar.map((slot) => (
              <div key={slot.date} className="border border-slate-700 p-3 rounded">
                <div className="text-sm text-slate-300">{slot.date}</div>
                <div className="flex flex-wrap gap-2 mt-2">
                  {slot.slots.map((s) => {
                    const asset = latestAssetForPlan(s.id);
                    return (
                      <div key={s.id} className="flex flex-col bg-slate-800 p-2 rounded text-xs gap-1 w-full">
                        <div className="flex justify-between">
                          <span>
                            Slot {s.slot_index} · {s.status}
                          </span>
                          <span>
                            {s.approved ? "Approved" : ""} {s.locked ? "Locked" : ""}
                          </span>
                        </div>
                        <div className="flex gap-2 flex-wrap">
                          <button className="px-2 py-1 bg-emerald-600 rounded text-xs" onClick={() => generateAssets(s.id)}>
                            Assets generieren
                          </button>
                          <button className="px-2 py-1 bg-blue-700 rounded text-xs" onClick={() => approvePlan(s.id)}>
                            Approve
                          </button>
                          <button className="px-2 py-1 bg-slate-700 rounded text-xs" onClick={() => lockPlan(s.id)}>
                            Lock
                          </button>
                          {asset && asset.signed_video_url && (
                            <button
                              className="px-2 py-1 bg-orange-600 rounded text-xs"
                              onClick={() => window.open(asset.signed_video_url!, "_blank")}
                            >
                              Preview
                            </button>
                          )}
                          {asset && (
                            <button className="px-2 py-1 bg-purple-700 rounded text-xs" onClick={() => publishNow(asset.id)}>
                              Publish
                            </button>
                          )}
                        </div>
                        {asset && (
                          <div className="text-[11px] text-slate-300">
                            Asset {asset.id.slice(0, 6)} · {asset.status}
                          </div>
                        )}
                      </div>
                    );
                  })}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {activeView === "library" && (
        <div className="bg-slate-900 p-4 rounded space-y-3">
          <div className="flex items-center justify-between">
            <h2 className="font-semibold">Video Library</h2>
            <button className="px-3 py-1 bg-slate-700 rounded text-sm" onClick={() => refreshData(projectId, orgId)}>
              Reload
            </button>
          </div>
          <div className="grid md:grid-cols-3 gap-3">
            {assets.map((asset) => (
              <div key={asset.id} className="bg-slate-800 p-3 rounded text-sm space-y-2">
                {asset.signed_thumbnail_url ? (
                  <img src={asset.signed_thumbnail_url} alt="thumbnail" className="rounded" />
                ) : (
                  <div className="h-32 bg-slate-700 rounded flex items-center justify-center text-xs text-slate-300">Kein Thumbnail</div>
                )}
                <div className="flex justify-between text-xs text-slate-400">
                  <span>Status: {asset.status}</span>
                  <span>{asset.created_at ? new Date(asset.created_at).toLocaleString() : ""}</span>
                </div>
                <div className="flex gap-2 flex-wrap text-xs">
                  {asset.signed_video_url && (
                    <button className="px-2 py-1 bg-orange-600 rounded" onClick={() => window.open(asset.signed_video_url!, "_blank")}>
                      Video öffnen
                    </button>
                  )}
                  <button className="px-2 py-1 bg-indigo-700 rounded" onClick={() => refreshPublishStatus(asset.id)}>
                    Status
                  </button>
                  <button className="px-2 py-1 bg-purple-700 rounded" onClick={() => publishNow(asset.id)}>
                    Publish
                  </button>
                </div>
                {asset.publish_response && <div className="text-[11px] text-slate-400 break-words">Last publish: {asset.publish_response}</div>}
              </div>
            ))}
          </div>
        </div>
      )}

      {activeView === "analytics" && (
        <div className="bg-slate-900 p-4 rounded space-y-2">
          <div className="flex items-center justify-between">
            <h2 className="font-semibold">Analytics</h2>
            <button className="px-3 py-1 bg-blue-600 rounded text-sm" onClick={refreshMetrics}>
              Metrics refresh
            </button>
          </div>
          <ul className="divide-y divide-slate-800 text-sm">
            {metrics.map((m, idx) => (
              <li key={idx} className="py-1 flex justify-between">
                <span>{m.metric}</span>
                <span>{m.value}</span>
              </li>
            ))}
          </ul>
        </div>
      )}

      {activeView === "credentials" && (
        <div className="bg-slate-900 p-4 rounded space-y-2">
          <h2 className="font-semibold">Credentials</h2>
          <button onClick={addCredential} className="px-3 py-2 bg-emerald-600 rounded text-sm">
            Credential hinzufügen
          </button>
          <ul className="divide-y divide-slate-800 text-sm">
            {credentials.map((c) => (
              <li key={c.id} className="py-1 flex justify-between">
                <span>
                  {c.provider} · {c.name}
                </span>
                <span>v{c.version}</span>
              </li>
            ))}
          </ul>
        </div>
      )}

      {activeView === "queue" && (
        <div className="bg-slate-900 p-4 rounded space-y-2">
          <h2 className="font-semibold">Production Queue</h2>
          <ul className="divide-y divide-slate-800 text-sm">
            {jobs.map((j) => (
              <li key={j.id} className="py-1">
                <div className="flex justify-between">
                  <span>{j.type}</span>
                  <span>{j.status}</span>
                </div>
                {j.runs && (
                  <div className="text-xs text-slate-400">
                    {j.runs.map((r, idx) => (
                      <div key={idx}>
                        {r.status} · {r.message || ""}
                      </div>
                    ))}
                  </div>
                )}
              </li>
            ))}
          </ul>
        </div>
      )}

      {activeView === "youtube" && (
        <div className="bg-slate-900 p-4 rounded space-y-2">
          <h2 className="font-semibold">YouTube Tool</h2>
          <button onClick={transcribe} className="px-3 py-2 bg-blue-600 rounded text-sm">
            Transcribe (falls verfügbar)
          </button>
        </div>
      )}
    </div>
  );
}

export default App;
