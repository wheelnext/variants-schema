# /// script
# requires-python = ">=3.13"
# dependencies = [
#     "pydantic==2.12.4"
# ]
# ///
"""
Python Script to generate the JSON Schema for Wheel Variant JSON side.
"""

import json
import re
from typing import Annotated

from pydantic import BaseModel
from pydantic import ConfigDict
from pydantic import Field
from pydantic import field_validator
from pydantic import model_validator


class DefaultPriorities(BaseModel):
    """Default provider priorities configuration."""

    namespace: Annotated[
        list[str], Field(min_length=1, description="Default namespace priorities")
    ]

    feature: (
        Annotated[
            dict[str, list[str]],
            Field(description="Default feature priorities (by namespace)"),
        ]
        | None
    ) = None

    property: (
        Annotated[
            dict[str, dict[str, list[str]]],
            Field(description="Default property priorities (by namespace)"),
        ]
        | None
    ) = None

    @field_validator("namespace")
    @classmethod
    def validate_namespace(cls, v: list[str]) -> list[str]:
        pattern = re.compile(r"^[a-z0-9_]+$")
        for item in v:
            if not pattern.match(item):
                raise ValueError(f"Namespace '{item}' must match ^[a-z0-9_]+$")
        if len(v) != len(set(v)):
            raise ValueError("Namespace items must be unique")
        return v

    @field_validator("feature")
    @classmethod
    def validate_feature(
        cls,
        v: dict[str, list[str]] | None,
    ) -> dict[str, list[str]] | None:
        if v is None:
            return v

        ns_pattern = re.compile(r"^[a-z0-9_]+$")
        feat_pattern = re.compile(r"^[a-z0-9_]+$")

        for namespace, features in v.items():
            if not ns_pattern.match(namespace):
                raise ValueError(
                    f"Feature namespace '{namespace}' must match ^[a-z0-9_]+$"
                )
            for feature in features:
                if not feat_pattern.match(feature):
                    raise ValueError(f"Feature '{feature}' must match ^[a-z0-9_]+$")
            if len(features) != len(set(features)):
                raise ValueError(f"Features for namespace '{namespace}' must be unique")
        return v

    @field_validator("property")
    @classmethod
    def validate_property(
        cls, v: dict[str, dict[str, list[str]]] | None
    ) -> dict[str, dict[str, list[str]]] | None:
        if v is None:
            return v

        ns_pattern = re.compile(r"^[a-z0-9_]+$")
        feat_pattern = re.compile(r"^[a-z0-9_]+$")
        prop_pattern = re.compile(r"^[a-z0-9_.]+$")

        for namespace, features in v.items():
            if not ns_pattern.match(namespace):
                raise ValueError(
                    f"Property namespace '{namespace}' must match ^[a-z0-9_]+$"
                )

            for feature, properties in features.items():
                if not feat_pattern.match(feature):
                    raise ValueError(
                        f"Property feature '{feature}' must match ^[a-z0-9_]+$"
                    )

                for prop in properties:
                    if not prop_pattern.match(prop):
                        raise ValueError(
                            f"Property value '{prop}' must match ^[a-z0-9_.]+$"
                        )

                if len(properties) != len(set(properties)):
                    raise ValueError(
                        f"Properties for '{namespace}.{feature}' must be unique"
                    )
        return v

    model_config = ConfigDict(populate_by_name=True)


class Provider(BaseModel):
    """Provider information."""

    plugin_api: Annotated[
        str | None,
        Field(alias="plugin-api", description="Object reference to plugin class"),
    ] = None

    enable_if: Annotated[
        str | None,
        Field(
            alias="enable-if",
            min_length=1,
            description="Environment marker specifying when to enable the plugin",
        ),
    ] = None

    install_time: Annotated[
        bool,
        Field(
            alias="install-time",
            description="Whether a plugin is used at install time",
        ),
    ] = True

    optional: Annotated[
        bool,
        Field(description="Whether the provider is optional"),
    ] = False

    requires: (
        Annotated[
            list[str],
            Field(description="Dependency specifiers for how to install the plugin"),
        ]
        | None
    ) = None

    @field_validator("plugin_api")
    @classmethod
    def validate_plugin_api(cls, v: str | None) -> str | None:
        if v is None:
            return v

        pattern = re.compile(r"^([a-zA-Z0-9._]+ *: *[a-zA-Z0-9._]+)|([a-zA-Z0-9._]+)$")
        if not pattern.match(v):
            raise ValueError(
                "plugin-api must match pattern: "
                "^([a-zA-Z0-9._]+ *: *[a-zA-Z0-9._]+)|([a-zA-Z0-9._]+)$"
            )
        return v

    @field_validator("requires")
    @classmethod
    def validate_requires(cls, v: list[str] | None) -> list[str] | None:
        if v is None:
            return v

        for item in v:
            if not item or len(item) < 1:
                raise ValueError("Each requires item must have minimum length 1")

        if len(v) != len(set(v)):
            raise ValueError("Requires items must be unique")
        return v

    @model_validator(mode="after")
    def validate_conditional_requires(self):
        """Validate: if install_time is not False, requires must be present."""
        if self.install_time is not False and self.requires is None:
            raise ValueError("'requires' is required when 'install-time' is not false")
        return self

    model_config = ConfigDict(populate_by_name=True)


