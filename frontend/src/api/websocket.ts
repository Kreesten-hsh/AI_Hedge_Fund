import { useEffect, useRef } from 'react';
import { useMonitoringStore } from '../store/monitoringStore';

export const useAegisWebSocket = (topics: string[]) => {
  const updateSnapshot = useMonitoringStore(state => state.updateSnapshot);
  const wsRefs = useRef<{ [topic: string]: WebSocket }>({});

  useEffect(() => {
    topics.forEach(topic => {
      if (!wsRefs.current[topic]) {
        const ws = new WebSocket(`ws://127.0.0.1:8000/ws/dashboard/${topic}`);
        ws.onmessage = (event) => {
          const payload = JSON.parse(event.data);
          updateSnapshot(payload.topic, payload.data);
        };
        wsRefs.current[topic] = ws;
      }
    });

    return () => {
      Object.values(wsRefs.current).forEach(ws => ws.close());
      wsRefs.current = {};
    };
  }, [topics, updateSnapshot]);
};
