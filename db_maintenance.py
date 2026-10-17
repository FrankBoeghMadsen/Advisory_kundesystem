import argparse
import json
from pathlib import Path

from db import DB_PATH, create_backup, restore_test, verify_database


def print_result(result):
    print(json.dumps(result, ensure_ascii=False, indent=2))


def main():
    parser = argparse.ArgumentParser(description="Sikker databasevedligeholdelse")
    subparsers = parser.add_subparsers(dest="command", required=True)

    backup_parser = subparsers.add_parser("backup", help="Opret og verificer backup")
    backup_parser.add_argument("--label", default="manual")

    verify_parser = subparsers.add_parser("verify", help="Kontroller en database")
    verify_parser.add_argument("path", nargs="?", default=str(DB_PATH))

    restore_parser = subparsers.add_parser(
        "restore-check", help="Gendan en backup midlertidigt og kontroller den"
    )
    restore_parser.add_argument("path")

    args = parser.parse_args()
    if args.command == "backup":
        path = create_backup(args.label)
        result = verify_database(path)
        result["backup_path"] = str(path)
        print_result(result)
    elif args.command == "verify":
        print_result(verify_database(Path(args.path)))
    elif args.command == "restore-check":
        print_result(restore_test(Path(args.path)))


if __name__ == "__main__":
    main()