class VariantsSchema(BaseModel):
    """Combined index metadata for wheel variants."""

    default_priorities: Annotated[
        DefaultPriorities,
        Field(alias="default-priorities", description="Default provider priorities"),
    ]

    providers: Annotated[
        dict[str, Provider],
        Field(description="Mapping of namespaces to provider information"),
    ]

    static_properties: Annotated[
        dict[str, dict[str, list[str]]] | None,
        Field(
            alias="static-properties",
            description="Static properties for AoT providers (by namespace)",
        ),
    ] = None

    variants: Annotated[
        dict[str, dict[str, dict[str, list[str]]]],
        Field(description="Mapping of variant labels to properties"),
    ]

    @field_validator("providers")
    @classmethod
    def validate_providers(cls, v: dict[str, Provider]) -> dict[str, Provider]:
        pattern = re.compile(r"^[A-Za-z0-9_]+$")
        for key in v:
            if not pattern.match(key):
                raise ValueError(f"Provider key '{key}' must match ^[A-Za-z0-9_]+$")

        return v

    @field_validator("static_properties")
    @classmethod
    def validate_static_properties(
        cls, v: dict[str, dict[str, list[str]]] | None
    ) -> dict[str, dict[str, list[str]]] | None:
        if v is None:
            return v

        ns_pattern = re.compile(r"^[a-z0-9_]+$")
        feat_pattern = re.compile(r"^[a-z0-9_]+$")
        val_pattern = re.compile(r"^[a-z0-9_.]+$")

        for namespace, features in v.items():
            if not ns_pattern.match(namespace):
                raise ValueError(
                    f"Static property namespace '{namespace}' must match ^[a-z0-9_]+$"
                )

            for feature, values in features.items():
                if not feat_pattern.match(feature):
                    raise ValueError(
                        f"Static property feature '{feature}' must match ^[a-z0-9_]+$"
                    )

                for val in values:
                    if not val_pattern.match(val):
                        raise ValueError(
                            f"Static property value '{val}' must match ^[a-z0-9_.]+$"
                        )

                if len(values) != len(set(values)):
                    raise ValueError(
                        f"Static property values for '{namespace}.{feature}' must be unique"
                    )
        return v

    @field_validator("variants")
    @classmethod
    def validate_variants(
        cls, v: dict[str, dict[str, dict[str, list[str]]]]
    ) -> dict[str, dict[str, dict[str, list[str]]]]:
        label_pattern = re.compile(r"^[a-z0-9_.]{1,16}$")
        ns_pattern = re.compile(r"^[a-z0-9_.]+$")
        feat_pattern = re.compile(r"^[a-z0-9_.]+$")
        val_pattern = re.compile(r"^[a-z0-9_.]+$")

        for label, namespaces in v.items():
            # Validate variant label
            if not label_pattern.match(label):
                raise ValueError(
                    f"Variant label '{label}' must match ^[a-z0-9_.]{1, 16}$"
                )

            for namespace, features in namespaces.items():
                # Validate namespace
                if not ns_pattern.match(namespace):
                    raise ValueError(
                        f"Variant namespace '{namespace}' must match ^[a-z0-9_.]+$"
                    )

                for feature, values in features.items():
                    # Validate feature
                    if not feat_pattern.match(feature):
                        raise ValueError(
                            f"Variant feature '{feature}' must match ^[a-z0-9_.]+$"
                        )

                    # Validate values
                    if len(values) < 1:
                        raise ValueError(
                            f"Variant '{label}.{namespace}.{feature}' must have at least 1 value"
                        )

                    for val in values:
                        if not val_pattern.match(val):
                            raise ValueError(
                                f"Variant value '{val}' must match ^[a-z0-9_.]+$"
                            )

                    if len(values) != len(set(values)):
                        raise ValueError(
                            f"Variant values for '{label}.{namespace}.{feature}' must be unique"
                        )
        return v

    model_config = ConfigDict(populate_by_name=True)


# Function to regenerate JSON schema from Pydantic model
def regenerate_json_schema(indent: int = 2, include_metadata: bool = True) -> str:
    """
    Generate JSON Schema from the Pydantic model.

    Args:
        indent: Number of spaces for JSON indentation
        include_metadata: Whether to include title and description metadata

    Returns:
        JSON schema as a string
    """
    schema = VariantsSchema.model_json_schema(by_alias=True, mode="serialization")

    if include_metadata:
        # Add custom metadata matching original schema
        schema["$schema"] = "https://json-schema.org/draft/2020-12/schema"
        schema["$id"] = "https://wheelnext.dev/variants.json"
        schema["title"] = "{name}-{version}-variants.json"

    return json.dumps(schema, indent=indent)


# Example usage
if __name__ == "__main__":
    # Generate and print the JSON schema
    json_schema = regenerate_json_schema()

    print(json_schema)

    # # Example: Parse a variants JSON
    # example_data = {
    #     "default-priorities": {"namespace": ["cuda", "cpu"]},
    #     "providers": {
    #         "cuda_provider": {
    #             "plugin-api": "my_module:CudaPlugin",
    #             "install-time": True,
    #             "requires": ["nvidia-cuda>=12.0"],
    #         }
    #     },
    #     "variants": {"cuda12": {"cuda": {"version": ["12.0", "12.1"]}}},
    # }

    # # Validate and parse
    # variants = VariantsSchema.model_validate(example_data)
    # print("\nParsed successfully!")
    # print(variants.model_dump(by_alias=True))
