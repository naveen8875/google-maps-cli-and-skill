from pathlib import Path

from gmaps_cli.config import load_job_from_path, save_job_to_path
from gmaps_cli.jobs import build_google_maps_search_url, build_job_template


def test_build_google_maps_search_url() -> None:
    assert build_google_maps_search_url("coffee in Austin TX").endswith(
        "coffee+in+Austin+TX"
    )


def test_save_and_load_job_roundtrip(tmp_path: Path) -> None:
    job = build_job_template(
        name="demo-job",
        queries=["coffee in Austin TX", "dentists in Austin TX"],
        output_filename="demo.csv",
        full_scroll=True,
        max_results=25,
    )

    path = tmp_path / "job.yaml"
    save_job_to_path(job, path)
    loaded = load_job_from_path(path)

    assert loaded.name == "demo-job"
    assert len(loaded.seeds) == 2
    assert loaded.output.filename == "demo.csv"
