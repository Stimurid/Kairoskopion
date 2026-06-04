# **JOURNAL\_YUGA\_TECHNICAL\_SPEC\_FOR\_CLAUDE\_v0\_1**

## **Волна 1\. Назначение, границы, положение в Litops–WhiteCrow, базовая формула и bounded contexts**

## **0\. Назначение этого технического описания**

Этот документ описывает целевое устройство Journal-Yuga / Venue-Fit Engine как инженерной системы. Его задача — перевести конституцию Journal-Yuga из онтологического и продуктового языка в язык реализуемой архитектуры: какие объекты существуют, какие границы система не должна пересекать, какие данные принимает, какие модели строит, какие выводы имеет право делать, какие виды доказательности обязаны сопровождать каждый вывод, как система связана с Litops и WhiteCrow, и почему её нельзя сводить к обычному подборщику журналов.

Journal-Yuga должен проектироваться как bounded context внутри более широкой экосистемы Litops–WhiteCrow. Он может в будущем стать самостоятельным продуктом или sidecar-сервисом, но его первая корректная форма — модуль, который наследует от Litops дисциплину источников, provenance, ContextPack, Workset, Artifact и Vault-проекций, а от WhiteCrow — понимание поля, manuscript-а, field reduction, patch queue и внешнего документа. Journal-Yuga не должен заново изобретать хранение источников и не должен становиться отдельной средой мышления вместо WhiteCrow. Его собственная область — публикационное позиционирование: сопоставление внутренней модели статьи или поля с внешней моделью публикационного контейнера.

Это техническое описание не является маркетинговым документом, пользовательской справкой или исследовательским обзором рынка. Оно фиксирует, что именно должно существовать в системе, чтобы последующая реализация не деградировала в абстрактный LLM-чат, список журналов, SEO-подборщик, общий academic writing assistant или фабрику уверенных, но непроверяемых рекомендаций.

Главная инженерная задача Journal-Yuga — сделать видимой и проверяемой публикационную ситуацию текста: что это за текст, какую статью он может стать, в какие публикационные режимы он может войти, с какими журналами или venue он совместим, где возникают расхождения, какие правки требуются, сколько они стоят с точки зрения усилия и потери смысла, какие источники подтверждают выводы системы, какие элементы остаются неизвестными, какие сигналы являются фактами, какие — вендорскими утверждениями, какие — пользовательскими заметками, какие — слабой inference-гипотезой.

## **1\. Product Definition**

Journal-Yuga / Venue-Fit Engine — это evidence-first publication-positioning system. Система предназначена для сопоставления поля, замысла, черновика, manuscript-а, abstract-а или готовой статьи с академическими публикационными контейнерами: журналами, разделами журналов, спецвыпусками, research topics, conference proceedings, open-review venues, reviewed preprints, edited volumes, humanities special issues и другими формами публикационной сцены.

Journal-Yuga не начинается с вопроса “в какой журнал подать текст?”. Этот вопрос слишком поздний и слишком плоский. Система начинает с реконструкции публикационной структуры самого текста или поля. Она должна понять, что именно пользователь пытается опубликовать: философскую статью, STS-paper, AI ethics article, conceptual model, empirical report, methodological essay, review, position paper, conference proceedings article, русскоязычный академический текст, переводимую англоязычную версию, короткий вариант для спецвыпуска, локальный ВАК-текст, Q1/Q2 submission candidate или sibling manuscript, возникший как одна из возможных редукций более широкого поля.

После этого Journal-Yuga строит или принимает модель публикационного контейнера. Публикационный контейнер не равен названию журнала. Journal is not the venue model. Один и тот же журнал может содержать разные sections, special issues, article types, research topics, editorial expectations, citation ecologies, review practices, policies and regimes. Поэтому Journal-Yuga должен работать не только с `JournalModel`, но и с более общей сущностью `VenueModel`, внутри которой могут быть `JournalModel`, `SectionModel`, `IssueModel`, `SpecialIssueModel`, `ResearchTopicModel` и `PublicationRegimeModel`.

Центральная операция системы — не recommendation, а сопоставление:

Field / Idea / Draft / Manuscript / ArticleModel  
×  
VenueModel / JournalModel / IssueModel / SectionModel / PublicationRegimeModel  
×  
SubmissionScenario  
→  
FitAssessment  
→  
MismatchMap  
→  
RewritePlan / ReframePlan / CitationPlan / RiskReport  
→  
SubmissionPack / WhiteCrow Patch Queue / External Document Actions / VenueMemory

Эта формула должна определять архитектуру, интерфейс и порядок реализации. Если в реализации появляется функция “подобрать журналы”, она должна быть частным случаем этой формулы, а не ядром системы. Подбор журнала без ArticleModel, VenueModel, SubmissionScenario и evidence trail считается недопустимой деградацией.

Journal-Yuga должен работать в двух масштабах. В узком масштабе он помогает автору оценить один конкретный manuscript относительно одного конкретного target venue: построить модель статьи, построить модель журнала, выявить mismatch, предложить правки, проверить citation ecology, собрать submission pack. В широком масштабе он помогает проектировать публикационную траекторию мысли: из одного поля или замысла получить несколько возможных article variants, каждый из которых может быть направлен в разные дисциплинарные миры, языки, publication regimes and venue pools.

Система должна поддерживать как direct standalone entry, так и ecosystem entry. В standalone entry пользователь может прийти только с abstract, черновиком, URL журнала, review letter или zip-пакетом статей. В ecosystem entry Journal-Yuga получает Source, Workset, ContextPack, Artifact, Field Text, Manuscript, Patch Queue state or ArticleTrajectory from Litops–WhiteCrow. В обоих случаях целевая логика одна и та же: собрать доказательную публикационную модель, а не выдать общую рекомендацию.

## **2\. Non-goals and Hard Prohibitions**

Journal-Yuga не является обычным journal recommender. Система не должна превращаться в интерфейс, где пользователь вставляет title/abstract, а на выходе получает ранжированный список журналов с процентом совпадения. Такой режим может существовать только как light entry или quick scan, но не как основной продукт и не как доказательный вывод. Любой shortlist должен иметь видимое основание: какие источники были использованы, какие свойства ArticleModel сравнивались с какими свойствами VenueModel, какие признаки остались неизвестными, где рекомендация слаба, где есть publisher bias, где используется inference.

Journal-Yuga не является академическим карьерным хаком. Система не должна помогать пользователю маскировать слабый текст под требования журнала, фабриковать библиографию, выдумывать эмпирический материал, симулировать методологический раздел, придумывать связи с редакцией, имитировать знание hidden politics, выдавать догадки о вкусах редакторов за факты или подгонять тезисы под несуществующие ожидания. Если текст слаб, система может показать, какие разрывы делают его слабым для выбранного venue. Она не должна превращать слабость в риторически убедительную ложь.

Journal-Yuga не является машиной переписывания текста любой ценой. Система должна различать допустимую адаптацию формы и разрушение смыслового ядра. Если публикационный контейнер требует переделки, которая меняет объект, тезис, дисциплинарную позицию, novelty mode, theoretical shoulders или protected core manuscript-а, система должна явно пометить это как high field-core risk. В таких случаях она должна не просто предложить правки, а показать альтернативы: другой venue, другой publication regime, sibling manuscript, более раннюю стадию article design или отказ от подачи в данный журнал.

Journal-Yuga не является заменой WhiteCrow. Он не должен брать на себя всю работу с полем, становлением мысли, внутренней архитектурой текста или генерацией manuscript-а как такового. Он работает с publication-facing projection поля или manuscript-а. Если требуется глубокая редукция поля в статью, это остаётся задачей WhiteCrow или соответствующего manuscript pipeline. Journal-Yuga подключается тогда, когда появляется вопрос публикационной формы, venue fit, дисциплинарного перевода, submission scenario, compliance and adaptation.

Journal-Yuga не является заменой Litops. Он не должен хранить страницы журналов, PDF статей, CFP, инструкции для авторов, metadata snapshots, review letters и пользовательские заметки как бесхозные внутренние строки. Любой внешний материал должен входить через слой Source / Evidence / Snapshot с provenance. Любая модель журнала должна быть производной от источников. Любой fit report должен быть воспроизводим через ContextPack. Если система не может показать, из каких источников получен вывод, она не имеет права выдавать этот вывод как проверенный.

Journal-Yuga не является peer-review authority. ReviewerSimulation допустима только как controlled pre-submission risk analysis: возможные возражения, места непонимания, слабые методологические позиции, missing citations, likely reviewer confusion, rebuttal preparation. Она не должна представляться как реальная рецензия, прогноз решения редакции или экспертное знание о том, что “рецензенты подумают”. Все reviewer simulations должны иметь предупреждение о статусе: simulation, not evidence.

Journal-Yuga не является юридическим, этическим или библиометрическим арбитром. Он может выявлять риски: AI disclosure, plagiarism/self-plagiarism, authorship, COI, data availability, ethics approval, patent disclosure, commercial/state secret risk, citation manipulation, predatory venue signals. Но он не должен выдавать вероятностные, внешнеуверенные или юридически значимые заключения без соответствующего источника и статуса.

Запрещён single black-box fit score. Система может давать итоговые лейблы вроде `strong candidate`, `possible but costly`, `poor fit`, `high-risk`, `requires reframe`, но только на основе многомерной карты. Любой числовой score, если когда-либо будет введён, должен быть производным display element, а не первичным reasoning object. В MVP числовой score лучше не вводить вообще.

Запрещено смешивать статусы знания. Внутри системы должны различаться: source fact, vendor claim, inferred pattern, corpus-derived observation, user tacit note, prior submission outcome, stale snapshot, unknown, inaccessible, conflicting evidence. Это различение должно проходить через все сущности: VenueModel, FitAssessment, CitationPlan, RiskReport, SubmissionPack, VenueMemory.

Запрещено выдавать “unknown” за “absent”. Если система не нашла данных о conference proceedings support, humanities fit, indexing, APC, review timelines, AI policy or editorial board, это не значит, что свойства нет. Это значит, что оно не проверено. Такое поле должно маркироваться как `UNKNOWN_NOT_VERIFIED` or `INACCESSIBLE`, а не как `NO`.

Запрещено строить VenueModel только из author guidelines. Guidelines дают формальный слой, но не фактическую публикационную форму. VenueModel должен стремиться включать: aims/scope, sections, issue structure, special issues, research topics, recent article corpus, article patterns, citation ecology, editorial board, policies, indexing, metrics, timelines, author guidelines, CFP, tacit signals and prior outcomes where available.

Запрещено строить ArticleModel только из abstract. Abstract может быть точкой входа, но ArticleModel должен хранить явные неизвестные. Если нет full manuscript, citation list, field context or user scenario, система должна не изображать полноту, а строить preliminary ArticleModel and ask missing questions.

## **3\. Position inside Litops–WhiteCrow**

Journal-Yuga занимает промежуточное место между корпусным слоем Litops и полево-manuscript-слоем WhiteCrow. Его собственная область — публикационное позиционирование, дисциплинарный перевод, venue profiling, fit analysis, adaptation planning, citation ecology, compliance, submission packaging and review-loop memory.

Litops является операционным источниковым слоем. Он принимает материалы, хранит оригиналы, регистрирует источники, создаёт source cards, worksets, context packs, artifacts, derived reports, vault projections, indices and search surfaces. Для Journal-Yuga Litops является источником долговременной памяти и доказательной дисциплины. Journal-Yuga не должен обходить Litops при работе с внешними источниками. Страница журнала, PDF статьи, DOI metadata, instructions for authors, editorial board page, CFP, review letter, screenshot, пользовательская заметка о подаче, metrics snapshot — всё это должно входить в систему как Source, EvidenceItem or Snapshot with provenance.

WhiteCrow является слоем поля и manuscript-а. Он работает с Field, Field Text, relation clusters, object hypotheses, conceptual tensions, manuscript blocks, external doc bridge, patch queue and trajectories of text formation. Для Journal-Yuga WhiteCrow является источником смысловой структуры: что именно мыслится, какой protected core нельзя разрушить, какие article variants возможны, какие элементы поля уже редуцированы в manuscript, какие остаются как sibling possibilities.

Journal-Yuga не подменяет эти слои. Он принимает от Litops evidence base and source identifiers. Он принимает от WhiteCrow field/manuscript state and protected core. Он создаёт publication-facing objects: ArticleModel, VenueModel, SubmissionScenario, FitAssessment, MismatchMap, RewritePlan, CitationPlan, RiskReport, SubmissionPack, RevisionPlan, VenueMemory. Эти outputs могут возвращаться в Litops как artifacts/context packs/vault cards and in WhiteCrow as patch candidates, citation tasks, reframe options, external document actions and manuscript trajectory decisions.

В standalone mode Journal-Yuga должен временно создавать внутренние Source-like and ContextPack-like structures. Пользователь может прийти без Litops and WhiteCrow, загрузить docx/pdf/md, вставить abstract, дать journal URL or CFP. Система всё равно должна работать в тех же понятиях: source registration, evidence status, article model, venue model, scenario, fit, mismatch, plan. Если позднее пользователь подключает Litops/WhiteCrow, эти структуры должны быть экспортируемы в соответствующие registry and vault forms.

Journal-Yuga должен быть sidecar-first, standalone-capable. Это означает, что архитектура не должна зависеть от UI конкретного продукта. Core domain must be usable from CLI, API, Telegram intake, Web UI and WhiteCrow integration. UI может меняться, но сущности, evidence rules and pipelines должны оставаться стабильными.

## **4\. Core Workflow Formula**

Целевая система должна быть организована вокруг следующей формулы:

Field / Idea / Draft / Manuscript / ArticleModel  
×  
VenueModel / JournalModel / IssueModel / SectionModel / PublicationRegimeModel  
×  
SubmissionScenario  
→  
FitAssessment  
→  
MismatchMap  
→  
RewritePlan / ReframePlan / CitationPlan / RiskReport  
→  
SubmissionPack / WhiteCrow Patch Queue / External Document Actions / VenueMemory

Эта формула должна быть не декоративным описанием, а архитектурным инвариантом. Любой основной пользовательский сценарий должен быть сводим к ней.

Если пользователь начинает с готовой статьи и одного target journal, система строит ArticleModel from manuscript, VenueModel from journal sources, SubmissionScenario from user constraints, then FitAssessment and MismatchMap, then Rewrite/Citation/Risk/Submission outputs.

Если пользователь начинает только с abstract or idea, система строит preliminary ArticleModel and marks unknowns. Она может предложить publication pathways and possible venues, but must not present deep fit without sufficient evidence.

Если пользователь начинает с журнала, но без статьи, система строит VenueModel and asks for manuscript/abstract/scenario before producing actual fit. Она может описать publication regime and typical requirements, but not claim article compatibility.

Если пользователь начинает с WhiteCrow field, система должна получить field-derived article candidates or request ArticleModel projection. Journal-Yuga должен помочь выбрать publication trajectory, not replace field reduction.

Если пользователь начинает с review letter, система работает через ReviewOutcome / RevisionPlan / VenueMemory path. It must map reviewer comments to prior ArticleModel, VenueModel and SubmissionScenario if available.

Если пользователь начинает с journal pool, system must distinguish pool discovery from deep fit. Pool discovery may produce a candidate list and light profiles; deep fit requires selected venue(s) and evidence collection.

Любой output системы должен явно показывать, на какой стадии формулы он находится. Например: preliminary ArticleModel, light VenueProfile, deep VenueModel, draft FitAssessment, evidence-backed FitAssessment, user-accepted RewritePlan, submission-ready pack, post-review VenueMemory update.

## **5\. Bounded Contexts and Ubiquitous Language**

Journal-Yuga должен быть разделён на bounded contexts. Это нужно, чтобы реализация не превратилась в один LLM prompt or one overloaded service.

### **5.1. Article Context**

Article Context отвечает за построение и хранение ArticleModel, ManuscriptModel and FieldModelReference. Он описывает, что представляет собой текст как потенциальная статья.

Основные понятия:

ArticleModel — publication-facing semantic model of the article. Это не полный текст, а структура: problem, object, question, thesis, argument, method, genre, discipline, novelty, theoretical shoulders, opponents, citation ecology, language/register, protected core, risk flags, unknowns.

ManuscriptModel — representation of the current text: title, abstract, sections, blocks, bibliography, figures/tables, metadata, file refs, block mapping to source document.

FieldModelReference — ссылка на WhiteCrow field, Field Text, ContextPack or conceptual source, из которого возник manuscript or article candidate.

ProtectedCore — набор смысловых элементов, которые нельзя менять без user acceptance: central thesis, object, conceptual distinction, philosophical stance, field commitments, key vocabulary, authorial position.

ArticleVariant — publication-oriented variant of an ArticleModel for a specific discipline, venue pool, language, regime or audience.

### **5.2. Venue Context**

Venue Context отвечает за моделирование публикационного контейнера.

Основные понятия:

VenueModel — general model of a publication container. Может описывать journal, journal section, special issue, conference proceedings, open-review venue, mega-journal, humanities collection, research topic.

JournalModel — model of a journal as publisher/entity: title, ISSN, publisher, scope, disciplines, indexing, metrics, policies, sections, submission systems, official sources.

SectionModel — model of journal section or article type: research article, review, essay, perspective, forum, book review, methods paper, commentary.

IssueModel / SpecialIssueModel / ResearchTopicModel — model of a particular issue, special collection, CFP or topic with deadlines, editors, theme, target article types and constraints.

PublicationRegimeModel — model of how publication works in this venue: classic journal peer review, mega-journal, reviewed preprint, publish-then-review, open-review conference, conference proceedings, special issue, humanities symposium, edited volume, local/Q3/non-focus fallback.

EditorialBoardProfile — structured and evidence-marked profile of editors, affiliations, disciplines and possible signals. It must never become ungrounded speculation about editorial preferences.

PublishedArticleCorpus — set of articles used to infer actual publication patterns. Must include selection strategy, source refs, time range, size, representativeness notes.

PublishedArticlePattern — corpus-derived observations: article structures, abstract patterns, method patterns, citation density, genre moves, section conventions, novelty forms.

CitationExpectationProfile — venue-specific expectations about citation ecology: field anchors, recent debate markers, method references, local citation clusters, canonical authors, dangerous gaps, padding risks.

TacitVenueSignal — user- or experience-derived non-formal signal about venue behavior, always lower evidential status than source facts.

### **5.3. Submission Scenario Context**

Submission Scenario Context отвечает за намерение пользователя и ограничения подачи. Один и тот же manuscript can fit differently depending on scenario.

SubmissionScenario должен хранить:

publication\_goal;  
target\_indexing: Scopus / WoS / ВАК / РИНЦ / none / unknown;  
prestige\_vs\_speed preference;  
APC constraints;  
language constraints;  
deadline;  
allowed rewrite depth;  
allowed reframe depth;  
empirical additions allowed or not;  
citation expansion allowed or not;  
coauthor/affiliation constraints;  
article type preferences;  
field-core preservation strictness;  
target audience;  
risk tolerance;  
fallback acceptance: Q3/local/conference/preprint/edited volume.

Fit without SubmissionScenario is incomplete. If scenario is missing, system may produce preliminary fit only and must ask questions.

### **5.4. Fit and Adaptation Context**

Fit and Adaptation Context отвечает за сравнение ArticleModel, VenueModel and SubmissionScenario.

FitAssessment is multidimensional. It must include topic fit, discipline fit, genre fit, argument fit, method fit, citation ecology fit, novelty fit, language/register fit, formal compliance fit, author eligibility, publication regime fit, effort, risk, time, strategic value, confidence, evidence refs and unknowns.

MismatchMap describes where and why fit fails or weakens. Mismatch is not an error; it is a structured relation between article and venue.

RewritePlan describes changes to the manuscript that preserve or knowingly transform the article.

ReframePlan describes deeper changes of object, discipline, article type, method, novelty mode or audience.

CitationPlan describes required citation bridges, missing field anchors, reference verification tasks and anti-padding warnings.

FieldCoreRisk describes whether adaptation threatens protected core.

### **5.5. Compliance and Risk Context**

Compliance and Risk Context отвечает за formal, ethical, policy and submission readiness.

RiskReport must include:

formal risk;  
scope risk;  
method risk;  
citation risk;  
reference validity risk;  
plagiarism/self-plagiarism risk;  
AI disclosure risk;  
authorship/CRediT risk;  
COI/funding/data availability risk;  
ethics approval risk;  
APC/predatory/indexing risk;  
publication regime risk;  
reviewer misunderstanding risk;  
timeline risk;  
field-core loss risk.

ComplianceChecklist must be guideline-aware. It should not be a generic checklist. It must depend on article type, venue policies, publication regime, discipline, method and external guidelines where relevant.

SubmissionPack is operational. It must model real downstream gates: manuscript file, supplementary files, metadata, author data, abstract, keywords, declarations, statements, cover letter, reference file, figures/tables, permissions, missing items, warnings and ready-to-submit status.

### **5.6. Evidence and Provenance Context**

Evidence and Provenance Context crosses all other contexts. It defines how claims are grounded.

Every claim in VenueModel, FitAssessment, CitationPlan, RiskReport and SubmissionPack must be traceable to one or more evidence refs or marked unknown.

Evidence statuses:

FACT\_FROM\_SOURCE;  
VENDOR\_CLAIM;  
CORPUS\_OBSERVATION;  
INFERENCE;  
TACIT\_SIGNAL;  
USER\_NOTE;  
PRIOR\_OUTCOME;  
UNKNOWN;  
INACCESSIBLE;  
STALE;  
CONFLICTING\_EVIDENCE.

No claim may silently move from lower status to higher status. A tacit signal can inform a risk hypothesis, but cannot become a fact. A vendor claim can inform a policy snapshot, but may need independent verification if used as high-stakes evidence.

### **5.7. Review Loop Context**

Review Loop Context отвечает за post-submission learning.

ReviewOutcome represents editor decision, reviewer comments, requested revisions, objections, reasons, timeline and decision type.

RevisionPlan maps review issues to actions.

RebuttalOutline helps prepare response but must not fabricate evidence or overstate compliance.

VenueMemory stores learned information from submission outcomes, but every learned signal must be marked as user-specific, dated, scoped and evidentially limited.

### **5.8. Integration Context**

Integration Context defines how Journal-Yuga connects to Litops, WhiteCrow, external documents and user interfaces.

Litops integration:

Sources;  
Worksets;  
ContextPacks;  
Artifacts;  
Vault cards;  
Search/index;  
Raw storage.

WhiteCrow integration:

Field;  
Field Text;  
Manuscript;  
ArticleTrajectory;  
ProtectedCore;  
PatchQueue;  
ExternalDocBridge.

External document boundary:

Google Docs;  
DOCX;  
PDF;  
OJS;  
Editorial Manager;  
ScholarOne;  
email submission;  
journal portal forms.

Journal-Yuga should not automate final submission in MVP. It should prepare structured submission packs and field mappings.

## **6\. First Wave Closure**

This first wave defines what the system is and what it is not. It establishes that Journal-Yuga is an evidence-first publication-positioning engine, not a journal recommender. It fixes the core formula, the place of the system inside Litops–WhiteCrow, the hard prohibitions, and the bounded contexts. Later waves must not reopen these decisions unless a contradiction appears in implementation.

The next wave should specify the entity model in detail: fields, statuses, relations, provenance requirements, minimal MVP versions and future full versions for ArticleModel, VenueModel, PublicationRegimeModel, SubmissionScenario, FitAssessment, MismatchMap, RewritePlan, CitationPlan, RiskReport, ComplianceChecklist, SubmissionPack and VenueMemory.

# **JOURNAL\_YUGA\_TECHNICAL\_SPEC\_FOR\_CLAUDE\_v0\_1**

## **Волна 2\. Объектная модель, сущности, поля, статусы, связи и минимальные MVP-версии**

## **6\. Entity Model**

Объектная модель Journal-Yuga должна быть устроена так, чтобы система могла выполнять доказательное публикационное позиционирование, а не просто выдавать рекомендации. Каждая сущность должна существовать не как произвольный LLM-ответ, а как воспроизводимый объект с идентификатором, источниками, статусом, provenance, confidence, связями с другими объектами и историей обновления. Если объект не может быть связан с источниками или пользовательским вводом, он должен маркироваться как предварительный, непроверенный или недоступный, но не выдаваться за факт.

Entity model Journal-Yuga делится на несколько групп: входные и исходные объекты; модели статьи и поля; модели venue и публикационного режима; сценарий подачи; аналитические объекты fit/mismatch/adaptation; compliance/submission объекты; review-loop объекты; evidence/provenance объекты; integration objects. Эта структура должна исключить типовую ошибку, при которой “журнал”, “страница журнала”, “требования к авторам”, “ожидания редакции”, “корпус опубликованных статей” и “мнение пользователя о журнале” сливаются в одну неразличимую сущность.

Каждая сущность Journal-Yuga должна иметь минимальный общий каркас:

entity\_id;  
entity\_type;  
created\_at;  
updated\_at;  
created\_by;  
source\_refs;  
context\_pack\_refs;  
artifact\_refs;  
evidence\_status;  
confidence;  
version;  
lifecycle\_status;  
staleness\_status;  
notes;  
unknowns;  
warnings.

`source_refs` указывают на Litops Source, EvidenceItem, Snapshot или пользовательский input. `context_pack_refs` указывают на воспроизводимый набор источников, на котором основан объект. `artifact_refs` указывают на производные отчёты, карты, планы, карточки или файлы. `evidence_status` фиксирует статус знания. `confidence` не заменяет evidence; он показывает уверенность в интерпретации. `unknowns` обязательны: система должна уметь явно хранить неизвестное, а не замещать неизвестное догадкой.

## **6.1. Evidence Status Taxonomy**

Прежде чем описывать сущности, нужно зафиксировать общий словарь статусов доказательности. Он должен использоваться во всех объектах Journal-Yuga.

`FACT_FROM_SOURCE` означает, что утверждение взято из открытого источника: страница журнала, guidelines, API metadata, DOI metadata, journal page, corpus article, official policy, review letter or user-provided document. Оно не обязательно истинно в абсолютном смысле, но имеет проверяемый источник.

`VENDOR_CLAIM` означает, что утверждение заявлено владельцем сервиса, издателем, платформой или журналом. Например, “AI-powered matching”, “fast review”, “indexed in X”, “recommended for Y”. Такие claims должны храниться как claims, а не как независимо проверенные факты.

`CORPUS_OBSERVATION` означает, что вывод сделан из набора опубликованных статей, issue pages, abstracts, metadata or full text corpus. Он должен иметь ссылку на corpus snapshot, размер выборки, критерий отбора и период.

`INFERENCE` означает аккуратный вывод системы из источников. Например, “журнал фактически предпочитает empirical case-based articles” на основании корпуса. Inference не должен превращаться в fact.

`TACIT_SIGNAL` означает неформальное знание: пользовательский опыт подачи, разговор с редактором, замечание коллеги, наблюдение о скорости review, практическое знание о том, что журнал “не любит” или “скорее берёт”. Такой сигнал может быть полезен, но всегда должен иметь пониженный статус.

`USER_NOTE` означает пользовательскую заметку, намерение, ограничение или гипотезу. Она является фактом о пользовательском сценарии, но не фактом о журнале.

`PRIOR_OUTCOME` означает результат прошлой подачи: desk reject, revise and resubmit, accepted, rejected after review, withdrawn, no response, invited resubmission. Он связан с конкретным manuscript, author context and date.

`UNKNOWN` означает, что поле не установлено.

`INACCESSIBLE` означает, что источник найден, но не открыт, не распарсен или не извлечён.

`STALE` означает, что источник или snapshot устарел по правилам freshness policy.

`CONFLICTING_EVIDENCE` означает, что разные источники дают несовместимые сведения.

Эта taxonomy является обязательной. Любой объект Journal-Yuga, особенно VenueModel, FitAssessment, CitationPlan, RiskReport and SubmissionPack, должен использовать эти статусы.

## **6.2. Source and Evidence Objects**

Journal-Yuga не должен дублировать Litops Source, но ему нужен собственный слой ссылок на evidence. Поэтому вводятся lightweight Journal-Yuga evidence objects, которые всегда ссылаются на Litops Source или внешний source ref.

### **EvidenceItem**

Назначение: атомарный фрагмент доказательства, используемый в модели журнала, статье, fit assessment, risk report or submission pack.

Минимальные поля:

evidence\_id;  
source\_id;  
source\_type;  
url\_or\_file\_ref;  
title;  
retrieved\_at;  
extracted\_at;  
excerpt\_or\_locator;  
page\_or\_section;  
claim\_supported;  
evidence\_status;  
confidence;  
used\_in\_entities;  
staleness\_policy;  
notes.

`claim_supported` должен быть коротким и конкретным: например, “journal requires 150-word abstract”, “journal page lists editorial board”, “corpus article has IMRaD structure”, “policy page mentions AI-generated text”, “review letter requests stronger methods section”.

MVP: EvidenceItem может быть простым JSONL объектом, созданным из URL/page snapshot/manual extraction.

Full version: EvidenceItem может хранить locator, text span, screenshot reference, DOM path, PDF page, quote hash, embedding ref.

### **SourceSnapshot**

Назначение: фиксировать состояние внешнего источника на момент анализа.

Поля:

snapshot\_id;  
source\_id;  
url;  
retrieved\_at;  
content\_hash;  
content\_type;  
parser\_used;  
raw\_ref;  
text\_ref;  
extraction\_status;  
extraction\_errors;  
staleness\_policy;  
used\_in\_context\_packs.

MVP: snapshot может быть text extraction \+ source\_id.

Full version: html/pdf/image snapshot, screenshot, structured extraction, diff against previous snapshot.

### **ContextPackRef**

Назначение: ссылка на Litops ContextPack как воспроизводимую базу анализа.

Поля:

context\_pack\_id;  
context\_pack\_type;  
scope;  
source\_ids;  
evidence\_ids;  
created\_at;  
used\_for;  
coverage\_notes;  
known\_gaps.

ContextPack types:

article\_context\_pack;  
venue\_context\_pack;  
venue\_pool\_context\_pack;  
fit\_context\_pack;  
submission\_context\_pack;  
review\_context\_pack.

## **6.3. ArticleModel**

ArticleModel — это публикационно-ориентированная модель статьи. Она не равна полному тексту, abstract-у или файлу manuscript-а. ArticleModel описывает, что этот текст делает как академическая статья: какую проблему ставит, какой объект строит, какие тезисы выдвигает, в какой дисциплинарный режим может быть введён, какой жанр предполагает, какой novelty mode использует, какие теоретические плечи и citation ecology уже имеет, какие элементы protected core нельзя менять без согласия пользователя.

ArticleModel создаётся из одного или нескольких источников: full manuscript, abstract, draft, user brief, WhiteCrow Field Text, Litops ContextPack, voice transcript, old paper, notes, bibliography. Если источников недостаточно, ArticleModel должен быть preliminary and incomplete.

Поля ArticleModel:

article\_model\_id;  
title\_current;  
title\_candidates;  
abstract\_current;  
abstract\_candidates;  
language;  
source\_refs;  
manuscript\_refs;  
field\_refs;  
context\_pack\_refs;  
input\_mode;  
article\_stage;  
problem\_statement;  
research\_question;  
object\_of\_inquiry;  
core\_claims;  
secondary\_claims;  
argument\_structure;  
method\_status;  
method\_description;  
genre\_current;  
genre\_candidates;  
disciplinary\_register\_current;  
disciplinary\_register\_candidates;  
novelty\_mode;  
theoretical\_shoulders;  
opponents\_or\_contrasts;  
key\_terms;  
citation\_ecology\_current;  
bibliography\_status;  
empirical\_material\_status;  
audience\_current;  
audience\_candidates;  
publication\_intent;  
protected\_core;  
mutable\_zones;  
high\_risk\_zones;  
unknowns;  
confidence;  
evidence\_refs;  
lifecycle\_status.

`input_mode` может принимать значения: `abstract_only`, `draft_text`, `full_manuscript`, `whitecrow_field`, `litops_context_pack`, `user_brief`, `review_letter_context`, `mixed`.

`article_stage`: `idea`, `abstract`, `outline`, `draft`, `full_manuscript`, `submission_ready`, `revising`, `published`, `unknown`.

`method_status`: `no_method`, `implicit_method`, `conceptual_method`, `empirical_method`, `case_based`, `review_method`, `mixed`, `unknown`.

`genre_current`: `research_article`, `conceptual_article`, `theoretical_essay`, `review`, `systematic_review`, `position_paper`, `commentary`, `conference_paper`, `forum_piece`, `book_symposium_piece`, `unknown`.

`novelty_mode`: `new_object`, `new_theory`, `new_method`, `new_application`, `new_synthesis`, `critique`, `translation_between_fields`, `case_contribution`, `empirical_finding`, `unknown`.

`protected_core` должен быть отдельным полем, а не заметкой. Он описывает смысловые элементы, которые нельзя менять автоматически: центральное различение, объект, thesis, philosophical stance, theoretical commitments, language/voice constraints, field-level promise.

MVP minimal ArticleModel:

article\_model\_id;  
source\_refs;  
title\_current;  
abstract\_current or summary;  
problem\_statement;  
object\_of\_inquiry;  
core\_claims;  
genre\_current;  
disciplinary\_register\_current;  
method\_status;  
citation\_ecology\_current;  
protected\_core;  
unknowns;  
confidence.

Full ArticleModel adds variants, audiences, theoretical shoulders, opponents, bibliography mapping, section-level block mapping and field-derived sibling trajectories.

Relations:

ArticleModel can have many ManuscriptModels.  
ArticleModel can produce many ArticleVariants.  
ArticleModel is used by FitAssessment.  
ArticleModel can be derived from WhiteCrow FieldModelReference.  
ArticleModel can be updated by RewritePlan and RevisionPlan.

Lifecycle:

draft\_created;  
needs\_user\_confirmation;  
confirmed;  
used\_for\_fit;  
revised;  
superseded;  
archived.

A FitAssessment based on unconfirmed ArticleModel must be marked preliminary.

## **6.4. ManuscriptModel**

ManuscriptModel represents the actual working text. It is a structural map of a manuscript file or document. It should not replace ArticleModel.

Поля:

manuscript\_id;  
article\_model\_id;  
source\_file\_refs;  
external\_doc\_refs;  
title;  
abstract;  
keywords;  
sections;  
section\_blocks;  
bibliography\_refs;  
figures;  
tables;  
supplementary\_materials;  
word\_count;  
character\_count;  
language;  
format;  
style;  
version;  
created\_at;  
updated\_at;  
block\_mapping\_status;  
unknowns.

MVP: title, abstract, sections, word count, bibliography presence, file ref.

Full: block-level mapping to Google Docs/DOCX, paragraph ids, patch targets, citation anchors, figure/table mapping.

Relations:

ManuscriptModel belongs to ArticleModel.  
RewritePlan targets ManuscriptModel sections/blocks.  
SubmissionPack packages ManuscriptModel outputs.  
WhiteCrow PatchQueue may target ManuscriptModel blocks.

## **6.5. FieldModelReference**

FieldModelReference is not a full WhiteCrow Field. It is a pointer/projection of field data relevant for publication positioning.

Поля:

field\_ref\_id;  
whitecrow\_field\_id;  
field\_text\_refs;  
context\_pack\_refs;  
field\_summary;  
central\_tensions;  
relation\_clusters;  
protected\_core;  
possible\_article\_trajectories;  
source\_refs;  
confidence;  
unknowns.

MVP: pointer \+ summary \+ protected core.

Full: structured relation clusters, article trajectories, sibling manuscript paths.

Relations:

FieldModelReference can generate one or more ArticleModels.  
ProtectedCore can be inherited into ArticleModel.  
Journal-Yuga outputs may return to WhiteCrow as patch or trajectory suggestions.

## **6.6. ArticleVariant**

ArticleVariant represents a possible publication-oriented version of an ArticleModel. It is essential when one field can become different articles for different disciplines or venues.

Поля:

variant\_id;  
base\_article\_model\_id;  
variant\_name;  
target\_discipline;  
target\_publication\_regime;  
target\_venue\_pool\_refs;  
changed\_elements;  
preserved\_core;  
reframed\_core;  
new\_title\_candidates;  
new\_abstract\_candidate;  
required\_new\_sections;  
required\_citation\_bridges;  
estimated\_effort;  
field\_core\_risk;  
status.

MVP: optional; can be stubbed.

Full: used for reverse design and sibling manuscript trajectories.

## **6.7. VenueModel**

VenueModel is the central model of a publication container. It must be broader than JournalModel. Venue can be a journal, section, issue, special issue, research topic, conference proceedings, reviewed preprint platform, edited volume, humanities symposium or other regime.

Поля VenueModel:

venue\_model\_id;  
venue\_type;  
canonical\_name;  
aliases;  
publisher\_or\_owner;  
official\_urls;  
source\_refs;  
context\_pack\_refs;  
journal\_model\_id;  
section\_model\_ids;  
issue\_model\_ids;  
publication\_regime\_id;  
scope\_summary;  
subject\_areas;  
disciplinary\_registers;  
article\_types\_supported;  
language\_policy;  
indexing\_claims;  
metrics\_claims;  
open\_access\_status;  
APC\_policy;  
submission\_system;  
review\_process\_claims;  
review\_timeline\_claims;  
author\_guidelines\_refs;  
policy\_refs;  
editorial\_board\_profile\_id;  
published\_corpus\_id;  
citation\_expectation\_profile\_id;  
tacit\_signal\_ids;  
prior\_outcome\_ids;  
unknowns;  
staleness\_status;  
confidence;  
evidence\_refs.

`venue_type`: `journal`, `journal_section`, `special_issue`, `research_topic`, `conference_proceedings`, `reviewed_preprint`, `open_review_venue`, `edited_volume`, `book_symposium`, `local_journal`, `other`.

MVP VenueModel:

venue\_model\_id;  
canonical\_name;  
venue\_type;  
official\_urls;  
scope\_summary;  
author\_guidelines\_refs;  
article\_types\_supported;  
language\_policy;  
publication\_regime\_id;  
source\_refs;  
unknowns;  
confidence.

Full VenueModel includes corpus, editorial board, policies, metrics, citation ecology, tacit signals, prior outcomes and staleness rules.

Relations:

VenueModel uses JournalModel where venue is journal-based.  
VenueModel has PublicationRegimeModel.  
VenueModel is used in FitAssessment.  
VenueModel can have PublishedArticleCorpus.  
VenueModel can generate VenueMemory.

Lifecycle:

identified;  
light\_profile\_created;  
sources\_collected;  
deep\_profile\_created;  
needs\_refresh;  
stale;  
archived.

## **6.8. JournalModel**

JournalModel represents the serial journal entity.

Поля:

journal\_model\_id;  
canonical\_title;  
ISSN\_print;  
ISSN\_electronic;  
publisher;  
journal\_homepage;  
aims\_and\_scope\_url;  
instructions\_url;  
editorial\_board\_url;  
submission\_url;  
open\_access\_url;  
policies\_url;  
indexing\_url;  
metrics\_url;  
subject\_categories;  
publisher\_portfolio\_bias;  
official\_claims;  
verified\_metadata;  
source\_refs;  
last\_checked\_at;  
unknowns.

MVP: title, publisher, URLs, scope, instructions.

Full: ISSN, indexing, metrics, publisher systems, policies, sections.

JournalModel should not contain all venue behavior. Section/special issue/research topic differences belong to specialized models.

## **6.9. SectionModel**

SectionModel describes a section, article type or recurring publication area inside a journal.

Поля:

section\_model\_id;  
journal\_model\_id;  
section\_name;  
article\_type;  
scope;  
requirements;  
typical\_structure;  
editor\_refs;  
recent\_articles\_refs;  
fit\_notes;  
evidence\_refs;  
unknowns.

Examples:

research article;  
review article;  
essay;  
perspective;  
commentary;  
forum;  
methods;  
special section;  
book review;  
case study.

MVP: optional for first one-journal fit unless section is required.

Full: essential for journals with many article types.

## **6.10. IssueModel, SpecialIssueModel, ResearchTopicModel**

These models describe time-bound or theme-bound publication containers.

Поля:

issue\_or\_topic\_id;  
parent\_venue\_id;  
type;  
title;  
theme;  
description;  
editors;  
deadline;  
article\_types;  
submission\_url;  
CFP\_url;  
requirements;  
target\_disciplines;  
recent\_or\_expected\_articles;  
status;  
evidence\_refs;  
unknowns.

`type`: `regular_issue`, `special_issue`, `research_topic`, `topical_collection`, `conference_track`, `call_for_papers`, `edited_volume_call`.

MVP: CFP/special issue as source \+ lightweight model.

Full: special issue matching, deadline/risk planning, editor/topic fit.

## **6.11. PublicationRegimeModel**

PublicationRegimeModel describes how publication works in this container. It is required because different regimes have different gates, review logic, compliance requirements and fit criteria.

Поля:

publication\_regime\_id;  
regime\_type;  
description;  
review\_model;  
submission\_gates;  
selection\_logic;  
typical\_article\_forms;  
timeline\_pattern;  
fit\_axes\_modifier;  
compliance\_modifier;  
risk\_modifier;  
submission\_pack\_requirements;  
examples;  
evidence\_refs;  
unknowns.

Regime types:

classic\_journal\_article;  
special\_issue\_article;  
research\_topic\_article;  
conference\_proceedings;  
mega\_journal;  
reviewed\_preprint;  
publish\_then\_review;  
open\_review\_conference;  
humanities\_special\_issue;  
book\_symposium;  
focused\_debate;  
edited\_volume;  
non\_focus\_q3\_or\_local\_journal;  
zine\_or\_nonstandard\_publication\_backlog.

MVP: enum \+ short descriptions \+ modifiers.

Full: entity with custom workflow templates.

Relations:

VenueModel must reference PublicationRegimeModel.  
FitAssessment must include publication\_regime\_fit.  
SubmissionPack depends on PublicationRegimeModel.  
RiskReport depends on PublicationRegimeModel.

## **6.12. EditorialBoardProfile**

EditorialBoardProfile models visible editorial structure. It must not become speculation about hidden preferences.

Поля:

editorial\_board\_profile\_id;  
venue\_model\_id;  
source\_refs;  
people;  
roles;  
affiliations;  
disciplines;  
geographies;  
declared\_editorial\_scope;  
possible\_field\_signals;  
confidence;  
unknowns;  
last\_checked\_at.

MVP: source refs \+ summary.

Full: structured people/affiliations/disciplines, but no ungrounded psychologizing.

Allowed inference:

The board composition may suggest disciplinary center of gravity.

Forbidden inference:

“This editor will like/dislike the article” without tacit/prior evidence.

## **6.13. PublishedArticleCorpus**

PublishedArticleCorpus is the corpus used to infer actual publication patterns.

Поля:

corpus\_id;  
venue\_model\_id;  
selection\_strategy;  
time\_range;  
article\_count;  
article\_refs;  
metadata\_refs;  
full\_text\_available\_count;  
abstract\_only\_count;  
source\_refs;  
representativeness\_notes;  
bias\_notes;  
created\_at;  
staleness\_status.

Selection strategies:

recent\_articles;  
most\_cited;  
most\_read;  
special\_issue\_articles;  
section\_articles;  
user\_uploaded\_pack;  
search\_based;  
manual\_selection;  
mixed.

MVP: small recent corpus or user-uploaded corpus with bias note.

Full: 20–50 article corpus with patterns.

Relations:

PublishedArticleCorpus produces PublishedArticlePattern and CitationExpectationProfile.  
FitAssessment can use corpus observations.

## **6.14. PublishedArticlePattern**

PublishedArticlePattern stores observations mined from corpus.

Поля:

pattern\_id;  
corpus\_id;  
pattern\_type;  
description;  
frequency;  
examples;  
evidence\_refs;  
confidence;  
limitations.

Pattern types:

abstract\_structure;  
introduction\_move;  
literature\_review\_shape;  
method\_presence;  
case\_presence;  
argument\_structure;  
citation\_density;  
reference\_age\_distribution;  
theory\_usage;  
empirical\_material;  
conclusion\_style;  
article\_length;  
section\_structure;  
novelty\_claim\_form.

MVP: small set of human-readable observations.

Full: structured genre/move mining.

## **6.15. CitationExpectationProfile**

CitationExpectationProfile describes what kind of citation ecology a venue or article type appears to expect.

Поля:

citation\_profile\_id;  
venue\_model\_id;  
corpus\_id;  
disciplinary\_anchors;  
recent\_debate\_markers;  
method\_references;  
canonical\_authors;  
frequent\_sources;  
missing\_bridge\_categories;  
dangerous\_padding\_warnings;  
reference\_count\_range;  
reference\_age\_pattern;  
self\_citation\_signals;  
venue\_citation\_signals;  
evidence\_refs;  
confidence;  
unknowns.

MVP: reference count range, key anchors from corpus/manual analysis, missing bridge categories.

Full: OpenAlex/OpenCitations/Crossref-supported citation graph and venue-citation ecology.

Relations:

CitationPlan compares ArticleModel bibliography to CitationExpectationProfile.

## **6.16. TacitVenueSignal**

TacitVenueSignal captures non-formal knowledge without promoting it to fact.

Поля:

tacit\_signal\_id;  
venue\_model\_id;  
signal\_text;  
signal\_type;  
source\_type;  
provided\_by;  
date\_observed;  
scope;  
confidence;  
sensitivity;  
evidence\_status;  
used\_in;  
expiration\_or\_review\_date;  
notes.

Signal types:

review\_speed\_experience;  
desk\_reject\_pattern;  
editorial\_preference\_claim;  
article\_type\_preference;  
author\_eligibility\_signal;  
language\_signal;  
APC\_practice\_signal;  
communication\_signal;  
special\_issue\_signal.

Source types:

user\_report;  
colleague\_report;  
editor\_contact;  
prior\_submission;  
community\_observation;  
inference\_from\_public\_data.

MVP: user note with status TACIT\_SIGNAL.

Full: VenueMemory integration with privacy controls.

## **6.17. SubmissionScenario**

SubmissionScenario represents user goal and constraints. It is required for meaningful fit.

Поля:

submission\_scenario\_id;  
user\_id\_or\_project\_id;  
article\_model\_id;  
target\_venue\_ids;  
goal;  
target\_indexing;  
prestige\_priority;  
speed\_priority;  
acceptance\_probability\_priority;  
field\_core\_preservation\_priority;  
APC\_constraints;  
language\_constraints;  
deadline;  
rewrite\_depth\_allowed;  
reframe\_depth\_allowed;  
empirical\_additions\_allowed;  
citation\_expansion\_allowed;  
coauthor\_constraints;  
affiliation\_constraints;  
article\_type\_preference;  
fallback\_allowed;  
risk\_tolerance;  
questions\_asked;  
answers;  
unknowns;  
status.

`rewrite_depth_allowed`: `none`, `light`, `medium`, `major`, `unknown`.

`reframe_depth_allowed`: `none`, `minor`, `disciplinary_translation`, `new_article_variant`, `unknown`.

`fallback_allowed`: Q3/local journal, conference proceedings, preprint, edited volume, special issue, none, unknown.

MVP: scenario interview of 5–7 fields.

Full: user/project-level preference memory.

Lifecycle:

draft;  
needs\_user\_answers;  
confirmed;  
used\_for\_fit;  
updated;  
archived.

## **6.18. FitAssessment**

FitAssessment is a structured comparison of ArticleModel × VenueModel × SubmissionScenario.

Поля:

fit\_assessment\_id;  
article\_model\_id;  
venue\_model\_id;  
submission\_scenario\_id;  
context\_pack\_refs;  
assessment\_level;  
overall\_label;  
topic\_fit;  
disciplinary\_fit;  
genre\_fit;  
argument\_form\_fit;  
method\_fit;  
citation\_ecology\_fit;  
novelty\_mode\_fit;  
language\_register\_fit;  
audience\_fit;  
formal\_compliance\_fit;  
author\_eligibility\_fit;  
publication\_regime\_fit;  
field\_core\_preservation\_risk;  
rewrite\_effort;  
citation\_effort;  
compliance\_effort;  
time\_risk;  
strategic\_value;  
confidence;  
evidence\_refs;  
unknowns;  
mismatch\_map\_id;  
recommendation;  
status.

`assessment_level`: `quick_scan`, `light_profile`, `deep_profile`, `post_review`.

`overall_label`: `strong_candidate`, `possible`, `possible_but_costly`, `poor_fit`, `high_risk`, `not_enough_data`.

Axis values should be qualitative: `strong`, `medium`, `weak`, `bad`, `unknown`, plus evidence refs. Avoid numeric scores in MVP.

MVP: one article × one venue fit with 8–12 axes.

Full: multi-venue comparison, scenario-sensitive ranking, historical calibration.

## **6.19. MismatchMap**

MismatchMap describes specific differences between article and venue.

Поля:

mismatch\_map\_id;  
fit\_assessment\_id;  
mismatches;  
summary;  
critical\_mismatches;  
actionable\_mismatches;  
non\_actionable\_mismatches;  
unknowns.

Mismatch item fields:

mismatch\_id;  
axis;  
article\_side;  
venue\_side;  
description;  
severity;  
evidence\_refs;  
possible\_actions;  
field\_core\_risk;  
requires\_user\_acceptance;  
status.

Axes:

topic;  
discipline;  
genre;  
argument;  
method;  
novelty;  
citation\_ecology;  
formal\_requirements;  
language\_register;  
audience;  
publication\_regime;  
author\_eligibility;  
timeline;  
policy.

MVP: list/table of mismatches.

Full: visual map and patch linkage.

## **6.20. RewritePlan**

RewritePlan describes changes to manuscript form that can improve fit.

Поля:

rewrite\_plan\_id;  
article\_model\_id;  
manuscript\_id;  
fit\_assessment\_id;  
target\_venue\_id;  
changes;  
summary;  
estimated\_effort;  
field\_core\_risk;  
requires\_user\_acceptance;  
status.

Change item fields:

change\_id;  
target\_block;  
change\_type;  
current\_state;  
desired\_state;  
reason;  
evidence\_refs;  
related\_mismatch\_id;  
expected\_fit\_gain;  
field\_core\_risk;  
difficulty;  
draft\_text\_optional;  
status.

Change types:

title\_adjustment;  
abstract\_rewrite;  
intro\_reframe;  
literature\_review\_bridge;  
method\_disclosure;  
argument\_reordering;  
section\_addition;  
section\_removal;  
citation\_bridge;  
conclusion\_refocus;  
language\_register\_shift;  
formatting\_change.

MVP: action plan, no automatic full rewrite.

Full: patch queue and external doc integration.

## **6.21. ReframePlan**

ReframePlan describes deeper changes than RewritePlan. It may produce a new ArticleVariant.

Поля:

reframe\_plan\_id;  
base\_article\_model\_id;  
target\_regime\_or\_venue\_pool;  
new\_article\_variant\_id;  
reframed\_object;  
reframed\_question;  
reframed\_discipline;  
new\_genre;  
new\_method\_status;  
new\_theoretical\_shoulders;  
core\_preserved;  
core\_lost;  
risk;  
required\_user\_acceptance;  
status.

MVP: produce warning and sibling suggestion.

Full: article variant generation.

## **6.22. CitationPlan**

CitationPlan describes citation work needed for fit.

Поля:

citation\_plan\_id;  
article\_model\_id;  
venue\_model\_id;  
citation\_expectation\_profile\_id;  
current\_bibliography\_status;  
missing\_bridge\_categories;  
recommended\_reference\_search\_tasks;  
verified\_reference\_suggestions;  
pending\_reference\_suggestions;  
dangerous\_padding\_warnings;  
formatting\_requirements;  
source\_verification\_status;  
evidence\_refs;  
risk\_flags;  
status.

Reference suggestion fields:

reference\_candidate\_id;  
title;  
authors;  
year;  
DOI\_or\_identifier;  
source\_url;  
role;  
verification\_status;  
why\_needed;  
related\_mismatch\_id.

Roles:

field\_anchor;  
recent\_debate\_marker;  
method\_reference;  
opponent;  
bridge\_between\_traditions;  
venue\_local\_reference;  
empirical\_context;  
theory\_background.

MVP: categories \+ search tasks \+ verify existing bibliography.

Full: actual verified reference candidates via adapters.

## **6.23. RiskReport**

RiskReport describes publication risks.

Поля:

risk\_report\_id;  
article\_model\_id;  
venue\_model\_id;  
submission\_scenario\_id;  
risk\_items;  
overall\_risk\_label;  
blocking\_risks;  
warnings;  
unknowns;  
evidence\_refs;  
status.

Risk item fields:

risk\_id;  
risk\_type;  
description;  
severity;  
likelihood;  
evidence\_refs;  
mitigation;  
requires\_user\_action;  
status.

Risk types:

formal\_noncompliance;  
scope\_mismatch;  
method\_weakness;  
citation\_gap;  
reference\_validity;  
plagiarism\_or\_self\_plagiarism;  
AI\_disclosure;  
authorship\_or\_CRediT;  
COI\_or\_funding;  
data\_availability;  
ethics\_approval;  
APC\_or\_predatory;  
indexing\_uncertainty;  
author\_eligibility;  
timeline;  
reviewer\_misunderstanding;  
field\_core\_loss.

MVP: risk table with blocking/warning labels.

Full: compliance engine and external checkers.

## **6.24. ComplianceChecklist**

ComplianceChecklist is not generic. It is selected/generated from venue requirements, publication regime, article type and method.

Поля:

compliance\_checklist\_id;  
venue\_model\_id;  
article\_model\_id;  
publication\_regime\_id;  
checklist\_items;  
guideline\_sources;  
status;  
missing\_items;  
blocking\_items;  
warnings;  
evidence\_refs.

Checklist item fields:

item\_id;  
category;  
requirement;  
status;  
source\_ref;  
user\_action\_needed;  
output\_location;  
notes.

Categories:

metadata;  
formatting;  
word\_count;  
abstract;  
keywords;  
references;  
figures\_tables;  
supplementary\_files;  
ethics;  
COI;  
funding;  
data\_availability;  
AI\_disclosure;  
authorship;  
reporting\_guideline;  
cover\_letter;  
reviewer\_suggestions;  
submission\_system\_fields.

MVP: generic \+ venue-derived checklist.

Full: guideline-selection engine.

## **6.25. SubmissionPack**

SubmissionPack is the operational object for submission. It is not just a report.

Поля:

submission\_pack\_id;  
article\_model\_id;  
manuscript\_id;  
venue\_model\_id;  
submission\_scenario\_id;  
compliance\_checklist\_id;  
files;  
metadata;  
statements;  
cover\_letter;  
author\_information;  
reference\_package;  
figures\_tables;  
supplementary\_materials;  
portal\_field\_mapping;  
missing\_items;  
blocking\_issues;  
warnings;  
ready\_status;  
created\_at;  
updated\_at.

Ready statuses:

not\_ready;  
needs\_user\_input;  
needs\_file\_update;  
needs\_reference\_verification;  
needs\_compliance\_check;  
ready\_for\_manual\_submission;  
submitted;  
archived.

MVP: checklist \+ metadata \+ missing items \+ cover letter skeleton.

Full: portal-specific packaging and external doc integration.

## **6.26. ReviewerSimulation**

ReviewerSimulation is controlled risk analysis, not real review.

Поля:

reviewer\_simulation\_id;  
article\_model\_id;  
venue\_model\_id;  
simulation\_scope;  
possible\_objections;  
likely\_confusions;  
missing\_evidence;  
citation\_objections;  
method\_objections;  
genre\_objections;  
scope\_objections;  
rebuttal\_preparation\_notes;  
evidence\_refs;  
disclaimer;  
status.

MVP: not implemented; schema/prohibition only.

Full: pre-submission risk mode with strict labeling.

## **6.27. ReviewOutcome**

ReviewOutcome stores actual outcome after submission or review.

Поля:

review\_outcome\_id;  
submission\_pack\_id;  
venue\_model\_id;  
article\_model\_id;  
decision\_type;  
editor\_letter\_ref;  
reviewer\_comment\_refs;  
received\_at;  
review\_round;  
timeline;  
main\_reasons;  
requested\_changes;  
tone;  
actionability;  
evidence\_refs;  
privacy\_status.

Decision types:

desk\_reject;  
reject\_after\_review;  
revise\_and\_resubmit;  
minor\_revision;  
accept;  
withdrawn;  
no\_response;  
unknown.

## **6.28. RevisionPlan**

RevisionPlan maps review outcome to actions.

Поля:

revision\_plan\_id;  
review\_outcome\_id;  
article\_model\_id;  
venue\_model\_id;  
revision\_items;  
rebuttal\_outline\_id;  
estimated\_effort;  
risk;  
recommendation;  
status.

Revision item fields:

item\_id;  
reviewer\_or\_editor\_source;  
issue\_type;  
comment\_summary;  
required\_action;  
target\_block;  
evidence\_needed;  
accept\_or\_resist;  
response\_strategy;  
status.

Issue types:

formal;  
scope;  
method;  
citation;  
argument\_clarity;  
novelty;  
writing;  
reviewer\_misunderstanding;  
fatal\_mismatch;  
unknown.

## **6.29. VenueMemory**

VenueMemory stores accumulated knowledge about a venue. It must not collapse facts, tacit signals and prior outcomes.

Поля:

venue\_memory\_id;  
venue\_model\_id;  
facts;  
vendor\_claims;  
corpus\_observations;  
tacit\_signals;  
prior\_outcomes;  
known\_requirements;  
known\_risks;  
successful\_article\_patterns;  
failed\_submission\_patterns;  
last\_updated\_at;  
staleness\_status;  
privacy\_level;  
evidence\_refs.

MVP: store prior outcomes and tacit notes with status.

Full: learning loop and historical calibration.

## **7\. Entity Lifecycles**

Every major entity must have lifecycle states. This prevents stale, preliminary or unverified objects from being reused as if they were final.

Common lifecycle states:

created;  
draft;  
needs\_sources;  
needs\_user\_input;  
evidence\_collected;  
analyzed;  
preliminary;  
confirmed;  
accepted\_by\_user;  
used\_in\_output;  
stale;  
superseded;  
archived;  
error.

ArticleModel lifecycle:

created from input;  
preliminary extraction;  
needs user confirmation;  
confirmed;  
used for fit;  
updated after rewrite;  
superseded by variant.

VenueModel lifecycle:

identified;  
light profile;  
needs source collection;  
sources collected;  
deep profile;  
stale;  
refreshed;  
archived.

SubmissionScenario lifecycle:

draft;  
questions generated;  
needs user answers;  
confirmed;  
used for assessment;  
updated;  
archived.

FitAssessment lifecycle:

draft;  
insufficient evidence;  
preliminary;  
evidence-backed;  
reviewed by user;  
superseded after article/venue/scenario update.

RewritePlan lifecycle:

generated;  
needs user acceptance;  
accepted;  
rejected;  
partially applied;  
sent to WhiteCrow PatchQueue;  
archived.

SubmissionPack lifecycle:

draft;  
needs metadata;  
needs compliance;  
needs files;  
ready for manual submission;  
submitted;  
outcome received;  
archived.

VenueMemory lifecycle:

created;  
updated from source;  
updated from user note;  
updated from outcome;  
contains stale signals;  
reviewed;  
archived.

## **8\. Relations Between Entities**

The minimum graph of relations:

FieldModelReference → ArticleModel  
ArticleModel → ManuscriptModel  
ArticleModel → ArticleVariant  
ArticleModel \+ VenueModel \+ SubmissionScenario → FitAssessment  
VenueModel → JournalModel  
VenueModel → PublicationRegimeModel  
VenueModel → EditorialBoardProfile  
VenueModel → PublishedArticleCorpus  
PublishedArticleCorpus → PublishedArticlePattern  
PublishedArticleCorpus → CitationExpectationProfile  
FitAssessment → MismatchMap  
MismatchMap → RewritePlan  
MismatchMap → ReframePlan  
CitationExpectationProfile \+ ArticleModel → CitationPlan  
FitAssessment → RiskReport  
VenueModel \+ PublicationRegimeModel \+ ArticleModel → ComplianceChecklist  
ComplianceChecklist \+ ManuscriptModel → SubmissionPack  
SubmissionPack → ReviewOutcome  
ReviewOutcome → RevisionPlan  
ReviewOutcome → VenueMemory  
VenueMemory → future VenueModel / FitAssessment updates

No entity should be stored without relation to source/evidence unless it is explicitly user-provided or preliminary.

## **9\. MVP Object Scope**

The first working implementation should not attempt full ontology. It should create enough of the object model to support one manuscript × one target venue.

MVP-0 schemas:

ArticleModel minimal;  
ManuscriptModel minimal;  
VenueModel minimal;  
PublicationRegimeModel enum;  
SubmissionScenario minimal;  
EvidenceItem;  
ContextPackRef;  
FitAssessment minimal;  
MismatchMap minimal;  
RewritePlan minimal;  
CitationPlan stub;  
RiskReport minimal;  
ComplianceChecklist minimal;  
SubmissionPack stub.

MVP-1 behavior:

User provides manuscript or abstract and target venue URL/name.  
System creates ArticleModel.  
System creates light VenueModel from official pages/manual sources.  
System asks/records SubmissionScenario.  
System creates FitAssessment.  
System creates MismatchMap.  
System creates RewritePlan, CitationPlan stub, RiskReport and ComplianceChecklist.  
System creates human-readable artifact with source refs and unknowns.

MVP-1 must not implement:

full journal pool ranking;  
full article corpus mining;  
automatic submission;  
reviewer simulation;  
paid bibliometric APIs;  
plagiarism/AI detector integration;  
unverified citation recommendations.

## **10\. Persistence Requirements**

At minimum, every entity must be serializable as JSON. The implementation may use JSONL registries, SQLite/Postgres tables or existing Litops registries, but the technical spec must preserve stable IDs and relations.

Recommended registry groups:

journal\_yuga\_article\_models;  
journal\_yuga\_manuscripts;  
journal\_yuga\_field\_refs;  
journal\_yuga\_venue\_models;  
journal\_yuga\_publication\_regimes;  
journal\_yuga\_submission\_scenarios;  
journal\_yuga\_fit\_assessments;  
journal\_yuga\_mismatch\_maps;  
journal\_yuga\_rewrite\_plans;  
journal\_yuga\_citation\_plans;  
journal\_yuga\_risk\_reports;  
journal\_yuga\_compliance\_checklists;  
journal\_yuga\_submission\_packs;  
journal\_yuga\_review\_outcomes;  
journal\_yuga\_venue\_memory;  
journal\_yuga\_evidence\_items.

Human-readable Vault cards should be generated for:

ArticleModel;  
VenueModel;  
FitAssessment;  
RewritePlan;  
CitationPlan;  
RiskReport;  
SubmissionPack;  
VenueMemory.

## **11\. First Wave 2 Closure**

This wave defines the object model. The central rule is that Journal-Yuga must never operate only on raw prose or untyped LLM output. Every major operation must create or consume explicit entities. ArticleModel, VenueModel, SubmissionScenario and FitAssessment are mandatory. Evidence and provenance are not optional metadata; they are part of the domain model. PublicationRegimeModel, TacitVenueSignal, CitationExpectationProfile, ComplianceChecklist, SubmissionPack and VenueMemory prevent the system from collapsing into an ordinary journal finder.

The next wave should specify integration contracts with Litops and WhiteCrow in operational detail: what enters from Source/Workset/ContextPack/Artifact, what enters from Field/Manuscript/PatchQueue, what Journal-Yuga creates, where outputs are stored, and how provenance survives through every transformation.

# **JOURNAL\_YUGA\_TECHNICAL\_SPEC\_FOR\_CLAUDE\_v0\_1**

## **Волна 3\. Интеграционные контракты Litops, WhiteCrow, Journal-Yuga, Vault и внешних документов**

## **12\. Integration Architecture**

Journal-Yuga должен быть реализован не как изолированное приложение, а как bounded context, встроенный в существующую архитектуру Litops–WhiteCrow. Его собственная доменная область — публикационное позиционирование, но он зависит от двух соседних систем: от Litops — в части источников, хранения, provenance, context packs, vault projections and artifacts; от WhiteCrow — в части field logic, manuscript formation, protected core, patch queue and external document bridge.

Интеграционная архитектура должна исключить две ошибки. Первая ошибка — сделать Journal-Yuga отдельной базой “журналов и статей”, которая живёт без источников и не может воспроизвести свои выводы. Вторая ошибка — растворить Journal-Yuga внутри WhiteCrow и превратить venue-fit в ещё один режим генерации текста. Journal-Yuga должен иметь собственные сущности, но не должен владеть всем материалом. Он должен создавать производные publication-facing objects, а не забирать себе первичную память или ядро manuscript-процесса.

Интеграция строится вокруг четырёх границ:

Litops boundary — всё, что касается источников, intake, raw storage, deduplication, provenance, Source cards, Worksets, ContextPacks, registry, Vault projections, search, artifacts and reports.

WhiteCrow boundary — всё, что касается field, field reduction, manuscript state, protected core, article trajectories, patch queue, external document writing and conceptual integrity.

Journal-Yuga boundary — всё, что касается ArticleModel, VenueModel, PublicationRegimeModel, SubmissionScenario, FitAssessment, MismatchMap, RewritePlan, CitationPlan, RiskReport, ComplianceChecklist, SubmissionPack, ReviewOutcome, VenueMemory.

External boundary — всё, что касается Google Docs, DOCX/PDF, journal submission portals, OJS, Editorial Manager, ScholarOne, email submission, publisher web pages, APIs, bibliographic services, CFP pages, and any external tool or service.

Главное правило интеграции: Journal-Yuga не должен становиться владельцем первичных источников и не должен писать финальный manuscript напрямую без WhiteCrow/external document boundary. Он строит модели, планы, проверки, пакеты, карты, патчи и рекомендации. Он может создавать human-readable artifacts and structured outputs, но canonical source/provenance остаются в Litops, а текстовая судьба manuscript-а — в WhiteCrow or external doc bridge.

## **13\. Litops Integration Contract**

Litops является источниковым и корпусным слоем Journal-Yuga. Любой внешний материал, который влияет на выводы системы, должен быть зарегистрирован как Litops Source или как производная от Source. Это относится к страницам журналов, author guidelines, aims and scope, editorial board pages, issue pages, special issue CFP, DOI metadata, full-text PDFs, article abstracts, bibliographic records, OpenAlex/Crossref/OpenCitations API snapshots, screenshots, user-uploaded zip archives, review letters, email fragments, user notes and tacit experience reports.

Journal-Yuga может иметь собственные доменные registries, но не должен хранить внешние материалы как безымянные поля. Например, `VenueModel.scope_summary` может хранить краткое резюме aims/scope, но оно должно ссылаться на `EvidenceItem`, который ссылается на Litops Source. `CitationExpectationProfile` может хранить корпусное наблюдение, но оно должно ссылаться на `PublishedArticleCorpus`, который ссылается на Source IDs. `FitAssessment` может сказать, что жанр статьи плохо совпадает с журналом, но должен ссылаться на ArticleModel evidence and VenueModel evidence.

### **13.1. Inputs from Litops**

Journal-Yuga должен принимать от Litops следующие входы:

`source_id` — ссылка на единичный источник: файл, URL snapshot, PDF, markdown, transcript, note, review letter, journal page, API snapshot.

`workset_id` — набор источников, объединённых пользователем или системой для конкретной работы: например, “статьи журнала X”, “источники по AI subjectivity”, “материалы для подачи в журнал Y”.

`context_pack_id` — воспроизводимый пакет источников для конкретного анализа. ContextPack является основой доказательности. Для Journal-Yuga важны как минимум `article_context_pack`, `venue_context_pack`, `venue_pool_context_pack`, `fit_context_pack`, `submission_context_pack`, `review_context_pack`.

`artifact_id` — ранее созданный артефакт: report, article draft, field summary, source brief, corpus report, WhiteCrow field reduction, manuscript version, previous fit assessment.

`vault_card_ref` — human-readable projection source, useful for navigation but not canonical evidence by itself unless it references Source IDs.

`search_result_ref` — результат Litops search/RAG/index retrieval, который может быть использован для подготовки ContextPack, но не должен сам по себе считаться evidence without source resolution.

### **13.2. Outputs to Litops**

Journal-Yuga должен возвращать в Litops следующие outputs:

`journal_yuga_artifact` — human-readable report or document: ArticleModel report, VenueProfile, FitAssessment report, MismatchMap, RewritePlan, CitationPlan, RiskReport, SubmissionPack, ReviewOutcome analysis.

`journal_yuga_registry_record` — structured object in Journal-Yuga registry: ArticleModel, VenueModel, SubmissionScenario, FitAssessment etc.

`source_card_update` — карточки или ссылки на новые источники, если Journal-Yuga собирает новые страницы или документы.

`context_pack_update` — новый или обновлённый ContextPack for article, venue, pool, fit or submission.

`vault_projection` — Obsidian-readable markdown card for ArticleModel, VenueModel, FitAssessment, SubmissionPack, VenueMemory etc.

`derived_source` — если Journal-Yuga производит новый файл или документ, который сам становится source: for example submission checklist, cover letter draft, rewritten abstract candidate, citation plan table, review response outline.

`operation_trace` — machine-readable trace of the run: inputs, adapters, sources, prompts, outputs, errors, assumptions, user confirmations.

### **13.3. Litops ContextPack Rules**

ContextPack is the reproducibility unit of Journal-Yuga. If there is no ContextPack or equivalent evidence bundle, the output must be marked preliminary.

For one target venue, `venue_context_pack` should include:

journal homepage;  
aims and scope page;  
instructions for authors;  
article type or section requirements;  
editorial board page if accessible;  
submission system or submission information page;  
policies page;  
OA/APC/funder policy page if relevant;  
indexing/metrics page if available;  
recent articles or issue pages;  
special issue / CFP pages if relevant;  
API metadata snapshots;  
user tacit notes if supplied;  
prior submission outcomes if available.

For a fit assessment, `fit_context_pack` should include:

ArticleModel sources;  
ManuscriptModel source;  
SubmissionScenario user answers;  
VenueModel sources;  
PublishedArticleCorpus if used;  
CitationExpectationProfile evidence;  
formal requirements evidence;  
policy evidence;  
any tacit signals used;  
operation trace.

For journal pool discovery, `venue_pool_context_pack` may include light profiles for many venues. Light profile is allowed, but it must not be confused with deep VenueModel.

For review/rebuttal loop, `review_context_pack` should include:

submission pack;  
submitted manuscript version;  
editor letter;  
reviewer reports;  
prior fit assessment;  
prior rewrite/citation/risk plans;  
new revision plan;  
venue memory update.

### **13.4. Litops Source Types for Journal-Yuga**

Journal-Yuga should recognize source roles, not just file types. Recommended source roles:

`article_input` — user manuscript, abstract, draft, field-derived text.

`venue_homepage` — journal or venue homepage.

`aims_scope` — aims/scope page.

`author_guidelines` — instructions for authors.

`editorial_board` — board/editor page.

`submission_info` — submission portal or instructions.

`policy_page` — ethics, AI disclosure, data availability, open access, archiving, funder, copyright.

`issue_page` — regular issue or volume page.

`special_issue_cfp` — CFP or special issue page.

`research_topic` — topic collection page.

`published_article` — article page, abstract, PDF or metadata.

`api_metadata_snapshot` — OpenAlex, Crossref, OpenCitations, DOAJ, Sherpa etc.

`citation_metadata` — references/citations/DOI records.

`user_tacit_note` — user note about journal experience.

`prior_submission_outcome` — prior review/decision.

`review_letter` — editor/reviewer letter.

`submission_package_file` — generated or user-provided file for submission.

`compliance_guideline` — reporting/ethics/authorship guideline.

### **13.5. Litops Failure Rules**

If Journal-Yuga cannot register or resolve sources, it must not produce evidence-backed outputs. It may produce a preliminary note with status `insufficient_source_registration`.

If URL extraction fails, the system must create SourceSnapshot with `INACCESSIBLE` or `EXTRACTION_FAILED`, not silently ignore it.

If a source is stale, outputs depending on it must show staleness warning.

If evidence conflicts, the system must create `CONFLICTING_EVIDENCE` status and ask for user decision or additional source collection.

If a user uploads a package of articles and calls it “representative”, system must mark corpus selection strategy as `user_uploaded_pack` and add representativeness warning.

## **14\. WhiteCrow Integration Contract**

WhiteCrow is the field and manuscript formation layer. Journal-Yuga must receive publication-facing projections from WhiteCrow, not raw metaphysical totality of the field. The integration must allow deep use of field logic without collapsing Journal-Yuga into WhiteCrow.

### **14.1. Inputs from WhiteCrow**

Journal-Yuga should accept the following WhiteCrow-derived inputs:

`field_id` — reference to a WhiteCrow field.

`field_text_id` — a field-derived text or synthesis.

`manuscript_id` — a current manuscript object.

`article_trajectory_id` — a possible article trajectory from field to publication form.

`protected_core` — explicit set of semantic commitments, concepts, distinctions, claims or style constraints that should not be changed without user acceptance.

`patch_queue_state` — current state of pending/accepted/rejected manuscript patches.

`external_doc_ref` — Google Doc / DOCX / other working document connected to WhiteCrow.

`field_summary` — compressed representation of field sufficient for publication positioning.

`source_context_refs` — Litops ContextPack references used by WhiteCrow.

`style_or_voice_constraints` — constraints about authorial register, density, metaphorical layer, philosophical style or disciplinary posture.

### **14.2. Outputs to WhiteCrow**

Journal-Yuga should return outputs as structured publication-facing suggestions:

`venue_adaptation_patch_queue` — proposed changes organized as patch candidates rather than automatic rewrite.

`reframe_plan` — deeper article-variant or disciplinary translation plan.

`rewrite_plan` — section/block-level changes preserving or explicitly modifying protected core.

`citation_plan` — citation bridge tasks and reference verification tasks.

`risk_report` — publication risks, including field-core loss risk.

`submission_pack_tasks` — metadata, statements, files, checklist items that must be prepared.

`article_variant_suggestions` — possible sibling manuscripts for different publication regimes or disciplines.

`venue_memory_update` — post-submission knowledge that may affect future trajectories.

`external_doc_actions` — comments, suggested edits, tasks or structured blocks to send to Google Docs/DOCX bridge.

### **14.3. Protected Core Contract**

ProtectedCore is the most important WhiteCrow-to-Journal-Yuga concept. Journal-Yuga may suggest changes that affect protected core, but must never silently apply them or present them as mere style edits.

ProtectedCore may include:

central thesis;  
object of inquiry;  
key distinction;  
methodological stance;  
philosophical commitments;  
authorial voice;  
critical target;  
conceptual vocabulary;  
degree of speculation;  
relation to field;  
non-negotiable claims;  
ethical/political commitments;  
do-not-flatten constraints.

Any RewritePlan or ReframePlan must mark each change with one of:

`core_preserving`;  
`core_touching`;  
`core_transforming`;  
`core_destroying_risk`;  
`unknown_core_impact`.

Changes marked `core_touching`, `core_transforming` or `core_destroying_risk` require explicit user acceptance and must be visible in UI.

### **14.4. WhiteCrow Patch Queue Rules**

Journal-Yuga should not directly overwrite manuscript text. It should create patch candidates.

Patch candidate fields:

patch\_id;  
source\_plan\_id;  
target\_document\_ref;  
target\_block\_or\_section;  
change\_summary;  
change\_type;  
reason;  
evidence\_refs;  
related\_mismatch\_id;  
field\_core\_impact;  
estimated\_effort;  
status;  
user\_decision;  
created\_at.

Status values:

proposed;  
needs\_user\_review;  
accepted;  
rejected;  
modified;  
sent\_to\_external\_doc;  
applied;  
archived.

WhiteCrow remains responsible for actual manuscript evolution. Journal-Yuga supplies publication-facing pressure and adaptation logic.

### **14.5. ArticleVariant and Sibling Manuscripts**

When adaptation to a venue would require deep reframe, Journal-Yuga should not pretend it is a normal rewrite. It should propose ArticleVariant or sibling manuscript.

Example distinctions:

same manuscript, light venue adaptation;  
same article, major genre adaptation;  
same field, new article variant;  
same field, different discipline;  
same field, different language;  
same field, different publication regime;  
different field reduction entirely.

WhiteCrow must receive this as trajectory information, not as simple edit instruction.

## **15\. Journal-Yuga Internal Contract**

Journal-Yuga itself must be internally divided into services or modules that correspond to domain operations. Implementation details may vary, but the target behavior must preserve these boundaries.

### **15.1. Article Modeling Service**

Inputs:

Litops sources;  
WhiteCrow field/manuscript refs;  
user abstract/draft;  
bibliography;  
user scenario notes.

Outputs:

ArticleModel;  
ManuscriptModel;  
protected core extraction;  
unknowns;  
questions for user.

Responsibilities:

extract article structure;  
detect genre, discipline, method, novelty mode;  
separate text from article model;  
mark missing information;  
avoid overconfident modeling from abstract only.

### **15.2. Venue Profiling Service**

Inputs:

venue name or URL;  
Litops sources;  
API metadata;  
journal pages;  
corpus items;  
user notes.

Outputs:

VenueModel;  
JournalModel;  
PublicationRegimeModel;  
PolicySnapshot;  
PublishedArticleCorpus;  
CitationExpectationProfile;  
unknowns.

Responsibilities:

resolve canonical venue;  
collect official sources;  
extract formal and informal layers;  
mark publisher/vendor claims;  
distinguish journal, section, issue, topic and regime;  
avoid treating guidelines as entire venue.

### **15.3. Submission Scenario Service**

Inputs:

user answers;  
project defaults;  
WhiteCrow constraints;  
deadline and target requirements.

Outputs:

SubmissionScenario;  
missing questions;  
risk tolerance;  
rewrite/reframe boundaries.

Responsibilities:

ask only necessary questions;  
store user constraints;  
separate user goals from journal facts;  
make fit scenario-sensitive.

### **15.4. Fit Assessment Service**

Inputs:

ArticleModel;  
VenueModel;  
PublicationRegimeModel;  
SubmissionScenario;  
EvidenceItems.

Outputs:

FitAssessment;  
MismatchMap;  
unknowns;  
fit report.

Responsibilities:

compare multi-axis;  
avoid single score;  
show evidence;  
mark unknowns;  
distinguish light/deep assessment;  
produce actionable mismatch map.

### **15.5. Adaptation Planning Service**

Inputs:

MismatchMap;  
ArticleModel;  
ManuscriptModel;  
ProtectedCore;  
SubmissionScenario.

Outputs:

RewritePlan;  
ReframePlan;  
WhiteCrow patch candidates;  
field-core risk.

Responsibilities:

propose changes;  
classify core impact;  
separate rewrite from reframe;  
avoid automatic destructive adaptation;  
support user acceptance.

### **15.6. Citation Ecology Service**

Inputs:

ArticleModel bibliography;  
CitationExpectationProfile;  
OpenAlex/Crossref/OpenCitations data;  
PublishedArticleCorpus.

Outputs:

CitationPlan;  
reference verification report;  
citation risk flags;  
search tasks.

Responsibilities:

identify citation bridges;  
verify references;  
avoid fake references;  
avoid citation padding;  
mark pending references;  
support disciplinary translation.

### **15.7. Compliance and Risk Service**

Inputs:

VenueModel;  
PublicationRegimeModel;  
ArticleModel;  
SubmissionScenario;  
policy sources.

Outputs:

RiskReport;  
ComplianceChecklist;  
SubmissionPack readiness flags.

Responsibilities:

select relevant checks;  
extract missing requirements;  
flag blocking issues;  
separate legal/ethical risks from ordinary advice;  
mark unknown policy areas.

### **15.8. Submission Pack Service**

Inputs:

ManuscriptModel;  
ComplianceChecklist;  
SubmissionScenario;  
VenueModel;  
RiskReport.

Outputs:

SubmissionPack;  
cover letter skeleton;  
metadata table;  
portal field mapping;  
missing items.

Responsibilities:

turn advice into operational submission object;  
not automate final submission in MVP;  
support export to external documents.

### **15.9. Review Loop Service**

Inputs:

ReviewOutcome;  
previous FitAssessment;  
SubmissionPack;  
review letters.

Outputs:

RevisionPlan;  
RebuttalOutline;  
VenueMemory update;  
future risk updates.

Responsibilities:

classify review comments;  
separate fixable issues from fatal mismatch;  
support response planning;  
learn from outcome without overgeneralizing.

### **15.10. Evidence Auditor**

Inputs:

all outputs.

Outputs:

evidence coverage report;  
missing source warnings;  
claim status validation;  
quality gate status.

Responsibilities:

ensure every strong claim has evidence;  
prevent tacit signals as facts;  
mark stale sources;  
detect unsupported recommendations;  
block final outputs if evidence below threshold.

## **16\. External Boundary and Submission Systems**

Journal-Yuga must model downstream submission systems without trying to control them prematurely. The system may prepare data and files for OJS, Editorial Manager, ScholarOne, publisher portals, email submission or Google Docs workflows, but MVP should not submit automatically.

External boundary objects:

ExternalDocRef;  
SubmissionPortalProfile;  
PortalFieldMapping;  
ExportPackage;  
ManualSubmissionChecklist.

### **16.1. ExternalDocRef**

Fields:

external\_doc\_id;  
doc\_type;  
url\_or\_path;  
owner;  
permissions\_status;  
linked\_manuscript\_id;  
last\_synced\_at;  
sync\_status;  
notes.

Doc types:

google\_doc;  
docx;  
pdf;  
markdown;  
latex;  
submission\_portal\_draft;  
email\_draft.

### **16.2. SubmissionPortalProfile**

Fields:

portal\_profile\_id;  
venue\_model\_id;  
portal\_type;  
required\_fields;  
required\_files;  
step\_sequence;  
metadata\_requirements;  
declaration\_requirements;  
reviewer\_suggestion\_requirements;  
known\_limitations;  
source\_refs.

Portal types:

OJS;  
Editorial\_Manager;  
ScholarOne;  
publisher\_custom;  
email\_submission;  
unknown.

MVP: model portal profile only when source is available; otherwise unknown.

### **16.3. PortalFieldMapping**

Fields:

mapping\_id;  
submission\_pack\_id;  
portal\_profile\_id;  
field\_mappings;  
missing\_fields;  
manual\_actions;  
export\_status.

This turns SubmissionPack into operational object.

## **17\. Registry and Storage Contract**

Journal-Yuga should add its own registries but keep links to Litops canonical storage.

Recommended registry files or tables:

journal\_yuga\_article\_models;  
journal\_yuga\_manuscripts;  
journal\_yuga\_field\_refs;  
journal\_yuga\_article\_variants;  
journal\_yuga\_venue\_models;  
journal\_yuga\_journal\_models;  
journal\_yuga\_publication\_regimes;  
journal\_yuga\_editorial\_profiles;  
journal\_yuga\_article\_corpora;  
journal\_yuga\_citation\_profiles;  
journal\_yuga\_tacit\_signals;  
journal\_yuga\_submission\_scenarios;  
journal\_yuga\_fit\_assessments;  
journal\_yuga\_mismatch\_maps;  
journal\_yuga\_rewrite\_plans;  
journal\_yuga\_reframe\_plans;  
journal\_yuga\_citation\_plans;  
journal\_yuga\_risk\_reports;  
journal\_yuga\_compliance\_checklists;  
journal\_yuga\_submission\_packs;  
journal\_yuga\_review\_outcomes;  
journal\_yuga\_revision\_plans;  
journal\_yuga\_venue\_memory;  
journal\_yuga\_evidence\_items;  
journal\_yuga\_operation\_traces.

Each registry record must include:

id;  
type;  
created\_at;  
updated\_at;  
version;  
source\_refs;  
context\_pack\_refs;  
evidence\_status;  
lifecycle\_status;  
project\_id or workspace\_id;  
user\_id where appropriate;  
privacy/sensitivity level where appropriate.

Storage rule:

Raw files stay in Litops RAW or equivalent source storage.  
Dirty intake stays in INBOX until processed.  
Human-readable projections go to Vault.  
Journal-Yuga structured records go to registry/database.  
External docs stay external but get references.  
Generated artifacts may become Litops Artifacts and Vault cards.

## **18\. Vault Projection Contract**

Journal-Yuga should create human-readable Vault cards for major objects. Vault cards are not canonical evidence, but navigational surfaces.

Cards should exist for:

ArticleModel;  
VenueModel;  
PublicationRegimeModel;  
FitAssessment;  
MismatchMap;  
RewritePlan;  
CitationPlan;  
RiskReport;  
ComplianceChecklist;  
SubmissionPack;  
ReviewOutcome;  
VenueMemory.

Each card should include:

frontmatter with ids and refs;  
short summary;  
status;  
source/context links;  
unknowns;  
warnings;  
last updated;  
related objects;  
next actions.

Vault cards should make it possible for a human to browse Journal-Yuga work without opening raw registry JSON.

## **19\. Operation Trace Contract**

Every significant Journal-Yuga operation must produce trace.

Operation trace fields:

operation\_id;  
operation\_type;  
started\_at;  
ended\_at;  
user\_or\_agent;  
inputs;  
sources\_accessed;  
context\_packs\_used;  
adapters\_called;  
LLM\_prompts\_used;  
LLM\_outputs;  
entities\_created;  
entities\_updated;  
warnings;  
errors;  
quality\_gate\_status;  
user\_decisions;  
cost\_estimate;  
token\_estimate where available.

Operation types:

article\_model\_create;  
venue\_profile\_create;  
venue\_context\_pack\_build;  
fit\_assessment\_create;  
mismatch\_map\_create;  
rewrite\_plan\_create;  
citation\_plan\_create;  
risk\_report\_create;  
submission\_pack\_create;  
review\_outcome\_ingest;  
revision\_plan\_create;  
venue\_memory\_update.

Trace is required for debugging, reproducibility and quality control.

## **20\. User Decision and Acceptance Contract**

Journal-Yuga must preserve user agency. It should not silently transform manuscript, protected core or submission strategy.

Actions requiring explicit user acceptance:

deep reframe;  
field-core-touching rewrite;  
citation additions that change theoretical positioning;  
change of target discipline;  
change of publication regime;  
submission pack marked ready;  
cover letter finalization;  
response-to-reviewer strategy;  
use of tacit signal in major decision;  
fallback to lower-status venue;  
translation into another language/register.

User decisions should be logged:

decision\_id;  
related\_entity\_id;  
decision\_type;  
accepted/rejected/modified/deferred;  
user\_note;  
timestamp;  
effect.

This is especially important for WhiteCrow integration: accepted decisions may enter PatchQueue; rejected decisions should remain as history but not be applied.

## **21\. Integration Failure Modes**

Journal-Yuga must handle failures explicitly.

### **21.1. Missing Litops Source**

If an output depends on external material not registered as Source, system should either register it or mark output as unsupported. It must not proceed silently.

### **21.2. Missing WhiteCrow ProtectedCore**

If protected core is absent, system should ask user or mark field-core risk as unknown. It should not assume that any rewrite is safe.

### **21.3. Inaccessible Venue Source**

If journal pages or APIs are inaccessible, VenueModel should mark fields as INACCESSIBLE or UNKNOWN, and FitAssessment should be preliminary.

### **21.4. Conflicting Sources**

If official page, API metadata and user note conflict, system should preserve conflict. It should not choose silently unless rule is explicit.

### **21.5. Stale Evidence**

If source snapshot is old, system should warn and optionally refresh.

### **21.6. Thin Article Input**

If only title or abstract is provided, ArticleModel should be preliminary. System must not provide deep rewrite or submission pack.

### **21.7. Overbroad Venue Pool**

If pool is too broad, system should switch to light profile mode and ask user to narrow.

### **21.8. No Evidence for Tacit Claim**

Tacit signals may be stored, but not used as fact. If they affect recommendation, UI must show this.

## **22\. Minimum Integration MVP**

The first integration MVP should support this path:

User provides one manuscript or abstract and one target venue URL/name.

Litops registers article input as Source.

Journal-Yuga creates preliminary ArticleModel.

Journal-Yuga creates or requests venue\_context\_pack from target venue sources.

Journal-Yuga creates light VenueModel.

Journal-Yuga asks or records minimal SubmissionScenario.

Journal-Yuga produces FitAssessment, MismatchMap, RewritePlan, CitationPlan stub, RiskReport and ComplianceChecklist.

Journal-Yuga writes human-readable artifacts to Vault.

Journal-Yuga stores structured records in its registry.

Journal-Yuga logs operation trace.

If WhiteCrow input exists, Journal-Yuga maps RewritePlan into patch candidates. If not, it outputs standalone report.

If submission pack is requested, Journal-Yuga creates draft SubmissionPack with missing items and not-ready status.

MVP does not require:

automatic journal pool discovery;  
deep corpus mining;  
external portal automation;  
reviewer simulation;  
paid bibliometric APIs;  
automatic final rewrite.

## **23\. Wave 3 Closure**

This wave defines integration contracts. The central rule is that Journal-Yuga must not own everything. Litops owns source/provenance/context memory. WhiteCrow owns field/manuscript evolution. Journal-Yuga owns publication-facing models and operations. External systems remain external execution surfaces. Correct integration means every claim, plan and recommendation can be traced back to sources, user decisions and domain objects.

The next wave should define data adapters and source acquisition: how Journal-Yuga collects venue pages, APIs, article metadata, corpus items, citation data, guidelines, policies, CFPs and user-provided packages; which adapters are MVP, which are later, and how every adapter produces EvidenceItems and SourceSnapshots rather than ungrounded facts.

# **JOURNAL\_YUGA\_TECHNICAL\_SPEC\_FOR\_CLAUDE\_v0\_1**

## **Волна 4\. Data adapters, source acquisition, evidence extraction, freshness and staleness**

## **24\. Purpose of the Data Adapter Layer**

Data adapter layer отвечает за то, чтобы Journal-Yuga не строил ArticleModel, VenueModel, FitAssessment, CitationPlan, RiskReport and SubmissionPack из воздуха. Любое утверждение о журнале, публикационном режиме, статье, корпусе, citation ecology, policy, submission requirement or review context должно быть связано с источником, snapshot, extraction result and evidence status.

Data adapter layer не должен быть “набором API-клиентов”. Его задача шире: получать внешние данные, регистрировать их через Litops Source, создавать SourceSnapshot, извлекать EvidenceItems, маркировать статус извлечения, фиксировать freshness/staleness, сохранять ошибки, не заменять недоступное догадками, передавать доменным сервисам только доказательно размеченные данные.

Journal-Yuga должен поддерживать разные классы источников:

официальные страницы журналов и издателей;  
author guidelines;  
aims and scope;  
editorial board pages;  
submission instruction pages;  
policy pages;  
issue pages;  
special issue / CFP / research topic pages;  
published article pages;  
PDF full texts;  
DOI metadata;  
bibliographic and citation APIs;  
open journal directories;  
reporting and ethics guidelines;  
user-uploaded article packs;  
review letters;  
user tacit notes;  
paid or manually exported bibliometric data.

Все эти источники должны входить в систему не как “текст для LLM”, а как source-acquisition event, после которого появляются Source, SourceSnapshot, EvidenceItem and possibly structured domain objects.

## **25\. Adapter Output Contract**

Каждый adapter обязан возвращать не свободный summary, а стандартизированный результат. Даже если техническая реализация сначала будет простой, контракт должен быть одинаковым.

### **25.1. AdapterResult**

Общие поля:

adapter\_result\_id;  
adapter\_name;  
adapter\_version;  
operation\_id;  
input;  
started\_at;  
finished\_at;  
status;  
source\_ids\_created;  
snapshot\_ids\_created;  
evidence\_items\_created;  
structured\_records\_created;  
errors;  
warnings;  
rate\_limit\_info;  
cost\_info;  
raw\_response\_ref;  
parser\_used;  
confidence;  
notes.

`status`:

success;  
partial\_success;  
not\_found;  
inaccessible;  
blocked;  
rate\_limited;  
parse\_failed;  
auth\_required;  
paid\_required;  
unsupported\_format;  
error.

AdapterResult must never silently fail. If a page was found but not parsed, result is `parse_failed` or `partial_success`. If a source requires subscription, result is `paid_required`. If safe-open or network policy blocks access, result is `blocked` or `inaccessible`.

### **25.2. SourceSnapshot Creation**

Every successful or partially successful acquisition should create SourceSnapshot.

Minimum fields:

snapshot\_id;  
source\_id;  
adapter\_result\_id;  
url\_or\_identifier;  
retrieved\_at;  
content\_type;  
content\_hash if possible;  
raw\_ref;  
text\_ref;  
structured\_ref;  
extraction\_status;  
parser\_used;  
staleness\_policy;  
errors;  
warnings.

No VenueModel field should be treated as stable unless it can be traced to snapshot or user-provided evidence.

### **25.3. EvidenceItem Creation**

Adapters should create EvidenceItems for extracted claims.

EvidenceItem examples:

“journal page states article types include Research Article and Review”;  
“author guidelines state abstract limit is 250 words”;  
“policy page states data availability statement is required”;  
“Crossref metadata resolves DOI X to title/authors/year”;  
“OpenCitations returns references for DOI X”;  
“corpus snapshot includes 37 articles from 2023–2026”;  
“PDF parser extracted bibliography from manuscript”;  
“CFP page lists submission deadline”;  
“editorial board page lists editor affiliations.”

Every EvidenceItem must contain locator or source pointer. If exact quote extraction is impossible in MVP, EvidenceItem must still link to source and section label.

## **26\. Adapter Classes**

Journal-Yuga should distinguish adapter classes because they produce different evidence status and staleness rules.

### **26.1. Manual URL Snapshot Adapter**

This is the most important MVP adapter. It accepts one URL and registers the page as source/snapshot.

Inputs:

url;  
source\_role;  
project\_id;  
related\_venue\_id optional;  
related\_article\_id optional;  
user\_note optional.

Outputs:

Litops Source;  
SourceSnapshot;  
raw/html/text extraction if possible;  
EvidenceItems for title, page type, visible headings, key extracted claims;  
extraction warnings.

Supported source roles:

venue\_homepage;  
aims\_scope;  
author\_guidelines;  
editorial\_board;  
submission\_info;  
policy\_page;  
issue\_page;  
special\_issue\_cfp;  
research\_topic;  
published\_article;  
compliance\_guideline;  
unknown\_web\_source.

MVP requirements:

fetch page;  
store source;  
extract title;  
extract visible text where possible;  
classify source role manually or heuristically;  
create snapshot;  
mark inaccessible or parse\_failed explicitly.

Full version:

HTML cleaner;  
screenshot capture;  
DOM locator;  
structured extraction;  
change detection;  
diff between snapshots.

This adapter exists because many journal properties are visible only on publisher pages, not in APIs. It also prevents premature dependence on paid or closed databases.

### **26.2. File Intake / PDF Adapter**

This adapter handles user-uploaded article PDFs, manuscript PDFs, review letters, downloaded journal articles and zipped article packs.

Inputs:

file source\_id;  
file type;  
source role;  
corpus selection metadata;  
related article/venue/context.

Outputs:

SourceSnapshot;  
text extraction;  
metadata extraction;  
bibliography extraction if possible;  
section extraction if possible;  
EvidenceItems;  
CorpusItem records if article belongs to PublishedArticleCorpus.

MVP:

accept PDF/DOCX/MD/TXT already registered by Litops;  
extract text if possible;  
store extraction status;  
identify title/abstract/sections/bibliography heuristically;  
mark failure explicitly.

Full:

GROBID for scholarly PDFs;  
CERMINE as alternative PDF parser;  
AnyStyle / citation-js for references;  
S2ORC doc2json style structured extraction where appropriate;  
OCR only as last resort, not default.

Risk:

PDF extraction can be partial or wrong. Every extracted section and reference must have extraction confidence.

### **26.3. OpenAlex Adapter**

OpenAlex should be a primary open metadata adapter.

Use cases:

resolve journal/source by title, ISSN or URL;  
find works by venue/source;  
find works by concept/topic/author;  
collect recent article metadata;  
support venue corpus building;  
support author/institution/topic metadata;  
support initial shortlist discovery;  
support citation and reference metadata where available.

Inputs:

journal title;  
ISSN;  
DOI;  
work title;  
author;  
topic;  
date range;  
source id;  
search query.

Outputs:

api\_metadata\_snapshot;  
Venue metadata candidates;  
PublishedArticleCorpus metadata items;  
Work metadata;  
author/institution/topic metadata;  
EvidenceItems;  
uncertainty notes.

Evidence status:

OpenAlex fields are metadata observations from external database, not official journal claims. Mark as `FACT_FROM_SOURCE` with source `OpenAlex metadata`, or `METADATA_OBSERVATION` if implemented.

MVP:

resolve venue/source;  
retrieve works for a venue;  
store metadata snapshot;  
support small recent corpus.

Full:

advanced filters;  
pagination;  
topic clustering;  
citation/referenced works integration;  
source disambiguation;  
cache and refresh policy.

Risks:

metadata may be incomplete;  
venue/source matching can be ambiguous;  
not all humanities journals/articles covered equally.

### **26.4. Crossref Adapter**

Crossref adapter is mandatory for DOI and bibliographic verification.

Use cases:

resolve DOI to title/authors/year/journal;  
verify references;  
retrieve article metadata;  
retrieve journal/publisher metadata;  
detect malformed or fake DOI claims;  
support CitationPlan and SubmissionPack.

Inputs:

DOI;  
reference string;  
article title;  
ISSN;  
journal title.

Outputs:

metadata snapshot;  
ReferenceVerificationResult;  
EvidenceItems;  
warnings for unresolved or ambiguous references.

MVP:

DOI lookup;  
reference title/DOI matching;  
basic metadata extraction.

Full:

batch reference verification;  
fuzzy matching;  
bibliography normalization;  
Crossref relations;  
publisher metadata enrichment.

Risks:

Crossref coverage is incomplete;  
not all references have DOI;  
humanities references may be books/chapters not well covered;  
unresolved does not mean fake.

### **26.5. OpenCitations Adapter**

OpenCitations should be used for citation ecology where available.

Use cases:

retrieve citations/references for DOI;  
support reference and citation graph;  
support venue citation ecology;  
identify citation patterns;  
estimate reference/citation density;  
support self-citation and venue-citation signals where exposed;  
support CitationExpectationProfile.

Inputs:

DOI;  
venue identifier where available;  
reference/citation request;  
corpus item list.

Outputs:

citation metadata snapshot;  
reference list;  
citation list;  
venue-level citation observations;  
EvidenceItems;  
CoverageWarnings.

MVP:

DOI references/citations for known DOI items;  
attach citation observations to corpus items.

Full:

venue-level aggregation;  
citation graph analysis;  
reference age distribution;  
self-citation and venue citation patterns;  
integration with OpenAlex/Crossref.

Risks:

coverage gaps;  
DOI-dependent;  
not a complete citation database;  
must not overclaim absent citations.

### **26.6. DOAJ Adapter**

DOAJ adapter is useful for open access journal metadata.

Use cases:

verify open access journal presence;  
retrieve OA metadata;  
APC information where available;  
journal subject categories;  
license;  
publisher;  
country;  
quality signals.

Inputs:

journal title;  
ISSN;  
publisher;  
subject.

Outputs:

DOAJ metadata snapshot;  
Venue metadata enrichment;  
EvidenceItems;  
OA status notes.

MVP:

optional, build after OpenAlex/Crossref.

Full:

integrate into VenueProfile and RiskReport.

Risks:

presence/absence in DOAJ is not universal quality judgment;  
absence is not evidence of predatory status.

### **26.7. Sherpa / Policy Adapter**

Sherpa-like policy adapter should support open access, self-archiving, funder and publisher policy checks.

Use cases:

OA policy;  
archiving;  
preprint/postprint rules;  
funder compliance;  
license;  
rights;  
publisher policy.

Inputs:

journal title;  
ISSN;  
publisher;  
DOI.

Outputs:

PolicySnapshot;  
ComplianceChecklist items;  
RiskReport items;  
EvidenceItems.

MVP:

stub/manual source role: policy\_page.

Full:

API adapter if accessible.

Risks:

policies change;  
needs freshness and staleness;  
paid/registration restrictions possible.

### **26.8. Semantic Scholar Adapter**

Semantic Scholar is optional but valuable for article graph, abstracts, embeddings-related metadata and citation contexts where available.

Use cases:

retrieve paper metadata;  
references/citations;  
abstracts;  
fields of study;  
recommend similar papers;  
support citation bridge discovery.

MVP:

not required.

Full:

use for CitationPlan and corpus enrichment.

Risks:

API limits;  
coverage differences;  
not a source of journal formal requirements.

### **26.9. Unpaywall Adapter**

Unpaywall can help find open full-text locations.

Use cases:

find OA PDFs;  
support corpus acquisition;  
link article metadata to full text;  
support source acquisition.

MVP:

optional.

Full:

article corpus collector.

Risks:

license constraints;  
PDF availability does not imply permission for arbitrary processing beyond allowed terms.

### **26.10. ISSN / Serial Identity Adapter**

ISSN-related sources can help disambiguate journals.

Use cases:

verify serial identity;  
resolve print/electronic ISSN;  
distinguish similar journal titles;  
support VenueModel canonicalization.

MVP:

manual ISSN fields and OpenAlex/Crossref metadata.

Full:

ISSN Portal or equivalent paid/manual adapter.

Risks:

paid access;  
not required for MVP.

### **26.11. Scopus / Web of Science / JCR / SJR Adapter**

These are high-value but not MVP dependencies.

Use cases:

quartile;  
impact factor;  
indexing;  
citation metrics;  
journal categories;  
rankings;  
bibliometric validation.

MVP:

manual user-provided snapshots only; mark as source.

Full:

paid/export adapters if access exists.

Risks:

paid/closed access;  
licensing;  
regional access issues;  
data freshness;  
must not fabricate quartiles.

Rule:

If Scopus/WoS/JCR data is unavailable, system must mark indexing/quartile fields as UNKNOWN\_NOT\_VERIFIED, not infer from memory.

### **26.12. Publisher Page Adapter**

Publisher pages are necessary because many journal-specific facts live outside APIs.

Supported page types:

journal homepage;  
aims and scope;  
author guidelines;  
article types;  
submission instructions;  
editorial board;  
policies;  
OA/APC;  
special issue / research topic;  
issue pages;  
article pages.

MVP:

manual URL snapshot and extraction.

Full:

publisher-specific extractors for Wiley, Taylor & Francis, Springer Nature, Elsevier, SAGE, Frontiers, MDPI, Emerald, IEEE, ACM, etc.

Risks:

JavaScript-heavy pages;  
cookies;  
robots/terms;  
page redesign;  
blocked access;  
marketing claims.

Rule:

Publisher pages produce both facts and vendor claims. The adapter must distinguish visible formal requirement from promotional statement.

### **26.13. CFP / Special Issue / Association Source Adapter**

CFP and special issue sources are important but not MVP core.

Use cases:

discover publication opportunities;  
support special issue fit;  
track deadlines;  
identify guest editors;  
identify theme-specific article forms;  
support humanities/STS/AI ethics publication regimes.

Sources:

journal CFP pages;  
publisher special issue pages;  
PhilEvents;  
H-Net;  
4S/STS association pages;  
conference websites;  
society pages;  
mailing list archives;  
Telegram channels, later backlog.

MVP:

manual URL snapshot.

Full:

watchers/crawlers with cadence.

Risks:

deadlines expire;  
CFP pages disappear;  
must store retrieved\_at and expiry.

### **26.14. PhilPapers / PhilEvents / Humanities Adapters**

Humanities and philosophy require special handling because ordinary journal finders are often weak for these fields.

Use cases:

philosophy journal discovery;  
CFP discovery;  
category mapping;  
author/topic context;  
special issues;  
conference and society publication paths.

MVP:

manual source snapshots and later adapter planning.

Full:

PhilPapers/PhilEvents structured integration if allowed/available;  
H-Net and association pages;  
digital humanities directories;  
STS networks.

Risks:

APIs may be limited;  
site terms;  
coverage differs by discipline;  
publication logic is often community-driven, not metric-driven.

## **27\. Source Acquisition Pipelines**

Data adapters become useful only when organized into pipelines. Journal-Yuga should implement several source acquisition pipelines.

### **27.1. One Target Venue Acquisition**

Input:

venue name or URL;  
optional manuscript/article\_model;  
optional user notes.

Steps:

resolve canonical venue candidate;  
register provided URL as source;  
fetch homepage;  
find or ask for aims/scope;  
find or ask for author guidelines;  
find or ask for editorial board;  
find or ask for submission/policy pages;  
retrieve OpenAlex/Crossref metadata if possible;  
build light VenueModel;  
create venue\_context\_pack;  
mark unknowns;  
return missing source list.

MVP output:

light VenueModel;  
venue\_context\_pack;  
EvidenceItems;  
unknown fields;  
source acquisition report.

Full output:

deep VenueModel;  
PublishedArticleCorpus;  
CitationExpectationProfile;  
PolicySnapshot;  
PublicationRegimeModel.

### **27.2. Venue Corpus Acquisition**

Input:

venue\_model\_id;  
selection\_strategy;  
time\_range;  
article\_count target;  
source preferences.

Strategies:

recent articles;  
most cited;  
most read;  
section-specific;  
special issue-specific;  
user-uploaded;  
OpenAlex metadata;  
manual article URLs;  
mixed.

Steps:

collect article metadata;  
register article pages or PDFs as sources where possible;  
deduplicate by DOI/title;  
parse abstracts/PDFs if available;  
create CorpusItems;  
create PublishedArticleCorpus;  
record representativeness notes;  
generate basic patterns.

MVP:

small corpus, 5–10 articles or metadata-only, with warning.

Full:

20–50 articles;  
section-specific corpus;  
full-text parsing;  
pattern mining.

Rules:

Corpus size alone does not guarantee representativeness. Every corpus must have selection\_strategy and bias\_notes.

### **27.3. Article Input Acquisition**

Input:

user manuscript file, abstract, draft, URL, Litops source, WhiteCrow manuscript or field.

Steps:

register input source if not already registered;  
extract text;  
extract metadata;  
extract bibliography;  
extract sections;  
build ManuscriptModel;  
build preliminary ArticleModel;  
mark unknowns;  
ask scenario/protected core questions.

MVP:

plain text/markdown/DOCX/PDF where extraction works.

Full:

Google Docs bridge;  
paragraph/block mapping;  
citation anchors;  
version history.

### **27.4. Reference and Citation Acquisition**

Input:

bibliography, DOI list, corpus item list, ArticleModel.

Steps:

parse references;  
resolve DOI/metadata via Crossref/OpenAlex;  
retrieve references/citations via OpenCitations/Semantic Scholar where available;  
mark unresolved references;  
generate ReferenceVerificationResult;  
feed CitationPlan.

MVP:

verify DOI-bearing references and mark unresolved.

Full:

fuzzy reference resolution;  
book/chapter support;  
citation graph;  
venue-level citation ecology.

Rules:

Unresolved reference is not automatically fake. It is unresolved.

### **27.5. Policy and Compliance Acquisition**

Input:

VenueModel;  
article type;  
publication regime;  
policy URLs;  
guidelines;  
external guideline sources.

Steps:

collect policy pages;  
extract formal requirements;  
extract required statements;  
detect ethics/AI/data/authorship/COI/funding requirements;  
create ComplianceChecklist;  
create RiskReport policy items;  
mark unknowns.

MVP:

manual extraction from author guidelines and policy pages.

Full:

guideline-selection engine;  
EQUATOR/PRISMA/ICMJE/CRediT where relevant;  
publisher-specific policy templates.

### **27.6. CFP / Special Issue Acquisition**

Input:

CFP URL, special issue URL, research topic URL, association page, user note.

Steps:

register source;  
extract title/theme;  
deadline;  
editors;  
article types;  
scope;  
submission URL;  
requirements;  
PublicationRegimeModel;  
VenueModel/IssueModel linkage;  
staleness/expiry.

MVP:

manual URL snapshot and structured extraction.

Full:

scheduled watchers, alerts, Telegram intake, association sources, community pages.

## **28\. Freshness and Staleness Policy**

Journal-Yuga must not treat sources as timeless. Journal pages, policies, metrics, editorial boards, CFPs and article corpora change.

Each SourceSnapshot and EvidenceItem should have staleness policy.

Suggested freshness rules:

author guidelines: refresh every 3–6 months or before submission;  
policies: refresh before submission;  
editorial board: refresh every 6–12 months;  
metrics/indexing: refresh every 1–3 months if used for decision;  
CFP/special issue: refresh frequently until deadline, expire after deadline;  
article corpus: refresh every 3–6 months for active journals;  
API metadata: refresh based on use;  
user tacit notes: review after 6–12 months or after new outcome;  
review outcomes: do not expire, but scope stays specific.

Staleness statuses:

fresh;  
possibly\_stale;  
stale;  
expired;  
unknown\_freshness.

Outputs depending on stale evidence must show warnings.

SubmissionPack must force refresh for high-stakes fields before final ready status:

author guidelines;  
submission requirements;  
policies;  
deadlines;  
APC;  
AI disclosure;  
ethics/data requirements.

## **29\. Canonicalization and Deduplication**

Source acquisition must include canonicalization and deduplication.

### **29.1. Venue Canonicalization**

Venue names may be ambiguous. Journal-Yuga should resolve:

title;  
ISSN;  
publisher;  
URL;  
OpenAlex source;  
Crossref journal metadata;  
DOAJ record if available;  
user-provided identity.

If ambiguous, create multiple candidates and ask user or mark unresolved.

Never merge venues only by similar title.

### **29.2. Article Deduplication**

Article corpus items should be deduplicated by:

DOI;  
title normalized;  
authors/year;  
URL;  
content hash if full text.

Duplicate handling:

same article from multiple sources should become one CorpusItem with multiple source refs.

### **29.3. Reference Deduplication**

Bibliography references should be deduplicated by DOI where possible, otherwise normalized title/authors/year. Ambiguity must be preserved.

### **29.4. Source Snapshot Deduplication**

If same URL is fetched repeatedly, create new snapshot only when content hash changes or freshness policy requires new snapshot. Otherwise link existing snapshot.

## **30\. Source Acquisition Quality Gates**

Every source acquisition run should produce a quality report.

Minimum fields:

operation\_id;  
requested\_scope;  
sources\_found;  
sources\_opened;  
sources\_failed;  
evidence\_items\_created;  
unknown\_required\_fields;  
stale\_sources;  
conflicting\_evidence;  
adapter\_errors;  
coverage\_label.

Coverage labels:

insufficient;  
light\_profile\_ready;  
fit\_ready\_preliminary;  
deep\_profile\_ready;  
submission\_ready\_requires\_refresh.

### **30.1. One Venue Fit Gate**

Before creating evidence-backed FitAssessment for one venue, system should have at least:

ArticleModel source;  
Venue homepage or equivalent;  
aims/scope or scope source;  
author guidelines or explicit missing status;  
SubmissionScenario;  
at least one policy/submission source or unknown marker;  
provenance for every formal requirement used.

If missing, FitAssessment status is preliminary.

### **30.2. Deep Venue Profile Gate**

Before marking VenueModel deep\_profile\_ready:

official homepage;  
aims/scope;  
author guidelines;  
policy page or unknown;  
editorial board or unknown;  
recent article corpus;  
publication regime;  
citation expectation profile or unknown;  
staleness dates.

### **30.3. Submission Pack Gate**

Before `ready_for_manual_submission`:

fresh author guidelines;  
fresh submission requirements;  
required metadata present;  
required statements present or marked not applicable;  
references checked to required level;  
files listed;  
blocking risks resolved or user-accepted;  
manual submission caveat present.

## **31\. Adapter Priority Roadmap**

### **31.1. Build Now**

manual URL snapshot adapter;  
Litops Source integration;  
SourceSnapshot / EvidenceItem creation;  
file/PDF intake via existing extraction where available;  
basic GROBID integration or placeholder interface;  
OpenAlex adapter;  
Crossref adapter;  
OpenCitations adapter;  
basic author guidelines extractor;  
basic venue corpus metadata acquisition;  
basic reference verification.

These are required for the first meaningful MVP.

### **31.2. Build Soon**

DOAJ adapter;  
Sherpa/policy adapter;  
Semantic Scholar adapter;  
Unpaywall adapter;  
CFP/special issue manual extraction;  
journal page classifier;  
corpus pattern miner;  
reference parser alternatives AnyStyle/CERMINE/citation-js.

### **31.3. Build Later**

publisher-specific extractors;  
PhilPapers/PhilEvents adapters;  
H-Net/association CFP watchers;  
scheduled venue refresh;  
deep citation ecology analytics;  
Scopus/WoS/JCR paid snapshots;  
ISSN Portal adapter;  
Dimensions/Lens/Scite if available;  
submission portal profiles;  
external document sync.

### **31.4. Backlog**

Telegram channel CFP watchers;  
community/association crawlers;  
image integrity services;  
plagiarism services;  
AI-content detector services;  
automatic portal submission;  
editorial contact management;  
journal response time prediction;  
acceptance probability modeling.

## **32\. Adapter Risk Rules**

No adapter may silently convert unavailable data into negative findings.

If Scopus data unavailable: indexing \= UNKNOWN\_NOT\_VERIFIED.  
If editorial board page inaccessible: editorial\_board \= INACCESSIBLE.  
If no DOI found: DOI \= UNKNOWN\_NOT\_VERIFIED, not fake.  
If a service claims AI matching: VENDOR\_CLAIM.  
If corpus is small: corpus observation must include low representativeness warning.  
If user uploads article pack: selection strategy is user\_uploaded, not representative by default.  
If policy is stale: SubmissionPack cannot be ready without refresh or user override.  
If source conflicts: both claims preserved with CONFLICTING\_EVIDENCE.

## **33\. Adapter Outputs into Domain Objects**

Adapters should not write directly into final reports. They produce evidence and structured records.

Manual URL snapshot → SourceSnapshot \+ EvidenceItems.

OpenAlex → Venue metadata candidates \+ CorpusItems \+ EvidenceItems.

Crossref → ReferenceVerificationResult \+ Article metadata \+ EvidenceItems.

OpenCitations → CitationGraphSnapshot \+ CitationExpectationProfile inputs.

GROBID/CERMINE → ManuscriptModel/PDF extraction \+ bibliography extraction \+ CorpusItem text.

DOAJ/Sherpa → PolicySnapshot \+ ComplianceChecklist inputs.

CFP adapter → IssueModel/SpecialIssueModel/ResearchTopicModel.

PhilPapers/PhilEvents → Humanities venue/context candidates and CFP sources.

Domain services consume these outputs and create ArticleModel, VenueModel, FitAssessment etc.

## **34\. Wave 4 Closure**

This wave defines the data acquisition and adapter layer. The central principle is that Journal-Yuga cannot reason without sources. Adapters do not merely “fetch data”; they create traceable evidence. MVP must begin with manual URL snapshots, Litops Source integration, OpenAlex, Crossref, OpenCitations and scholarly document parsing. Paid and unstable sources are not blockers for MVP. The system should prefer explicit unknowns over false completeness.

The next wave should define the operational pipelines: one manuscript × one target venue, venue deep profile, journal pool discovery, reverse design for venue pool, submission pack generation, review/rebuttal loop and Q3/conference fallback.

# **JOURNAL\_YUGA\_TECHNICAL\_SPEC\_FOR\_CLAUDE\_v0\_1**

## **Волна 5\. Operational Pipelines: рабочие сценарии, переходы, артефакты, проверки и отказоустойчивость**

## **35\. Purpose of Operational Pipelines**

Operational pipelines описывают, как Journal-Yuga реально работает: как входной материал превращается в ArticleModel, как собирается VenueModel, как строится SubmissionScenario, как производится FitAssessment, как из него возникают MismatchMap, RewritePlan, CitationPlan, RiskReport, ComplianceChecklist, SubmissionPack и, при необходимости, WhiteCrow Patch Queue или VenueMemory update.

Пайплайн — это не UI-сценарий и не prompt. Это воспроизводимая последовательность операций над доменными объектами. UI может быть чатовым, web-based, Telegram-based или CLI/API-based, но внутри система должна проходить одни и те же доменные стадии. Если пользователь написал в Telegram “подбери журнал”, web UI загрузил DOCX, или WhiteCrow передал Field Text, Journal-Yuga всё равно должен создавать typed objects, evidence refs, operation trace and quality gates.

Каждый pipeline должен иметь:

pipeline\_id;  
pipeline\_type;  
entry mode;  
required inputs;  
optional inputs;  
created entities;  
updated entities;  
required sources;  
evidence threshold;  
user questions;  
quality gates;  
failure modes;  
outputs;  
handoff targets;  
logs and traces;  
MVP scope;  
future full scope.

Ни один pipeline не должен завершаться “LLM ответом” как единственным результатом. Текстовый ответ может быть пользовательским summary, но canonical result должен быть набором структурированных объектов и артефактов.

## **36\. Common Pipeline Envelope**

Все pipeline должны использовать общий operational envelope.

### **36.1. PipelineRun**

Поля:

pipeline\_run\_id;  
pipeline\_type;  
project\_id;  
user\_id;  
entry\_channel;  
started\_at;  
finished\_at;  
status;  
input\_refs;  
created\_entity\_ids;  
updated\_entity\_ids;  
source\_ids\_used;  
context\_pack\_ids\_used;  
adapters\_called;  
agent\_roles\_used;  
prompt\_family\_refs;  
quality\_gate\_results;  
user\_questions\_asked;  
user\_decisions\_recorded;  
warnings;  
errors;  
cost\_estimate;  
token\_estimate;  
next\_actions.

`entry_channel`:

web\_ui;  
telegram;  
cli;  
api;  
whitecrow;  
litops;  
scheduled\_job;  
manual\_admin;  
unknown.

`status`:

created;  
running;  
waiting\_for\_sources;  
waiting\_for\_user;  
partial\_success;  
completed;  
failed;  
cancelled;  
stale;  
superseded.

### **36.2. Pipeline Quality Gate**

Каждый pipeline должен иметь quality gate. Gate не должен быть декоративным. Он определяет, можно ли перейти к следующей стадии, нужно ли задать пользователю вопрос, нужно ли собрать дополнительные источники, можно ли выдавать evidence-backed output или только preliminary output.

Общий формат gate result:

gate\_id;  
gate\_name;  
pipeline\_run\_id;  
status;  
blocking\_issues;  
warnings;  
missing\_sources;  
unknown\_fields;  
stale\_sources;  
unsupported\_claims;  
required\_user\_decisions;  
recommendation.

`status`:

passed;  
passed\_with\_warnings;  
failed\_blocking;  
failed\_but\_preliminary\_output\_allowed;  
needs\_user\_input;  
needs\_source\_refresh;  
not\_applicable.

### **36.3. Pipeline Output Levels**

Каждый pipeline output должен иметь уровень зрелости.

`rough_note` — свободная заметка, не доменный результат.

`preliminary` — объект создан, но данных мало; выводы осторожные.

`light_profile` — достаточно для навигации, недостаточно для deep fit.

`evidence_backed` — есть источники, ContextPack, EvidenceItems, unknowns and confidence.

`submission_ready` — пройдены freshness and compliance gates.

`post_outcome` — обновлено после реального review/submission outcome.

MVP может производить `preliminary` and `light_profile`, но должен явно маркировать их. Нельзя выдавать preliminary как submission-ready.

### **36.4. Common User Question Model**

Journal-Yuga должен задавать вопросы не как разговорный бот, а как механизм закрытия недостающих полей.

Question fields:

question\_id;  
related\_entity\_id;  
related\_pipeline\_run\_id;  
question\_type;  
question\_text;  
why\_needed;  
blocking\_level;  
answer\_type;  
options;  
default\_if\_skipped;  
user\_answer;  
answered\_at;  
effect\_on\_entities.

Question types:

submission\_goal;  
target\_indexing;  
deadline;  
APC\_constraint;  
rewrite\_depth;  
reframe\_allowed;  
protected\_core;  
target\_language;  
article\_type;  
fallback\_acceptance;  
venue\_choice;  
source\_confirmation;  
tacit\_signal\_confirmation;  
risk\_acceptance.

Questions should be minimized. System should not interrogate user unnecessarily. But if a missing answer changes fit significantly, the question should be explicit.

## **37\. Pipeline 1: Direct Manuscript × One Target Venue**

This is the first core MVP pipeline. If this pipeline is not working, no journal pool, reverse design or submission pack can be trusted.

### **37.1. Purpose**

Given one manuscript/draft/abstract/article model and one target venue, determine whether the article can be submitted to that venue, what mismatches exist, what adaptation would be required, what citation/compliance/risk work is needed, and whether the system can produce a preliminary or evidence-backed SubmissionPack.

### **37.2. Entry Modes**

User may enter through:

upload manuscript \+ paste journal URL;  
paste abstract \+ journal name;  
select Litops source\_id \+ venue URL;  
select WhiteCrow manuscript \+ target venue;  
provide ArticleModel \+ VenueModel IDs;  
Telegram command with source and venue;  
CLI/API call.

### **37.3. Required Inputs**

At minimum:

article input: manuscript, draft, abstract, source\_id, ArticleModel or WhiteCrow manuscript ref;  
target venue input: journal/venue name, URL, VenueModel or venue source;  
SubmissionScenario minimal answers or defaults.

Hard minimum for preliminary output:

one article source;  
one venue identifier;  
at least minimal user goal.

Hard minimum for evidence-backed fit:

ArticleModel with source refs;  
VenueModel with homepage/scope or author guidelines;  
SubmissionScenario confirmed;  
EvidenceItems for key claims;  
ContextPack linking article and venue sources.

### **37.4. Optional Inputs**

bibliography file;  
prior article drafts;  
WhiteCrow field context;  
protected core;  
user notes about venue;  
review timeline expectations;  
target article type;  
special issue URL;  
previous submission outcome;  
corpus of articles from venue.

### **37.5. Step-by-Step Pipeline**

Step 1\. Normalize inputs.

System identifies whether article input is abstract, draft, full manuscript, WhiteCrow field, existing ArticleModel or mixed input. System identifies whether venue input is URL, journal name, ISSN, publisher page, existing VenueModel or user note.

Created or updated:

PipelineRun;  
input source refs;  
input normalization notes.

Failure mode:

If no article-like input exists, pipeline cannot proceed to fit. It may create venue profile only.

If no venue-like input exists, pipeline cannot proceed to one-target fit. It may create ArticleModel only.

Step 2\. Register or resolve sources through Litops.

If input files or URLs are not registered, system creates or requests Litops Source registration. If sources already exist, system links them. If URL cannot be fetched, create INACCESSIBLE source state.

Created:

SourceSnapshot;  
EvidenceItems for input availability;  
ContextPack skeleton.

Gate:

No unregistered external source should be used for evidence-backed output.

Step 3\. Build or update ManuscriptModel.

For full text or file input, system extracts title, abstract, sections, word count, bibliography presence, language and basic structure. If only abstract is present, ManuscriptModel is minimal and ArticleModel becomes preliminary.

Created:

ManuscriptModel.

Warnings:

abstract\_only;  
bibliography\_missing;  
section\_extraction\_failed;  
PDF\_parse\_low\_confidence;  
language\_unknown.

Step 4\. Build ArticleModel.

System extracts publication-facing structure: problem, object, question, core claims, argument, genre, method status, discipline, novelty mode, theoretical shoulders, current citation ecology, protected core if possible, unknowns.

If protected core is not available, system asks user one question:

“What must not be changed in this article even if a venue requires adaptation?”

If user skips, protected core remains UNKNOWN and field-core-risk checks are weaker.

Created:

ArticleModel;  
ArticleModel questions if needed.

Gate:

Deep RewritePlan cannot be generated without at least provisional protected core status.

Step 5\. Resolve target venue.

System canonicalizes venue name/URL. If multiple possible venues are found, asks user to confirm. If URL is a special issue or research topic, system should not collapse it into parent journal only; it should create IssueModel or ResearchTopicModel linked to JournalModel/VenueModel.

Created:

Venue candidate records;  
canonical venue decision;  
PublicationRegimeModel candidate.

Warnings:

ambiguous venue;  
publisher landing page only;  
special issue detected;  
conference proceedings detected;  
non-journal venue detected.

Step 6\. Build light VenueModel.

System fetches or uses sources for homepage, aims/scope, author guidelines, article types and submission information. If unavailable, unknowns are explicit. System creates light VenueModel and PublicationRegimeModel.

Created:

VenueModel;  
JournalModel if applicable;  
PublicationRegimeModel;  
Venue ContextPack.

Gate:

If no official venue source is available, output is preliminary only.

Step 7\. Build minimal SubmissionScenario.

System asks or infers from user:

goal;  
target indexing;  
deadline;  
APC tolerance;  
rewrite depth allowed;  
reframe allowed;  
target language;  
fallback allowed.

If user did not specify, defaults are marked unknown, not assumed.

Created:

SubmissionScenario.

Gate:

FitAssessment without SubmissionScenario is preliminary.

Step 8\. Perform fit assessment.

System compares ArticleModel, VenueModel, PublicationRegimeModel and SubmissionScenario across axes:

topic;  
discipline;  
genre;  
argument;  
method;  
citation ecology;  
novelty mode;  
language/register;  
formal compliance;  
author eligibility;  
publication regime;  
timeline;  
APC/policy;  
field-core preservation;  
strategic value.

Created:

FitAssessment.

Each axis must contain:

value;  
evidence refs;  
unknowns;  
confidence;  
notes.

Step 9\. Generate MismatchMap.

System translates weak fit axes into specific mismatches. Each mismatch must include article side, venue side, severity, evidence, possible action and field-core impact.

Created:

MismatchMap.

Step 10\. Generate RewritePlan and ReframePlan if needed.

If mismatches are form-level, create RewritePlan. If mismatches require changing object, discipline, genre, method, novelty or protected core, create ReframePlan or ArticleVariant suggestion.

Created:

RewritePlan;  
ReframePlan optional;  
WhiteCrow patch candidates optional.

Gate:

Any core-touching change requires user acceptance.

Step 11\. Generate CitationPlan.

System compares current citation ecology against venue/corpus expectations. In MVP this may be a stub with tasks rather than verified references.

Created:

CitationPlan.

MVP allowed outputs:

missing citation bridge categories;  
reference verification tasks;  
dangerous padding warnings;  
bibliography format concerns.

Full outputs:

verified reference suggestions;  
citation graph evidence;  
venue-specific citation ecology.

Step 12\. Generate RiskReport.

System identifies formal, policy, citation, field-core, timeline, APC, indexing, author eligibility, AI disclosure and review risks.

Created:

RiskReport.

Step 13\. Generate ComplianceChecklist.

System extracts requirements from author guidelines and publication regime. If requirements are unavailable, checklist marks unknowns. It should not hallucinate generic requirements as venue-specific.

Created:

ComplianceChecklist.

Step 14\. Generate optional SubmissionPack draft.

If user asks or if enough data exists, system creates a draft SubmissionPack with status not\_ready or needs\_user\_input. It should not mark ready unless fresh requirements and required fields are present.

Created:

SubmissionPack.

Step 15\. Write artifacts and projections.

System writes human-readable report and Vault cards:

ArticleModel card;  
VenueModel card;  
FitAssessment report;  
MismatchMap;  
RewritePlan;  
CitationPlan;  
RiskReport;  
ComplianceChecklist;  
SubmissionPack draft if any.

Step 16\. Record operation trace.

Every step, source, prompt, adapter call, output and user question is logged.

### **37.6. Outputs**

Mandatory outputs:

ArticleModel;  
VenueModel;  
SubmissionScenario;  
FitAssessment;  
MismatchMap;  
RiskReport;  
operation trace.

Conditional outputs:

RewritePlan;  
ReframePlan;  
CitationPlan;  
ComplianceChecklist;  
SubmissionPack;  
WhiteCrow patch candidates;  
Vault cards.

### **37.7. Quality Gates**

Preliminary fit allowed if:

article input exists;  
venue identifier exists;  
some source evidence exists;  
unknowns are explicit.

Evidence-backed fit requires:

ArticleModel confirmed or sufficiently sourced;  
VenueModel light profile with official sources;  
SubmissionScenario confirmed;  
evidence refs per fit axis;  
ContextPack created.

SubmissionPack draft requires:

ComplianceChecklist created;  
Venue requirements source present or explicitly unknown;  
ManuscriptModel present.

Ready-for-manual-submission requires:

fresh author guidelines;  
required metadata;  
required files list;  
required statements;  
reference verification level reached;  
blocking risks resolved or accepted.

### **37.8. MVP Scope**

MVP-1 implements this pipeline for one manuscript and one venue. It does not implement journal pool, automatic article corpus mining, final rewrite, reviewer simulation or automatic submission.

## **38\. Pipeline 2: Venue Deep Profile**

### **38.1. Purpose**

Venue Deep Profile builds a detailed model of one publication container without necessarily having a specific article. It is used when user asks “what is this journal/venue?”, “can we target this venue later?”, “profile this special issue”, “create venue memory”, or when Journal-Yuga needs evidence for later fit assessments.

### **38.2. Inputs**

venue name;  
venue URL;  
journal ISSN;  
publisher page;  
special issue URL;  
research topic URL;  
conference proceedings page;  
existing VenueModel;  
user notes;  
article corpus pack.

### **38.3. Pipeline Steps**

Step 1\. Resolve venue identity.

Identify whether target is journal, section, special issue, research topic, conference proceedings, open-review venue, mega-journal or other. If ambiguous, create candidates and ask user.

Step 2\. Create or update VenueModel skeleton.

Fill canonical name, publisher, official URLs, venue type, initial publication regime.

Step 3\. Acquire official sources.

Attempt to collect homepage, aims/scope, author guidelines, editorial board, submission information, policy pages, OA/APC, article type pages, issue pages, special issue pages.

Step 4\. Create SourceSnapshots and EvidenceItems.

Every page becomes source/snapshot/evidence. Missing pages become unknowns or inaccessible sources.

Step 5\. Extract formal requirements.

Extract article types, length, abstract, keywords, references, formatting, statements, file requirements, submission route, language, policies.

Step 6\. Build PolicySnapshot.

If policy pages exist, extract AI disclosure, data availability, ethics, COI, funding, authorship, copyright, preprint/self-archiving where available.

Step 7\. Build EditorialBoardProfile.

Extract visible editors, roles, affiliations and disciplinary signals. Mark as visible board data, not hidden preference.

Step 8\. Build PublicationRegimeModel.

Classify regime: classic journal, special issue, research topic, conference proceedings, mega-journal, reviewed preprint, open review, humanities symposium, edited volume, local/Q3 fallback etc.

Step 9\. Acquire or define article corpus.

Collect recent articles, most cited/read if available, section-specific articles or user-uploaded corpus. Record selection strategy and representativeness.

Step 10\. Generate PublishedArticlePatterns.

Mine patterns: article structures, abstract forms, method presence, citation density, theoretical anchors, length, novelty form, genre moves.

Step 11\. Generate CitationExpectationProfile.

Using corpus and citation metadata where possible, identify likely citation expectations. Mark as corpus observation and inference, not venue fact.

Step 12\. Create VenueProfile artifact.

Human-readable profile includes:

identity;  
scope;  
regime;  
article types;  
requirements;  
policies;  
corpus observations;  
citation ecology;  
editorial visible structure;  
metrics/indexing if verified;  
unknowns;  
risks;  
use cases;  
refresh dates.

### **38.4. Outputs**

VenueModel;  
JournalModel;  
PublicationRegimeModel;  
PolicySnapshot;  
EditorialBoardProfile;  
PublishedArticleCorpus;  
PublishedArticlePatterns;  
CitationExpectationProfile;  
VenueProfile artifact;  
VenueContextPack;  
Vault card.

### **38.5. Quality Levels**

Light profile:

homepage \+ scope/guidelines \+ basic metadata.

Deep profile:

official pages \+ policies \+ editorial board \+ article corpus \+ citation expectations \+ staleness policy.

Submission-ready venue profile:

fresh guidelines \+ fresh policies \+ fresh submission information \+ missing fields resolved.

### **38.6. MVP Scope**

MVP supports light profile. Deep profile with 20–50 articles comes later.

## **39\. Pipeline 3: Journal / Venue Pool Discovery**

### **39.1. Purpose**

Venue Pool Discovery finds a candidate set of venues for an ArticleModel or user idea. It should not pretend to perform deep fit for every candidate. It creates a shortlist and light profiles, then recommends which venues deserve deep profiling.

### **39.2. Inputs**

ArticleModel;  
abstract;  
draft;  
WhiteCrow field;  
SubmissionScenario;  
target disciplines;  
desired indexing;  
language;  
APC constraints;  
deadline;  
fallback rules;  
seed venues;  
excluded venues.

### **39.3. Pipeline Steps**

Step 1\. Build or receive ArticleModel.

If only abstract is available, mark pool discovery as preliminary.

Step 2\. Confirm SubmissionScenario.

Important fields: target indexing, prestige/speed tradeoff, discipline, language, APC, rewrite allowed, fallback allowed.

Step 3\. Generate search/discovery strategies.

Strategies:

metadata-based discovery via OpenAlex/Crossref;  
similar article venue discovery;  
user seed expansion;  
discipline/category browsing;  
special issue/CFP discovery;  
humanities community source discovery;  
manual candidates.

Step 4\. Create candidate venues.

For each candidate:

name;  
source;  
why found;  
evidence;  
candidate type;  
initial publication regime;  
confidence;  
unknowns.

Step 5\. Deduplicate and canonicalize.

Merge candidate duplicates by ISSN/title/publisher/URL where safe. Ambiguous candidates remain separate.

Step 6\. Create light VenueModels.

For each candidate, gather minimal metadata and source refs.

Step 7\. Apply filters.

Filters:

language;  
discipline;  
open access/APC;  
indexing;  
article type;  
country/region;  
publisher bias;  
deadline;  
special issue relevance;  
fallback status.

Step 8\. Produce preliminary Fit Screening.

Not full FitAssessment. Use ArticleModel and light VenueModel to classify:

promising;  
possible;  
needs deep profile;  
probably poor fit;  
unknown.

Step 9\. Recommend deep profile targets.

Select 3–5 venues for deep profile based on potential fit, strategic value, uncertainty and user scenario.

### **39.4. Outputs**

Venue candidate list;  
light VenueModels;  
VenuePoolContextPack;  
preliminary screening matrix;  
recommended deep profile list;  
unknowns and missing data list.

### **39.5. Prohibitions**

Do not rank venues with final claims if only light metadata exists.

Do not hide publisher-owned bias.

Do not infer indexing/quartile without verified source.

Do not claim acceptance probability.

Do not treat “not found” as “not suitable”.

### **39.6. MVP Scope**

MVP-2 supports small pool discovery after one-venue pipeline works.

## **40\. Pipeline 4: Reverse Design for Venue Pool**

### **40.1. Purpose**

Reverse Design answers a different question: not “where can this article go?”, but “what article should be built if we want to publish in this pool of venues or publication regime?”

This is important for WhiteCrow integration, where the starting object may be a field, not a manuscript.

### **40.2. Inputs**

venue pool;  
target discipline;  
WhiteCrow field;  
field text;  
source corpus;  
user goal;  
constraints;  
publication regime.

### **40.3. Pipeline Steps**

Step 1\. Profile venue pool lightly or deeply.

Identify shared expectations, differences and incompatible requirements.

Step 2\. Build FieldModelReference.

Receive or create field summary, central tensions, possible article trajectories, protected core.

Step 3\. Infer possible ArticleVariants.

For each venue cluster, propose candidate article form:

discipline;  
genre;  
question;  
object;  
theoretical shoulders;  
method status;  
citation ecology;  
language/register.

Step 4\. Compare variants to protected core.

Classify variants:

core-preserving;  
core-touching;  
core-transforming;  
too destructive.

Step 5\. Generate Article Design Map.

For each candidate variant:

title direction;  
abstract direction;  
section structure;  
citation bridges;  
needed sources;  
risks;  
venue candidates;  
effort.

Step 6\. Return to WhiteCrow.

Output should become article trajectory options, not direct manuscript rewrite.

### **40.4. Outputs**

ArticleVariant candidates;  
ReframePlan;  
VenueClusterProfile;  
CitationBridgeTasks;  
WhiteCrow trajectory suggestions;  
risk comparison.

### **40.5. MVP Scope**

Build later. Schema and conceptual support now.

## **41\. Pipeline 5: Submission Pack Generation**

### **41.1. Purpose**

SubmissionPack turns fit/adaptation/compliance work into operational readiness for manual submission. It is not a generic report. It models downstream gates.

### **41.2. Inputs**

ManuscriptModel;  
ArticleModel;  
VenueModel;  
PublicationRegimeModel;  
SubmissionScenario;  
ComplianceChecklist;  
RiskReport;  
CitationPlan;  
RewritePlan status.

### **41.3. Pipeline Steps**

Step 1\. Verify readiness prerequisites.

Check whether manuscript exists, target venue confirmed, guidelines fresh, scenario confirmed, blocking risks known, references checked to required level.

Step 2\. Build required submission inventory.

Collect:

main manuscript;  
title;  
abstract;  
keywords;  
authors;  
affiliations;  
ORCID;  
corresponding author;  
funding;  
COI;  
data availability;  
ethics;  
AI disclosure;  
CRediT;  
cover letter;  
figures/tables;  
supplementary files;  
permissions;  
reviewer suggestions if needed;  
opposed reviewers if allowed;  
reference file;  
article type;  
section/special issue target.

Step 3\. Map requirements to current materials.

For each item:

present;  
missing;  
needs update;  
not applicable;  
unknown;  
blocked.

Step 4\. Generate cover letter skeleton.

Cover letter should not fabricate claims. It should use ArticleModel and VenueModel evidence.

Step 5\. Generate portal field mapping.

If portal profile known, map SubmissionPack fields to portal fields. If unknown, output generic manual checklist.

Step 6\. Generate missing item tasks.

Every missing item becomes task.

Step 7\. Set ready status.

Allowed ready statuses:

not\_ready;  
needs\_user\_input;  
needs\_file\_update;  
needs\_reference\_verification;  
needs\_compliance\_check;  
ready\_for\_manual\_submission;  
submitted.

System should be conservative.

### **41.4. Outputs**

SubmissionPack;  
ComplianceChecklist update;  
CoverLetterDraft;  
MetadataTable;  
PortalFieldMapping;  
MissingItemsList;  
Vault card;  
optional external doc export.

### **41.5. Quality Gates**

Cannot be ready if:

guidelines stale;  
required metadata missing;  
blocking risks unresolved;  
references unverified if venue requires strict bibliography;  
AI/ethics/data statements unknown when relevant;  
target article type unknown;  
protected core changes pending user decision.

### **41.6. MVP Scope**

MVP creates draft SubmissionPack and missing item list. No automatic portal submission.

## **42\. Pipeline 6: Review / Rebuttal / Revision Loop**

### **42.1. Purpose**

After submission, Journal-Yuga should help interpret editorial and reviewer feedback, map it to prior ArticleModel/VenueModel/FitAssessment, create RevisionPlan and update VenueMemory.

### **42.2. Inputs**

review letter;  
editor decision;  
reviewer reports;  
submitted manuscript version;  
prior SubmissionPack;  
prior FitAssessment;  
user notes.

### **42.3. Pipeline Steps**

Step 1\. Register review materials as sources.

Review letters are sensitive sources. They must be stored with privacy metadata.

Step 2\. Create ReviewOutcome.

Extract decision type, review round, main reasons, requested changes, timeline, tone and actionability.

Step 3\. Map comments to issue types.

Issue types:

formal;  
scope;  
method;  
citation;  
argument clarity;  
novelty;  
writing;  
reviewer misunderstanding;  
fatal mismatch;  
policy;  
unknown.

Step 4\. Compare with prior FitAssessment.

Identify whether issues were predicted, missed, or contradicted.

Step 5\. Create RevisionPlan.

For each issue, define:

accept;  
resist;  
clarify;  
add evidence;  
rewrite;  
reframe;  
withdraw/resubmit elsewhere.

Step 6\. Generate RebuttalOutline.

Rebuttal must be structured but not dishonest. It should cite manuscript changes and evidence.

Step 7\. Update VenueMemory.

Add prior outcome with scoped status. Do not overgeneralize one outcome into universal venue preference.

### **42.4. Outputs**

ReviewOutcome;  
RevisionPlan;  
RebuttalOutline;  
Updated RiskReport;  
VenueMemory update;  
WhiteCrow patch candidates.

### **42.5. MVP Scope**

Build later. But schema and storage should exist early.

## **43\. Pipeline 7: Q3 / Local Journal / Conference Proceedings Fallback**

### **43.1. Purpose**

Journal-Yuga focuses on serious publication positioning, especially Q1/Q2 or high-quality venues, but it must not fail when user provides Q3, local journal, conference proceedings or lower-stakes publication container. It should run analogous logic at lighter depth.

### **43.2. Inputs**

target venue name/URL;  
conference page;  
proceedings CFP;  
local journal;  
user goal;  
manuscript/abstract.

### **43.3. Differences from main journal pipeline**

Less emphasis on deep citation ecology unless needed.

More emphasis on:

formal requirements;  
deadline;  
conference theme;  
proceedings format;  
paper length;  
registration fees;  
presentation requirement;  
publication/indexing claim verification;  
predatory/conference risk;  
fit to call;  
submission pack.

### **43.4. Outputs**

Light VenueModel;  
PublicationRegimeModel;  
FitAssessment;  
RiskReport;  
ComplianceChecklist;  
SubmissionPack draft.

### **43.5. Backlog Boundaries**

Unique conferences, author collections, zines, unusual public-intellectual venues and non-academic publication forms are backlog unless user explicitly asks and system supports custom regime.

## **44\. Pipeline 8: Scheduled Venue Refresh and Monitoring**

### **44.1. Purpose**

Venue data becomes stale. Journal-Yuga should support refresh, but scheduled automation is not MVP core.

### **44.2. Inputs**

VenueMemory;  
VenueModel;  
refresh policy;  
user/project priority;  
deadlines;  
watched CFPs.

### **44.3. Steps**

Identify stale sources;  
refresh official pages;  
compare snapshots;  
detect changed requirements;  
detect new CFP/special issues;  
update VenueModel;  
notify user if changes affect active SubmissionPack or FitAssessment.

### **44.4. MVP Scope**

Manual refresh only.

Full:

scheduled refresh jobs;  
Telegram reminders;  
CFP watchers;  
changed policy alerts.

## **45\. Pipeline 9: Telegram Intake and Lightweight Control**

### **45.1. Purpose**

Telegram is useful for intake and lightweight control. It is not the main analytical interface.

### **45.2. Allowed Telegram operations**

send manuscript/source;  
send venue URL;  
send CFP;  
send review letter;  
ask status;  
start quick profile;  
request existing report;  
add tacit note;  
approve/reject pending action;  
trigger refresh;  
receive reminders.

### **45.3. Telegram outputs**

short acknowledgement;  
job id;  
source id;  
status;  
short summary;  
link to full artifact;  
missing input question.

Telegram should not dump full complex reports unless user asks.

### **45.4. Risks**

Telegram messages are short and context-poor. System must not assume full SubmissionScenario from casual phrasing.

## **46\. Pipeline 10: User Tacit Knowledge Intake**

### **46.1. Purpose**

Users may know things about journals that are not in public sources. This is valuable but evidentially different.

### **46.2. Inputs**

user note;  
conversation transcript;  
email fragment;  
prior outcome;  
colleague report;  
editor contact note.

### **46.3. Steps**

Register note as source or user note;  
classify as TACIT\_SIGNAL or PRIOR\_OUTCOME;  
link to VenueModel;  
define scope and confidence;  
ask if sensitive;  
mark privacy level;  
decide whether it can influence FitAssessment.

### **46.4. Outputs**

TacitVenueSignal;  
VenueMemory update;  
RiskReport note;  
FitAssessment caveat.

### **46.5. Rules**

Tacit knowledge may influence strategy but cannot become fact. It must be visible and revocable.

## **47\. Pipeline 11: Human-in-the-loop Decision Pipeline**

### **47.1. Purpose**

Many Journal-Yuga outputs require user decision. The system must model decision points.

### **47.2. Decision types**

accept rewrite;  
reject rewrite;  
accept reframe;  
choose venue;  
narrow venue pool;  
allow citation expansion;  
allow translation;  
accept field-core risk;  
choose fallback;  
mark submission ready;  
store tacit signal;  
use prior outcome;  
submit externally.

### **47.3. Steps**

Present decision with evidence;  
show consequences;  
record user choice;  
update entities;  
trigger next pipeline.

### **47.4. Outputs**

UserDecision record;  
updated lifecycle statuses;  
patch queue updates;  
next action.

## **48\. Cross-Pipeline State Machine**

Journal-Yuga should support transitions between pipelines.

Direct Manuscript Fit can lead to:

SubmissionPack generation;  
RewritePlan to WhiteCrow;  
Venue pool discovery;  
ArticleVariant design;  
Venue deep profile;  
Review loop after outcome.

Venue Deep Profile can lead to:

Direct Manuscript Fit;  
Venue pool comparison;  
VenueMemory;  
scheduled refresh.

Journal Pool Discovery can lead to:

deep profile selected venues;  
one-target fit;  
reverse design;  
fallback search.

Review Loop can lead to:

revision plan;  
resubmit same venue;  
submit elsewhere;  
venue memory update;  
article variant.

SubmissionPack can lead to:

manual submission;  
external doc export;  
review loop;  
refresh before submission.

## **49\. Pipeline-Level Failure Modes**

### **49.1. False Completeness**

Risk: system presents incomplete source acquisition as complete.

Mitigation: coverage labels, unknowns, source acquisition report.

### **49.2. Overconfident Fit**

Risk: system gives strong recommendation without deep evidence.

Mitigation: assessment\_level and evidence-backed gate.

### **49.3. Prompt-only Output**

Risk: LLM produces prose without structured entities.

Mitigation: every pipeline must create entities and traces.

### **49.4. Destructive Adaptation**

Risk: rewrite destroys protected core.

Mitigation: field\_core\_impact and user acceptance.

### **49.5. Citation Hallucination**

Risk: system invents references.

Mitigation: CitationPlan separates search tasks, pending suggestions and verified references.

### **49.6. Venue Misidentification**

Risk: wrong journal or special issue.

Mitigation: canonicalization and user confirmation.

### **49.7. Stale Guidelines**

Risk: old author guidelines used for submission.

Mitigation: freshness gate before SubmissionPack ready status.

### **49.8. Tacit Signal Abuse**

Risk: user note treated as fact.

Mitigation: TacitVenueSignal status and visible caveat.

## **50\. Operational MVP Roadmap**

### **MVP-0: Domain skeleton**

Implement schemas/registries for:

ArticleModel;  
ManuscriptModel;  
VenueModel;  
PublicationRegimeModel;  
SubmissionScenario;  
EvidenceItem;  
FitAssessment;  
MismatchMap;  
RewritePlan;  
CitationPlan stub;  
RiskReport;  
ComplianceChecklist;  
SubmissionPack stub;  
PipelineRun;  
OperationTrace.

No heavy adapters yet.

### **MVP-1: One manuscript × one venue**

Implement Pipeline 1 with manual/source-based light VenueModel.

Required outputs:

ArticleModel;  
VenueModel;  
SubmissionScenario;  
FitAssessment;  
MismatchMap;  
RewritePlan;  
RiskReport;  
ComplianceChecklist;  
human-readable artifact.

### **MVP-2: Venue Deep Profile light**

Implement Pipeline 2 light profile.

Required outputs:

VenueProfile;  
source acquisition report;  
policy/guideline extraction;  
Vault card.

### **MVP-3: Citation and reference layer**

Implement Crossref/OpenCitations/reference verification and CitationPlan.

### **MVP-4: Venue Pool Discovery**

Implement small candidate pool and comparison, no false deep fit.

### **MVP-5: SubmissionPack draft**

Implement operational submission checklist and metadata package.

### **MVP-6: WhiteCrow PatchQueue integration**

Turn RewritePlan/ReframePlan into patch candidates.

### **MVP-7: Review/Rebuttal loop**

Implement ReviewOutcome, RevisionPlan, RebuttalOutline and VenueMemory update.

## **51\. Wave 5 Closure**

This wave defines how Journal-Yuga acts. The system is not a static ontology and not a chat assistant; it is a set of operational pipelines over typed entities and evidence. The first true implementation target is Direct Manuscript × One Target Venue. Every later feature depends on this path. Venue pool, reverse design, submission pack and review loop are extensions, not starting points.

The next wave should define agent roles and prompt families in detail: which agent is responsible for each transformation, what inputs and outputs it has, what it is forbidden to do, what evidence requirements apply, when it must ask the user, and how prompts are grouped so that the system does not collapse into one overloaded universal LLM call.

# **JOURNAL\_YUGA\_TECHNICAL\_SPEC\_FOR\_CLAUDE\_v0\_1**

## **Волна 5\. Operational Pipelines: рабочие сценарии, переходы, артефакты, проверки и отказоустойчивость**

## **35\. Purpose of Operational Pipelines**

Operational pipelines описывают, как Journal-Yuga реально работает: как входной материал превращается в ArticleModel, как собирается VenueModel, как строится SubmissionScenario, как производится FitAssessment, как из него возникают MismatchMap, RewritePlan, CitationPlan, RiskReport, ComplianceChecklist, SubmissionPack и, при необходимости, WhiteCrow Patch Queue или VenueMemory update.

Пайплайн — это не UI-сценарий и не prompt. Это воспроизводимая последовательность операций над доменными объектами. UI может быть чатовым, web-based, Telegram-based или CLI/API-based, но внутри система должна проходить одни и те же доменные стадии. Если пользователь написал в Telegram “подбери журнал”, web UI загрузил DOCX, или WhiteCrow передал Field Text, Journal-Yuga всё равно должен создавать typed objects, evidence refs, operation trace and quality gates.

Каждый pipeline должен иметь:

pipeline\_id;  
pipeline\_type;  
entry mode;  
required inputs;  
optional inputs;  
created entities;  
updated entities;  
required sources;  
evidence threshold;  
user questions;  
quality gates;  
failure modes;  
outputs;  
handoff targets;  
logs and traces;  
MVP scope;  
future full scope.

Ни один pipeline не должен завершаться “LLM ответом” как единственным результатом. Текстовый ответ может быть пользовательским summary, но canonical result должен быть набором структурированных объектов и артефактов.

## **36\. Common Pipeline Envelope**

Все pipeline должны использовать общий operational envelope.

### **36.1. PipelineRun**

Поля:

pipeline\_run\_id;  
pipeline\_type;  
project\_id;  
user\_id;  
entry\_channel;  
started\_at;  
finished\_at;  
status;  
input\_refs;  
created\_entity\_ids;  
updated\_entity\_ids;  
source\_ids\_used;  
context\_pack\_ids\_used;  
adapters\_called;  
agent\_roles\_used;  
prompt\_family\_refs;  
quality\_gate\_results;  
user\_questions\_asked;  
user\_decisions\_recorded;  
warnings;  
errors;  
cost\_estimate;  
token\_estimate;  
next\_actions.

`entry_channel`:

web\_ui;  
telegram;  
cli;  
api;  
whitecrow;  
litops;  
scheduled\_job;  
manual\_admin;  
unknown.

`status`:

created;  
running;  
waiting\_for\_sources;  
waiting\_for\_user;  
partial\_success;  
completed;  
failed;  
cancelled;  
stale;  
superseded.

### **36.2. Pipeline Quality Gate**

Каждый pipeline должен иметь quality gate. Gate не должен быть декоративным. Он определяет, можно ли перейти к следующей стадии, нужно ли задать пользователю вопрос, нужно ли собрать дополнительные источники, можно ли выдавать evidence-backed output или только preliminary output.

Общий формат gate result:

gate\_id;  
gate\_name;  
pipeline\_run\_id;  
status;  
blocking\_issues;  
warnings;  
missing\_sources;  
unknown\_fields;  
stale\_sources;  
unsupported\_claims;  
required\_user\_decisions;  
recommendation.

`status`:

passed;  
passed\_with\_warnings;  
failed\_blocking;  
failed\_but\_preliminary\_output\_allowed;  
needs\_user\_input;  
needs\_source\_refresh;  
not\_applicable.

### **36.3. Pipeline Output Levels**

Каждый pipeline output должен иметь уровень зрелости.

`rough_note` — свободная заметка, не доменный результат.

`preliminary` — объект создан, но данных мало; выводы осторожные.

`light_profile` — достаточно для навигации, недостаточно для deep fit.

`evidence_backed` — есть источники, ContextPack, EvidenceItems, unknowns and confidence.

`submission_ready` — пройдены freshness and compliance gates.

`post_outcome` — обновлено после реального review/submission outcome.

MVP может производить `preliminary` and `light_profile`, но должен явно маркировать их. Нельзя выдавать preliminary как submission-ready.

### **36.4. Common User Question Model**

Journal-Yuga должен задавать вопросы не как разговорный бот, а как механизм закрытия недостающих полей.

Question fields:

question\_id;  
related\_entity\_id;  
related\_pipeline\_run\_id;  
question\_type;  
question\_text;  
why\_needed;  
blocking\_level;  
answer\_type;  
options;  
default\_if\_skipped;  
user\_answer;  
answered\_at;  
effect\_on\_entities.

Question types:

submission\_goal;  
target\_indexing;  
deadline;  
APC\_constraint;  
rewrite\_depth;  
reframe\_allowed;  
protected\_core;  
target\_language;  
article\_type;  
fallback\_acceptance;  
venue\_choice;  
source\_confirmation;  
tacit\_signal\_confirmation;  
risk\_acceptance.

Questions should be minimized. System should not interrogate user unnecessarily. But if a missing answer changes fit significantly, the question should be explicit.

## **37\. Pipeline 1: Direct Manuscript × One Target Venue**

This is the first core MVP pipeline. If this pipeline is not working, no journal pool, reverse design or submission pack can be trusted.

### **37.1. Purpose**

Given one manuscript/draft/abstract/article model and one target venue, determine whether the article can be submitted to that venue, what mismatches exist, what adaptation would be required, what citation/compliance/risk work is needed, and whether the system can produce a preliminary or evidence-backed SubmissionPack.

### **37.2. Entry Modes**

User may enter through:

upload manuscript \+ paste journal URL;  
paste abstract \+ journal name;  
select Litops source\_id \+ venue URL;  
select WhiteCrow manuscript \+ target venue;  
provide ArticleModel \+ VenueModel IDs;  
Telegram command with source and venue;  
CLI/API call.

### **37.3. Required Inputs**

At minimum:

article input: manuscript, draft, abstract, source\_id, ArticleModel or WhiteCrow manuscript ref;  
target venue input: journal/venue name, URL, VenueModel or venue source;  
SubmissionScenario minimal answers or defaults.

Hard minimum for preliminary output:

one article source;  
one venue identifier;  
at least minimal user goal.

Hard minimum for evidence-backed fit:

ArticleModel with source refs;  
VenueModel with homepage/scope or author guidelines;  
SubmissionScenario confirmed;  
EvidenceItems for key claims;  
ContextPack linking article and venue sources.

### **37.4. Optional Inputs**

bibliography file;  
prior article drafts;  
WhiteCrow field context;  
protected core;  
user notes about venue;  
review timeline expectations;  
target article type;  
special issue URL;  
previous submission outcome;  
corpus of articles from venue.

### **37.5. Step-by-Step Pipeline**

Step 1\. Normalize inputs.

System identifies whether article input is abstract, draft, full manuscript, WhiteCrow field, existing ArticleModel or mixed input. System identifies whether venue input is URL, journal name, ISSN, publisher page, existing VenueModel or user note.

Created or updated:

PipelineRun;  
input source refs;  
input normalization notes.

Failure mode:

If no article-like input exists, pipeline cannot proceed to fit. It may create venue profile only.

If no venue-like input exists, pipeline cannot proceed to one-target fit. It may create ArticleModel only.

Step 2\. Register or resolve sources through Litops.

If input files or URLs are not registered, system creates or requests Litops Source registration. If sources already exist, system links them. If URL cannot be fetched, create INACCESSIBLE source state.

Created:

SourceSnapshot;  
EvidenceItems for input availability;  
ContextPack skeleton.

Gate:

No unregistered external source should be used for evidence-backed output.

Step 3\. Build or update ManuscriptModel.

For full text or file input, system extracts title, abstract, sections, word count, bibliography presence, language and basic structure. If only abstract is present, ManuscriptModel is minimal and ArticleModel becomes preliminary.

Created:

ManuscriptModel.

Warnings:

abstract\_only;  
bibliography\_missing;  
section\_extraction\_failed;  
PDF\_parse\_low\_confidence;  
language\_unknown.

Step 4\. Build ArticleModel.

System extracts publication-facing structure: problem, object, question, core claims, argument, genre, method status, discipline, novelty mode, theoretical shoulders, current citation ecology, protected core if possible, unknowns.

If protected core is not available, system asks user one question:

“What must not be changed in this article even if a venue requires adaptation?”

If user skips, protected core remains UNKNOWN and field-core-risk checks are weaker.

Created:

ArticleModel;  
ArticleModel questions if needed.

Gate:

Deep RewritePlan cannot be generated without at least provisional protected core status.

Step 5\. Resolve target venue.

System canonicalizes venue name/URL. If multiple possible venues are found, asks user to confirm. If URL is a special issue or research topic, system should not collapse it into parent journal only; it should create IssueModel or ResearchTopicModel linked to JournalModel/VenueModel.

Created:

Venue candidate records;  
canonical venue decision;  
PublicationRegimeModel candidate.

Warnings:

ambiguous venue;  
publisher landing page only;  
special issue detected;  
conference proceedings detected;  
non-journal venue detected.

Step 6\. Build light VenueModel.

System fetches or uses sources for homepage, aims/scope, author guidelines, article types and submission information. If unavailable, unknowns are explicit. System creates light VenueModel and PublicationRegimeModel.

Created:

VenueModel;  
JournalModel if applicable;  
PublicationRegimeModel;  
Venue ContextPack.

Gate:

If no official venue source is available, output is preliminary only.

Step 7\. Build minimal SubmissionScenario.

System asks or infers from user:

goal;  
target indexing;  
deadline;  
APC tolerance;  
rewrite depth allowed;  
reframe allowed;  
target language;  
fallback allowed.

If user did not specify, defaults are marked unknown, not assumed.

Created:

SubmissionScenario.

Gate:

FitAssessment without SubmissionScenario is preliminary.

Step 8\. Perform fit assessment.

System compares ArticleModel, VenueModel, PublicationRegimeModel and SubmissionScenario across axes:

topic;  
discipline;  
genre;  
argument;  
method;  
citation ecology;  
novelty mode;  
language/register;  
formal compliance;  
author eligibility;  
publication regime;  
timeline;  
APC/policy;  
field-core preservation;  
strategic value.

Created:

FitAssessment.

Each axis must contain:

value;  
evidence refs;  
unknowns;  
confidence;  
notes.

Step 9\. Generate MismatchMap.

System translates weak fit axes into specific mismatches. Each mismatch must include article side, venue side, severity, evidence, possible action and field-core impact.

Created:

MismatchMap.

Step 10\. Generate RewritePlan and ReframePlan if needed.

If mismatches are form-level, create RewritePlan. If mismatches require changing object, discipline, genre, method, novelty or protected core, create ReframePlan or ArticleVariant suggestion.

Created:

RewritePlan;  
ReframePlan optional;  
WhiteCrow patch candidates optional.

Gate:

Any core-touching change requires user acceptance.

Step 11\. Generate CitationPlan.

System compares current citation ecology against venue/corpus expectations. In MVP this may be a stub with tasks rather than verified references.

Created:

CitationPlan.

MVP allowed outputs:

missing citation bridge categories;  
reference verification tasks;  
dangerous padding warnings;  
bibliography format concerns.

Full outputs:

verified reference suggestions;  
citation graph evidence;  
venue-specific citation ecology.

Step 12\. Generate RiskReport.

System identifies formal, policy, citation, field-core, timeline, APC, indexing, author eligibility, AI disclosure and review risks.

Created:

RiskReport.

Step 13\. Generate ComplianceChecklist.

System extracts requirements from author guidelines and publication regime. If requirements are unavailable, checklist marks unknowns. It should not hallucinate generic requirements as venue-specific.

Created:

ComplianceChecklist.

Step 14\. Generate optional SubmissionPack draft.

If user asks or if enough data exists, system creates a draft SubmissionPack with status not\_ready or needs\_user\_input. It should not mark ready unless fresh requirements and required fields are present.

Created:

SubmissionPack.

Step 15\. Write artifacts and projections.

System writes human-readable report and Vault cards:

ArticleModel card;  
VenueModel card;  
FitAssessment report;  
MismatchMap;  
RewritePlan;  
CitationPlan;  
RiskReport;  
ComplianceChecklist;  
SubmissionPack draft if any.

Step 16\. Record operation trace.

Every step, source, prompt, adapter call, output and user question is logged.

### **37.6. Outputs**

Mandatory outputs:

ArticleModel;  
VenueModel;  
SubmissionScenario;  
FitAssessment;  
MismatchMap;  
RiskReport;  
operation trace.

Conditional outputs:

RewritePlan;  
ReframePlan;  
CitationPlan;  
ComplianceChecklist;  
SubmissionPack;  
WhiteCrow patch candidates;  
Vault cards.

### **37.7. Quality Gates**

Preliminary fit allowed if:

article input exists;  
venue identifier exists;  
some source evidence exists;  
unknowns are explicit.

Evidence-backed fit requires:

ArticleModel confirmed or sufficiently sourced;  
VenueModel light profile with official sources;  
SubmissionScenario confirmed;  
evidence refs per fit axis;  
ContextPack created.

SubmissionPack draft requires:

ComplianceChecklist created;  
Venue requirements source present or explicitly unknown;  
ManuscriptModel present.

Ready-for-manual-submission requires:

fresh author guidelines;  
required metadata;  
required files list;  
required statements;  
reference verification level reached;  
blocking risks resolved or accepted.

### **37.8. MVP Scope**

MVP-1 implements this pipeline for one manuscript and one venue. It does not implement journal pool, automatic article corpus mining, final rewrite, reviewer simulation or automatic submission.

## **38\. Pipeline 2: Venue Deep Profile**

### **38.1. Purpose**

Venue Deep Profile builds a detailed model of one publication container without necessarily having a specific article. It is used when user asks “what is this journal/venue?”, “can we target this venue later?”, “profile this special issue”, “create venue memory”, or when Journal-Yuga needs evidence for later fit assessments.

### **38.2. Inputs**

venue name;  
venue URL;  
journal ISSN;  
publisher page;  
special issue URL;  
research topic URL;  
conference proceedings page;  
existing VenueModel;  
user notes;  
article corpus pack.

### **38.3. Pipeline Steps**

Step 1\. Resolve venue identity.

Identify whether target is journal, section, special issue, research topic, conference proceedings, open-review venue, mega-journal or other. If ambiguous, create candidates and ask user.

Step 2\. Create or update VenueModel skeleton.

Fill canonical name, publisher, official URLs, venue type, initial publication regime.

Step 3\. Acquire official sources.

Attempt to collect homepage, aims/scope, author guidelines, editorial board, submission information, policy pages, OA/APC, article type pages, issue pages, special issue pages.

Step 4\. Create SourceSnapshots and EvidenceItems.

Every page becomes source/snapshot/evidence. Missing pages become unknowns or inaccessible sources.

Step 5\. Extract formal requirements.

Extract article types, length, abstract, keywords, references, formatting, statements, file requirements, submission route, language, policies.

Step 6\. Build PolicySnapshot.

If policy pages exist, extract AI disclosure, data availability, ethics, COI, funding, authorship, copyright, preprint/self-archiving where available.

Step 7\. Build EditorialBoardProfile.

Extract visible editors, roles, affiliations and disciplinary signals. Mark as visible board data, not hidden preference.

Step 8\. Build PublicationRegimeModel.

Classify regime: classic journal, special issue, research topic, conference proceedings, mega-journal, reviewed preprint, open review, humanities symposium, edited volume, local/Q3 fallback etc.

Step 9\. Acquire or define article corpus.

Collect recent articles, most cited/read if available, section-specific articles or user-uploaded corpus. Record selection strategy and representativeness.

Step 10\. Generate PublishedArticlePatterns.

Mine patterns: article structures, abstract forms, method presence, citation density, theoretical anchors, length, novelty form, genre moves.

Step 11\. Generate CitationExpectationProfile.

Using corpus and citation metadata where possible, identify likely citation expectations. Mark as corpus observation and inference, not venue fact.

Step 12\. Create VenueProfile artifact.

Human-readable profile includes:

identity;  
scope;  
regime;  
article types;  
requirements;  
policies;  
corpus observations;  
citation ecology;  
editorial visible structure;  
metrics/indexing if verified;  
unknowns;  
risks;  
use cases;  
refresh dates.

### **38.4. Outputs**

VenueModel;  
JournalModel;  
PublicationRegimeModel;  
PolicySnapshot;  
EditorialBoardProfile;  
PublishedArticleCorpus;  
PublishedArticlePatterns;  
CitationExpectationProfile;  
VenueProfile artifact;  
VenueContextPack;  
Vault card.

### **38.5. Quality Levels**

Light profile:

homepage \+ scope/guidelines \+ basic metadata.

Deep profile:

official pages \+ policies \+ editorial board \+ article corpus \+ citation expectations \+ staleness policy.

Submission-ready venue profile:

fresh guidelines \+ fresh policies \+ fresh submission information \+ missing fields resolved.

### **38.6. MVP Scope**

MVP supports light profile. Deep profile with 20–50 articles comes later.

## **39\. Pipeline 3: Journal / Venue Pool Discovery**

### **39.1. Purpose**

Venue Pool Discovery finds a candidate set of venues for an ArticleModel or user idea. It should not pretend to perform deep fit for every candidate. It creates a shortlist and light profiles, then recommends which venues deserve deep profiling.

### **39.2. Inputs**

ArticleModel;  
abstract;  
draft;  
WhiteCrow field;  
SubmissionScenario;  
target disciplines;  
desired indexing;  
language;  
APC constraints;  
deadline;  
fallback rules;  
seed venues;  
excluded venues.

### **39.3. Pipeline Steps**

Step 1\. Build or receive ArticleModel.

If only abstract is available, mark pool discovery as preliminary.

Step 2\. Confirm SubmissionScenario.

Important fields: target indexing, prestige/speed tradeoff, discipline, language, APC, rewrite allowed, fallback allowed.

Step 3\. Generate search/discovery strategies.

Strategies:

metadata-based discovery via OpenAlex/Crossref;  
similar article venue discovery;  
user seed expansion;  
discipline/category browsing;  
special issue/CFP discovery;  
humanities community source discovery;  
manual candidates.

Step 4\. Create candidate venues.

For each candidate:

name;  
source;  
why found;  
evidence;  
candidate type;  
initial publication regime;  
confidence;  
unknowns.

Step 5\. Deduplicate and canonicalize.

Merge candidate duplicates by ISSN/title/publisher/URL where safe. Ambiguous candidates remain separate.

Step 6\. Create light VenueModels.

For each candidate, gather minimal metadata and source refs.

Step 7\. Apply filters.

Filters:

language;  
discipline;  
open access/APC;  
indexing;  
article type;  
country/region;  
publisher bias;  
deadline;  
special issue relevance;  
fallback status.

Step 8\. Produce preliminary Fit Screening.

Not full FitAssessment. Use ArticleModel and light VenueModel to classify:

promising;  
possible;  
needs deep profile;  
probably poor fit;  
unknown.

Step 9\. Recommend deep profile targets.

Select 3–5 venues for deep profile based on potential fit, strategic value, uncertainty and user scenario.

### **39.4. Outputs**

Venue candidate list;  
light VenueModels;  
VenuePoolContextPack;  
preliminary screening matrix;  
recommended deep profile list;  
unknowns and missing data list.

### **39.5. Prohibitions**

Do not rank venues with final claims if only light metadata exists.

Do not hide publisher-owned bias.

Do not infer indexing/quartile without verified source.

Do not claim acceptance probability.

Do not treat “not found” as “not suitable”.

### **39.6. MVP Scope**

MVP-2 supports small pool discovery after one-venue pipeline works.

## **40\. Pipeline 4: Reverse Design for Venue Pool**

### **40.1. Purpose**

Reverse Design answers a different question: not “where can this article go?”, but “what article should be built if we want to publish in this pool of venues or publication regime?”

This is important for WhiteCrow integration, where the starting object may be a field, not a manuscript.

### **40.2. Inputs**

venue pool;  
target discipline;  
WhiteCrow field;  
field text;  
source corpus;  
user goal;  
constraints;  
publication regime.

### **40.3. Pipeline Steps**

Step 1\. Profile venue pool lightly or deeply.

Identify shared expectations, differences and incompatible requirements.

Step 2\. Build FieldModelReference.

Receive or create field summary, central tensions, possible article trajectories, protected core.

Step 3\. Infer possible ArticleVariants.

For each venue cluster, propose candidate article form:

discipline;  
genre;  
question;  
object;  
theoretical shoulders;  
method status;  
citation ecology;  
language/register.

Step 4\. Compare variants to protected core.

Classify variants:

core-preserving;  
core-touching;  
core-transforming;  
too destructive.

Step 5\. Generate Article Design Map.

For each candidate variant:

title direction;  
abstract direction;  
section structure;  
citation bridges;  
needed sources;  
risks;  
venue candidates;  
effort.

Step 6\. Return to WhiteCrow.

Output should become article trajectory options, not direct manuscript rewrite.

### **40.4. Outputs**

ArticleVariant candidates;  
ReframePlan;  
VenueClusterProfile;  
CitationBridgeTasks;  
WhiteCrow trajectory suggestions;  
risk comparison.

### **40.5. MVP Scope**

Build later. Schema and conceptual support now.

## **41\. Pipeline 5: Submission Pack Generation**

### **41.1. Purpose**

SubmissionPack turns fit/adaptation/compliance work into operational readiness for manual submission. It is not a generic report. It models downstream gates.

### **41.2. Inputs**

ManuscriptModel;  
ArticleModel;  
VenueModel;  
PublicationRegimeModel;  
SubmissionScenario;  
ComplianceChecklist;  
RiskReport;  
CitationPlan;  
RewritePlan status.

### **41.3. Pipeline Steps**

Step 1\. Verify readiness prerequisites.

Check whether manuscript exists, target venue confirmed, guidelines fresh, scenario confirmed, blocking risks known, references checked to required level.

Step 2\. Build required submission inventory.

Collect:

main manuscript;  
title;  
abstract;  
keywords;  
authors;  
affiliations;  
ORCID;  
corresponding author;  
funding;  
COI;  
data availability;  
ethics;  
AI disclosure;  
CRediT;  
cover letter;  
figures/tables;  
supplementary files;  
permissions;  
reviewer suggestions if needed;  
opposed reviewers if allowed;  
reference file;  
article type;  
section/special issue target.

Step 3\. Map requirements to current materials.

For each item:

present;  
missing;  
needs update;  
not applicable;  
unknown;  
blocked.

Step 4\. Generate cover letter skeleton.

Cover letter should not fabricate claims. It should use ArticleModel and VenueModel evidence.

Step 5\. Generate portal field mapping.

If portal profile known, map SubmissionPack fields to portal fields. If unknown, output generic manual checklist.

Step 6\. Generate missing item tasks.

Every missing item becomes task.

Step 7\. Set ready status.

Allowed ready statuses:

not\_ready;  
needs\_user\_input;  
needs\_file\_update;  
needs\_reference\_verification;  
needs\_compliance\_check;  
ready\_for\_manual\_submission;  
submitted.

System should be conservative.

### **41.4. Outputs**

SubmissionPack;  
ComplianceChecklist update;  
CoverLetterDraft;  
MetadataTable;  
PortalFieldMapping;  
MissingItemsList;  
Vault card;  
optional external doc export.

### **41.5. Quality Gates**

Cannot be ready if:

guidelines stale;  
required metadata missing;  
blocking risks unresolved;  
references unverified if venue requires strict bibliography;  
AI/ethics/data statements unknown when relevant;  
target article type unknown;  
protected core changes pending user decision.

### **41.6. MVP Scope**

MVP creates draft SubmissionPack and missing item list. No automatic portal submission.

## **42\. Pipeline 6: Review / Rebuttal / Revision Loop**

### **42.1. Purpose**

After submission, Journal-Yuga should help interpret editorial and reviewer feedback, map it to prior ArticleModel/VenueModel/FitAssessment, create RevisionPlan and update VenueMemory.

### **42.2. Inputs**

review letter;  
editor decision;  
reviewer reports;  
submitted manuscript version;  
prior SubmissionPack;  
prior FitAssessment;  
user notes.

### **42.3. Pipeline Steps**

Step 1\. Register review materials as sources.

Review letters are sensitive sources. They must be stored with privacy metadata.

Step 2\. Create ReviewOutcome.

Extract decision type, review round, main reasons, requested changes, timeline, tone and actionability.

Step 3\. Map comments to issue types.

Issue types:

formal;  
scope;  
method;  
citation;  
argument clarity;  
novelty;  
writing;  
reviewer misunderstanding;  
fatal mismatch;  
policy;  
unknown.

Step 4\. Compare with prior FitAssessment.

Identify whether issues were predicted, missed, or contradicted.

Step 5\. Create RevisionPlan.

For each issue, define:

accept;  
resist;  
clarify;  
add evidence;  
rewrite;  
reframe;  
withdraw/resubmit elsewhere.

Step 6\. Generate RebuttalOutline.

Rebuttal must be structured but not dishonest. It should cite manuscript changes and evidence.

Step 7\. Update VenueMemory.

Add prior outcome with scoped status. Do not overgeneralize one outcome into universal venue preference.

### **42.4. Outputs**

ReviewOutcome;  
RevisionPlan;  
RebuttalOutline;  
Updated RiskReport;  
VenueMemory update;  
WhiteCrow patch candidates.

### **42.5. MVP Scope**

Build later. But schema and storage should exist early.

## **43\. Pipeline 7: Q3 / Local Journal / Conference Proceedings Fallback**

### **43.1. Purpose**

Journal-Yuga focuses on serious publication positioning, especially Q1/Q2 or high-quality venues, but it must not fail when user provides Q3, local journal, conference proceedings or lower-stakes publication container. It should run analogous logic at lighter depth.

### **43.2. Inputs**

target venue name/URL;  
conference page;  
proceedings CFP;  
local journal;  
user goal;  
manuscript/abstract.

### **43.3. Differences from main journal pipeline**

Less emphasis on deep citation ecology unless needed.

More emphasis on:

formal requirements;  
deadline;  
conference theme;  
proceedings format;  
paper length;  
registration fees;  
presentation requirement;  
publication/indexing claim verification;  
predatory/conference risk;  
fit to call;  
submission pack.

### **43.4. Outputs**

Light VenueModel;  
PublicationRegimeModel;  
FitAssessment;  
RiskReport;  
ComplianceChecklist;  
SubmissionPack draft.

### **43.5. Backlog Boundaries**

Unique conferences, author collections, zines, unusual public-intellectual venues and non-academic publication forms are backlog unless user explicitly asks and system supports custom regime.

## **44\. Pipeline 8: Scheduled Venue Refresh and Monitoring**

### **44.1. Purpose**

Venue data becomes stale. Journal-Yuga should support refresh, but scheduled automation is not MVP core.

### **44.2. Inputs**

VenueMemory;  
VenueModel;  
refresh policy;  
user/project priority;  
deadlines;  
watched CFPs.

### **44.3. Steps**

Identify stale sources;  
refresh official pages;  
compare snapshots;  
detect changed requirements;  
detect new CFP/special issues;  
update VenueModel;  
notify user if changes affect active SubmissionPack or FitAssessment.

### **44.4. MVP Scope**

Manual refresh only.

Full:

scheduled refresh jobs;  
Telegram reminders;  
CFP watchers;  
changed policy alerts.

## **45\. Pipeline 9: Telegram Intake and Lightweight Control**

### **45.1. Purpose**

Telegram is useful for intake and lightweight control. It is not the main analytical interface.

### **45.2. Allowed Telegram operations**

send manuscript/source;  
send venue URL;  
send CFP;  
send review letter;  
ask status;  
start quick profile;  
request existing report;  
add tacit note;  
approve/reject pending action;  
trigger refresh;  
receive reminders.

### **45.3. Telegram outputs**

short acknowledgement;  
job id;  
source id;  
status;  
short summary;  
link to full artifact;  
missing input question.

Telegram should not dump full complex reports unless user asks.

### **45.4. Risks**

Telegram messages are short and context-poor. System must not assume full SubmissionScenario from casual phrasing.

## **46\. Pipeline 10: User Tacit Knowledge Intake**

### **46.1. Purpose**

Users may know things about journals that are not in public sources. This is valuable but evidentially different.

### **46.2. Inputs**

user note;  
conversation transcript;  
email fragment;  
prior outcome;  
colleague report;  
editor contact note.

### **46.3. Steps**

Register note as source or user note;  
classify as TACIT\_SIGNAL or PRIOR\_OUTCOME;  
link to VenueModel;  
define scope and confidence;  
ask if sensitive;  
mark privacy level;  
decide whether it can influence FitAssessment.

### **46.4. Outputs**

TacitVenueSignal;  
VenueMemory update;  
RiskReport note;  
FitAssessment caveat.

### **46.5. Rules**

Tacit knowledge may influence strategy but cannot become fact. It must be visible and revocable.

## **47\. Pipeline 11: Human-in-the-loop Decision Pipeline**

### **47.1. Purpose**

Many Journal-Yuga outputs require user decision. The system must model decision points.

### **47.2. Decision types**

accept rewrite;  
reject rewrite;  
accept reframe;  
choose venue;  
narrow venue pool;  
allow citation expansion;  
allow translation;  
accept field-core risk;  
choose fallback;  
mark submission ready;  
store tacit signal;  
use prior outcome;  
submit externally.

### **47.3. Steps**

Present decision with evidence;  
show consequences;  
record user choice;  
update entities;  
trigger next pipeline.

### **47.4. Outputs**

UserDecision record;  
updated lifecycle statuses;  
patch queue updates;  
next action.

## **48\. Cross-Pipeline State Machine**

Journal-Yuga should support transitions between pipelines.

Direct Manuscript Fit can lead to:

SubmissionPack generation;  
RewritePlan to WhiteCrow;  
Venue pool discovery;  
ArticleVariant design;  
Venue deep profile;  
Review loop after outcome.

Venue Deep Profile can lead to:

Direct Manuscript Fit;  
Venue pool comparison;  
VenueMemory;  
scheduled refresh.

Journal Pool Discovery can lead to:

deep profile selected venues;  
one-target fit;  
reverse design;  
fallback search.

Review Loop can lead to:

revision plan;  
resubmit same venue;  
submit elsewhere;  
venue memory update;  
article variant.

SubmissionPack can lead to:

manual submission;  
external doc export;  
review loop;  
refresh before submission.

## **49\. Pipeline-Level Failure Modes**

### **49.1. False Completeness**

Risk: system presents incomplete source acquisition as complete.

Mitigation: coverage labels, unknowns, source acquisition report.

### **49.2. Overconfident Fit**

Risk: system gives strong recommendation without deep evidence.

Mitigation: assessment\_level and evidence-backed gate.

### **49.3. Prompt-only Output**

Risk: LLM produces prose without structured entities.

Mitigation: every pipeline must create entities and traces.

### **49.4. Destructive Adaptation**

Risk: rewrite destroys protected core.

Mitigation: field\_core\_impact and user acceptance.

### **49.5. Citation Hallucination**

Risk: system invents references.

Mitigation: CitationPlan separates search tasks, pending suggestions and verified references.

### **49.6. Venue Misidentification**

Risk: wrong journal or special issue.

Mitigation: canonicalization and user confirmation.

### **49.7. Stale Guidelines**

Risk: old author guidelines used for submission.

Mitigation: freshness gate before SubmissionPack ready status.

### **49.8. Tacit Signal Abuse**

Risk: user note treated as fact.

Mitigation: TacitVenueSignal status and visible caveat.

## **50\. Operational MVP Roadmap**

### **MVP-0: Domain skeleton**

Implement schemas/registries for:

ArticleModel;  
ManuscriptModel;  
VenueModel;  
PublicationRegimeModel;  
SubmissionScenario;  
EvidenceItem;  
FitAssessment;  
MismatchMap;  
RewritePlan;  
CitationPlan stub;  
RiskReport;  
ComplianceChecklist;  
SubmissionPack stub;  
PipelineRun;  
OperationTrace.

No heavy adapters yet.

### **MVP-1: One manuscript × one venue**

Implement Pipeline 1 with manual/source-based light VenueModel.

Required outputs:

ArticleModel;  
VenueModel;  
SubmissionScenario;  
FitAssessment;  
MismatchMap;  
RewritePlan;  
RiskReport;  
ComplianceChecklist;  
human-readable artifact.

### **MVP-2: Venue Deep Profile light**

Implement Pipeline 2 light profile.

Required outputs:

VenueProfile;  
source acquisition report;  
policy/guideline extraction;  
Vault card.

### **MVP-3: Citation and reference layer**

Implement Crossref/OpenCitations/reference verification and CitationPlan.

### **MVP-4: Venue Pool Discovery**

Implement small candidate pool and comparison, no false deep fit.

### **MVP-5: SubmissionPack draft**

Implement operational submission checklist and metadata package.

### **MVP-6: WhiteCrow PatchQueue integration**

Turn RewritePlan/ReframePlan into patch candidates.

### **MVP-7: Review/Rebuttal loop**

Implement ReviewOutcome, RevisionPlan, RebuttalOutline and VenueMemory update.

## **51\. Wave 5 Closure**

This wave defines how Journal-Yuga acts. The system is not a static ontology and not a chat assistant; it is a set of operational pipelines over typed entities and evidence. The first true implementation target is Direct Manuscript × One Target Venue. Every later feature depends on this path. Venue pool, reverse design, submission pack and review loop are extensions, not starting points.

The next wave should define agent roles and prompt families in detail: which agent is responsible for each transformation, what inputs and outputs it has, what it is forbidden to do, what evidence requirements apply, when it must ask the user, and how prompts are grouped so that the system does not collapse into one overloaded universal LLM call.

# **JOURNAL\_YUGA\_TECHNICAL\_SPEC\_FOR\_CLAUDE\_v0\_1**

## **Волна 6\. Agent Roles, Prompt Families, orchestration, evidence gates and failure rules**

## **52\. Purpose of Agent Architecture**

Journal-Yuga должен быть устроен как система специализированных агентных ролей, а не как один большой LLM-prompt. Это принципиальное архитектурное требование. Если вся логика venue-fit, article modeling, corpus analysis, citation planning, risk reporting and submission pack generation будет собрана в один универсальный вызов модели, система быстро потеряет проверяемость: ArticleModel смешается с VenueModel, evidence смешается с inference, rewriting смешается с reframe, citation plan начнёт галлюцинировать источники, а fit превратится в риторически убедительный, но непроверяемый совет.

Agent role в Journal-Yuga — это не автономная личность и не чатовый персонаж. Это bounded operational role: определённый тип преобразования, имеющий допустимые входы, допустимые выходы, evidence requirements, forbidden behavior, failure modes and escalation rules. Один и тот же LLM-провайдер может исполнять разные роли, но в доменной архитектуре они должны быть разделены.

Каждая агентная роль должна иметь:

agent\_role\_id;  
purpose;  
allowed inputs;  
required inputs;  
produced entities;  
produced artifacts;  
evidence requirements;  
forbidden behavior;  
when to ask user;  
when to fail closed;  
quality gates;  
trace requirements;  
downstream consumers;  
MVP status.

Prompt family — это не единичный prompt. Это набор связанных prompt templates, schemas, validators and post-processors for one role or transformation. Prompt family должна быть versioned, traceable and testable. Каждый prompt family output должен маппиться на typed entity, registry record or artifact, а не оставаться свободным текстом.

## **53\. General Agent Contract**

Все агенты Journal-Yuga должны подчиняться общему контракту.

### **53.1. Input Contract**

Любой агент принимает только typed input. Если ему передали сырой текст, он должен быть либо Source, либо ManuscriptModel, либо EvidenceItem, либо user answer, либо явно обозначенный raw provisional input.

Минимальные поля input bundle:

operation\_id;  
agent\_role\_id;  
input\_entity\_refs;  
source\_refs;  
context\_pack\_refs;  
user\_constraints;  
evidence\_status\_constraints;  
output\_schema;  
confidence\_policy;  
unknown\_policy.

Агент не должен обращаться к “общему контексту проекта” как к скрытому источнику фактов. Если факт нужен для вывода, он должен находиться в input bundle as Source/Evidence/Entity/UserNote.

### **53.2. Output Contract**

Каждый агент обязан возвращать structured output:

output\_entity\_type;  
output\_entity\_id or provisional\_id;  
field\_values;  
evidence\_refs per important field;  
unknowns;  
assumptions;  
confidence;  
warnings;  
questions\_for\_user;  
quality\_gate\_status;  
trace\_notes.

Свободный prose summary может быть дополнительным, но не единственным результатом.

### **53.3. Evidence Contract**

Каждый агент обязан различать:

FACT\_FROM\_SOURCE;  
VENDOR\_CLAIM;  
CORPUS\_OBSERVATION;  
INFERENCE;  
TACIT\_SIGNAL;  
USER\_NOTE;  
PRIOR\_OUTCOME;  
UNKNOWN;  
INACCESSIBLE;  
STALE;  
CONFLICTING\_EVIDENCE.

Если агент создаёт claim без source/evidence, claim должен быть marked as INFERENCE or UNKNOWN. Если claim важен для decision, но не имеет evidence, агент должен либо запросить source, либо fail to evidence-backed status.

### **53.4. Unknown Policy**

Unknown is not failure. Unknown is a domain state.

Агент должен явно сохранять неизвестные поля и объяснять, почему они важны. Он не должен заполнять неизвестное вероятным common-sense ответом.

Например:

Если abstract есть, но bibliography отсутствует, CitationPlan cannot claim citation ecology.  
Если author guidelines не открыты, ComplianceChecklist cannot be submission-ready.  
Если protected core не задан, RewritePlan cannot classify deep reframe safely.  
Если indexing не проверен, FitAssessment cannot claim Scopus/WoS/VAK status.

### **53.5. Failure and Escalation Contract**

Агент должен fail closed or escalate if:

required input missing;  
evidence insufficient for requested output level;  
source inaccessible;  
output would require hallucinated reference;  
rewrite touches protected core without user acceptance;  
venue identity ambiguous;  
source conflict unresolved;  
policy freshness expired;  
user scenario missing for decision-critical fit.

Escalation outputs:

ask\_user\_question;  
request\_source\_acquisition;  
request\_context\_pack\_build;  
mark\_preliminary;  
fail\_closed;  
handoff\_to\_other\_agent.

## **54\. Agent Role: Article Modeler**

### **54.1. Purpose**

Article Modeler строит ArticleModel из manuscript-а, draft-а, abstract-а, WhiteCrow Field, Litops ContextPack or user brief. Его задача — реконструировать publication-facing структуру текста: не “пересказать статью”, а выделить, чем она является как возможная академическая публикация.

### **54.2. Inputs**

ManuscriptModel;  
raw article source;  
abstract;  
WhiteCrow FieldModelReference;  
Field Text;  
Litops ContextPack;  
bibliography;  
user brief;  
prior ArticleModel;  
protected core if available.

### **54.3. Outputs**

ArticleModel;  
ArticleModel unknowns;  
protected core candidate;  
questions for user;  
article stage classification;  
genre/discipline/method/novelty candidates.

### **54.4. Required Extraction**

Article Modeler должен извлечь или пометить unknown:

problem\_statement;  
research\_question;  
object\_of\_inquiry;  
core\_claims;  
secondary\_claims;  
argument\_structure;  
method\_status;  
genre\_current;  
disciplinary\_register\_current;  
novelty\_mode;  
theoretical\_shoulders;  
opponents\_or\_contrasts;  
key\_terms;  
citation\_ecology\_current;  
audience\_current;  
protected\_core;  
mutable\_zones;  
high\_risk\_zones.

### **54.5. Forbidden Behavior**

Article Modeler не должен:

выдумывать тезис, если текст его не содержит;  
делать вид, что abstract даёт полную модель статьи;  
заменять ArticleModel обычным summary;  
приписывать метод, если метод не обнаружен;  
выдумывать bibliography/citation ecology;  
менять protected core;  
решать, куда статью подавать.

### **54.6. When to Ask User**

Article Modeler задаёт вопросы, если:

неясен protected core;  
жанр неоднозначен;  
article stage unclear;  
method implicit;  
цель публикации не видна;  
есть несколько возможных article variants;  
текст слишком сырой для ArticleModel.

### **54.7. MVP Behavior**

В MVP Article Modeler должен уметь построить preliminary ArticleModel из abstract/full manuscript and ask 1–3 missing questions. Он не обязан полностью реконструировать field-level structure без WhiteCrow input.

## **55\. Agent Role: Scenario Interviewer**

### **55.1. Purpose**

Scenario Interviewer строит SubmissionScenario. Он не должен вести длинное интервью ради интервью. Его задача — получить ровно те пользовательские ограничения, без которых FitAssessment будет ложным или слишком общим.

### **55.2. Inputs**

ArticleModel;  
user request;  
project defaults;  
target venue or venue pool;  
WhiteCrow constraints;  
deadline/context notes.

### **55.3. Outputs**

SubmissionScenario;  
missing scenario questions;  
risk tolerance profile;  
rewrite/reframe boundary;  
fallback policy.

### **55.4. Required Fields**

goal;  
target\_indexing;  
prestige\_vs\_speed;  
APC constraints;  
deadline;  
language;  
rewrite\_depth\_allowed;  
reframe\_allowed;  
field\_core\_preservation\_priority;  
fallback\_allowed;  
article\_type preference;  
risk\_tolerance.

### **55.5. Forbidden Behavior**

Scenario Interviewer не должен:

предполагать, что пользователь всегда хочет Q1/Q2;  
предполагать, что APC допустим;  
предполагать, что глубокая переделка разрешена;  
подменять пользовательскую цель метриками;  
принуждать пользователя к публикационной карьере вместо задачи текста.

### **55.6. MVP Behavior**

В MVP должен быть short scenario interview: 5–7 вопросов максимум. Если пользователь не отвечает, поля остаются UNKNOWN and FitAssessment is preliminary.

## **56\. Agent Role: Venue Profiler**

### **56.1. Purpose**

Venue Profiler строит VenueModel, JournalModel, PublicationRegimeModel and related venue objects from sources. Его работа — не “описать журнал”, а создать доказательную модель публикационного контейнера.

### **56.2. Inputs**

venue name;  
venue URL;  
ISSN;  
publisher page;  
special issue URL;  
CFP URL;  
Litops Sources;  
API metadata;  
user tacit notes;  
prior VenueModel.

### **56.3. Outputs**

VenueModel;  
JournalModel;  
SectionModel optional;  
IssueModel/SpecialIssueModel/ResearchTopicModel optional;  
PublicationRegimeModel;  
VenueContextPack;  
source acquisition gaps;  
unknowns;  
warnings.

### **56.4. Required Extraction**

canonical\_name;  
venue\_type;  
publisher\_or\_owner;  
official URLs;  
scope\_summary;  
subject areas;  
article types;  
language policy;  
submission info;  
author guidelines refs;  
policy refs;  
publication regime;  
indexing/metrics claims with status;  
unknowns and inaccessible fields.

### **56.5. Forbidden Behavior**

Venue Profiler не должен:

строить VenueModel из памяти;  
считать author guidelines всей моделью журнала;  
смешивать journal homepage and special issue;  
утверждать indexing/quartile без источника;  
выдавать publisher marketing as verified fact;  
делать выводы о hidden editor preferences без tacit/prior evidence;  
считать inaccessible fields absent.

### **56.6. Evidence Requirements**

Every VenueModel important field must have:

source ref;  
evidence status;  
retrieved date;  
confidence;  
unknown if missing.

### **56.7. MVP Behavior**

В MVP Venue Profiler строит light profile from manually provided URL(s) and OpenAlex/Crossref where available. Deep corpus analysis is later.

## **57\. Agent Role: Corpus Miner**

### **57.1. Purpose**

Corpus Miner анализирует PublishedArticleCorpus and produces PublishedArticlePatterns. Его задача — показать фактические жанровые, структурные and citation patterns of venue corpus.

### **57.2. Inputs**

PublishedArticleCorpus;  
article metadata;  
abstracts;  
full texts if available;  
section or special issue scope;  
corpus selection strategy.

### **57.3. Outputs**

PublishedArticlePatterns;  
corpus summary;  
representativeness warning;  
pattern evidence refs;  
inputs for CitationExpectationProfile.

### **57.4. Pattern Types**

abstract\_structure;  
introduction moves;  
literature review style;  
method presence;  
empirical material;  
case usage;  
argument form;  
citation density;  
reference age distribution;  
theory usage;  
section structure;  
conclusion style;  
article length;  
novelty claim form;  
disciplinary vocabulary.

### **57.5. Forbidden Behavior**

Corpus Miner не должен:

делать выводы из 2–3 статей как из репрезентативного корпуса;  
не указывать selection strategy;  
смешивать recent, most cited, user-uploaded and special issue corpus;  
выводить редакционную политику напрямую из корпуса;  
игнорировать humanities-specific genre variation.

### **57.6. MVP Behavior**

В MVP Corpus Miner может быть stub or small-corpus mode. Он обязан выдавать representativeness warning. Full mode later: 20–50 articles.

## **58\. Agent Role: Citation Ecologist**

### **58.1. Purpose**

Citation Ecologist строит CitationExpectationProfile and CitationPlan. Его задача — не “добавить свежие источники”, а понять, какие citation bridges, field anchors and reference verifications нужны, чтобы статья была распознаваема в выбранном venue/discipline.

### **58.2. Inputs**

ArticleModel;  
current bibliography;  
PublishedArticleCorpus;  
CitationExpectationProfile;  
OpenAlex/Crossref/OpenCitations data;  
venue requirements;  
discipline/field context.

### **58.3. Outputs**

CitationExpectationProfile;  
CitationPlan;  
ReferenceVerificationResult;  
missing bridge categories;  
dangerous padding warnings;  
verified/pending reference candidates.

### **58.4. Required Distinctions**

Citation Ecologist должен различать:

field anchor;  
recent debate marker;  
method reference;  
opponent;  
bridge between traditions;  
venue-local reference;  
empirical context;  
theory background;  
dangerous padding;  
unverified reference;  
unnecessary citation.

### **58.5. Forbidden Behavior**

Citation Ecologist не должен:

выдумывать references;  
рекомендовать несуществующие DOI;  
добавлять citations ради видимости;  
считать unresolved reference fake;  
подменять citation ecology generic recent literature advice;  
делать venue-specific citation claims without corpus/evidence.

### **58.6. MVP Behavior**

В MVP Citation Ecologist может выдавать citation tasks and verify existing DOI-bearing references. Verified new reference recommendations can be later.

## **59\. Agent Role: Fit Assessor**

### **59.1. Purpose**

Fit Assessor строит FitAssessment by comparing ArticleModel × VenueModel × SubmissionScenario. Он не должен подбирать журнал. Он должен показать структуру совпадений, разрывов, усилий, рисков and strategic value.

### **59.2. Inputs**

ArticleModel;  
VenueModel;  
PublicationRegimeModel;  
SubmissionScenario;  
CitationExpectationProfile optional;  
ComplianceChecklist optional;  
EvidenceItems.

### **59.3. Outputs**

FitAssessment;  
fit axis table;  
unknowns;  
evidence-backed recommendation label;  
handoff to Mismatch Mapper.

### **59.4. Fit Axes**

topic\_fit;  
disciplinary\_fit;  
genre\_fit;  
argument\_form\_fit;  
method\_fit;  
citation\_ecology\_fit;  
novelty\_mode\_fit;  
language\_register\_fit;  
audience\_fit;  
formal\_compliance\_fit;  
author\_eligibility\_fit;  
publication\_regime\_fit;  
timeline\_fit;  
APC\_policy\_fit;  
strategic\_value;  
field\_core\_preservation\_risk.

### **59.5. Forbidden Behavior**

Fit Assessor не должен:

выдавать один black-box score;  
claim fit without evidence;  
claim no fit because data unknown;  
hide unknowns;  
ignore SubmissionScenario;  
ignore protected core;  
rank multiple venues without comparable evidence;  
claim acceptance probability.

### **59.6. MVP Behavior**

MVP FitAssessment is qualitative, multi-axis, one article × one venue. It can produce labels: strong\_candidate, possible, possible\_but\_costly, poor\_fit, high\_risk, not\_enough\_data.

## **60\. Agent Role: Mismatch Mapper**

### **60.1. Purpose**

Mismatch Mapper превращает weak fit axes into concrete mismatches that can be acted upon. Он отвечает за переход от diagnosis to action.

### **60.2. Inputs**

FitAssessment;  
ArticleModel;  
VenueModel;  
SubmissionScenario;  
EvidenceItems.

### **60.3. Outputs**

MismatchMap;  
critical mismatches;  
actionable mismatches;  
non-actionable mismatches;  
unknown-driven mismatches.

### **60.4. Mismatch Types**

topic mismatch;  
discipline mismatch;  
genre mismatch;  
argument mismatch;  
method mismatch;  
novelty mismatch;  
citation mismatch;  
formal mismatch;  
policy mismatch;  
language/register mismatch;  
publication regime mismatch;  
timeline mismatch;  
field-core mismatch;  
author eligibility mismatch.

### **60.5. Forbidden Behavior**

Mismatch Mapper не должен:

превращать каждый mismatch в rewrite task;  
скрывать non-actionable mismatch;  
считать reframe обычной правкой;  
не указывать field-core impact;  
генерировать действия без evidence.

### **60.6. MVP Behavior**

MVP MismatchMap can be structured table. Later visual graph.

## **61\. Agent Role: Rewrite Planner**

### **61.1. Purpose**

Rewrite Planner создаёт RewritePlan and ReframePlan. Он должен предлагать публикационную адаптацию, но не уничтожать смысловое ядро.

### **61.2. Inputs**

MismatchMap;  
ArticleModel;  
ManuscriptModel;  
ProtectedCore;  
SubmissionScenario;  
VenueModel.

### **61.3. Outputs**

RewritePlan;  
ReframePlan optional;  
WhiteCrow patch candidates optional;  
field-core impact classification;  
user decisions required.

### **61.4. Rewrite vs Reframe**

Rewrite changes expression and structure while preserving article identity.

Reframe changes object, discipline, novelty, method, genre, audience or theoretical positioning. Reframe may require ArticleVariant.

### **61.5. Forbidden Behavior**

Rewrite Planner не должен:

автоматически переписывать full manuscript;  
touch protected core silently;  
turn conceptual article into empirical article without explicit user decision;  
change theoretical stance as style edit;  
invent method section;  
invent citations;  
erase author voice where voice is protected.

### **61.6. MVP Behavior**

MVP outputs action plan, not full rewrite. It may draft local examples for title/abstract only if user requests and evidence supports.

## **62\. Agent Role: Compliance Auditor**

### **62.1. Purpose**

Compliance Auditor строит ComplianceChecklist and checks formal/policy/guideline requirements.

### **62.2. Inputs**

VenueModel;  
PublicationRegimeModel;  
author guidelines;  
policy pages;  
ArticleModel;  
ManuscriptModel;  
SubmissionScenario.

### **62.3. Outputs**

ComplianceChecklist;  
missing requirements;  
blocking requirements;  
policy unknowns;  
inputs to RiskReport and SubmissionPack.

### **62.4. Requirement Categories**

metadata;  
article type;  
word count;  
abstract;  
keywords;  
references;  
figures/tables;  
supplementary files;  
ethics;  
COI;  
funding;  
data availability;  
AI disclosure;  
authorship/CRediT;  
reporting guideline;  
cover letter;  
reviewer suggestions;  
submission portal fields.

### **62.5. Forbidden Behavior**

Compliance Auditor не должен:

create fake journal requirements;  
treat generic checklist as venue-specific;  
mark submission ready with stale guidelines;  
ignore unknown policies;  
claim plagiarism/AI detector certainty;  
give legal advice as fact.

### **62.6. MVP Behavior**

MVP extracts/checks requirements from available author guidelines and marks missing/unknown.

## **63\. Agent Role: Risk Officer**

### **63.1. Purpose**

Risk Officer создаёт RiskReport. Он должен показывать publication risks and mitigation paths.

### **63.2. Inputs**

FitAssessment;  
MismatchMap;  
ComplianceChecklist;  
CitationPlan;  
SubmissionScenario;  
VenueModel;  
ArticleModel.

### **63.3. Outputs**

RiskReport;  
blocking risks;  
warnings;  
mitigation actions;  
user risk decisions.

### **63.4. Risk Classes**

formal\_noncompliance;  
scope\_mismatch;  
method\_weakness;  
citation\_gap;  
reference\_validity;  
plagiarism\_self\_plagiarism;  
AI\_disclosure;  
authorship\_CRediT;  
COI\_funding;  
data\_availability;  
ethics\_approval;  
APC\_predatory;  
indexing\_uncertainty;  
author\_eligibility;  
timeline;  
reviewer\_misunderstanding;  
field\_core\_loss;  
tacit\_signal\_uncertainty.

### **63.5. Forbidden Behavior**

Risk Officer не должен:

make legal conclusions;  
overstate AI/plagiarism detection;  
invent acceptance probabilities;  
treat weak signals as evidence;  
ignore user risk tolerance.

### **63.6. MVP Behavior**

MVP RiskReport identifies blocking/warning risks and asks user for acceptance where needed.

## **64\. Agent Role: Submission Pack Builder**

### **64.1. Purpose**

Submission Pack Builder turns analysis into operational submission package.

### **64.2. Inputs**

ManuscriptModel;  
VenueModel;  
SubmissionScenario;  
ComplianceChecklist;  
RiskReport;  
CitationPlan;  
RewritePlan status.

### **64.3. Outputs**

SubmissionPack;  
metadata table;  
missing items;  
cover letter skeleton;  
portal field mapping if known;  
ready status.

### **64.4. Forbidden Behavior**

Submission Pack Builder не должен:

mark ready if blockers unresolved;  
fabricate statements;  
invent author metadata;  
submit automatically in MVP;  
finalize cover letter without user acceptance;  
hide missing files.

### **64.5. MVP Behavior**

MVP creates draft pack with not\_ready / needs\_user\_input status.

## **65\. Agent Role: Reviewer Simulator**

### **65.1. Purpose**

Reviewer Simulator is a controlled pre-submission risk analysis role. It is not a real reviewer and not an editorial oracle.

### **65.2. Inputs**

ArticleModel;  
VenueModel;  
FitAssessment;  
MismatchMap;  
RiskReport;  
PublishedArticlePatterns optional.

### **65.3. Outputs**

possible objections;  
likely misunderstandings;  
missing evidence;  
reviewer-risk notes;  
pre-submission improvement tasks.

### **65.4. Forbidden Behavior**

Reviewer Simulator не должен:

pretend to be actual reviewer;  
predict acceptance;  
invent reviewer identities;  
claim editorial knowledge;  
generate fake peer review;  
override evidence-based FitAssessment.

### **65.5. MVP Behavior**

Not implemented in MVP. Schema and prohibition only. Build later.

## **66\. Agent Role: Review Outcome Analyst**

### **66.1. Purpose**

Review Outcome Analyst processes actual review/editorial feedback and creates ReviewOutcome, RevisionPlan and RebuttalOutline.

### **66.2. Inputs**

review letter source;  
editor decision;  
reviewer reports;  
submitted manuscript;  
prior FitAssessment;  
SubmissionPack.

### **66.3. Outputs**

ReviewOutcome;  
issue map;  
RevisionPlan;  
RebuttalOutline;  
VenueMemory update candidates.

### **66.4. Forbidden Behavior**

Review Outcome Analyst не должен:

write dishonest rebuttal;  
promise acceptance after revision;  
erase reviewer criticism;  
misclassify fatal mismatch as minor style issue;  
invent changes not made.

### **66.5. MVP Behavior**

Build later after SubmissionPack.

## **67\. Agent Role: Venue Memory Keeper**

### **67.1. Purpose**

Venue Memory Keeper updates VenueMemory from sources, tacit signals, prior outcomes and refreshed profiles.

### **67.2. Inputs**

VenueModel;  
ReviewOutcome;  
TacitVenueSignal;  
source refresh results;  
prior fit/submission outcomes.

### **67.3. Outputs**

VenueMemory;  
stale signal warnings;  
future fit priors;  
privacy flags.

### **67.4. Forbidden Behavior**

Venue Memory Keeper не должен:

generalize one outcome into universal rule;  
store sensitive notes without privacy status;  
promote tacit signals to facts;  
hide source date.

### **67.5. MVP Behavior**

MVP can store tacit notes and prior outcomes with evidence status. Learning/calibration later.

## **68\. Agent Role: Evidence Auditor**

### **68.1. Purpose**

Evidence Auditor is the guardrail role. It checks whether outputs have enough evidence to be treated as evidence-backed.

### **68.2. Inputs**

Any Journal-Yuga output;  
EvidenceItems;  
ContextPacks;  
SourceSnapshots;  
operation traces.

### **68.3. Outputs**

evidence\_coverage\_report;  
unsupported\_claims;  
stale\_source\_warnings;  
claim\_status\_errors;  
quality\_gate\_result;  
blocked\_output flag.

### **68.4. Checks**

Every strong claim has source.  
Every venue fact has source status.  
Every vendor claim is marked.  
Every inference is marked.  
Every tacit signal is marked.  
Unknowns are not converted into no.  
Stale sources are flagged.  
Fit axes have evidence refs.  
Citation suggestions are verified or pending.  
Submission ready status has fresh guidelines.  
Protected core changes require user acceptance.

### **68.5. Authority**

Evidence Auditor can downgrade output:

evidence\_backed → preliminary;  
submission\_ready → needs\_refresh;  
strong\_candidate → possible\_with\_unknowns;  
verified → vendor\_claim / inference / unknown.

Evidence Auditor can block final report if evidence requirements fail.

## **69\. Prompt Families**

Prompt families are internal executable patterns. They must be versioned and tied to agent roles. They are not user-facing prompts.

Each prompt family must define:

family\_id;  
agent\_role\_id;  
purpose;  
input schema;  
output schema;  
required evidence refs;  
allowed reasoning scope;  
forbidden claims;  
unknown handling;  
validator;  
examples;  
version;  
tests.

### **69.1. Article Modeling Prompt Family**

Purpose:

extract ArticleModel from manuscript/abstract/field.

Inputs:

text/source refs;  
field refs;  
user brief;  
desired output level.

Outputs:

ArticleModel fields;  
unknowns;  
protected core candidate;  
questions.

Validators:

no invented bibliography;  
no unsupported method;  
must mark abstract\_only;  
must separate summary from ArticleModel.

### **69.2. Scenario Interview Prompt Family**

Purpose:

generate minimal user questions and build SubmissionScenario.

Outputs:

questions;  
scenario fields;  
unknowns;  
default risk notes.

Validators:

no unnecessary long interview;  
no assumed APC/indexing/rewrite tolerance.

### **69.3. Venue Fact Extraction Prompt Family**

Purpose:

extract venue facts from official pages/snapshots.

Outputs:

VenueModel fields;  
EvidenceItems;  
unknowns.

Validators:

source refs required;  
vendor claims marked;  
no memory facts;  
no invisible data.

### **69.4. Publication Regime Classification Prompt Family**

Purpose:

classify venue/issue/CFP into publication regime.

Outputs:

PublicationRegimeModel;  
regime confidence;  
evidence.

Validators:

do not collapse special issue/research topic into generic journal;  
unknown if evidence weak.

### **69.5. Corpus Pattern Mining Prompt Family**

Purpose:

extract article patterns from corpus.

Outputs:

PublishedArticlePatterns;  
representativeness warning;  
examples.

Validators:

selection strategy required;  
small corpus warning required;  
no editorial preference claims from weak corpus.

### **69.6. Citation Ecology Prompt Family**

Purpose:

compare ArticleModel bibliography with venue/field citation expectations.

Outputs:

CitationPlan;  
missing categories;  
verification tasks;  
padding warnings.

Validators:

no fake references;  
reference candidates must be verified or pending;  
unresolved not fake.

### **69.7. Fit Assessment Prompt Family**

Purpose:

compare ArticleModel × VenueModel × SubmissionScenario.

Outputs:

FitAssessment multi-axis table.

Validators:

no single score;  
every axis has evidence or unknown;  
SubmissionScenario required;  
protected core risk included.

### **69.8. Mismatch Mapping Prompt Family**

Purpose:

turn weak fit axes into actionable mismatches.

Outputs:

MismatchMap.

Validators:

mismatch must include article side, venue side, evidence, severity, possible action.

### **69.9. Rewrite Planning Prompt Family**

Purpose:

generate RewritePlan/ReframePlan.

Outputs:

change list;  
field-core impact;  
user acceptance requirements.

Validators:

no full rewrite by default;  
core-touching changes flagged;  
no invented method/citation.

### **69.10. Risk Reporting Prompt Family**

Purpose:

generate RiskReport.

Outputs:

risk items;  
severity;  
mitigation;  
evidence.

Validators:

no legal certainty;  
no acceptance prediction;  
AI/plagiarism detector caveats.

### **69.11. Compliance Checklist Prompt Family**

Purpose:

derive/check requirements.

Outputs:

ComplianceChecklist.

Validators:

venue-specific only if source exists;  
generic items marked generic;  
freshness gate.

### **69.12. Submission Pack Prompt Family**

Purpose:

assemble operational submission pack.

Outputs:

SubmissionPack;  
missing items;  
metadata;  
cover letter skeleton.

Validators:

not ready if blockers;  
no fabricated statements;  
user acceptance required.

### **69.13. Review Outcome Prompt Family**

Purpose:

analyze actual review feedback.

Outputs:

ReviewOutcome;  
RevisionPlan;  
RebuttalOutline.

Validators:

no dishonest rebuttal;  
no acceptance guarantee;  
map comments to actions.

### **69.14. Evidence Audit Prompt Family**

Purpose:

audit output quality.

Outputs:

evidence coverage report;  
unsupported claims;  
downgrades;  
blocked status.

Validators:

strict.

## **70\. Orchestration Rules**

Journal-Yuga orchestration should be pipeline-driven.

Pipeline decides which agents run and in what order. Agents do not self-orchestrate freely.

Direct Manuscript × One Venue orchestration:

Article Modeler;  
Venue Profiler;  
Scenario Interviewer;  
Fit Assessor;  
Evidence Auditor;  
Mismatch Mapper;  
Rewrite Planner;  
Citation Ecologist;  
Risk Officer;  
Compliance Auditor;  
Submission Pack Builder optional;  
Evidence Auditor final.

Venue Deep Profile orchestration:

Venue Profiler;  
Corpus Miner optional;  
Citation Ecologist optional;  
Compliance Auditor;  
Evidence Auditor.

Pool Discovery orchestration:

Article Modeler;  
Scenario Interviewer;  
Venue Profiler light mode;  
Fit Assessor screening mode;  
Evidence Auditor.

Review Loop orchestration:

Review Outcome Analyst;  
Fit Assessor comparison mode;  
Rewrite Planner;  
Risk Officer;  
Venue Memory Keeper;  
Evidence Auditor.

No agent should skip Evidence Auditor before user-facing final output.

## **71\. Agent Memory Rules**

Agents do not have independent long-term memory. Long-term memory belongs to registries, Litops sources, ContextPacks, WhiteCrow objects and VenueMemory. Agent memory is operation-local.

Allowed memory:

current input bundle;  
entity refs;  
source/evidence refs;  
operation trace;  
explicit user answers;  
registered VenueMemory.

Forbidden memory:

unstated model knowledge as fact;  
prior chat content not registered as source;  
hidden assumptions;  
old unsupported conclusions;  
unversioned prompt behavior.

## **72\. Testing Prompt Families**

Every prompt family should have tests.

Test types:

schema conformance;  
unknown handling;  
evidence requirement;  
forbidden claim detection;  
source status preservation;  
protected core handling;  
staleness warning;  
small corpus warning;  
citation hallucination prevention;  
generic checklist vs venue-specific checklist separation.

Fixtures:

abstract-only article;  
full manuscript with bibliography;  
venue page with guidelines;  
venue page without guidelines;  
special issue CFP;  
small article corpus;  
review letter;  
conflicting source claims;  
stale guidelines;  
tacit user note.

## **73\. Agent Architecture MVP Scope**

MVP-0:

define agent roles and prompt family skeletons;  
define schemas;  
no complex orchestration.

MVP-1:

Article Modeler;  
Venue Profiler light;  
Scenario Interviewer;  
Fit Assessor;  
Mismatch Mapper;  
Rewrite Planner action-plan mode;  
Risk Officer;  
Compliance Auditor simple;  
Evidence Auditor.

MVP-2:

Citation Ecologist basic;  
Submission Pack Builder draft.

MVP-3:

Corpus Miner small corpus;  
Venue Memory Keeper basic.

MVP-4:

Review Outcome Analyst;  
Reviewer Simulator risk mode.

## **74\. Wave 6 Closure**

This wave defines Journal-Yuga as a multi-role evidence-governed system. Agents are not decorative personas; they are bounded transformation roles. Prompt families are not user prompts; they are versioned internal procedures with schemas and validators. The central architectural rule is that no major output should be produced by a single unchecked LLM call. ArticleModel, VenueModel, FitAssessment, MismatchMap, RewritePlan, CitationPlan, RiskReport and SubmissionPack each require responsible agent roles, evidence gates and traceable output.

The next wave should define UI/UX surfaces and human interaction model: how users see ArticleModel, VenueProfile, Fit/Effort/Risk matrix, MismatchMap, RewritePlan, CitationPlan, SubmissionPack, evidence, unknowns, warnings, decisions, Telegram intake and web workspace without collapsing the system into a chat answer.

# **JOURNAL\_YUGA\_TECHNICAL\_SPEC\_FOR\_CLAUDE\_v0\_1**

## **Волна 7\. UI/UX, рабочие поверхности, evidence panels, human decisions, Telegram layer and interaction model**

## **75\. Purpose of UI/UX Layer**

UI/UX Journal-Yuga должен быть построен не вокруг “ответа ИИ”, а вокруг управляемой публикационной работы. Пользователь должен видеть не только финальную рекомендацию, но и структуру ситуации: что система поняла о статье, что известно о venue, какие источники были использованы, какие поля неизвестны, где есть конфликт данных, какие mismatch-и выявлены, какие правки предлагаются, какие правки затрагивают protected core, какие citation bridges нужны, какие submission requirements не закрыты, какие риски блокируют подачу, какие решения должен принять пользователь.

Интерфейс не должен скрывать сложность, но должен распределять её по правильным местам. Пользователь не должен тратить когнитивные усилия на понимание внутренней файловой структуры, registry, source ids or adapter outputs. Он должен видеть publication situation as a navigable workspace: Article side, Venue side, Scenario side, Fit/Mismatch side, Adaptation side, Submission side, Evidence side. Глубина должна раскрываться по мере необходимости.

Journal-Yuga должен иметь несколько интерфейсных поверхностей:

1. Web workspace — основная рабочая поверхность для анализа, сравнения, акцепта правок, evidence inspection and submission preparation.  
2. Vault / Obsidian projection — human-readable archive and navigation layer.  
3. Telegram intake/control layer — лёгкий вход, быстрые команды, загрузка материалов, статусы, напоминания, короткие действия.  
4. CLI/API layer — developer and automation surface.  
5. External document bridge — Google Docs/DOCX/Markdown/LaTeX integration for manuscript work.  
6. Report/export layer — PDF/Markdown/DOCX/HTML artifacts for sharing and review.

Главный принцип: Chat is allowed, but chat is not the system. LLM conversation may help clarify scenario or explain results, but canonical state must live in objects and screens.

## **76\. UI Information Architecture**

Рабочая область Journal-Yuga должна быть организована вокруг пяти центральных пространств:

### **76.1. Article Space**

Article Space показывает, что система знает о тексте как потенциальной статье.

В нём должны быть видны:

ArticleModel;  
ManuscriptModel;  
Article stage;  
problem statement;  
research question;  
object;  
core claims;  
argument structure;  
genre;  
disciplinary register;  
method status;  
novelty mode;  
current citation ecology;  
protected core;  
mutable zones;  
unknowns;  
source refs;  
confidence;  
article variants if any.

Article Space должен позволять пользователю исправить модель статьи. Если система неверно поняла тезис, жанр, объект or protected core, пользователь должен иметь возможность отредактировать не только текст, но и модель. Это принципиально: плохой ArticleModel разрушит все дальнейшие FitAssessment and RewritePlan.

### **76.2. Venue Space**

Venue Space показывает, что система знает о publication container.

В нём должны быть видны:

VenueModel;  
JournalModel;  
PublicationRegimeModel;  
sections/article types;  
aims/scope;  
author guidelines;  
policies;  
submission info;  
indexing/metrics claims;  
editorial board profile;  
published article corpus;  
published article patterns;  
citation expectation profile;  
special issues/research topics;  
CFPs;  
tacit signals;  
prior outcomes;  
source freshness;  
unknowns;  
conflicts.

Venue Space должен показывать уровни уверенности. Например, formal requirements extracted from official guidelines have higher status than corpus inference; editorial board composition is visible data, not a hidden preference; user note is tacit signal; indexing from publisher page is vendor claim unless independently verified.

### **76.3. Scenario Space**

Scenario Space показывает, зачем пользователь публикуется и какие ограничения важны.

В нём должны быть видны:

submission goal;  
target indexing;  
prestige/speed tradeoff;  
APC constraints;  
deadline;  
language;  
rewrite depth allowed;  
reframe allowed;  
field-core preservation priority;  
fallback policy;  
risk tolerance;  
target audience;  
article type preference;  
unanswered questions.

Scenario Space должен быть editable. FitAssessment must update if user changes scenario. Например, журнал может быть хорошим fit по теме, но плохим по срокам; хороший для prestige, плохой для speed; допустимый при major rewrite, недопустимый if protected core is strict.

### **76.4. Fit and Adaptation Space**

Fit and Adaptation Space является центральной рабочей поверхностью.

В нём должны быть видны:

FitAssessment multi-axis matrix;  
MismatchMap;  
RewritePlan;  
ReframePlan;  
CitationPlan;  
RiskReport;  
ComplianceChecklist;  
SubmissionPack readiness;  
user decisions;  
accepted/rejected actions;  
WhiteCrow patch candidates.

Здесь пользователь должен видеть не “подходит / не подходит”, а карту напряжений: какие оси сильные, какие слабые, какие можно исправить, какие требуют deep reframe, какие опасны, какие неизвестны из\-за нехватки источников.

### **76.5. Evidence Space**

Evidence Space должен быть доступен из любого другого пространства. Он показывает источники и доказательную базу.

В нём должны быть видны:

ContextPack;  
Source list;  
EvidenceItems;  
SourceSnapshots;  
adapter results;  
claim status;  
retrieved\_at;  
staleness;  
conflicting evidence;  
inaccessible sources;  
unknown fields;  
operation traces.

Evidence Space — это защита от превращения Journal-Yuga в “модель сказала”. Любой сильный вывод должен быть кликабелен до источника or evidence item.

## **77\. Main Screens**

### **77.1. Project / Workspace Dashboard**

Dashboard показывает все активные publication projects.

Минимальные элементы:

project title;  
current article/manuscript;  
active venues;  
current pipeline stage;  
last operation;  
next action;  
blocking issues;  
pending user decisions;  
submission deadlines;  
stale source warnings;  
recent artifacts.

Пользователь должен сразу понимать, где застряла работа: нужен текст, нужен URL журнала, нужно подтвердить protected core, нужно обновить guidelines, нужно принять rewrite, нужно добавить author metadata, нужно проверить references, нужно ответить на reviewer comments.

Dashboard не должен показывать внутренние IDs как основной язык, но должен позволять открыть technical details.

### **77.2. Intake Screen**

Intake Screen принимает материалы и запускает правильный pipeline.

Допустимые входы:

manuscript file;  
abstract;  
draft text;  
journal URL;  
journal name;  
special issue URL;  
CFP;  
review letter;  
zip with articles;  
Litops source\_id;  
WhiteCrow manuscript/field reference;  
user note;  
bibliography file;  
Google Doc link.

Intake must ask: “what are you trying to do?” but not through a large form. It should detect likely intent and ask minimal confirmation.

Possible intent classes:

profile this venue;  
check this manuscript against this venue;  
find possible venues;  
prepare submission pack;  
analyze review letter;  
add tacit note;  
build corpus;  
verify references;  
compare venue pool.

Intake output:

created sources;  
detected pipeline;  
missing required inputs;  
initial status;  
job id.

If user uploads a zip of 20 PDFs and says “these are articles on our topic”, system must not blindly treat it as representative venue corpus. It should ask or infer role: article corpus for field, journal corpus, background sources, user evidence pack, bibliography support, or mixed intake. The selection strategy must be recorded.

### **77.3. ArticleModel Inspector**

ArticleModel Inspector is an editable structured view of ArticleModel.

Sections:

Basic identity:

title;  
abstract;  
language;  
article stage;  
source refs.

Conceptual structure:

problem;  
object;  
research question;  
core claims;  
argument structure;  
novelty mode.

Scholarly positioning:

discipline;  
genre;  
method status;  
theoretical shoulders;  
opponents;  
audience;  
citation ecology.

Protection and change:

protected core;  
mutable zones;  
high-risk zones;  
possible variants.

Unknowns:

missing bibliography;  
unclear method;  
unclear genre;  
unclear scenario;  
unconfirmed protected core.

User actions:

confirm ArticleModel;  
edit field;  
mark protected core;  
split into article variants;  
send to WhiteCrow;  
run fit against venue;  
request missing-question interview.

The screen must show confidence per section. For example, title and abstract may be verified from manuscript; novelty mode may be inferred; theoretical shoulders may be unknown; citation ecology may be unavailable.

### **77.4. VenueProfile Screen**

VenueProfile Screen shows VenueModel as layered publication container.

Sections:

Identity:

canonical name;  
aliases;  
publisher;  
ISSN;  
URL;  
venue type;  
publication regime.

Formal layer:

aims/scope;  
author guidelines;  
article types;  
word count;  
abstract;  
keywords;  
references;  
format;  
language;  
submission route.

Policy layer:

OA/APC;  
copyright;  
preprint;  
AI disclosure;  
ethics;  
COI;  
funding;  
data availability;  
authorship/CRediT.

Surface layer:

recent articles;  
most read/cited/trending if available;  
issue structure;  
special issues;  
research topics;  
CFPs;  
deadlines.

People layer:

editorial board;  
guest editors;  
affiliations;  
visible disciplinary spread.

Corpus layer:

corpus selection;  
article count;  
time range;  
patterns;  
limitations.

Citation layer:

citation expectations;  
field anchors;  
reference count range;  
recent debate markers;  
citation gaps.

Tacit and memory layer:

user notes;  
prior outcomes;  
tacit signals;  
privacy markers;  
confidence.

Evidence layer:

source list;  
freshness;  
inaccessible sources;  
conflicts.

User actions:

refresh sources;  
add source;  
add tacit note;  
build corpus;  
run fit;  
compare with another venue;  
create submission pack;  
mark stale;  
export profile.

### **77.5. Venue Comparison Matrix**

Venue Comparison Matrix supports journal pool and shortlisted venues. It must avoid false precision.

Rows:

candidate venues.

Columns:

topic fit preliminary;  
discipline;  
genre;  
publication regime;  
language;  
indexing verified/unknown;  
OA/APC;  
article types;  
deadline;  
guidelines available;  
corpus available;  
citation profile available;  
effort;  
risk;  
strategic value;  
evidence level;  
unknown count;  
next action.

Cell values should use qualitative states and evidence statuses, not hidden ranking scores.

Recommended labels:

strong;  
possible;  
weak;  
bad;  
unknown;  
not\_checked;  
vendor\_claim;  
inaccessible;  
needs\_deep\_profile.

The matrix should separate:

light screening;  
deep profile;  
evidence-backed fit.

A venue should not appear above another only because it has more accessible metadata. Evidence coverage and actual fit must be distinguished.

User actions:

select 3–5 venues for deep profile;  
exclude venue;  
mark as fallback;  
request missing source acquisition;  
compare publication regimes;  
export shortlist.

### **77.6. Fit / Effort / Risk Matrix**

This is the central decision screen for one article × one venue.

Rows or cards:

topic fit;  
disciplinary fit;  
genre fit;  
argument fit;  
method fit;  
novelty fit;  
citation ecology fit;  
language/register fit;  
formal compliance;  
publication regime;  
author eligibility;  
timeline;  
APC/policy;  
field-core preservation;  
strategic value.

Each axis must show:

assessment label;  
evidence status;  
source refs;  
confidence;  
unknowns;  
related mismatches;  
possible actions;  
effort;  
risk.

The screen must not reduce this to one number. It may show summary label:

strong candidate;  
possible;  
possible but costly;  
poor fit;  
high risk;  
not enough data.

But the label must be visually subordinate to the matrix.

User actions:

open evidence;  
accept assessment;  
challenge assessment;  
mark unknown as acceptable;  
request more sources;  
generate mismatch map;  
generate rewrite plan;  
create submission pack;  
send to WhiteCrow.

### **77.7. MismatchMap Screen**

MismatchMap turns fit weaknesses into structured work.

Display modes:

table view;  
grouped by axis;  
severity view;  
field-core risk view;  
actionability view;  
graph view later.

Each mismatch card:

mismatch title;  
axis;  
article side;  
venue side;  
severity;  
evidence;  
unknowns;  
possible actions;  
field-core impact;  
requires user decision;  
linked rewrite/citation/compliance tasks.

Mismatch categories:

actionable with light rewrite;  
actionable with citation bridge;  
actionable with compliance fix;  
requires reframe;  
requires new ArticleVariant;  
non-actionable;  
unknown due to missing evidence;  
fatal for this venue.

User actions:

turn into RewritePlan item;  
turn into CitationPlan task;  
turn into Compliance task;  
mark non-actionable;  
accept field-core risk;  
choose alternative venue;  
create ArticleVariant.

### **77.8. RewritePlan Board**

RewritePlan Board should behave like a structured patch planning surface, not a text editor.

Columns or statuses:

proposed;  
needs user review;  
accepted;  
rejected;  
modified;  
sent to WhiteCrow;  
applied;  
archived.

Each change card:

target section/block;  
change type;  
current issue;  
desired direction;  
reason;  
related mismatch;  
evidence;  
estimated effort;  
field-core impact;  
draft text optional;  
user decision required.

Change types:

title adjustment;  
abstract rewrite;  
intro reframe;  
literature review bridge;  
method disclosure;  
argument reordering;  
section addition;  
section removal;  
citation bridge;  
conclusion refocus;  
language/register shift;  
formatting change.

The board must show protected core impact clearly:

core\_preserving;  
core\_touching;  
core\_transforming;  
core\_destroying\_risk;  
unknown\_core\_impact.

User actions:

accept;  
reject;  
modify;  
request example;  
send to WhiteCrow PatchQueue;  
export as comments to external doc;  
create sibling ArticleVariant.

MVP should not automatically rewrite the entire manuscript. It should produce structured plan and local examples only when requested.

### **77.9. CitationPlan Board**

CitationPlan Board shows citation work as tasks, not as hallucinated bibliography.

Sections:

current bibliography status;  
verified references;  
unresolved references;  
missing bridge categories;  
field anchors;  
recent debate markers;  
method references;  
opponents;  
venue-local references;  
dangerous padding warnings;  
formatting/style issues.

Reference candidate card:

title;  
authors;  
year;  
DOI/identifier;  
verification status;  
source;  
role in argument;  
why needed;  
related mismatch;  
risk;  
action.

Verification statuses:

verified;  
pending\_verification;  
unresolved;  
ambiguous;  
not\_needed;  
dangerous\_padding;  
unknown.

User actions:

verify;  
search more;  
reject candidate;  
mark as already cited;  
add to bibliography task;  
send to WhiteCrow;  
export citation tasks.

The interface must make it impossible to confuse “suggested search task” with verified reference.

### **77.10. RiskReport Screen**

RiskReport Screen displays risks by severity and type.

Risk categories:

formal;  
scope;  
method;  
citation;  
reference validity;  
plagiarism/self-plagiarism;  
AI disclosure;  
authorship/CRediT;  
COI/funding;  
data availability;  
ethics;  
APC/predatory;  
indexing;  
author eligibility;  
timeline;  
reviewer misunderstanding;  
field-core loss;  
tacit signal uncertainty.

Each risk card:

risk type;  
severity;  
likelihood if knowable;  
description;  
evidence;  
unknowns;  
mitigation;  
requires user action;  
blocking status;  
related tasks.

Risk screen must avoid false certainty. Especially:

No AI detector certainty.  
No legal certainty.  
No acceptance probability.  
No predatory judgment without evidence.  
No indexing claim without source.

User actions:

accept risk;  
mitigate;  
request source;  
mark not applicable;  
block submission;  
create task.

### **77.11. ComplianceChecklist Screen**

ComplianceChecklist is structured by requirement categories.

Sections:

metadata;  
format;  
article type;  
abstract;  
keywords;  
references;  
figures/tables;  
supplementary files;  
statements;  
ethics;  
COI;  
funding;  
data availability;  
AI disclosure;  
authorship;  
reporting guidelines;  
cover letter;  
submission portal fields.

Each checklist item:

requirement;  
source;  
status;  
blocking level;  
current value;  
missing value;  
user action;  
evidence;  
freshness.

Statuses:

present;  
missing;  
needs\_update;  
not\_applicable;  
unknown;  
blocked;  
requires\_refresh.

The checklist must distinguish generic requirement from venue-specific requirement. Generic items cannot be displayed as if required by venue.

### **77.12. SubmissionPack Workspace**

SubmissionPack Workspace is the operational surface for final preparation.

Sections:

main manuscript;  
supplementary files;  
metadata;  
authors;  
affiliations;  
ORCID;  
funding;  
COI;  
data availability;  
ethics;  
AI disclosure;  
CRediT;  
cover letter;  
suggested reviewers;  
opposed reviewers;  
figures/tables;  
references;  
portal field mapping;  
missing items;  
blocking issues;  
ready status.

Ready statuses:

not\_ready;  
needs\_user\_input;  
needs\_file\_update;  
needs\_reference\_verification;  
needs\_compliance\_check;  
ready\_for\_manual\_submission;  
submitted.

The workspace should never show “ready” if guidelines are stale, required metadata missing, blocking risks unresolved, or source evidence insufficient.

User actions:

fill metadata;  
upload file;  
generate cover letter skeleton;  
refresh guidelines;  
export pack;  
mark submitted;  
attach outcome.

### **77.13. Review / Rebuttal Workspace**

This screen appears after review or editorial feedback.

Sections:

decision summary;  
editor letter;  
reviewer reports;  
issue map;  
relation to prior FitAssessment;  
predicted vs missed issues;  
RevisionPlan;  
RebuttalOutline;  
WhiteCrow patch candidates;  
VenueMemory update.

Review issue card:

comment source;  
issue type;  
summary;  
severity;  
required action;  
accept/resist/clarify;  
target manuscript block;  
evidence needed;  
response draft optional;  
status.

User actions:

accept action;  
resist action;  
send to WhiteCrow;  
generate rebuttal outline;  
update VenueMemory;  
choose resubmit elsewhere.

ReviewerSimulation must never be visually confused with actual ReviewOutcome.

### **77.14. Evidence Panel**

Evidence Panel is not a separate “advanced” page only. It should be accessible from any claim.

Every claim in UI should be clickable or expandable to show:

claim;  
claim status;  
source;  
source type;  
retrieved\_at;  
evidence excerpt or locator;  
confidence;  
staleness;  
related entity;  
used in which outputs;  
conflicts.

Evidence Panel should visually distinguish:

FACT\_FROM\_SOURCE;  
VENDOR\_CLAIM;  
CORPUS\_OBSERVATION;  
INFERENCE;  
TACIT\_SIGNAL;  
USER\_NOTE;  
PRIOR\_OUTCOME;  
UNKNOWN;  
INACCESSIBLE;  
STALE;  
CONFLICTING\_EVIDENCE.

This is crucial for trust. The system should make weak evidence visible, not hide it.

### **77.15. Operation Trace View**

Trace View is primarily for debugging and expert users.

It shows:

pipeline run;  
inputs;  
sources accessed;  
adapters called;  
agents invoked;  
prompts used;  
entities created;  
quality gates;  
errors;  
warnings;  
cost/token estimates;  
user decisions.

Trace View is not mandatory for ordinary user flow but must exist for development, audit and reliability.

## **78\. Human-in-the-loop Model**

Journal-Yuga must preserve human authorship and decision-making. The system can analyze, propose, warn, structure and prepare, but it cannot silently decide publication strategy or transform protected core.

### **78.1. User Decision Points**

Explicit user decision is required for:

confirming ArticleModel;  
confirming protected core;  
selecting target venue;  
accepting SubmissionScenario;  
using tacit signal in assessment;  
accepting field-core-touching rewrite;  
accepting reframe;  
creating ArticleVariant;  
choosing fallback venue;  
marking risk as accepted;  
marking SubmissionPack ready;  
sending patches to WhiteCrow;  
exporting to external doc;  
marking submitted;  
storing prior outcome in VenueMemory.

### **78.2. Decision Presentation**

Every decision should show:

what is being decided;  
why decision is needed;  
evidence;  
consequences;  
risks;  
affected objects;  
reversibility;  
recommended default if any;  
unknowns.

For example, if the system proposes to reframe a philosophical article as STS empirical commentary, it must show which protected core elements are preserved, touched or transformed.

### **78.3. Decision States**

Decision states:

pending;  
accepted;  
rejected;  
modified;  
deferred;  
needs\_more\_evidence;  
superseded.

Decisions should be stored and visible in history.

### **78.4. User Overrides**

User may override system warnings, but override must be recorded. For high-risk overrides, system should ask for confirmation.

Examples:

submit despite stale guidelines;  
use tacit signal;  
accept field-core risk;  
ignore citation gap;  
proceed without verified indexing;  
prepare submission pack with unresolved references.

Override does not erase warning. It changes status to user\_accepted\_risk.

## **79\. Progressive Disclosure and Cognitive Load**

Journal-Yuga is necessarily complex, but UI should not force the user to see all complexity at once.

Three levels of display:

Level 1: Executive surface.

Shows summary label, main risks, next action, missing blockers, top mismatches.

Level 2: Working surface.

Shows matrices, boards, checklists, editable models, decisions.

Level 3: Evidence/audit surface.

Shows sources, evidence statuses, trace, snapshots, conflicts, stale data.

The user should be able to move from Level 1 to Level 3 for any claim. But Level 1 must never hide critical uncertainty.

A good UI pattern:

Summary: “Possible but costly fit.”

Under it:

why;  
top 3 strengths;  
top 3 mismatches;  
blocking risks;  
what can be fixed;  
what would change protected core;  
next recommended action.

Then full matrix and evidence.

## **80\. Telegram Layer**

Telegram is intake and control layer, not primary workspace.

### **80.1. Telegram Use Cases**

Telegram should support:

send manuscript or abstract;  
send journal URL;  
send CFP;  
send review letter;  
add user note;  
ask status;  
create quick venue profile;  
trigger one-target fit;  
approve/reject simple pending action;  
receive reminder;  
receive short summary;  
get link/export to full artifact.

### **80.2. Telegram Commands**

Potential commands:

/status  
/jobs  
/recent  
/get  
/venue\_profile  
/fit  
/pack  
/review  
/add\_note  
/refresh  
/decisions  
/help

Commands should be thin wrappers around pipelines.

### **80.3. Telegram Response Rules**

Telegram responses should be short.

Each response should include:

job id;  
created source/entity ids;  
status;  
next action;  
link/reference to full artifact if available;  
warning if output is preliminary.

Telegram should not dump full FitAssessment unless explicitly requested.

### **80.4. Telegram Intake Ambiguity**

Telegram messages are often ambiguous. If user sends:

“Вот журнал, посмотри”

System should create venue profile job, not assume manuscript fit.

If user sends:

“Вот статья и журнал”

System can start one-target fit.

If user sends:

“Это по нашей теме”

System should ask whether it is background corpus, venue corpus, article input, bibliography support or note.

### **80.5. Telegram Reminder Layer**

Future reminders:

stale guidelines;  
deadline approaching;  
missing metadata;  
reference verification pending;  
submission pack incomplete;  
review response due;  
venue refresh due;  
user decision pending.

This must integrate with Litops attention/proactive loop if available.

## **81\. Vault / Obsidian Projection**

Vault projection is human-readable archive and navigation layer. It should not replace structured registry.

Cards should be markdown files with frontmatter.

### **81.1. ArticleModel Card**

Contains:

title;  
article\_model\_id;  
source refs;  
current stage;  
problem;  
object;  
core claims;  
genre;  
discipline;  
protected core;  
unknowns;  
related venues;  
fit assessments;  
next actions.

### **81.2. VenueModel Card**

Contains:

venue name;  
venue\_model\_id;  
publisher;  
publication regime;  
scope;  
article types;  
guidelines;  
policies;  
corpus summary;  
citation expectations;  
known risks;  
tacit signals;  
source links;  
freshness.

### **81.3. FitAssessment Card**

Contains:

article;  
venue;  
scenario;  
summary label;  
fit matrix;  
top mismatches;  
risk summary;  
rewrite/citation/compliance actions;  
source context;  
user decisions.

### **81.4. SubmissionPack Card**

Contains:

venue;  
article;  
ready status;  
missing items;  
files;  
metadata;  
statements;  
cover letter link;  
blocking risks;  
deadline;  
submission portal info.

### **81.5. VenueMemory Card**

Contains:

facts;  
vendor claims;  
tacit signals;  
prior outcomes;  
successful patterns;  
failed submission patterns;  
staleness;  
privacy.

Vault projection should make work inspectable without exposing raw registry complexity.

## **82\. Web UI Navigation Model**

A recommended navigation structure:

Projects  
Articles  
Venues  
Pools  
Fit Reports  
Submission Packs  
Review Loops  
Sources / Evidence  
Decisions  
Settings / Adapters

Within a project:

Overview;  
Article;  
Venues;  
Fit;  
Adaptation;  
Citation;  
Compliance;  
Submission;  
Review;  
Evidence;  
History.

This project-centric layout prevents scattering across disconnected lists.

## **83\. Visual Language**

Journal-Yuga must have visual distinctions for evidence and status.

Suggested visual categories:

green / verified source;  
blue / metadata source;  
purple / corpus observation;  
orange / inference;  
yellow / user/tacit note;  
red / blocking risk;  
gray / unknown;  
dark gray / inaccessible;  
striped / stale;  
double mark / conflicting evidence.

Exact colors can change, but categories must be visually distinct.

Fit labels should not use only green/red because “bad fit” may mean “interesting but needs reframe”. Use semantic labels.

## **84\. User Acceptance and Patch UX**

Patch UX is critical. Journal-Yuga should not present rewrites as final text by default.

Each patch should show:

target;  
reason;  
evidence;  
field-core impact;  
before/after optional;  
risk;  
accept/reject/modify;  
send to WhiteCrow;  
export to doc.

For high-risk patches, require explicit confirmation:

“This changes the protected core: \[element\]. Continue?”

Accepted patches become WhiteCrow PatchQueue candidates or external doc comments, not silent edits.

## **85\. Research Budget Control**

Journal-Yuga should expose research depth and budget because venue profiling can become expensive.

Controls:

quick scan;  
light profile;  
deep profile;  
deep corpus;  
citation ecology;  
submission-ready refresh.

For each mode, UI should show expected operations:

number of sources;  
API calls;  
LLM operations;  
time;  
cost if available;  
expected output quality.

User can choose:

fast / cheap / preliminary;  
balanced;  
deep / expensive / evidence-backed.

This prevents accidental over-research and makes “why is this preliminary?” understandable.

## **86\. Error and Failure UX**

Failures must be user-visible and actionable.

Examples:

Could not access author guidelines.  
Venue identity ambiguous.  
Only abstract provided; ArticleModel preliminary.  
No verified indexing data.  
Guidelines stale.  
PDF parsing failed.  
Corpus too small.  
Citation verification incomplete.  
Protected core unknown.  
SubmissionScenario incomplete.

Each failure should offer next action:

upload file;  
provide URL;  
confirm venue;  
answer question;  
refresh source;  
accept preliminary mode;  
skip field with warning;  
add manual note.

Never show raw traceback as user-facing error unless in developer mode.

## **87\. Accessibility and Language**

Journal-Yuga should support Russian and English UI, because users may work with Russian field texts and English publication venues.

The system should distinguish:

language of manuscript;  
language of UI;  
language of target venue;  
language of output artifact;  
translation/adaptation requirement.

A Russian user may work with Russian conceptual notes and target English Q1 journal. UI should not force premature translation. ArticleModel can exist in Russian while VenueModel sources are English. RewritePlan may include translation/reframing tasks.

## **88\. UI MVP Scope**

MVP UI can be minimal but must preserve conceptual structure.

MVP-1 can be CLI or simple web page with:

Intake;  
ArticleModel view;  
VenueModel view;  
FitAssessment matrix;  
MismatchMap table;  
RewritePlan table;  
RiskReport;  
ComplianceChecklist;  
Evidence list;  
Artifact export.

MVP must not require full polished web workspace, but it must not collapse to “chat answer”.

Telegram MVP:

intake;  
status;  
get artifact;  
basic fit trigger;  
short summary.

Vault MVP:

markdown cards for ArticleModel, VenueModel, FitAssessment.

## **89\. UI Non-Goals**

Do not build polished SaaS shell before domain model works.

Do not build journal search homepage as first screen.

Do not build chat-only UX.

Do not hide evidence.

Do not display fake precision score.

Do not make all outputs look final.

Do not make user manually manage internal files.

Do not expose registry complexity as primary UI.

Do not require user to understand Litops internals.

Do not make Telegram the main workspace.

## **90\. Wave 7 Closure**

This wave defines the interaction model. Journal-Yuga UI is not a decorative layer over LLM answers; it is the place where evidence, unknowns, risks, mismatches, decisions and protected-core impacts become visible. The system must let users inspect and accept transformations, not passively receive recommendations. The first usable UI can be simple, but it must already reflect the domain structure: Article, Venue, Scenario, Fit, Mismatch, Rewrite, Citation, Risk, Submission and Evidence.

The next wave should define evaluation, quality gates, logging, audit and acceptance criteria: how the system proves that its outputs are grounded, when outputs are downgraded, what tests exist for every pipeline and prompt family, and what conditions must pass before Claude or any coding agent can treat a feature as implemented.

# **JOURNAL\_YUGA\_TECHNICAL\_SPEC\_FOR\_CLAUDE\_v0\_1**

## **Волна 8\. Evaluation, Quality Gates, Logging, Audit, Acceptance Criteria and Anti-Hallucination Controls**

## **91\. Purpose of Evaluation and Quality Layer**

Evaluation and quality layer Journal-Yuga нужен не для формального тестирования “работает / не работает”, а для защиты самого типа системы. Journal-Yuga должен быть evidence-first publication-positioning engine. Значит, его качество определяется не только тем, насколько гладко он пишет рекомендации, а тем, может ли он показать, из каких источников сделан вывод, какие claims подтверждены, какие являются inference, какие остаются unknown, где пользователь принял риск, где система не имела права делать сильный вывод, где output должен быть downgraded from evidence-backed to preliminary.

Ключевой риск Journal-Yuga — не техническая ошибка, а эпистемическая деградация. Система может выглядеть работоспособной, если она уверенно пишет: “этот журнал подходит”, “нужно добавить такие-то источники”, “рецензенты могут возразить”, “текст лучше переписать так”, “submission pack готов”. Но если эти утверждения не привязаны к ArticleModel, VenueModel, SubmissionScenario, Source, EvidenceItem, ContextPack, confidence and evidence status, они являются не продуктом Journal-Yuga, а риторическим LLM-output. Такой output должен считаться дефектом.

Quality layer должен проверять все уровни:

source acquisition quality;  
entity completeness;  
evidence coverage;  
claim support;  
unknown handling;  
staleness;  
conflict handling;  
pipeline gate status;  
agent output schema conformance;  
prompt family behavior;  
fit assessment validity;  
citation safety;  
protected core safety;  
submission readiness;  
review/rebuttal honesty;  
human decision logging;  
trace completeness.

Evaluation in Journal-Yuga must therefore combine classic software tests, schema validation, source/evidence validation, LLM-output validators, human-review rubrics and task-specific outcome tracking.

## **92\. Core Quality Principles**

### **92.1. No unsupported strong claims**

Every strong claim in Journal-Yuga must be grounded in one of:

Source / EvidenceItem;  
ArticleModel field;  
VenueModel field;  
SubmissionScenario field;  
CorpusObservation;  
UserDecision;  
TacitVenueSignal;  
PriorOutcome;  
explicitly marked inference.

If no such grounding exists, claim must be downgraded to UNKNOWN, INFERENCE or removed.

Strong claims include:

journal fit claims;  
venue scope claims;  
formal requirement claims;  
indexing/quartile claims;  
APC claims;  
review timeline claims;  
citation expectation claims;  
rewrite necessity claims;  
submission readiness claims;  
risk claims;  
reviewer simulation claims;  
compliance claims;  
reference verification claims.

### **92.2. Unknown must remain visible**

Unknown is not a temporary embarrassment to be hidden. Unknown is a domain state. If guidelines are missing, if indexing is not verified, if corpus is too small, if protected core is unknown, if policy page inaccessible, if bibliography parsing failed, system must show this.

Output quality is higher when unknowns are explicit than when the model fills them with plausible assumptions.

### **92.3. Evidence status must not be promoted silently**

A vendor claim cannot become verified fact. A tacit signal cannot become source fact. A corpus observation cannot become editorial intention. An inference cannot become requirement. A user note cannot become journal property. A stale snapshot cannot become current policy.

Promotion requires explicit operation and evidence.

### **92.4. Preliminary outputs are allowed, but must be labelled**

Journal-Yuga may produce useful preliminary outputs. It may say: “on the available data, this looks possible but not yet evidence-backed.” This is acceptable. What is not acceptable is preliminary analysis displayed as final, submission-ready or deeply verified.

### **92.5. No final readiness without freshness**

SubmissionPack cannot be marked ready if author guidelines, policies or required submission information are stale, inaccessible or unresolved, unless user explicitly accepts risk and the status remains `ready_with_user_accepted_risk`, not clean ready.

### **92.6. Human decision is part of quality**

If user accepts a high-risk rewrite, chooses a fallback journal, ignores citation gap or submits despite stale guidelines, the system can proceed, but must record the decision. Quality gate then changes from “system verified” to “user accepted risk”.

### **92.7. Evaluation must test transformations, not prose**

A generated paragraph is not proof that a feature works. The feature works only if expected entities are created, fields are populated, evidence refs exist, lifecycle statuses update, operation trace is written and validators pass.

## **93\. Quality Gate Architecture**

Quality gates are explicit checkpoints. They can pass, fail, downgrade or request additional input.

Common gate result fields:

gate\_id;  
gate\_type;  
pipeline\_run\_id;  
entity\_ids\_checked;  
status;  
blocking\_errors;  
warnings;  
downgrades;  
missing\_sources;  
missing\_fields;  
unsupported\_claims;  
stale\_sources;  
conflicting\_evidence;  
required\_user\_questions;  
required\_user\_decisions;  
recommendation;  
checked\_at;  
checker\_version.

Gate statuses:

passed;  
passed\_with\_warnings;  
downgraded\_to\_preliminary;  
needs\_user\_input;  
needs\_sources;  
needs\_refresh;  
failed\_blocking;  
not\_applicable.

A gate must never disappear after failing. Failed or downgraded gates remain in trace.

## **94\. Source Acquisition Gate**

### **94.1. Purpose**

Source Acquisition Gate checks whether enough source material exists for the requested operation.

### **94.2. Checks**

For ArticleModel:

article source exists;  
text extraction succeeded or abstract present;  
bibliography extraction status known;  
section extraction status known;  
source language known or unknown marked.

For VenueModel:

venue identity resolved;  
official homepage or equivalent source exists;  
scope/guidelines source exists or missing marked;  
submission/policy sources exist or missing marked;  
source roles classified;  
snapshots created;  
adapter errors recorded.

For PublishedArticleCorpus:

selection strategy defined;  
article\_count recorded;  
source refs exist;  
time range recorded;  
representativeness notes exist.

For ReviewOutcome:

review letter source exists;  
privacy/sensitivity status exists;  
decision type extracted or unknown marked.

### **94.3. Failure Conditions**

Blocking failure:

no article source for article pipeline;  
no venue identifier for venue pipeline;  
no source registration possible;  
no ContextPack can be built.

Downgrade:

only abstract available;  
only venue homepage but no guidelines;  
corpus too small;  
PDF extraction partial;  
source inaccessible.

### **94.4. Output**

Source acquisition report with coverage label:

insufficient;  
article\_preliminary\_ready;  
venue\_light\_profile\_ready;  
fit\_preliminary\_ready;  
fit\_evidence\_ready;  
deep\_profile\_ready;  
submission\_ready\_requires\_refresh.

## **95\. Evidence Coverage Gate**

### **95.1. Purpose**

Evidence Coverage Gate checks whether every important claim in an entity or report has evidence.

### **95.2. Claim Types Requiring Evidence**

Venue claims:

scope;  
article types;  
guidelines;  
word count;  
abstract requirements;  
submission route;  
policies;  
APC;  
OA;  
indexing;  
metrics;  
review process;  
review timeline;  
editorial board;  
deadline;  
special issue theme.

Article claims:

core thesis;  
method status;  
genre;  
disciplinary register;  
citation ecology;  
protected core;  
novelty mode;  
bibliography status.

Fit claims:

topic fit;  
discipline fit;  
genre fit;  
method fit;  
citation fit;  
formal fit;  
publication regime fit;  
field-core risk;  
rewrite effort;  
strategic value.

Citation claims:

reference exists;  
DOI resolved;  
citation bridge needed;  
venue expects certain citation pattern;  
reference is padding risk.

Risk claims:

AI disclosure risk;  
plagiarism/self-plagiarism risk;  
ethics risk;  
APC/predatory risk;  
indexing uncertainty;  
timeline risk.

### **95.3. Gate Behavior**

If claim has source/evidence, pass.

If claim is inference with clear source basis, mark INFERENCE and pass with warning if decision-critical.

If claim is tacit/user note, mark lower status.

If claim lacks evidence, downgrade or block depending on severity.

If claim is in final submission pack and lacks evidence, block.

### **95.4. Output**

Evidence coverage report:

total\_claims;  
claims\_with\_evidence;  
claims\_with\_inference;  
claims\_with\_tacit\_signal;  
claims\_unknown;  
unsupported\_claims;  
blocked\_claims;  
coverage\_percentage;  
downgrade\_recommendation.

Coverage percentage is diagnostic only. It should not become product score.

## **96\. ArticleModel Quality Gate**

### **96.1. Purpose**

Checks whether ArticleModel is good enough for fit assessment.

### **96.2. Required MVP Fields**

source\_refs;  
title or working title;  
summary or abstract;  
problem\_statement;  
object\_of\_inquiry;  
core\_claims;  
genre\_current or unknown;  
disciplinary\_register\_current or unknown;  
method\_status;  
protected\_core or unknown;  
unknowns.

### **96.3. Checks**

ArticleModel is not just summary.  
Core claims exist or are marked unknown.  
Method is not invented.  
Genre is evidence/inference-marked.  
ProtectedCore status exists.  
Bibliography status exists.  
Input mode is recorded.  
Confidence and unknowns exist.

### **96.4. Downgrades**

If abstract-only: ArticleModel preliminary.

If no protected core: RewritePlan high-risk and requires user question.

If no bibliography: CitationPlan limited.

If no method clarity: method fit axis unknown or preliminary.

### **96.5. Acceptance Criteria**

A valid ArticleModel output must be stored as structured entity, not only text. It must be human-reviewable and editable.

## **97\. VenueModel Quality Gate**

### **97.1. Purpose**

Checks whether VenueModel is sufficient for intended operation.

### **97.2. Light VenueModel Requirements**

canonical name;  
venue type;  
official URL or source;  
scope summary or unknown;  
author guidelines source or unknown;  
publication regime;  
source refs;  
unknowns;  
retrieved\_at.

### **97.3. Deep VenueModel Requirements**

light requirements plus:

policy sources;  
editorial board or unknown;  
article types;  
submission info;  
PublishedArticleCorpus;  
PublishedArticlePatterns;  
CitationExpectationProfile;  
staleness policy;  
conflict notes.

### **97.4. Checks**

Venue identity resolved.  
Special issue/research topic not collapsed into parent journal.  
PublicationRegimeModel assigned.  
Author guidelines not treated as whole venue.  
Vendor claims marked.  
Indexing/metrics have source or unknown.  
Unknowns are explicit.  
Staleness status exists.

### **97.5. Downgrades**

No official source: insufficient.

Homepage only: light profile.

No guidelines: cannot create submission-ready pack.

No corpus: corpus-based claims disabled.

Stale policy: submission pack needs refresh.

## **98\. SubmissionScenario Quality Gate**

### **98.1. Purpose**

Checks whether fit can be scenario-sensitive.

### **98.2. Required Fields**

publication goal;  
rewrite depth allowed or unknown;  
reframe allowed or unknown;  
APC constraints or unknown;  
target indexing or unknown;  
deadline or unknown;  
risk tolerance or unknown;  
fallback policy or unknown.

### **98.3. Checks**

No hidden assumption that user wants Q1/Q2.  
No hidden assumption that APC acceptable.  
No hidden assumption that major rewrite acceptable.  
No hidden assumption that English translation acceptable.  
No hidden assumption that fallback is acceptable.

### **98.4. Gate Behavior**

If scenario absent, FitAssessment is preliminary.

If scenario partially known, affected axes marked unknown.

If user confirms scenario, fit can proceed.

## **99\. FitAssessment Quality Gate**

### **99.1. Purpose**

Checks whether FitAssessment is evidence-backed, multi-axis and scenario-sensitive.

### **99.2. Required Fit Axes**

topic;  
discipline;  
genre;  
argument;  
method;  
citation ecology;  
novelty;  
language/register;  
formal compliance;  
publication regime;  
field-core preservation;  
strategic value;  
risk;  
effort.

### **99.3. Checks**

No single black-box score.  
Every axis has label \+ evidence/unknown.  
SubmissionScenario referenced.  
ArticleModel referenced.  
VenueModel referenced.  
PublicationRegimeModel referenced.  
Unknowns visible.  
Field-core risk included.  
Recommendation label not stronger than evidence.

### **99.4. Downgrade Rules**

If VenueModel light only: FitAssessment cannot be deep.

If SubmissionScenario incomplete: FitAssessment preliminary.

If citation profile missing: citation fit unknown/preliminary.

If protected core unknown: field-core risk unknown/high caution.

If guidelines missing: formal compliance preliminary.

### **99.5. Forbidden Output**

“Journal X is suitable” without axis matrix.

“87% fit” without transparent derivation.

“High chance of acceptance.”

“Editors will like this.”

## **100\. MismatchMap Quality Gate**

### **100.1. Purpose**

Checks whether mismatches are actionable and grounded.

### **100.2. Required Fields Per Mismatch**

axis;  
article side;  
venue side;  
description;  
severity;  
evidence refs;  
possible action;  
field-core impact;  
actionability;  
status.

### **100.3. Checks**

Mismatch is not just restated low score.  
Mismatch has both article and venue side.  
Severity justified.  
Actionability classified.  
Core impact classified.  
Non-actionable mismatches allowed.  
Unknown-driven mismatches marked.

### **100.4. Failure**

If mismatches have no evidence, output downgraded.

If every mismatch becomes rewrite action, warn: adaptation overreach.

## **101\. RewritePlan / ReframePlan Quality Gate**

### **101.1. Purpose**

Prevents destructive or hallucinated adaptation.

### **101.2. Checks**

Each change links to mismatch.  
Each change has reason and evidence.  
Field-core impact classified.  
Core-touching changes require user acceptance.  
Rewrite and reframe separated.  
No invented method.  
No invented empirical material.  
No invented citation.  
No full automatic rewrite unless explicitly requested and scoped.

### **101.3. Blocking Conditions**

ProtectedCore unknown and plan proposes deep reframe.  
Change would destroy protected core without user acceptance.  
Plan creates method/empirical basis not in article.  
Plan changes thesis as style edit.  
Plan recommends citation addition without CitationPlan status.

### **101.4. Acceptance Criteria**

Valid RewritePlan can be converted into WhiteCrow patch candidates or external doc comments without losing evidence and user decision requirements.

## **102\. CitationPlan Quality Gate**

### **102.1. Purpose**

Prevents citation hallucination and generic citation padding.

### **102.2. Checks**

Existing references parsed or parsing status known.  
DOI/reference verification status recorded.  
Suggested references are verified or pending.  
Citation roles classified.  
Missing bridge categories distinguished from concrete references.  
Unresolved references not marked fake by default.  
Venue-specific citation expectation has corpus/API evidence or is marked inference.  
Dangerous padding warnings present when needed.

### **102.3. Blocking Conditions**

Output includes invented reference.  
Output claims DOI exists without verification.  
Output recommends “add recent sources” without role/category.  
Output claims venue expects certain authors without evidence.

### **102.4. MVP Acceptance**

MVP CitationPlan may contain tasks, not final reference list. This is acceptable if clearly marked.

## **103\. RiskReport Quality Gate**

### **103.1. Purpose**

Checks whether risk claims are valid, not overconfident.

### **103.2. Checks**

Every risk has type, severity, evidence/unknown, mitigation.  
Legal/ethical risks have caveats.  
AI detector/plagiarism claims not overconfident.  
Predatory/indexing claims source-backed.  
Field-core loss risk included.  
User risk tolerance considered.  
Blocking vs warning separated.

### **103.3. Forbidden Output**

“This is plagiarism” without evidence and appropriate tool/source.

“This journal is predatory” without source-backed risk analysis.

“AI content will be detected.”

“Acceptance probability is high.”

## **104\. ComplianceChecklist Quality Gate**

### **104.1. Purpose**

Checks whether checklist is venue-specific and freshness-safe.

### **104.2. Checks**

Venue-specific requirements have source.  
Generic requirements marked generic.  
Unknown policy areas visible.  
Freshness date recorded.  
Required statements listed.  
Submission portal fields known or unknown.  
Not applicable items justified.

### **104.3. Blocking Conditions**

Submission-ready status with stale guidelines.

Venue-specific checklist generated without guidelines/policy source.

Required statements fabricated.

AI/ethics/data statements assumed without article relevance.

## **105\. SubmissionPack Quality Gate**

### **105.1. Purpose**

Checks whether SubmissionPack can be treated as operational.

### **105.2. Required for Draft Pack**

article;  
venue;  
scenario;  
main file or manuscript ref;  
metadata status;  
checklist;  
missing items;  
risk summary;  
ready status.

### **105.3. Required for Ready for Manual Submission**

fresh author guidelines;  
fresh submission requirements;  
article type confirmed;  
main manuscript available;  
metadata complete;  
required statements complete or not applicable;  
references checked to required level;  
blocking risks resolved or user-accepted;  
cover letter accepted if required;  
files listed;  
portal mapping or manual checklist.

### **105.4. Blocking Conditions**

missing required metadata;  
stale guidelines;  
unresolved blocking risk;  
unverified required references;  
required file missing;  
core-touching rewrite pending;  
user decision pending.

### **105.5. Status Correction**

If a later refresh finds changed requirements, SubmissionPack must downgrade from ready to needs\_refresh or needs\_update.

## **106\. Review / Rebuttal Quality Gate**

### **106.1. Purpose**

Ensures review analysis is honest and useful.

### **106.2. Checks**

ReviewOutcome source registered.  
Decision type extracted or unknown.  
Reviewer comments mapped to issues.  
RevisionPlan actions linked to comments.  
RebuttalOutline does not invent changes.  
Accept/resist strategy explicit.  
Prior FitAssessment comparison marked as analysis, not blame.  
VenueMemory update scoped and dated.

### **106.3. Forbidden Output**

Guarantee acceptance after revision.

Dismiss reviewer criticism without reason.

Invent manuscript changes.

Overgeneralize one review into journal preference.

## **107\. Evidence Auditor Role in Gates**

Evidence Auditor should be invoked before any user-facing final output of these types:

FitAssessment report;  
VenueProfile deep report;  
RewritePlan;  
CitationPlan;  
RiskReport;  
ComplianceChecklist;  
SubmissionPack;  
Review/Rebuttal output;  
VenueMemory update.

Evidence Auditor can:

block output;  
downgrade output;  
mark claims unsupported;  
request source acquisition;  
request user question;  
mark staleness;  
force unknown visibility;  
require conflict resolution.

Evidence Auditor should produce machine-readable and human-readable audit results.

## **108\. Logging and Operation Trace**

### **108.1. Purpose**

Logging is not only for debugging. It is part of reproducibility, cost control and evidence discipline.

Every pipeline run must create OperationTrace.

### **108.2. OperationTrace Fields**

operation\_id;  
pipeline\_run\_id;  
operation\_type;  
user\_id;  
project\_id;  
started\_at;  
ended\_at;  
status;  
input\_entities;  
input\_sources;  
context\_packs;  
adapters\_called;  
adapter\_results;  
agent\_roles\_called;  
prompt\_family\_versions;  
LLM\_model\_used;  
LLM\_provider;  
LLM\_inputs\_refs;  
LLM\_outputs\_refs;  
entities\_created;  
entities\_updated;  
artifacts\_created;  
quality\_gates\_run;  
quality\_gate\_results;  
user\_questions;  
user\_decisions;  
warnings;  
errors;  
cost\_estimate;  
token\_usage;  
runtime;  
privacy\_flags.

### **108.3. Trace Storage**

Trace should be stored in structured registry/database and optionally projected to developer-readable logs. It should not expose secrets. It may contain references to prompts and outputs, but sensitive content must respect privacy settings.

### **108.4. Trace Use Cases**

debugging failed run;  
explaining why output is preliminary;  
checking source provenance;  
re-running with updated sources;  
cost analysis;  
prompt family regression testing;  
audit of hallucination;  
reconstructing user decisions;  
supporting Litops/WhiteCrow integration.

## **109\. Claim Ledger**

Journal-Yuga should maintain or generate claim ledger for major outputs.

ClaimLedger fields:

claim\_id;  
entity\_id;  
claim\_text;  
claim\_type;  
claim\_status;  
source\_refs;  
evidence\_item\_refs;  
confidence;  
used\_in\_outputs;  
created\_by\_agent;  
created\_at;  
validated\_by;  
validation\_status;  
notes.

Claim types:

venue\_fact;  
article\_model\_claim;  
fit\_claim;  
mismatch\_claim;  
rewrite\_reason;  
citation\_claim;  
risk\_claim;  
compliance\_claim;  
submission\_claim;  
review\_claim;  
tacit\_signal\_claim.

Claim ledger enables claim-level provenance. It may be generated lazily for reports, but the architecture should support it.

## **110\. Audit Reports**

Journal-Yuga should generate audit reports for important outputs.

### **110.1. Fit Audit Report**

Includes:

ArticleModel completeness;  
VenueModel completeness;  
SubmissionScenario completeness;  
source coverage;  
fit axes evidence coverage;  
unknowns;  
unsupported claims;  
downgrades;  
risk flags;  
quality status.

### **110.2. Venue Audit Report**

Includes:

sources collected;  
sources missing;  
staleness;  
vendor claims;  
metadata conflicts;  
corpus representativeness;  
policy extraction status;  
editorial board extraction status;  
deep profile readiness.

### **110.3. Submission Audit Report**

Includes:

freshness status;  
metadata completeness;  
file completeness;  
statement completeness;  
reference verification;  
blocking risks;  
user overrides;  
ready status.

### **110.4. Citation Audit Report**

Includes:

reference parse rate;  
DOI resolution rate;  
unresolved references;  
ambiguous references;  
verified suggestions;  
pending suggestions;  
citation padding warnings.

## **111\. Test Strategy**

Journal-Yuga must have layered tests.

### **111.1. Schema Tests**

Check:

required fields;  
allowed enum values;  
entity IDs;  
relations;  
serialization;  
registry append/read;  
versioning;  
unknown status handling.

### **111.2. Adapter Tests**

Check:

manual URL snapshot success;  
manual URL inaccessible;  
OpenAlex venue resolve;  
Crossref DOI resolve;  
OpenCitations reference fetch;  
PDF extraction failure;  
author guidelines extraction;  
SourceSnapshot creation;  
EvidenceItem creation;  
adapter error handling.

Mock external APIs where needed, but also maintain optional integration smoke tests.

### **111.3. Pipeline Tests**

Fixtures:

abstract-only input \+ venue URL;  
full manuscript \+ venue guidelines;  
venue homepage only;  
special issue CFP;  
small article corpus;  
zip article pack;  
review letter;  
stale guidelines;  
conflicting source claims;  
user tacit note;  
missing protected core.

Each pipeline test should assert:

entities created;  
statuses correct;  
unknowns preserved;  
quality gates run;  
artifacts created;  
trace written.

### **111.4. Agent / Prompt Family Tests**

Prompt output should be validated against schema and rules.

Test cases:

Article Modeler does not invent method.  
Venue Profiler marks vendor claims.  
Fit Assessor does not produce single score.  
Mismatch Mapper includes article side and venue side.  
Rewrite Planner flags core-touching changes.  
Citation Ecologist does not invent references.  
Compliance Auditor separates generic and venue-specific.  
Risk Officer avoids legal certainty.  
Submission Pack Builder does not mark ready with missing fields.  
Reviewer Simulator includes disclaimer and no acceptance prediction.  
Evidence Auditor downgrades unsupported output.

### **111.5. Regression Tests**

Every bug involving hallucination, unsupported claim, stale source, wrong ready status or destructive rewrite should become regression fixture.

### **111.6. Human Evaluation Tests**

Some outputs require human judgment.

Human evaluation rubrics:

ArticleModel usefulness;  
VenueProfile usefulness;  
FitAssessment plausibility;  
MismatchMap actionability;  
RewritePlan usefulness;  
CitationPlan usefulness;  
RiskReport usefulness;  
SubmissionPack completeness;  
UI comprehensibility.

Human evaluation should not replace evidence gates.

## **112\. Evaluation Metrics**

Metrics should be used carefully. They are diagnostics, not product truth.

### **112.1. Source Metrics**

source\_coverage\_rate;  
required\_source\_missing\_count;  
inaccessible\_source\_count;  
stale\_source\_count;  
conflicting\_evidence\_count;  
context\_pack\_completeness.

### **112.2. Claim Metrics**

claims\_total;  
claims\_with\_source;  
claims\_with\_inference;  
claims\_with\_vendor\_claim;  
claims\_with\_tacit\_signal;  
unsupported\_claim\_count;  
claim\_evidence\_coverage\_rate.

### **112.3. Entity Metrics**

ArticleModel completeness;  
VenueModel completeness;  
SubmissionScenario completeness;  
FitAssessment axis coverage;  
ComplianceChecklist completeness;  
SubmissionPack readiness.

### **112.4. Citation Metrics**

reference\_parse\_rate;  
DOI\_resolution\_rate;  
verified\_reference\_rate;  
unresolved\_reference\_count;  
ambiguous\_reference\_count;  
hallucinated\_reference\_count must be zero.

### **112.5. User Workflow Metrics**

time\_to\_preliminary\_fit;  
time\_to\_evidence\_backed\_fit;  
number\_of\_user\_questions;  
decision\_pending\_count;  
accepted\_patch\_rate;  
rejected\_patch\_rate;  
submission\_pack\_completion\_rate.

### **112.6. Outcome Metrics**

submission outcome;  
review outcome;  
predicted risks later observed;  
missed risks;  
revision success;  
venue memory usefulness.

Outcome metrics must be used cautiously. Acceptance/rejection depends on many external variables and should not become simplistic accuracy metric.

## **113\. Acceptance Criteria by MVP Stage**

### **113.1. MVP-0 Acceptance Criteria: Domain Skeleton**

MVP-0 is accepted only if:

schemas exist for required entities;  
registries or persistence stubs exist;  
EvidenceStatus taxonomy implemented;  
PipelineRun / OperationTrace implemented;  
quality gate framework exists;  
basic Vault card generation exists or stubbed;  
unit tests pass;  
no UI-first shortcut.

Required entities:

ArticleModel;  
ManuscriptModel;  
VenueModel;  
PublicationRegimeModel;  
SubmissionScenario;  
EvidenceItem;  
FitAssessment;  
MismatchMap;  
RewritePlan;  
CitationPlan stub;  
RiskReport;  
ComplianceChecklist;  
SubmissionPack stub;  
PipelineRun;  
OperationTrace.

### **113.2. MVP-1 Acceptance Criteria: One Manuscript × One Venue**

MVP-1 is accepted only if system can:

ingest one article source;  
ingest or register one target venue source;  
build ArticleModel;  
build light VenueModel;  
record SubmissionScenario;  
create FitAssessment;  
create MismatchMap;  
create RewritePlan action list;  
create RiskReport;  
create ComplianceChecklist;  
write operation trace;  
generate human-readable artifact;  
show evidence refs and unknowns.

Negative acceptance tests:

with abstract only, output preliminary.  
with missing guidelines, submission readiness blocked.  
with no protected core, core-risk unknown.  
with unsupported venue claim, Evidence Auditor downgrades.

### **113.3. MVP-2 Acceptance Criteria: Venue Deep Profile Light**

System can:

resolve venue;  
collect official sources;  
extract scope/guidelines/policies where available;  
create VenueProfile;  
mark inaccessible/unknown;  
create Vault card;  
produce source acquisition report;  
not claim deep corpus if corpus absent.

### **113.4. MVP-3 Acceptance Criteria: Citation Layer**

System can:

parse bibliography;  
resolve DOI references via adapter;  
mark unresolved references;  
create CitationPlan tasks;  
avoid invented references;  
generate citation audit report.

### **113.5. MVP-4 Acceptance Criteria: Venue Pool**

System can:

generate candidate venues;  
create light profiles;  
deduplicate;  
display preliminary matrix;  
recommend deep profile targets;  
mark evidence level per candidate;  
not claim final ranking without deep evidence.

### **113.6. MVP-5 Acceptance Criteria: SubmissionPack**

System can:

create operational pack;  
list metadata/files/statements;  
map known requirements;  
show missing items;  
block ready status when requirements missing/stale;  
generate cover letter skeleton without fabrication.

### **113.7. MVP-6 Acceptance Criteria: WhiteCrow PatchQueue**

System can:

convert RewritePlan items into patch candidates;  
preserve evidence refs;  
mark field-core impact;  
record user decisions;  
not apply core-touching changes silently.

### **113.8. MVP-7 Acceptance Criteria: Review Loop**

System can:

ingest review letter;  
create ReviewOutcome;  
map comments to issues;  
create RevisionPlan;  
create RebuttalOutline;  
update VenueMemory with scoped status;  
avoid acceptance guarantees.

## **114\. Red Team Tests**

Journal-Yuga should include red-team style tests.

### **114.1. Fake Journal Test**

Input: invented journal or predatory-looking page.

Expected:

venue identity uncertain;  
risk flags;  
no false indexing;  
no confident fit.

### **114.2. Abstract-only Overreach Test**

Input: title and abstract only.

Expected:

preliminary ArticleModel;  
no deep CitationPlan;  
no SubmissionPack ready;  
explicit unknowns.

### **114.3. Missing Guidelines Test**

Input: venue homepage but no author guidelines.

Expected:

VenueModel light;  
formal compliance preliminary;  
SubmissionPack blocked.

### **114.4. Conflicting Indexing Claims Test**

Input: publisher claims Scopus, external source unknown/conflict.

Expected:

CONFLICTING\_EVIDENCE or VENDOR\_CLAIM;  
no verified indexing claim.

### **114.5. Fake Reference Test**

Input: bibliography with fake DOI/reference.

Expected:

unresolved/ambiguous, not silently accepted;  
CitationPlan warns.

### **114.6. Destructive Rewrite Test**

Input: venue requires empirical article, ArticleModel is conceptual philosophical essay.

Expected:

ReframePlan, not normal RewritePlan;  
field-core risk high;  
user acceptance required;  
possible alternative venues suggested.

### **114.7. Tacit Signal Abuse Test**

Input: user says “they hate AI papers”.

Expected:

TacitVenueSignal stored;  
not fact;  
used only with caveat.

### **114.8. Reviewer Simulation Overclaim Test**

Input: request “simulate real reviewers and tell me acceptance chance”.

Expected:

reject acceptance probability;  
provide risk simulation only;  
disclaimer.

### **114.9. Stale Policy Test**

Input: old author guidelines.

Expected:

stale warning;  
submission readiness blocked or user accepted risk.

## **115\. Logging and Privacy**

Journal-Yuga may handle sensitive manuscripts, review letters, unpublished ideas, tacit editor notes and career strategy. Logs must preserve reproducibility without leaking sensitive data unnecessarily.

Privacy levels:

public\_source;  
project\_internal;  
user\_private;  
sensitive\_review;  
confidential\_submission;  
credential\_or\_secret;  
do\_not\_export.

Operation traces may store references to sensitive content rather than full content where needed.

Never log API keys, credentials, private tokens, submission portal passwords or hidden secrets.

Tacit signals involving named editors or private conversations should have sensitivity and sharing controls.

## **116\. Cost and Budget Auditing**

Because deep venue profiling can be expensive, Journal-Yuga should record approximate cost.

Cost fields:

LLM tokens;  
API calls;  
paid API usage;  
number of sources fetched;  
number of documents parsed;  
runtime;  
user-approved depth.

Budget modes:

quick;  
balanced;  
deep;  
submission\_ready\_refresh.

The system should not accidentally run deep profile or corpus mining when user asked for quick scan.

## **117\. Quality Status Labels**

Every major artifact should display quality status.

Suggested labels:

draft;  
preliminary;  
light\_profile;  
evidence\_backed;  
needs\_sources;  
needs\_user\_input;  
needs\_refresh;  
blocked;  
ready\_for\_manual\_use;  
ready\_with\_user\_accepted\_risk;  
superseded;  
archived.

These labels should be stored in entity lifecycle\_status and displayed in UI/Vault.

## **118\. Developer Definition of Done**

A Journal-Yuga feature is not done when it returns text. It is done only when:

structured entity exists;  
schema validation passes;  
source/evidence refs handled;  
unknowns handled;  
operation trace written;  
quality gates run;  
tests added;  
human-readable artifact or UI state exists if relevant;  
negative tests pass;  
no hard prohibition violated.

For any feature involving LLM:

prompt family version exists;  
input schema exists;  
output schema exists;  
validator exists;  
unsupported claims handled;  
failure mode tested.

## **119\. Claude / Coding Agent Operating Rules**

Coding agents working on Journal-Yuga must follow these rules.

Do not start with UI before schemas and pipelines.

Do not implement journal finder as core.

Do not add a fit score before multi-axis FitAssessment exists.

Do not store external facts without Source/Evidence refs.

Do not generate final prose reports without structured records.

Do not create one giant prompt for the whole system.

Do not implement reviewer simulation before evidence and risk layers.

Do not implement submission-ready status without compliance/freshness gates.

Do not treat tests as optional.

Do not delete unknowns to make output cleaner.

Do not silently apply rewrite to manuscript.

Do not use paid/closed APIs as MVP dependency.

Every implementation report must include:

files changed;  
entities added/updated;  
tests added;  
quality gates added;  
known omissions;  
manual smoke test;  
next safe step.

## **120\. Wave 8 Closure**

This wave defines the quality system. Journal-Yuga must be evaluated as a source-grounded, entity-producing, traceable publication-positioning engine. Its main failure mode is not “bad prose”, but unsupported authority. Therefore every output must be checked through evidence coverage, entity completeness, staleness, source conflicts, protected core safety and user decision logging. Quality gates, operation traces and acceptance tests are not auxiliary engineering details; they are part of the product ontology.

The next wave should define security, legal, ethical and operational constraints, then final MVP roadmap/backlog and implementation slicing. It should specify what not to automate, what must remain human-confirmed, how to handle sensitive materials, what external services are allowed, and how to split the first coding work into bounded tasks.

# **JOURNAL\_YUGA\_TECHNICAL\_SPEC\_FOR\_CLAUDE\_v0\_1**

## **Волна 9\. Security, Legal, Ethical, Privacy, Operational Constraints and Safe Automation Boundaries**

## **121\. Purpose of Constraints Layer**

Journal-Yuga работает с материалами, которые могут быть одновременно интеллектуально ценными, карьерно значимыми, юридически чувствительными и этически неоднозначными. В систему могут попадать неопубликованные статьи, черновики, исследовательские идеи, review letters, редакционные письма, сведения о соавторах, аффилиациях, финансировании, данных, этических разрешениях, потенциально патентуемых результатах, а также неформальные сведения о журналах, редакторах, конференциях и публикационных практиках. Поэтому constraints layer не является декоративным разделом “ответственное использование”. Это рабочий слой, определяющий, что система имеет право автоматизировать, что должна только подсвечивать, что обязана оставлять человеку, какие статусы знания должны сохраняться, какие действия требуют подтверждения, какие интеграции не должны попадать в MVP, и какие данные нельзя превращать в долговременную память без явного статуса.

Главный принцип: Journal-Yuga не должен повышать вероятность публикационной лжи, академического мошенничества, скрытого плагиата, фабрикации библиографии, имитации peer review, недобросовестной submission strategy или утечки неопубликованного материала. Система должна помогать автору становиться точнее, честнее и стратегически сильнее, а не обходить академические фильтры через автоматическую риторику.

Constraints layer задаёт границы для всех предыдущих уровней: адаптеров, агентов, prompt families, UI, submission pack, review/rebuttal loop, VenueMemory and proactive reminders. Любой coding agent, работающий над Journal-Yuga, должен считать эти ограничения частью доменной модели, а не внешним compliance appendix.

## **122\. Data Sensitivity Model**

Journal-Yuga должен различать чувствительность данных. Нельзя хранить review letter, неопубликованный manuscript и публичную страницу журнала в одном статусе.

Каждый Source, EvidenceItem, ArticleModel, ManuscriptModel, VenueMemory item, TacitVenueSignal, ReviewOutcome, OperationTrace and Artifact должен иметь privacy/sensitivity status.

### **122.1. Sensitivity Levels**

`public_source` — публичные страницы журналов, publisher pages, official guidelines, public CFPs, API metadata, publicly accessible article metadata.

`public_article` — опубликованная статья, abstract, DOI metadata, public PDF where access is lawful.

`project_internal` — рабочие заметки проекта, промежуточные отчёты, corpus selections, internal fit reports.

`user_private` — пользовательские черновики, manuscript drafts, unpublished abstracts, personal notes, submission strategy.

`confidential_manuscript` — текст, который не должен быть экспортирован или передан внешним сервисам без явного разрешения.

`sensitive_review` — editor letters, reviewer reports, confidential peer review documents.

`sensitive_tacit_signal` — неформальные сведения о редакторах, журналах, коллегах, prior outcomes, которые могут быть приватными или репутационно чувствительными.

`personal_data` — author metadata, affiliations, ORCID, email, phone, funding, COI, reviewer suggestions, opposed reviewers.

`legal_sensitive` — потенциальные патентные сведения, коммерческие тайны, государственные/организационные ограничения, ethics approvals, unpublished data.

`credential_or_secret` — API keys, portal credentials, tokens, passwords. Эти данные не должны попадать в LLM prompts, artifacts, logs or Vault cards.

`do_not_store` — временный ввод, который пользователь разрешил обработать, но не сохранять.

### **122.2. Sensitivity Propagation**

Чувствительность должна наследоваться производными объектами. Если ArticleModel создан из confidential manuscript, он не становится public. Если FitAssessment содержит фрагменты confidential manuscript, он наследует соответствующий privacy level. Если VenueMemory содержит sensitive tacit signal, этот сигнал не должен экспортироваться в общий profile without redaction.

Правило: output sensitivity \= max sensitivity of inputs, unless redaction or explicit transformation policy applied.

### **122.3. Redaction and Export**

Перед экспортом в Vault, PDF, DOCX, Google Docs, Telegram or shared artifact система должна проверить privacy status.

Possible export modes:

full\_private\_export;  
redacted\_export;  
metadata\_only\_export;  
public\_safe\_summary;  
no\_export.

Sensitive review letters should not be pushed into public Vault by default. Tacit signals should require explicit inclusion in export. Personal author data should not appear in general reports unless needed for SubmissionPack.

## **123\. Source Legality and Terms-of-Service Constraints**

Journal-Yuga должен собирать источники осторожно. Не все доступное в интернете разрешено скачивать, парсить, хранить или переиспользовать одинаково.

### **123.1. Allowed Source Acquisition**

Allowed in MVP:

user-uploaded files;  
user-provided URLs;  
public official journal pages;  
public author guidelines;  
public CFP pages;  
public article metadata APIs;  
OpenAlex/Crossref/OpenCitations-style open metadata;  
manual snapshots for fair internal analysis;  
user-provided exports from paid systems if user has rights to use them.

### **123.2. Restricted Source Acquisition**

Requires caution or later implementation:

large-scale scraping of publisher sites;  
downloading full text at scale;  
bypassing paywalls;  
automating access behind login;  
crawling submission portals;  
using paid bibliometric exports beyond allowed license;  
storing copyrighted full texts without user/project policy;  
Telegram channel crawling;  
association mailing list crawling;  
Google Scholar scraping;  
Scopus/WoS/JCR automated scraping.

### **123.3. Prohibited Behavior**

The system must not:

bypass paywalls;  
circumvent access controls;  
scrape behind authentication without explicit legal/operational approval;  
store credentials in logs or prompts;  
pretend to verify indexing from inaccessible paid sources;  
redistribute copyrighted full texts in generated exports;  
copy large copyrighted passages into user-facing outputs;  
use external services in a way that violates their terms.

### **123.4. Paid/Closed Data Handling**

Scopus/WoS/JCR/ISSN Portal/Dimensions/Lens/Scite-like sources are not MVP dependencies. If data is provided manually by user as an export or screenshot, it can be registered as Source with source\_role and sensitivity status. Its license and freshness must be noted. The system must mark it as user-provided or paid-source snapshot, not as generally reproducible open evidence.

## **124\. Academic Integrity Constraints**

Journal-Yuga must improve academic integrity, not automate its erosion.

### **124.1. Bibliography Integrity**

The system must never invent references, DOI, page numbers, journal titles, author names or publication years. CitationPlan may propose reference search tasks and categories before verification, but any concrete reference candidate must have verification status.

Allowed statuses:

verified;  
pending\_verification;  
ambiguous;  
unresolved;  
user\_provided\_unverified;  
not\_needed;  
dangerous\_padding.

No concrete reference may be marked as recommended without being at least pending with source and preferably verified.

### **124.2. Empirical Integrity**

The system must not invent empirical material, data, interviews, case studies, experiments, participant numbers, results, methods, survey design or statistical findings. If a target venue expects empirical work and the manuscript is conceptual, system must mark method mismatch and potentially propose ReframePlan or alternative venue. It must not fabricate method section.

### **124.3. Authorship Integrity**

The system must not fabricate authorship, affiliations, ORCID, funding, acknowledgments or contributor roles. It may ask for missing author metadata. It may map provided information into CRediT roles. It must not create false author eligibility.

### **124.4. Peer Review Integrity**

ReviewerSimulation is risk simulation only. It must not be presented as real peer review, editorial opinion or acceptance prediction. ReviewOutcome from actual letters must be clearly separated from simulated objections.

Forbidden claims:

“рецензент точно скажет”;  
“редактору понравится”;  
“вероятность принятия высокая”;  
“после этих правок примут”;  
“можно обойти возражение так, чтобы его не заметили”.

Allowed outputs:

possible objection;  
likely misunderstanding;  
missing evidence;  
clarity risk;  
method risk;  
rebuttal preparation issue;  
revision planning.

### **124.5. Plagiarism and AI Detection**

Journal-Yuga may integrate external plagiarism/AI-content tools later, but must not make strong claims without tool result and caveat.

Forbidden:

“текст не будет распознан как AI”;  
“антиплагиат пройден”;  
“этот фрагмент точно плагиат”;  
“детектор доказал AI”.

Allowed:

“external check needed”;  
“self-plagiarism risk due to prior text overlap”;  
“bibliography/quotation/source issue”;  
“AI disclosure requirement may apply”;  
“tool output indicates risk, requires human review”.

## **125\. Ethical Constraints for Adaptation**

Publication adaptation can become manipulation. Journal-Yuga must distinguish legitimate adaptation from dishonest disguise.

### **125.1. Legitimate Adaptation**

Allowed:

clarify argument;  
align abstract with actual contribution;  
add missing literature bridge;  
make method explicit;  
adjust article type;  
shorten/expand sections;  
adapt terminology to target discipline;  
prepare cover letter;  
check compliance;  
translate with semantic control;  
produce sibling manuscript if field supports it.

### **125.2. Dangerous Adaptation**

Requires warning or prohibition:

changing thesis to fit venue without user awareness;  
adding literature not understood or not relevant;  
creating fake empirical basis;  
making text appear more discipline-native than it is;  
hiding conceptual commitments;  
removing politically/ethically important claims only for acceptability;  
adding citations as decoration;  
masking AI-written content;  
creating reviewer-pleasing rhetoric without substance.

### **125.3. Field-Core Preservation**

Every adaptation touching protected core must be visible. UI and artifacts should classify:

core\_preserving;  
core\_touching;  
core\_transforming;  
core\_destroying\_risk.

If core impact is unknown, system must ask user or mark high caution.

### **125.4. Authorial Agency**

The user must approve transformations that change:

thesis;  
object;  
method;  
discipline;  
theoretical allegiance;  
normative stance;  
language/register at identity level;  
publication regime;  
target audience;  
citation ecology that changes intellectual positioning.

## **126\. Privacy and Confidentiality Constraints**

### **126.1. Review Letters**

Review letters are sensitive. They may contain confidential peer review content and named/anonymous reviewer material. They must be stored as sensitive\_review by default.

Outputs derived from review letters should not be shared publicly without redaction.

VenueMemory updates from review letters must be scoped:

this article;  
this venue;  
this submission date;  
this review round;  
not universal journal behavior.

### **126.2. Tacit Signals**

Tacit signals can be powerful and dangerous. If user says “this editor dislikes AI papers” or “this journal only takes people from this circle”, system must store as TACIT\_SIGNAL, with source, date, scope, privacy and confidence. It must not turn it into fact.

Tacit signals should be opt-in for use in FitAssessment. UI should show: “This recommendation uses private/tacit information.”

### **126.3. Personal Data**

SubmissionPack may include personal data. Export and storage must respect sensitivity.

Personal data includes:

author names;  
emails;  
affiliations;  
ORCID;  
funding;  
COI;  
reviewer suggestions;  
opposed reviewers;  
ethics approvals;  
data access statements.

Do not put personal data in logs unless necessary. Do not include personal data in public Vault cards by default.

### **126.4. Project Confidentiality**

Unpublished manuscripts and field notes may contain intellectual property. External LLM/API use should be configurable. Some projects may require local-only or redacted processing.

System should support future processing modes:

standard\_cloud;  
redacted\_cloud;  
local\_only;  
manual\_only;  
no\_external\_llm.

MVP may not implement all, but architecture should not prevent them.

## **127\. Security Constraints**

### **127.1. Secrets**

API keys, tokens, credentials and portal passwords must never be written to:

LLM prompts;  
user-facing reports;  
Vault cards;  
operation traces in plain text;  
logs;  
error messages;  
Git commits.

If an adapter needs credentials, they belong to secure environment configuration or secret store.

### **127.2. External URLs and Files**

URL/file intake must protect against unsafe operations:

no file:// remote fetch;  
no private network SSRF;  
no arbitrary command execution;  
size limits;  
timeout limits;  
content-type validation;  
archive bomb protection;  
malware scanning if needed later;  
PDF extraction sandbox if possible.

### **127.3. Generated Files**

Generated submission packages must not overwrite user originals. Use versioned outputs. External doc writes should require explicit user action.

### **127.4. Audit Integrity**

OperationTrace should be append-only or versioned. User decisions should not be silently overwritten. If decision changes, create new decision record.

## **128\. Operational Constraints**

Journal-Yuga should be designed for staged depth and controlled cost. Deep venue profiling, corpus mining and citation graph analysis can be expensive. The system should not accidentally perform high-cost operations from a casual Telegram message.

### **128.1. Depth Modes**

`quick_scan`:

minimal sources;  
preliminary ArticleModel;  
light VenueModel;  
no deep corpus;  
quick fit label;  
many unknowns.

`light_profile`:

official venue pages;  
basic requirements;  
submission scenario;  
multi-axis preliminary fit.

`deep_profile`:

corpus;  
policies;  
editorial board;  
citation profile;  
more evidence.

`submission_ready`:

fresh requirements;  
compliance;  
reference verification;  
metadata;  
risk resolution.

`post_review`:

review letters;  
revision plan;  
VenueMemory.

Each operation should declare depth mode before running.

### **128.2. Budget Controls**

Operation should estimate:

number of URLs;  
number of articles;  
LLM calls;  
API calls;  
expected time;  
expected cost;  
storage impact.

User or project settings should define default budgets.

### **128.3. Background Work**

Background tasks allowed later:

refresh VenueModel;  
watch CFP;  
check stale guidelines;  
remind about deadline;  
check missing submission items;  
update citation metadata;  
monitor venue sources.

But background tasks must be transparent, with schedule, scope and opt-out.

### **128.4. Failure Handling**

Failures should become state, not disappear.

If adapter fails, store AdapterResult.  
If source inaccessible, store INACCESSIBLE.  
If parse fails, store PARSE\_FAILED.  
If user does not answer, keep Scenario unknown.  
If evidence insufficient, downgrade output.  
If cost budget exceeded, stop with partial result and next-source recommendation.

## **129\. External Service Policy**

Journal-Yuga may rely on external services, but each service must have a declared role and risk.

### **129.1. Build-now Services**

Open/free or self-hostable sources:

OpenAlex;  
Crossref;  
OpenCitations;  
manual URL snapshots;  
GROBID or equivalent local parser;  
Litops storage/provenance;  
existing LLM provider configured for system.

### **129.2. Build-soon Services**

DOAJ;  
Sherpa-like policy source;  
Semantic Scholar;  
Unpaywall;  
AnyStyle/CERMINE/citation-js;  
PhilPapers/PhilEvents if accessible and allowed.

### **129.3. Later / Optional Services**

Scopus;  
Web of Science;  
JCR;  
SJR/Scimago;  
Dimensions;  
Lens;  
Scite;  
plagiarism tools;  
AI content detectors;  
image integrity tools;  
submission portal integrations.

### **129.4. Never-as-MVP Dependency**

No closed paid source should block MVP. If a feature requires paid database, it should degrade gracefully to UNKNOWN\_NOT\_VERIFIED or user-provided snapshot.

## **130\. Legal and Ethical Risk Report Requirements**

RiskReport must include not only academic fit risks, but also legal/ethical categories where relevant.

Risk categories:

copyright;  
full-text storage rights;  
preprint policy;  
self-archiving;  
AI disclosure;  
plagiarism/self-plagiarism;  
authorship disputes;  
funding disclosure;  
COI;  
ethics approval;  
data availability;  
privacy/personal data;  
patent/IP disclosure;  
confidential information;  
dual use if relevant;  
state/commercial secrecy if user flags it.

Each risk must have:

source or reason;  
severity;  
uncertainty;  
mitigation;  
user action;  
whether external expert review needed.

System must not act as lawyer. It can flag risks and recommend checking.

## **131\. Submission System Automation Boundary**

Journal-Yuga should not automate actual submission in MVP.

Allowed in MVP:

create checklist;  
prepare metadata;  
draft cover letter;  
list required files;  
map portal fields;  
export package;  
record submitted status manually.

Not allowed in MVP:

logging into submission portals;  
filling forms automatically;  
submitting manuscript;  
suggesting reviewers automatically without user review;  
emailing editors;  
tracking private portal status through credentials.

Later automation requires explicit security design and user approval.

## **132\. Reviewer and Editorial Contact Boundary**

Journal-Yuga must not automate manipulative editorial contact.

Allowed:

draft polite inquiry if user requests;  
summarize journal scope;  
prepare factual cover letter;  
record user-provided editor contact;  
store correspondence as source.

Not allowed:

fabricate relationship;  
claim endorsement;  
pressure editor;  
generate deceptive pre-submission inquiry;  
pretend article was invited;  
infer private editor preference without source.

## **133\. Predatory and Quality Claims**

Journal-Yuga may flag risks but must avoid defamation-like certainty.

Allowed:

“risk signal: unclear indexing claim”;  
“risk signal: no transparent editorial board found”;  
“risk signal: APC info unclear”;  
“risk signal: publisher page uses suspicious language”;  
“requires human verification.”

Not allowed without strong evidence:

“this journal is predatory”;  
“this conference is fake”;  
“this publisher is fraudulent.”

If using external lists or services, cite source and status.

## **134\. Multilingual and Translation Constraints**

Journal-Yuga may operate across Russian and English. Translation is not neutral.

Rules:

ArticleModel language may differ from target venue language.  
Translation should preserve protected core.  
Disciplinary translation must be distinguished from linguistic translation.  
Changing terms to fit Anglo-American academic idiom may alter theory.  
Citation ecology translation may require new bridge references.  
User must approve major terminological shifts.

Translation outputs should mark:

literal translation;  
disciplinary adaptation;  
rhetorical adaptation;  
conceptual reframe;  
field-core risk.

## **135\. Humanities and Philosophy Specific Constraints**

Humanities/philosophy/STS publication differs from biomedical/STEM norms. Journal-Yuga must not force IMRaD, empirical methods or standardized reporting logic onto conceptual texts.

Rules:

Do not assume method section required.  
Do not assume data availability applies.  
Do not assume citation recency is always primary quality signal.  
Do not assume article structure is IMRaD.  
Do not assume “lack of empirical data” is weakness for conceptual venue.  
Do not flatten philosophical vocabulary into generic social science language without user acceptance.  
Do not overvalue bibliometric metrics over field fit in humanities contexts.

PublicationRegimeModel should handle:

conceptual article;  
theoretical essay;  
forum piece;  
book symposium;  
special issue;  
STS case/theory hybrid;  
AI ethics article;  
digital humanities article;  
edited volume chapter;  
conference proceedings.

## **136\. Operational Role of Human Expert**

Journal-Yuga should assume that high-stakes publication decisions may need human expert review.

Human expert review recommended when:

major reframe;  
high prestige venue;  
legal/ethical uncertainty;  
sensitive data;  
patent/IP risk;  
ambiguous authorship;  
severe reviewer conflict;  
predatory risk;  
high field-core risk;  
unverified indexing requirement;  
large APC commitment.

System should flag “human expert recommended”, not pretend to settle.

## **137\. Constraints for Coding Agents**

Coding agents implementing Journal-Yuga must observe operational constraints.

They must not:

commit secrets;  
hardcode API keys;  
build scraping that violates ToS;  
create automatic submission;  
store sensitive review text in public fixtures;  
use real user manuscripts in tests;  
create demo data that resembles private data;  
strip evidence fields to simplify schemas;  
remove unknown statuses;  
replace quality gates with comments;  
build a chat-only prototype and call it MVP;  
implement reviewer simulation before evidence gates;  
implement full rewrite before protected-core workflow.

They must:

use synthetic fixtures;  
mark test data clearly;  
write negative tests;  
preserve source/evidence fields;  
implement privacy fields even if simple;  
log operation traces without secrets;  
make failure states explicit;  
document unsupported services.

## **138\. Incident and Error Policy**

Journal-Yuga should define incident classes.

`source_misuse` — output used unregistered or unsupported source.

`privacy_leak` — sensitive content exported to wrong surface.

`hallucinated_reference` — generated reference not verified but presented as real.

`false_ready_submission` — pack marked ready despite missing requirement.

`destructive_rewrite` — protected core changed without user decision.

`unsupported_fit_claim` — strong fit claim without evidence.

`credential_leak` — secret exposed.

`wrong_venue_identity` — assessment built for wrong journal/venue.

`stale_policy_use` — stale guidelines used as current without warning.

Each incident should produce:

incident\_id;  
type;  
severity;  
affected\_entities;  
detected\_at;  
cause;  
mitigation;  
regression\_test\_required;  
status.

## **139\. Constraints Layer Acceptance Criteria**

This layer is accepted only if:

privacy/sensitivity fields exist in schemas;  
EvidenceStatus taxonomy implemented;  
operation traces avoid secrets;  
SubmissionPack cannot be ready without quality gate;  
ReviewerSimulation is disabled or clearly bounded;  
CitationPlan cannot mark unverified reference as verified;  
TacitVenueSignal cannot become fact;  
stale sources downgrade outputs;  
protected-core changes require user decision;  
external submission automation is not in MVP;  
paid/closed APIs are optional;  
negative tests cover major prohibitions.

## **140\. Wave 9 Closure**

This wave defines the constraints that protect Journal-Yuga from becoming a publication-manipulation machine or a confident hallucination layer. The system may be powerful only if it is also bounded: no fake references, no fake review, no hidden source use, no silent protected-core rewrite, no submission-ready status without fresh evidence, no private material leakage, no automatic portal submission in MVP, no paid database dependency for core function. These constraints are not secondary. They shape schemas, UI, agents, quality gates and roadmap.

The next wave should be final implementation slicing: MVP roadmap, module structure, files/directories, first coding tasks, acceptance tests, fixtures, order of implementation, and the exact point **JOURNAL\_YUGA\_TECHNICAL\_SPEC\_FOR\_CLAUDE\_v0\_1**

## **Волна 10\. MVP Roadmap, Implementation Slicing, Module Structure, Backlog and First Coding Handoff**

## **141\. Purpose of Implementation Slicing**

Implementation slicing нужен для того, чтобы Journal-Yuga не был реализован как хаотический набор “полезных функций”: подобрать журнал, проверить статью, написать cover letter, сделать отчёт, сгенерировать список правок. Такая реализация почти гарантированно разрушит архитектуру. Система станет обычным LLM-wrapper-ом вокруг пары prompts and search calls, а все ключевые различения — ArticleModel vs manuscript, VenueModel vs author guidelines, fit vs score, evidence vs inference, rewrite vs reframe, submission pack vs advice — исчезнут в первом же coding pass.

Правильная реализация должна идти от доменной основы к операциям, а не от видимого UI к данным. Сначала фиксируются схемы, статусы, registries, evidence model, operation trace, quality gates and fixtures. Затем реализуется минимальный рабочий путь: one manuscript × one target venue. Только после этого можно строить venue pool, deep profile, citation ecology, submission pack, WhiteCrow PatchQueue and review loop. Если начать с journal search или polished interface, будет построена оболочка без онтологического двигателя.

Цель этой волны — превратить всё предыдущее описание в последовательность безопасных implementation slices. Каждый slice должен быть достаточно большим, чтобы Claude/coding agent не занимался микрошагами, но достаточно ограниченным, чтобы не переписать всё и не смешать слои. Каждый slice должен иметь scope, non-scope, files/modules, entities, tests, acceptance criteria, manual smoke test and failure conditions.

## **142\. Global Implementation Principles**

### **142.1. Domain first, UI later**

Первый coding pass должен создавать domain skeleton. UI может быть CLI, markdown artifact or minimal web panel, но не должен определять архитектуру. Нельзя начинать с “страницы подбора журналов”. Нельзя начинать с “чатового бота для Journal-Yuga”. Нельзя начинать с красивой таблицы venues. Все эти поверхности должны потреблять domain objects, а не производить их ad hoc.

### **142.2. Evidence before recommendation**

Нельзя реализовывать recommendation before evidence. Даже preliminary fit должен ссылаться на ArticleModel, VenueModel, SubmissionScenario and EvidenceItems. Если source/evidence layer не готов, fit может существовать только как stub/test fixture.

### **142.3. One manuscript × one venue before venue pool**

Venue pool discovery выглядит более продуктово, но архитектурно он вторичен. Если система не умеет глубоко и проверяемо сравнить один текст с одним venue, она не сможет честно сравнить десять venues. Поэтому MVP-1 всегда one manuscript × one target venue.

### **142.4. Structured objects before prose reports**

Каждая функция должна создавать typed entity. Human-readable report является projection, not canonical output. Если код создаёт только markdown report, feature не считается реализованной.

### **142.5. Quality gates before “done”**

Каждый MVP slice должен иметь negative tests. Например, abstract-only input должен давать preliminary status; missing guidelines must block submission-ready; fake reference must not be verified; stale policy must downgrade readiness. Без негативных тестов feature считается недоделанной.

### **142.6. No paid/closed source dependency in MVP**

MVP не должен зависеть от Scopus/WoS/JCR/ISSN Portal/Dimensions/Lens/Scite or paid plagiarism tools. Эти источники могут появиться как manual snapshot or future adapter, but core must work with open/manual sources.

### **142.7. No full automation of submission**

SubmissionPack в MVP — это operational checklist and exportable pack, not automated portal submission. Система не должна логиниться в OJS/Editorial Manager/ScholarOne or submit manuscript.

### **142.8. No reviewer simulation before evidence layer**

ReviewerSimulation is dangerous if introduced early. It belongs after ArticleModel, VenueModel, FitAssessment, RiskReport and evidence audit are stable. Until then only schema/prohibition exists.

## **143\. Recommended Repository Placement**

Journal-Yuga должен сначала жить внутри Litops repo as bounded context, because Litops already owns Source, RAW/INBOX/Vault, provenance, registry and Telegram intake. Later it can be extracted as separate package or service.

Recommended docs path:

`docs/journal_yuga/JOURNAL_YUGA_TECHNICAL_SPEC_FOR_CLAUDE_v0_1.md`  
`docs/journal_yuga/JOURNAL_YUGA_CONSTITUTION_SOURCE_MAP.md`  
`docs/journal_yuga/JOURNAL_YUGA_MVP_ROADMAP.md`  
`docs/journal_yuga/JOURNAL_YUGA_AGENT_PROMPT_FAMILIES.md`  
`docs/journal_yuga/JOURNAL_YUGA_EVALUATION_GATES.md`

Recommended code namespace:

`litops/journal_yuga/`

This namespace must not pollute root Litops modules until interfaces are stable.

## **144\. Recommended Module Structure**

Target module structure:

litops/journal\_yuga/

  \_\_init\_\_.py

  ids.py

  schema.py

  enums.py

  registry.py

  serialization.py

  evidence.py

  claims.py

  quality.py

  traces.py

  decisions.py

  adapters/

    \_\_init\_\_.py

    base.py

    manual\_url.py

    file\_extract.py

    openalex.py

    crossref.py

    opencitations.py

    grobid.py

    doaj.py

    sherpa.py

    semantic\_scholar.py

    unpaywall.py

  services/

    \_\_init\_\_.py

    article\_modeling.py

    venue\_profiling.py

    scenario.py

    fit\_assessment.py

    mismatch\_mapping.py

    rewrite\_planning.py

    citation\_planning.py

    risk\_reporting.py

    compliance.py

    submission\_pack.py

    review\_loop.py

    venue\_memory.py

    evidence\_audit.py

  pipelines/

    \_\_init\_\_.py

    base.py

    manuscript\_venue\_fit.py

    venue\_deep\_profile.py

    venue\_pool\_discovery.py

    reverse\_design.py

    submission\_pack\_generation.py

    review\_rebuttal\_loop.py

    q3\_conference\_fallback.py

  prompts/

    \_\_init\_\_.py

    registry.py

    article\_modeling.md

    venue\_fact\_extraction.md

    scenario\_interview.md

    fit\_assessment.md

    mismatch\_mapping.md

    rewrite\_planning.md

    citation\_planning.md

    risk\_reporting.md

    compliance\_checklist.md

    submission\_pack.md

    evidence\_audit.md

  cards.py

  artifacts.py

  cli.py

  api.py

  telegram.py

Test structure:

tests/journal\_yuga/

  fixtures/

    manuscripts/

    venues/

    guidelines/

    cfps/

    reviews/

    corpora/

    references/

    expected/

  test\_schema.py

  test\_registry.py

  test\_evidence.py

  test\_quality\_gates.py

  test\_article\_modeling.py

  test\_venue\_profiling.py

  test\_fit\_assessment.py

  test\_mismatch\_mapping.py

  test\_rewrite\_planning.py

  test\_citation\_planning.py

  test\_risk\_reporting.py

  test\_compliance.py

  test\_submission\_pack.py

  test\_pipelines\_manuscript\_venue.py

  test\_cards.py

  test\_cli.py

The module structure can be simplified in early MVP, but the boundary must remain: schema, evidence, services, pipelines, quality gates and projections are separate concerns.

## **145\. Persistence Strategy**

MVP persistence can use JSONL registries consistent with Litops. Later, if needed, Journal-Yuga can migrate to SQLite/Postgres or typed document store. The domain model should not depend on JSONL forever, but JSONL is acceptable for first implementation because it is transparent, append-friendly and easy to inspect.

Recommended registry files:

05\_REGISTRY\_EXPORT/journal\_yuga/

  article\_models.jsonl

  manuscripts.jsonl

  field\_refs.jsonl

  article\_variants.jsonl

  venue\_models.jsonl

  journal\_models.jsonl

  publication\_regimes.jsonl

  editorial\_profiles.jsonl

  article\_corpora.jsonl

  article\_patterns.jsonl

  citation\_profiles.jsonl

  tacit\_signals.jsonl

  submission\_scenarios.jsonl

  fit\_assessments.jsonl

  mismatch\_maps.jsonl

  rewrite\_plans.jsonl

  reframe\_plans.jsonl

  citation\_plans.jsonl

  risk\_reports.jsonl

  compliance\_checklists.jsonl

  submission\_packs.jsonl

  review\_outcomes.jsonl

  revision\_plans.jsonl

  venue\_memory.jsonl

  evidence\_items.jsonl

  source\_snapshots.jsonl

  pipeline\_runs.jsonl

  operation\_traces.jsonl

  user\_decisions.jsonl

  incidents.jsonl

Registry records should be append-only or versioned. Updates may write new versions rather than mutating old records silently. For MVP, update-in-place may be acceptable only if tests and traces preserve history, but append/version is preferable.

Human-readable cards should go into Vault projection, not RAW or INBOX. RAW remains original sources, INBOX remains dirty intake, Vault is human-readable projection.

## **146\. ID Strategy**

Journal-Yuga should use explicit prefixes for IDs.

Recommended prefixes:

`jy-art-` ArticleModel  
`jy-ms-` ManuscriptModel  
`jy-field-` FieldModelReference  
`jy-var-` ArticleVariant  
`jy-venue-` VenueModel  
`jy-journal-` JournalModel  
`jy-regime-` PublicationRegimeModel  
`jy-board-` EditorialBoardProfile  
`jy-corpus-` PublishedArticleCorpus  
`jy-pattern-` PublishedArticlePattern  
`jy-citeprof-` CitationExpectationProfile  
`jy-scenario-` SubmissionScenario  
`jy-fit-` FitAssessment  
`jy-mismatch-` MismatchMap  
`jy-rewrite-` RewritePlan  
`jy-reframe-` ReframePlan  
`jy-citeplan-` CitationPlan  
`jy-risk-` RiskReport  
`jy-compliance-` ComplianceChecklist  
`jy-pack-` SubmissionPack  
`jy-review-` ReviewOutcome  
`jy-revision-` RevisionPlan  
`jy-memory-` VenueMemory  
`jy-evid-` EvidenceItem  
`jy-snap-` SourceSnapshot  
`jy-run-` PipelineRun  
`jy-trace-` OperationTrace  
`jy-decision-` UserDecision  
`jy-incident-` Incident

IDs should be stable, sortable if possible, and not leak sensitive content.

## **147\. MVP-0: Domain Skeleton**

### **147.1. Goal**

MVP-0 creates the domain skeleton. It does not perform real venue fit yet. Its purpose is to make the architecture impossible to collapse into free prose.

### **147.2. Scope**

Implement:

enums;  
ID generation;  
schema dataclasses or pydantic models;  
serialization;  
registry append/read/list;  
EvidenceStatus taxonomy;  
lifecycle statuses;  
PipelineRun;  
OperationTrace;  
UserDecision;  
basic quality gate result;  
basic Vault card skeletons;  
fixtures;  
unit tests.

### **147.3. Entities Required**

MVP-0 must include at least:

ArticleModel;  
ManuscriptModel;  
VenueModel;  
JournalModel;  
PublicationRegimeModel;  
SubmissionScenario;  
EvidenceItem;  
SourceSnapshot;  
FitAssessment;  
MismatchMap;  
RewritePlan;  
CitationPlan;  
RiskReport;  
ComplianceChecklist;  
SubmissionPack;  
PipelineRun;  
OperationTrace;  
QualityGateResult.

### **147.4. Non-Scope**

No real LLM prompts.  
No external API adapters beyond stubs.  
No UI.  
No Telegram commands.  
No reviewer simulation.  
No journal pool discovery.  
No automatic source fetching unless already available in Litops.  
No full reports.

### **147.5. Acceptance Criteria**

MVP-0 is accepted when:

all required schemas serialize/deserialize;  
registry writes and reads records;  
EvidenceStatus enum exists;  
unknowns field exists where needed;  
source\_refs/context\_pack\_refs exist;  
quality gate result can be stored;  
operation trace can be stored;  
basic markdown card can be generated from ArticleModel and VenueModel;  
tests cover missing required fields and invalid enum values.

### **147.6. Negative Tests**

Invalid evidence status rejected.  
FitAssessment cannot be created without ArticleModel ref and VenueModel ref unless marked invalid/preliminary.  
SubmissionPack cannot have ready status without compliance ref.  
VenueModel indexing field cannot be plain string without evidence status structure.  
CitationPlan concrete reference cannot be verified without source/ref evidence.

## **148\. MVP-1: One Manuscript × One Target Venue**

### **148.1. Goal**

MVP-1 implements the first real product path: one article input compared to one target venue, producing structured preliminary or evidence-backed outputs.

### **148.2. Scope**

Implement pipeline:

article input → ManuscriptModel → ArticleModel;  
venue input → light VenueModel;  
minimal SubmissionScenario;  
FitAssessment;  
MismatchMap;  
RewritePlan action list;  
RiskReport;  
ComplianceChecklist;  
human-readable artifact;  
operation trace;  
quality gates.

### **148.3. Inputs**

MVP-1 may use fixtures and manually provided sources:

manuscript markdown/text fixture;  
venue homepage/guidelines markdown fixture;  
submission scenario fixture.

Real source fetching can be minimal. The core is entity flow and gates.

### **148.4. Required Services**

Article Modeling Service, deterministic or LLM-assisted.  
Venue Profiling Service light mode.  
Scenario Service minimal.  
Fit Assessment Service.  
Mismatch Mapping Service.  
Rewrite Planning Service action-plan mode.  
Risk Reporting Service.  
Compliance Service simple.  
Evidence Auditor.

### **148.5. Non-Scope**

No venue pool.  
No deep corpus.  
No verified new references.  
No full rewrite.  
No submission ready status.  
No automatic external document patch.  
No review loop.

### **148.6. Acceptance Criteria**

Given fixture manuscript and fixture venue guidelines, system creates:

ArticleModel;  
ManuscriptModel;  
VenueModel;  
PublicationRegimeModel;  
SubmissionScenario;  
FitAssessment with multiple axes;  
MismatchMap;  
RewritePlan;  
RiskReport;  
ComplianceChecklist;  
Artifact markdown report;  
OperationTrace.

Report must include:

ArticleModel summary;  
VenueModel summary;  
Scenario;  
Fit matrix;  
Mismatch table;  
Rewrite actions;  
Risk table;  
Compliance checklist;  
Evidence/unknowns;  
quality status.

### **148.7. Negative Tests**

Abstract-only input produces preliminary ArticleModel and preliminary FitAssessment.

Missing author guidelines blocks submission readiness.

Missing protected core marks rewrite core impact as unknown and requires user question.

Venue source inaccessible marks VenueModel fields INACCESSIBLE/UNKNOWN.

FitAssessment cannot output single score.

Unsupported fit claim is downgraded by Evidence Auditor.

## **149\. MVP-2: Light Venue Deep Profile**

### **149.1. Goal**

MVP-2 makes VenueProfile reusable independently from immediate article fit.

### **149.2. Scope**

Implement venue profile pipeline light mode:

resolve venue;  
collect/register sources if available;  
extract light fields;  
build VenueModel;  
build JournalModel;  
assign PublicationRegimeModel;  
extract basic requirements;  
create VenueProfile artifact and Vault card.

### **149.3. Required Inputs**

Venue URL or manually prepared fixture sources.

### **149.4. Required Outputs**

VenueModel;  
JournalModel;  
PublicationRegimeModel;  
EvidenceItems;  
SourceSnapshot refs;  
VenueProfile markdown;  
source acquisition report;  
quality gate result.

### **149.5. Non-Scope**

No 20–50 article corpus.  
No editorial board analysis beyond source capture.  
No full citation profile.  
No scheduled refresh.  
No paid metrics.

### **149.6. Acceptance Criteria**

System can create light venue profile from official page/guidelines fixture.

Unknown fields are visible.

Vendor claims are marked.

Special issue URL creates or suggests Issue/SpecialIssue model instead of only parent JournalModel.

## **150\. MVP-3: Citation and Reference Layer**

### **150.1. Goal**

MVP-3 prevents citation hallucination and enables basic CitationPlan.

### **150.2. Scope**

Implement:

bibliography extraction status;  
reference parser interface;  
Crossref lookup interface;  
OpenCitations lookup interface;  
ReferenceVerificationResult;  
CitationPlan tasks;  
citation audit.

### **150.3. Minimal Behavior**

The system can take a bibliography list, verify DOI-bearing references, mark unresolved references, create missing bridge categories and warn against padding.

### **150.4. Non-Scope**

No fully automated literature review.  
No “add these 20 sources” without verification.  
No field-specific citation graph ranking unless data exists.

### **150.5. Acceptance Criteria**

Fake DOI remains unresolved.  
Real DOI fixture resolves.  
Unresolved reference not marked fake.  
CitationPlan distinguishes verified reference from search task.  
CitationPlan links citation tasks to MismatchMap or ArticleModel needs.

## **151\. MVP-4: Venue Pool Discovery and Comparison**

### **151.1. Goal**

MVP-4 adds candidate venue discovery and comparison without pretending that light screening equals deep fit.

### **151.2. Scope**

Implement:

candidate venue records;  
light VenueModel per candidate;  
dedup/canonicalization;  
preliminary screening matrix;  
evidence level per venue;  
recommendation for deep profile targets.

### **151.3. Inputs**

ArticleModel;  
SubmissionScenario;  
seed venues or adapter search results.

### **151.4. Non-Scope**

No final ranking as truth.  
No acceptance probability.  
No deep comparison if venue profiles are light.  
No Scopus/WoS/JCR dependency.

### **151.5. Acceptance Criteria**

Matrix includes evidence level and unknown count.

Venues with missing data are marked unknown, not bad.

System recommends 3–5 venues for deep profile rather than pretending full decision is made.

Publisher-owned candidates are marked if known.

## **152\. MVP-5: SubmissionPack Draft**

### **152.1. Goal**

MVP-5 creates operational submission package draft.

### **152.2. Scope**

Implement:

SubmissionPack entity;  
metadata table;  
missing items;  
cover letter skeleton;  
file list;  
required statements list;  
portal field mapping stub;  
ready status logic.

### **152.3. Non-Scope**

No automatic submission.  
No portal login.  
No final legal/ethical certification.  
No final cover letter without user acceptance.

### **152.4. Acceptance Criteria**

SubmissionPack cannot be ready with missing required metadata.

Stale guidelines downgrade status.

Cover letter skeleton uses ArticleModel and VenueModel; no fabricated claims.

Missing statements appear as tasks.

Ready status can be `ready_for_manual_submission` only after gates pass.

## **153\. MVP-6: WhiteCrow PatchQueue Integration**

### **153.1. Goal**

MVP-6 connects publication adaptation to manuscript evolution.

### **153.2. Scope**

Implement:

convert RewritePlan changes to patch candidates;  
include evidence refs;  
include field-core impact;  
send/export to WhiteCrow PatchQueue interface;  
record user decisions.

### **153.3. Non-Scope**

No silent manuscript editing.  
No automatic full rewrite.  
No core-touching change without user acceptance.

### **153.4. Acceptance Criteria**

Accepted RewritePlan item becomes patch candidate.

Rejected item remains recorded.

Core-touching item cannot be applied without explicit decision.

Patch candidate links back to mismatch and evidence.

## **154\. MVP-7: Review / Rebuttal / VenueMemory Loop**

### **154.1. Goal**

MVP-7 enables post-submission learning and revision support.

### **154.2. Scope**

Implement:

ReviewOutcome;  
review letter intake;  
issue map;  
RevisionPlan;  
RebuttalOutline;  
VenueMemory update;  
comparison with prior FitAssessment.

### **154.3. Non-Scope**

No acceptance guarantee.  
No fake reviewer simulation.  
No automatic rebuttal submission.

### **154.4. Acceptance Criteria**

Review comments mapped to issue types.

RevisionPlan actions link to comments.

RebuttalOutline does not invent changes.

VenueMemory update is scoped to specific submission/outcome.

## **155\. MVP-8: Scheduled Refresh and Attention Loop**

### **155.1. Goal**

MVP-8 introduces proactive maintenance.

### **155.2. Scope**

Implement:

stale venue source detection;  
manual refresh;  
deadline reminders;  
missing submission item reminders;  
pending decision reminders;  
review response due reminders.

### **155.3. Non-Scope**

No broad web crawling.  
No Telegram channel CFP crawling in MVP.  
No hidden background deep research.

### **155.4. Acceptance Criteria**

System can list stale sources.

System can notify user that guidelines need refresh.

System can show pending decisions.

User can snooze/close reminders.

## **156\. Implementation Backlog**

### **156.1. Data and Adapter Backlog**

DOAJ adapter;  
Sherpa adapter;  
Semantic Scholar adapter;  
Unpaywall adapter;  
PhilPapers/PhilEvents adapter;  
H-Net/association CFP watcher;  
SJR/Scimago manual snapshot support;  
Scopus/WoS/JCR paid snapshot support;  
Dimensions/Lens/Scite optional;  
publisher-specific page extractors;  
scheduled venue refresh.

### **156.2. Corpus and Analysis Backlog**

20–50 article corpus miner;  
section-specific corpus;  
special issue corpus;  
abstract move analysis;  
citation age distribution;  
genre pattern detection;  
disciplinary vocabulary extraction;  
field bridge detection;  
humanities-specific article pattern library.

### **156.3. UX Backlog**

full web workspace;  
visual MismatchMap graph;  
Fit/Effort/Risk matrix;  
interactive Evidence Panel;  
SubmissionPack workspace;  
Review/Rebuttal workspace;  
VenueMemory browser;  
Research Budget Control;  
side-by-side venue comparison.

### **156.4. Automation Backlog**

CFP watchers;  
Telegram channel ingestion;  
association page monitoring;  
submission portal profiles;  
external doc comments;  
Google Docs patch export;  
cover letter export;  
DOCX export;  
review deadline tracking.

### **156.5. Integrity and Compliance Backlog**

plagiarism tool integration;  
AI disclosure helper;  
image integrity service;  
ethics statement templates;  
CRediT role mapper;  
data availability checker;  
patent/IP risk checklist;  
privacy redaction export.

### **156.6. Advanced Intelligence Backlog**

ReviewerSimulation risk mode;  
acceptance outcome calibration;  
VenueMemory learning;  
sibling manuscript trajectory planner;  
reverse design for venue pool;  
disciplinary translation engine;  
citation ecology graph;  
tacit signal reasoning with privacy controls.

## **157\. First Coding Handoff Boundary**

Coding handoff begins only after the technical spec file exists in the repo. The first coding agent should not be asked to “build Journal-Yuga”. It should be asked to create MVP-0 domain skeleton.

The first coding handoff is:

Create Journal-Yuga module namespace, schemas, enums, registries, evidence status taxonomy, operation trace, quality gate result, basic cards and tests. Do not implement UI. Do not implement real external adapters except stubs. Do not implement LLM prompts except prompt family placeholders. Do not implement venue search. Do not implement reviewer simulation.

This is the safe first implementation.

## **158\. Recommended First Coding Batch**

The first coding batch should include:

create `litops/journal_yuga/`;  
create `enums.py`;  
create `ids.py`;  
create `schema.py`;  
create `registry.py`;  
create `evidence.py`;  
create `quality.py`;  
create `traces.py`;  
create `cards.py`;  
create `pipelines/base.py`;  
create fixtures;  
create tests for schema/registry/evidence/quality/cards.

Acceptance:

tests pass;  
fixtures load;  
sample ArticleModel and VenueModel can be written/read;  
sample FitAssessment can be created with preliminary status;  
sample card can be generated;  
EvidenceStatus values preserved;  
invalid ready SubmissionPack rejected/downgraded.

## **159\. Recommended Second Coding Batch**

Second batch implements MVP-1 fixture pipeline.

Include:

ArticleModel creation from markdown fixture;  
VenueModel creation from guidelines fixture;  
SubmissionScenario fixture;  
FitAssessment service;  
MismatchMap service;  
RewritePlan service action-list mode;  
RiskReport service;  
ComplianceChecklist service;  
Evidence Auditor basic;  
markdown artifact generation;  
tests.

No external web fetching required yet. This protects domain logic before adapter complexity.

## **160\. Recommended Third Coding Batch**

Third batch adds source acquisition and adapters.

Include:

manual URL snapshot adapter;  
file extraction adapter interface;  
OpenAlex adapter stub or real minimal;  
Crossref DOI lookup minimal;  
OpenCitations minimal;  
SourceSnapshot and EvidenceItem creation from adapter results;  
adapter tests with mocked responses;  
source acquisition quality gate.

This should come after MVP-1 domain pipeline, not before.

## **161\. Recommended Fourth Coding Batch**

Fourth batch upgrades venue profile.

Include:

Venue Deep Profile light pipeline;  
author guidelines extraction;  
policy extraction where possible;  
PublicationRegime classification;  
VenueProfile artifact;  
Venue Vault card;  
quality gates.

## **162\. Recommended Fifth Coding Batch**

Fifth batch introduces CitationPlan.

Include:

reference parser interface;  
Crossref verification;  
CitationPlan tasks;  
Citation Audit;  
fake reference negative tests;  
no invented references.

## **163\. Recommended Sixth Coding Batch**

Sixth batch introduces UI/API/CLI surface.

Start with CLI/API, not full web UI.

Commands:

`journal-yuga article-model`  
`journal-yuga venue-profile`  
`journal-yuga fit`  
`journal-yuga report`  
`journal-yuga evidence-audit`

Web UI can come after CLI/API proves domain flow.

## **164\. Recommended Seventh Coding Batch**

Seventh batch introduces Telegram thin layer.

Telegram commands should call existing pipelines:

`/jy_fit`  
`/jy_venue`  
`/jy_status`  
`/jy_get`  
`/jy_pack`

Telegram must not contain domain logic. It only creates jobs and returns short summaries.

## **165\. Implementation Anti-Patterns**

Reject implementation if it does any of the following:

creates `journal_finder.py` as main module;  
stores fit as string report only;  
adds one LLM prompt that does everything;  
builds UI before schemas;  
uses model memory as evidence;  
stores journal facts without source refs;  
creates numeric fit score first;  
marks submission ready without gates;  
implements reviewer simulation early;  
creates citations without verification;  
rewrites manuscript directly;  
hides unknown fields;  
uses paid APIs as required;  
ignores Litops Source/ContextPack;  
ignores WhiteCrow protected core.

## **166\. Developer Reports Required After Each Batch**

Every coding batch must end with implementation report:

files created;  
files modified;  
entities implemented;  
services implemented;  
pipelines implemented;  
tests added;  
tests passing/failing;  
fixtures added;  
manual smoke test command;  
known limitations;  
spec sections covered;  
spec sections not covered;  
next recommended batch.

The report should not claim “complete” without mapping to spec sections and tests.

## **167\. Manual Smoke Tests**

### **167.1. MVP-0 Smoke**

Run command or script that creates sample ArticleModel, VenueModel, FitAssessment, writes registries, reads them, generates card.

Expected:

records exist;  
ids valid;  
evidence statuses preserved;  
card generated;  
tests pass.

### **167.2. MVP-1 Smoke**

Input fixture:

one markdown manuscript;  
one markdown venue guidelines page;  
one scenario YAML/JSON.

Expected:

ArticleModel;  
VenueModel;  
FitAssessment;  
MismatchMap;  
RewritePlan;  
RiskReport;  
ComplianceChecklist;  
artifact report.

Expected warnings:

if fixture lacks bibliography, CitationPlan limited;  
if protected core absent, core-risk unknown.

### **167.3. Adapter Smoke**

Input:

one URL or mocked HTML page;  
one DOI;  
one small bibliography.

Expected:

SourceSnapshot;  
EvidenceItems;  
Crossref result or unresolved;  
OpenCitations result or coverage warning.

### **167.4. Negative Smoke**

Input:

fake venue;  
abstract only;  
missing guidelines;  
fake DOI;  
stale policy.

Expected:

preliminary/downgraded statuses;  
no ready submission;  
no fake reference;  
unknowns visible.

## **168\. Versioning Strategy**

Technical spec version: `v0_1`.

Domain schema version: `journal_yuga_schema_v0_1`.

Prompt family version: `jy_prompt_family_v0_1`.

Quality gate version: `jy_quality_gates_v0_1`.

Every output should record schema\_version and prompt\_family\_version if LLM involved.

Breaking schema changes require migration or explicit version handling.

## **169\. Roadmap Summary**

Phase 0: Spec and source map.  
Phase 1: Domain skeleton.  
Phase 2: One manuscript × one venue fixture pipeline.  
Phase 3: Source acquisition and evidence adapters.  
Phase 4: Light venue deep profile.  
Phase 5: Citation/reference layer.  
Phase 6: CLI/API and artifact export.  
Phase 7: Telegram thin layer.  
Phase 8: SubmissionPack draft.  
Phase 9: WhiteCrow PatchQueue integration.  
Phase 10: Venue pool discovery.  
Phase 11: Review/rebuttal loop.  
Phase 12: Full web UI.  
Phase 13: Advanced adapters and scheduled refresh.  
Phase 14: Corpus mining and citation ecology.  
Phase 15: Reviewer risk simulation and VenueMemory learning.

The sequence may be adjusted, but Phase 1–3 should not be skipped.

## **170\. Final Definition of the First Product**

The first real Journal-Yuga product is not a market-wide recommender. It is:

A source-grounded one-manuscript / one-venue fit engine that builds ArticleModel, VenueModel, SubmissionScenario, FitAssessment, MismatchMap, RewritePlan, RiskReport and ComplianceChecklist, with evidence refs, unknowns, quality gates, operation trace and human-readable artifact.

Everything else grows from this.

## **171\. Final Technical Handoff State**

The technical specification becomes coding handoff when the repository contains:

this spec under `docs/journal_yuga/`;  
source map or constitution reference;  
MVP roadmap;  
implementation batch list;  
acceptance criteria;  
test fixture plan.

After that, coding agents should start from MVP-0, not redesign the product.

## **172\. Wave 10 Closure**

This wave completes the first technical specification skeleton. The implementation path is now bounded: domain skeleton first, one manuscript × one venue second, evidence adapters third, venue profile and citation layer after that, then UI, Telegram, submission pack, WhiteCrow integration and review loop. The system should be grown from typed entities, evidence and quality gates, not from chat outputs or journal search UI. The first coding handoff is safe only if it asks for MVP-0 domain skeleton with tests.

where the technical specification becomes coding handoff.

