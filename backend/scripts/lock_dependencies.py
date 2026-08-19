import importlib.metadata

distributions = importlib.metadata.distributions()
pkgs = []
for dist in distributions:
    name = dist.metadata["Name"]
    version = dist.version
    if name:
        pkgs.append(f"{name}=={version}")

pkgs = sorted(list(set(pkgs)))
with open("requirements-lock.txt", "w", encoding="utf-8") as f:
    f.write("\n".join(pkgs) + "\n")

print(f"Locked {len(pkgs)} backend packages in requirements-lock.txt.")
