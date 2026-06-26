# AI Agent Local pentru AutoCAD 2D

Acest proiect descrie o arhitectura practica pentru un AI local care automatizeaza fluxuri 2D in AutoCAD, folosind integrare directa prin API (nu control de mouse).

## Obiectiv

Construirea unui sistem care poate:

- citi DWG-ul curent;
- extrage blocuri, texte, layere si polilinii;
- interpreta comenzi in limbaj natural;
- executa actiuni CAD prin plugin-ul AutoCAD;
- evolua incremental, de la MVP la versiune robusta.

## Arhitectura recomandata

- AutoCAD Plugin: C# + .NET (citire/executie CAD)
- AI Orchestrator: Python + FastAPI (coordoneaza context, validari, plan de actiuni)
- LLM local: Ollama + Qwen2.5 (7B pentru MVP, 14B pentru calitate mai buna)
- Protocol comunicare: HTTP + JSON
- Chat UI AutoCAD: `AI_CHAT` pentru lansarea unui panel de chat intern cu sesiune persistată, health check și analiză directă.

Flux:

1. Plugin-ul extrage context din DWG si trimite JSON.
2. AI-ul genereaza actiuni structurate (tool calling).
3. Plugin-ul executa actiunile in AutoCAD.

## Milestone-uri esentiale

### M0. Contracte JSON si reguli de validare (obligatoriu)

Scop:

- definirea schemelor JSON pentru context CAD (input) si actiuni (output);
- validare stricta cu JSON Schema;
- definirea regulilor minime de siguranta in executie (ce are voie sa ruleze).

Livrabil:

- pachet de scheme versionate in `shared/schemas/`;
- validator comun folosit de plugin si AI server.

Durata estimata:

- 1-2 zile.

Criteriu de acceptare:

- orice payload invalid este respins explicit, cu erori clare.

### M1. Citire DWG (fundatia)

Scop:

- citire blocuri;
- citire texte;
- listare layere.

Livrabil:

- endpoint/command care returneaza JSON cu entitatile principale.

Durata estimata:

- 2-3 zile.

Criteriu de acceptare:

- datele extrase sunt corecte pe minim 5 desene reale (fixture set).

### M2. AI local functional

Scop:

- instalare Ollama;
- rulare model Qwen2.5:7b local;
- validare prompt simplu pentru analiza JSON.

Nota:

- Qwen2.5:14b se adopta doar daca hardware-ul permite latenta buna in utilizare curenta.

Livrabil:

- AI server capabil sa primeasca context si sa returneze raspuns coerent.

Durata estimata:

- 1 zi.

Criteriu de acceptare:

- raspuns stabil la aceeasi intrare, fara dependente cloud.

### M3. Integrare Plugin <-> AI Server

Scop:

- comunicare HTTP intre plugin si FastAPI;
- endpoint principal `POST /analyze`.

Livrabil:

- request/response cap-coada functionale din AutoCAD.

Durata estimata:

- 2 zile.

Criteriu de acceptare:

- plugin trimite context si primeste actiuni JSON valide.

### M3.1. Validation Gate intre AI si executor

Scop:

- nici o actiune AI nu este executata direct;
- validare semantica inainte de executie:
  - block exista in librarie;
  - layer permis de reguli;
  - coordonate in limite configurate;
  - comenzi nepermise sunt blocate.

Livrabil:

- validator semantic + jurnal de decizie (acceptat/refuzat + motiv).

Durata estimata:

- 2-3 zile.

Criteriu de acceptare:

- actiunile invalide sunt respinse predictibil, fara efecte in desen.

### M4. Primul tool real (valoare imediata)

Scop:

- comanda de tip: "insereaza bloc AMP pentru fiecare text tinta".

Livrabil:

- pipeline complet: analiza -> actiuni -> executie CAD.

Durata estimata:

- 3-5 zile.

Criteriu de acceptare:

- inserarile sunt corecte geometric si repetabile.

### M5. Tool Calling standardizat

Scop:

- definirea tool-urilor CAD cu schema clara (JSON):
  - `insert_block`
  - `create_polyline`
  - `update_attribute`
  - `find_entities`

Livrabil:

- executor generic de actiuni + validare schema.

Durata estimata:

- ~1 saptamana.

Criteriu de acceptare:

- AI-ul nu genereaza cod ad-hoc, ci apeleaza tool-uri standard.

### M5.1. Teste de regresie pe fixture DWG

Scop:

- set de 5-10 desene etalon pentru verificare automata;
- teste pentru extractie, plan de actiuni si executie.

Livrabil:

- suita de teste care ruleaza local si raporteaza regresii.

Durata estimata:

- 2-4 zile initial, apoi mentenanta incrementala.

Criteriu de acceptare:

- fiecare schimbare trece testele pe fixture-uri inainte de release.

### M6. UI de chat in AutoCAD

Scop:

- interfata de utilizare in AutoCAD (PaletteSet/WPF / WinForms).

Livrabil:

- panou chat pentru cereri, status si rezultate.
- comanda AutoCAD `AI_CHAT` / `AI_OPEN_CHAT`.
- lansare prompt + analiza + preview + executie din același panel.
- sesiune persistată local în `ai_chat_session.json`.

Durata estimata:

- ~1 saptamana.

Criteriu de acceptare:

- utilizatorul poate lansa task-uri fara scripturi externe.

### M7. Memorie de proiect si reguli CAD

Scop:

- adaugare reguli specifice proiectului:
  - standarde de layer;
  - blocuri uzuale;
  - conventii interne.

Livrabil:

- mecanism de context persistent pentru decizii mai bune.

Durata estimata:

- 1-2 saptamani.

Criteriu de acceptare:

- rezultate mai consistente intre sesiuni.

## MVP minim realist

Un MVP bun trebuie sa livreze doar:

- listare blocuri;
- inserare blocuri;
- conectare polilinii;
- modificare atribute;
- citire texte.

## Ce sa eviti

- control de mouse/screenshot automation;
- abordari de computer vision pentru desen 2D;
- tentativa de autonomie completa din prima faza.

Acestea cresc dramatic complexitatea si instabilitatea.

## Roadmap estimativ

- MVP solid: 3-6 saptamani
- Varianta buna: 2-3 luni
- Aproape comercial: 6-12 luni

## Riscuri tehnice principale

- variabilitate LLM la prompturi ambigue;
- erori geometrice UCS/WCS sau transformari coordonate;
- degradare de performanta pe desene mari fara filtrare de context.

## Masuri de control al riscului

- contracte JSON stricte si versionate;
- validation gate obligatoriu inainte de executie;
- testare de regresie pe fixture DWG;
- fallback explicit: daca AI e nesigur, returneaza clarificare, nu executie.

## Structura recomandata proiect

```text
cad-ai-agent/
  autocad-plugin/
    Commands.cs
    BlockReader.cs
    EntityExecutor.cs
  ai-server/
    main.py
    prompts/
    tools/
  shared/
    schemas/
  docs/
```

## Principiul cheie

Succesul nu depinde doar de modelul AI, ci de:

- integrarea corecta cu AutoCAD API;
- tool calling robust;
- arhitectura modulara si usor de depanat.
