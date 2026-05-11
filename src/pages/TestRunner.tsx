import { useState } from 'react';
import {
  IonButton,
  IonCard,
  IonCardContent,
  IonCardHeader,
  IonCardTitle,
  IonChip,
  IonContent,
  IonHeader,
  IonItem,
  IonLabel,
  IonPage,
  IonTitle,
  IonToolbar
} from '@ionic/react';

import {
  createBucket,
  deleteObject,
  downloadObject,
  getBilling,
  listObjects,
  startProcess,
  StorageObject,
  testBroker,
  uploadTestImage,
  waitForImageDone
} from '../api/testRunnerApi';

import './TestRunner.css';

type LogItem = {
  status: 'pass' | 'fail' | 'info';
  message: string;
};

export default function TestRunner() {
  const [logs, setLogs] = useState<LogItem[]>([]);
  const [running, setRunning] = useState(false);
  const [bucketId, setBucketId] = useState<number | null>(null);
  const [fileId, setFileId] = useState<string | null>(null);
  const [objects, setObjects] = useState<StorageObject[]>([]);
  const [previewUrl, setPreviewUrl] = useState<string>('');

  const passed = logs.filter(l => l.status === 'pass').length;
  const failed = logs.filter(l => l.status === 'fail').length;

  function addLog(status: LogItem['status'], message: string) {
    setLogs(prev => [
      {
        status,
        message: `[${new Date().toLocaleTimeString()}] ${message}`
      },
      ...prev
    ]);
  }

  function pass(message: string) {
    addLog('pass', `PASS: ${message}`);
  }

  function fail(message: string, error: unknown) {
    const text = error instanceof Error ? error.message : String(error);
    addLog('fail', `FAIL: ${message} -> ${text}`);
  }

  async function runStorageTest() {
    try {
      addLog('info', 'Starting storage API test...');

      const newBucketId = await createBucket();
      setBucketId(newBucketId);
      pass(`Bucket created ID=${newBucketId}`);

      const uploaded = await uploadTestImage(newBucketId);
      setFileId(uploaded.id);
      pass(`Image uploaded ID=${uploaded.id}`);

      const listed = await listObjects(newBucketId);
      setObjects(listed);
      pass(`Objects listed total=${listed.length}`);

      const blob = await downloadObject(uploaded.id);
      pass(`Downloaded uploaded image size=${blob.size} B`);

      const url = URL.createObjectURL(blob);
      setPreviewUrl(url);
    } catch (error) {
      fail('Storage API test', error);
    }
  }

  async function runBrokerTest() {
    try {
      addLog('info', 'Starting broker test...');
      const message = await testBroker();
      pass(`Broker delivered message on topic ${message.topic}`);
    } catch (error) {
      fail('Broker test', error);
    }
  }

  async function runSingleImageOperation(
    currentBucketId: number,
    currentFileId: string,
    operation: string,
    params: Record<string, unknown> = {}
  ) {
    const donePromise = waitForImageDone(currentFileId, operation);

    await startProcess(currentBucketId, currentFileId, operation, params);
    addLog('info', `Processing started operation=${operation}`);

    const done = await donePromise;

    if (done.status !== 'done') {
      throw new Error(done.error ?? `Worker returned status=${done.status}`);
    }

    const resultId = done.result?.id;

    if (!resultId) {
      throw new Error('image.done does not contain result.id');
    }

    pass(`Image operation ${operation} finished result=${resultId}`);

    const blob = await downloadObject(resultId);
    pass(`Downloaded processed image ${operation}, size=${blob.size} B`);

    const listed = await listObjects(currentBucketId);
    setObjects(listed);

    const url = URL.createObjectURL(blob);
    setPreviewUrl(url);
  }

  async function runImageWorkerTest() {
    try {
      addLog('info', 'Starting image worker test...');

      let currentBucketId = bucketId;
      let currentFileId = fileId;

      if (!currentBucketId) {
        currentBucketId = await createBucket();
        setBucketId(currentBucketId);
        pass(`Bucket created ID=${currentBucketId}`);
      }

      if (!currentFileId) {
        const uploaded = await uploadTestImage(currentBucketId);
        currentFileId = uploaded.id;
        setFileId(uploaded.id);
        pass(`Image uploaded ID=${uploaded.id}`);
      }

      await runSingleImageOperation(currentBucketId, currentFileId, 'grayscale');
      await runSingleImageOperation(currentBucketId, currentFileId, 'invert');
      await runSingleImageOperation(currentBucketId, currentFileId, 'mirror');
      await runSingleImageOperation(currentBucketId, currentFileId, 'brightness', { value: 50 });
      await runSingleImageOperation(currentBucketId, currentFileId, 'crop', {
        x: 1,
        y: 1,
        width: 4,
        height: 4
      });
    } catch (error) {
      fail('Image worker test', error);
    }
  }

  async function runBillingTest() {
    try {
      addLog('info', 'Starting billing test...');

      const currentBucketId = await createBucket();
      setBucketId(currentBucketId);
      pass(`Bucket created ID=${currentBucketId}`);

      const before = await getBilling(currentBucketId);

      const uploaded = await uploadTestImage(currentBucketId);
      setFileId(uploaded.id);
      pass(`External upload done ID=${uploaded.id}`);

      const afterUpload = await getBilling(currentBucketId);

      const ingressDelta = afterUpload.ingress_bytes - before.ingress_bytes;
      const storageDelta = afterUpload.current_storage_bytes - before.current_storage_bytes;

      if (ingressDelta <= 0) {
        throw new Error('ingress_bytes did not increase after external upload');
      }

      if (storageDelta <= 0) {
        throw new Error('current_storage_bytes did not increase after external upload');
      }

      pass(`Ingress increased by ${ingressDelta} B`);
      pass(`Storage increased by ${storageDelta} B`);

      await downloadObject(uploaded.id);

      const afterDownload = await getBilling(currentBucketId);

      const egressDelta = afterDownload.egress_bytes - afterUpload.egress_bytes;

      if (egressDelta <= 0) {
        throw new Error('egress_bytes did not increase after external download');
      }

      pass(`Egress increased by ${egressDelta} B`);

      const beforeWorkerInternal = afterDownload.internal_transfer_bytes;

      await runSingleImageOperation(currentBucketId, uploaded.id, 'grayscale');

      const afterWorker = await getBilling(currentBucketId);

      const internalDelta = afterWorker.internal_transfer_bytes - beforeWorkerInternal;

      if (internalDelta <= 0) {
        throw new Error('internal_transfer_bytes did not increase after worker processing');
      }

      pass(`Internal transfer increased by ${internalDelta} B`);
    } catch (error) {
      fail('Billing test', error);
    }
  }

  async function runSoftDeleteTest() {
    try {
      addLog('info', 'Starting soft delete test...');

      const currentBucketId = await createBucket();
      setBucketId(currentBucketId);
      pass(`Bucket created ID=${currentBucketId}`);

      const uploaded = await uploadTestImage(currentBucketId);
      setFileId(uploaded.id);
      pass(`Uploaded object ID=${uploaded.id}`);

      const beforeDelete = await listObjects(currentBucketId);
      setObjects(beforeDelete);

      const existsBefore = beforeDelete.some(o => o.id === uploaded.id);

      if (!existsBefore) {
        throw new Error('Uploaded object is not visible before delete');
      }

      pass('Object is visible before delete');

      await deleteObject(uploaded.id);
      pass('DELETE request successful');
          
      setFileId(null);

      const afterDelete = await listObjects(currentBucketId);
      setObjects(afterDelete);

      const existsAfter = afterDelete.some(o => o.id === uploaded.id);

      if (existsAfter) {
        throw new Error('Soft deleted object is still visible in bucket listing');
      }

      pass('Soft deleted object is hidden from bucket listing');
    } catch (error) {
      fail('Soft delete test', error);
    }
  }

  async function runAllTests() {
    setRunning(true);
    setLogs([]);
    setObjects([]);
    setPreviewUrl('');
    setBucketId(null);
    setFileId(null);

    await runStorageTest();
    await runBrokerTest();
    await runBillingTest();
    await runSoftDeleteTest();
    await runImageWorkerTest();

    addLog('info', 'All tests finished.');
    setRunning(false);
  }

  async function refreshObjects() {
    if (!bucketId) {
      addLog('info', 'No bucket selected yet.');
      return;
    }

    try {
      const listed = await listObjects(bucketId);
      setObjects(listed);
      pass(`Objects refreshed total=${listed.length}`);
    } catch (error) {
      fail('Refresh objects', error);
    }
  }

  async function previewObject(id: string) {
    try {
      const blob = await downloadObject(id);
      const url = URL.createObjectURL(blob);
      setPreviewUrl(url);
      pass(`Preview loaded file=${id}`);
    } catch (error) {
      fail('Preview object', error);
    }
  }

  return (
    <IonPage>
      <IonHeader>
        <IonToolbar color="primary">
          <IonTitle>Test Runner</IonTitle>
        </IonToolbar>
      </IonHeader>

      <IonContent fullscreen>
        <div className="test-runner-wrap">
          <IonCard>
            <IonCardHeader>
              <IonCardTitle>Ovládání testů</IonCardTitle>
            </IonCardHeader>

            <IonCardContent>
              <div className="test-actions">
                <IonButton disabled={running} onClick={runAllTests}>
                  Spustit všechny testy
                </IonButton>

                <IonButton disabled={running} fill="outline" onClick={runStorageTest}>
                  Test Storage API
                </IonButton>

                <IonButton disabled={running} fill="outline" onClick={runBrokerTest}>
                  Test Broker
                </IonButton>

                <IonButton disabled={running} fill="outline" onClick={runBillingTest}>
                  Test Billing
                </IonButton>

                <IonButton disabled={running} fill="outline" onClick={runSoftDeleteTest}>
                  Test Soft Delete
                </IonButton>

                <IonButton disabled={running} fill="outline" onClick={runImageWorkerTest}>
                  Test Image Worker
                </IonButton>

                <IonButton
                  disabled={running}
                  color="medium"
                  onClick={() => setLogs([])}
                >
                  Vyčistit log
                </IonButton>
              </div>

              <div className="test-summary">
                <IonChip color="success">PASS: {passed}</IonChip>
                <IonChip color="danger">FAIL: {failed}</IonChip>
                <IonChip color="medium">
                  Bucket: {bucketId ?? '-'}
                </IonChip>
                <IonChip color="medium">
                  File: {fileId ? fileId.slice(0, 8) : '-'}
                </IonChip>
              </div>
            </IonCardContent>
          </IonCard>

          <div className="test-grid">
            <IonCard>
              <IonCardHeader>
                <IonCardTitle>Log</IonCardTitle>
              </IonCardHeader>

              <IonCardContent>
                <div className="test-log">
                  {logs.length === 0 && <div className="log-info">Zatím nic neběželo.</div>}

                  {logs.map((log, index) => (
                    <div key={index} className={`log-${log.status}`}>
                      {log.message}
                    </div>
                  ))}
                </div>
              </IonCardContent>
            </IonCard>

            <IonCard>
              <IonCardHeader>
                <IonCardTitle>Objekty a náhled</IonCardTitle>
              </IonCardHeader>

              <IonCardContent>
                <IonButton size="small" fill="outline" onClick={refreshObjects}>
                  Načíst objekty
                </IonButton>

                <div className="object-list">
                  {objects.map(obj => (
                    <IonItem key={obj.id}>
                      <IonLabel>
                        <strong>{obj.filename}</strong>
                        <p>{obj.id} | {obj.size} B</p>
                      </IonLabel>

                      <IonButton slot="end" size="small" onClick={() => previewObject(obj.id)}>
                        Náhled
                      </IonButton>
                    </IonItem>
                  ))}
                </div>

                {previewUrl && (
                  <img className="test-preview" src={previewUrl} alt="preview" />
                )}
              </IonCardContent>
            </IonCard>
          </div>
        </div>
      </IonContent>
    </IonPage>
  );
}
