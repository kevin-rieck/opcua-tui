# Connect Modal File Picker Specification

## Status
- Draft

## Problem Statement
The connect modal currently accepts certificate and private key paths via free-text inputs only. This is error-prone (typos, wrong directories, non-existent files) and slows secure connection setup.

A picker flow is needed so users can browse the filesystem and choose paths reliably while keeping manual entry available.

## Goals
- Add browse-based file selection for certificate and private key fields in the connect modal.
- Require a file name in the picker flow before selection can be confirmed.
- Keep manual path entry fully supported.
- Ensure picker cancel is non-destructive (no field mutation).
- Keep implementation aligned with built-in Textual widgets and current architecture.

## Non-Goals
- Replacing all path entry with picker-only UX.
- Full file manager features (create/delete/rename/copy/move).
- Multi-select support.
- Cross-screen generic picker rollout beyond connect modal in phase 1.

## Findings

### Textual widget landscape
- Textual widget gallery includes `DirectoryTree` and `Tree`, but no built-in `FilePicker` widget.
- `DirectoryTree` emits file-selection events (`DirectoryTree.FileSelected`) and supports filtering via subclassed `filter_paths`.

References:
- Widget gallery: https://textual.textualize.io/widget_gallery/
- DirectoryTree docs: https://textual.textualize.io/widgets/directory_tree/

### Dependency option
- Third-party package `textual-fspicker` exists and provides ready-made dialogs.
- For this repo, first implementation should avoid adding dependencies and build an in-house modal on top of `DirectoryTree`.

Reference:
- https://pypi.org/project/textual-fspicker/

## Proposed Architecture

### 1) New `PathPickerScreen`
Create a reusable modal screen at `src/opcua_tui/ui/screens/path_picker_screen.py`:
- Base: `ModalScreen[str | None]`
- Primary widget: `DirectoryTree`
- Footer controls: `Cancel`, `Select`
- Input: `Filename` (`Input`) used to require/override selected file name

Return contract:
- `None` on cancel
- absolute selected path string on confirm

### 2) Required Filename Contract
Picker confirm rules:
- `Filename` input must be non-empty (trimmed).
- If a file is selected in the tree, populate `Filename` from selection basename.
- If a directory is selected/focused, user must still provide filename manually.
- `Select` button is disabled until a valid filename is present.

Path resolution on confirm:
- `selected_dir / filename` if current target is directory.
- If selected file exists and filename unchanged, return that file path.
- Normalize via `Path(...).expanduser().resolve()` where possible.

Validation errors shown inline:
- `Filename is required`
- `Selection must resolve to a file path`

### 3) Picker Modes and Filters
Use one screen with mode configuration:
- `kind="certificate"` with extension hint/filter: `.der`, `.pem`, `.crt`, `.cer`
- `kind="private_key"` with extension hint/filter: `.pem`, `.key`, `.der`

Behavior:
- Filter should be advisory in phase 1 (prefer showing all files, with hint text) to avoid hiding valid uncommon formats.
- Future optional toggle: `show only suggested extensions`.

### 4) Connect Modal Integration
Update `src/opcua_tui/ui/screens/connect_modal_screen.py`:
- Add `Browse...` buttons next to `Client Certificate Path` and `Client Private Key Path`.
- Launch picker with start directory:
  - parent of current field value if value is non-empty and path-like
  - otherwise `Path.home()`
- On picker success:
  - write selected path into the corresponding input/reactive field
- On picker cancel:
  - do nothing

Existing pair validation remains unchanged:
- cert path requires key path
- key path requires cert path

### 5) Keyboard and Accessibility
Picker bindings:
- `enter`: confirm when valid
- `escape`: cancel
- `tab`/`shift+tab`: cycle tree, filename input, buttons

Focus policy:
- On open, focus `DirectoryTree`
- If no prior selection and user starts typing, focus can move to filename input via binding (optional `f` key)

## Data Structures

### PathPickerConfig (new dataclass)
- `title: str`
- `start_dir: str`
- `kind: Literal["certificate", "private_key", "generic_file"]`
- `extension_hints: tuple[str, ...]`

### PathPickerState (screen-local reactive state)
- `current_dir: str`
- `selected_file: str`
- `filename: str`
- `error_text: str`
- `is_confirm_enabled: bool`

## Module Changes
- `src/opcua_tui/ui/screens/path_picker_screen.py` (new)
  - picker UI, state, resolution, and return handling
- `src/opcua_tui/ui/screens/connect_modal_screen.py`
  - browse buttons + open picker handlers + writeback behavior
- `tests/unit/ui/screens/test_path_picker_screen.py` (new)
  - picker behavior tests
- `tests/unit/ui/screens/test_connect_modal_screen.py`
  - browse button integration tests
- `tools/capture_screenshot.py`
  - optional new mode for picker capture (`--screen path-picker`) if needed
- `README.md`
  - brief mention of browse-enabled cert/key path selection

## Test Plan

### Unit tests
- confirm disabled when filename empty
- selecting a file populates filename
- selecting directory + manual filename resolves correctly
- cancel returns `None` and does not mutate source field
- cert browse updates certificate field only
- key browse updates private key field only
- existing cert/key pair validation still enforced in connect modal

### Integration/UI checks
- Screenshot harness run required for UI changes:
  - `uv run .\\tools\\capture_screenshot.py --screen connect --output artifacts/screens/connect-modal-with-browse.svg`
- Optional picker snapshot if harness mode is added.

## Rollout Phases
1. Build `PathPickerScreen` and unit tests.
2. Integrate certificate browse action in connect modal.
3. Integrate key browse action in connect modal.
4. UI screenshot validation and docs update.

## Acceptance Criteria
- Connect modal shows browse actions for cert and key path fields.
- Picker can be canceled without changing existing values.
- Picker enforces filename-required confirm behavior.
- Picker returns a file path string and writes it to the intended field.
- Existing connect validation and insecure flow remain functional.

## Open Questions
- Should extension filtering be strict by default or advisory only?
- Should the picker allow creating a new file path (save-style) in phase 1, or only selecting existing files?
- Should hidden files be shown by default?
