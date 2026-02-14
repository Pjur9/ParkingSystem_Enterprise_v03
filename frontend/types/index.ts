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

export interface User {
  id: number;
  full_name: string;
  first_name: string;
  last_name: string;
  role_id: number;
  tenant_id: number | null;
  credential_type: string;
  email?: string;
  role: string;
  tenant: string | null;
  primary_credential?: string;
  is_active: boolean;
}