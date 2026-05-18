# Appify Cloud - Haystack Architecture

Projekt obsahuje 4 nezávislé FastAPI služby:

1. **S3 Gateway** (`localhost:8000`)  
   Přijímá HTTP požadavky, validuje upload, drží SQLite metadata, status objektu, `volume_id`, `offset`, `size` a `is_deleted`.

2. **Message Broker** (`localhost:8001`)  
   Jednoduchý Pub/Sub broker přes WebSocket a MessagePack.

3. **Image Processing Node** (`localhost:8002`)  
   Samostatná služba pro práci s obrázky přes NumPy/Pillow.

4. **Haystack Node** (`localhost:8003`)  
   Fyzicky ukládá binární data append-only do `volume_X.dat` souborů.

## Spuštění bez Dockeru

V každém terminálu spusť:

```bash
python -m venv .venv
.venv\Scripts\activate  # Windows
pip install -r requirements.txt
```

Terminál 1:

```bash
py -m uvicorn broker.app.main:app --reload --port 8001
```

Terminál 2:

```bash
py -m uvicorn haystack_node.app.main:app --reload --port 8003
```

Terminál 3:

```bash
py -m uvicorn s3_gateway.app.main:app --reload --port 8000
```

Terminál 4:

```bash
py -m uvicorn image_worker.app.main:app --reload --port 8002
```

## Spuštění přes Docker Compose

```bash
docker compose up --build
```

## Upload

```bash
curl -X POST "http://localhost:8000/upload" -F "file=@photo.jpg"
```

Gateway odpoví `202 Accepted`, protože objekt je nejdřív ve stavu `uploading`.

## Kontrola objektu

```bash
curl http://localhost:8000/objects/<object_id>
```

Po ACK zprávě z Haystack Node bude objekt `ready` a bude mít vyplněné:

```json
{
  "volume_id": 1,
  "offset": 0,
  "size": 12345,
  "status": "ready"
}
```

## Download

```bash
curl http://localhost:8000/download/<object_id> --output downloaded.jpg
```

Gateway interně volá Haystack Node endpoint:

```text
GET /volume/{volume_id}/{offset}/{size}
```

## Soft delete

```bash
curl -X DELETE http://localhost:8000/download/<object_id>
```

Objekt se nesmaže z volume souboru. Pouze se nastaví `is_deleted = true`.

## Kompakce

```bash
python scripts/compact.py 1
```

Nebo přímo:

```bash
curl -X POST http://localhost:8003/admin/compact/1
```

Haystack Node si vyžádá ze S3 Gateway živé objekty daného volume, vytvoří compacted soubor, přepíše živá data za sebe a následně Gateway aktualizuje offsety.

## Databázová tabulka `objects`

| Sloupec | Význam |
|---|---|
| object_id | UUID objektu |
| filename | původní název souboru |
| content_type | MIME typ |
| status | `uploading` nebo `ready` |
| volume_id | číslo volume souboru |
| offset | začátek dat ve volume |
| size | počet bajtů |
| is_deleted | soft delete příznak |
| created_at | čas vytvoření |
| ready_at | čas potvrzení zápisu |

## Tok uploadu

```text
Klient
  -> POST /upload
S3 Gateway
  -> DB: object status=uploading
  -> Broker topic storage.write {object_id, data}
Haystack Node
  -> append do volume_X.dat
  -> Broker topic storage.ack {object_id, volume_id, offset, size}
S3 Gateway
  -> DB: status=ready, doplnění location metadat
```

## Billing / kredity

Billing je doplněný přímo v **S3 Gateway**. Každý objekt patří uživateli podle HTTP hlavičky `X-User-Id`.
Když hlavičku nepošleš, použije se `demo-user`.

Důležité: kredity se nestrhávají při `POST /upload`. Upload pouze vytvoří DB záznam se stavem `uploading` a pošle binární data do `storage.write`.
Kredity se strhnou až v `storage_ack_listener()`, tedy až po přijetí potvrzení z Haystack Node na topicu `storage.ack`.

Výchozí nastavení:

```text
INITIAL_CREDITS = 100000
UPLOAD_CREDIT_PER_KIB = 1
DOWNLOAD_CREDIT_PER_KIB = 0
```

To znamená: za každý započatý KiB úspěšně uloženého souboru se strhne 1 kredit. Download egress se eviduje, ale defaultně nic nestojí.

### Billing endpointy

Zobrazení účtu:

```bash
curl http://localhost:8000/billing/account -H "X-User-Id: michal"
```

Zobrazení billing historie:

```bash
curl http://localhost:8000/billing/events -H "X-User-Id: michal"
```

Admin dobití kreditů:

```bash
curl -X POST http://localhost:8000/admin/billing/michal/credits \
  -H "X-Admin-Token: dev-secret" \
  -H "Content-Type: application/json" \
  -d '{"amount": 5000}'
```

Upload s uživatelem:

```bash
curl -X POST "http://localhost:8000/upload" \
  -H "X-User-Id: michal" \
  -F "file=@photo.jpg"
```

Download se stejným uživatelem:

```bash
curl http://localhost:8000/download/<object_id> \
  -H "X-User-Id: michal" \
  --output downloaded.jpg
```

### Billing tabulky

Projekt má navíc tabulky:

| Tabulka | Účel |
|---|---|
| `user_accounts` | kredity uživatele, aktivní storage, ingress, egress |
| `billing_events` | auditní log účtování |

`objects` má navíc:

| Sloupec | Účel |
|---|---|
| `user_id` | vlastník objektu |
| `billed_credits` | kolik kreditů bylo strženo po ACK |
| `deleted_at` | čas soft delete |

Pokud uživatel po ACK nemá dost kreditů, Gateway objekt označí jako `payment_required`. Data už fyzicky mohou být ve volume, ale Gateway nedovolí download, dokud se kredity nedobijí a stav se ručně nevyřeší.
