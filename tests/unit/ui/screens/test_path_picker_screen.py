from pathlib import Path

from opcua_tui.ui.screens.path_picker_screen import PathPickerScreen


def test_path_picker_validates_filename_required() -> None:
    screen = PathPickerScreen(title="Pick", start_dir=".", extension_hints=())

    assert screen._validate_filename("") == "Filename is required"
    assert screen._validate_filename("   ") == "Filename is required"


def test_path_picker_rejects_path_segments_in_filename() -> None:
    screen = PathPickerScreen(title="Pick", start_dir=".", extension_hints=())

    assert screen._validate_filename("nested/name.der") == "Selection must resolve to a file path"
    assert screen._validate_filename("..") == "Selection must resolve to a file path"


def test_path_picker_file_selected_sets_current_dir_and_filename() -> None:
    screen = PathPickerScreen(title="Pick", start_dir=".", extension_hints=())
    event = type("FileSelected", (), {"path": Path("C:/certs/client.der")})()

    screen.on_directory_tree_file_selected(event)

    assert screen.current_dir == "C:\\certs"
    assert screen.file_name == "client.der"


def test_path_picker_resolve_start_dir_uses_home_for_missing_path(
    monkeypatch, tmp_path: Path
) -> None:
    home = tmp_path / "home"
    home.mkdir()
    monkeypatch.setattr("pathlib.Path.home", lambda: home)

    screen = PathPickerScreen(title="Pick", start_dir="C:/does/not/exist", extension_hints=())

    assert screen._initial_current_dir == str(home)
