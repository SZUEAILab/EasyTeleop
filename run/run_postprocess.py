import argparse
from fnmatch import fnmatch
from pathlib import Path
from typing import Iterable, List, Sequence

from EasyTeleop.Components.PostProcess import DataPostProcessor


def parse_args():
    parser = argparse.ArgumentParser(
        description="Convert EasyTeleop temp sessions into HDF5 datasets."
    )
    parser.add_argument(
        "--temp_dir",
        default="datasets/temp",
        help="Directory containing session folders (default: %(default)s)",
    )
    parser.add_argument(
        "--output_dir",
        default="datasets/hdf5",
        help="Directory to store generated HDF5 files (default: %(default)s)",
    )
    parser.add_argument(
        "--session",
        nargs="+",
        help="One or more session IDs to process (overrides --latest / --pattern).",
    )
    parser.add_argument(
        "--pattern",
        help="Glob pattern to filter sessions (e.g., demo_*). Ignored if --session is set.",
    )
    parser.add_argument(
        "--latest",
        action="store_true",
        help="Process only the most recently modified session after filtering.",
    )
    parser.add_argument(
        "--skip_existing",
        action="store_true",
        help="Skip sessions whose target HDF5 already exists in the output directory.",
    )
    parser.add_argument(
        "--dry_run",
        action="store_true",
        help="Print which sessions would be processed, but do not run the converter.",
    )
    parser.add_argument(
        "--list",
        action="store_true",
        help="List detected sessions (after filtering) and exit without processing.",
    )
    return parser.parse_args()


def select_latest_session(temp_dir: Path, candidates: Sequence[str]) -> str | None:
    """Return the latest session ID from candidates based on folder mtime."""
    newest: str | None = None
    newest_mtime: float | None = None
    for session_id in candidates:
        session_path = temp_dir / session_id
        if not session_path.exists():
            continue
        try:
            mtime = session_path.stat().st_mtime
        except OSError:
            continue
        if newest is None or newest_mtime is None or mtime > newest_mtime:
            newest = session_id
            newest_mtime = mtime
    return newest


def filter_by_pattern(sessions: Iterable[str], pattern: str) -> List[str]:
    return [session for session in sessions if fnmatch(session, pattern)]


def main():
    args = parse_args()
    temp_dir = Path(args.temp_dir).expanduser()
    output_dir = Path(args.output_dir).expanduser()

    if not temp_dir.exists():
        raise SystemExit(f"Temp directory not found: {temp_dir}")

    processor = DataPostProcessor(str(temp_dir), str(output_dir))
    available_sessions = sorted(processor.find_sessions())

    if not available_sessions:
        message = f"No sessions found in {temp_dir}"
        if args.list:
            print(message)
            return
        raise SystemExit(message)

    target_sessions: List[str]
    if args.session:
        missing = [session for session in args.session if session not in available_sessions]
        if missing:
            raise SystemExit(
                f"Session(s) not found in {temp_dir}: {', '.join(missing)}"
            )
        target_sessions = list(dict.fromkeys(args.session))  # preserve order, remove dupes
    else:
        filtered = available_sessions
        if args.pattern:
            filtered = filter_by_pattern(filtered, args.pattern)
            if not filtered:
                raise SystemExit(
                    f"No sessions match pattern '{args.pattern}' inside {temp_dir}"
                )
        if args.latest:
            latest = select_latest_session(temp_dir, filtered)
            if latest is None:
                raise SystemExit("Unable to determine the latest session.")
            filtered = [latest]
        target_sessions = filtered

    if args.list:
        print("Matched sessions:")
        for session in target_sessions:
            print(f" - {session}")
        return

    if args.skip_existing:
        retained = []
        skipped = []
        for session in target_sessions:
            output_path = output_dir / f"{session}.hdf5"
            if output_path.exists():
                skipped.append(session)
            else:
                retained.append(session)
        if skipped:
            print(
                "Skipping sessions with existing outputs: "
                + ", ".join(skipped)
            )
        target_sessions = retained

    if not target_sessions:
        print("No sessions left to process after filtering.")
        return

    if args.dry_run:
        print("Dry run: the following sessions would be processed:")
        for session in target_sessions:
            print(f" - {session}")
        return

    for session in target_sessions:
        print(f"Processing session {session}...")
        try:
            processor.process_session_to_hdf5(session)
        except Exception as exc:  # pragma: no cover - safety net
            print(f"Error processing session {session}: {exc}")


if __name__ == "__main__":
    main()
