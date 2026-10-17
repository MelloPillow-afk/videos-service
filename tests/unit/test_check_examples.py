"""Exercise example validation across local OpenAPI files."""

import tempfile
import unittest
from pathlib import Path

import yaml

from scripts.check_examples import check_examples


class CheckExamplesTests(unittest.TestCase):
    def setUp(self) -> None:
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.root = Path(self.directory.name)
        self.spec = self.root / "index.yaml"
        self.write(
            "index.yaml",
            {
                "content": {
                    "application/json": {
                        "schema": {"$ref": "schemas/video.yaml"},
                        "examples": {"video": {"$ref": "examples/video.yaml"}},
                    }
                },
                "parameters": [{"$ref": "parameters/limit.yaml"}],
            },
        )
        self.write(
            "schemas/video.yaml",
            {
                "type": "object",
                "required": ["id"],
                "properties": {"id": {"$ref": "id.yaml"}},
            },
        )
        self.write(
            "schemas/id.yaml",
            {
                "type": "string",
                "format": "uuid",
                "examples": ["550e8400-e29b-41d4-a716-446655440000"],
            },
        )
        self.write("examples/video.yaml", {"$ref": "nested/video.yaml"})
        self.write(
            "examples/nested/video.yaml", {"value": {"id": "550e8400-e29b-41d4-a716-446655440000"}}
        )
        self.write(
            "parameters/limit.yaml",
            {
                "name": "limit",
                "in": "query",
                "schema": {"$ref": "../schemas/limit.yaml"},
                "example": 20,
            },
        )
        self.write("schemas/limit.yaml", {"type": "integer", "minimum": 1, "maximum": 100})

    def write(self, relative_path: str, document: object) -> None:
        path = self.root / relative_path
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(yaml.safe_dump(document))

    def test_validates_nested_schemas_parameters_and_example_references(self) -> None:
        self.assertEqual(check_examples(self.spec), (3, []))

    def test_rejects_invalid_payload_against_external_schema(self) -> None:
        self.write("examples/nested/video.yaml", {"value": {"id": "invalid"}})
        checked, errors = check_examples(self.spec)
        self.assertEqual(checked, 3)
        self.assertEqual(len(errors), 1)
        self.assertIn("index.yaml#/content/application~1json/examples/video/id", errors[0])
        self.assertIn("'uuid'", errors[0])

    def test_checks_examples_inside_external_schemas(self) -> None:
        self.write("schemas/id.yaml", {"type": "string", "format": "uuid", "examples": ["invalid"]})
        checked, errors = check_examples(self.spec)
        self.assertEqual(checked, 3)
        self.assertEqual(len(errors), 1)
        self.assertIn("schemas/id.yaml#/examples/0", errors[0])

    def test_reports_broken_transitive_references(self) -> None:
        (self.root / "schemas/id.yaml").unlink()
        checked, errors = check_examples(self.spec)
        self.assertEqual(checked, 0)
        self.assertEqual(len(errors), 1)
        self.assertIn("schemas/video.yaml#/properties/id", errors[0])
        self.assertIn("unresolved reference id.yaml", errors[0])

    def test_rejects_remote_references_without_fetching(self) -> None:
        self.write("schemas/id.yaml", {"$ref": "https://example.invalid/id.yaml"})
        checked, errors = check_examples(self.spec)
        self.assertEqual(checked, 0)
        self.assertEqual(len(errors), 1)
        self.assertIn("unresolved reference https://example.invalid/id.yaml", errors[0])


if __name__ == "__main__":
    unittest.main()
