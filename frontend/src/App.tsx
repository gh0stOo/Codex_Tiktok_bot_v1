import { useEffect, useMemo, useState } from "react";
import axios from "axios";
import "./index.css";

type Org = { id: string; name: string };
type Project = { 
  id: string; 
  name: string; 
  organization_id: string; 
  autopilot_enabled?: boolean;
  video_provider?: string | null;
  video_model_id?: string | null;
  video_credential_id?: string | null;
  video_generation_provider?: string | null;
  video_generation_model_id?: string | null;
  video_generation_credential_id?: string | null;
};
type Plan = { 
  id: string; 
  slot_date: string; 
  slot_index: number; 
  status: string; 
  approved: boolean; 
  locked: boolean;
  category?: string | null;
  topic?: string | null;
  script_content?: string | null;
  hook?: string | null;
  title?: string | null;
  cta?: string | null;
  visual_prompt?: string | null;
  lighting?: string | null;
  composition?: string | null;
  camera_angles?: string | null;
  visual_style?: string | null;
};
type CalendarSlot = { date: string; slots: Plan[]; dateObj?: Date };
type Metric = { metric: string; value: number; created_at: string };
type Credential = { id: string; provider: string; name: string; version: number };
type JobRun = { status: string; message?: string; created_at: string };
type Job = { 
  id: string; 
  type: string; 
  status: string; 
  created_at: string; 
  payload?: string | null;
  runs?: JobRun[] 
};
type VideoAsset = {
  id: string;
  plan_id?: string | null;
  project_id?: string | null;
  organization_id?: string | null;
  status: string;
  created_at?: string;
  publish_response?: string | null;
  signed_thumbnail_url?: string | null;
  signed_video_url?: string | null;
  video_path: string;
  thumbnail_path: string;
  transcript?: string | null;
  original_language?: string | null;
  translated_language?: string | null;
  voice_clone_model_id?: string | null;
  translation_provider?: string | null;
};
type UsageSnapshot = { [metric: string]: number };

const api = axios.create({ 
  baseURL: "/api",
  headers: {
    "Content-Type": "application/json"
  }
});

// Token-Refresh bei 401 Fehler
let refreshTokenPromise: Promise<{ access_token: string; refresh_token: string }> | null = null;

// Request Interceptor: Füge Token hinzu
api.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem("access_token");
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  (error) => Promise.reject(error)
);

// Response Interceptor: Automatisches Token-Refresh bei 401
api.interceptors.response.use(
  (response) => response,
  async (error) => {
    const originalRequest = error.config;
    
    // Wenn 401 und noch nicht retried
    if (error.response?.status === 401 && !originalRequest._retry) {
      originalRequest._retry = true;
      
      const refreshToken = localStorage.getItem("refresh_token");
      if (!refreshToken) {
        // Kein Refresh-Token vorhanden, zurück zum Login
        localStorage.removeItem("access_token");
        localStorage.removeItem("refresh_token");
        window.dispatchEvent(new CustomEvent('token-refresh-failed'));
        return Promise.reject(error);
      }
      
      // Verhindere mehrere gleichzeitige Refresh-Requests
      if (!refreshTokenPromise) {
        refreshTokenPromise = (async () => {
          const resp = await axios.post("/api/auth/refresh", { refresh_token: refreshToken });
          return resp.data;
        })();
      }
      
      try {
        const tokenData = await refreshTokenPromise;
        refreshTokenPromise = null;
        
        const newToken = tokenData.access_token;
        const newRefreshToken = tokenData.refresh_token;
        
        // Speichere neue Tokens
        localStorage.setItem("access_token", newToken);
        if (newRefreshToken) {
          localStorage.setItem("refresh_token", newRefreshToken);
        }
        
        // Update State (wenn App-Komponente verfügbar)
        // Trigger Custom Event für State-Update
        window.dispatchEvent(new CustomEvent('token-refreshed', { 
          detail: { access_token: newToken, refresh_token: newRefreshToken } 
        }));
        
        originalRequest.headers.Authorization = `Bearer ${newToken}`;
        
        // Retry original request
        return api(originalRequest);
      } catch (refreshError) {
        refreshTokenPromise = null;
        localStorage.removeItem("access_token");
        localStorage.removeItem("refresh_token");
        // Trigger Event für Logout
        window.dispatchEvent(new CustomEvent('token-refresh-failed'));
        return Promise.reject(refreshError);
      }
    }
    
    console.error("API Error:", error.response?.data || error.message);
    return Promise.reject(error);
  }
);

