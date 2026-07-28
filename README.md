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

## Milestone-uri viitoare

Obiectivul urmatoarei etape este trecerea de la un planner monolitic la o arhitectura agentica modulara, capabila sa rezolve task-uri CAD complexe, cu verificare automata dupa executie.

### Arhitectura tinta pentru planner

Flow recomandat:

1. Intent Parser
2. Planner
3. Tool Selector
4. Executor
5. Verifier
6. Memory
7. Replanner (daca verificarea esueaza)

Model operational:

1. Think
2. Act
3. Observe
4. Replan (cand este necesar)

### Principii de design

- Fiecare componenta are un singur rol.
- Executorul executa, nu decide.
- Planner-ul produce obiective si sub-obiective, nu doar actiuni plate.
- Verifierul valideaza rezultatul in DWG si inchide bucla de feedback.
- Memoria de sesiune permite comenzi contextuale de tipul "muta-l mai la stanga".

### Etapa 1: Executor complet (prioritatea maxima)

Scop:

- finalizarea executiei CAD reale pentru tool-urile principale;
- reducerea dependentei de raspunsuri pur descriptive.

Actiuni tinta:

- insert_block
- move_block
- delete_block
- copy_block
- create_polyline
- create_line
- update_attribute
- modify_text
- zoom_to_entity
- select_entities

### Etapa 2: Tool Registry unificat

Scop:

- definirea unui catalog unic de tool-uri;
- decuplarea planner-ului de detalii specifice AutoCAD.

Exemple de tool-uri candidate:

- find_room
- find_block
- find_text
- find_nearest_wall
- compute_room_center
- compute_path
- find_loop
- find_layer
- check_normative

### Etapa 3: Goal Planner + Task Graph

Scop:

- introducerea planificarii ierarhice (goal -> subgoal -> actions);
- executie pe graf de task-uri, nu doar pe lista liniara.

Exemplu de flow:

1. Find Rooms
2. Find Existing Detectors
3. Compare Coverage
4. Insert Missing
5. Verify Result
6. Generate Report

### Etapa 4: Verifier + replanning automat

Scop:

- verificare post-executie direct din DWG;
- relansare automata a planificarii cand exista gap-uri.

Exemplu:

1. Executor insereaza detectoare.
2. Verifier reciteste DWG.
3. Daca mai exista camere fara detector, planner-ul continua cu pasii lipsa.

### Etapa 5: Memory de sesiune si proiect

Scop:

- persistenta contextului operational intre comenzi;
- eliminarea re-cautarii complete la fiecare interactiune.

Date utile in memorie:

- handle camera curenta
- handle detector inserat
- ultimele entitati modificate
- ultima zona analizata

### Ce NU este prioritar acum

- fine-tuning timpuriu al modelului LLM;
- cresterea modelului fara consolidarea arhitecturii agentice.

Capabilitatile urmatoare vor veni in principal din designul planner-ului, tooling si bucla de verificare, nu din schimbarea prematura a modelului.

### Roadmap pe milestone-uri

Milestone 1 (finalizat):

- [x] citire DWG
- [x] extragere entitati
- [x] FastAPI + Ollama
- [x] planner JSON
- [x] validare schema + semantica

Milestone 2:

- [x] executor complet
- [x] tool registry
- [x] tool selector
- [x] session memory

Milestone 3:

- [x] goal planner
- [x] task graph
- [x] verifier
- [x] replanning automat

### Stare curenta Milestone 3 (actualizat: 2026-07-26)

Implementat in acest moment:

- goal planner activ in server, cu subgoals generate automat;
- task graph activ in server, inclusiv execution_order explicit;
- executorul plugin ruleaza pe execution_order (nu doar pe lista liniara de actions);
- raportul de executie include node_results cu status real pending -> running -> done/failed;
- raportul de executie include goal status + subgoal status derivat din node_results;
- chat panel afiseaza sumar de progres + tabel/lista compacta pentru subgoals.

Milestone 3 este inchis functional:

- verifier minim activ pentru `insert_block` si `update_attribute` (bazat pe context_before/context_after + execution_report);
- pluginul apeleaza `/verify` dupa `Execute`;
- cand verifier returneaza `failed`, pluginul cere automat un plan incremental nou prin `/chat`.

### Continuare recomandata in pasi mici (Milestone 4)

Pas 1 (rapid): extindere verifier pe alte actiuni

- adauga verificari post-executie pentru:
  - create_polyline;
  - find_entities (consistenta cu context_after).

Pas 2: consolidare endpoint server pentru verificare

- pastreaza `/verify` ca poarta centrala si adauga coduri de verdict mai detaliate.

Pas 3: consolidare legatura in plugin

- normalizeaza afisarea verifier in chat pe nivele info/warn/error;
- adauga buton de retry pentru planul incremental rezultat din replanning.

Pas 4: replanning avansat

- adauga regula de deduplicare pentru a preveni repetarea actiunilor deja validate.

### Checklist scurt pentru reluarea lucrului

1. Porneste serverul local din ai-server.
2. Ruleaza taskul Plugin: Build + Reload AutoCAD.
3. In AutoCAD, NETLOAD pe ultimul DLL versionat daca reload automat nu merge.
4. Testeaza fluxul: Analyze -> Preview -> Execute din AI_CHAT.
5. Verifica in chat:
   - overall status
   - goal status
   - subgoal status (compact sau tabel)
6. Daca verifier da failed, verifica planul incremental nou din chat si ruleaza retry controlat.

Milestone 4:

- [ ] RAG cu normative
- [ ] cautare semantica in DWG
- [ ] planificare pe mai multe desene
- [ ] agent autonom pe task-uri complexe

Milestone 5:

- [ ] asistent CAD aproape autonom
- [ ] explicarea deciziilor
- [ ] generare rapoarte de conformitate

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
