import json
import subprocess
import sys

def main():
    out = subprocess.check_output([sys.executable, "-m", "pip", "list", "--format=json"]).decode("utf-8")
    pkgs = json.loads(out)
    sbom = {
        "$schema": "http://cyclonedx.org/schema/bom-1.5.schema.json",
        "bomFormat": "CycloneDX",
        "specVersion": "1.5",
        "serialNumber": "urn:uuid:3e679e0e-4f52-4f74-bc61-e5757878dcd1",
        "version": 1,
        "metadata": {
            "component": {
                "name": "selnikel-ai-backend",
                "version": "0.1.0",
                "type": "application"
            }
        },
        "components": [
            {
                "type": "library",
                "name": p["name"],
                "version": p["version"],
                "purl": f"pkg:pypi/{p['name']}@{p['version']}"
            }
            for p in pkgs
        ]
    }
    with open("sbom-backend.cdx.json", "w", encoding="utf-8") as f:
        json.dump(sbom, f, indent=2)
    print(f"Successfully generated sbom-backend.cdx.json with {len(pkgs)} components.")

if __name__ == "__main__":
    main()
