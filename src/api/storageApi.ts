import { API_BASE_URL, USER_ID } from '../config';

export type Bucket = {
  id: number;
  name: string;
};

export type StorageObject = {
  id: string;
  filename: string;
  size: number;
};

export type BucketObjectsResponse = {
  items: StorageObject[];
  total: number;
};

export type ProcessRequest = {
  operation: string;
  params?: Record<string, unknown>;
};

async function ensureOk(response: Response): Promise<Response> {
  if (!response.ok) {
    const text = await response.text();
    throw new Error(`${response.status} ${response.statusText}: ${text}`);
  }
  return response;
}

export async function createBucket(name: string): Promise<Bucket> {
  const response = await fetch(`${API_BASE_URL}/buckets/`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json'
    },
    body: JSON.stringify({ name })
  });

  await ensureOk(response);
  return response.json();
}

export async function listBucketObjects(bucketId: number): Promise<BucketObjectsResponse> {
  const response = await fetch(`${API_BASE_URL}/buckets/${bucketId}/objects`);
  await ensureOk(response);
  return response.json();
}

export async function uploadObject(bucketId: number, file: File): Promise<StorageObject> {
  const formData = new FormData();
  formData.append('file', file);

  const response = await fetch(`${API_BASE_URL}/files/upload`, {
    method: 'POST',
    headers: {
      'x-user-id': USER_ID,
      'bucket-id': String(bucketId)
    },
    body: formData
  });

  await ensureOk(response);
  return response.json();
}

export function getObjectUrl(fileId: string): string {
  return `${API_BASE_URL}/files/${fileId}`;
}

export async function downloadObjectBlob(fileId: string): Promise<Blob> {
  const response = await fetch(getObjectUrl(fileId), {
    headers: {
      'x-user-id': USER_ID
    }
  });

  await ensureOk(response);
  return response.blob();
}

export async function startImageProcess(
  bucketId: number,
  fileId: string,
  request: ProcessRequest
): Promise<unknown> {
  const response = await fetch(
    `${API_BASE_URL}/buckets/${bucketId}/objects/${fileId}/process`,
    {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'x-user-id': USER_ID
      },
      body: JSON.stringify(request)
    }
  );

  await ensureOk(response);
  return response.json();
}
