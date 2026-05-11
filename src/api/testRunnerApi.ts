import { API_BASE_URL, BROKER_WS_URL, USER_ID } from '../config';

export type TestLog = {
  status: 'pass' | 'fail' | 'info';
  message: string;
};

export type StorageObject = {
  id: string;
  filename: string;
  size: number;
};

export async function getBilling(bucketId: number): Promise<any> {
  const response = await fetch(`${API_BASE_URL}/buckets/${bucketId}/billing`);
  await ensureOk(response, 'get billing');
  return response.json();
}

export function createTestPngBlob(): Promise<Blob> {
  const canvas = document.createElement('canvas');
  canvas.width = 8;
  canvas.height = 8;

  const ctx = canvas.getContext('2d');
  if (!ctx) throw new Error('Canvas is not supported');

  ctx.fillStyle = 'red';
  ctx.fillRect(0, 0, 4, 4);

  ctx.fillStyle = 'green';
  ctx.fillRect(4, 0, 4, 4);

  ctx.fillStyle = 'blue';
  ctx.fillRect(0, 4, 4, 4);

  ctx.fillStyle = 'white';
  ctx.fillRect(4, 4, 4, 4);

  return new Promise((resolve) => {
    canvas.toBlob((blob) => {
      if (!blob) throw new Error('Could not create test PNG');
      resolve(blob);
    }, 'image/png');
  });
}

async function ensureOk(response: Response, name: string): Promise<Response> {
  if (!response.ok) {
    const text = await response.text();
    throw new Error(`${name}: HTTP ${response.status} ${response.statusText}: ${text}`);
  }

  return response;
}

export async function createBucket(): Promise<number> {
  const response = await fetch(`${API_BASE_URL}/buckets/`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      name: `react-ui-test-${Date.now()}`
    })
  });

  await ensureOk(response, 'create bucket');

  const data = await response.json();
  return data.id;
}

export async function uploadTestImage(bucketId: number): Promise<StorageObject> {
  const blob = await createTestPngBlob();
  const formData = new FormData();
  formData.append('file', blob, 'react-ui-test.png');

  const response = await fetch(`${API_BASE_URL}/files/upload`, {
    method: 'POST',
    headers: {
      'x-user-id': USER_ID,
      'bucket-id': String(bucketId)
    },
    body: formData
  });

  await ensureOk(response, 'upload test image');

  return response.json();
}

export async function listObjects(bucketId: number): Promise<StorageObject[]> {
  const response = await fetch(`${API_BASE_URL}/buckets/${bucketId}/objects`);
  await ensureOk(response, 'list objects');

  const data = await response.json();
  return data.items ?? [];
}

export async function downloadObject(fileId: string): Promise<Blob> {
  const response = await fetch(`${API_BASE_URL}/files/${fileId}`, {
    headers: {
      'x-user-id': USER_ID
    }
  });

  await ensureOk(response, 'download object');

  return response.blob();
}

export async function deleteObject(fileId: string): Promise<void> {
  const response = await fetch(`${API_BASE_URL}/files/${fileId}`, {
    method: 'DELETE',
    headers: {
      'x-user-id': USER_ID
    }
  });

  await ensureOk(response, 'delete object');
}

export async function startProcess(
  bucketId: number,
  fileId: string,
  operation: string,
  params: Record<string, unknown> = {}
): Promise<unknown> {
  const response = await fetch(
    `${API_BASE_URL}/buckets/${bucketId}/objects/${fileId}/process`,
    {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'x-user-id': USER_ID
      },
      body: JSON.stringify({
        operation,
        params
      })
    }
  );

  await ensureOk(response, `start process ${operation}`);

  return response.json();
}

export function waitForImageDone(
  sourceFileId: string,
  operation: string,
  timeoutMs = 30000
): Promise<any> {
  return new Promise((resolve, reject) => {
    const ws = new WebSocket(BROKER_WS_URL);

    const timer = window.setTimeout(() => {
      ws.close();
      reject(new Error(`Timeout waiting for image.done operation=${operation}`));
    }, timeoutMs);

    ws.onopen = () => {
      ws.send(JSON.stringify({
        action: 'subscribe',
        topic: 'image.done'
      }));
    };

    ws.onerror = () => {
      window.clearTimeout(timer);
      reject(new Error('WebSocket error while waiting for image.done'));
    };

    ws.onmessage = (event) => {
      const message = JSON.parse(event.data);

      if (message.action !== 'deliver') return;

      const payload = message.payload ?? {};

      if (message.message_id) {
        ws.send(JSON.stringify({
          action: 'ack',
          message_id: message.message_id
        }));
      }

      if (
        payload.source_file_id === sourceFileId &&
        payload.operation === operation
      ) {
        window.clearTimeout(timer);
        ws.close();
        resolve(payload);
      }
    };
  });
}

export function testBroker(): Promise<any> {
  return new Promise((resolve, reject) => {
    const topic = `react-ui-test-topic-${Date.now()}`;
    const text = `hello-${Date.now()}`;

    const subscriber = new WebSocket(BROKER_WS_URL);

    const timer = window.setTimeout(() => {
      subscriber.close();
      reject(new Error('Timeout waiting for broker message'));
    }, 10000);

    subscriber.onopen = () => {
      subscriber.send(JSON.stringify({
        action: 'subscribe',
        topic
      }));

      window.setTimeout(() => {
        const publisher = new WebSocket(BROKER_WS_URL);

        publisher.onopen = () => {
          publisher.send(JSON.stringify({
            action: 'publish',
            topic,
            payload: { text }
          }));

          window.setTimeout(() => publisher.close(), 300);
        };

        publisher.onerror = () => {
          reject(new Error('Publisher websocket error'));
        };
      }, 300);
    };

    subscriber.onerror = () => {
      window.clearTimeout(timer);
      reject(new Error('Subscriber websocket error'));
    };

    subscriber.onmessage = (event) => {
      const message = JSON.parse(event.data);

      if (message.action !== 'deliver') return;

      if (message.payload?.text === text) {
        if (message.message_id) {
          subscriber.send(JSON.stringify({
            action: 'ack',
            message_id: message.message_id
          }));
        }

        window.clearTimeout(timer);
        subscriber.close();
        resolve(message);
      }
    };
  });
}
