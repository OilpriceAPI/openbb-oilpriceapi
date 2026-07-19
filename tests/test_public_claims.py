"""Keep indexed package copy aligned with the versioned product contract."""

from pathlib import Path
import re


ROOT = Path(__file__).parents[1]
PUBLIC_FILES = (
    ROOT / "README.md",
    ROOT / "pyproject.toml",
    ROOT / "openbb_oilpriceapi" / "__init__.py",
    ROOT / "docs" / "publication-copy.md",
)


def test_public_copy_avoids_unsupported_claims() -> None:
    text = "\n".join(path.read_text() for path in PUBLIC_FILES)
    unsupported = {
        "real-time": r"\breal[ -]?time\b",
        "fixed free allocation": r"\b(?:100|200|10,?000)\s+requests?\b",
        "universal catalog response": r"\b(?:returns?|gets?|fetches?)\s+all\b",
        "fixed cadence": r"\b(?:hourly|daily)\s+prices?\b",
    }

    for label, pattern in unsupported.items():
        assert not re.search(pattern, text, flags=re.IGNORECASE), label


def test_mutable_facts_link_to_canonical_contract() -> None:
    readme = (ROOT / "README.md").read_text()
    assert "https://api.oilpriceapi.com/product-facts.json" in readme
    assert "https://www.oilpriceapi.com/legal/data-usage" in readme


def test_documented_symbol_mapping_matches_implementation() -> None:
    from openbb_oilpriceapi.utils.constants import SYMBOL_MAPPING

    readme = (ROOT / "README.md").read_text()
    documented = {
        match.groups()
        for match in re.finditer(
            r"^\| `([^`]+)` \| `([^`]+)` \|$", readme, re.MULTILINE
        )
    }
    assert documented == set(SYMBOL_MAPPING.items())
