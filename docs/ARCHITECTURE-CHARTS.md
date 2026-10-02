# DJONE — Architecture Charts

> Repository: `appolon1908/DJONE`  
> Baseline branch: `main`  
> Repository-local visual architecture. Keep these diagrams aligned with source, contracts and deployment.

## 1. System context
```mermaid
flowchart LR
 A["DJ operator / agent"] --> B["DJONE API + orchestration"]
 B --> R["DJONE<br/>AI-assisted DJ workstation/control plane"]
 R --> S["library/queue/session state"]
 R --> D["Mixxx / remix / stems / streaming"]
```

## 2. Internal component architecture
```mermaid
flowchart TB
 I["Entrypoint / API / CLI / worker"] --> P["Identity, policy, validation"]
 P --> C["Core domain / orchestration"]
 C --> S["State / configuration / persistence"]
 C --> A["Adapters / integrations"]
 A --> X["Approved dependencies"]
 C --> O["Metrics, logs, traces, audit"]
```

## 3. Critical flow
```mermaid
sequenceDiagram
 participant U as Caller
 participant B as DJONE
 participant P as Policy
 participant C as Core
 participant S as State
 participant X as Dependency
 U->>B: Request / event / action
 B->>P: Authenticate + validate
 P-->>B: Decision
 B->>C: Select media, apply policy, issue Mixxx command and verify playback
 C->>S: Read / persist
 C->>X: Bounded integration
 X-->>C: Result / readback
 C-->>U: Normalized response
```

## 4. Deployment and promotion
```mermaid
flowchart LR
 F["Feature branch"] --> T["Tests / validation"]
 T --> PR["Pull request + review"]
 PR --> CI["CI green"]
 CI --> ST["Staging / isolated verification"]
 ST --> EX["Exact-SHA certification"]
 EX --> G{"Production approval?"}
 G -- No --> ST
 G -- Yes --> P["Production promotion"]
 P --> H["Health/readiness + rollback check"]
```

## 5. Observability and recovery
```mermaid
flowchart LR
 R["DJONE"] --> M["Metrics"]
 R --> L["Logs / audit"]
 R --> T["Traces / correlation"]
 M --> O["Observability stack"]
 L --> O
 T --> O
 O --> A["Dashboards / alerts"]
 R --> B["Backup / config snapshot"]
 B --> RR["Restore / rollback rehearsal"]
```

## Ownership notes
- **Role:** AI-assisted DJ workstation/control plane
- **Primary boundary:** DJONE API + orchestration
- **State/config:** library/queue/session state
- **Dependencies/consumers:** Mixxx / remix / stems / streaming
- Cross-repository effects must use reviewed contracts; production effects remain separately gated.
