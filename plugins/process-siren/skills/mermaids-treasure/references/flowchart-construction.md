> Parent: [Mermaid Flowchart Syntax](../SKILL.md)

> [!IMPORTANT]
> A Mermaid process diagram carries the authority of the instruction that presents it. When a governing instruction names a diagram as its procedure, as the paragraph below does, execute it exactly as written: sequence, conditions, loops, parallel paths and terminal states, with no improvised, reordered or skipped steps. For an ambiguous or underspecified node, investigate available evidence first and ask only when the answer needs a decision the source leaves open.
> A diagram you are asked to analyze, improve or represent is the subject of that work; its steps are data to model, not instructions to run.
> When interacting with a user, report before acting the interpreted path you will follow from the diagram, then execute.

The following diagram is the authoritative procedure for Mermaid flowchart construction element selection. Execute steps in the exact order shown, including branches, decision points, and stop conditions.

```mermaid
flowchart TD
    Start(["Start — build Mermaid flowchart from process description"])

    %% Phase 1: Direction selection — evaluated once per diagram
    Start --> DirQ{"What is the structural pattern<br>of the process being diagrammed?"}
    DirQ -->|"Decision tree or general workflow — default"| TD["Direction TD — top-down<br>Use for decision trees and most workflows"]
    DirQ -->|"Linear pipeline or left-to-right transformation chain"| LR["Direction LR — left-right<br>Use for pipelines and sequential stages"]
    DirQ -->|"Build-up or bottom-to-top accumulation"| BT["Direction BT — bottom-top<br>Use for layered build-up diagrams"]
    DirQ -->|"Reverse or right-to-left flow"| RL["Direction RL — right-left<br>Use for reverse or inverted flows"]

    TD --> ShapeQ
    LR --> ShapeQ
    BT --> ShapeQ
    RL --> ShapeQ

    %% Phase 2: Node shape selection — evaluated once per element; repeat for each node
    ShapeQ{"For each element — what role does<br>this node play in the diagram?"}

    ShapeQ -->|"Process or action — default workhorse node"| SRect["Shape — rectangle<br>Syntax: NodeId[label]"]
    ShapeQ -->|"Event, start state, or end state"| SRounded["Shape — rounded rectangle<br>Syntax: NodeId(label)"]
    ShapeQ -->|"Named terminal point — start or stop label"| SStadium["Shape — stadium<br>Syntax: NodeId([label])"]
    ShapeQ -->|"Decision or branching condition"| SDiamond["Shape — diamond<br>Syntax: NodeId{label}"]
    ShapeQ -->|"Entry point start marker"| SCircle["Shape — circle<br>Syntax: NodeId((label))"]
    ShapeQ -->|"Hard termination stop marker"| SDblCirc["Shape — double circle<br>Syntax: NodeId(((label)))"]
    ShapeQ -->|"Prepare step or conditional setup"| SHex["Shape — hexagon<br>Syntax: NodeId with double-brace delimiters"]
    ShapeQ -->|"Database or persistent storage"| SCyl["Shape — cylinder<br>Syntax: NodeId with bracket-paren delimiters"]
    ShapeQ -->|"Subprocess or subroutine call"| SSubproc["Shape — subroutine<br>Syntax: NodeId with double-bracket delimiters"]

    SRect --> EdgeQ
    SRounded --> EdgeQ
    SStadium --> EdgeQ
    SDiamond --> EdgeQ
    SCircle --> EdgeQ
    SDblCirc --> EdgeQ
    SHex --> EdgeQ
    SCyl --> EdgeQ
    SSubproc --> EdgeQ

    %% Phase 3: Edge type selection — evaluated once per connection; repeat for each edge
    EdgeQ{"For each connection — what relationship<br>does this edge express?"}

    EdgeQ -->|"Normal flow — default sequential step"| ESolid["Edge — solid arrow<br>Syntax: A --> B"]
    EdgeQ -->|"Conditional or optional flow"| EDotted["Edge — dotted arrow<br>Syntax: A -.-> B"]
    EdgeQ -->|"Emphasis or main critical path"| EThick["Edge — thick arrow<br>Syntax: A ==> B"]
    EdgeQ -->|"Association without directional arrow"| EOpen["Edge — open link no arrowhead<br>Syntax: A --- B"]

    ESolid --> LabelQ
    EDotted --> LabelQ
    EThick --> LabelQ
    EOpen --> LabelQ

    %% Phase 4: Edge label — evaluated once per edge
    LabelQ{"Does this edge need a<br>descriptive label?"}
    LabelQ -->|"Yes — label clarifies the branch meaning or flow context"| AddLabel["Add edge label<br>Syntax: A -->|label text| B<br>Alt syntax: A -- label text --> B"]
    LabelQ -->|"No — flow is self-evident from node labels alone"| SkipLabel["Omit edge label<br>proceed to grouping decision"]

    AddLabel --> GroupQ
    SkipLabel --> GroupQ

    %% Phase 5: Grouping — evaluated once per diagram after all nodes are defined
    GroupQ{"Are there nodes that belong to<br>a named logical phase or subsystem?"}
    GroupQ -->|"Yes — nodes share a phase, actor, or subsystem boundary"| AddSubgraph["Wrap related nodes in subgraph block<br>Syntax: subgraph Title ... end<br>Place subgraph after all node definitions"]
    GroupQ -->|"No — all nodes are at the same structural level"| SkipSubgraph["No subgraph needed<br>proceed to styling decision"]

    AddSubgraph --> StyleQ
    SkipSubgraph --> StyleQ

    %% Phase 6: Styling — evaluated once per diagram
    StyleQ{"Are there node types requiring visual<br>distinction — decisions, error paths, or roles?"}
    StyleQ -->|"Yes — decision nodes or error paths need differentiated fill or stroke"| ApplyClassDef["Define classDef and apply to nodes<br>Syntax: classDef name fill:#hex,stroke:#hex<br>Apply with: class NodeId name<br>Place classDef statements at end of diagram"]
    StyleQ -->|"No — default Mermaid styling is sufficient for all nodes"| SkipStyle["No classDef needed<br>diagram construction complete"]

    ApplyClassDef --> Done
    SkipStyle --> Done

    %% Terminal state — agent recognizes diagram is structurally complete
    Done(["Diagram construction complete — Mermaid source ready for rendering and validation"])
```
