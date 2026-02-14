"use client";
import { useEffect, useState } from "react";
import { Plus, Trash2, Shield, Pencil, X, Check } from "lucide-react";

interface Role {
  id: number;
  name: string;
  description: string;
  can_ignore_capacity: boolean;
  can_ignore_antipassback: boolean;
  is_billable: boolean;
}

export default function RolesPage() {
  const [roles, setRoles] = useState<Role[]>([]);
  const [showModal, setShowModal] = useState(false);
  const [editingId, setEditingId] = useState<number | null>(null);

  const [formData, setFormData] = useState({
    name: "",
    description: "",
    can_ignore_capacity: false,
    can_ignore_antipassback: false,
    is_billable: false
  });

  useEffect(() => { fetchRoles(); }, []);

  const fetchRoles = async () => {
    const res = await fetch("http://127.0.0.1:5000/api/roles/");
    if (res.ok) setRoles(await res.json());
  };

  const handleOpenAdd = () => {
      setEditingId(null);
      setFormData({ name: "", description: "", can_ignore_capacity: false, can_ignore_antipassback: false, is_billable: false });
      setShowModal(true);
  };

  const handleOpenEdit = (role: Role) => {
      setEditingId(role.id);
      setFormData({
          name: role.name,
          description: role.description,
          can_ignore_capacity: role.can_ignore_capacity,
          can_ignore_antipassback: role.can_ignore_antipassback,
          is_billable: role.is_billable
      });
      setShowModal(true);
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    const url = editingId ? `http://127.0.0.1:5000/api/roles/${editingId}` : "http://127.0.0.1:5000/api/roles/";
    const method = editingId ? "PUT" : "POST";

    await fetch(url, {
        method,
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(formData)
    });
    setShowModal(false);
    fetchRoles();
  };

  const handleDelete = async (id: number) => {
    if(confirm("Delete this role?")) {
        await fetch(`http://127.0.0.1:5000/api/roles/${id}`, { method: "DELETE" });
        fetchRoles();
    }
  };

  return (
    <div className="space-y-6">
      <div className="flex justify-between items-center">
        <div>
            <h1 className="text-2xl font-bold text-slate-800">Roles & Permissions</h1>
            <p className="text-slate-500">Define access levels and billing rules</p>
        </div>
        <button onClick={handleOpenAdd} className="bg-blue-600 text-white px-4 py-2 rounded-lg flex gap-2 hover:bg-blue-700">
          <Plus size={18} /> New Role
        </button>
      </div>

      <div className="bg-white rounded-xl shadow-sm border border-slate-200 overflow-hidden">
        <table className="w-full text-left text-sm">
          <thead className="bg-slate-50 text-slate-500 border-b">
            <tr>
              <th className="px-6 py-3">Role Name</th>
              <th className="px-6 py-3">Ignore Capacity?</th>
              <th className="px-6 py-3">Ignore Anti-Passback?</th>
              <th className="px-6 py-3">Is Billable?</th>
              <th className="px-6 py-3 text-right">Actions</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-100">
            {roles.map((role) => (
              <tr key={role.id} className="hover:bg-slate-50">
                <td className="px-6 py-3">
                    <div className="font-bold text-slate-700 flex items-center gap-2">
                        <Shield size={16} className="text-purple-500"/> {role.name}
                    </div>
                    <div className="text-xs text-slate-400">{role.description}</div>
                </td>
                
                {/* Permissions Indicators */}
                <td className="px-6 py-3">
                    {role.can_ignore_capacity ? 
                        <span className="text-green-600 bg-green-50 px-2 py-1 rounded text-xs font-bold">YES</span> : 
                        <span className="text-slate-400 text-xs">No</span>
                    }
                </td>
                <td className="px-6 py-3">
                    {role.can_ignore_antipassback ? 
                        <span className="text-orange-600 bg-orange-50 px-2 py-1 rounded text-xs font-bold">YES</span> : 
                        <span className="text-slate-400 text-xs">No</span>
                    }
                </td>
                <td className="px-6 py-3">
                    {role.is_billable ? 
                        <span className="text-blue-600 bg-blue-50 px-2 py-1 rounded text-xs font-bold">$$$</span> : 
                        <span className="text-slate-400 text-xs">Free</span>
                    }
                </td>

                <td className="px-6 py-3 text-right">
                    <div className="flex justify-end gap-2">
                        <button title = "Edit Role" onClick={() => handleOpenEdit(role)} className="p-2 text-blue-600 hover:bg-blue-50 rounded"><Pencil size={16} /></button>
                        <button title="Delete Role" onClick={() => handleDelete(role.id)} className="p-2 text-red-600 hover:bg-red-50 rounded"><Trash2 size={16} /></button>
                    </div>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {showModal && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
          <div className="bg-white p-6 rounded-xl w-96 relative shadow-xl">
            <button title="showModal" onClick={() => setShowModal(false)} className="absolute top-4 right-4 text-slate-400 hover:text-slate-600"><X size={20} /></button>
            <h2 className="text-xl font-bold mb-4">{editingId ? "Edit Role" : "New Role"}</h2>
            
            <form onSubmit={handleSubmit} className="space-y-4">
              <div>
                <label htmlFor="Role Name" className="block text-xs font-bold text-slate-500 mb-1">Role Name</label>
                <input id = "Role Name" required type="text" className="w-full p-2 border rounded" value={formData.name} onChange={e => setFormData({...formData, name: e.target.value})} />
              </div>
              <div>
                <label htmlFor="Description" className="block text-xs font-bold text-slate-500 mb-1">Description</label>
                <input id = "Description" type="text" className="w-full p-2 border rounded" value={formData.description} onChange={e => setFormData({...formData, description: e.target.value})} />
              </div>

              <div className="space-y-2 pt-2 border-t">
                  <label className="flex items-center gap-2 cursor-pointer">
                      <input type="checkbox" checked={formData.can_ignore_capacity} onChange={e => setFormData({...formData, can_ignore_capacity: e.target.checked})} />
                      <span className="text-sm font-medium">Ignore Capacity (VIP)</span>
                  </label>
                  <label className="flex items-center gap-2 cursor-pointer">
                      <input type="checkbox" checked={formData.can_ignore_antipassback} onChange={e => setFormData({...formData, can_ignore_antipassback: e.target.checked})} />
                      <span className="text-sm font-medium">Ignore Anti-Passback</span>
                  </label>
                  <label className="flex items-center gap-2 cursor-pointer">
                      <input type="checkbox" checked={formData.is_billable} onChange={e => setFormData({...formData, is_billable: e.target.checked})} />
                      <span className="text-sm font-medium">Is Billable (Guest)</span>
                  </label>
              </div>

              <button type="submit" className="w-full bg-blue-600 text-white py-2 rounded hover:bg-blue-700 font-medium">Save Role</button>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}