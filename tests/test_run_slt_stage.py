from pathlib import Path

import pytest

from scripts.run_slt_stage import load_stage_paths


def test_load_stage_paths_reads_non_comment_lines(tmp_path: Path) -> None:
    stage_file = tmp_path / "current_stage.txt"
    stage_file.write_text(
        "\n".join(
            [
                "# comment",
                "",
                "tests/sqllogictest/select1.test",
                "tests/sqllogictest/select2.test",
            ]
        )
    )

    paths = load_stage_paths(stage_file)

    assert paths == [
        "tests/sqllogictest/select1.test",
        "tests/sqllogictest/select2.test",
    ]


def test_load_stage_paths_rejects_empty_stage_file(tmp_path: Path) -> None:
    stage_file = tmp_path / "current_stage.txt"
    stage_file.write_text("# comment only\n")

    with pytest.raises(ValueError, match="stage file is empty"):
        load_stage_paths(stage_file)
