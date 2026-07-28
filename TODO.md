# TODO - Implementare Arhitectura Recomandata

Acest TODO operationalizeaza arhitectura din README in pasi concreti, executabili.

## 0) Setup initial proiect

- [x] Creeaza structura de directoare:
  - [x] `autocad-plugin/`
  - [x] `ai-server/`
  - [x] `shared/schemas/`
  - [x] `docs/`
- [x] Defineste conventii de naming (entitati, tool-uri, layere, versiuni schema).
- [x] Configureaza repo (branching simplu, release tags, changelog).
- [x] Configurare mediu de dezvoltare:
  - [x] `venv` creat și `requirements.txt` instalate pentru `ai-server` (în `.venv`)
  - [x] Dependințe `fastapi`, `uvicorn`, `jsonschema`, `httpx` instalate

## 1) Contracte JSON si validare (M0)

- [x] Defineste schema pentru context DWG (input):
  - [x] metadata desen (units, UCS/WCS, versiune)
  - [x] blocks (handle, nume, pozitie, layer, atribute)
  - [x] texts (handle, continut, pozitie, layer)
  - [x] lines/polylines (handle, puncte, layer)
- [x] Defineste schema pentru actiuni AI (output):
  - [x] `insert_block`
  - [x] `create_polyline`
  - [x] `update_attribute`
  - [x] `find_entities`
- [x] Adauga versionare schema (`schema_version`).
- [x] Implementeaza validare JSON Schema in AI server.
- [x] Implementeaza validare JSON Schema in plugin (inainte de executie).
- [x] Defineste coduri standard de eroare pentru payload invalid.

## 2) AutoCAD Plugin (C#/.NET)

- [x] Creeaza comanda de test in AutoCAD (ex: `AI_PING`).
- [x] Creeaza comenzi plugin: `AI_PING`, `AI_EXTRACT`, `AI_ANALYZE`, `AI_EXECUTE`.
- [ ] Implementeaza extractor DWG:
  - [ ] citire block references
  - [ ] citire texte
  - [ ] citire layere
  - [ ] citire linii/polilinii
- [ ] Normalizeaza coordonate (WCS) in payload.
- [ ] Serializeaza context in JSON conform schemei.
- [ ] Implementeaza executor de actiuni:
  - [x] mapare action type -> handler
  - [ ] tranzactii AutoCAD cu rollback la eroare
  - [x] jurnalizare per entitate (before/after)
  - [x] preview/execution report structurat
  - [x] `find_entities` pe contextul extras

## 3) AI Server (Python/FastAPI)

- [x] Initializeaza API cu endpoint-uri:
  - [x] `POST /analyze`
  - [x] `GET /health`
- [x] Integreaza model local prin Ollama.
- [x] Construieste prompt deterministic pentru tool calling.
- [x] Parseaza raspunsul modelului in JSON strict.
- [x] Adauga fallback controlat:
  - [x] cand input e ambiguu -> cere clarificare
  - [x] cand modelul e nesigur -> nu propune executie

## 4) Validation Gate (obligatoriu inainte de executie)

- [x] Implementeaza validare semantica pentru fiecare actiune:
  - [x] block exista in librarie
  - [x] layer permis
  - [x] coordonate in limite
  - [x] valori atribute conforme
- [x] Blocheaza actiuni nepermise cu motive explicite.
- [x] Returneaza raport de validare per actiune.

## 5) Flux cap-coada Plugin <-> AI

- [x] Plugin trimite context JSON la `POST /analyze`.
- [ ] AI server returneaza lista de actiuni + justificare scurta.
- [ ] Plugin ruleaza preview (highlight) inainte de commit.
- [ ] Utilizatorul confirma executia.
- [ ] Plugin executa tranzactional si raporteaza rezultat.

## 6) Observabilitate si audit

- [x] Introdu `request_id` unic per comanda.
- [x] Logheaza evenimente structurate:
  - [x] input user
  - [x] context summary
  - [x] raspuns LLM
  - [x] rezultat validator
  - [x] rezultat executie
