# Caster Heads-Up Display (HUD) Architecture & Compatibility Guidelines

## 1. Documentation Hierarchy, Progressive Disclosure & Single Source of Truth (SSoT)
All architectural analyses, master requirements, post-mortems, and design documents for the Caster HUD are stored in the user local directory:
`%LOCALAPPDATA%\caster\docs\caster_hud\` (or `~/.caster/docs/caster_hud/`)

### Documentation Roles, Status & Lifecycle:
- **`005_caster_hud_requirements_and_specifications.md`**: **DEFINITIVE SINGLE SOURCE OF TRUTH (SSoT)**. Authoritative master requirements, feature matrix, UI widget specifications, and UX contracts.
- **`007_caster_hud_lessons_learned_timeline.md`**: **LIVING ENGINEERING TIMELINE**. Chronological trail of issues encountered, root causes, lessons learned, and permanent architectural solutions.
- **`008_dragonfly_and_adce_active_rules_resolution_deep_dive.md`**: **EDUCATIONAL EXPLAINER**. Comprehensive technical deep dive into Dragonfly grammar context resolution, ADCE micro-focus integration, and pluggable OS focus observers.
- **`009_caster_hud_architectural_review_and_clean_architecture_synthesis.md`**: **ARCHITECTURAL REVIEW & CLEAN SYNTHESIS**. 5-layer clean architecture model, boundary invariants, anti-pattern mitigations, and health scorecard.
- **`010_fine_grained_context_recognition_native_vs_adce_explainer.md`**: **CONTEXT RECOGNITION & ROADMAP EXPLAINER**. Native OS vs ADCE 2-tier context architecture, Electron single-HWND analysis, and in-process UIA roadmap.
- **`011_adce_realtime_stream_and_native_focus_decoupling_deep_dive.md`**: **REAL-TIME ADCE & NATIVE DECOUPLING DEEP DIVE**. Real-time SSE micro-context streaming, sub-window click resolution, and clean UI panel matrix.
- `004_caster_hud_nextgen_modular_architecture_and_context_integration.md`: Target modular architecture blueprint (Refined architectural baseline).
- `006_caster_hud_thread_safety_and_compatibility_postmortem.md`: Thread boundary isolation, event loop deadlocks, and compatibility post-mortem.
- `001_caster_hud_architecture_and_threading_primer.md`: Baseline architecture, Dragonfly hooks, and threading primer (*Historical Reference*).
- `002_caster_hud_system_tray_and_upstream_evolution_audit.md`: System tray lifecycle and upstream audit (*Historical Reference*).
- `003_caster_hud_modular_theming_and_profiles_architecture.md`: Earlier modular theming & layout persistence specification (*Superseded by 004/005*).

*Future Capability Blueprints*: Stored separately in `%LOCALAPPDATA%\caster\docs\future_ideas/` (e.g. `001_caster_help_rule_and_context_aware_assist_architecture.md`).

### Maintenance Invariants:
1. **SSoT Synchronization**: Whenever HUD features, widget layouts, IPC protocols, or voice commands are modified, agents must update `005_caster_hud_requirements_and_specifications.md` to reflect current truth.
2. **Timeline Recording**: Any non-trivial bug, deadlock, layout constraint, or architectural pivot must be recorded in `007_caster_hud_lessons_learned_timeline.md` with an RCA and permanent solution.
3. **Progressive Disclosure**: Agents should consult `005` first for runtime contracts, `007` for historical lessons/pitfalls, and `004`/`006` for deep design rationale.

---

## 2. Strict Cross-Thread Qt Event Boundary Isolation
- **Rule**: NEVER instantiate, modify, show, or manipulate `QWidget`, `QDialog`, `QMenu`, or `QApplication` directly from a background socket, IPC, or XML-RPC thread.
- **Implementation**: All cross-thread interactions must strictly use:
  - `QtCore.QCoreApplication.postEvent(target, custom_event)`
  - Qt Signals connected via `Qt.QueuedConnection` / `Qt.AutoConnection` (`QtCore.Signal(object)`).
- Direct synchronous calls across threads lead to access violations, GUI freezes, and silent deadlocks that prevent subsequent recognition updates.

---

## 3. Backward & Cross-Version Compatibility Constraints
- **Python 2.7 / 3.x Compatibility**:
  - Do not use language syntax exclusive to Python 3.6+ without fallbacks (e.g. avoid raw f-strings in upstream core files, use `.format()` or `%` interpolation).
  - Do not use `dataclasses` or Python 3.7+ type annotations in files that may be imported under Python 2.7 / NatLink engines without compatibility wrappers or fallback dictionaries.
  - Use explicit `super(ClassName, self).__init__(...)` instead of zero-argument `super()`.
- **Operating Systems**: Windows 10, Windows 11, and legacy Windows 7/8 / Dragon NaturallySpeaking (DPI 15) setups.
- **Upstream Feature Preservation**:
  - Always preserve core features: Active Rules tree inspection (`show_rules`), Help commands reference (`show_help`), Right-Click Context Menu, Frameless Toggle ('T'), Drag Mode ('D'), System Tray docking, and theme cycling.
