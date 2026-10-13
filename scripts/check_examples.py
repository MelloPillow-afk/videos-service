"""Validate inline and referenced OpenAPI examples against their schemas."""

import argparse
from pathlib import Path
from urllib.parse import unquote, urldefrag, urljoin, urlsplit

import yaml
from jsonschema import FormatChecker
from openapi_schema_validator import OAS32Validator
from referencing import Registry
from referencing.exceptions import NoSuchResource, Unresolvable
from referencing.jsonschema import DRAFT202012


def check_examples(spec_path: Path) -> tuple[int, list[str]]:
    base_uri = spec_path.resolve().as_uri()
    documents = {}

    def retrieve(uri):
        parsed = urlsplit(uri)
        if parsed.scheme != "file" or parsed.netloc:
            raise NoSuchResource(ref=uri)
        if uri not in documents:
            documents[uri] = yaml.safe_load(Path(unquote(parsed.path)).read_text())
        return DRAFT202012.create_resource(documents[uri])

    registry = Registry(retrieve=retrieve).with_resource(base_uri, retrieve(base_uri))
    checked = 0
    errors = []

    def check_references(node, location, uri):
        if isinstance(node, dict):
            if "$ref" in node:
                try:
                    registry.resolver(uri).lookup(node["$ref"])
                except Unresolvable:
                    errors.append(f"{uri}{location}: unresolved reference {node['$ref']}")
            for key, value in node.items():
                if key not in {"example", "examples", "value"}:
                    check_references(value, f"{location}/{key}", uri)
                elif key == "examples" and isinstance(value, dict):
                    # Example Objects can be references; payloads are plain data.
                    for name, example in value.items():
                        check_references(example, f"{location}/examples/{name}", uri)
        elif isinstance(node, list):
            for index, value in enumerate(node):
                check_references(value, f"{location}/{index}", uri)

    visited_documents = set()
    while pending := documents.keys() - visited_documents:
        for uri in sorted(pending):
            visited_documents.add(uri)
            check_references(documents[uri], "#", uri)
    if errors:
        return checked, errors

    def resolve_example(example, uri):
        resolver = registry.resolver(uri)
        visited = set()
        while "$ref" in example:
            reference = urljoin(uri, example["$ref"])
            if reference in visited:
                raise ValueError(f"Cyclic example reference: {example['$ref']}")
            visited.add(reference)
            resolved = resolver.lookup(example["$ref"])
            example, resolver = resolved.contents, resolved.resolver
            uri = urldefrag(reference).url
        return example

    def validate_example(value, schema_pointer, location, uri):
        nonlocal checked
        checked += 1
        validator = OAS32Validator(
            {"$ref": f"{uri}{schema_pointer}"},
            registry=registry,
            format_checker=FormatChecker(),
        )
        for error in validator.iter_errors(value):
            instance_path = "/".join(str(part) for part in error.absolute_path)
            errors.append(f"{uri}{location}/{instance_path}: {error.message}")

    def walk(node, location, uri):
        if isinstance(node, dict):
            # Media Type, Parameter, and Header Objects hold examples beside a schema.
            if "schema" in node:
                if "example" in node:
                    validate_example(
                        node["example"], f"{location}/schema", f"{location}/example", uri
                    )
                for name, example in node.get("examples", {}).items():
                    example = resolve_example(example, uri)
                    if "value" in example:
                        validate_example(
                            example["value"], f"{location}/schema", f"{location}/examples/{name}", uri
                        )
                    else:
                        errors.append(f"{uri}{location}/examples/{name}: provide an inline value")
            # JSON Schema examples are arrays, including on nested properties.
            elif isinstance(node.get("examples"), list):
                for index, value in enumerate(node["examples"]):
                    validate_example(value, location, f"{location}/examples/{index}", uri)
            for key, value in node.items():
                if key not in {"example", "examples", "value"}:
                    pointer_key = key.replace("~", "~0").replace("/", "~1")
                    walk(value, f"{location}/{pointer_key}", uri)
        elif isinstance(node, list):
            for index, value in enumerate(node):
                walk(value, f"{location}/{index}", uri)

    for uri, document in documents.items():
        walk(document, "#", uri)
    return checked, errors


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "spec",
        type=Path,
        nargs="?",
        default=Path(__file__).resolve().parents[1] / "api/index.yaml",
    )
    arguments = parser.parse_args()
    checked, errors = check_examples(arguments.spec)
    if errors:
        for error in errors:
            print(error)
        raise SystemExit(1)
    print(f"Validated {checked} OpenAPI examples.")


if __name__ == "__main__":
    main()
