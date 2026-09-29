# Context routing index

Read [current state and task queue](../CONTEXT.md) at session startup. Load the routes below only when the task needs them. Follow the relevant headings within long documents rather than loading whole history trees.

| Task / question | Required context |
|---|---|
| Generate SVGs | [Production use](PRODUCTION_USE.md), only for CLI details |
| Git administration | [Repository administration](REPOSITORY_ADMINISTRATION.md), only for scope details |
| Change docs, tooling or tests | [Workflow](WORKFLOW.md); affected source; [testing](TESTING.md) for test changes |
| Renderer behavior or correctness | [Workflow](WORKFLOW.md), [design-language headings/sections](../chip_design_language.md), [testing](TESTING.md), the relevant issue evidence |
| Component/LOCAL occupied-area share | Current-state task and [area-share evidence](AREA_SHARE_SYSTEM.md); design-language ?19.2.1?19.4 and workflow/testing for renderer changes |
| Deferred residual clustering correction | Current-state issue and [residual distribution evidence](RESIDUAL_CLUSTER_DISTRIBUTION.md); design-language residual/LOCAL sections on demand |
| Performance optimization | Workflow optimization section; relevant [optimization history](OPTIMIZATION_HISTORY.md), [long/fine audit](LONG_FINE_PERFORMANCE_AUDIT.md) or [MAIN instrumentation](MAIN1_INSTRUMENTATION_AUDIT.md) |
| MAIN persistence / survival | Relevant design-language MAIN sections; [persistence diagnosis](LONG_FINE_PERSISTENCE_DIAGNOSIS.md) and [line-survival history](LINE_MURDER_PROMOTION_HISTORY.md) when needed |
| Semantic SVG consumers | [Semantic SVG export](SEMANTIC_SVG_EXPORT.md) |
| Historical roadmap or project state | [Roadmap history pointer](POST_OPTIMIZATION_ROADMAP.md), [pre-migration state](../archive/project_state/2026-09-27/README.md) |
| Prior versions or inactive experiments | [Archive index](../archive/README.md); do not treat archived task instructions as current |

Authority: design language specifies behavior; CONTEXT.md records live state/tasks; WORKFLOW.md specifies process; changelog and archive record history. Evidence documents describe dated findings, not independent live task queues.
