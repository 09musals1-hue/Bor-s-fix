from datetime import datetime
from typing import List, Optional
from fastapi import FastAPI, HTTPException, Depends, Query
from fastapi.responses import HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.openapi.docs import get_swagger_ui_html
from fastapi.openapi.utils import get_openapi
from pydantic import BaseModel
from sqlalchemy import create_engine, Column, Integer, String, Text, Boolean, DateTime, ForeignKey
from sqlalchemy.orm import declarative_base, sessionmaker, Session, relationship

# ------------------------------------------------------------------------------
# KONFIGURATION & SÄKERHET
# ------------------------------------------------------------------------------
ADMIN_PASSCODE = "gt3"  # Adminkod för moderering och API-dokumentation

SQLALCHEMY_DATABASE_URL = "sqlite:///./boras_hjalo.db"
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# ------------------------------------------------------------------------------
# 1. DATABASMODELLER
# ------------------------------------------------------------------------------
class ReportModel(Base):
    __tablename__ = "reports"
    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, nullable=False)
    category = Column(String, nullable=False)
    description = Column(Text, nullable=False)
    location = Column(String, nullable=True)
    status = Column(String, default="Mottagen")
    created_at = Column(DateTime, default=datetime.utcnow)


class SuggestionModel(Base):
    __tablename__ = "suggestions"
    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, nullable=False)
    description = Column(Text, nullable=False)
    category = Column(String, nullable=False)
    upvotes = Column(Integer, default=0)
    status = Column(String, default="Inkommet")
    created_at = Column(DateTime, default=datetime.utcnow)


class EventModel(Base):
    __tablename__ = "events"
    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, nullable=False)
    date_time = Column(String, nullable=True)
    description = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)


