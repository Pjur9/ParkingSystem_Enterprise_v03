"use client";

import React, { createContext, useContext, useEffect, useState } from "react";
import { io, Socket } from "socket.io-client";
import { AccessLog, Zone } from "@/types";

interface SocketContextType {
  socket: Socket | null;
  isConnected: boolean;
  logs: AccessLog[];
  zones: Zone[];
}

const SocketContext = createContext<SocketContextType>({
  socket: null,
  isConnected: false,
  logs: [],
  zones: [],
});

export const useSocket = () => useContext(SocketContext);

export const SocketProvider = ({ children }: { children: React.ReactNode }) => {
  const [socket, setSocket] = useState<Socket | null>(null);
  const [isConnected, setIsConnected] = useState(false);
  const [logs, setLogs] = useState<AccessLog[]>([]);
  const [zones, setZones] = useState<Zone[]>([]);

  useEffect(() => {
    // ⚠️ PROMENA: Koristimo 127.0.0.1 umesto localhost radi stabilnosti na Windowsu
    // Uklonili smo 'transports: websocket' da dozvolimo polling ako treba
    const socketInstance = io("http://127.0.0.1:5000", {
      reconnectionAttempts: 5,
      reconnectionDelay: 1000,
      autoConnect: true,
    });

    socketInstance.on("connect", () => {
      console.log("✅ SOCKET CONNECTED! ID:", socketInstance.id);
      setIsConnected(true);
    });

    socketInstance.on("connect_error", (err) => {
      console.error("❌ SOCKET CONNECTION ERROR:", err.message);
    });

    socketInstance.on("disconnect", (reason) => {
      console.warn("⚠️ SOCKET DISCONNECTED:", reason);
      setIsConnected(false);
    });

    // Slušamo događaj 'access_log'
    socketInstance.on("access_log", (data: AccessLog) => {
      console.log("🔔 EVENT RECEIVED (Access Log):", data);
      setLogs((prev) => [data, ...prev].slice(0, 50));
    });

    socketInstance.on("occupancy_update", (data: any) => {
       console.log("📊 EVENT RECEIVED (Occupancy):", data);
    });

    setSocket(socketInstance);

    return () => {
      socketInstance.disconnect();
    };
  }, []);

  return (
    <SocketContext.Provider value={{ socket, isConnected, logs, zones }}>
      {children}
    </SocketContext.Provider>
  );
};