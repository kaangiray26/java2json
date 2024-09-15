#!env/bin/python3
# -*- coding: utf-8 -*-

import os
import json
import argparse
import javalang
from lib.types import type_conversions
from javalang.tree import Node
from javalang.tree import Declaration
from javalang.tree import ClassDeclaration
from javalang.tree import FieldDeclaration
from javalang.tree import EnumDeclaration
from javalang.tree import InterfaceDeclaration

def create_new_schema(class_name):
    return {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "$id": "",
        "title": class_name.split(".")[-1],
        "description": f"Schema for {class_name}",
    }

class Architect:
    def __init__(self):
        # Variables
        self.trees = {}
        self.classes = {}
        self.directory = os.path.join("btb-objektmodell", "src", "main", "java")
        self.ignored_attributes = ["collection", "visited", "complexObjects", "objMapper", "uuid", "createdById", "updatedById"]

        # Check if the directory exists
        if not os.path.exists("btb-objektmodell"):
            raise Exception(f"Directory 'btb-objektmodell' does not exist!")

        # Search all directories for java classes
        for root, _dirs, files in os.walk(self.directory):
            java_files = [f for f in files if f.endswith(".java")]
            for file in java_files:
                filepath = os.path.join(root, file)
                class_name, _ = os.path.splitext(file)
                self.classes[class_name] = filepath

    """Create schemas for all classes"""
    def create_all(self):
        for class_name in self.classes:
            print(f"Creating schema for {class_name}...")
            self.create(class_name)
        print("done.")

    def create(self, class_name):
        javapath = self.classes[class_name]
        # Read the java file
        with open(javapath) as f:
            javatree =  javalang.parse.parse(f.read())

        schema = create_new_schema(class_name)

        # Find the object in the javatree with the given name
        # It can be a class, enum, interface, etc.
        for path, node in javatree.filter(Declaration):
            if node.name != class_name:
                continue

            # Match the type
            node_type = node.__class__
            if node_type == EnumDeclaration:
                schema["enum"] = self.get_enum_properties(node)
                break

            if node_type == ClassDeclaration or node_type == InterfaceDeclaration:
                schema["type"] = "object"
                schema["properties"] = self.get_class_properties(node)
                break

            print(f"Unknown type: {node_type}")
            continue

        # Write the schema to a file
        relpath = os.path.relpath(javapath, self.directory)
        schema_id = relpath.replace(os.sep, ".").replace(".java", "")
        schema["$id"] = schema_id
        with open(os.path.join("schemas", schema_id), "w", encoding="utf-8") as f:
            json.dump(schema, f, indent=4, ensure_ascii=False)

    """Return the java tree of the given class."""
    def get_class(self, class_name) -> Node:
        # Check if the class exists
        if class_name not in self.classes:
            raise Exception(f"Class {class_name} not found!")

        # Read the java file
        with open(self.classes[class_name]) as f:
            javatree =  javalang.parse.parse(f.read())

        # Get the class
        for path, node in javatree.filter(ClassDeclaration):
            if node.name != class_name:
                continue
            return node

    def get_class_properties(self, _class) -> dict:
        properties = {}
        # Check if it extends another class

        if _class.extends:
            try:
                node = self.get_class(_class.extends.name)
                properties.update(self.get_class_properties(node))
            except Exception:
                pass

        # Attributes
        for path, node in _class.filter(FieldDeclaration):
            properties[node.declarators[0].name] = self.get_property(node)

        # Remove ignored attributes
        for attr in self.ignored_attributes:
            if attr in properties:
                del properties[attr]

        return properties

    def get_enum_properties(self, node) -> list:
        return [str(constant.name) for constant in node.body.constants]

    def get_property(self, node) -> dict:
        property = {}
        if node.type.name in type_conversions:
            property["type"] = type_conversions[node.type.name]
            property["$comment"]: node.type.name
            return property

        # Find the reference class
        if node.type.name in self.classes:
            relpath = os.path.relpath(self.classes[node.type.name], self.directory)
            schema_id = relpath.replace(os.sep, ".").replace(".java", "")
            property["$ref"] = schema_id
            return property

        # Default fallback
        property["type"] = "unknown"
        property["$comment"] = node.type.name
        return property

if __name__ == "__main__":
    # Create directories
    os.makedirs("schemas", exist_ok=True)

    architect = Architect()
    architect.create_all()