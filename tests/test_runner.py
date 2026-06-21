from pathlib import Path

from gmaps_cli.models import LocationRecord, QuerySeed, ResolvedProxy, ScrapeJob
from gmaps_cli.runner import run_job


class FakeBackend:
    def __init__(self) -> None:
        self.calls: list[str] = []

    def scrape_seed(self, seed: QuerySeed) -> list[LocationRecord]:
        query = seed.query or "unknown"
        self.calls.append(query)
        return [
            LocationRecord(
                title=query,
                url=f"https://example.com/{query.replace(' ', '-')}",
                source_url=f"https://maps.example/{query.replace(' ', '+')}",
                query=query,
            )
        ]


def test_run_job_resume_skips_completed_seeds(tmp_path: Path, monkeypatch) -> None:
    backend = FakeBackend()

    def fake_make_backend(job: ScrapeJob, proxy: ResolvedProxy) -> FakeBackend:
        return backend

    monkeypatch.setattr("gmaps_cli.runner._make_backend", fake_make_backend)

    job = ScrapeJob(
        name="resume-test",
        seeds=[
            QuerySeed(query="coffee in Austin TX"),
            QuerySeed(query="dentists in Austin TX"),
        ],
        output={"directory": tmp_path, "filename": "results.csv"},
    )

    first = run_job(job)

    assert first.seeds_processed == 2
    assert len(backend.calls) == 2

    backend.calls.clear()
    resumed = run_job(job, resume_from=first.output_dir)

    assert resumed.seeds_processed == 0
    assert resumed.seeds_skipped == 2
    assert backend.calls == []
