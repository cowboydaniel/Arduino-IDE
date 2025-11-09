import pytest

pytest.importorskip(
    "PySide6.QtWidgets",
    reason="PySide6 (and libGL) not available in the test environment",
)

from PySide6.QtWidgets import QApplication

from arduino_ide.ui.project_explorer import (
    ProjectExplorer,
    PATH_ROLE,
    IS_DIR_ROLE,
)


@pytest.fixture(scope="module")
def qt_app():
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    yield app


def collect_child_items(item):
    return [item.child(row) for row in range(item.rowCount())]


def test_load_project_populates_tree_with_metadata(tmp_path, qt_app):
    src_dir = tmp_path / "src"
    src_dir.mkdir()
    main_file = src_dir / "sketch.ino"
    main_file.write_text("void setup(){}\n")

    readme = tmp_path / "README.md"
    readme.write_text("# Example\n")

    ignored_dir = tmp_path / ".git"
    ignored_dir.mkdir()
    (ignored_dir / "config").write_text("[core]\n")

    ignored_file = tmp_path / "Thumbs.db"
    ignored_file.write_text("binary")

    explorer = ProjectExplorer()
    explorer.load_project(tmp_path)

    root_item = explorer.model.item(0, 0)
    assert root_item is not None
    assert root_item.data(PATH_ROLE) == str(tmp_path.resolve())

    children = collect_child_items(root_item)
    child_paths = {child.data(PATH_ROLE) for child in children}

    assert str(src_dir.resolve()) in child_paths
    assert str(readme.resolve()) in child_paths
    assert str(ignored_dir.resolve()) not in child_paths
    assert str(ignored_file.resolve()) not in child_paths

    src_item = next(child for child in children if child.data(PATH_ROLE) == str(src_dir.resolve()))
    assert bool(src_item.data(IS_DIR_ROLE)) is True

    src_children = collect_child_items(src_item)
    assert any(child.data(PATH_ROLE) == str(main_file.resolve()) for child in src_children)


def test_refresh_updates_tree_and_emits_signal(tmp_path, qt_app):
    initial_file = tmp_path / "main.ino"
    initial_file.write_text("void loop(){}\n")

    explorer = ProjectExplorer()
    explorer.load_project(tmp_path)

    received = []
    explorer.file_open_requested.connect(received.append)

    root_item = explorer.model.item(0, 0)
    file_item = next(
        child for child in collect_child_items(root_item)
        if not child.data(IS_DIR_ROLE)
    )
    explorer.on_item_clicked(explorer.model.indexFromItem(file_item))
    assert received == [file_item.data(PATH_ROLE)]

    new_file = tmp_path / "util.cpp"
    new_file.write_text("int util() { return 0; }\n")

    explorer.refresh()

    root_item = explorer.model.item(0, 0)
    paths_after_refresh = {
        child.data(PATH_ROLE) for child in collect_child_items(root_item)
    }
    assert str(new_file.resolve()) in paths_after_refresh
