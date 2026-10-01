"""Package only tracked source and the explicitly named final deliverables."""

import hashlib
import json
import re
import subprocess
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile


def main():
    root = Path(__file__).resolve().parents[1]
    output = root.parent / "deliverables"
    output.mkdir(exist_ok=True)
    paths = subprocess.check_output(["git", "ls-files", "-z"], cwd=root).decode().split("\0")
    tracked = [Path(p) for p in paths if p]
    if not tracked:
        raise SystemExit("Stage the reviewed project source before creating a package.")
    secret_patterns = [r"AIza[0-9A-Za-z_-]{35}", r"gh[pousr]_[A-Za-z0-9]{30,}", r"sk-[A-Za-z0-9_-]{24,}"]
    for relative in tracked:
        absolute = (root / relative).resolve()
        if not absolute.is_relative_to(root):
            raise SystemExit("Tracked path escapes the project directory")
        if (relative.name.startswith(".env") and relative.name != ".env.example") or relative.suffix in {
            ".sqlite3",
            ".log",
            ".wav",
        }:
            raise SystemExit(f"Private/runtime file unexpectedly staged: {relative}")
        try:
            text = absolute.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        if any(re.search(pattern, text) for pattern in secret_patterns):
            raise SystemExit(f"Potential secret detected; review {relative}")
    source = output / "MarginGuard_Source.zip"
    with ZipFile(source, "w", ZIP_DEFLATED, compresslevel=9) as archive:
        for relative in tracked:
            archive.write(root / relative, "marginguard/" + relative.as_posix())
    names = [
        "MarginGuard_Source.zip",
        "MarginGuard_Final_Project.pptx",
        "MarginGuard_Final_Project.pdf",
        "MarginGuard_Product_Demo.mp4",
        "MarginGuard_Final_Submission.md",
    ]
    records = []
    for name in names:
        data = (output / name).read_bytes()
        records.append({"file": name, "bytes": len(data), "sha256": hashlib.sha256(data).hexdigest()})
    manifest = output / "MarginGuard_Manifest.json"
    manifest.write_text(json.dumps({"files": records}, indent=2), encoding="utf-8")
    bundle = output / "MarginGuard_Submission_Package.zip"
    with ZipFile(bundle, "w", ZIP_DEFLATED) as archive:
        for name in [*names, manifest.name]:
            archive.write(output / name, name)
    with ZipFile(source) as archive:
        assert archive.testzip() is None
    with ZipFile(bundle) as archive:
        assert archive.testzip() is None
    print(f"Packaged {len(tracked)} source files; private data and local dependencies excluded.")
    print(bundle)


if __name__ == "__main__":
    main()
