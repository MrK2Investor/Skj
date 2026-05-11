import { useState } from 'react';
import {
  IonApp,
  IonContent,
  IonHeader,
  IonPage,
  IonSegment,
  IonSegmentButton,
  IonLabel,
  IonTitle,
  IonToolbar,
  setupIonicReact
} from '@ionic/react';

import StorageDashboard from './pages/StorageDashboard';
import TestRunner from './pages/TestRunner';

setupIonicReact();

export default function App() {
  const [page, setPage] = useState<'app' | 'tests'>('app');

  return (
    <IonApp>
      <IonPage>
        <IonHeader>
          <IonToolbar color="primary">
            <IonTitle>Mini Cloud Storage + Image Worker</IonTitle>
          </IonToolbar>

          <IonToolbar>
            <IonSegment
              value={page}
              onIonChange={e => setPage(e.detail.value as 'app' | 'tests')}
            >
              <IonSegmentButton value="app">
                <IonLabel>Aplikace</IonLabel>
              </IonSegmentButton>

              <IonSegmentButton value="tests">
                <IonLabel>Testy</IonLabel>
              </IonSegmentButton>
            </IonSegment>
          </IonToolbar>
        </IonHeader>

        <IonContent fullscreen>
          {page === 'app' && <StorageDashboard />}
          {page === 'tests' && <TestRunner />}
        </IonContent>
      </IonPage>
    </IonApp>
  );
}