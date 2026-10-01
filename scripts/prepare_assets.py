"""Prepare screenshots from the real Playwright journey for docs and presentation."""

import shutil
from pathlib import Path

from PIL import Image

ARTIFACTS = Path("artifacts")
TARGET = Path("docs/images")


def main():
    TARGET.mkdir(parents=True, exist_ok=True)
    names = {
        "02-overview": "overview",
        "05-decision-lab": "decision-lab",
        "07-stale-memo": "stale-memo",
        "08-quality-gate": "quality-gate",
    }
    for source, target in names.items():
        shutil.copyfile(ARTIFACTS / (source + ".png"), TARGET / (target + ".png"))
    crops = {
        "overview": ("02-overview", (263, 225, 1406, 772)),
        "investigation": ("04-investigation", (248, 90, 1420, 1010)),
        "decision": ("05-decision-lab", (585, 225, 1405, 745)),
        "approval": ("06-approved-memo", (264, 230, 1313, 526)),
        "stale": ("07-stale-memo", (264, 230, 1313, 526)),
        "quality": ("08-quality-gate", (263, 290, 1406, 860)),
    }
    for target, (source, box) in crops.items():
        with Image.open(ARTIFACTS / (source + ".png")) as image:
            bounded = (*box[:3], min(box[3], image.height))
            image.crop(bounded).save(ARTIFACTS / ("deck-" + target + ".png"))
    print("Prepared actual product images for the repository and presentation.")


if __name__ == "__main__":
    main()
