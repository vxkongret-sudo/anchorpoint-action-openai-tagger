import random

import apsync as aps

attribute_colors = [
        "grey", "blue", "purple", "green",
        "turk", "orange", "yellow", "red"]

def ensure_attribute(database: aps.Api, attribute_name: str) -> aps.Attribute:
    """Ensure an attribute exists in the database"""
    attribute = database.attributes.get_attribute(attribute_name)
    if not attribute:
        attribute = database.attributes.create_attribute(
            attribute_name, aps.AttributeType.multiple_choice_tag
        )
    return attribute

def replace_tag(tag: str, variants: list[list[str]]) -> str:
    """Replace a tag with a variant if it exists"""
    if not variants:
        return tag
    for variant in variants:
        if tag in variant:
            return variant[0]

    return tag

def check_or_update_attribute(attribute: aps.Attribute, tag: str, database: aps.Api):
    """Check if a tag exists in an attribute and add it if it doesn't"""
    anchorpoint_tags = attribute.tags
    colors = attribute_colors

    # Create a set of anchorpoint tag names for faster lookup
    anchorpoint_tag_names = {a_tag.name for a_tag in anchorpoint_tags}
    if tag not in anchorpoint_tag_names:
        new_tag = aps.AttributeTag(tag, random.choice(colors))
        anchorpoint_tags.append(new_tag)
        database.attributes.set_attribute_tags(attribute, anchorpoint_tags)
        return new_tag

    for a_tag in anchorpoint_tags:
        if a_tag.name == tag:
            return a_tag

    raise ValueError(f"Tag {tag} not found in the attribute tags: {anchorpoint_tag_names}")