"use client";

import { useEffect, useState, useRef } from "react";
import { io, Socket } from "socket.io-client";
import { 
  Activity, ShieldCheck, ShieldAlert, Car, 
  Power, ArrowUpCircle, ArrowDownCircle, MoreVertical, 
  Unlock, Lock, Clock 
} from "lucide-react";

// --- TIPOVI PODATAKA ---
interface Log {
  time: string;
  gate_name: string;
  gate_id: number;
  user_name: string;
  role: string;
  credential: string;
  status: "ALLOWED" | "DENIED";
  reason: string;
  is_entry: boolean;
}

interface Gate {
  id: number;
  name: string;
  is_entry: boolean;
  status: "online" | "offline";
}

// --- GATE KARTICA KOMPONENTA ---
// Ovo je "mali prozor" za svaku rampu pojedinačno
function GateCard({ gate, logs, onOpenGate }: { gate: Gate, logs: Log[], onOpenGate: (id: number) => void }) {
  const scrollRef = useRef<HTMLDivElement>(null);

  // Auto-scroll na dno logova kad stigne novi
  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = 0; // Skrolujemo na vrh jer su novi logovi na vrhu
    }
  }, [logs]);

  return (
    <div className="bg-white rounded-xl border border-slate-200 shadow-sm flex flex-col h-full overflow-hidden relative group">
      {/* HEADER KARTICE */}
      <div className={`p-4 border-b flex justify-between items-center ${gate.is_entry ? 'bg-blue-50/50' : 'bg-orange-50/50'}`}>
        <div className="flex items-center gap-3">
          <div className={`p-2 rounded-lg ${gate.is_entry ? 'bg-blue-100 text-blue-600' : 'bg-orange-100 text-orange-600'}`}>
            {gate.is_entry ? <ArrowDownCircle size={20} /> : <ArrowUpCircle size={20} />}
          </div>
          <div>
            <h3 className="font-bold text-slate-800 leading-tight">{gate.name}</h3>
            <div className="flex items-center gap-1.5 mt-0.5">
              <span className={`w-2 h-2 rounded-full ${gate.status === 'online' ? 'bg-green-500 animate-pulse' : 'bg-red-500'}`} />
              <span className="text-[10px] uppercase font-bold text-slate-400 tracking-wider">{gate.status}</span>
            </div>
          </div>
        </div>
        
        {/* AKCIJE (Dugme za otvaranje) */}
        <button 
            onClick={() => onOpenGate(gate.id)}
            className="p-2 bg-white border border-slate-200 text-slate-600 rounded-lg hover:bg-green-50 hover:text-green-600 hover:border-green-200 transition-all active:scale-95 shadow-sm"
            title="Open Gate Manually"
        >
            <Power size={18} />
        </button>
      </div>

      {/* BODY - LISTA LOGOVA */}
      <div className="flex-1 overflow-y-auto bg-slate-50/50 p-2 space-y-2 relative" ref={scrollRef}>
        {logs.length === 0 ? (
          <div className="h-full flex flex-col items-center justify-center text-slate-400 opacity-60">
            <Activity size={32} className="mb-2" />
            <span className="text-xs">No activity yet</span>
          </div>
        ) : (
          logs.map((log, idx) => (
            <div key={idx} className={`p-3 rounded-lg border text-sm shadow-sm flex items-start gap-3 transition-all animate-in fade-in slide-in-from-top-2 duration-300 ${
              log.status === "ALLOWED" 
                ? "bg-white border-green-100 hover:border-green-300" 
                : "bg-red-50 border-red-100 hover:border-red-300"
            }`}>
              <div className={`mt-0.5 ${log.status === "ALLOWED" ? "text-green-500" : "text-red-500"}`}>
                {log.status === "ALLOWED" ? <ShieldCheck size={16} /> : <ShieldAlert size={16} />}
              </div>
              <div className="flex-1 min-w-0">
                <div className="flex justify-between items-start">
                    <p className="font-bold text-slate-700 truncate">{log.user_name}</p>
                    <span className="text-[10px] font-mono text-slate-400 flex items-center gap-1">
                        <Clock size={10} />
                        {new Date(log.time).toLocaleTimeString([], {hour: '2-digit', minute:'2-digit', second:'2-digit'})}
                    </span>
                </div>
                <div className="flex justify-between items-center mt-1">
                    <p className="text-xs text-slate-500 flex items-center gap-1">
                        <span className="px-1.5 py-0.5 bg-slate-100 rounded text-[10px] font-bold">{log.credential.split(':')[0]}</span>
                        <span className="truncate max-w-[80px]">{log.credential.split(':')[1]}</span>
                    </p>
                    {log.status === "DENIED" && (
                        <span className="text-[10px] font-bold text-red-600 bg-red-100 px-1.5 py-0.5 rounded ml-2">
                            {log.reason}
                        </span>
                    )}
                </div>
              </div>
            </div>
          ))
        )}
        
        {/* Overlay gradient na dnu da se vidi da ima još */}
        <div className="absolute bottom-0 left-0 right-0 h-8 bg-gradient-to-t from-slate-50 to-transparent pointer-events-none" />
      </div>

      {/* FOOTER - STATUS BAR */}
      <div className="p-2 border-t bg-white text-[10px] text-slate-400 flex justify-between px-4">
        <span>Log count: {logs.length}</span>
        <span>ID: #{gate.id}</span>
      </div>
    </div>
  );
}


