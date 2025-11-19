import argparse
from pathlib import Path

from EasyTeleop.Components.PostProcess import DataPostProcessor


def parse_args():
    parser = argparse.ArgumentParser(
        description="Convert raw EasyTeleop sessions in datasets/temp to HDF5 files."
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
        help="Only process the given session ID. Omit to process every detected session.",
    )
    parser.add_argument(
        "--latest",
        action="store_true",
        help="Process only the most recently modified session (ignored if --session is set).",
    )
    parser.add_argument(
        "--list",
        action="store_true",
        help="List detected sessions and exit without processing.",
    )
    return parser.parse_args()


def select_latest_session(temp_dir: Path):
    sessions = [
        (p.name, p.stat().st_mtime)
        for p in temp_dir.iterdir()
        if p.is_dir() and (p / "metadata.json").exists()
    ]
    if not sessions:
        return None
    sessions.sort(key=lambda item: item[1], reverse=True)
    return sessions[0][0]


def main():
    args = parse_args()
    temp_dir = Path(args.temp_dir).expanduser()
    output_dir = Path(args.output_dir).expanduser()

    if not temp_dir.exists():
        raise SystemExit(f"Temp directory not found: {temp_dir}")

    processor = DataPostProcessor(str(temp_dir), str(output_dir))
    sessions = processor.find_sessions()

    if args.list:
        if not sessions:
            print(f"No sessions found in {temp_dir}")
        else:
            print("Available sessions:")
            for session in sessions:
                print(f" - {session}")
        return

    if args.session:
        session_id = args.session
    elif args.latest:
        session_id = select_latest_session(temp_dir)
        if session_id is None:
            raise SystemExit("No valid session directories were found.")
        print(f"Processing latest session: {session_id}")
    else:
        session_id = None

    if session_id:
        if session_id not in sessions:
            raise SystemExit(f"Session '{session_id}' not found in {temp_dir}")
        processor.process_session_to_hdf5(session_id)
    else:
        processor.process_all_sessions()


if __name__ == "__main__":
    main()
