# Feature-map example

Map every user-facing feature this pack may reproduce. Read the relevant section before driving the app. Keep this map at the user point of view. Discover internals and current code paths at runtime instead of freezing them here.

Copy this file to `.cstack/intake/feature-map.md` and set `control.feature_map_path` to that copy. Pack refreshes must not overwrite the copy.

Follow [the Codex runtime contract](../../../skills/cstack/references/codex-runtime.md).

## Per-feature template

### Feature name

One sentence: what the user can do.

#### How a user gets there

- Click path through visible controls
- Keyboard shortcut, or none

#### How the control adapter drives it

- Named adapter actions and the expected result
- Reset for a second independent attempt

#### Stable selectors

Roles, accessible names, ARIA, `data-component`, or purpose-named attributes. Never generated CSS classes, dynamic hashes, child indexes, or brittle DOM position.

#### States to exercise

Default, hover, focus-visible, active, disabled, loading, empty, error, selected, open, expanded, plus feature-specific states. Mark states that do not apply.

#### Preconditions and setup

Auth, data, permissions, flags, services.

#### Evidence and cross-check

Screenshot, video, and a read-only state check.

#### Gotchas

Wrong surfaces, dead ends, safe environment translations.

## Fictional example

These features belong to a fictional task app. They are examples, not required product features.

### Sign in

Lets a user enter the task app.

#### How a user gets there

- Open the app and choose `Sign in`. No shortcut.

#### How the control adapter drives it

- `open_app`, `click Sign in`, `fill credentials`, and `click Continue` should open the item list.
- Reset by signing out and clearing the disposable session.

#### Stable selectors

- Button `Sign in`, textboxes `Email` and `Password`, `data-component="sign-in-form"`

#### States to exercise

- Default, focus-visible, submitting, disabled, loading, error

#### Preconditions and setup

- Disposable account and available authentication service

#### Evidence and cross-check

- Record landing page through item list. Check read-only session state.

#### Gotchas

- A marketing page is the wrong surface. A missing auth service is a block.

### Item list and detail

Lets a user browse items and open one.

#### How a user gets there

- Open the `Items` tab, then choose a row.

#### How the control adapter drives it

- `select_tab Items` and click a fixture-named row should open its detail.
- Reset by closing the detail and clearing selection.

#### Stable selectors

- Tab and list named `Items`, fixture-named row, `data-component="item-detail"`

#### States to exercise

- Loading, empty, error, selected, open, expanded

#### Preconditions and setup

- Named fixture items, read permission, available item service

#### Evidence and cross-check

- Show selection and matching detail title. Check selected-item ID.

#### Gotchas

- Search results may look similar but use a different path.

### Item editor

Lets a user create or edit an item.

#### How a user gets there

- Choose `Edit` from detail or `New item` from the list.

#### How the control adapter drives it

- `click Edit`, fill the mapped field, and `click Save` should update detail.
- Reset by restoring the fixture.

#### Stable selectors

- Buttons `Edit`, `New item`, `Save`, form `Item editor`, label-linked fields

#### States to exercise

- Default, focus-visible, dirty, validating, disabled, saving, error, success

#### Preconditions and setup

- Editable fixture, write permission, available save service

#### Evidence and cross-check

- Show field change through updated detail. Check the stored item value read-only.

#### Gotchas

- Do not inject form state. A read-only detail field is not the editor.

### Settings

Lets a user change personal preferences.

#### How a user gets there

- Open the profile menu, then choose `Settings`.

#### How the control adapter drives it

- `open_menu Profile`, `click Settings`, and toggle the mapped preference should update the control.
- Reset by restoring the starting preference.

#### Stable selectors

- Button `Profile`, menu item `Settings`, region `Settings`, purpose-named preference attribute

#### States to exercise

- Closed, open, selected, focus-visible, disabled, loading, error

#### Preconditions and setup

- Signed-in test account, known preferences, available preference service

#### Evidence and cross-check

- Show the menu path and final control state. Check the preference value read-only.

#### Gotchas

- Operating-system settings are a different surface.

## Completeness checklist

- Every reproducible user-facing feature has a section.
- Every section names a user path, adapter actions, and reset.
- Selectors use roles, names, ARIA, stable component markers, or purpose-named attributes.
- No selector uses generated classes or DOM position.
- Relevant interaction, loading, empty, error, selected, and expanded states are covered.
- Auth, fixtures, permissions, flags, and services are explicit.
- Screenshot, video, and underlying cross-check requirements are explicit.
- Wrong surfaces, dead ends, and safe environment translations are listed.
- Implementation details remain runtime discoveries.
