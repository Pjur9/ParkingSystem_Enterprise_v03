"use client";

import { useEffect, useState } from "react";
import { Plus, Server, Video, Monitor, Cpu, Trash2, Pencil, X, Link as LinkIcon, AlertCircle } from "lucide-react";

// --- TIPOVI PODATAKA ---
interface Device {
  id: number;
  name: string;
  ip_address: string;
  port: number;
  device_type: string;
  gate_id: number | null;
  gate_name: string;
  is_online: boolean;
}

interface GateOption {
  id: number;
  name: string;
}

export default function DevicesPage() {
  const [devices, setDevices] = useState<Device[]>([]);
  const [gates, setGates] = useState<GateOption[]>([]);
  const [loading, setLoading] = useState(true);
  
  // Stanje za Modal (Forma)
  const [showModal, setShowModal] = useState(false);
  const [editingId, setEditingId] = useState<number | null>(null);

  // Podaci forme
  const [formData, setFormData] = useState({
    name: "",
    ip_address: "",
    port: 80,
    device_type: "CONTROLLER",
    gate_id: ""
  });

  // Učitavanje podataka pri startu
  useEffect(() => {
    fetchDevices();
    fetchOptions();
  }, []);

  const fetchDevices = async () => {
    try {
        const res = await fetch("http://127.0.0.1:5000/api/devices/");
        if(res.ok) setDevices(await res.json());
        setLoading(false);
    } catch (e) { 
        console.error("Failed to fetch devices", e); 
    }
  };

  const fetchOptions = async () => {
    try {
        const res = await fetch("http://127.0.0.1:5000/api/devices/options");
        if(res.ok) {
            const data = await res.json();
            setGates(data.gates);
        }
    } catch (e) { 
        console.error("Failed to fetch options", e); 
    }
  };

  // --- HANDLERS ZA FORMU ---
  const handleOpenAdd = () => {
    setEditingId(null);
    setFormData({ name: "", ip_address: "", port: 80, device_type: "CONTROLLER", gate_id: "" });
    setShowModal(true);
  };

  const handleOpenEdit = (dev: Device) => {
    setEditingId(dev.id);
    setFormData({
        name: dev.name,
        ip_address: dev.ip_address,
        port: dev.port,
        device_type: dev.device_type,
        gate_id: dev.gate_id ? String(dev.gate_id) : ""
    });
    setShowModal(true);
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    const url = editingId ? `http://127.0.0.1:5000/api/devices/${editingId}` : "http://127.0.0.1:5000/api/devices/";
    const method = editingId ? "PUT" : "POST";

    try {
        const res = await fetch(url, {
            method,
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(formData)
        });
        
        if (res.ok) {
            setShowModal(false);
            fetchDevices();
        } else {
            const err = await res.json();
            alert("Error: " + err.error);
        }
    } catch (error) {
        alert("Failed to save device");
    }
  };

  const handleDelete = async (id: number) => {
      if(confirm("Are you sure you want to remove this hardware device?")) {
          await fetch(`http://127.0.0.1:5000/api/devices/${id}`, { method: "DELETE" });
          fetchDevices();
      }
  }

  // --- HELPER ZA IKONICE ---
  const getIcon = (type: string) => {
      if(type.includes("CAMERA") || type.includes("LPR")) return <Video size={18} className="text-blue-500"/>;
      if(type.includes("DISPLAY")) return <Monitor size={18} className="text-purple-500"/>;
      if(type.includes("QR")) return <div className="font-bold text-xs border border-orange-500 text-orange-500 rounded px-1">QR</div>;
      return <Cpu size={18} className="text-slate-500"/>; // Default Controller
  }

  return (
    <div className="space-y-6">
      {/* HEADER STRANICE */}
      <div className="flex justify-between items-center">
        <div>
          <h1 className="text-2xl font-bold text-slate-800">Hardware Devices</h1>
          <p className="text-slate-500">Manage controllers, cameras, and IoT sensors</p>
        </div>
        <button onClick={handleOpenAdd} className="bg-blue-600 hover:bg-blue-700 text-white px-4 py-2 rounded-lg flex items-center gap-2 shadow-sm transition-all active:scale-95">
          <Plus size={18} /> Add Device
        </button>
      </div>

      {/* TABELA UREĐAJA */}
      <div className="bg-white rounded-xl shadow-sm border border-slate-200 overflow-hidden">
        <table className="w-full text-left text-sm">
          <thead className="bg-slate-50 text-slate-500 border-b border-slate-200">
            <tr>
              <th className="px-6 py-3 font-semibold">Device Identity</th>
              <th className="px-6 py-3 font-semibold">Network Config</th>
              <th className="px-6 py-3 font-semibold">Assigned Gate</th>
              <th className="px-6 py-3 text-right font-semibold">Actions</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-100">
            {loading ? (
                <tr><td colSpan={5} className="p-8 text-center text-slate-400">Loading hardware inventory...</td></tr>
            ) : devices.length === 0 ? (
                <tr><td colSpan={5} className="p-8 text-center text-slate-400 flex flex-col items-center gap-2">
                    <Server size={32} className="opacity-20"/>
                    <span>No devices configured yet. Add a controller or camera.</span>
                </td></tr>
            ) : (
                devices.map((dev) => (
                <tr key={dev.id} className="hover:bg-slate-50 group transition-colors">
                    {/* KOLONA: Identity */}
                    <td className="px-6 py-3">
                        <div className="flex items-center gap-3">
                            <div className="p-2 bg-slate-100 rounded-lg shadow-sm border border-slate-200">
                                {getIcon(dev.device_type)}
                            </div>
                            <div>
                                <div className="font-bold text-slate-700">{dev.name}</div>
                                <div className="text-xs text-slate-400 font-mono tracking-tight">{dev.device_type}</div>
                            </div>
                        </div>
                    </td>

                    {/* KOLONA: Network */}
                    <td className="px-6 py-3">
                        <div className="font-mono text-xs bg-slate-100 px-2 py-1 rounded w-fit text-slate-600 border border-slate-200">
                            {dev.ip_address}<span className="text-slate-400">:</span>{dev.port}
                        </div>
                    </td>

                    {/* KOLONA: Gate */}
                    <td className="px-6 py-3">
                        {dev.gate_id ? (
                            <span className="flex items-center gap-1.5 text-blue-700 bg-blue-50 px-2.5 py-1 rounded-full text-xs font-bold w-fit border border-blue-100">
                                <LinkIcon size={12} /> {dev.gate_name}
                            </span>
                        ) : (
                            <span className="flex items-center gap-1 text-slate-400 text-xs italic">
                                <AlertCircle size={12} /> Unassigned
                            </span>
                        )}
                    </td>

                    {/* KOLONA: Actions */}
                    <td className="px-6 py-3 text-right">
                        <div className="flex justify-end gap-2 opacity-0 group-hover:opacity-100 transition-opacity">
                            <button onClick={() => handleOpenEdit(dev)} className="p-2 text-blue-600 hover:bg-blue-50 rounded transition-colors" title="Configure">
                                <Pencil size={16}/>
                            </button>
                            <button onClick={() => handleDelete(dev.id)} className="p-2 text-red-600 hover:bg-red-50 rounded transition-colors" title="Delete">
                                <Trash2 size={16}/>
                            </button>
                        </div>
                    </td>
                </tr>
                ))
            )}
          </tbody>
        </table>
      </div>

      {/* MODAL ZA DODAVANJE/IZMENU */}
      {showModal && (
        <div className="fixed inset-0 bg-black/50 backdrop-blur-sm flex items-center justify-center z-50 animate-in fade-in duration-200">
            <div className="bg-white p-6 rounded-xl w-full max-w-md shadow-2xl relative border border-slate-100 scale-100 animate-in zoom-in-95 duration-200">
                <button title="ShowModale" onClick={() => setShowModal(false)} className="absolute top-4 right-4 text-slate-400 hover:text-slate-600 transition-colors">
                    <X size={20}/>
                </button>
                
                <h2 className="text-xl font-bold mb-1 text-slate-800">
                    {editingId ? "Configure Device" : "Add New Hardware"}
                </h2>
                <p className="text-sm text-slate-500 mb-6">Enter network details for the IoT device.</p>
                
                <form onSubmit={handleSubmit} className="space-y-4">
                    <div>
                        <label className="block text-xs font-bold text-slate-500 mb-1 uppercase tracking-wider">Device Name</label>
                        <input required type="text" 
                            className="w-full p-2.5 border border-slate-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 outline-none transition-all" 
                            value={formData.name} onChange={e => setFormData({...formData, name: e.target.value})} 
                            placeholder="e.g. Entrance LPR Camera"/>
                    </div>
                    
                    <div className="flex gap-4">
                        <div className="flex-1">
                            <label className="block text-xs font-bold text-slate-500 mb-1 uppercase tracking-wider">IP Address</label>
                            <div className="relative">
                                <Server size={16} className="absolute left-3 top-3 text-slate-400"/>
                                <input required type="text" 
                                    className="w-full pl-9 p-2.5 border border-slate-300 rounded-lg font-mono text-sm focus:ring-2 focus:ring-blue-500 outline-none" 
                                    value={formData.ip_address} onChange={e => setFormData({...formData, ip_address: e.target.value})} 
                                    placeholder="192.168.1.X"/>
                            </div>
                        </div>
                        <div className="w-24">
                            <label htmlFor="port" className="block text-xs font-bold text-slate-500 mb-1 uppercase tracking-wider">Port</label>
                            <input id="port" required type="number" 
                                className="w-full p-2.5 border border-slate-300 rounded-lg font-mono text-sm focus:ring-2 focus:ring-blue-500 outline-none" 
                                value={formData.port} onChange={e => setFormData({...formData, port: Number(e.target.value)})}/>
                        </div>
                    </div>

                    <div className="grid grid-cols-2 gap-4">
                        <div>
                            <label htmlFor="" className="block text-xs font-bold text-slate-500 mb-1 uppercase tracking-wider">Device Type</label>
                            <select title="device_type" className="w-full p-2.5 border border-slate-300 rounded-lg bg-white focus:ring-2 focus:ring-blue-500 outline-none" 
                                value={formData.device_type} onChange={e => setFormData({...formData, device_type: e.target.value})}>
                                <option value="CONTROLLER">Gate Controller</option>
                                <option value="LPR_CAMERA">LPR Camera</option>
                                <option value="QR_SCANNER">QR Scanner</option>
                                <option value="DISPLAY">LED Display</option>
                            </select>
                        </div>
                        <div>
                            <label className="block text-xs font-bold text-slate-500 mb-1 uppercase tracking-wider">Assigned Gate</label>
                            <select title = "gate_id" className="w-full p-2.5 border border-slate-300 rounded-lg bg-white focus:ring-2 focus:ring-blue-500 outline-none" 
                                value={formData.gate_id} onChange={e => setFormData({...formData, gate_id: e.target.value})}>
                                <option value="">-- Unassigned --</option>
                                {gates.map(g => <option key={g.id} value={g.id}>{g.name}</option>)}
                            </select>
                        </div>
                    </div>

                    <div className="pt-4 flex gap-3">
                        <button type="button" onClick={() => setShowModal(false)} className="flex-1 py-2.5 border border-slate-300 text-slate-600 rounded-lg hover:bg-slate-50 font-medium transition-colors">
                            Cancel
                        </button>
                        <button type="submit" className="flex-1 py-2.5 bg-blue-600 text-white rounded-lg hover:bg-blue-700 font-medium shadow-md shadow-blue-200 transition-all active:scale-95">
                            {editingId ? "Save Changes" : "Register Device"}
                        </button>
                    </div>
                </form>
            </div>
        </div>
      )}
    </div>
  );
}