#!/usr/bin/env python3
"""Check the local Wasm feature graph with Python's offline TOML parser."""

from pathlib import Path
import sys
import tomllib


class BoundaryError(ValueError):
    pass


def check_boundary(manifest):
    features = manifest.get("features", {})
    dependencies = dict(manifest.get("dependencies", {}))
    for target in manifest.get("target", {}).values():
        dependencies.update(target.get("dependencies", {}))
    optional = {
        name
        for name, config in dependencies.items()
        if isinstance(config, dict) and config.get("optional", False)
    }
    ai = {
        name
        for name, config in dependencies.items()
        if (config.get("package", name) if isinstance(config, dict) else name)
        in {"quoridor-ai", "quoridor-nnue"}
    }
    engines = {
        name
        for name, config in dependencies.items()
        if (config.get("package", name) if isinstance(config, dict) else name) == "quoridor-ai"
    }
    if not engines or not ai <= optional:
        raise BoundaryError("AI dependencies must remain optional")
    if features.get("default") != [] or "rules" not in features or "ai" not in features:
        raise BoundaryError("Separate rules/ai features and empty defaults are required")
    for name, items in features.items():
        if not isinstance(items, list) or not all(isinstance(item, str) for item in items):
            raise BoundaryError(f"Invalid feature list: {name}")
    suppressed = {
        item[4:] for items in features.values() for item in items if item.startswith("dep:")
    }
    graph = dict(features)
    for name in optional - suppressed:
        graph.setdefault(name, ["dep:" + name])
    for name, items in graph.items():
        if not isinstance(items, list) or not all(isinstance(item, str) for item in items):
            raise BoundaryError(f"Invalid feature list: {name}")
        for item in items:
            if item.startswith("dep:"):
                if item[4:] not in optional:
                    raise BoundaryError(f"Unknown optional dependency: {item}")
            elif "/" in item:
                dependency, feature = item.split("/", 1)
                if dependency.removesuffix("?") not in dependencies or not feature:
                    raise BoundaryError(f"Unknown dependency feature: {item}")
            elif item not in graph:
                raise BoundaryError(f"Unknown feature alias: {item}")

    def reachable(start):
        enabled = set(dependencies) - optional
        pending = [start]
        visited = set()
        while pending:
            name = pending.pop()
            if name in visited:
                continue
            visited.add(name)
            for item in graph[name]:
                if item.startswith("dep:"):
                    enabled.add(item[4:])
                elif "/" in item:
                    dependency = item.split("/", 1)[0]
                    # Weak dependency features do not enable an optional dependency.
                    if not dependency.endswith("?"):
                        enabled.add(dependency)
                else:
                    pending.append(item)
        return enabled

    if reachable("rules") & ai or reachable("default") & ai:
        raise BoundaryError("Rules/default features reach an AI dependency")
    if not reachable("ai") & engines:
        raise BoundaryError("The ai feature must enable quoridor-ai")


def main():
    path = Path(sys.argv[1]) if len(sys.argv) == 2 else Path("crates/quoridor-wasm/Cargo.toml")
    with path.open("rb") as source:
        check_boundary(tomllib.load(source))
    print("Wasm feature boundary: rules/default cannot enable optional AI dependencies.")


if __name__ == "__main__":
    main()