function App() {
  const [email, setEmail] = useState(localStorage.getItem("last_email") || "demo@codex.dev");
  const [password, setPassword] = useState("");
  const [token, setToken] = useState(localStorage.getItem("access_token") || "");
  const [refreshToken, setRefreshToken] = useState(localStorage.getItem("refresh_token") || "");
  const [orgs, setOrgs] = useState<Org[]>([]);
  const [orgId, setOrgId] = useState(localStorage.getItem("last_org_id") || "");
  const [projects, setProjects] = useState<Project[]>([]);
  const [projectId, setProjectId] = useState(localStorage.getItem("last_project_id") || "");
  const [calendar, setCalendar] = useState<CalendarSlot[]>([]);
  const [metrics, setMetrics] = useState<Metric[]>([]);
  const [credentials, setCredentials] = useState<Credential[]>([]);
  const [jobs, setJobs] = useState<Job[]>([]);
  const [jobStatusPolling, setJobStatusPolling] = useState<boolean>(false);
  const [queueFilter, setQueueFilter] = useState<"all" | "processing" | "queued" | "completed" | "failed">("all");
  const [libraryFilter, setLibraryFilter] = useState<"all" | "generated" | "transcribed" | "translated" | "published">("all");
  
  // YouTube Translation State
  const [translateMode, setTranslateMode] = useState<boolean>(false);
  const [translateTargetLanguage, setTranslateTargetLanguage] = useState<string>("de");
  const [voiceCloningProvider, setVoiceCloningProvider] = useState<string>("rask");
  const [voiceCloningModelId, setVoiceCloningModelId] = useState<string>("");
  const [voiceCloningCredentialId, setVoiceCloningCredentialId] = useState<string>("");
  const [voiceCloningModels, setVoiceCloningModels] = useState<Array<{id: string; name: string; provider: string; description?: string; cost_per_minute?: number; supported_languages?: string[]}>>([]);
  const [loadingVoiceModels, setLoadingVoiceModels] = useState<boolean>(false);
  const [assets, setAssets] = useState<VideoAsset[]>([]);
  const [usage, setUsage] = useState<UsageSnapshot>({});
  const [status, setStatus] = useState<string>("");
  const [activeView, setActiveView] = useState<
    "dashboard" | "calendar" | "library" | "analytics" | "credentials" | "queue" | "youtube"
  >("dashboard");
  const [autopilot, setAutopilot] = useState<boolean>(false);
  const [newProjectName, setNewProjectName] = useState<string>("");
  const [showCreateProject, setShowCreateProject] = useState<boolean>(false);
  const [newOrgName, setNewOrgName] = useState<string>("");
  const [showCreateOrg, setShowCreateOrg] = useState<boolean>(false);
  const [transcribeUrl, setTranscribeUrl] = useState<string>("");
  const [transcribeLanguage, setTranscribeLanguage] = useState<string>("auto");
  // Video-Generierungs-Einstellungen State (für Text-to-Video APIs)
  const [videoGenerationProvider, setVideoGenerationProvider] = useState<string>("falai");
  const [videoGenerationModelId, setVideoGenerationModelId] = useState<string>("");
  const [videoGenerationCredentialId, setVideoGenerationCredentialId] = useState<string>("");
  const [videoGenerationModels, setVideoGenerationModels] = useState<Array<{id: string; name: string; provider: string; description?: string; cost_per_minute?: number; pricing?: any; currency?: string; supports_video_generation?: boolean}>>([]);
  const [loadingVideoGenerationModels, setLoadingVideoGenerationModels] = useState<boolean>(false);
  const [apiProvider, setApiProvider] = useState<string>("openrouter");
  const [apiKey, setApiKey] = useState<string>("");
  const [selectedCredentialId, setSelectedCredentialId] = useState<string>("");
  const [availableModels, setAvailableModels] = useState<any[]>([]);
  const [selectedModel, setSelectedModel] = useState<string>("");
  const [loadingModels, setLoadingModels] = useState<boolean>(false);
  
  // Credentials Management
  const [newCredentialProvider, setNewCredentialProvider] = useState<string>("openrouter");
  const [newCredentialName, setNewCredentialName] = useState<string>("");
  const [newCredentialSecret, setNewCredentialSecret] = useState<string>("");
  const [showAddCredential, setShowAddCredential] = useState<boolean>(false);
  
  // Calendar/Content Plan Management
  const [selectedCategory, setSelectedCategory] = useState<string>("faceless_tiktok");
  const [contentTopic, setContentTopic] = useState<string>("");
  const [planFeedback, setPlanFeedback] = useState<string>("");
  const [selectedDay, setSelectedDay] = useState<string | null>(null);
  const [dayPlans, setDayPlans] = useState<Plan[]>([]);
  const [selectedPlanForScript, setSelectedPlanForScript] = useState<string | null>(null);
  const [scriptFeedback, setScriptFeedback] = useState<string>("");
  const [generatingPlan, setGeneratingPlan] = useState<boolean>(false);
  const [generatingScript, setGeneratingScript] = useState<boolean>(false);

  const headers = useMemo(() => (token ? { Authorization: `Bearer ${token}` } : {}), [token]);

  const login = async () => {
    if (!email.trim() || !password.trim()) {
      setStatus("Bitte Email und Passwort eingeben");
      return;
    }
    try {
      console.log("Login attempt:", email);
      const resp = await api.post("/auth/login", { email, password });
      console.log("Login successful");
      const newToken = resp.data.access_token;
      const newRefreshToken = resp.data.refresh_token;
      
      // Speichere Tokens und Email
      setToken(newToken);
      setRefreshToken(newRefreshToken);
      localStorage.setItem("access_token", newToken);
      localStorage.setItem("refresh_token", newRefreshToken);
      localStorage.setItem("last_email", email); // Speichere Email für nächstes Mal
      
      // Lade Organisationen direkt mit dem neuen Token
      await loadOrgs(newToken);
      setActiveView("dashboard");
      setStatus("Eingeloggt");
    } catch (e: any) {
      console.error("Login error:", e);
      const errorMsg = e?.response?.data?.detail || e?.message || "Login fehlgeschlagen";
      setStatus(`Login fehlgeschlagen: ${errorMsg}`);
    }
  };

  const loadOrgs = async (authToken?: string) => {
    try {
      const tokenToUse = authToken || token;
      const authHeaders = tokenToUse ? { Authorization: `Bearer ${tokenToUse}` } : {};
      console.log("Loading orgs with token:", tokenToUse ? "present" : "missing");
      // Verwende /orgs/ mit Slash am Ende, um Redirect zu vermeiden
      const o = await api.get("/orgs/", { headers: authHeaders });
      console.log("Orgs loaded:", o.data.length);
    setOrgs(o.data);
    if (o.data.length > 0) {
        // FIX: Verwende gespeicherte orgId, falls vorhanden und gültig
        const savedOrgId = localStorage.getItem("last_org_id");
        const orgToUse = savedOrgId && o.data.find(org => org.id === savedOrgId)
          ? savedOrgId
          : o.data[0].id;
        console.log("Setting orgId to:", orgToUse);
        setOrgId(orgToUse);
        localStorage.setItem("last_org_id", orgToUse);
        await loadProjects(orgToUse, authToken);
      } else {
        setStatus("Keine Organisationen gefunden. Bitte erstelle eine Organisation.");
        localStorage.removeItem("last_org_id");
        localStorage.removeItem("last_project_id");
      }
    } catch (e: any) {
      console.error("Load orgs error:", e);
      setStatus(e?.response?.data?.detail || "Fehler beim Laden der Organisationen");
    }
  };

  const loadProjects = async (oid: string, authToken?: string) => {
    try {
      const tokenToUse = authToken || token;
      const authHeaders = tokenToUse ? { Authorization: `Bearer ${tokenToUse}` } : {};
      console.log("Loading projects for org:", oid);
      const p = await api.get(`/projects/${oid}`, { headers: authHeaders });
      console.log("Projects loaded:", p.data.length);
    setProjects(p.data);
    if (p.data.length > 0) {
        // FIX: Verwende gespeichertes projectId, falls vorhanden und gültig
        const savedProjectId = localStorage.getItem("last_project_id");
        const projectToUse = savedProjectId && p.data.find(proj => proj.id === savedProjectId)
          ? savedProjectId
          : p.data[0].id;
        console.log("Setting projectId to:", projectToUse);
        setProjectId(projectToUse);
        localStorage.setItem("last_project_id", projectToUse);
        // FIX: Lade Video-Generierungs-Einstellungen aus dem Projekt
        const selectedProject = p.data.find(proj => proj.id === projectToUse) || p.data[0];
        if (selectedProject) {
          setVideoGenerationProvider(selectedProject.video_generation_provider || "falai");
          setVideoGenerationModelId(selectedProject.video_generation_model_id || "");
          setVideoGenerationCredentialId(selectedProject.video_generation_credential_id || "");
          // Lade Modelle für die ausgewählte Provider/Credential
          if (selectedProject.video_generation_provider || selectedProject.video_generation_credential_id) {
            loadVideoGenerationModels(selectedProject.video_generation_provider || "falai", selectedProject.video_generation_credential_id || "", oid);
          }
        }
        await refreshData(projectToUse, oid, authToken);
        setStatus(`Projekt "${selectedProject.name}" ausgewählt`);
      } else {
        setStatus("Keine Projekte gefunden. Bitte erstelle ein Projekt.");
        localStorage.removeItem("last_project_id");
      }
    } catch (e: any) {
      console.error("Load projects error:", e);
      setStatus(e?.response?.data?.detail || "Fehler beim Laden der Projekte");
    }
  };

  const createProject = async () => {
    if (!orgId) {
      setStatus("Bitte wähle zuerst eine Organisation aus");
      return;
    }
    if (!newProjectName.trim()) {
      setStatus("Bitte gib einen Projektnamen ein");
      return;
    }
    try {
      const resp = await api.post(
        `/projects/${orgId}`,
        { name: newProjectName.trim(), autopilot_enabled: false },
        { headers }
      );
      const newProject = resp.data;
      setNewProjectName("");
      setShowCreateProject(false);
      // FIX: Wähle das neu erstellte Projekt automatisch aus
      setProjectId(newProject.id);
      localStorage.setItem("last_project_id", newProject.id);
      await loadProjects(orgId);
      setStatus(`Projekt "${newProject.name}" erstellt und ausgewählt`);
    } catch (e: any) {
      console.error("Create project error:", e);
      setStatus(e?.response?.data?.detail || "Fehler beim Erstellen des Projekts");
    }
  };

  const createOrg = async () => {
    if (!newOrgName.trim()) {
      setStatus("Bitte gib einen Organisationsnamen ein");
      return;
    }
    try {
      const resp = await api.post("/orgs/", { name: newOrgName.trim() }, { headers });
      const newOrg = resp.data;
      setNewOrgName("");
      setShowCreateOrg(false);
      // FIX: Wähle die neu erstellte Organisation automatisch aus
      setOrgId(newOrg.id);
      localStorage.setItem("last_org_id", newOrg.id);
      localStorage.removeItem("last_project_id"); // Lösche projectId wenn neue Org erstellt wird
      setProjectId("");
      await loadOrgs();
      setStatus(`Organisation "${newOrg.name}" erstellt und ausgewählt`);
    } catch (e: any) {
      console.error("Create org error:", e);
      setStatus(e?.response?.data?.detail || "Fehler beim Erstellen der Organisation");
    }
  };

  const refreshData = async (pid: string, oid: string, authToken?: string) => {
    if (!pid || !oid) return;
    try {
      const tokenToUse = authToken || token;
      const authHeaders = tokenToUse ? { Authorization: `Bearer ${tokenToUse}` } : {};
    const [cal, metricsResp, creds, jobsResp, assetsResp, usageResp] = await Promise.all([
        api.get(`/plans/calendar/${pid}`, { headers: authHeaders }),
        api.get(`/analytics/metrics/${pid}`, { headers: authHeaders }),
        api.get(`/credentials/${oid}`, { headers: authHeaders }),
        api.get(`/jobs/${pid}`, { headers: authHeaders }),
        api.get(`/video/assets/project/${pid}`, { headers: authHeaders }),
        api.get(`/usage/${oid}`, { headers: authHeaders }),
      ]);
      // FIX: Sortiere Kalender nach Datum und filtere/graue vergangene Tage aus
      const today = new Date();
      today.setHours(0, 0, 0, 0);
      
      const sortedCalendar = cal.data
        .map(slot => ({
          ...slot,
          dateObj: new Date(slot.date),
        }))
        .sort((a, b) => a.dateObj.getTime() - b.dateObj.getTime());
      
      setCalendar(sortedCalendar);
    setMetrics(metricsResp.data.metrics || []);
      
      // FIX: Scrolle automatisch zu heute nach dem Laden
      setTimeout(() => {
        const today = new Date();
        today.setHours(0, 0, 0, 0);
        const todayElement = document.querySelector(`[data-date="${today.toISOString().split('T')[0]}"]`);
        if (todayElement) {
          todayElement.scrollIntoView({ behavior: 'smooth', block: 'center' });
        }
      }, 100);
    setCredentials(creds.data);
    setJobs(jobsResp.data.jobs || []);
    setAssets(assetsResp.data || []);
    setUsage(usageResp.data.usage || {});
    const proj = projects.find((p) => p.id === pid);
    if (proj && typeof proj.autopilot_enabled !== "undefined") {
      setAutopilot(!!proj.autopilot_enabled);
      }
    } catch (e: any) {
      console.error("Refresh data error:", e);
      setStatus(e?.response?.data?.detail || "Fehler beim Laden der Daten");
    }
  };

  useEffect(() => {
    // Versuche Auto-Login mit gespeichertem Token
    const storedToken = localStorage.getItem("access_token");
    const storedRefreshToken = localStorage.getItem("refresh_token");
    
    if (storedToken) {
      setToken(storedToken);
      if (storedRefreshToken) {
        setRefreshToken(storedRefreshToken);
      }
      // Setze API-Header
      api.defaults.headers.common["Authorization"] = `Bearer ${storedToken}`;
      // Versuche Daten zu laden - bei 401 wird automatisch Refresh gemacht
      loadOrgs(storedToken).catch((e) => {
        // Wenn Refresh auch fehlschlägt, zeige Meldung (kein automatischer Login mit Demo-Credentials)
        if (!storedRefreshToken) {
          setStatus("Session abgelaufen. Bitte erneut einloggen.");
        }
      });
    } else {
      // Kein gespeicherter Token - zeige Login-Formular, aber logge nicht automatisch ein
      setStatus("Bitte einloggen");
    }
    
    // Listener für Token-Refresh Events
    const handleTokenRefresh = (event: CustomEvent) => {
      const { access_token, refresh_token } = event.detail;
      setToken(access_token);
      if (refresh_token) {
        setRefreshToken(refresh_token);
      }
      // Aktualisiere API-Header
      api.defaults.headers.common["Authorization"] = `Bearer ${access_token}`;
    };
    
    const handleTokenRefreshFailed = () => {
      setToken("");
      setRefreshToken("");
      setOrgs([]);
      setProjects([]);
      // Lösche Tokens, aber behalte Email
      localStorage.removeItem("access_token");
      localStorage.removeItem("refresh_token");
      setStatus("Session abgelaufen. Bitte erneut einloggen.");
    };
    
    window.addEventListener('token-refreshed', handleTokenRefresh as EventListener);
    window.addEventListener('token-refresh-failed', handleTokenRefreshFailed);
    
    return () => {
      window.removeEventListener('token-refreshed', handleTokenRefresh as EventListener);
      window.removeEventListener('token-refresh-failed', handleTokenRefreshFailed);
    };
  }, []);

  // Job-Status Polling
  useEffect(() => {
    if (!jobStatusPolling || !projectId) return;
    
    const interval = setInterval(async () => {
      try {
        const jobsResp = await api.get(`/jobs/${projectId}`, { headers });
        const currentJobs = jobsResp.data.jobs || [];
        setJobs(currentJobs);
        
        // Prüfe ob alle Jobs abgeschlossen sind
        const activeJobs = currentJobs.filter((j: Job) => 
          j.status === "pending" || j.status === "in_progress"
        );
        if (activeJobs.length === 0) {
          stopJobStatusPolling();
          // Lade auch Assets neu
          await refreshData(projectId, orgId);
        }
      } catch (e) {
        console.error("Job status polling error:", e);
      }
    }, 2000); // Alle 2 Sekunden aktualisieren
    
    return () => clearInterval(interval);
  }, [jobStatusPolling, projectId, orgId, headers]);

  const generatePlanMonth = async () => {
    if (!projectId) {
      setStatus("Bitte wähle zuerst ein Projekt aus");
      return;
    }
    try {
    await api.post(`/plans/generate/${projectId}`, null, { headers });
    await refreshData(projectId, orgId);
    setStatus("Monatsplan erstellt");
    } catch (e: any) {
      console.error("Generate plan error:", e);
      setStatus(e?.response?.data?.detail || "Fehler beim Erstellen des Plans");
    }
  };
  
  const generateContentPlan = async () => {
    if (!projectId) {
      setStatus("Bitte wähle zuerst ein Projekt aus");
      return;
    }
    if (!contentTopic.trim()) {
      setStatus("Bitte gib ein Thema ein");
      return;
    }
    setGeneratingPlan(true);
    try {
      await api.post(
        `/plans/content-plan/${projectId}`,
        {
          category: selectedCategory,
          topic: contentTopic.trim(),
          feedback: planFeedback.trim() || null
        },
        { headers }
      );
      await refreshData(projectId, orgId);
      setStatus("Content-Plan generiert");
      setPlanFeedback("");
    } catch (e: any) {
      console.error("Generate content plan error:", e);
      setStatus(e?.response?.data?.detail || "Fehler beim Generieren des Content-Plans");
    } finally {
      setGeneratingPlan(false);
    }
  };
  
  const loadDayPlans = async (dayDate: string) => {
    if (!projectId) return;
    try {
      const resp = await api.get(`/plans/day/${projectId}/${dayDate}`, { headers });
      setDayPlans(resp.data);
      setSelectedDay(dayDate);
    } catch (e: any) {
      console.error("Load day plans error:", e);
      setStatus(e?.response?.data?.detail || "Fehler beim Laden der Tages-Plans");
    }
  };
  
  const generateScript = async (planId: string, feedback?: string) => {
    setGeneratingScript(true);
    try {
      await api.post(
        `/plans/generate-script/${planId}`,
        {
          plan_id: planId,
          feedback: feedback || null
        },
        { headers }
      );
      if (selectedDay) {
        await loadDayPlans(selectedDay);
      }
    await refreshData(projectId, orgId);
      setStatus("Script generiert");
      setScriptFeedback("");
      setSelectedPlanForScript(null);
    } catch (e: any) {
      console.error("Generate script error:", e);
      setStatus(e?.response?.data?.detail || "Fehler beim Generieren des Scripts");
    } finally {
      setGeneratingScript(false);
    }
  };
  
  const generateAllVideosForDay = async (dayDate: string) => {
    if (!projectId) return;
    try {
      const resp = await api.get(`/plans/day/${projectId}/${dayDate}`, { headers });
      const plans = resp.data;
      for (const plan of plans) {
        if (plan.script_content) {
          await generateAssets(plan.id);
        }
      }
      setStatus(`Video-Generierung für ${dayDate} gestartet`);
      await refreshData(projectId, orgId);
    } catch (e: any) {
      console.error("Generate all videos for day error:", e);
      setStatus(e?.response?.data?.detail || "Fehler beim Generieren der Videos");
    }
  };
  
  const generateAllVideos = async () => {
    if (!projectId) return;
    try {
      const resp = await api.get(`/plans/calendar/${projectId}`, { headers });
      const calendarSlots = resp.data;
      let count = 0;
      for (const slot of calendarSlots) {
        for (const plan of slot.slots) {
          if (plan.script_content) {
            await generateAssets(plan.id);
            count++;
            await new Promise(resolve => setTimeout(resolve, 100));
          }
        }
      }
      setStatus(`${count} Video-Generierungen gestartet`);
      await refreshData(projectId, orgId);
    } catch (e: any) {
      console.error("Generate all videos error:", e);
      setStatus(e?.response?.data?.detail || "Fehler beim Generieren aller Videos");
    }
  };

  const generateAssets = async (planId: string) => {
    if (!projectId) {
      setStatus("Bitte wähle zuerst ein Projekt aus");
      return;
    }
    try {
      const resp = await api.post(`/video/generate/${projectId}/${planId}`, null, { headers });
      setStatus("Video-Generierung gestartet...");
      // Starte Polling für Job-Status
      if (resp.data.job_id) {
        startJobStatusPolling();
      }
      await refreshData(projectId, orgId);
    } catch (e: any) {
      console.error("Generate assets error:", e);
      setStatus(e?.response?.data?.detail || "Fehler beim Generieren der Assets");
    }
  };

  const startJobStatusPolling = () => {
    if (jobStatusPolling) return; // Bereits aktiv
    setJobStatusPolling(true);
  };

  const stopJobStatusPolling = () => {
    setJobStatusPolling(false);
  };

  const publishNow = async (assetId: string) => {
    try {
    await api.post(`/video/publish/${assetId}`, { use_stored_token: true }, { headers });
    setStatus("Publish-Job gestartet");
    await refreshData(projectId, orgId);
    } catch (e: any) {
      console.error("Publish error:", e);
      setStatus(e?.response?.data?.detail || "Fehler beim Publishen");
    }
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
    if (!orgId) {
      setStatus("Bitte wähle zuerst eine Organisation aus");
      return;
    }
    if (!newCredentialName.trim() || !newCredentialSecret.trim()) {
      setStatus("Bitte gib Name und Secret ein");
      return;
    }
    try {
    await api.post(
      `/credentials/${orgId}`,
        { 
          provider: newCredentialProvider, 
          name: newCredentialName.trim(), 
          secret: newCredentialSecret.trim() 
        }
      );
      setNewCredentialName("");
      setNewCredentialSecret("");
      setShowAddCredential(false);
    await refreshData(projectId, orgId);
      setStatus("Credential hinzugefügt");
    } catch (e: any) {
      console.error("Add credential error:", e);
      setStatus(e?.response?.data?.detail || "Fehler beim Hinzufügen des Credentials");
    }
  };
  
  // Lade gespeicherten API-Key für Provider
  const loadStoredApiKey = (provider: string) => {
    const cred = credentials.find(c => c.provider === provider);
    if (cred) {
      // API-Key wird vom Backend nicht zurückgegeben (Sicherheit)
      // Wir müssen den User fragen oder einen anderen Weg finden
      return "";
    }
    return "";
  };

  const connectTikTok = async () => {
    if (!orgId) {
      setStatus("Bitte wähle zuerst eine Organisation aus");
      return;
    }
    try {
    const start = await api.get(`/tiktok/oauth/start?org_id=${orgId}`, { headers });
    setStatus("TikTok OAuth URL bereit: " + start.data.redirect_url);
    window.open(start.data.redirect_url, "_blank");
    } catch (e: any) {
      console.error("Connect TikTok error:", e);
      setStatus(e?.response?.data?.detail || "Fehler beim Verbinden mit TikTok");
    }
  };

  const logout = async () => {
    try {
      // Versuche Logout auf Server
      await api.post("/auth/logout");
    } catch (e) {
      console.error("Logout error:", e);
    }
    
    // Lösche lokale Tokens (aber behalte Email für nächstes Mal)
    setToken("");
    setRefreshToken("");
    localStorage.removeItem("access_token");
    localStorage.removeItem("refresh_token");
    // FIX: Lösche auch gespeicherte Org/Project IDs beim Logout
    localStorage.removeItem("last_org_id");
    localStorage.removeItem("last_project_id");
    // Email bleibt gespeichert, damit der User sie nicht erneut eingeben muss
    
    setProjects([]);
    setProjectId("");
    setOrgs([]);
    setOrgId("");
    setCalendar([]);
    setMetrics([]);
    setCredentials([]);
    setJobs([]);
    setAssets([]);
    setPassword(""); // Lösche Passwort-Feld
    setStatus("Abgemeldet");
  };

  const refreshMetrics = async () => {
    if (!projectId) {
      setStatus("Bitte wähle zuerst ein Projekt aus");
      return;
    }
    try {
    await api.post(`/analytics/metrics/${projectId}/refresh`, null, { headers });
    setStatus("Metrics-Job gestartet");
    await refreshData(projectId, orgId);
    } catch (e: any) {
      console.error("Refresh metrics error:", e);
      setStatus(e?.response?.data?.detail || "Fehler beim Aktualisieren der Metrics");
    }
  };

  const loadModels = async () => {
    // FIX: Unterstütze sowohl API-Key als auch Credentials
    if ((!apiKey.trim() && !selectedCredentialId) || !apiProvider) {
      setAvailableModels([]);
      setSelectedModel("");
      return;
    }
    
    if (selectedCredentialId && !orgId) {
      setStatus("Bitte wähle eine Organisation aus, um gespeicherte Credentials zu verwenden");
      return;
    }
    
    setLoadingModels(true);
    try {
      const authHeaders = token ? { Authorization: `Bearer ${token}` } : {};
      const payload: any = {
        provider: apiProvider,
      };
      
      if (selectedCredentialId && orgId) {
        payload.credential_id = selectedCredentialId;
        payload.org_id = orgId;
      } else {
        payload.api_key = apiKey.trim();
      }
      
      const resp = await api.post(
        "/youtube/models",
        payload,
        { headers: authHeaders }
      );
      setAvailableModels(resp.data);
      if (resp.data.length > 0 && !selectedModel) {
        setSelectedModel(resp.data[0].id);
      }
      setStatus(`${resp.data.length} Modelle gefunden`);
    } catch (e: any) {
      console.error("Load models error:", e);
      setAvailableModels([]);
      setSelectedModel("");
      setStatus(e?.response?.data?.detail || "Fehler beim Laden der Modelle. Prüfe deinen API-Key oder Credential.");
    } finally {
      setLoadingModels(false);
    }
  };

  // Lade Video-Generierungs-Modelle (Text-to-Video APIs)
  const loadVideoGenerationModels = async (provider: string, credentialId: string, orgId: string) => {
    if (!orgId) return;
    try {
      setLoadingVideoGenerationModels(true);
      const req: any = {
        provider: provider || "falai",
      };
      if (credentialId && orgId) {
        req.credential_id = credentialId;
        req.org_id = orgId;
      }
      const resp = await api.post("/video/generation-models", req, { headers });
      const models = resp.data || [];
      setVideoGenerationModels(models);
      
      // Automatisch erstes Modell auswählen, wenn noch keins ausgewählt
      if (!videoGenerationModelId && models.length > 0) {
        setVideoGenerationModelId(models[0].id);
      }
    } catch (e: any) {
      console.error("Load video generation models error:", e);
      setVideoGenerationModels([]);
      setStatus(e?.response?.data?.detail || "Fehler beim Laden der Video-Generierungs-Modelle");
    } finally {
      setLoadingVideoGenerationModels(false);
    }
  };

  // Speichere Video-Generierungs-Einstellungen (Text-to-Video APIs)
  const saveVideoGenerationSettings = async () => {
    if (!projectId) {
      setStatus("Bitte wähle zuerst ein Projekt aus");
      return;
    }
    try {
      const params = new URLSearchParams();
      if (videoGenerationProvider) params.append("video_generation_provider", videoGenerationProvider);
      if (videoGenerationModelId) params.append("video_generation_model_id", videoGenerationModelId);
      if (videoGenerationCredentialId !== undefined) {
        params.append("video_generation_credential_id", videoGenerationCredentialId || "");
      }
      
      await api.put(`/projects/video-generation-settings/${projectId}?${params.toString()}`, {}, { headers });
      setStatus("Video-Generierungs-Einstellungen gespeichert");
      // Aktualisiere Projekte
      await loadProjects(orgId);
    } catch (e: any) {
      console.error("Save video generation settings error:", e);
      setStatus(e?.response?.data?.detail || "Fehler beim Speichern der Video-Generierungs-Einstellungen");
    }
  };

  const transcribe = async () => {
    if (!transcribeUrl.trim()) {
      setStatus("Bitte gib eine YouTube URL ein");
      return;
    }
    if (!selectedModel) {
      setStatus("Bitte wähle ein Modell aus");
      return;
    }
    if (!apiKey.trim() && !selectedCredentialId) {
      setStatus("Bitte gib einen API-Key ein oder wähle ein gespeichertes Credential");
      return;
    }
    if (selectedCredentialId && !orgId) {
      setStatus("Bitte wähle eine Organisation aus, um gespeicherte Credentials zu verwenden");
      return;
    }
    try {
      const payload: any = {
        url: transcribeUrl.trim(),
        target_language: transcribeLanguage,
        provider: apiProvider,
        model_id: selectedModel,
      };
      
      if (selectedCredentialId && orgId) {
        payload.credential_id = selectedCredentialId;
        payload.org_id = orgId;
      } else {
        payload.api_key = apiKey.trim();
      }
      
      const resp = await api.post(
        `/youtube/transcribe`,
        payload,
        { headers }
      );
      const model = availableModels.find((m) => m.id === selectedModel);
      const costInfo = model && model.cost_per_minute
        ? `Geschätzte Kosten: ${model.currency} ${resp.data.estimated_cost?.toFixed(4) || "0.0000"}`
        : "";
      setStatus(`${resp.data.message || "Transcription gestartet"} ${costInfo}`);
      
      // Lade Jobs neu, damit der neue Transcription-Job in der Queue sichtbar ist
      if (projectId) {
        try {
          const jobsResp = await api.get(`/jobs/${projectId}`, { headers });
          setJobs(jobsResp.data.jobs || []);
          // Starte Polling, falls noch nicht aktiv
          if (!jobStatusPolling) {
            startJobStatusPolling();
          }
        } catch (e: any) {
          console.error("Load jobs error:", e);
        }
      }
    } catch (e: any) {
      console.error("Transcribe error:", e);
      setStatus(e?.response?.data?.detail || "Fehler bei der Transcription");
    }
  };

  const translateVideo = async () => {
    if (!transcribeUrl.trim()) {
      setStatus("Bitte gib eine YouTube URL ein");
      return;
    }
    if (!voiceCloningModelId) {
      setStatus("Bitte wähle ein Voice Cloning Modell aus");
      return;
    }
    if (!voiceCloningCredentialId) {
      setStatus("Bitte wähle ein gespeichertes Credential für Voice Cloning aus");
      return;
    }
    if (!orgId) {
      setStatus("Bitte wähle eine Organisation aus");
      return;
    }
    if (!voiceCloningProvider) {
      setStatus("Bitte wähle einen Voice Cloning Provider aus");
      return;
    }
    try {
      const payload: any = {
        url: transcribeUrl.trim(),
        target_language: translateTargetLanguage,
        voice_cloning_provider: voiceCloningProvider,
        voice_cloning_model_id: voiceCloningModelId,
        credential_id: voiceCloningCredentialId,
        org_id: orgId,
      };
      
      const resp = await api.post(
        `/youtube/translate`,
        payload,
        { headers }
      );
      setStatus(resp.data.message || "Video-Übersetzung gestartet");
      
      // Lade Jobs neu, damit der neue Translation-Job in der Queue sichtbar ist
      if (projectId) {
        try {
          const jobsResp = await api.get(`/jobs/${projectId}`, { headers });
          setJobs(jobsResp.data.jobs || []);
          // Starte Polling, falls noch nicht aktiv
          if (!jobStatusPolling) {
            startJobStatusPolling();
          }
        } catch (e: any) {
          console.error("Load jobs error:", e);
        }
      }
    } catch (e: any) {
      console.error("Translate video error:", e);
      setStatus(e?.response?.data?.detail || "Fehler bei der Video-Übersetzung");
    }
  };

  useEffect(() => {
    // FIX: Lade Modelle wenn API-Key, Credential oder Provider sich ändern
    if ((apiKey.trim() || selectedCredentialId) && apiProvider && (!selectedCredentialId || orgId)) {
      const timeoutId = setTimeout(() => {
        loadModels();
      }, 500); // Debounce
      return () => clearTimeout(timeoutId);
    } else {
      setAvailableModels([]);
      setSelectedModel("");
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [apiKey, apiProvider, selectedCredentialId, orgId]);

  const approvePlan = async (planId: string) => {
    try {
    await api.post(`/plans/approve/${planId}`, null, { headers });
    await refreshData(projectId, orgId);
      setStatus("Plan genehmigt");
    } catch (e: any) {
      console.error("Approve plan error:", e);
      setStatus(e?.response?.data?.detail || "Fehler beim Genehmigen des Plans");
    }
  };

  const lockPlan = async (planId: string) => {
    try {
    await api.post(`/plans/lock/${planId}`, null, { headers });
    await refreshData(projectId, orgId);
      setStatus("Plan gesperrt");
    } catch (e: any) {
      console.error("Lock plan error:", e);
      setStatus(e?.response?.data?.detail || "Fehler beim Sperren des Plans");
    }
  };

  const toggleAutopilot = async (enabled: boolean) => {
    if (!projectId) {
      setStatus("Bitte wähle zuerst ein Projekt aus");
      return;
    }
    try {
    await api.post(`/projects/toggle/${projectId}?enabled=${enabled}`, null, { headers });
    setAutopilot(enabled);
      setStatus(`Autopilot ${enabled ? "aktiviert" : "deaktiviert"}`);
    } catch (e: any) {
      console.error("Toggle autopilot error:", e);
      setStatus(e?.response?.data?.detail || "Fehler beim Umschalten des Autopilots");
    }
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
            <div className="flex gap-2 items-center flex-wrap">
              <select
                className="bg-slate-800 px-2 py-1 rounded text-sm"
                value={orgId}
                onChange={(e) => {
                  const newOrgId = e.target.value;
                  setOrgId(newOrgId);
                  localStorage.setItem("last_org_id", newOrgId);
                  // Lösche projectId wenn Org wechselt
                  localStorage.removeItem("last_project_id");
                  setProjectId("");
                  loadProjects(newOrgId);
                }}
                disabled={orgs.length === 0}
              >
                {orgs.length === 0 ? (
                  <option value="">Keine Organisationen verfügbar</option>
                ) : (
                  orgs.map((o) => (
                  <option key={o.id} value={o.id}>
                    {o.name}
                  </option>
                  ))
                )}
              </select>
              <button
                className="px-3 py-1 bg-green-600 rounded text-sm"
                onClick={() => setShowCreateOrg(!showCreateOrg)}
              >
                {showCreateOrg ? "Abbrechen" : "+ Org"}
              </button>
              {showCreateOrg && (
                <>
                  <input
                    className="bg-slate-800 px-2 py-1 rounded text-sm w-40"
                    placeholder="Org-Name"
                    value={newOrgName}
                    onChange={(e) => setNewOrgName(e.target.value)}
                    onKeyPress={(e) => e.key === "Enter" && createOrg()}
                  />
                  <button className="px-3 py-1 bg-emerald-600 rounded text-sm" onClick={createOrg}>
                    Erstellen
                  </button>
                </>
              )}
            </div>
            <div className="flex gap-2 items-center flex-wrap">
              <select
                className="bg-slate-800 px-2 py-1 rounded text-sm"
                value={projectId}
                onChange={(e) => {
                  const newProjectId = e.target.value;
                  setProjectId(newProjectId);
                  localStorage.setItem("last_project_id", newProjectId);
                  refreshData(newProjectId, orgId);
                }}
                disabled={projects.length === 0}
              >
                {projects.length === 0 ? (
                  <option value="">Keine Projekte verfügbar</option>
                ) : (
                  projects.map((p) => (
                  <option key={p.id} value={p.id}>
                    {p.name}
                  </option>
                  ))
                )}
              </select>
              <button className="px-3 py-1 bg-blue-600 rounded text-sm" onClick={generatePlanMonth}>
                30x3 Plan
              </button>
              <button className="px-3 py-1 bg-slate-700 rounded text-sm" onClick={() => refreshData(projectId, orgId)}>
                Refresh
              </button>
            </div>
            <div className="flex gap-2 items-center">
              <button
                className="px-3 py-1 bg-green-600 rounded text-sm"
                onClick={() => setShowCreateProject(!showCreateProject)}
                disabled={!orgId}
              >
                {showCreateProject ? "Abbrechen" : "+ Projekt erstellen"}
              </button>
              {showCreateProject && (
                <>
                  <input
                    className="bg-slate-800 px-2 py-1 rounded text-sm w-48"
                    placeholder="Projektname"
                    value={newProjectName}
                    onChange={(e) => setNewProjectName(e.target.value)}
                    onKeyPress={(e) => e.key === "Enter" && createProject()}
                  />
                  <button className="px-3 py-1 bg-emerald-600 rounded text-sm" onClick={createProject}>
                    Erstellen
                  </button>
                </>
              )}
            </div>
            <div className="text-xs text-slate-400">
              Token: {token ? "aktiv" : "-"} | 
              Org: {orgId ? orgs.find(o => o.id === orgId)?.name || orgId : "nicht ausgewählt"} | 
              Project: {projectId ? projects.find(p => p.id === projectId)?.name || projectId : "nicht ausgewählt"}
            </div>
          </div>
          <div className="bg-slate-900 p-4 rounded space-y-3">
            <h2 className="font-semibold">TikTok Connect</h2>
            <p className="text-sm text-slate-300">OAuth starten; Callback im Backend. Danach kann Publish genutzt werden.</p>
            <button className="px-3 py-1 bg-purple-600 rounded text-sm" onClick={connectTikTok}>
              TikTok verbinden
            </button>
            <p className="text-xs text-slate-400">Hinweis: Tokens werden verschlüsselt gespeichert.</p>
          </div>
          {/* Video-Generierungs-Einstellungen */}
          {projectId && (
            <>
              {/* Script-Generierung (Info-only, fest GPT-4.0 Mini) */}
              <div className="bg-slate-900 p-4 rounded space-y-3">
                <h2 className="font-semibold">Script-Generierung</h2>
                <div className="bg-slate-800 p-3 rounded text-sm">
                  <div className="text-slate-300">
                    <strong>Modell:</strong> GPT-4.0 Mini (fest, nicht auswählbar)
                  </div>
                  <div className="text-slate-400 text-xs mt-1">
                    Script-Generierung verwendet immer GPT-4.0 Mini über OpenRouter für konsistente, hochwertige Texte.
                  </div>
                </div>
              </div>
              
              {/* Video-Generierung (auswählbar, Text-to-Video APIs) */}
              <div className="bg-slate-900 p-4 rounded space-y-3">
                <h2 className="font-semibold">Video-Generierung (Text-to-Video)</h2>
                <div className="space-y-3">
                  <div className="flex gap-2 items-center flex-wrap">
                    <label className="text-sm text-slate-300">API Provider:</label>
                    <select
                      className="bg-slate-800 px-2 py-1 rounded text-sm"
                      value={videoGenerationProvider}
                      onChange={(e) => {
                        setVideoGenerationProvider(e.target.value);
                        setVideoGenerationModelId("");
                        setVideoGenerationModels([]);
                        // Lade Modelle für neuen Provider
                        if (e.target.value && orgId) {
                          loadVideoGenerationModels(e.target.value, videoGenerationCredentialId, orgId);
                        }
                      }}
                    >
                      <option value="falai">Fal.ai (Text-to-Video APIs)</option>
                    </select>
                  </div>
                  <div className="flex gap-2 items-center flex-wrap">
                    <label className="text-sm text-slate-300">Credential:</label>
                    <select
                      className="bg-slate-800 px-2 py-1 rounded text-sm"
                      value={videoGenerationCredentialId}
                      onChange={(e) => {
                        setVideoGenerationCredentialId(e.target.value);
                        // Lade Modelle mit neuem Credential
                        if (videoGenerationProvider && orgId) {
                          loadVideoGenerationModels(videoGenerationProvider, e.target.value, orgId);
                        }
                      }}
                    >
                      <option value="">Kein Credential (Global)</option>
                      {credentials
                        .filter(c => c.provider === videoGenerationProvider || (videoGenerationProvider === "falai" && c.provider === "falai"))
                        .map(c => (
                          <option key={c.id} value={c.id}>
                            {c.name} ({c.provider})
                          </option>
                        ))}
                    </select>
                    <button
                      className="px-3 py-1 bg-blue-600 rounded text-sm"
                      onClick={() => {
                        if (videoGenerationProvider && orgId) {
                          loadVideoGenerationModels(videoGenerationProvider, videoGenerationCredentialId, orgId);
                        }
                      }}
                      disabled={loadingVideoGenerationModels || !videoGenerationProvider || !orgId}
                    >
                      {loadingVideoGenerationModels ? "Lädt..." : "Modelle laden"}
                    </button>
                  </div>
                  <div className="flex gap-2 items-center flex-wrap">
                    <label className="text-sm text-slate-300">Video-Modell:</label>
                    <select
                      className="bg-slate-800 px-2 py-1 rounded text-sm flex-1 min-w-48"
                      value={videoGenerationModelId}
                      onChange={(e) => setVideoGenerationModelId(e.target.value)}
                      disabled={videoGenerationModels.length === 0}
                    >
                      {videoGenerationModels.length === 0 ? (
                        <option value="">Bitte zuerst Modelle laden</option>
                      ) : (
                        videoGenerationModels.map(m => {
                          let priceInfo = "";
                          if (m.cost_per_minute) {
                            priceInfo = ` - $${m.cost_per_minute.toFixed(2)}/Minute`;
                          } else if (m.pricing?.per_minute) {
                            priceInfo = ` - ${m.pricing.per_minute}/Minute`;
                          } else if (m.pricing?.per_second) {
                            priceInfo = ` - ${m.pricing.per_second}/Sekunde`;
                          }
                          return (
                            <option key={m.id} value={m.id}>
                              {m.name}{priceInfo}
                            </option>
                          );
                        })
                      )}
                    </select>
                    {videoGenerationModelId && videoGenerationModels.length > 0 && (() => {
                      const model = videoGenerationModels.find(m => m.id === videoGenerationModelId);
                      if (!model) return null;
                      return (
                        <div className="bg-slate-800 p-3 rounded text-xs mt-2 space-y-1">
                          {model.description && (
                            <div className="text-slate-300 mb-1">{model.description}</div>
                          )}
                          {model.cost_per_minute ? (
                            <div className="text-slate-300">
                              <strong>Kosten:</strong> ${model.cost_per_minute.toFixed(2)} pro Minute generiertes Video ({model.currency || "USD"})
                              {model.pricing?.note && (
                                <div className="text-slate-400 text-xs mt-1">{model.pricing.note}</div>
                              )}
                            </div>
                          ) : model.pricing?.per_minute ? (
                            <div className="text-slate-300">
                              <strong>Kosten:</strong> {model.pricing.per_minute} pro Minute generiertes Video ({model.currency || "USD"})
                            </div>
                          ) : model.pricing?.per_second ? (
                            <div className="text-slate-300">
                              <strong>Kosten:</strong> {model.pricing.per_second} pro Sekunde generiertes Video ({model.currency || "USD"})
                            </div>
                          ) : null}
                        </div>
                      );
                    })()}
                  </div>
                  <button
                    className="px-3 py-1 bg-emerald-600 rounded text-sm"
                    onClick={saveVideoGenerationSettings}
                    disabled={!videoGenerationProvider || !videoGenerationModelId}
                  >
                    Einstellungen speichern
                  </button>
                  <p className="text-xs text-slate-400">
                    Diese Einstellungen werden für die <strong>Video-Generierung</strong> verwendet (Text-zu-Video APIs).
                    <br />
                    <strong>Hinweis:</strong> Script-Generierung verwendet immer GPT-4.0 Mini (fest, nicht auswählbar).
                  </p>
                </div>
              </div>
            </>
          )}
        </div>
      )}

      {activeView === "calendar" && (
        <div className="bg-slate-900 p-4 rounded space-y-4">
          {!selectedDay ? (
            <>
              {/* Content-Plan-Generierung */}
              <div className="bg-slate-800 p-4 rounded space-y-3">
                <h2 className="font-semibold">Content-Plan erstellen</h2>
                <div className="space-y-3">
                  <div>
                    <label className="text-sm text-slate-300 block mb-1">Kategorie</label>
                    <select
                      className="bg-slate-700 px-3 py-2 rounded text-sm w-full"
                      value={selectedCategory}
                      onChange={(e) => setSelectedCategory(e.target.value)}
                    >
                      <option value="faceless_tiktok">Faceless TikTok</option>
                    </select>
                  </div>
                  <div>
                    <label className="text-sm text-slate-300 block mb-1">Thema</label>
                    <input
                      className="bg-slate-700 px-3 py-2 rounded text-sm w-full"
                      placeholder="z.B. Productivity Tips, Motivation, etc."
                      value={contentTopic}
                      onChange={(e) => setContentTopic(e.target.value)}
                    />
                  </div>
                  <div>
                    <label className="text-sm text-slate-300 block mb-1">Feedback/Anpassungen (optional)</label>
                    <textarea
                      className="bg-slate-700 px-3 py-2 rounded text-sm w-full h-20"
                      placeholder="z.B. Mehr Fokus auf X, weniger Y..."
                      value={planFeedback}
                      onChange={(e) => setPlanFeedback(e.target.value)}
                    />
                  </div>
                  <button
                    onClick={generateContentPlan}
                    disabled={!contentTopic.trim() || generatingPlan}
                    className="px-4 py-2 bg-blue-600 rounded text-sm hover:bg-blue-700 disabled:bg-slate-700"
                  >
                    {generatingPlan ? "Generiere..." : "Content-Plan generieren"}
                  </button>
                </div>
              </div>
              
              {/* Kalender-Grid */}
              <div>
                <div className="flex justify-between items-center mb-3">
                  <h2 className="font-semibold">Kalender</h2>
                  <div className="flex gap-2">
                  {calendar.length > 0 && (
                      <>
                        <button
                          onClick={() => {
                            const today = new Date();
                            today.setHours(0, 0, 0, 0);
                            const todayElement = document.querySelector(`[data-date="${today.toISOString().split('T')[0]}"]`);
                            if (todayElement) {
                              todayElement.scrollIntoView({ behavior: 'smooth', block: 'center' });
                            }
                          }}
                          className="px-3 py-1 bg-blue-600 rounded text-sm"
                        >
                          Zu heute scrollen
                        </button>
                    <button
                      onClick={generateAllVideos}
                      className="px-3 py-1 bg-purple-600 rounded text-sm"
                    >
                      Alle Videos erstellen
                    </button>
                      </>
                  )}
                </div>
                </div>
                <div className="grid grid-cols-7 gap-2 max-h-[600px] overflow-y-auto">
                  {calendar.map((slot) => {
                    const slotDate = slot.dateObj || new Date(slot.date);
                    const today = new Date();
                    today.setHours(0, 0, 0, 0);
                    const isPast = slotDate < today;
                    const isToday = slotDate.getTime() === today.getTime();
                    
                    const hasScripts = slot.slots.some(s => s.script_content);
                    const allHaveScripts = slot.slots.length === 3 && slot.slots.every(s => s.script_content);
                    
                    // FIX: Vergangene Tage ausgrauen, aber zugänglich machen
                    return (
                      <button
                        key={slot.date}
                        data-date={slot.date}
                        onClick={() => loadDayPlans(slot.date)}
                        className={`p-2 rounded text-xs border ${
                          isPast
                            ? "bg-slate-900 border-slate-600 opacity-50"
                            : isToday
                            ? "bg-blue-900 border-blue-600 ring-2 ring-blue-400"
                            : allHaveScripts
                            ? "bg-emerald-900 border-emerald-600"
                            : hasScripts
                            ? "bg-yellow-900 border-yellow-600"
                            : "bg-slate-800 border-slate-700"
                        } ${isPast ? "hover:opacity-70" : "hover:bg-slate-700"} transition-opacity`}
                        title={isPast ? `Vergangener Tag: ${slotDate.toLocaleDateString('de-DE')}` : slotDate.toLocaleDateString('de-DE')}
                      >
                        <div className={`font-semibold ${isPast ? "text-slate-500" : ""}`}>
                          {slotDate.getDate()}
                        </div>
                        <div className={`text-[10px] ${isPast ? "text-slate-600" : "text-slate-400"}`}>
                          {slot.slots.filter(s => s.script_content).length}/3
                        </div>
                        {isToday && (
                          <div className="text-[8px] text-blue-300 mt-1">Heute</div>
                        )}
                          </button>
                    );
                  })}
                </div>
              </div>
            </>
          ) : (
            <>
              {/* Tages-Ansicht */}
              <div className="flex justify-between items-center">
                <div>
                  <button
                    onClick={() => {
                      setSelectedDay(null);
                      setDayPlans([]);
                    }}
                    className="px-3 py-1 bg-slate-700 rounded text-sm mb-2"
                  >
                    ← Zurück zum Kalender
                          </button>
                  <h2 className="font-semibold mt-2">
                    {new Date(selectedDay).toLocaleDateString("de-DE", {
                      weekday: "long",
                      year: "numeric",
                      month: "long",
                      day: "numeric"
                    })}
                  </h2>
                </div>
                <button
                  onClick={() => generateAllVideosForDay(selectedDay)}
                  className="px-3 py-1 bg-purple-600 rounded text-sm"
                >
                  Alle Videos für diesen Tag erstellen
                          </button>
              </div>
              
              <div className="space-y-4">
                {dayPlans.map((plan) => {
                  const asset = latestAssetForPlan(plan.id);
                  return (
                    <div key={plan.id} className="bg-slate-800 p-4 rounded space-y-3">
                      <div className="flex justify-between items-start">
                        <div>
                          <h3 className="font-semibold">Video {plan.slot_index}</h3>
                          {plan.topic && (
                            <p className="text-sm text-slate-400">Thema: {plan.topic}</p>
                          )}
                        </div>
                        <div className="flex gap-2">
                          {plan.script_content ? (
                            <>
                            <button
                                onClick={() => generateAssets(plan.id)}
                                className="px-3 py-1 bg-emerald-600 rounded text-sm"
                                disabled={!!asset}
                              >
                                {asset ? "Video erstellt" : "Video erstellen"}
                              </button>
                              <button
                                onClick={() => setSelectedPlanForScript(plan.id)}
                                className="px-3 py-1 bg-blue-600 rounded text-sm"
                              >
                                Script bearbeiten
                              </button>
                            </>
                          ) : (
                            <button
                              onClick={() => generateScript(plan.id)}
                              className="px-3 py-1 bg-blue-600 rounded text-sm"
                              disabled={generatingScript}
                            >
                              {generatingScript ? "Generiere..." : "Script generieren"}
                            </button>
                          )}
                        </div>
                      </div>
                      
                      {plan.script_content && (
                        <div className="bg-slate-900 p-3 rounded space-y-2 text-sm">
                          <div>
                            <strong className="text-slate-300">Hook:</strong>
                            <p className="text-slate-400 mt-1">{plan.hook || "Kein Hook"}</p>
                          </div>
                          <div>
                            <strong className="text-slate-300">Script:</strong>
                            <p className="text-slate-400 mt-1 whitespace-pre-wrap">{plan.script_content}</p>
                          </div>
                          {plan.title && (
                            <div>
                              <strong className="text-slate-300">Titel:</strong>
                              <p className="text-slate-400 mt-1">{plan.title}</p>
                            </div>
                          )}
                          {plan.cta && (
                            <div>
                              <strong className="text-slate-300">CTA:</strong>
                              <p className="text-slate-400 mt-1">{plan.cta}</p>
                            </div>
                          )}
                          
                          {/* Visuelle Einstellungen */}
                          {(plan.visual_prompt || plan.lighting || plan.composition || plan.camera_angles || plan.visual_style) && (
                            <div className="mt-3 pt-3 border-t border-slate-700">
                              <strong className="text-slate-300 block mb-2">🎬 Visuelle Einstellungen:</strong>
                              {plan.visual_prompt && (
                                <div className="mb-2">
                                  <strong className="text-slate-400 text-xs">Visuelle Beschreibung:</strong>
                                  <p className="text-slate-500 text-xs mt-1 whitespace-pre-wrap">{plan.visual_prompt}</p>
                                </div>
                              )}
                              <div className="grid grid-cols-2 gap-2 text-xs">
                                {plan.lighting && (
                                  <div>
                                    <strong className="text-slate-400">Beleuchtung:</strong>
                                    <p className="text-slate-500">{plan.lighting}</p>
                                  </div>
                                )}
                                {plan.composition && (
                                  <div>
                                    <strong className="text-slate-400">Komposition:</strong>
                                    <p className="text-slate-500">{plan.composition}</p>
                                  </div>
                                )}
                                {plan.camera_angles && (
                                  <div>
                                    <strong className="text-slate-400">Kamerawinkel:</strong>
                                    <p className="text-slate-500">{plan.camera_angles}</p>
                                  </div>
                                )}
                                {plan.visual_style && (
                                  <div>
                                    <strong className="text-slate-400">Stil:</strong>
                                    <p className="text-slate-500">{plan.visual_style}</p>
                                  </div>
                                )}
                              </div>
                            </div>
                          )}
                        </div>
                      )}
                      
                      {/* Job-Status für dieses Video */}
                      {(() => {
                        // Finde Job für diesen Plan (payload enthält plan.id als String)
                        const videoJob = jobs.find(j => 
                          j.type === "generate_assets" && 
                          (j.payload === plan.id || j.payload === String(plan.id)) &&
                          (j.status === "pending" || j.status === "in_progress" || j.status === "failed")
                        );
                        
                        if (videoJob) {
                          const statusColor = 
                            videoJob.status === "failed" ? "bg-red-900 border-red-600" :
                            videoJob.status === "in_progress" ? "bg-yellow-900 border-yellow-600" :
                            "bg-blue-900 border-blue-600";
                          
                          const statusText = 
                            videoJob.status === "failed" ? "Fehler" :
                            videoJob.status === "in_progress" ? "Wird erstellt..." :
                            "In Warteschlange";
                          
                          const latestRun = videoJob.runs && videoJob.runs.length > 0 
                            ? videoJob.runs[videoJob.runs.length - 1] 
                            : null;
                          
                          return (
                            <div className={`p-3 rounded border-2 ${statusColor} space-y-1`}>
                              <div className="flex items-center gap-2">
                                <span className="text-sm font-semibold">{statusText}</span>
                                {videoJob.status === "in_progress" && (
                                  <span className="animate-spin">⟳</span>
                                )}
                              </div>
                              {latestRun && latestRun.message && (
                                <p className="text-xs text-slate-300">{latestRun.message}</p>
                              )}
                              {videoJob.status === "failed" && latestRun && (
                                <p className="text-xs text-red-300 mt-1">
                                  Fehler: {latestRun.message || "Unbekannter Fehler"}
                                </p>
                              )}
                            </div>
                          );
                        }
                        
                        return null;
                      })()}
                      
                          {asset && (
                        <div className={`p-3 rounded border-2 bg-emerald-900 border-emerald-600 space-y-2`}>
                          <div className="flex items-center gap-2">
                            <span className="text-sm font-semibold text-emerald-300">✓ Video erstellt</span>
                          </div>
                        <div className="flex gap-2">
                          {asset.signed_video_url && (
                            <button
                              onClick={() => window.open(asset.signed_video_url!, "_blank")}
                              className="px-3 py-1 bg-orange-600 rounded text-sm"
                            >
                              Video ansehen
                            </button>
                          )}
                          <button
                            onClick={() => publishNow(asset.id)}
                            className="px-3 py-1 bg-purple-600 rounded text-sm"
                          >
                            Publish
                          </button>
                        </div>
                          </div>
                        )}
                      </div>
                    );
                  })}
                </div>
              
              {/* Chat-Fenster für Script-Regenerierung */}
              {selectedPlanForScript && (() => {
                const plan = dayPlans.find(p => p.id === selectedPlanForScript);
                if (!plan) return null;
                
                return (
                  <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
                    <div className="bg-slate-800 p-6 rounded-lg max-w-3xl w-full max-h-[90vh] overflow-auto">
                      <h3 className="font-semibold mb-3">Script bearbeiten / Regenerieren</h3>
                      <div className="space-y-4">
                        {/* Aktuelles Script anzeigen */}
                        {plan.script_content && (
                          <div className="bg-slate-900 p-4 rounded space-y-2 text-sm">
                            <h4 className="text-slate-300 font-semibold mb-2">Aktuelles Script:</h4>
                            {plan.hook && (
                              <div>
                                <strong className="text-slate-400">Hook:</strong>
                                <p className="text-slate-300 mt-1">{plan.hook}</p>
              </div>
                            )}
                            {plan.title && (
                              <div>
                                <strong className="text-slate-400">Titel:</strong>
                                <p className="text-slate-300 mt-1">{plan.title}</p>
          </div>
                            )}
                            <div>
                              <strong className="text-slate-400">Script:</strong>
                              <p className="text-slate-300 mt-1 whitespace-pre-wrap">{plan.script_content}</p>
                            </div>
                            {plan.cta && (
                              <div>
                                <strong className="text-slate-400">CTA:</strong>
                                <p className="text-slate-300 mt-1">{plan.cta}</p>
                              </div>
                            )}
                            
                            {/* Visuelle Einstellungen */}
                            {(plan.visual_prompt || plan.lighting || plan.composition || plan.camera_angles || plan.visual_style) && (
                              <div className="mt-3 pt-3 border-t border-slate-700">
                                <strong className="text-slate-400 block mb-2">Visuelle Einstellungen:</strong>
                                {plan.visual_prompt && (
                                  <div className="mb-2">
                                    <strong className="text-slate-400 text-xs">Visuelle Beschreibung:</strong>
                                    <p className="text-slate-500 text-xs mt-1 whitespace-pre-wrap">{plan.visual_prompt}</p>
                                  </div>
                                )}
                                <div className="grid grid-cols-2 gap-2 text-xs">
                                  {plan.lighting && (
                                    <div>
                                      <strong className="text-slate-400">Beleuchtung:</strong>
                                      <p className="text-slate-500">{plan.lighting}</p>
                                    </div>
                                  )}
                                  {plan.composition && (
                                    <div>
                                      <strong className="text-slate-400">Komposition:</strong>
                                      <p className="text-slate-500">{plan.composition}</p>
                                    </div>
                                  )}
                                  {plan.camera_angles && (
                                    <div>
                                      <strong className="text-slate-400">Kamerawinkel:</strong>
                                      <p className="text-slate-500">{plan.camera_angles}</p>
                                    </div>
                                  )}
                                  {plan.visual_style && (
                                    <div>
                                      <strong className="text-slate-400">Stil:</strong>
                                      <p className="text-slate-500">{plan.visual_style}</p>
                                    </div>
                                  )}
                                </div>
                              </div>
                            )}
                          </div>
                        )}
                        
                        {/* Feedback für Regenerierung */}
                        <div>
                          <label className="text-sm text-slate-300 block mb-1">
                            Feedback/Anpassungen für Regenerierung
                          </label>
                          <textarea
                            className="bg-slate-700 px-3 py-2 rounded text-sm w-full h-32"
                            placeholder="z.B. Hook sollte spannender sein, mehr Fokus auf X, visuell mehr Energie..."
                            value={scriptFeedback}
                            onChange={(e) => setScriptFeedback(e.target.value)}
                          />
                          <p className="text-xs text-slate-400 mt-1">
                            Tipp: Du kannst auch visuelle Anpassungen anfordern (z.B. "hellere Beleuchtung", "Close-up statt Medium Shot")
                          </p>
                        </div>
                        
                        <div className="flex gap-2">
                          <button
                            onClick={() => generateScript(selectedPlanForScript, scriptFeedback)}
                            disabled={generatingScript}
                            className="px-4 py-2 bg-blue-600 rounded text-sm hover:bg-blue-700 disabled:bg-slate-600"
                          >
                            {generatingScript ? "Generiere..." : "Script neu generieren"}
                          </button>
                          <button
                            onClick={() => {
                              setSelectedPlanForScript(null);
                              setScriptFeedback("");
                            }}
                            className="px-4 py-2 bg-slate-700 rounded text-sm hover:bg-slate-600"
                          >
                            Abbrechen
                          </button>
                        </div>
                      </div>
                    </div>
                  </div>
                );
              })()}
            </>
          )}
        </div>
      )}

      {activeView === "library" && (
        <div className="bg-slate-900 p-4 rounded space-y-4">
          <div className="flex items-center justify-between">
            <h2 className="font-semibold">Video Library</h2>
            <div className="flex gap-2">
              <select
                className="bg-slate-800 px-3 py-1 rounded text-sm"
                value={libraryFilter}
                onChange={(e) => setLibraryFilter(e.target.value)}
              >
                <option value="all">Alle Videos</option>
                <option value="generated">Generiert</option>
                <option value="transcribed">Transkribiert</option>
                <option value="translated">Übersetzt</option>
                <option value="published">Veröffentlicht</option>
              </select>
              <button className="px-3 py-1 bg-slate-700 rounded text-sm" onClick={() => refreshData(projectId, orgId)}>
                Reload
              </button>
            </div>
          </div>
          
          {(() => {
            const filteredAssets = assets.filter(asset => {
              if (libraryFilter === "all") return true;
              return asset.status === libraryFilter;
            });
            
            if (filteredAssets.length === 0) {
              return (
                <div className="text-center py-12">
                  <p className="text-slate-400">Keine Videos in dieser Kategorie</p>
                </div>
              );
            }
            
            return (
              <div className="grid md:grid-cols-3 gap-4">
                {filteredAssets.map((asset) => (
                  <div key={asset.id} className="bg-slate-800 p-4 rounded text-sm space-y-3">
                    {asset.signed_thumbnail_url ? (
                      <img src={asset.signed_thumbnail_url} alt="thumbnail" className="rounded w-full" />
                    ) : (
                      <div className="h-48 bg-slate-700 rounded flex items-center justify-center text-xs text-slate-300">Kein Thumbnail</div>
                    )}
                    
                    <div className="space-y-2">
                      <div className="flex justify-between items-center text-xs">
                        <span className={`px-2 py-1 rounded ${
                          asset.status === "generated" ? "bg-emerald-600" :
                          asset.status === "transcribed" ? "bg-blue-600" :
                          asset.status === "translated" ? "bg-purple-600" :
                          asset.status === "published" ? "bg-indigo-600" :
                          "bg-slate-600"
                        }`}>
                          {asset.status}
                        </span>
                        <span className="text-slate-400">
                          {asset.created_at ? new Date(asset.created_at).toLocaleString() : ""}
                        </span>
                      </div>
                      
                      {/* Metadaten */}
                      {(asset.original_language || asset.translated_language || asset.translation_provider) && (
                        <div className="text-xs text-slate-400 space-y-1">
                          {asset.original_language && (
                            <div>Original: {asset.original_language}</div>
                          )}
                          {asset.translated_language && (
                            <div>Übersetzt: {asset.translated_language}</div>
                          )}
                          {asset.translation_provider && (
                            <div>Provider: {asset.translation_provider}</div>
                          )}
                        </div>
                      )}
                      
                      {asset.transcript && (
                        <div className="text-xs text-slate-400 line-clamp-2">
                          {asset.transcript.substring(0, 100)}...
                        </div>
                      )}
                    </div>
                    
                    <div className="flex gap-2 flex-wrap text-xs">
                      {/* Download-Button für ALLE Videos */}
                      <button 
                        className="px-3 py-1.5 bg-emerald-600 rounded hover:bg-emerald-700 transition-colors" 
                        onClick={async () => {
                          try {
                            const resp = await api.get(`/video/download/${asset.id}`, {
                              responseType: 'blob',
                              headers
                            });
                            const url = window.URL.createObjectURL(new Blob([resp.data]));
                            const link = document.createElement('a');
                            link.href = url;
                            link.download = `video-${asset.id}.mp4`;
                            document.body.appendChild(link);
                            link.click();
                            document.body.removeChild(link);
                            window.URL.revokeObjectURL(url);
                            setStatus("Video wird heruntergeladen...");
                          } catch (e: any) {
                            console.error("Download error:", e);
                            setStatus(e?.response?.data?.detail || "Fehler beim Download");
                          }
                        }}
                      >
                        Download
                      </button>
                      
                      {asset.signed_video_url && (
                        <button 
                          className="px-3 py-1.5 bg-orange-600 rounded hover:bg-orange-700 transition-colors" 
                          onClick={() => window.open(asset.signed_video_url!, "_blank")}
                        >
                          Öffnen
                        </button>
                      )}
                      
                      {/* Publish nur für generierte Videos */}
                      {asset.status === "generated" && asset.project_id && (
                        <button 
                          className="px-3 py-1.5 bg-purple-700 rounded hover:bg-purple-800 transition-colors" 
                          onClick={() => publishNow(asset.id)}
                        >
                          Publish
                        </button>
                      )}
                      
                      {/* Status nur für veröffentlichte Videos */}
                      {asset.status === "published" && (
                        <button 
                          className="px-3 py-1.5 bg-indigo-700 rounded hover:bg-indigo-800 transition-colors" 
                          onClick={() => refreshPublishStatus(asset.id)}
                        >
                          Status
                        </button>
                      )}
                    </div>
                    
                    {asset.publish_response && (
                      <div className="text-[11px] text-slate-400 break-words">
                        Last publish: {asset.publish_response}
                      </div>
                    )}
                  </div>
                ))}
              </div>
            );
          })()}
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
        <div className="bg-slate-900 p-4 rounded space-y-4">
          <div className="flex items-center justify-between">
          <h2 className="font-semibold">Credentials</h2>
            <button 
              onClick={() => setShowAddCredential(!showAddCredential)} 
              className="px-3 py-2 bg-emerald-600 rounded text-sm"
            >
              {showAddCredential ? "Abbrechen" : "+ Credential hinzufügen"}
          </button>
          </div>
          
          {showAddCredential && (
            <div className="bg-slate-800 p-4 rounded space-y-3">
              <h3 className="font-semibold text-sm">Neues Credential</h3>
              <div>
                <label className="text-sm text-slate-300 block mb-1">Provider</label>
                <select
                  className="bg-slate-700 px-3 py-2 rounded text-sm w-full"
                  value={newCredentialProvider}
                  onChange={(e) => setNewCredentialProvider(e.target.value)}
                >
                  <option value="openrouter">OpenRouter</option>
                  <option value="falai">Fal.ai</option>
                </select>
              </div>
              <div>
                <label className="text-sm text-slate-300 block mb-1">Name</label>
                <input
                  className="bg-slate-700 px-3 py-2 rounded text-sm w-full"
                  placeholder="z.B. openrouter_main"
                  value={newCredentialName}
                  onChange={(e) => setNewCredentialName(e.target.value)}
                />
              </div>
              <div>
                <label className="text-sm text-slate-300 block mb-1">API Key / Secret</label>
                <input
                  type="password"
                  className="bg-slate-700 px-3 py-2 rounded text-sm w-full"
                  placeholder="Dein API Key"
                  value={newCredentialSecret}
                  onChange={(e) => setNewCredentialSecret(e.target.value)}
                />
              </div>
              <button 
                onClick={addCredential} 
                className="px-4 py-2 bg-blue-600 rounded text-sm hover:bg-blue-700"
                disabled={!newCredentialName.trim() || !newCredentialSecret.trim()}
              >
                Speichern
              </button>
            </div>
          )}
          
          <div className="space-y-2">
            <h3 className="font-semibold text-sm">Gespeicherte Credentials</h3>
            {credentials.length === 0 ? (
              <p className="text-sm text-slate-400">Keine Credentials vorhanden</p>
            ) : (
          <ul className="divide-y divide-slate-800 text-sm">
            {credentials.map((c) => (
                  <li key={c.id} className="py-2 flex justify-between items-center">
                    <div>
                      <span className="font-semibold">{c.provider}</span>
                      <span className="text-slate-400"> · {c.name}</span>
                    </div>
                    <span className="text-xs text-slate-500">v{c.version}</span>
              </li>
            ))}
          </ul>
            )}
          </div>
          
          <div className="bg-slate-800 p-3 rounded text-xs text-slate-400">
            <p className="font-semibold mb-1">Hinweis:</p>
            <p>Credentials werden verschlüsselt gespeichert. Verwende diese für:</p>
            <ul className="list-disc list-inside mt-1 space-y-1">
              <li><strong>OpenRouter:</strong> API-Key für LLM- und Transcription-Modelle</li>
              <li><strong>Fal.ai:</strong> API-Key für Transcription-Modelle</li>
            </ul>
            <p className="mt-2">Die API-Keys werden automatisch für YouTube-Transcription verwendet.</p>
          </div>
        </div>
      )}

      {activeView === "queue" && (
        <div className="bg-slate-950 min-h-screen">
          {/* Top Bar */}
          <div className="bg-slate-900 border-b border-slate-800 px-6 py-4">
            <div className="flex justify-between items-center">
              <div className="flex items-center gap-4">
                <h1 className="text-xl font-semibold">TikTok Content Maker</h1>
                <div className="flex items-center gap-2 text-sm text-slate-400">
                  <span className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse"></span>
                  <span>Queue ({jobs.filter(j => j.status === "pending" || j.status === "in_progress").length} active)</span>
                </div>
                      </div>
              <div className="flex items-center gap-3">
                <button
                  onClick={() => refreshData(projectId, orgId)}
                  className="px-3 py-1.5 bg-slate-800 hover:bg-slate-700 rounded text-sm transition-colors"
                >
                  Aktualisieren
                </button>
                {jobStatusPolling && (
                  <button
                    onClick={stopJobStatusPolling}
                    className="px-3 py-1.5 bg-red-600 hover:bg-red-700 rounded text-sm transition-colors"
                  >
                    Polling stoppen
                  </button>
                )}
              </div>
            </div>
          </div>

          <div className="flex">
            {/* Left Panel - Filters */}
            <div className="w-64 bg-slate-900 border-r border-slate-800 p-4">
              <h2 className="text-sm font-semibold text-slate-300 mb-3">Queue</h2>
              <div className="space-y-1">
                {[
                  { key: "all", label: "All", count: jobs.length },
                  { key: "processing", label: "Processing", count: jobs.filter(j => j.status === "in_progress").length },
                  { key: "queued", label: "Queued", count: jobs.filter(j => j.status === "pending").length },
                  { key: "completed", label: "Completed", count: jobs.filter(j => j.status === "completed").length },
                  { key: "failed", label: "Failed", count: jobs.filter(j => j.status === "failed").length },
                ].map((filter) => (
                  <button
                    key={filter.key}
                    onClick={() => setQueueFilter(filter.key as any)}
                    className={`w-full text-left px-3 py-2 rounded text-sm transition-colors ${
                      queueFilter === filter.key
                        ? "bg-blue-600 text-white"
                        : "text-slate-400 hover:bg-slate-800 hover:text-slate-200"
                    }`}
                  >
                    {filter.label} ({filter.count})
                  </button>
                ))}
              </div>
            </div>

            {/* Main Queue Area */}
            <div className="flex-1 p-6">
              {(() => {
                const filteredJobs = jobs.filter(j => {
                  if (queueFilter === "all") return true;
                  if (queueFilter === "processing") return j.status === "in_progress";
                  if (queueFilter === "queued") return j.status === "pending";
                  if (queueFilter === "completed") return j.status === "completed";
                  if (queueFilter === "failed") return j.status === "failed";
                  return true;
                });

                if (filteredJobs.length === 0) {
                  return (
                    <div className="text-center py-12">
                      <p className="text-slate-400">Keine Jobs in dieser Kategorie</p>
                    </div>
                  );
                }

                return (
                  <div className="space-y-4">
                    {filteredJobs.map((job) => {
                      const plan = job.payload ? calendar
                        .flatMap(slot => slot.slots)
                        .find(p => p.id === job.payload) : null;
                      
                      const asset = job.payload ? assets.find(a => a.plan_id === job.payload) : null;
                      
                      // Pipeline Steps für verschiedene Job-Typen
                      const steps = job.type === "generate_assets" ? [
                        { name: "Script", key: "script" },
                        { name: "Voiceover", key: "voiceover" },
                        { name: "Video Render", key: "render" },
                        { name: "Upload", key: "upload" },
                      ] : job.type === "youtube_transcribe" ? [
                        { name: "Download", key: "download" },
                        { name: "Extract Audio", key: "extract" },
                        { name: "Transcribe", key: "transcribe" },
                        { name: "Save Result", key: "save" },
                      ] : [];

                      // Bestimme aktuellen Step basierend auf Job-Runs
                      const getStepStatus = (stepKey: string) => {
                        if (!job.runs || job.runs.length === 0) {
                          return stepKey === "script" ? "pending" : "waiting";
                        }
                        const latestRun = job.runs[job.runs.length - 1];
                        if (job.status === "completed") return "completed";
                        if (job.status === "failed") return "failed";
                        if (job.status === "in_progress") {
                          if (stepKey === "script") return "completed";
                          if (stepKey === "voiceover") return latestRun.message?.toLowerCase().includes("voice") ? "active" : "completed";
                          if (stepKey === "render") return latestRun.message?.toLowerCase().includes("render") || latestRun.message?.toLowerCase().includes("video") ? "active" : "waiting";
                          return "waiting";
                        }
                        return "waiting";
                      };

                      const completedSteps = steps.filter(s => getStepStatus(s.key) === "completed").length;
                      const progressPercent = steps.length > 0 ? (completedSteps / steps.length) * 100 : 0;

                      // Status-Farben
                      const statusConfig = {
                        pending: { color: "#64748b", label: "Queued", icon: "○" },
                        in_progress: { color: "#3b82f6", label: "Processing", icon: "⟳" },
                        completed: { color: "#10b981", label: "Completed", icon: "✓" },
                        failed: { color: "#ef4444", label: "Failed", icon: "✗" },
                      };

                      const config = statusConfig[job.status as keyof typeof statusConfig] || statusConfig.pending;
                      const latestRun = job.runs && job.runs.length > 0 ? job.runs[job.runs.length - 1] : null;

                      return (
                        <div
                          key={job.id}
                          className="bg-slate-900 rounded-lg border-l-4 shadow-sm hover:shadow-md transition-shadow"
                          style={{ borderLeftColor: config.color }}
                        >
                          <div className="p-5">
                            {/* Header */}
                            <div className="flex items-start justify-between mb-4">
                              <div className="flex-1">
                                <div className="flex items-center gap-3 mb-2">
                                  {asset?.signed_thumbnail_url ? (
                                    <img
                                      src={asset.signed_thumbnail_url}
                                      alt="Thumbnail"
                                      className="w-20 h-20 rounded object-cover"
                                    />
                                  ) : (
                                    <div className="w-20 h-20 rounded bg-slate-800 flex items-center justify-center text-slate-600">
                                      <span className="text-2xl">🎬</span>
                  </div>
                )}
                                  <div className="flex-1">
                                    <h3 className="font-semibold text-base mb-1">
                                      {job.type === "youtube_transcribe" ? (
                                        (() => {
                                          try {
                                            const payload = JSON.parse(job.payload || "{}");
                                            return `YouTube Transcription: ${payload.url || job.id.slice(0, 8)}`;
                                          } catch {
                                            return `YouTube Transcription ${job.id.slice(0, 8)}`;
                                          }
                                        })()
                                      ) : (
                                        plan?.title || plan?.topic || `Video ${job.id.slice(0, 8)}`
                                      )}
                                    </h3>
                                    {job.type === "youtube_transcribe" ? (
                                      (() => {
                                        try {
                                          const payload = JSON.parse(job.payload || "{}");
                                          return (
                                            <p className="text-sm text-slate-400">
                                              {payload.provider}/{payload.model_id} · {payload.target_language || "auto"}
                                            </p>
                                          );
                                        } catch {
                                          return null;
                                        }
                                      })()
                                    ) : plan?.topic ? (
                                      <p className="text-sm text-slate-400">{plan.topic}</p>
                                    ) : null}
        </div>
                                </div>
                              </div>
                              <div className="text-right">
                                <div className="flex items-center gap-2 mb-1">
                                  <span className="text-xs text-slate-400">Status:</span>
                                  <span className="text-sm font-medium" style={{ color: config.color }}>
                                    {config.icon} {config.label}
                                  </span>
                                  {job.status === "in_progress" && (
                                    <span className="w-2 h-2 rounded-full animate-pulse" style={{ backgroundColor: config.color }}></span>
                                  )}
                                </div>
                                {latestRun?.created_at && (
                                  <p className="text-xs text-slate-500">
                                    Last update: {Math.floor((Date.now() - new Date(latestRun.created_at).getTime()) / 1000)}s ago
                                  </p>
                                )}
                              </div>
                            </div>

                            {/* Progress Bar */}
                            {job.status === "in_progress" && steps.length > 0 && (
                              <div className="mb-4">
                                <div className="flex justify-between text-xs text-slate-400 mb-1">
                                  <span>Progress</span>
                                  <span>{Math.round(progressPercent)}%</span>
                                </div>
                                <div className="w-full bg-slate-800 rounded-full h-2">
                                  <div
                                    className="h-2 rounded-full transition-all duration-500"
                                    style={{
                                      width: `${progressPercent}%`,
                                      backgroundColor: config.color,
                                    }}
                                  ></div>
                                </div>
                              </div>
                            )}

                            {/* Pipeline Steps */}
                            {steps.length > 0 && (
                              <div className="mb-4">
                                <p className="text-xs text-slate-400 mb-2">Steps:</p>
                                <div className="flex items-center gap-2 flex-wrap">
                                  {steps.map((step) => {
                                    const stepStatus = getStepStatus(step.key);
                                    const isActive = stepStatus === "active";
                                    const isCompleted = stepStatus === "completed";
                                    const isFailed = stepStatus === "failed";

                                    return (
                                      <div
                                        key={step.key}
                                        className={`flex items-center gap-1.5 px-3 py-1.5 rounded text-xs ${
                                          isActive
                                            ? "bg-blue-600 text-white"
                                            : isCompleted
                                            ? "bg-emerald-600 text-white"
                                            : isFailed
                                            ? "bg-red-600 text-white"
                                            : "bg-slate-800 text-slate-400"
                                        }`}
                                      >
                                        <span>
                                          {isCompleted ? "✓" : isActive ? "⟳" : isFailed ? "✗" : "○"}
                                        </span>
                                        <span>{step.name}</span>
                                        {isActive && <span className="animate-spin">⟳</span>}
                                      </div>
                                    );
                                  })}
                                </div>
                              </div>
                            )}

                            {/* Error Message */}
                            {job.status === "failed" && latestRun?.message && (
                              <div className="mb-4 p-3 bg-red-900/30 border border-red-800 rounded">
                                <div className="flex items-start gap-2">
                                  <span className="text-red-400">⚠</span>
                                  <div className="flex-1">
                                    <p className="text-sm font-medium text-red-300 mb-1">Status: Failed</p>
                                    <p className="text-xs text-red-400">Reason: {latestRun.message}</p>
                                  </div>
                                </div>
                                <div className="flex gap-2 mt-3">
                                  <button
                                    onClick={() => {
                                      if (job.payload && plan) {
                                        generateAssets(plan.id);
                                      }
                                    }}
                                    className="px-3 py-1.5 bg-red-600 hover:bg-red-700 rounded text-xs transition-colors"
                                  >
                                    Retry
                                  </button>
                                  <button className="px-3 py-1.5 bg-slate-700 hover:bg-slate-600 rounded text-xs transition-colors">
                                    View Logs
                                  </button>
                                </div>
                              </div>
                            )}

                            {/* Actions */}
                            <div className="flex items-center justify-between pt-4 border-t border-slate-800">
                              <div className="flex gap-2">
                                {job.status === "in_progress" && (
                                  <button className="px-3 py-1.5 bg-slate-700 hover:bg-slate-600 rounded text-xs transition-colors">
                                    Pause
                                  </button>
                                )}
                                {(job.status === "pending" || job.status === "in_progress") && (
                                  <button className="px-3 py-1.5 bg-red-600 hover:bg-red-700 rounded text-xs transition-colors">
                                    Cancel
                                  </button>
                                )}
                                {jobs.length > 1 && job.status === "pending" && (
                                  <button className="px-3 py-1.5 bg-slate-700 hover:bg-slate-600 rounded text-xs transition-colors">
                                    ↑ Priority
                                  </button>
                                )}
                              </div>
                              <div className="text-xs text-slate-500">
                                {job.created_at && new Date(job.created_at).toLocaleString("de-DE")}
                              </div>
                            </div>
                          </div>
                        </div>
                      );
                    })}
                  </div>
                );
              })()}
            </div>
          </div>
        </div>
      )}

      {activeView === "youtube" && (
        <div className="bg-slate-900 p-4 rounded space-y-4">
          <div className="flex items-center justify-between">
            <h2 className="font-semibold">YouTube Video Processing</h2>
            <div className="flex gap-2">
              <button
                className={`px-3 py-1 rounded text-sm ${!translateMode ? "bg-blue-600" : "bg-slate-700"}`}
                onClick={() => setTranslateMode(false)}
              >
                Transkribieren
              </button>
              <button
                className={`px-3 py-1 rounded text-sm ${translateMode ? "bg-blue-600" : "bg-slate-700"}`}
                onClick={() => setTranslateMode(true)}
              >
                Übersetzen
              </button>
            </div>
          </div>
          
          {!translateMode ? (
            /* Transcription Mode */
            <div className="space-y-3">
            <div>
              <label className="text-sm text-slate-300 block mb-1">API Provider</label>
              <select
                className="bg-slate-800 px-3 py-2 rounded text-sm w-full"
                value={apiProvider}
                onChange={(e) => {
                  setApiProvider(e.target.value);
                  setAvailableModels([]);
                  setSelectedModel("");
                }}
              >
                <option value="openrouter">OpenRouter</option>
                <option value="falai">Fal.ai</option>
              </select>
            </div>

            <div>
              <label className="text-sm text-slate-300 block mb-1">API Key</label>
              <div className="space-y-2">
                <select
                  className="bg-slate-800 px-3 py-2 rounded text-sm w-full"
                  value={selectedCredentialId || "manual"}
                  onChange={(e) => {
                    if (e.target.value === "manual") {
                      setSelectedCredentialId("");
                      setApiKey("");
                      setAvailableModels([]);
                      setSelectedModel("");
                    } else {
                      setSelectedCredentialId(e.target.value);
                      setApiKey(""); // API-Key wird vom Backend verwendet
                      // Modelle werden automatisch via useEffect geladen
                    }
                  }}
                >
                  <option value="manual">Manuell eingeben</option>
                  {credentials
                    .filter(c => c.provider === apiProvider)
                    .map(c => (
                      <option key={c.id} value={c.id}>
                        {c.name} (gespeichert)
                      </option>
                    ))}
                </select>
                {(!selectedCredentialId || selectedCredentialId === "manual") && (
                  <input
                    className="bg-slate-800 px-3 py-2 rounded text-sm w-full"
                    type="password"
                    placeholder={`Dein ${apiProvider === "openrouter" ? "OpenRouter" : "Fal.ai"} API Key`}
                    value={apiKey}
                    onChange={(e) => setApiKey(e.target.value)}
                  />
                )}
              </div>
              <p className="text-xs text-slate-400 mt-1">
                Tipp: Speichere deinen API-Key im "Credentials"-Tab, um ihn dauerhaft zu verwenden.
              </p>
            </div>

            {loadingModels && (
              <div className="text-sm text-slate-400">Lade verfügbare Modelle...</div>
            )}

            {!loadingModels && availableModels.length > 0 && (
              <div>
                <label className="text-sm text-slate-300 block mb-1">Modell auswählen</label>
                <select
                  className="bg-slate-800 px-3 py-2 rounded text-sm w-full"
                  value={selectedModel}
                  onChange={(e) => setSelectedModel(e.target.value)}
                >
                  {availableModels.map((model) => (
                    <option key={model.id} value={model.id}>
                      {model.name} - {model.cost_per_minute === 0 ? "Kostenlos" : `${model.currency} ${model.cost_per_minute.toFixed(4)}/Min`}
                    </option>
                  ))}
                </select>
              </div>
            )}

            {selectedModel && availableModels.length > 0 && (() => {
              const model = availableModels.find((m) => m.id === selectedModel);
              if (!model) return null;
              return (
                <div className="bg-slate-800 p-3 rounded text-xs space-y-2">
                  <div className="text-slate-300 font-semibold">{model.name}</div>
                  {model.description && (
                    <div className="text-slate-400">{model.description}</div>
                  )}
                  <div className="text-slate-300">
                    <strong>Kosten:</strong> {model.cost_per_minute === 0 ? (
                      <span className="text-green-400">Kostenlos</span>
                    ) : (
                      <span>{model.currency} {model.cost_per_minute.toFixed(4)} pro Minute</span>
                    )}
                  </div>
                  <div className="text-slate-400">
                    <strong>Unterstützte Sprachen:</strong> {model.supported_languages.length > 20 ? (
                      <span>{model.supported_languages.length} Sprachen (z.B. {model.supported_languages.slice(0, 10).join(", ")}...)</span>
                    ) : (
                      <span>{model.supported_languages.join(", ")}</span>
                    )}
                  </div>
                </div>
              );
            })()}

            <div>
              <label className="text-sm text-slate-300 block mb-1">YouTube URL</label>
              <input
                className="bg-slate-800 px-3 py-2 rounded text-sm w-full"
                placeholder="https://youtube.com/watch?v=..."
                value={transcribeUrl}
                onChange={(e) => {
                  let url = e.target.value.trim();
                  // FIX: Unterstütze verschiedene YouTube-URL-Formate
                  if (url && !url.startsWith("http")) {
                    // Wenn nur Video-ID eingegeben wurde, füge Standard-URL hinzu
                    if (url.match(/^[a-zA-Z0-9_-]{11}$/)) {
                      url = `https://www.youtube.com/watch?v=${url}`;
                    } else if (url.includes("youtube.com") || url.includes("youtu.be")) {
                      url = `https://${url}`;
                    }
                  }
                  setTranscribeUrl(url);
                }}
              />
              {transcribeUrl && (
                <p className="text-xs text-slate-400 mt-1">
                  URL: {transcribeUrl}
                </p>
              )}
            </div>

            {selectedModel && availableModels.length > 0 && (() => {
              const model = availableModels.find((m) => m.id === selectedModel);
              if (!model) return null;
              const languages = model.supported_languages || [];
              return (
                <div>
                  <label className="text-sm text-slate-300 block mb-1">Zielsprache</label>
                  <select
                    className="bg-slate-800 px-3 py-2 rounded text-sm w-full"
                    value={transcribeLanguage}
                    onChange={(e) => setTranscribeLanguage(e.target.value)}
                  >
                    {languages.map((lang) => (
                      <option key={lang} value={lang}>
                        {lang === "auto" ? "Automatisch erkennen" : lang.toUpperCase()}
                      </option>
                    ))}
                  </select>
                </div>
              );
            })()}

            <button
              onClick={transcribe}
              className="px-4 py-2 bg-blue-600 rounded text-sm hover:bg-blue-700 w-full disabled:bg-slate-700 disabled:cursor-not-allowed"
              disabled={!transcribeUrl.trim() || !selectedModel || (!apiKey.trim() && !selectedCredentialId)}
            >
              Transkribieren starten
            </button>
          </div>
          ) : (
            /* Translation Mode */
            <div className="space-y-3">
              <div>
                <label className="text-sm text-slate-300 block mb-1">Voice Cloning Provider</label>
                <select
                  className="bg-slate-800 px-3 py-2 rounded text-sm w-full"
                  value={voiceCloningProvider}
                  onChange={(e) => {
                    setVoiceCloningProvider(e.target.value);
                    setVoiceCloningModelId("");
                    setVoiceCloningModels([]);
                    if (e.target.value && orgId) {
                      loadVoiceCloningModels(e.target.value, voiceCloningCredentialId, orgId);
                    }
                  }}
                >
                  <option value="rask">Rask.ai</option>
                  <option value="heygen">HeyGen</option>
                  <option value="elevenlabs">ElevenLabs</option>
                  <option value="falai">Fal.ai</option>
                </select>
              </div>

              <div>
                <label className="text-sm text-slate-300 block mb-1">Credential</label>
                <select
                  className="bg-slate-800 px-3 py-2 rounded text-sm w-full"
                  value={voiceCloningCredentialId}
                  onChange={(e) => {
                    setVoiceCloningCredentialId(e.target.value);
                    if (voiceCloningProvider && orgId) {
                      loadVoiceCloningModels(voiceCloningProvider, e.target.value, orgId);
                    }
                  }}
                >
                  <option value="">Kein Credential (Global)</option>
                  {credentials
                    .filter(c => c.provider === voiceCloningProvider)
                    .map(c => (
                      <option key={c.id} value={c.id}>
                        {c.name} ({c.provider})
                      </option>
                    ))}
                </select>
                <button
                  className="px-3 py-1 bg-blue-600 rounded text-sm mt-2"
                  onClick={() => {
                    if (voiceCloningProvider && orgId) {
                      loadVoiceCloningModels(voiceCloningProvider, voiceCloningCredentialId, orgId);
                    }
                  }}
                  disabled={loadingVoiceModels || !voiceCloningProvider || !orgId}
                >
                  {loadingVoiceModels ? "Lädt..." : "Modelle laden"}
                </button>
              </div>

              {voiceCloningModels.length > 0 && (
                <div>
                  <label className="text-sm text-slate-300 block mb-1">Voice Cloning Modell</label>
                  <select
                    className="bg-slate-800 px-3 py-2 rounded text-sm w-full"
                    value={voiceCloningModelId}
                    onChange={(e) => setVoiceCloningModelId(e.target.value)}
                  >
                    {voiceCloningModels.map((model) => (
                      <option key={model.id} value={model.id}>
                        {model.name} - ${model.cost_per_minute?.toFixed(2) || "0.00"}/Minute
                      </option>
                    ))}
                  </select>
                </div>
              )}

              <div>
                <label className="text-sm text-slate-300 block mb-1">YouTube URL</label>
                <input
                  className="bg-slate-800 px-3 py-2 rounded text-sm w-full"
                  placeholder="https://youtube.com/watch?v=..."
                  value={transcribeUrl}
                  onChange={(e) => {
                    let url = e.target.value.trim();
                    if (url && !url.startsWith("http")) {
                      if (url.match(/^[a-zA-Z0-9_-]{11}$/)) {
                        url = `https://www.youtube.com/watch?v=${url}`;
                      } else if (url.includes("youtube.com") || url.includes("youtu.be")) {
                        url = `https://${url}`;
                      }
                    }
                    setTranscribeUrl(url);
                  }}
                />
              </div>

              <div>
                <label className="text-sm text-slate-300 block mb-1">Zielsprache</label>
                <select
                  className="bg-slate-800 px-3 py-2 rounded text-sm w-full"
                  value={translateTargetLanguage}
                  onChange={(e) => setTranslateTargetLanguage(e.target.value)}
                >
                  <option value="de">Deutsch</option>
                  <option value="en">Englisch</option>
                  <option value="es">Spanisch</option>
                  <option value="fr">Französisch</option>
                  <option value="it">Italienisch</option>
                  <option value="pt">Portugiesisch</option>
                  <option value="ru">Russisch</option>
                  <option value="ja">Japanisch</option>
                  <option value="ko">Koreanisch</option>
                  <option value="zh">Chinesisch</option>
                </select>
              </div>

              {voiceCloningModelId && voiceCloningModels.length > 0 && (() => {
                const model = voiceCloningModels.find(m => m.id === voiceCloningModelId);
                if (!model) return null;
                return (
                  <div className="bg-slate-800 p-3 rounded text-xs space-y-2">
                    <div className="text-slate-300 font-semibold">{model.name}</div>
                    {model.description && (
                      <div className="text-slate-400">{model.description}</div>
                    )}
                    <div className="text-slate-300">
                      <strong>Kosten:</strong> ${model.cost_per_minute?.toFixed(2) || "0.00"} pro Minute generiertes Video
                    </div>
                    {model.supported_languages && (
                      <div className="text-slate-400">
                        <strong>Unterstützte Sprachen:</strong> {model.supported_languages.length > 20 ? (
                          <span>{model.supported_languages.length} Sprachen</span>
                        ) : (
                          <span>{model.supported_languages.join(", ")}</span>
                        )}
                      </div>
                    )}
                  </div>
                );
              })()}

              <button
                onClick={translateVideo}
                className="px-4 py-2 bg-purple-600 rounded text-sm hover:bg-purple-700 w-full disabled:bg-slate-700 disabled:cursor-not-allowed"
                disabled={!transcribeUrl.trim() || !voiceCloningModelId || !voiceCloningCredentialId}
              >
                Video übersetzen (mit Voice Cloning)
              </button>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

export default App;
