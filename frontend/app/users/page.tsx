"use client";

import { useEffect, useState } from "react";
import { Plus, User as UserIcon, CreditCard, Pencil, Trash2, X, Car, QrCode, Scan, Mail, Phone } from "lucide-react";
import { User, Credential } from "@/types";

export default function UsersPage() {
  const [users, setUsers] = useState<User[]>([]);
  const [loading, setLoading] = useState(true);

  const [searchQuery, setSearchQuery] = useState("");
  
  // Stanje za formu
  const [showModal, setShowModal] = useState(false);
  const [editingId, setEditingId] = useState<number | null>(null);

  const [roles, setRoles] = useState<{id: number, name: string}[]>([]);
  const [tenants, setTenants] = useState<{id: number, name: string}[]>([]);
  
  // Ažuriran formData sa email i phone_number
  const [formData, setFormData] = useState({
    first_name: "",
    last_name: "",
    email: "",          // NOVO
    phone_number: "",   // NOVO
    role_id: 1,
    tenant_id: "",
    credentials: [] as Credential[] 
  });

  useEffect(() => {
    fetchUsers();
    fetchOptions();
  }, []);

  const fetchUsers = async () => {
    try {
      const res = await fetch("http://127.0.0.1:5000/api/users/");
      const data = await res.json();
      setUsers(data.users);
      setLoading(false);
    } catch (err) {
      console.error("Failed to fetch users", err);
    }
  };

  const filteredUsers = users.filter(user => {
    const term = searchQuery.toLowerCase();
    return (
      user.first_name.toLowerCase().includes(term) ||
      user.last_name.toLowerCase().includes(term) ||
      (user.email && user.email.toLowerCase().includes(term)) ||
      (user.phone_number && user.phone_number.includes(term)) ||
      user.role.toLowerCase().includes(term)
    );
  });

  const fetchOptions = async () => {
    try {
      const res = await fetch("http://127.0.0.1:5000/api/users/options");
      const data = await res.json();
      setRoles(data.roles);
      setTenants(data.tenants);
    } catch (err) {
      console.error("Failed to fetch options", err);
    }
  };

  // --- HANDLERS ZA FORMU ---

  const handleAddCredentialRow = () => {
    setFormData({
      ...formData,
      credentials: [...formData.credentials, { type: "RFID", value: "" }]
    });
  };

  const handleRemoveCredentialRow = (index: number) => {
    const newCreds = [...formData.credentials];
    newCreds.splice(index, 1);
    setFormData({ ...formData, credentials: newCreds });
  };

  const handleChangeCredential = (index: number, field: "type" | "value", val: string) => {
    const newCreds = [...formData.credentials];
    newCreds[index] = { ...newCreds[index], [field]: val };
    setFormData({ ...formData, credentials: newCreds });
  };

  // --- OTVARANJE MODALA ---
  const handleOpenAdd = () => {
    setEditingId(null);
    setFormData({
        first_name: "",
        last_name: "",
        email: "",          // Reset
        phone_number: "",   // Reset
        role_id: roles.length > 0 ? roles[0].id : 1,
        tenant_id: "",
        credentials: [{ type: "RFID", value: "" }] 
    });
    setShowModal(true);
  };

  const handleOpenEdit = (user: User) => {
    setEditingId(user.id);
    setFormData({
        first_name: user.first_name,
        last_name: user.last_name,
        email: user.email || "",                // Load existing
        phone_number: user.phone_number || "",  // Load existing
        role_id: user.role_id,
        tenant_id: user.tenant_id ? String(user.tenant_id) : "",
        credentials: user.credentials.length > 0 
            ? user.credentials.map(c => ({ type: c.type, value: c.value }))
            : [{ type: "RFID", value: "" }]
    });
    setShowModal(true);
  };

  const handleDelete = async (id: number) => {
    if(!confirm("Are you sure you want to delete this user?")) return;
    await fetch(`http://127.0.0.1:5000/api/users/${id}`, { method: "DELETE" });
    fetchUsers();
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      const payload = {
        ...formData,
        tenant_id: formData.tenant_id ? Number(formData.tenant_id) : null,
        role_id: Number(formData.role_id),
        credentials: formData.credentials.filter(c => c.value.trim() !== "")
      };

      const url = editingId ? `http://127.0.0.1:5000/api/users/${editingId}` : "http://127.0.0.1:5000/api/users/";
      const method = editingId ? "PUT" : "POST";

      const res = await fetch(url, {
        method: method,
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload)
      });

      if (res.ok) {
        setShowModal(false);
        fetchUsers();
      } else {
        const err = await res.json();
        alert("Error: " + err.error);
      }
    } catch (error) {
      alert("System Error");
    }
  };

  // Helper za ikonice u tabeli
  const getCredIcon = (type: string) => {
      if(type === "RFID") return <CreditCard size={12} />;
      if(type === "LPR") return <Car size={12} />;
      if(type === "QR") return <QrCode size={12} />;
      return <Scan size={12} />;
  }

  return (
    <div className="space-y-6">
      <div className="flex justify-between items-center">
        <div>
          <h1 className="text-2xl font-bold text-slate-800">User Management</h1>
          <p className="text-slate-500">Manage access credentials and roles</p>
        </div>
        <div className="flex gap-4">
           <input 
             type="text" 
             placeholder="Search users..." 
             className="border p-2 rounded w-64"
             value={searchQuery}
             onChange={(e) => setSearchQuery(e.target.value)}
           />
        </div>
        <button 
          onClick={handleOpenAdd}
          className="bg-blue-600 hover:bg-blue-700 text-white px-4 py-2 rounded-lg flex items-center gap-2 transition-colors"
        >
          <Plus size={18} /> Add New User
        </button>
      </div>

      <div className="bg-white rounded-xl shadow-sm border border-slate-200 overflow-hidden">
        <table className="w-full text-left text-sm">
          <thead className="bg-slate-50 text-slate-500 border-b border-slate-200">
            <tr>
              <th className="px-6 py-3">User Info</th>
              <th className="px-6 py-3">Role & Tenant</th>
              <th className="px-6 py-3">Credentials (Multi)</th>
              <th className="px-6 py-3">Phone Number</th>
              <th className="px-6 py-3">Email</th>
              <th className="px-6 py-3 text-right">Actions</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-100">
            {loading ? (
               <tr><td colSpan={6} className="p-6 text-center">Loading users...</td></tr>
            ) : filteredUsers.map((user) => (
              <tr key={user.id} className="hover:bg-slate-50 group">
                <td className="px-6 py-3">
                    <div className="flex items-center gap-3">
                        <div className="w-8 h-8 rounded-full bg-slate-100 flex items-center justify-center text-slate-500">
                            <UserIcon size={14} />
                        </div>
                        <div>
                            <div className="font-bold text-slate-700">{user.full_name}</div>
                            <div className="text-xs text-slate-400 font-mono">ID: {user.id}</div>
                        </div>
                    </div>
                </td>
                <td className="px-6 py-3">
                    <div className="flex flex-col gap-1 items-start">
                        <span className="px-2 py-0.5 bg-purple-50 text-purple-700 rounded text-xs font-bold border border-purple-100">
                            {user.role}
                        </span>
                        {user.tenant && (
                            <span className="px-2 py-0.5 bg-blue-50 text-blue-700 rounded text-xs border border-blue-100">
                                {user.tenant}
                            </span>
                        )}
                    </div>
                </td>
                <td className="px-6 py-3">
                  <div className="flex flex-wrap gap-2">
                    {user.credentials.length > 0 ? (
                        user.credentials.map((cred, idx) => (
                            <div key={idx} className="flex items-center gap-1 bg-slate-100 px-2 py-1 rounded border border-slate-200 text-xs font-mono text-slate-600">
                                {getCredIcon(cred.type)}
                                <span className="font-bold">{cred.type}:</span>
                                <span>{cred.value}</span>
                            </div>
                        ))
                    ) : (
                        <span className="text-slate-400 italic text-xs">No credentials</span>
                    )}
                  </div>
                </td>
                {/* DODATE KOLONE ZA TELEFON I EMAIL U BODY */}
                <td className="px-6 py-3 text-slate-600">
                    {user.phone_number || "-"}
                </td>
                <td className="px-6 py-3 text-slate-600">
                    {user.email || "-"}
                </td>
                
                <td className="px-6 py-3 text-right">
                    <div className="flex justify-end gap-2 opacity-0 group-hover:opacity-100 transition-opacity">
                        <button onClick={() => handleOpenEdit(user)} className="p-2 text-blue-600 hover:bg-blue-50 rounded" title="Edit">
                            <Pencil size={16} />
                        </button>
                        <button onClick={() => handleDelete(user.id)} className="p-2 text-red-600 hover:bg-red-50 rounded" title="Delete">
                            <Trash2 size={16} />
                        </button>
                    </div>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* MODAL ZA EDITOVANJE */}
      {showModal && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
          <div className="bg-white p-6 rounded-xl shadow-xl w-full max-w-lg relative max-h-[90vh] overflow-y-auto">
            <button title = "setShowModal" onClick={() => setShowModal(false)} className="absolute top-4 right-4 text-slate-400 hover:text-slate-600">
                <X size={20} />
            </button>
            
            <h2 className="text-xl font-bold mb-4">{editingId ? "Edit User" : "Add New User"}</h2>
            
            <form onSubmit={handleSubmit} className="space-y-4">
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label htmlFor="first_name" className="block text-xs font-bold text-slate-500 mb-1">First Name</label>
                  <input id = "first_name" required type="text" className="w-full p-2 border rounded" 
                    value={formData.first_name}
                    onChange={e => setFormData({...formData, first_name: e.target.value})} />
                </div>
                <div>
                  <label htmlFor="last_name" className="block text-xs font-bold text-slate-500 mb-1">Last Name</label>
                  <input id="last_name" required type="text" className="w-full p-2 border rounded" 
                    value={formData.last_name}
                    onChange={e => setFormData({...formData, last_name: e.target.value})} />
                </div>
              </div>

              {/* NOVI RED ZA EMAIL I TELEFON */}
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label htmlFor="email" className="block text-xs font-bold text-slate-500 mb-1">Email</label>
                  <div className="relative">
                    <Mail className="absolute left-2 top-2.5 text-slate-400" size={14} />
                    <input id="email" type="email" className="w-full p-2 pl-8 border rounded" 
                      placeholder="user@example.com"
                      value={formData.email}
                      onChange={e => setFormData({...formData, email: e.target.value})} />
                  </div>
                </div>
                <div>
                  <label htmlFor="phone" className="block text-xs font-bold text-slate-500 mb-1">Phone Number</label>
                  <div className="relative">
                    <Phone className="absolute left-2 top-2.5 text-slate-400" size={14} />
                    <input id="phone" type="text" className="w-full p-2 pl-8 border rounded" 
                      placeholder="+387..."
                      value={formData.phone_number}
                      onChange={e => setFormData({...formData, phone_number: e.target.value})} />
                  </div>
                </div>
              </div>

              <div className="grid grid-cols-2 gap-4">
                <div>
                    <label className="block text-xs font-bold text-slate-500 mb-1">Role</label>
                    <select title = "role_id" className="w-full p-2 border rounded"
                    value={formData.role_id}
                    onChange={e => setFormData({...formData, role_id: Number(e.target.value)})}>
                    {roles.map(r => <option key={r.id} value={r.id}>{r.name}</option>)}
                    </select>
                </div>
                <div>
                    <label className="block text-xs font-bold text-slate-500 mb-1">Tenant</label>
                    <select title = "tenant_id" className="w-full p-2 border rounded"
                    value={formData.tenant_id}
                    onChange={e => setFormData({...formData, tenant_id: e.target.value})}>
                    <option value="">-- No Tenant --</option>
                    {tenants.map(t => <option key={t.id} value={t.id}>{t.name}</option>)}
                    </select>
                </div>
              </div>

              {/* DYNAMIC CREDENTIALS SECTION */}
              <div className="border-t pt-4 mt-4">
                <div className="flex justify-between items-center mb-2">
                    <label className="text-sm font-bold text-slate-700">Access Credentials</label>
                    <button type="button" onClick={handleAddCredentialRow} className="text-xs text-blue-600 hover:text-blue-800 font-bold flex items-center gap-1">
                        <Plus size={14} /> Add Another
                    </button>
                </div>
                
                <div className="space-y-2 bg-slate-50 p-3 rounded-lg">
                    {formData.credentials.map((cred, idx) => (
                        <div key={idx} className="flex gap-2 items-center">
                            <select 
                                title ="Select"
                                className="w-1/3 p-2 border rounded text-sm"
                                value={cred.type}
                                onChange={e => handleChangeCredential(idx, "type", e.target.value)}
                            >
                                <option value="RFID">RFID Card</option>
                                <option value="LPR">License Plate</option>
                                <option value="QR">QR Ticket</option>
                                <option value="PIN">PIN Code</option>
                            </select>
                            <input 
                                type="text" 
                                className="flex-1 p-2 border rounded text-sm font-mono"
                                placeholder="Value (e.g. BG-123-AA)"
                                value={cred.value}
                                onChange={e => handleChangeCredential(idx, "value", e.target.value)}
                            />
                            <button 
                                title = "Remove"
                                type="button"
                                onClick={() => handleRemoveCredentialRow(idx)}
                                className="text-slate-400 hover:text-red-500 p-1"
                            >
                                <X size={16} />
                            </button>
                        </div>
                    ))}
                    {formData.credentials.length === 0 && (
                        <div className="text-center text-xs text-slate-400 py-2">No credentials added. User cannot access.</div>
                    )}
                </div>
              </div>

              <div className="flex justify-end gap-2 mt-6">
                <button type="button" onClick={() => setShowModal(false)} className="px-4 py-2 text-slate-500 hover:bg-slate-100 rounded">Cancel</button>
                <button type="submit" className="px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700">
                    {editingId ? "Save Changes" : "Create User"}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}