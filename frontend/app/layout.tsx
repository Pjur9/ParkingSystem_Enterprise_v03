// frontend/app/layout.tsx
import type { Metadata } from "next";
import { Inter } from "next/font/google";
import "./globals.css";
import { SocketProvider } from "@/context/SocketContext";
import Link from "next/link";
import { LayoutDashboard, Users, Settings, Car } from "lucide-react";

const inter = Inter({ subsets: ["latin"] });

export const metadata: Metadata = {
  title: "ParkingOS V3.0",
  description: "Enterprise Dashboard",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body className={inter.className}>
        <SocketProvider>
          <div className="flex min-h-screen bg-slate-50 text-slate-900">
            {/* --- SIDEBAR --- */}
            <aside className="w-64 bg-slate-900 text-white flex flex-col fixed h-full">
              <div className="p-6 border-b border-slate-800">
                <h1 className="text-xl font-bold flex items-center gap-2">
                  <Car className="text-blue-500" />
                  ParkingOS <span className="text-xs bg-blue-600 px-1 rounded">V3</span>
                </h1>
              </div>
              
              <nav className="flex-1 p-4 space-y-2">
                <Link href="/" className="flex items-center gap-3 px-4 py-3 text-slate-300 hover:bg-slate-800 hover:text-white rounded-lg transition-colors">
                  <LayoutDashboard size={20} />
                  Dashboard
                </Link>
                <Link href="/users" className="flex items-center gap-3 px-4 py-3 text-slate-300 hover:bg-slate-800 hover:text-white rounded-lg transition-colors">
                  <Users size={20} />
                  User Management
                </Link>
                <Link href="/settings" className="flex items-center gap-3 px-4 py-3 text-slate-300 hover:bg-slate-800 hover:text-white rounded-lg transition-colors">
                  <Settings size={20} />
                  System Rules
                </Link>
                <Link href="/zones" className="flex items-center gap-3 px-4 py-3 text-slate-300 hover:bg-slate-800 hover:text-white rounded-lg transition-colors">
                <LayoutDashboard size={20} /> {/* Možeš promeniti ikonicu */}
                  Zones & Capacity
                </Link>
                <Link href="/gates" className="flex items-center gap-3 px-4 py-3 text-slate-300 hover:bg-slate-800 hover:text-white rounded-lg transition-colors">
                  <Settings size={20} />
                  Gates & Devices
                </Link>
                <Link href="/devices" className="flex items-center gap-3 px-4 py-3 text-slate-300 hover:bg-slate-800 hover:text-white rounded-lg transition-colors">
                  <Settings size={20} />
                    Hardware Devices
                </Link>
                <Link href="/roles" className="flex items-center gap-3 px-4 py-3 text-slate-300 hover:bg-slate-800 hover:text-white rounded-lg transition-colors">
                  <Settings size={20} />
                  Roles & Permissions
                </Link>
              </nav>

              <div className="p-4 border-t border-slate-800 text-xs text-slate-500 text-center">
                Connected to Core: 127.0.0.1
              </div>
            </aside>

            {/* --- MAIN CONTENT --- */}
            <main className="flex-1 ml-64 p-8">
              {children}
            </main>
          </div>
        </SocketProvider>
      </body>
    </html>
  );
}