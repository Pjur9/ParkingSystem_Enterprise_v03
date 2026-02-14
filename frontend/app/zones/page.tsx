"use client";
import { useEffect, useState } from "react";
import { Plus, Trash2, Map, Layout, X, Pencil } from "lucide-react";

export default function ZonesPage() {
  const [zones, setZones] = useState<any[]>([]);
  
  // Stanje za formu
  const [showModal, setShowModal] = useState(false);
  const [editingId, setEditingId] = useState<number | null>(null); // ID zone koju menjamo
  
  const [formData, setFormData] = useState({ 
    name: "", 
    capacity: 0, 
    parent_zone_id: "" 
  });

  useEffect(() => { fetchZones(); }, []);

  const fetchZones = async () => {
    try {
        const res = await fetch("http://127.0.0.1:5000/api/infra/zones");
        if(res.ok) {
            const data = await res.json();
            if(Array.isArray(data)) setZones(data);
        }
    } catch (e) {
        console.error(e);
    }
  };

  // --- HANDLERS ---
  
  const handleOpenAdd = () => {
      setEditingId(null);
      setFormData({ name: "", capacity: 0, parent_zone_id: "" });
      setShowModal(true);
  };

  const handleOpenEdit = (zone: any) => {
      setEditingId(zone.id);
      setFormData({ 
          name: zone.name, 
          capacity: zone.capacity, 
          parent_zone_id: zone.parent_zone_id ? String(zone.parent_zone_id) : "" 
      });
      setShowModal(true);
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    
    const url = editingId 
        ? `http://127.0.0.1:5000/api/infra/zones/${editingId}`
        : "http://127.0.0.1:5000/api/infra/zones";
        
    const method = editingId ? "PUT" : "POST";

    await fetch(url, {
      method: method,
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(formData)
    });
    
    setShowModal(false);
    fetchZones();
  };

  const handleDelete = async (id: number) => {
    if(confirm("Delete zone?")) {
        await fetch(`http://127.0.0.1:5000/api/infra/zones/${id}`, { method: "DELETE" });
        fetchZones();
    }
  };

  return (
    <div className="space-y-6">
      <div className="flex justify-between items-center">
        <h1 className="text-2xl font-bold text-slate-800">Zones & Capacity</h1>
        <button onClick={handleOpenAdd} className="bg-blue-600 hover:bg-blue-700 text-white px-4 py-2 rounded-lg flex gap-2 transition-colors">
          <Plus size={18} /> Add Zone
        </button>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {Array.isArray(zones) && zones.map((zone) => (
            <div key={zone.id} className="bg-white p-6 rounded-xl border border-slate-200 shadow-sm relative group">
                <div className="flex justify-between items-start mb-4">
                    <div>
                        <h3 className="font-bold text-lg flex items-center gap-2">
                            <Map size={18} className="text-blue-500"/> {zone.name}
                        </h3>
                        <p className="text-xs text-slate-500">Parent: {zone.parent_name}</p>
                    </div>
                    
                    {/* EDIT / DELETE Buttons */}
                    <div className="flex gap-2 opacity-0 group-hover:opacity-100 transition-opacity">
                        <button title="Edit Zone" onClick={() => handleOpenEdit(zone)} className="text-blue-400 hover:text-blue-600 p-1 rounded hover:bg-blue-50">
                            <Pencil size={18} />
                        </button>
                        <button title = "Delete Zone" onClick={() => handleDelete(zone.id)} className="text-red-400 hover:text-red-600 p-1 rounded hover:bg-red-50">
                            <Trash2 size={18} />
                        </button>
                    </div>
                </div>
                
                <div className="mb-1 flex justify-between text-xs font-bold text-slate-500">
                    <span>Occupancy</span>
                    <span>{zone.occupancy} / {zone.capacity}</span>
                </div>
                <div className="w-full bg-slate-100 rounded-full h-2.5">
                    <div className="bg-blue-600 h-2.5 rounded-full" style={{ width: `${(zone.occupancy / zone.capacity) * 100}%` }}></div>
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
            <h2 className="text-xl font-bold mb-4">{editingId ? "Edit Zone" : "New Zone"}</h2>
            <form onSubmit={handleSubmit} className="space-y-4">
              <div>
                <label htmlFor="zoneName" className="block text-xs font-bold text-slate-500">Zone Name</label>
                <input id="zoneName" required type="text" className="w-full p-2 border rounded" 
                  value={formData.name}
                  onChange={e => setFormData({...formData, name: e.target.value})} />
              </div>
              <div>
                <label htmlFor="capacity" className="block text-xs font-bold text-slate-500">Capacity</label>
                <input id="capacity" required type="number" className="w-full p-2 border rounded" 
                  value={formData.capacity}
                  onChange={e => setFormData({...formData, capacity: Number(e.target.value)})} />
              </div>
              <div>
                <label htmlFor="parentZone" className="block text-xs font-bold text-slate-500">Parent Zone</label>
                <select id="parentZone" className="w-full p-2 border rounded"
                  value={formData.parent_zone_id}
                  onChange={e => setFormData({...formData, parent_zone_id: e.target.value})}>
                  <option value="">-- No Parent (Root Zone) --</option>
                  {zones
                    .filter(z => z.id !== editingId) // Ne možeš biti roditelj sam sebi
                    .map(z => <option key={z.id} value={z.id}>{z.name}</option>)}
                </select>
              </div>
              <button type="submit" className="w-full bg-blue-600 text-white py-2 rounded hover:bg-blue-700">
                  {editingId ? "Update Zone" : "Create Zone"}
              </button>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}