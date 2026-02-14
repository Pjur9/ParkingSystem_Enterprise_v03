"use client";
import { useEffect, useState } from "react";
import { Plus, Trash2, ArrowRight, Server, X, Pencil } from "lucide-react";

export default function GatesPage() {
  const [gates, setGates] = useState<any[]>([]);
  const [zones, setZones] = useState<any[]>([]);
  
  // Stanje za formu
  const [showModal, setShowModal] = useState(false);
  const [editingId, setEditingId] = useState<number | null>(null);
  const [formData, setFormData] = useState({ name: "", zone_from_id: "", zone_to_id: "" });

  useEffect(() => { fetchGates(); fetchZones(); }, []);

  const fetchGates = async () => {
    try {
        const res = await fetch("http://127.0.0.1:5000/api/infra/gates");
        if(res.ok) {
            const data = await res.json();
            if(Array.isArray(data)) setGates(data);
        }
    } catch(e) { console.error(e); }
  };
  
  const fetchZones = async () => {
    try {
        const res = await fetch("http://127.0.0.1:5000/api/infra/zones");
        if(res.ok) setZones(await res.json());
    } catch(e) { console.error(e); }
  };

  // --- HANDLERS ---

  const handleOpenAdd = () => {
      setEditingId(null);
      setFormData({ name: "", zone_from_id: "", zone_to_id: "" });
      setShowModal(true);
  };

  const handleOpenEdit = (gate: any) => {
      setEditingId(gate.id);
      setFormData({ 
          name: gate.name, 
          zone_from_id: gate.zone_from_id ? String(gate.zone_from_id) : "", 
          zone_to_id: gate.zone_to_id ? String(gate.zone_to_id) : "" 
      });
      setShowModal(true);
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    
    const url = editingId 
        ? `http://127.0.0.1:5000/api/infra/gates/${editingId}`
        : "http://127.0.0.1:5000/api/infra/gates";
    
    const method = editingId ? "PUT" : "POST";

    await fetch(url, {
      method: method,
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(formData)
    });
    
    setShowModal(false);
    fetchGates();
  };

  const handleDelete = async (id: number) => {
    if(confirm("Delete gate?")) {
        await fetch(`http://127.0.0.1:5000/api/infra/gates/${id}`, { method: "DELETE" });
        fetchGates();
    }
  };

  return (
    <div className="space-y-6">
      <div className="flex justify-between items-center">
        <h1 className="text-2xl font-bold text-slate-800">Gates & Devices</h1>
        <button onClick={handleOpenAdd} className="bg-blue-600 hover:bg-blue-700 text-white px-4 py-2 rounded-lg flex gap-2 transition-colors">
          <Plus size={18} /> Add Gate
        </button>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        {Array.isArray(gates) && gates.map((gate) => (
            <div key={gate.id} className="bg-white p-6 rounded-xl border border-slate-200 shadow-sm relative group">
                <div className="flex justify-between items-start mb-4">
                    <h3 className="font-bold text-lg flex items-center gap-2">
                        <Server size={18} className={gate.is_online ? "text-green-500" : "text-red-500"}/> 
                        {gate.name}
                    </h3>
                    
                    {/* EDIT / DELETE Buttons */}
                    <div className="flex gap-2 opacity-0 group-hover:opacity-100 transition-opacity">
                         <button title="Edit Gate" onClick={() => handleOpenEdit(gate)} className="text-blue-400 hover:text-blue-600 p-1 rounded hover:bg-blue-50">
                            <Pencil size={18} />
                        </button>
                        <button title = "Delete Gate" onClick={() => handleDelete(gate.id)} className="text-red-400 hover:text-red-600 p-1 rounded hover:bg-red-50">
                            <Trash2 size={18} />
                        </button>
                    </div>
                </div>
                
                <div className="flex items-center justify-between bg-slate-50 p-3 rounded-lg text-sm">
                    <span className="font-medium text-slate-600 truncate w-1/3 text-center">{gate.zone_from_name}</span>
                    <ArrowRight size={16} className="text-slate-400" />
                    <span className="font-medium text-slate-600 truncate w-1/3 text-center">{gate.zone_to_name}</span>
                </div>
                <div className="mt-2 text-xs text-center text-slate-400 uppercase font-mono">
                    ID: {gate.id}
                </div>
            </div>
        ))}
      </div>

      {showModal && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
          <div className="bg-white p-6 rounded-xl w-96 relative shadow-2xl">
             <button 
                title="Show Modal"
                onClick={() => setShowModal(false)}
                className="absolute top-4 right-4 text-slate-400 hover:text-slate-600">
                <X size={20} />
            </button>
            <h2 className="text-xl font-bold mb-4">{editingId ? "Edit Gate" : "New Gate"}</h2>
            <form onSubmit={handleSubmit} className="space-y-4">
              <div>
                <label htmlFor="gateName" className="block text-xs font-bold text-slate-500">Gate Name</label>
                <input id="gateName" required type="text" className="w-full p-2 border rounded" 
                  value={formData.name}
                  onChange={e => setFormData({...formData, name: e.target.value})} />
              </div>
              <div className="grid grid-cols-2 gap-2">
                  <div>
                    <label htmlFor="fromZone" className="block text-xs font-bold text-slate-500">From (Entry)</label>
                    <select id="fromZone" className="w-full p-2 border rounded text-xs"
                      value={formData.zone_from_id}
                      onChange={e => setFormData({...formData, zone_from_id: e.target.value})}>
                      <option value="">World (Outside)</option>
                      {zones.map(z => <option key={z.id} value={z.id}>{z.name}</option>)}
                    </select>
                  </div>
                  <div>
                    <label htmlFor="toZone" className="block text-xs font-bold text-slate-500">To (Destination)</label>
                    <select id="toZone" className="w-full p-2 border rounded text-xs"
                      value={formData.zone_to_id}
                      onChange={e => setFormData({...formData, zone_to_id: e.target.value})}>
                      <option value="">World (Outside)</option>
                      {zones.map(z => <option key={z.id} value={z.id}>{z.name}</option>)}
                    </select>
                  </div>
              </div>
              <button type="submit" className="w-full bg-blue-600 text-white py-2 rounded hover:bg-blue-700">
                  {editingId ? "Update Gate" : "Create Gate"}
              </button>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}