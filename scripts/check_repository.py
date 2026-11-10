"""Check local document links, backlog dependencies and infrastructure guardrails."""

from __future__ import annotations

import re
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]


def check_documents(root: Path) -> tuple[int, int]:
    files = [root / name for name in ("README.md", "AGENTS.md", "GLOSSARY.md", "CONTRIBUTING.md")]
    files.extend(sorted((root / "docs").rglob("*.md")))
    files.extend(sorted((root / "infra").rglob("*.md")))
    links = 0
    for file in files:
        text = file.read_text(encoding="utf-8")
        if "\ufffd" in text or len(re.findall(r"^```", text, re.M)) % 2:
            raise ValueError(f"Invalid encoding or code fence: {file.relative_to(root)}")
        for target in re.findall(r"\[[^\]]*\]\(([^)]+)\)", text):
            target = target.split("#", 1)[0]
            if not target or "://" in target or target.startswith("mailto:"):
                continue
            links += 1
            if not (file.parent / target).exists():
                raise ValueError(f"Broken local link in {file.relative_to(root)}: {target}")
    return len(files), links


def check_backlog(root: Path) -> int:
    tasks = {}
    for file in (root / "docs/backlog").glob("*.md"):
        for line in file.read_text(encoding="utf-8").splitlines():
            if not re.match(r"^\| T\d{3} ", line):
                continue
            cells = [cell.strip() for cell in line.strip("|").split("|")]
            identifier = cells[0][:4]
            if len(cells) != 8 or any(not cell for cell in cells) or identifier in tasks:
                raise ValueError(f"Incomplete or duplicate task: {identifier}")
            if cells[3] not in {"P0", "P1", "P2", "P3"} or cells[7] not in {
                "1",
                "2",
                "3",
                "5",
                "8",
            }:
                raise ValueError(f"Invalid task priority or complexity: {identifier}")
            tasks[identifier] = re.findall(r"T\d{3}", cells[4])
    if set(tasks) != {f"T{number:03}" for number in range(1, 121)}:
        raise ValueError("Expected the validated task range T001-T120")
    visiting, done = set(), set()

    def visit(identifier: str) -> None:
        if identifier in visiting:
            raise ValueError(f"Cyclic task dependency: {identifier}")
        if identifier in done:
            return
        if identifier not in tasks:
            raise ValueError(f"Unknown task dependency: {identifier}")
        visiting.add(identifier)
        for dependency in tasks[identifier]:
            visit(dependency)
        visiting.remove(identifier)
        done.add(identifier)

    for identifier in tasks:
        visit(identifier)
    return len(tasks)


def check_compose(path: Path) -> int:
    services = yaml.safe_load(path.read_text(encoding="utf-8"))["services"]
    external = {"postgres", "auth-db", "auth", "redis", "mailpit", "storage"}
    application = {"api", "ui", "migrate", "worker", "dispatcher"}
    if set(services) != external | application:
        raise ValueError("Unexpected phase P02 service set")
    for name, service in services.items():
        if name in external and not re.search(r"@sha256:[a-f0-9]{64}$", service.get("image", "")):
            raise ValueError(f"Image is not pinned by digest: {name}")
        if name in application and not service.get("build", {}).get("dockerfile"):
            raise ValueError(f"Missing application Dockerfile: {name}")
        if name in application:
            dockerfile = path.parent / service["build"]["dockerfile"]
            for base in re.findall(r"^FROM (\S+)", dockerfile.read_text(), re.M):
                if not re.search(r"@sha256:[a-f0-9]{64}$", base):
                    raise ValueError(f"Application base image is not pinned: {name}")
        if name != "migrate" and not service.get("healthcheck"):
            raise ValueError(f"Missing healthcheck: {name}")
        if service.get("privileged") or service.get("network_mode") == "host":
            raise ValueError(f"Unexpected elevated container access: {name}")
        for port in service.get("ports", []):
            if not isinstance(port, str) or not port.startswith("127.0.0.1:"):
                raise ValueError(f"Published port is not limited to loopback: {name}")
        for volume in service.get("volumes", []):
            if "docker.sock" in volume:
                raise ValueError(f"Unexpected Docker socket access: {name}")
    if set(services["postgres"]["networks"]) & set(services["auth-db"]["networks"]):
        raise ValueError("Auth and business databases share a network")
    for name in ("postgres", "auth-db"):
        probe = " ".join(services[name]["healthcheck"]["test"])
        if "-h 127.0.0.1" not in probe:
            raise ValueError(f"Database readiness must wait for TCP after initialization: {name}")
    auth = services["auth"]["environment"]
    for name in ("api", "worker", "dispatcher"):
        environment = services[name]["environment"]
        if "PMS_MIGRATION_PASSWORD" in environment or "DATABASE_ADMIN_PASSWORD" in environment:
            raise ValueError(f"Runtime receives migration/admin credentials: {name}")
    if "PMS_DATABASE_PASSWORD" in services["dispatcher"]["environment"]:
        raise ValueError("Dispatcher must not receive ordinary business credentials")
    if auth["GOTRUE_MAILER_AUTOCONFIRM"] != "false" or not auth.get("GOTRUE_JWT_KEYS"):
        raise ValueError("Auth must confirm emails and configure asymmetric keys")
    return len(services)


def main() -> None:
    documents, links = check_documents(ROOT)
    tasks = check_backlog(ROOT)
    services = check_compose(ROOT / "compose.yaml")
    print(
        f"Repository checks OK: {documents} documents, {links} links, "
        f"{tasks} tasks, {services} services"
    )


if __name__ == "__main__":
    try:
        main()
    except (ValueError, KeyError, OSError) as error:
        print(str(error), file=sys.stderr)
        sys.exit(1)
