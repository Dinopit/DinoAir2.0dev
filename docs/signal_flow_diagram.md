# Signal Flow Diagram - Complete Architecture

## Complete Signal Flow Architecture

```mermaid
graph TB
    subgraph "Main Application Layer"
        MW[MainWindow<br/>- Central hub<br/>- Window management]
        TC[TabbedContentWidget<br/>- Tab management<br/>- Page container]
    end
    
    subgraph "Signal Coordination Layer"
        SC[SignalCoordinator<br/>- Signal routing<br/>- State synchronization]
        FSM[FilterStateManager<br/>- Project filter state<br/>- Subscriber notifications]
        SD[SignalDebugger<br/>- Signal monitoring<br/>- Debug logging]
    end
    
    subgraph "Page Layer"
        AP[ArtifactsPage<br/>- Artifact management<br/>- Project associations]
        PP[ProjectsPage<br/>- Project hierarchy<br/>- Cross-references]
        NP[NotesPage<br/>- Note management]
        CP[CalendarPage<br/>- Event management]
    end
    
    subgraph "Component Layer"
        PCB[ProjectComboBox<br/>- Shared component<br/>- Filter selector]
        AT[ArtifactTree<br/>- Visual hierarchy<br/>- Project badges]
        PT[ProjectTree<br/>- Project structure<br/>- Item counts]
    end
    
    subgraph "Data Layer"
        ADB[ArtifactsDB]
        PDB[ProjectsDB]
        NDB[NotesDB]
        CDB[CalendarDB]
    end
    
    %% Main connections
    MW --> TC
    TC --> SC
    SC --> FSM
    SC --> SD
    
    %% Page connections
    SC <--> AP
    SC <--> PP
    SC <--> NP
    SC <--> CP
    
    %% Component connections
    AP --> PCB
    AP --> AT
    PP --> PT
    PP --> PCB
    
    %% Data connections
    AP --> ADB
    PP --> PDB
    NP --> NDB
    CP --> CDB
    
    %% Signal flows
    PCB -.->|project_changed| FSM
    AT -.->|navigate_to_project| SC
    PT -.->|navigate_to_artifact| SC
    FSM -.->|filter_update| AP
    FSM -.->|filter_update| PP
```

## Key Signal Flows

### 1. Project Filter Synchronization

```mermaid
sequenceDiagram
    participant User
    participant PCB_Artifacts as ProjectComboBox<br/>[Artifacts]
    participant FSM as FilterStateManager
    participant SC as SignalCoordinator
    participant PCB_Projects as ProjectComboBox<br/>[Projects]
    participant AP as ArtifactsPage
    participant PP as ProjectsPage
    
    User->>PCB_Artifacts: Select Project X
    PCB_Artifacts->>FSM: set_project_filter(X)
    FSM->>FSM: Update state
    FSM->>SC: project_filter_changed(X)
    
    par Update All Pages
        SC->>PCB_Projects: set_project_id(X)
        SC->>AP: apply_project_filter(X)
        SC->>PP: highlight_project(X)
    end
    
    AP->>AP: Refresh artifact list
    PP->>PP: Expand to project X
```

### 2. Cross-Page Navigation - Artifact to Project

```mermaid
sequenceDiagram
    participant User
    participant AP as ArtifactsPage
    participant SC as SignalCoordinator
    participant TC as TabbedContentWidget
    participant PP as ProjectsPage
    
    User->>AP: Click View Project button
    AP->>AP: Get selected artifact
    AP->>SC: request_navigate_to_project(project_id)
    SC->>TC: setCurrentWidget(ProjectsPage)
    SC->>PP: show_project(project_id)
    PP->>PP: select_project_in_tree(project_id)
    PP->>PP: load_project_details()
    PP->>PP: scroll_to_project()
```

### 3. Real-Time Artifact Unlinking

```mermaid
sequenceDiagram
    participant User
    participant PP as ProjectsPage
    participant PDB as ProjectsDB
    participant SC as SignalCoordinator
    participant AP as ArtifactsPage
    participant AT as ArtifactTree
    
    User->>PP: Click Unlink Artifact
    PP->>PP: Get selected artifact
    PP->>PDB: update_artifact_project(artifact_id, None)
    PDB-->>PP: Success
    PP->>SC: artifact_unlinked_from_project(artifact_id, project_id)
    
    par Update Views
        SC->>AP: handle_artifact_unlinked(artifact_id, project_id)
        and
        SC->>PP: refresh_artifact_list()
    end
    
    AP->>AT: update_artifact_item(artifact_id)
    AT->>AT: remove_project_badge()
    PP->>PP: update_statistics()
```

### 4. Project Creation with Artifact Association

```mermaid
sequenceDiagram
    participant User
    participant AP as ArtifactsPage
    participant Dialog as ProjectDialog
    participant PDB as ProjectsDB
    participant SC as SignalCoordinator
    participant PP as ProjectsPage
    
    User->>AP: Create New Project for Artifact
    AP->>Dialog: Show with artifact context
    User->>Dialog: Enter project details
    Dialog->>PDB: create_project(project_data)
    PDB-->>Dialog: new_project_id
    Dialog->>PDB: link_artifact_to_project(artifact_id, project_id)
    PDB-->>Dialog: Success
    Dialog->>SC: project_created(project_id)
    Dialog->>SC: artifact_linked_to_project(artifact_id, project_id)
    
    par Update All Views
        SC->>PP: add_project_to_tree(project_id)
        SC->>AP: update_artifact_project(artifact_id, project_id)
        SC->>AP: refresh_project_combo()
    end
```

## Signal Types and Priorities

### High Priority Signals (Immediate)
- Navigation requests
- Filter changes
- User-initiated actions

### Medium Priority Signals (Batched)
- Multiple item updates
- Statistics refresh
- Tree expansions

### Low Priority Signals (Deferred)
- Background sync
- Auto-save triggers
- Debug logging

## Error Handling Flow

```mermaid
graph LR
    SE[Signal Emitted] --> EH{Error Handler}
    EH -->|Success| SP[Signal Processed]
    EH -->|Failure| RC{Retry Count}
    RC -->|< Max| RT[Retry with Delay]
    RC -->|>= Max| LG[Log Error]
    RT --> EH
    LG --> UN[User Notification]
    LG --> FB[Fallback Action]
```

## Performance Considerations

1. **Batch Updates**: Group multiple updates within 100ms window
2. **Lazy Loading**: Only update visible items in trees
3. **Debouncing**: Filter changes debounced by 300ms
4. **Caching**: Project/artifact relationships cached in memory
5. **Async Operations**: Database queries run in separate thread

## Testing Scenarios

### Scenario 1: Filter Sync Test
1. Set filter in Artifacts page
2. Verify Projects page combo box updates
3. Verify filtered views in both pages
4. Clear filter and verify reset

### Scenario 2: Navigation Test
1. Select artifact with project
2. Navigate to project
3. Verify correct project selected
4. Navigate back to artifact
5. Verify artifact still selected

### Scenario 3: Real-time Update Test
1. Open both pages side-by-side
2. Link artifact to project
3. Verify badge appears immediately
4. Unlink artifact
5. Verify badge removed immediately

### Scenario 4: Error Recovery Test
1. Simulate database error
2. Verify retry mechanism
3. Verify user notification
4. Verify system recovers gracefully