class PollModel(Base):
    __tablename__ = "polls"
    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, nullable=False)
    description = Column(Text, nullable=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    options = relationship("PollOptionModel", back_populates="poll", cascade="all, delete-orphan")


class PollOptionModel(Base):
    __tablename__ = "poll_options"
    id = Column(Integer, primary_key=True, index=True)
    poll_id = Column(Integer, ForeignKey("polls.id"))
    option_text = Column(String, nullable=False)
    votes = Column(Integer, default=0)
    poll = relationship("PollModel", back_populates="options")


Base.metadata.create_all(bind=engine)


# ------------------------------------------------------------------------------
# 2. SCHEMAS
# ------------------------------------------------------------------------------
class ReportCreate(BaseModel):
    title: str; category: str; description: str; location: Optional[str] = None

class ReportResponse(ReportCreate):
    id: int; status: str; created_at: datetime
    class Config: from_attributes = True


class SuggestionCreate(BaseModel):
    title: str; description: str; category: str

class SuggestionResponse(SuggestionCreate):
    id: int; upvotes: int; status: str; created_at: datetime
    class Config: from_attributes = True


class EventCreate(BaseModel):
    title: str; description: str; date_time: Optional[str] = None

class EventResponse(EventCreate):
    id: int; created_at: datetime
    class Config: from_attributes = True


class PollOptionResponse(BaseModel):
    id: int; option_text: str; votes: int
    class Config: from_attributes = True


class PollResponse(BaseModel):
    id: int; title: str; description: str; is_active: bool; options: List[PollOptionResponse]
    class Config: from_attributes = True


# ------------------------------------------------------------------------------
# 3. FASTAPI APP (SWAGGER INAKTIVERAD PÅ STANDARDADRESSER)
# ------------------------------------------------------------------------------
app = FastAPI(
    title="Borås Hjälp API",
    version="2.3.0",
    docs_url=None,      # Offentlig /docs inaktiverad
    redoc_url=None,     # Offentlig /redoc inaktiverad
    openapi_url=None   # Offentlig /openapi.json inaktiverad
)

app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"])


@app.on_event("startup")
def seed_data():
    db = SessionLocal()
    try:
        if db.query(PollModel).count() == 0:
            poll = PollModel(title="Ska Borås Stad sälja Djurparken?", description="Rösta om Djurparkens framtid.")
            db.add(poll); db.commit(); db.refresh(poll)
            db.add_all([
                PollOptionModel(poll_id=poll.id, option_text="Behåll i kommunal ägo"),
                PollOptionModel(poll_id=poll.id, option_text="Sälja / Privatisera"),
                PollOptionModel(poll_id=poll.id, option_text="Satsa och utveckla parken")
            ])
        if db.query(ReportModel).count() == 0:
            db.add(ReportModel(title="Söndrig bänk i Stadsparken", category="Park & Natur", description="En träbänk har spruckit.", location="Stadsparken", status="Mottagen"))
        if db.query(SuggestionModel).count() == 0:
            db.add(SuggestionModel(title="Nya cykelställ vid Resecentrum", category="Infrastruktur & Cykel", description="Saknas väderskyddade cykelställ för pendlare.", upvotes=38, status="Godkänd"))
        if db.query(EventModel).count() == 0:
            db.add(EventModel(title="IF Elfsborg vs BK Häcken", date_time="Lördag kl 15:00", description="Allsvensk fotbollsmatch på Borås Arena. Kom och stötta gult och svart!"))
        db.commit()
    finally:
        db.close()


# ------------------------------------------------------------------------------
# 4. WEBBGRÄNSNSITT (HTML & JS)
# ------------------------------------------------------------------------------
@app.get("/", response_class=HTMLResponse, include_in_schema=False)
def read_root():
    return """
    <!DOCTYPE html>
    <html lang="sv">
    <head>
        <meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Borås Hjälp</title>
        <script src="https://cdn.tailwindcss.com"></script>
        <link href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css" rel="stylesheet">
    </head>
    <body class="bg-slate-100 min-h-screen text-slate-800 font-sans pb-12">

        <!-- HEADER -->
        <header class="bg-red-700 text-white shadow-md mb-4">
            <div class="max-w-xl mx-auto p-4 text-center">
                <h1 class="text-2xl font-extrabold tracking-tight">Borås Hjälp</h1>
                <p class="text-red-100 text-xs mt-0.5">Din stad. Din röst. Ditt Borås.</p>
            </div>
        </header>

        <!-- MAIN CONTAINER -->
        <main class="max-w-xl mx-auto px-4 space-y-4">

            <!-- STORA RUTOR -->
            <div class="grid grid-cols-2 gap-3">
                <button onclick="nav('forms')" id="btn-forms" class="bg-white border-2 border-red-200 p-4 rounded-2xl shadow-sm hover:shadow-md hover:border-red-500 transition flex flex-col items-center justify-center text-center space-y-2 group">
                    <div class="w-12 h-12 bg-red-100 text-red-700 rounded-full flex items-center justify-center text-xl group-hover:scale-110 transition-transform">
                        <i class="fa-solid fa-wrench"></i>
                    </div>
                    <div>
                        <span class="font-extrabold text-sm text-slate-900 block">Felanmälan & Förslag</span>
                        <span class="text-[10px] text-slate-500">Anmäl fel eller ge idéer</span>
                    </div>
                </button>

                <button onclick="nav('events')" id="btn-events" class="bg-white border-2 border-purple-200 p-4 rounded-2xl shadow-sm hover:shadow-md hover:border-purple-500 transition flex flex-col items-center justify-center text-center space-y-2 group">
                    <div class="w-12 h-12 bg-purple-100 text-purple-700 rounded-full flex items-center justify-center text-xl group-hover:scale-110 transition-transform">
                        <i class="fa-solid fa-calendar-days"></i>
                    </div>
                    <div>
                        <span class="font-extrabold text-sm text-slate-900 block">Händelser & Forum</span>
                        <span class="text-[10px] text-slate-500">Matcher, loppisar m.m.</span>
                    </div>
                </button>

                <button onclick="nav('polls')" id="btn-polls" class="bg-white border-2 border-blue-200 p-4 rounded-2xl shadow-sm hover:shadow-md hover:border-blue-500 transition flex flex-col items-center justify-center text-center space-y-2 group">
                    <div class="w-12 h-12 bg-blue-100 text-blue-700 rounded-full flex items-center justify-center text-xl group-hover:scale-110 transition-transform">
                        <i class="fa-solid fa-square-poll-vertical"></i>
                    </div>
                    <div>
                        <span class="font-extrabold text-sm text-slate-900 block">Omröstningar</span>
                        <span class="text-[10px] text-slate-500">Tyck till om Borås</span>
                    </div>
                </button>

                <button onclick="nav('admin')" id="btn-admin" class="bg-slate-800 border-2 border-slate-900 p-4 rounded-2xl shadow-sm hover:bg-slate-900 transition flex flex-col items-center justify-center text-center space-y-2 group text-white">
                    <div class="w-12 h-12 bg-slate-700 text-amber-400 rounded-full flex items-center justify-center text-xl group-hover:scale-110 transition-transform">
                        <i class="fa-solid fa-shield-halved"></i>
                    </div>
                    <div>
                        <span class="font-extrabold text-sm block">Admin / Kommun</span>
                        <span class="text-[10px] text-slate-400">Begränsad behörighet</span>
                    </div>
                </button>
            </div>

            <!-- DYNAMISK INNEHÅLLSRUTA -->
            <div id="content-box" class="bg-white p-5 rounded-2xl shadow-sm border border-slate-200">
                Laddar innehåll...
            </div>

        </main>

        <script>
            let adminCode = "";

            async function api(path, method='GET', body=null) {
                const opts = { method, headers: {'Content-Type': 'application/json'} };
                if (body) opts.body = JSON.stringify(body);
                const res = await fetch(path, opts);
                if (res.status === 401) return { error: 401 };
                return res.ok ? res.json() : null;
            }

            function nav(sec) {
                const box = document.getElementById('content-box');

                if (sec === 'forms') {
                    box.innerHTML = `
                        <h2 class="font-bold text-base mb-3 text-red-700 flex items-center gap-2">
                            <i class="fa-solid fa-wrench"></i> Felanmälan & Förslag
                        </h2>
                        <form onsubmit="sendForm(event)" class="space-y-3 mb-6 bg-slate-50 p-4 rounded-xl border text-xs">
                            <div>
                                <label class="block font-bold mb-1 text-slate-700">Välj typ av ärende:</label>
                                <select id="f-type" onchange="toggleFormFields(this.value)" class="w-full border p-2.5 rounded-lg bg-white font-bold text-slate-800 shadow-sm">
                                    <option value="report">🛠️ Felanmäla (trasig lampa, väghål, klotter)</option>
                                    <option value="suggestion">💡 Ge ett förslag (nya cykelställ, utegym m.m.)</option>
                                </select>
                            </div>
                            <div>
                                <label class="block font-bold mb-1 text-slate-700">Rubrik</label>
                                <input type="text" id="f-title" required class="w-full border p-2.5 rounded-lg bg-white" placeholder="t.ex. Trasig lyktstolpe på Allégatan">
                            </div>
                            <div class="grid grid-cols-2 gap-2">
                                <div>
                                    <label class="block font-bold mb-1 text-slate-700">Kategori</label>
                                    <input type="text" id="f-cat" required class="w-full border p-2.5 rounded-lg bg-white" placeholder="Gatubelysning, Infrastruktur...">
                                </div>
                                <div id="f-loc-wrap">
                                    <label class="block font-bold mb-1 text-slate-700">Plats / Adress</label>
                                    <input type="text" id="f-loc" class="w-full border p-2.5 rounded-lg bg-white" placeholder="t.ex. Sjöbo 14">
                                </div>
                            </div>
                            <div>
                                <label class="block font-bold mb-1 text-slate-700">Beskrivning</label>
                                <textarea id="f-desc" required oninput="aiCategorize(this.value)" class="w-full border p-2.5 rounded-lg bg-white" rows="3" placeholder="Beskriv ärendet eller din idé..."></textarea>
                                <p id="ai-txt" class="text-[11px] text-blue-600 mt-1 italic hidden"></p>
                            </div>
                            <button type="submit" id="f-btn" class="w-full bg-red-700 hover:bg-red-800 text-white font-bold py-2.5 rounded-lg transition shadow">
                                Skicka Felanmälan
                            </button>
                        </form>

                        <div class="flex gap-4 border-b pb-2 mb-3 text-xs font-bold">
                            <button onclick="loadList('reports')" id="tab-rep" class="text-red-700 border-b-2 border-red-700 pb-1">Inskickade Felanmälningar</button>
                            <button onclick="loadList('suggestions')" id="tab-sug" class="text-slate-400 pb-1">Inkomna Förslag</button>
                        </div>
                        <div id="list-box" class="space-y-2 text-xs">Laddar...</div>
                    `;
                    loadList('reports');
                } else if (sec === 'events') {
                    box.innerHTML = `
                        <h2 class="font-bold text-base mb-3 text-purple-700 flex items-center gap-2">
                            <i class="fa-solid fa-calendar-days"></i> Händelser & Forum
                        </h2>
                        <form onsubmit="sendEvent(event)" class="space-y-3 mb-6 bg-slate-50 p-4 rounded-xl border text-xs">
                            <div>
                                <label class="block font-bold mb-1 text-slate-700">Händelsens Rubrik</label>
                                <input type="text" id="e-title" required class="w-full border p-2.5 rounded-lg bg-white" placeholder="t.ex. IF Elfsborg vs BK Häcken / Loppis i Knalleland">
                            </div>
                            <div>
                                <label class="block font-bold mb-1 text-slate-700">Tid & Plats</label>
                                <input type="text" id="e-time" class="w-full border p-2.5 rounded-lg bg-white" placeholder="t.ex. Lördag kl 15:00 på Borås Arena">
                            </div>
                            <div>
                                <label class="block font-bold mb-1 text-slate-700">Beskrivning</label>
                                <textarea id="e-desc" required class="w-full border p-2.5 rounded-lg bg-white" rows="2" placeholder="Vad händer? Berätta mer..."></textarea>
                            </div>
                            <button type="submit" class="w-full bg-purple-700 hover:bg-purple-800 text-white font-bold py-2.5 rounded-lg transition shadow">
                                Publicera Händelse
                            </button>
                        </form>
                        <h3 class="font-bold text-xs mb-2 text-slate-700">Kommande händelser i Borås:</h3>
                        <div id="events-box" class="space-y-2 text-xs">Laddar händelser...</div>
                    `;
                    loadEvents();
                } else if (sec === 'polls') {
                    box.innerHTML = `
                        <h2 class="font-bold text-base mb-3 text-blue-700 flex items-center gap-2">
                            <i class="fa-solid fa-square-poll-vertical"></i> Kommunala Omröstningar
                        </h2>
                        <div id="polls-box" class="space-y-3 text-xs">Laddar omröstningar...</div>
                    `;
                    loadPolls();
                } else if (sec === 'admin') {
                    if (!adminCode) {
                        box.innerHTML = `
                            <h2 class="font-bold text-base mb-2 text-slate-800">🔐 Admin-inloggning</h2>
                            <p class="text-xs text-slate-500 mb-4">Ange din adminkod för att logga in som administratör.</p>
                            <form onsubmit="loginAdmin(event)" class="space-y-3 text-xs">
                                <input type="password" id="a-pass" placeholder="Mata in adminkod..." class="w-full border p-2.5 rounded-lg" required>
                                <button type="submit" class="w-full bg-slate-800 text-white font-bold py-2.5 rounded-lg hover:bg-slate-900 transition">Logga in</button>
                            </form>
                            <p id="a-err" class="text-xs text-red-600 font-bold mt-2 hidden">Felaktig adminkod!</p>
                        `;
                    } else {
                        renderAdminView();
                    }
                }
            }

            function toggleFormFields(type) {
                const isRep = type === 'report';
                document.getElementById('f-btn').innerText = isRep ? 'Skicka Felanmälan' : 'Skicka Förslag';
                document.getElementById('f-loc-wrap').style.display = isRep ? 'block' : 'none';
                loadList(isRep ? 'reports' : 'suggestions');
            }

            async function sendForm(e) {
                e.preventDefault();
                const type = document.getElementById('f-type').value;
                const body = {
                    title: document.getElementById('f-title').value,
                    category: document.getElementById('f-cat').value,
                    description: document.getElementById('f-desc').value,
                    location: type === 'report' ? document.getElementById('f-loc').value : null
                };
                await api(`/api/${type === 'report' ? 'reports' : 'suggestions'}`, 'POST', body);
                alert('Tack! Din registrering har sparats.');
                nav('forms');
            }

            async function sendEvent(e) {
                e.preventDefault();
                const body = {
                    title: document.getElementById('e-title').value,
                    date_time: document.getElementById('e-time').value,
                    description: document.getElementById('e-desc').value
                };
                await api('/api/events', 'POST', body);
                alert('Händelsen har publicerats!');
                nav('events');
            }

            async function loadList(type) {
                const tabRep = document.getElementById('tab-rep');
                const tabSug = document.getElementById('tab-sug');
                if (tabRep && tabSug) {
                    tabRep.className = type === 'reports' ? "text-red-700 border-b-2 border-red-700 pb-1" : "text-slate-400 pb-1";
                    tabSug.className = type === 'suggestions' ? "text-red-700 border-b-2 border-red-700 pb-1" : "text-slate-400 pb-1";
                }

                const box = document.getElementById('list-box');
                if (!box) return;

                if (type === 'reports') {
                    const data = await api('/api/reports') || [];
                    box.innerHTML = data.map(r => `
                        <div class="p-3 bg-slate-50 rounded-lg border flex justify-between items-center">
                            <div>
                                <span class="font-bold text-slate-800">${r.title}</span> 
                                <span class="text-[10px] bg-slate-200 text-slate-700 px-1.5 py-0.5 rounded ml-1">${r.category}</span>
                                <p class="text-slate-500 text-[11px] mt-0.5">${r.description} ${r.location ? '📍 ' + r.location : ''}</p>
                            </div>
                            <span class="font-bold px-2 py-0.5 rounded text-[10px] ${r.status==='Åtgärdad'?'bg-green-100 text-green-800':'bg-amber-100 text-amber-800'}">${r.status}</span>
                        </div>
                    `).join('') || '<p class="text-slate-400">Inga felanmälningar ännu.</p>';
                } else {
                    const data = await api('/api/suggestions') || [];
                    const c = {'Godkänd':'bg-green-100 text-green-800','Nekad':'bg-red-100 text-red-800','Under utredning':'bg-amber-100 text-amber-800'};
                    box.innerHTML = data.map(s => `
                        <div class="p-3 bg-slate-50 rounded-lg border flex justify-between items-center">
                            <div>
                                <span class="font-bold text-slate-800">${s.title}</span>
                                <span class="text-[10px] font-bold px-1.5 py-0.5 rounded ml-1 ${c[s.status]||'bg-slate-200'}">${s.status}</span>
                                <p class="text-slate-500 text-[11px] mt-0.5">${s.description}</p>
                            </div>
                            <button onclick="upvoteSuggestion(${s.id})" class="bg-white text-red-700 font-bold px-2.5 py-1 rounded-lg border hover:bg-red-50 text-xs shadow-sm">
                                👍 ${s.upvotes}
                            </button>
                        </div>
                    `).join('') || '<p class="text-slate-400">Inga förslag ännu.</p>';
                }
            }

            async function loadEvents() {
                const data = await api('/api/events') || [];
                const box = document.getElementById('events-box');
                if (!box) return;
                box.innerHTML = data.map(ev => `
                    <div class="p-3 bg-slate-50 rounded-lg border">
                        <div class="flex justify-between items-start">
                            <span class="font-bold text-slate-800">${ev.title}</span>
                            ${ev.date_time ? `<span class="text-[10px] bg-purple-100 text-purple-800 font-bold px-2 py-0.5 rounded-full">${ev.date_time}</span>` : ''}
                        </div>
                        <p class="text-slate-600 text-[11px] mt-1">${ev.description}</p>
                    </div>
                `).join('') || '<p class="text-slate-400">Inga händelser inlagda ännu.</p>';
            }

            async function loadPolls() {
                const data = await api('/api/polls') || [];
                const box = document.getElementById('polls-box');
                if (!box) return;
                box.innerHTML = data.map(p => `
                    <div class="p-3.5 bg-slate-50 rounded-xl border space-y-2">
                        <p class="font-bold text-slate-800">${p.title}</p>
                        <p class="text-slate-500 text-[11px]">${p.description}</p>
                        <div class="space-y-1.5 pt-1">
                            ${p.options.map(o => `
                                <button onclick="votePoll(${o.id})" class="w-full text-left p-2.5 bg-white rounded-lg border hover:bg-blue-50 flex justify-between items-center text-xs font-medium transition">
                                    <span>${o.option_text}</span>
                                    <span class="font-bold text-blue-700 bg-blue-50 px-2 py-0.5 rounded border border-blue-100 text-[10px]">${o.votes} röster</span>
                                </button>
                            `).join('')}
                        </div>
                    </div>
                `).join('');
            }

            async function upvoteSuggestion(id) { await api(`/api/suggestions/${id}/upvote`, 'POST'); loadList('suggestions'); }
            async function votePoll(id) { await api(`/api/polls/vote/${id}`, 'POST'); loadPolls(); }

            async function aiCategorize(txt) {
                if (txt.length < 6) return;
                const res = await api('/api/ai/categorize-issue?description=' + encodeURIComponent(txt), 'POST');
                if (res) {
                    const txtEl = document.getElementById('ai-txt');
                    txtEl.innerText = '🤖 AI föreslår kategori: ' + res.suggested_category;
                    txtEl.classList.remove('hidden');
                    document.getElementById('f-cat').value = res.suggested_category;
                }
            }

            // SÄKER ADMIN-INLOGGNING
            async function loginAdmin(e) {
                e.preventDefault();
                const pass = document.getElementById('a-pass').value;
                const checkRes = await api(`/api/reports?admin_code=${encodeURIComponent(pass)}`);
                
                if (checkRes && !checkRes.error) {
                    adminCode = pass;
                    renderAdminView();
                } else {
                    document.getElementById('a-err').classList.remove('hidden');
                }
            }

            async function renderAdminView() {
                const box = document.getElementById('content-box');
                const reports = await api(`/api/reports?admin_code=${encodeURIComponent(adminCode)}`);
                
                if (reports && reports.error === 401) {
                    adminCode = "";
                    nav('admin');
                    return;
                }

                const suggestions = await api('/api/suggestions') || [];
                const events = await api('/api/events') || [];

                box.innerHTML = `
                    <div class="flex justify-between items-center mb-4 pb-2 border-b">
                        <div>
                            <h2 class="font-bold text-base text-slate-800">🔑 Adminpanel (Borås Stad)</h2>
                            <a href="/admin/docs?admin_code=${encodeURIComponent(adminCode)}" target="_blank" class="inline-flex items-center gap-1.5 text-xs font-bold text-blue-600 hover:text-blue-800 bg-blue-50 px-2.5 py-1 rounded-lg border border-blue-200 mt-1">
                                <i class="fa-solid fa-code"></i> 📖 Öppna Swagger API-docs
                            </a>
                        </div>
                        <button onclick="adminCode=''; nav('admin');" class="text-xs bg-red-100 text-red-700 px-2.5 py-1 rounded-full font-bold">Logga ut</button>
                    </div>

                    <div class="space-y-5 text-xs">
                        <div>
                            <h3 class="font-bold mb-2 text-slate-700">🛠️ Felanmälningar (${reports ? reports.length : 0})</h3>
                            <div class="space-y-2">${reports && reports.map ? reports.map(r => `
                                <div class="p-2.5 bg-slate-50 border rounded-lg space-y-1">
                                    <div class="flex justify-between font-bold"><span>${r.title}</span><span class="text-amber-700">${r.status}</span></div>
                                    <p class="text-slate-500 text-[11px]">${r.description}</p>
                                    <div class="flex gap-1.5 pt-1">
                                        <button onclick="mod('reports',${r.id},'status','Under behandling')" class="bg-amber-100 text-amber-800 px-2 py-1 rounded font-bold">Behandla</button>
                                        <button onclick="mod('reports',${r.id},'status','Åtgärdad')" class="bg-green-100 text-green-800 px-2 py-1 rounded font-bold">Åtgärda</button>
                                        <button onclick="mod('reports',${r.id},'del')" class="bg-red-600 text-white px-2 py-1 rounded font-bold ml-auto">Radera</button>
                                    </div>
                                </div>
                            `).join('') : '<p class="text-slate-400">Inga anmälningar.</p>'}</div>
                        </div>

                        <div>
                            <h3 class="font-bold mb-2 text-slate-700">💡 Förslag (${suggestions.length})</h3>
                            <div class="space-y-2">${suggestions.map(s => `
                                <div class="p-2.5 bg-slate-50 border rounded-lg space-y-1">
                                    <div class="flex justify-between font-bold"><span>${s.title}</span><span>Status:${s.status}</span></div>
                                    <p class="text-slate-500 text-[11px]">${s.description}</p>
                                    <div class="flex gap-1.5 pt-1">
                                        <button onclick="mod('suggestions',${s.id},'status','Godkänd')" class="bg-green-100 text-green-800 px-2 py-1 rounded font-bold">Godkänn</button>
                                        <button onclick="mod('suggestions',${s.id},'status','Under utredning')" class="bg-amber-100 text-amber-800 px-2 py-1 rounded font-bold">Utred</button>
                                        <button onclick="mod('suggestions',${s.id},'status','Nekad')" class="bg-slate-200 text-slate-800 px-2 py-1 rounded font-bold">Neka</button>
                                        <button onclick="mod('suggestions',${s.id},'del')" class="bg-red-600 text-white px-2 py-1 rounded font-bold ml-auto">Radera</button>
                                    </div>
                                </div>
                            `).join('') || '<p class="text-slate-400">Inga förslag.</p>'}</div>
                        </div>

                        <div>
                            <h3 class="font-bold mb-2 text-slate-700">📅 Händelser (${events.length})</h3>
                            <div class="space-y-2">${events.map(ev => `
                                <div class="p-2.5 bg-slate-50 border rounded-lg flex justify-between items-center">
                                    <div>
                                        <p class="font-bold">${ev.title} <span class="text-purple-700 text-[10px]">(${ev.date_time || 'Ej angivet'})</span></p>
                                        <p class="text-slate-500 text-[11px]">${ev.description}</p>
                                    </div>
                                    <button onclick="mod('events',${ev.id},'del')" class="bg-red-600 text-white px-2 py-1 rounded font-bold">Radera</button>
                                </div>
                            `).join('') || '<p class="text-slate-400">Inga händelser.</p>'}</div>
                        </div>
                    </div>
                `;
            }

            async function mod(type, id, act, val="") {
                if (act === 'del') {
                    if (confirm('Radera permanent?')) await api(`/api/${type}/${id}?admin_code=${encodeURIComponent(adminCode)}`, 'DELETE');
                } else {
                    await api(`/api/${type}/${id}/status?status=${encodeURIComponent(val)}&admin_code=${encodeURIComponent(adminCode)}`, 'PATCH');
                }
                renderAdminView();
            }

            // INITIAL START
            nav('forms');
        </script>
    </body>
    </html>
    """


# ------------------------------------------------------------------------------
# 5. SKYDDADE SWAGGER ENDPOINTS (ENDAST TILLGÄNGLIGA MED gt3)
# ------------------------------------------------------------------------------
@app.get("/admin/openapi.json", include_in_schema=False)
def get_admin_openapi(admin_code: str = Query(...)):
    if admin_code != ADMIN_PASSCODE:
        raise HTTPException(status_code=401, detail="Felaktig adminkod")
    return get_openapi(title=app.title, version=app.version, routes=app.routes)


@app.get("/admin/docs", response_class=HTMLResponse, include_in_schema=False)
def get_admin_docs(admin_code: str = Query(...)):
    if admin_code != ADMIN_PASSCODE:
        raise HTTPException(status_code=401, detail="Felaktig adminkod")
    return get_swagger_ui_html(
        openapi_url=f"/admin/openapi.json?admin_code={admin_code}",
        title=f"{app.title} - Admin Swagger Docs"
    )


# ------------------------------------------------------------------------------
# 6. API ENDPOINTS (SÄKRADE MED ADMIN_PASSCODE)
# ------------------------------------------------------------------------------
@app.post("/api/reports", response_model=ReportResponse, status_code=201, tags=["Felanmälan"])
def create_report(report: ReportCreate, db: Session = Depends(get_db)):
    r = ReportModel(**report.model_dump()); db.add(r); db.commit(); db.refresh(r); return r


@app.get("/api/reports", response_model=List[ReportResponse], tags=["Felanmälan"])
def get_reports(admin_code: Optional[str] = None, db: Session = Depends(get_db)):
    if admin_code and admin_code != ADMIN_PASSCODE:
        raise HTTPException(status_code=401, detail="Felaktig adminkod")
    return db.query(ReportModel).order_by(ReportModel.created_at.desc()).all()


@app.patch("/api/reports/{report_id}/status", response_model=ReportResponse, tags=["Admin"])
def update_report_status(report_id: int, status: str, admin_code: str = Query(...), db: Session = Depends(get_db)):
    if admin_code != ADMIN_PASSCODE:
        raise HTTPException(status_code=401, detail="Felaktig adminkod")
    r = db.query(ReportModel).filter(ReportModel.id == report_id).first()
    if not r: raise HTTPException(status_code=404, detail="Hittades inte")
    r.status = status; db.commit(); db.refresh(r); return r


@app.delete("/api/reports/{report_id}", tags=["Admin"])
def delete_report(report_id: int, admin_code: str = Query(...), db: Session = Depends(get_db)):
    if admin_code != ADMIN_PASSCODE:
        raise HTTPException(status_code=401, detail="Felaktig adminkod")
    r = db.query(ReportModel).filter(ReportModel.id == report_id).first()
    if not r: raise HTTPException(status_code=404, detail="Hittades inte")
    db.delete(r); db.commit(); return {"message": "Raderad"}


@app.post("/api/events", response_model=EventResponse, status_code=201, tags=["Händelser"])
def create_event(event: EventCreate, db: Session = Depends(get_db)):
    ev = EventModel(**event.model_dump()); db.add(ev); db.commit(); db.refresh(ev); return ev


@app.get("/api/events", response_model=List[EventResponse], tags=["Händelser"])
def get_events(db: Session = Depends(get_db)):
    return db.query(EventModel).order_by(EventModel.created_at.desc()).all()


@app.delete("/api/events/{event_id}", tags=["Admin"])
def delete_event(event_id: int, admin_code: str = Query(...), db: Session = Depends(get_db)):
    if admin_code != ADMIN_PASSCODE:
        raise HTTPException(status_code=401, detail="Felaktig adminkod")
    ev = db.query(EventModel).filter(EventModel.id == event_id).first()
    if not ev: raise HTTPException(status_code=404, detail="Hittades inte")
    db.delete(ev); db.commit(); return {"message": "Raderad"}


@app.post("/api/suggestions", response_model=SuggestionResponse, status_code=201, tags=["Förslag"])
def create_suggestion(suggestion: SuggestionCreate, db: Session = Depends(get_db)):
    s = SuggestionModel(**suggestion.model_dump()); db.add(s); db.commit(); db.refresh(s); return s


@app.get("/api/suggestions", response_model=List[SuggestionResponse], tags=["Förslag"])
def get_suggestions(db: Session = Depends(get_db)):
    return db.query(SuggestionModel).order_by(SuggestionModel.upvotes.desc()).all()


@app.post("/api/suggestions/{suggestion_id}/upvote", response_model=SuggestionResponse, tags=["Förslag"])
def upvote_suggestion(suggestion_id: int, db: Session = Depends(get_db)):
    s = db.query(SuggestionModel).filter(SuggestionModel.id == suggestion_id).first()
    if not s: raise HTTPException(status_code=404, detail="Hittades inte")
    s.upvotes += 1; db.commit(); db.refresh(s); return s


@app.patch("/api/suggestions/{suggestion_id}/status", response_model=SuggestionResponse, tags=["Admin"])
def update_suggestion_status(suggestion_id: int, status: str, admin_code: str = Query(...), db: Session = Depends(get_db)):
    if admin_code != ADMIN_PASSCODE:
        raise HTTPException(status_code=401, detail="Felaktig adminkod")
    s = db.query(SuggestionModel).filter(SuggestionModel.id == suggestion_id).first()
    if not s: raise HTTPException(status_code=404, detail="Hittades inte")
    s.status = status; db.commit(); db.refresh(s); return s


@app.delete("/api/suggestions/{suggestion_id}", tags=["Admin"])
def delete_suggestion(suggestion_id: int, admin_code: str = Query(...), db: Session = Depends(get_db)):
    if admin_code != ADMIN_PASSCODE:
        raise HTTPException(status_code=401, detail="Felaktig adminkod")
    s = db.query(SuggestionModel).filter(SuggestionModel.id == suggestion_id).first()
    if not s: raise HTTPException(status_code=404, detail="Hittades inte")
    db.delete(s); db.commit(); return {"message": "Raderad"}


@app.get("/api/polls", response_model=List[PollResponse], tags=["Omröstningar"])
def get_polls(db: Session = Depends(get_db)):
    return db.query(PollModel).filter(PollModel.is_active == True).all()


@app.post("/api/polls/vote/{option_id}", tags=["Omröstningar"])
def vote_poll(option_id: int, db: Session = Depends(get_db)):
    o = db.query(PollOptionModel).filter(PollOptionModel.id == option_id).first()
    if not o: raise HTTPException(status_code=404, detail="Hittades inte")
    o.votes += 1; db.commit(); return {"message": "Registrerad", "total_votes": o.votes}


@app.post("/api/ai/categorize-issue", tags=["AI"])
def ai_categorize_issue(description: str):
    d = description.lower()
    if any(w in d for w in ["lampa", "mörkt", "belysning", "lyktstolpe"]): cat = "Gatubelysning"
    elif any(w in d for w in ["hål", "asfalt", "väg", "trottoar"]): cat = "Väg & Trafik"
    elif any(w in d for w in ["cykel", "cykelställ", "parkering"]): cat = "Infrastruktur & Cykel"
    elif any(w in d for w in ["bänk", "park", "träd", "gräs", "lekpark"]): cat = "Park & Natur"
    else: cat = "Övrigt"
    return {"suggested_category": cat, "ai_confidence": 0.95}


# ------------------------------------------------------------------------------
# 7. EXEKVERING
# ------------------------------------------------------------------------------
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)