export interface Zone {
  id: number;
  name: string;
  capacity: number;
  occupancy: number;
  percent_full: number;
  children?: Zone[];
}

export interface AccessLog {
  id?: number;
  time: string;
  gate_name: string;
  user_name: string;
  role: string;
  credential: string;
  status: 'ALLOWED' | 'DENIED';
  reason: string;
  is_entry: boolean;
}

export interface Gate {
  id: number;
  name: string;
  active_rules: string[];
  is_online: boolean;
}

export interface Credential {
  type: string;
  value: string;
}

export interface User {
  id: number;
  first_name: string;
  last_name: string;
  full_name: string;      // Ovo smo dodali na backendu
  email?: string;         // Opciono jer može biti null
  phone_number?: string;  // Opciono
  role: string;
  role_id: number;
  tenant: string | null;
  tenant_id: number | null;
  credentials: Credential[]; // Niz kredencijala
  is_active: boolean;
}