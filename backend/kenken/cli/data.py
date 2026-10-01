"""`kenken data ...`: dataset commands (see kenken/data/__init__.py for the layout).

Typical workflow
    kenken data ingest              labels for digital PDFs + drafts for photos, manifest
    kenken data train-ocr           OCR model from fonts + dev glyphs
    kenken data ingest --redo-drafts  re-draft unverified photo labels with the new model
    kenken data review --unverified -o review/   images to check drafts by eye
    kenken data eval --split test   metrics for the report
"""

from __future__ import annotations

import json
from dataclasses import asdict
from pathlib import Path
from typing import Annotated, Optional

import typer

from . import output

data_app = typer.Typer(no_args_is_help=True, help="Dataset: labels, manifest, OCR training, evaluation.")

SplitOpt = Annotated[Optional[str], typer.Option("--split", help="dev | test | synthetic")]
SourceOpt = Annotated[Optional[str], typer.Option("--source", help="digital | printed | synthetic")]
JsonOpt = Annotated[bool, typer.Option("--json", help="Print JSON")]


@data_app.command("ingest")
def ingest_cmd(redo_drafts: Annotated[bool, typer.Option(
        "--redo-drafts", help="Re-create unverified draft labels (verified labels are never touched)")] = False):
    """Create missing labels and rebuild data/manifest.json."""
    from ..data.ingest import ingest

    report = ingest(overwrite_drafts=redo_drafts)
    typer.echo(f"{report.samples} samples · {len(report.created)} labels created · "
               f"{len(report.kept)} kept · {len(report.failed)} failed")
    for sid in report.created:
        typer.echo(f"  created {sid}")
    for sid, err in report.failed.items():
        typer.echo(f"  FAILED  {sid}: {err}")
    if report.failed:
        raise typer.Exit(1)


@data_app.command("list")
def list_cmd(split: SplitOpt = None, source: SourceOpt = None, as_json: JsonOpt = False):
    """List the samples of the manifest."""
    from ..data.dataset import load_manifest, select

    samples = select(load_manifest(), split=split, source=source)
    rows = [asdict(s) for s in samples]
    if as_json:
        typer.echo(json.dumps(rows, indent=2))
    elif rows:
        output.print_table(rows, ["id", "split", "size", "label_source", "verified", "file"])


@data_app.command("review")
def review_cmd(
    ids: Annotated[Optional[list[str]], typer.Argument(help="Sample ids (see `kenken data list`)")] = None,
    unverified: Annotated[bool, typer.Option("--unverified", help="All samples with unverified labels")] = False,
    out: Annotated[Path, typer.Option("--out", "-o", file_okay=False, help="Output folder")] = Path("review"),
):
    """Write image + label side by side (PNG) to check labels by eye."""
    import cv2

    from ..data.dataset import load_manifest
    from ..data.ingest import review_image

    samples = load_manifest()
    chosen = [s for s in samples if s.has_label() and ((ids and s.id in ids) or (unverified and not s.verified))]
    if not chosen:
        typer.echo("nothing to review")
        raise typer.Exit()
    out.mkdir(parents=True, exist_ok=True)
    for s in chosen:
        path = out / f"{s.id}.png"
        cv2.imwrite(str(path), review_image(s))
        typer.echo(f"  {path}   label: {s.label_path}")
    typer.echo("Fix the label JSON if needed and set meta.verified to true, then run `kenken data ingest`.")


@data_app.command("synth")
def synth_cmd(count: Annotated[int, typer.Option(min=1, help="Number of puzzles")] = 28,
              seed: Annotated[int, typer.Option(help="Random seed")] = 0):
    """Generate the synthetic (secondary) dataset, then rebuild the manifest."""
    from ..data import synth
    from ..data.dataset import save_manifest, scan

    for path in synth.generate(count, seed):
        typer.echo(f"  {path}")
    save_manifest(scan())


@data_app.command("train-ocr")
def train_ocr_cmd(dev: Annotated[bool, typer.Option(
        "--dev/--fonts-only", help="Add real glyphs from the dev split (digital PDFs)")] = True):
    """Train the clue OCR model (saved to backend/models/ocr_glyphs.npz)."""
    from ..data.ocr_training import train

    report = train(use_dev=dev)
    typer.echo(f"OCR model: {report.font_glyphs} font glyphs + {report.real_glyphs} real glyphs "
               f"from {len(report.samples_used)} dev samples -> {report.path}")


@data_app.command("eval")
def eval_cmd(split: SplitOpt = None, source: SourceOpt = None,
             include_unverified: Annotated[bool, typer.Option(
                 "--include-unverified", help="Also evaluate samples whose label is not verified")] = False,
             verbose: Annotated[bool, typer.Option("--verbose", "-v", help="Show every error")] = False,
             as_json: JsonOpt = False):
    """Evaluate the pipeline against the labels (metrics for the report)."""
    from ..data.dataset import load_manifest, select
    from ..data.evaluate import as_dict, evaluate

    samples = [s for s in select(load_manifest(), split=split, source=source)
               if s.has_label() and (s.verified or include_unverified)]
    if not samples:
        typer.echo("no labelled samples selected (are the labels verified?)")
        raise typer.Exit(1)
    results, summaries = evaluate(samples)
    if as_json:
        typer.echo(json.dumps(as_dict(results, summaries), indent=2, ensure_ascii=False))
        return
    for r in results:
        if verbose or r.error or r.clue_errors or not r.solved:
            status = "solved" if r.solved else "NOT SOLVED"
            typer.echo(f"  {r.id}: {status} {r.error} corrections={r.corrections}")
            for e in r.clue_errors:
                typer.echo(f"      {e}")
    output.print_table([asdict(s) for s in summaries],
                       ["group", "samples", "size_acc", "cage_acc", "edge_acc", "clue_acc",
                        "solve_acc", "vision_ms", "solver_ms"])
