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

## 1) Contracte JSON si validare (M0)

- [ ] Defineste schema pentru context DWG (input):
  - [ ] metadata desen (units, UCS/WCS, versiune)
  - [ ] blocks (handle, nume, pozitie, layer, atribute)
  - [ ] texts (handle, continut, pozitie, layer)
  - [ ] lines/polylines (handle, puncte, layer)
- [ ] Defineste schema pentru actiuni AI (output):
  - [ ] `insert_block`
  - [ ] `create_polyline`
  - [ ] `update_attribute`
  - [ ] `find_entities`
- [ ] Adauga versionare schema (`schema_version`).
- [ ] Implementeaza validare JSON Schema in AI server.
- [ ] Implementeaza validare JSON Schema in plugin (inainte de executie).
- [ ] Defineste coduri standard de eroare pentru payload invalid.

## 2) AutoCAD Plugin (C#/.NET)

- [ ] Creeaza comanda de test in AutoCAD (ex: `AI_PING`).
- [ ] Implementeaza extractor DWG:
  - [ ] citire block references
  - [ ] citire texte
  - [ ] citire layere
  - [ ] citire linii/polilinii
- [ ] Normalizeaza coordonate (WCS) in payload.
- [ ] Serializeaza context in JSON conform schemei.
- [ ] Implementeaza executor de actiuni:
  - [ ] mapare action type -> handler
  - [ ] tranzactii AutoCAD cu rollback la eroare
  - [ ] jurnalizare per entitate (before/after)

## 3) AI Server (Python/FastAPI)

- [ ] Initializeaza API cu endpoint-uri:
  - [ ] `POST /analyze`
  - [ ] `GET /health`
- [ ] Integreaza model local prin Ollama.
- [ ] Construieste prompt deterministic pentru tool calling.
- [ ] Parseaza raspunsul modelului in JSON strict.
- [ ] Adauga fallback controlat:
  - [ ] cand input e ambiguu -> cere clarificare
  - [ ] cand modelul e nesigur -> nu propune executie

## 4) Validation Gate (obligatoriu inainte de executie)

- [ ] Implementeaza validare semantica pentru fiecare actiune:
  - [ ] block exista in librarie
  - [ ] layer permis
  - [ ] coordonate in limite
  - [ ] valori atribute conforme
- [ ] Blocheaza actiuni nepermise cu motive explicite.
- [ ] Returneaza raport de validare per actiune.

## 5) Flux cap-coada Plugin <-> AI

- [ ] Plugin trimite context JSON la `POST /analyze`.
- [ ] AI server returneaza lista de actiuni + justificare scurta.
- [ ] Plugin ruleaza preview (highlight) inainte de commit.
- [ ] Utilizatorul confirma executia.
- [ ] Plugin executa tranzactional si raporteaza rezultat.

## 6) Observabilitate si audit

- [ ] Introdu `request_id` unic per comanda.
- [ ] Logheaza evenimente structurate:
  - [ ] input user
  - [ ] context summary
  - [ ] raspuns LLM
  - [ ] rezultat validator
  - [ ] rezultat executie
- [ ] Stocheaza audit trail cu handles entitati modificate.
- [ ] Creeaza mod replay pentru debugging.

## 7) Fixture-uri DWG si teste de regresie

- [ ] Creeaza set initial de 5-10 desene etalon.
- [ ] Defineste teste pentru:
  - [ ] extractie context
  - [ ] validare schema
  - [ ] validare semantica
  - [ ] executie tool-uri critice
- [ ] Ruleaza testele la fiecare schimbare de schema sau tool.

## 8) UI in AutoCAD (PaletteSet/WPF)

- [ ] Creeaza panel minim de chat/comenzi.
- [ ] Afiseaza:
  - [ ] ce a inteles AI
  - [ ] ce actiuni propune
  - [ ] ce a blocat validatorul
  - [ ] ce s-a executat efectiv
- [ ] Adauga butoane `Preview`, `Execute`, `Undo last`.

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
