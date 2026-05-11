import { useEffect, useRef, useState } from 'react';
import { BROKER_WS_URL } from '../config';

export type BrokerDoneMessage = {
  action?: string;
  topic?: string;
  message_id?: number;
  payload?: any;
};

export function useBrokerDone(enabled: boolean) {
  const [messages, setMessages] = useState<BrokerDoneMessage[]>([]);
  const [connected, setConnected] = useState(false);
  const wsRef = useRef<WebSocket | null>(null);

  useEffect(() => {
    if (!enabled) return;

    const ws = new WebSocket(BROKER_WS_URL);
    wsRef.current = ws;

    ws.onopen = () => {
      setConnected(true);
      ws.send(JSON.stringify({
        action: 'subscribe',
        topic: 'image.done'
      }));
    };

    ws.onclose = () => {
      setConnected(false);
    };

    ws.onerror = () => {
      setConnected(false);
    };

    ws.onmessage = (event) => {
      try {
        const message = JSON.parse(event.data);
        setMessages(prev => [message, ...prev].slice(0, 20));

        if (message.message_id) {
          ws.send(JSON.stringify({
            action: 'ack',
            message_id: message.message_id
          }));
        }
      } catch {
        // invalid broker message ignored
      }
    };

    return () => {
      ws.close();
    };
  }, [enabled]);

  return {
    connected,
    messages
  };
}
