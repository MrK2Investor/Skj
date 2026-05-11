import { useMemo, useState } from 'react';
import {
  IonButton,
  IonCardTitle,
  IonInput,
  IonItem,
  IonLabel,
  IonSelect,
  IonSelectOption,
  IonTextarea,
  IonToast
} from '@ionic/react';

import {
  createBucket,
  downloadObjectBlob,
  listBucketObjects,
  startImageProcess,
  StorageObject,
  uploadObject
} from '../api/storageApi';

import { useBrokerDone } from '../hooks/useBrokerDone';

type Operation = 'negative' | 'mirror' | 'crop' | 'brightness' | 'grayscale';

export default function StorageDashboard() {
  const [bucketName, setBucketName] = useState('images');
  const [bucketId, setBucketId] = useState<number | null>(null);
  const [objects, setObjects] = useState<StorageObject[]>([]);
  const [selectedObjectId, setSelectedObjectId] = useState<string>('');
  const [selectedFile, setSelectedFile] = useState<File | null>(null);

  const [operation, setOperation] = useState<Operation>('grayscale');
  const [brightness, setBrightness] = useState<number>(50);
  const [cropX, setCropX] = useState<number>(100);
  const [cropY, setCropY] = useState<number>(100);
  const [cropWidth, setCropWidth] = useState<number>(300);
  const [cropHeight, setCropHeight] = useState<number>(300);

  const [previewUrl, setPreviewUrl] = useState<string>('');
  const [status, setStatus] = useState('Ready.');
  const [toast, setToast] = useState('');

  const { connected, messages } = useBrokerDone(true);

  const selectedObject = useMemo(
    () => objects.find(o => o.id === selectedObjectId),
    [objects, selectedObjectId]
  );

  async function refreshObjects(id = bucketId) {
    if (!id) return;

    const result = await listBucketObjects(id);
    setObjects(result.items);

    if (!selectedObjectId && result.items.length > 0) {
      setSelectedObjectId(result.items[0].id);
    }
  }

  async function handleCreateBucket() {
    try {
      const bucket = await createBucket(bucketName);
      setBucketId(bucket.id);
      setStatus(`Bucket created: ${bucket.name} / ID ${bucket.id}`);
      setToast('Bucket vytvořen');
      await refreshObjects(bucket.id);
    } catch (error: any) {
      setStatus(error.message);
      setToast('Chyba při vytvoření bucketu');
    }
  }

  async function handleUpload() {
    if (!bucketId) {
      setToast('Nejdřív vytvoř nebo nastav bucket ID');
      return;
    }

    if (!selectedFile) {
      setToast('Vyber obrázek');
      return;
    }

    try {
      const uploaded = await uploadObject(bucketId, selectedFile);
      setSelectedObjectId(uploaded.id);
      setStatus(`Uploaded: ${uploaded.filename} (${uploaded.id})`);
      setToast('Soubor nahrán');
      await refreshObjects(bucketId);
    } catch (error: any) {
      setStatus(error.message);
      setToast('Chyba uploadu');
    }
  }

  async function handlePreview(fileId = selectedObjectId) {
    if (!fileId) return;

    try {
      const blob = await downloadObjectBlob(fileId);
      if (previewUrl) URL.revokeObjectURL(previewUrl);
      setPreviewUrl(URL.createObjectURL(blob));
      setStatus(`Preview loaded: ${fileId}`);
    } catch (error: any) {
      setStatus(error.message);
      setToast('Chyba při stažení náhledu');
    }
  }

  function buildProcessRequest() {
    if (operation === 'brightness') {
      return {
        operation,
        params: {
          value: Number(brightness)
        }
      };
    }

    if (operation === 'crop') {
      return {
        operation,
        params: {
          x: Number(cropX),
          y: Number(cropY),
          width: Number(cropWidth),
          height: Number(cropHeight)
        }
      };
    }

    return {
      operation
    };
  }

  async function handleProcess() {
    if (!bucketId || !selectedObjectId) {
      setToast('Vyber bucket a objekt');
      return;
    }

    try {
      const request = buildProcessRequest();
      const result = await startImageProcess(bucketId, selectedObjectId, request);
      setStatus(`Processing started:\n${JSON.stringify(result, null, 2)}`);
      setToast('Processing spuštěn');
    } catch (error: any) {
      setStatus(error.message);
      setToast('Chyba při spuštění zpracování');
    }
  }

  return (
    <div className="page-wrap">
      <div className="grid">
        <div className="card">
          <IonCardTitle>1. Bucket</IonCardTitle>

          <IonItem>
            <IonLabel position="stacked">Název bucketu</IonLabel>
            <IonInput
              value={bucketName}
              onIonInput={e => setBucketName(String(e.detail.value ?? ''))}
            />
          </IonItem>

          <IonItem>
            <IonLabel position="stacked">Bucket ID</IonLabel>
            <IonInput
              type="number"
              value={bucketId ?? ''}
              placeholder="můžeš zadat existující bucket ID"
              onIonInput={e => {
                const value = Number(e.detail.value);
                setBucketId(Number.isFinite(value) && value > 0 ? value : null);
              }}
            />
          </IonItem>

          <div style={{ display: 'flex', gap: 10, marginTop: 14 }}>
            <IonButton onClick={handleCreateBucket}>Vytvořit bucket</IonButton>
            <IonButton fill="outline" onClick={() => refreshObjects()}>
              Načíst objekty
            </IonButton>
          </div>
        </div>

        <div className="card">
          <IonCardTitle>2. Upload obrázku</IonCardTitle>

          <input
            type="file"
            accept="image/png,image/jpeg"
            onChange={e => setSelectedFile(e.target.files?.[0] ?? null)}
          />

          <div style={{ marginTop: 14 }}>
            <IonButton onClick={handleUpload}>Nahrát obrázek</IonButton>
          </div>

          <p className="small-muted">
            Upload používá hlavičky <code>x-user-id</code> a <code>bucket-id</code>.
          </p>
        </div>
      </div>

      <div className="grid">
        <div className="card">
          <IonCardTitle>3. Objekty v bucketu</IonCardTitle>

          {objects.length === 0 && <p>Zatím nejsou načtené žádné objekty.</p>}

          {objects.map(obj => (
            <div className="object-row" key={obj.id}>
              <div>
                <strong>{obj.filename}</strong>
                <div className="small-muted">
                  ID: {obj.id} | {obj.size} B
                </div>
              </div>

              <div style={{ display: 'flex', gap: 8 }}>
                <IonButton
                  size="small"
                  fill={selectedObjectId === obj.id ? 'solid' : 'outline'}
                  onClick={() => setSelectedObjectId(obj.id)}
                >
                  Vybrat
                </IonButton>

                <IonButton
                  size="small"
                  fill="outline"
                  onClick={() => handlePreview(obj.id)}
                >
                  Náhled
                </IonButton>
              </div>
            </div>
          ))}
        </div>

        <div className="card">
          <IonCardTitle>4. Image processing</IonCardTitle>

          <IonItem>
            <IonLabel position="stacked">Vybraný objekt</IonLabel>
            <IonInput value={selectedObject?.filename ?? selectedObjectId} readonly />
          </IonItem>

          <IonItem>
            <IonLabel position="stacked">Operace</IonLabel>
            <IonSelect
              value={operation}
              onIonChange={e => setOperation(e.detail.value)}
            >
              <IonSelectOption value="negative">Negativ</IonSelectOption>
              <IonSelectOption value="mirror">Horizontální zrcadlo</IonSelectOption>
              <IonSelectOption value="crop">Crop</IonSelectOption>
              <IonSelectOption value="brightness">Jas</IonSelectOption>
              <IonSelectOption value="grayscale">Grayscale</IonSelectOption>
            </IonSelect>
          </IonItem>

          {operation === 'brightness' && (
            <IonItem>
              <IonLabel position="stacked">Zesvětlení</IonLabel>
              <IonInput
                type="number"
                value={brightness}
                onIonInput={e => setBrightness(Number(e.detail.value ?? 0))}
              />
            </IonItem>
          )}

          {operation === 'crop' && (
            <>
              <IonItem>
                <IonLabel position="stacked">x</IonLabel>
                <IonInput type="number" value={cropX} onIonInput={e => setCropX(Number(e.detail.value ?? 0))} />
              </IonItem>
              <IonItem>
                <IonLabel position="stacked">y</IonLabel>
                <IonInput type="number" value={cropY} onIonInput={e => setCropY(Number(e.detail.value ?? 0))} />
              </IonItem>
              <IonItem>
                <IonLabel position="stacked">width</IonLabel>
                <IonInput type="number" value={cropWidth} onIonInput={e => setCropWidth(Number(e.detail.value ?? 0))} />
              </IonItem>
              <IonItem>
                <IonLabel position="stacked">height</IonLabel>
                <IonInput type="number" value={cropHeight} onIonInput={e => setCropHeight(Number(e.detail.value ?? 0))} />
              </IonItem>
            </>
          )}

          <div style={{ display: 'flex', gap: 10, marginTop: 14 }}>
            <IonButton onClick={handleProcess}>Spustit processing</IonButton>
            <IonButton fill="outline" onClick={() => handlePreview()}>
              Zobrazit vybraný
            </IonButton>
          </div>
        </div>
      </div>

      <div className="grid">
        <div className="card">
          <IonCardTitle>Náhled obrázku</IonCardTitle>
          {previewUrl ? (
            <img src={previewUrl} className="preview-img" alt="preview" />
          ) : (
            <p>Není načtený žádný náhled.</p>
          )}
        </div>

        <div className="card">
          <IonCardTitle>Stav a Message Broker</IonCardTitle>

          <p>
            Broker image.done:{' '}
            <strong>{connected ? 'připojeno' : 'nepřipojeno'}</strong>
          </p>

          <IonTextarea
            className="status-box"
            value={status}
            readonly
            autoGrow
          />

          <h3>Dokončené joby</h3>

          {messages.length === 0 && <p>Zatím žádná zpráva z image.done.</p>}

          {messages.map((msg, index) => (
            <pre className="status-box" key={index}>
              {JSON.stringify(msg, null, 2)}
            </pre>
          ))}
        </div>
      </div>

      <IonToast
        isOpen={toast.length > 0}
        message={toast}
        duration={1800}
        onDidDismiss={() => setToast('')}
      />
    </div>
  );
}
