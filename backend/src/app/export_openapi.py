import argparse
import json
from pathlib import Path

from app.bootstrap import create_app


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    content = (
        json.dumps(create_app().openapi(), ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    )
    target = Path(__file__).resolve().parents[3] / "docs/api/openapi.json"
    if args.check:
        if target.read_text(encoding="utf-8") != content:
            raise SystemExit("OpenAPI snapshot changed; review and regenerate the client")
    else:
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")


if __name__ == "__main__":
    main()