- [x] Stocheaza audit trail cu handles entitati modificate.
- [x] Creeaza mod replay pentru debugging.

## Repo & Commits

- [x] Import fixtures DWG din `C:\Users\tutuc\OneDrive\Desktop\Projectare` în `fixtures/dwg/edge/` și meta generate
- [x] Adăugat validator și extractor placeholder pentru fixtures în `fixtures/dwg/`
- [x] `fixtures/dwg/fixtures_index.json` generat (78 intrări) și exporturi JSON validate
- [x] Modificările comise și împinse pe branch-ul `cosmin` (fișiere: `.gitignore`, `ai-server/README.md`, `fixtures/dwg/*` forțat pentru anumite fișiere)

## 7) Fixture-uri DWG si teste de regresie

- [x] Creeaza set initial de fixtures prin import (smoke + edge)
- [x] Implementat `fixtures/dwg/validate_fixtures.py` (validare meta + index)
- [x] Implementat `fixtures/dwg/extract_contexts.py` (export placeholder JSON conform `dwg-context.schema.json`)
- [x] Generat exporturi în `fixtures/dwg/exports/` și validat față de `shared/schemas/dwg-context.schema.json`
- [x] Scris teste automate de regresie care rulează extractor + validator

## 8) UI in AutoCAD (PaletteSet/WPF) - Chat-first, reusable

- [x] Creeaza un panel de chat AutoCAD reutilizabil pentru multiple versiuni.
- [ ] Defineste un `PaletteSet` / `UserControl` generic cu:
  - [x] text de intrare pentru prompt user
  - [ ] zona de istoric chat (mesaje user + AI)
  - [ ] afisare stare server/health
  - [x] lista de actiuni propuse si recomandari de executie
  - [x] butoane `Trimite`, `Analizeaza`, `Preview`, `Executa`, `Inchide`
- [x] Adauga optiuni pentru configurarea URL-ului serverului AI si a directorului de scheme JSON.
- [x] Implementeaza un command `AI_CHAT` sau `AI_OPEN_CHAT` care deschide panelul din AutoCAD.
- [x] Construieste un flux de chat care poate trimite:
  - [x] mesajul userului
  - [x] context DWG extras
  - [x] istoric de conversatie scurt
- [x] Adauga operațiuni rapide din chat:
  - [x] generare plan `Analyze`
  - [x] preview `Preview`
  - [x] execuție `Execute`
- [x] Salveaza sesiunea de chat local în `ai_chat_session.json`.

### Chat UI imediat

- [x] implementare minimă WinForms pentru chat.
- [x] comandă `AI_CHAT` / `AI_OPEN_CHAT`.
- [ ] urmează: istoric conversație și sesiune chat persistată.

## 9) Definition of Done MVP

- [ ] Listare blocuri/texte/layere functionala pe desene reale.
- [ ] Inserare bloc pe baza comenzii naturale + confirmare user.
- [ ] Conectare polilinii pentru cazuri standard.
- [ ] Modificare atribute cu validare.
- [ ] Zero executii fara trecere prin validation gate.
- [ ] Rata de succes stabila pe fixture-uri de test.

## 10) Ordine recomandata de executie (primele 2 saptamani)

- [ ] Ziua 1-2: M0 (schema + validare)
- [ ] Ziua 3-5: extractor plugin + `POST /analyze`
- [ ] Ziua 6-7: un tool complet (`insert_block`) cap-coada
- [ ] Saptamana 2: validation gate + preview + fixture tests

## Deliverables finale pentru faza MVP

- [ ] Plugin AutoCAD stabil cu extractor + executor tranzactional
- [ ] AI server local cu tool calling JSON strict
- [ ] Contracte schema versionate in `shared/schemas/`
- [ ] Set minim de teste pe fixture-uri DWG
- [ ] Documentatie operationala in `docs/`
