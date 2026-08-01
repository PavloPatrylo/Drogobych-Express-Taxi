import React, { createContext, useContext, useState, useEffect, useRef } from 'react';

const WebSocketContext = createContext();

export function WebSocketProvider({ children }) {
  const [isConnected, setIsConnected] = useState(false);
  const [lastEvent, setLastEvent] = useState(null);
  const socketRef = useRef(null);
  const reconnectTimeoutRef = useRef(null);

  const getWsUrl = () => {
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const hostname = window.location.hostname || 'localhost';
    const port = window.location.port;

    // If running under Vite dev server (e.g. port 3000 or 5173), target backend 8000 directly
    if (port === '3000' || port === '5173') {
      return `${protocol}//${hostname}:8000/ws`;
    }
    // Production or proxied host
    return `${protocol}//${window.location.host}/ws`;
  };

  const connect = () => {
    try {
      const wsUrl = getWsUrl();
      console.log('🔌 Connecting WebSocket to:', wsUrl);

      const ws = new WebSocket(wsUrl);
      socketRef.current = ws;

      ws.onopen = () => {
        console.log('✅ WebSocket Connected Successfully');
        setIsConnected(true);
      };

      ws.onmessage = (e) => {
        try {
          const parsed = JSON.parse(e.data);
          if (parsed.event === 'pong') return;
          console.log('📡 WebSocket Event Received:', parsed);
          setLastEvent({ ...parsed, timestamp: Date.now() });
        } catch (err) {
          console.error('Failed to parse WebSocket message:', err);
        }
      };

      ws.onclose = () => {
        console.warn('⚠️ WebSocket Disconnected. Retrying in 3s...');
        setIsConnected(false);
        reconnectTimeoutRef.current = setTimeout(connect, 3000);
      };

      ws.onerror = (err) => {
        console.error('WebSocket Connection Error:', err);
        ws.close();
      };
    } catch (err) {
      console.error('WebSocket Init Error:', err);
      reconnectTimeoutRef.current = setTimeout(connect, 5000);
    }
  };

  useEffect(() => {
    connect();
    const pingInterval = setInterval(() => {
      if (socketRef.current && socketRef.current.readyState === WebSocket.OPEN) {
        socketRef.current.send('ping');
      }
    }, 15000);

    return () => {
      clearInterval(pingInterval);
      if (reconnectTimeoutRef.current) clearTimeout(reconnectTimeoutRef.current);
      if (socketRef.current) socketRef.current.close();
    };
  }, []);

  return (
    <WebSocketContext.Provider value={{ isConnected, lastEvent }}>
      {children}
    </WebSocketContext.Provider>
  );
}

export function useWebSocket() {
  return useContext(WebSocketContext);
}
