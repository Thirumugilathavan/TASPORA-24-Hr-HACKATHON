import json
import re
from pathlib import Path

i18n_path = Path("frontend/src/lib/i18n.ts")
content = i18n_path.read_text(encoding="utf-8")

# Extract JSON from TRANSLATIONS = {...};
match = re.search(r"export const TRANSLATIONS: Record<LanguageCode, Record<string, string>> = (\{.*?\});\n\nexport function", content, re.DOTALL)
if not match:
    print("FAILED to extract TRANSLATIONS object from i18n.ts")
    exit(1)

translations = json.loads(match.group(1))
languages = ["en", "ta", "hi", "te", "bn"]

print("=== CareBridge i18n Comprehensive Verification ===")
print(f"Total languages: {len(translations)} -> {list(translations.keys())}")

for lang in languages:
    if lang not in translations:
        print(f"ERROR: Missing language {lang}!")
        exit(1)

en_keys = set(translations["en"].keys())
print(f"English keys count: {len(en_keys)}")

all_ok = True
for lang in languages:
    keys = set(translations[lang].keys())
    missing = en_keys - keys
    extra = keys - en_keys
    empty = [k for k, v in translations[lang].items() if not str(v).strip()]
    print(f"Language [{lang}]: {len(keys)} keys | Missing: {len(missing)} | Extra: {len(extra)} | Empty: {len(empty)}")
    if missing:
        print(f"  Missing keys in {lang}: {list(missing)[:5]}")
        all_ok = False
    if empty:
        print(f"  Empty keys in {lang}: {empty[:5]}")
        all_ok = False

if all_ok:
    print("\nSUCCESS: All 5 languages have 100% complete and valid translations!")
else:
    print("\nFAILURE: Some translations are missing or empty.")
    exit(1)