// --- GLAVNA STRANICA ---
export default function Dashboard() {
  const [socket, setSocket] = useState<Socket | null>(null);
  const [gates, setGates] = useState<Gate[]>([]);
  // Ovo je mapa: Key=GateID, Value=Logovi za taj gejt
  const [gateLogs, setGateLogs] = useState<Record<number, Log[]>>({}); 
  const [loading, setLoading] = useState(true);

  // 1. Učitavanje Gejtova (Infrastrukture)
  useEffect(() => {
    const fetchInfrastructure = async () => {
      try {
        // Ovde bi trebalo da zovemo tvoj API /api/gates, ali za demo ćemo mockovati ili zvati pravi ako postoji
        const res = await fetch("http://127.0.0.1:5000/api/infra/gates");
        if(res.ok) {
            const data = await res.json();
            setGates(data);
            
            // Inicijalizuj prazne logove za svaki gejt
            const initialLogs: Record<number, Log[]> = {};
            data.forEach((g: Gate) => initialLogs[g.id] = []);
            setGateLogs(initialLogs);
        }
      } catch (e) {
        console.error("Failed to load gates", e);
      } finally {
        setLoading(false);
      }
    };
    fetchInfrastructure();
  }, []);

  // 2. Socket.IO Konekcija
  useEffect(() => {
    const newSocket = io("http://127.0.0.1:5000", { transports: ["websocket"] });
    setSocket(newSocket);

    newSocket.on("access_log", (newLog: Log) => {
      // Kada stigne log, ubacujemo ga u niz TAČNO ODREĐENOG gejta
      setGateLogs((prevLogs) => {
        const gateId = newLog.gate_id;
        const currentLogs = prevLogs[gateId] || [];
        
        // Dodaj novi na početak, zadrži samo zadnjih 50
        return {
          ...prevLogs,
          [gateId]: [newLog, ...currentLogs].slice(0, 50)
        };
      });
    });

    return () => { newSocket.disconnect(); };
  }, []);

  // 3. Komanda za otvaranje
  const handleOpenGate = async (gateId: number) => {
    try {
        await fetch(`http://127.0.0.1:5000/api/control/${gateId}`, {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({ action: 'open' })
        });
        // Ovde možemo dodati privremeni "Manual Open" log na frontend čisto radi feedbacka
    } catch (e) {
        alert("Failed to connect to gate controller");
    }
  };

  // 4. Logika za Grid Layout (Dinamičko skaliranje)
  const getGridClass = (count: number) => {
    if (count === 1) return "grid-cols-1 max-w-3xl mx-auto h-[600px]";
    if (count === 2) return "grid-cols-1 md:grid-cols-2 h-[600px]"; // Pola pola
    if (count === 3) return "grid-cols-1 md:grid-cols-2 lg:grid-cols-3 h-[400px]"; // Tri u redu (manji)
    if (count === 4) return "grid-cols-1 md:grid-cols-2 h-[800px] md:h-[600px]"; // 2x2
    if (count >= 5) return "grid-cols-1 md:grid-cols-2 lg:grid-cols-3"; // 3 po redu, wrapuje se
    return "grid-cols-1";
  };

  if (loading) return <div className="p-10 text-center text-slate-400">Loading Control Center...</div>;

  return (
    <div className="space-y-6 h-[calc(100vh-100px)] flex flex-col">
      {/* HEADER */}
      <div className="flex justify-between items-center shrink-0">
        <div>
          <h1 className="text-2xl font-bold text-slate-800 flex items-center gap-3">
            <Activity className="text-blue-600" /> 
            Live Control Center
          </h1>
          <p className="text-slate-500">Real-time monitoring and manual override</p>
        </div>
        <div className="flex gap-2">
            <span className="px-3 py-1 bg-green-100 text-green-700 text-xs font-bold rounded-full flex items-center gap-2">
                <span className="w-2 h-2 bg-green-500 rounded-full animate-pulse"></span>
                SYSTEM ONLINE
            </span>
        </div>
      </div>

      {/* DYNAMIC GRID */}
      <div className={`grid gap-6 w-full flex-1 min-h-0 ${getGridClass(gates.length)}`}>
        {gates.map((gate, index) => {
            // Logika za raspored "2 gore, 1 dole" ako ih je 3
            // Ako imamo 3 gejta, i ovo je treći (index 2), neka se raširi preko celog ekrana (col-span-2 ili 3)
            // Ovo je opcionalno, standardni grid je često bolji, ali evo trika:
            const isLastOdd = gates.length % 2 !== 0 && index === gates.length - 1 && gates.length > 1;
            
            return (
                <div key={gate.id} className={`${isLastOdd ? 'md:col-span-2 lg:col-span-1' : ''} min-h-0`}>
                    <GateCard 
                        gate={gate} 
                        logs={gateLogs[gate.id] || []} 
                        onOpenGate={handleOpenGate} 
                    />
                </div>
            );
        })}

        {gates.length === 0 && (
            <div className="col-span-full flex flex-col items-center justify-center bg-slate-50 border-2 border-dashed border-slate-200 rounded-xl p-10 text-slate-400">
                <ShieldAlert size={48} className="mb-4 text-slate-300" />
                <h3 className="text-lg font-bold">No Gates Configured</h3>
                <p>Run the seed script or add gates in database.</p>
            </div>
        )}
      </div>
    </div>
  );
}