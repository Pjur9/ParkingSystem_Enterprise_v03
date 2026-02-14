"use client";
import { useEffect, useState } from "react";
import { Settings, ToggleLeft, ToggleRight, ShieldAlert, Activity, AlertTriangle } from "lucide-react";

interface Rule {
  id: number;
  rule_type: string;
  scope: string;
  target_zone_id: number | null;
  is_enabled: boolean;
}

export default function SettingsPage() {
  const [rules, setRules] = useState<Rule[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => { fetchRules(); }, []);

  const fetchRules = async () => {
    try {
        // Prvo inicijalizuj default pravila ako ih nema
        await fetch("http://127.0.0.1:5000/api/rules/init", { method: "POST" });
        
        // Onda povuci listu
        const res = await fetch("http://127.0.0.1:5000/api/rules/");
        if (res.ok) setRules(await res.json());
    } finally {
        setLoading(false);
    }
  };

  const toggleRule = async (id: number) => {
    // Optimistički update (da odmah reaguje UI)
    setRules(rules.map(r => r.id === id ? {...r, is_enabled: !r.is_enabled} : r));
    
    // Poziv API-ja
    await fetch(`http://127.0.0.1:5000/api/rules/${id}/toggle`, { method: "POST" });
  };

  return (
    <div className="space-y-6">
      <div className="flex justify-between items-center">
        <div>
          <h1 className="text-2xl font-bold text-slate-800">System Configuration</h1>
          <p className="text-slate-500">Global rules and validation logic</p>
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        {/* CARD FOR GLOBAL RULES */}
        <div className="bg-white p-6 rounded-xl border border-slate-200 shadow-sm">
            <h3 className="font-bold text-lg mb-4 flex items-center gap-2">
                <ShieldAlert className="text-purple-500" /> Security Rules
            </h3>
            <div className="space-y-4">
                {rules.filter(r => r.scope === "GLOBAL").map(rule => (
                    <div key={rule.id} className="flex justify-between items-center p-3 bg-slate-50 rounded-lg">
                        <div>
                            <div className="font-bold text-sm text-slate-700">{rule.rule_type}</div>
                            <div className="text-xs text-slate-400">Scope: GLOBAL</div>
                        </div>
                        <button onClick={() => toggleRule(rule.id)} className={`transition-colors ${rule.is_enabled ? "text-green-600" : "text-slate-300"}`}>
                            {rule.is_enabled ? <ToggleRight size={32} /> : <ToggleLeft size={32} />}
                        </button>
                    </div>
                ))}
            </div>
        </div>

        {/* CARD FOR ZONE RULES */}
        <div className="bg-white p-6 rounded-xl border border-slate-200 shadow-sm">
            <h3 className="font-bold text-lg mb-4 flex items-center gap-2">
                <Activity className="text-blue-500" /> Zone Logic
            </h3>
            <p className="text-xs text-slate-400 mb-4">
                These rules apply to specific zones (e.g., Garage Capacity). 
                They are created automatically when you seed the database.
            </p>
            <div className="space-y-4 max-h-60 overflow-y-auto">
                {rules.filter(r => r.scope === "ZONE").map(rule => (
                    <div key={rule.id} className="flex justify-between items-center p-3 bg-slate-50 rounded-lg">
                        <div>
                            <div className="font-bold text-sm text-slate-700">{rule.rule_type}</div>
                            <div className="text-xs text-slate-400">Target Zone ID: {rule.target_zone_id}</div>
                        </div>
                        <button onClick={() => toggleRule(rule.id)} className={`transition-colors ${rule.is_enabled ? "text-green-600" : "text-slate-300"}`}>
                            {rule.is_enabled ? <ToggleRight size={32} /> : <ToggleLeft size={32} />}
                        </button>
                    </div>
                ))}
                {rules.filter(r => r.scope === "ZONE").length === 0 && (
                    <div className="text-sm text-slate-400 italic">No zone rules found. Run seed script.</div>
                )}
            </div>
        </div>
      </div>
    </div>
  );
}