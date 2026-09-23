# Control-adapter contract

Intake does not know how to start or drive every app. The operator must configure one adapter that implements this contract for the target app.

Set its name in `control.adapter_name`. Point `connectors.control.mcp_server` at an MCP server registered with `codex mcp add` when the adapter lives there. A session browser or simulator that already exposes the seven operations is valid. Named tools go in `connectors.control.tools` only when the server actually exposes those names.

Set the completed user-facing feature map path in `control.feature_map_path`. Copy and fill [feature-map.example.md](feature-map.example.md) to <code>.github/cstack/intake/feature-map.md</code> instead of editing the pack copy.

If the adapter, feature map, or a required capability is absent, ambiguous, or incomplete, reproduce and fix work must fail closed. The GitHub Actions Codex step uses the read-only sandbox, which has no network, so an adapter that needs the network is a block.

Follow [the Codex runtime contract](../../../skills/cstack/references/codex-runtime.md).

## Required capabilities

### 1. Bring up

Start the requested app revision in the requested test environment.

Input: repository and revision, build or start mode, workspace, account, fixture, and feature-state requirements, artifact directory, completed feature-map path.

Return: session identifier, how the adapter confirmed the correct app and environment, stable app markers, running process or target details needed by later calls, any missing capability.

The adapter must distinguish the target app from a similar window, shell, or production instance.

### 2. Drive UI

Perform real user actions: click, type, press keys, scroll, drag, resize, navigate through app controls.

Prefer roles, labels, and stable selectors. Use coordinates only after a fresh screenshot.

Return each action and the observed state change.

Do not set internal state, call hidden app methods, write directly to storage, or inject DOM changes to create the symptom.

### 3. Drive mapped features and states

Read the relevant feature-map section before driving the app.

The adapter must expose ways to:

- Navigate every mapped feature through the user-visible path.
- Invoke the adapter action names listed for that feature.
- Interact with default, hover, focus-visible, active, disabled, loading, empty, error, selected, open, expanded, and feature-specific states when they apply.
- Arrange a state through safe fixture data, permissions, flags, service responses, or supported test controls.
- Reset the feature for a second independent repro attempt.
- Capture the screenshot, video, and read-only cross-check named by the feature map.

Use roles, accessible names, ARIA relationships, stable component markers, and purpose-named data attributes. Never use generated CSS classes, dynamic hashes, child indexes, or brittle DOM position.

Arranging a precondition is not permission to inject the reported symptom. The repro itself must still come from real user interaction.

### 4. Inspect state

Read state to confirm what the UI shows. Examples: accessibility tree, DOM or view hierarchy, process state, local logs, network request status, app-exposed debug state.

Inspection is read-only. If a query changes state, it belongs in Drive UI and must represent a real user action.

### 5. Screenshot

Capture the current app state to a requested path.

Return: file path, capture time, app marker or window title, short description of what should be visible.

The screenshot must show enough app chrome to prove that the correct app is under test.

### 6. Recording

Start and stop a screen recording around the full repro path.

Return: file path, start and stop times, captured window or region, whether audio or sensitive overlays were omitted.

The recording must show the discriminating final state, not only setup or a loading screen.

### 7. Cleanup

Stop processes and sessions created by the adapter. Remove disposable browser or app profiles, temporary workspaces, test accounts or fixtures the adapter created, debug ports and tunnels, and captures past their retention window.

Return what was stopped, removed, retained, or left for a person. Cleanup must not delete user work.

## Adapter behavior

The adapter must:

- Report capabilities before the repro starts.
- Report which feature-map sections it can drive and which are blocked.
- Use the same environment inputs for baseline and patched builds.
- Surface startup failures as failures.
- Bound retries.
- Keep secrets out of logs and artifacts.
- Keep captures outside the repository.
- Support a fresh or reset state between the two repro attempts.
- Avoid production changes unless the user explicitly configured a safe test action.

## Environment translation

Before declaring an environment block, restate the defect without platform-specific nouns and ask whether the same behavior can be tested safely in the available environment. Use a translated attempt only when it tests the same underlying behavior. Label it as translated evidence. Do not call it an exact repro when the missing environment is part of the defect.

## Setup check

Before enabling the reproduce workflow, run one harmless adapter check. No source-thread post is involved.

1. Bring up the app.
2. Confirm the stable app marker.
3. Load one completed feature-map section.
4. Navigate to that feature through its user path.
5. Exercise one disposable state through mapped adapter actions.
6. Inspect the resulting state.
7. Capture a screenshot.
8. Record a short clip.
9. Clean up.

Enable reproduce work only when all nine steps succeed.
