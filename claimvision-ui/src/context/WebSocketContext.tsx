"use client";

import React, { createContext, useCallback, useContext, useEffect, useMemo, useRef, useState } from "react";
import { useAuth } from "@/context/AuthContext";

// Event payloads we currently expect from backend
// - From notifier_handler: { type: string, timestamp: string, data: any }
//   Known types when sent via websocket_sender.py: 'file_processed' | 'analysis_complete' | 'export_status'
//   Batch tracker notifications currently arrive as type 'notification' with data containing event-specific fields.
// - From default_handler echoes/acks: 'pong' | 'subscribed' | 'echo'

export type WebSocketStatus = "disconnected" | "connecting" | "connected" | "error";

export type WebSocketMessage = {
  type?: string;
  timestamp?: string | number;
  data?: unknown;
  [k: string]: unknown;
};

interface WebSocketContextType {
  status: WebSocketStatus;
  lastMessage: WebSocketMessage | null;
  send: (payload: unknown) => void;
  subscribeToClaim: (claimId: string) => void;
}

const WebSocketContext = createContext<WebSocketContextType | null>(null);

export const WebSocketProvider = ({ children }: { children: React.ReactNode }) => {
  const { user } = useAuth();
  const [status, setStatus] = useState<WebSocketStatus>("disconnected");
  const [lastMessage, setLastMessage] = useState<WebSocketMessage | null>(null);

  const wsRef = useRef<WebSocket | null>(null);
  const reconnectTimerRef = useRef<number | null>(null);
  const heartbeatTimerRef = useRef<number | null>(null);
  const backoffRef = useRef<number>(1000); // start 1s, max 30s
  const connectRef = useRef<() => void>(() => {});

  const endpoint = useMemo(() => {
    // Prefer env var; fallback to known dev endpoint from deployment output
    return (
      process.env.NEXT_PUBLIC_WS_ENDPOINT ||
      "wss://ws.dev.claimvision.made-something.com"
    );
  }, []);

  const cleanup = useCallback(() => {
    if (heartbeatTimerRef.current) {
      window.clearInterval(heartbeatTimerRef.current);
      heartbeatTimerRef.current = null;
    }
    if (reconnectTimerRef.current) {
      window.clearTimeout(reconnectTimerRef.current);
      reconnectTimerRef.current = null;
    }
    if (wsRef.current) {
      try { wsRef.current.close(); } catch {}
      wsRef.current = null;
    }
  }, []);

  const scheduleReconnect = useCallback(() => {
    if (reconnectTimerRef.current) return; // already scheduled
    const delay = Math.min(backoffRef.current, 30000);
    reconnectTimerRef.current = window.setTimeout(() => {
      reconnectTimerRef.current = null;
      backoffRef.current = Math.min(backoffRef.current * 2, 30000);
      // Use ref to avoid hook dependency cycles
      connectRef.current();
    }, delay);
  }, []);

  const connect = useCallback(() => {
    // Require an ID token to authenticate the $connect route
    const idToken = user?.id_token;
    if (!endpoint || !idToken) {
      cleanup();
      setStatus("disconnected");
      return;
    }

    // Check if token is expired before attempting connection
    try {
      const payload = JSON.parse(atob(idToken.split('.')[1]));
      const now = Math.floor(Date.now() / 1000);
      if (payload.exp && payload.exp <= now) {
        console.warn('[WS] Token expired, cannot connect. Exp:', payload.exp, 'Now:', now);
        setStatus("error");
        return;
      }
      console.warn('[WS] Token valid, expires at:', new Date(payload.exp * 1000).toISOString());
    } catch (e) {
      console.warn('[WS] Invalid token format:', e);
      setStatus("error");
      return;
    }

    try {
      setStatus("connecting");
      const url = `${endpoint}?token=${encodeURIComponent(idToken)}`;
      console.warn('[WS] Attempting connection to:', endpoint);
      const ws = new WebSocket(url);
      wsRef.current = ws;

      ws.onopen = () => {
        setStatus("connected");
        backoffRef.current = 1000; // reset backoff

        // Heartbeat ping every 30s
        heartbeatTimerRef.current = window.setInterval(() => {
          try {
            ws.send(JSON.stringify({ action: "ping" }));
          } catch {}
        }, 30000) as unknown as number;
      };

      ws.onmessage = (event) => {
        try {
          const parsed = JSON.parse(event.data) as unknown;
          // We expect an object with optional type/timestamp/data
          if (parsed && typeof parsed === "object") {
            setLastMessage(parsed as WebSocketMessage);
          }
          console.warn("[WS] message:", parsed);
        } catch {
          console.warn("[WS] non-JSON message:", event.data);
        }
      };

      ws.onclose = () => {
        setStatus("disconnected");
        cleanup();
        scheduleReconnect();
      };

      ws.onerror = () => {
        setStatus("error");
        try { ws.close(); } catch {}
      };
    } catch {
      setStatus("error");
      scheduleReconnect();
    }
  // Only re-run when auth token changes
  }, [endpoint, user?.id_token, cleanup, scheduleReconnect]);

  // Keep a ref to the latest connect callback to break dependency cycles
  useEffect(() => {
    connectRef.current = connect;
  }, [connect]);

  useEffect(() => {
    connect();
    return () => cleanup();
  }, [connect, cleanup]);

  const send = useCallback((payload: unknown) => {
    if (!wsRef.current || wsRef.current.readyState !== WebSocket.OPEN) return;
    try { wsRef.current.send(JSON.stringify(payload)); } catch {}
  }, []);

  const subscribeToClaim = useCallback((claimId: string) => {
    if (!claimId) return;
    send({ action: "subscribe", claimId });
  }, [send]);

  const value = useMemo<WebSocketContextType>(() => ({
    status,
    lastMessage,
    send,
    subscribeToClaim,
  }), [status, lastMessage, send, subscribeToClaim]);

  return (
    <WebSocketContext.Provider value={value}>{children}</WebSocketContext.Provider>
  );
};

export const useWebSocket = (): WebSocketContextType => {
  const ctx = useContext(WebSocketContext);
  if (!ctx) throw new Error("useWebSocket must be used within a WebSocketProvider");
  return ctx;
};
