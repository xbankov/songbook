def is_tag(text: str):
    stripped = text.strip()
    return "\n" not in stripped and stripped.startswith("{") and stripped.endswith("}")


def get_tag_items(tag):
    splits = tag.strip()[1:-1].split(":", 1)
    return splits[0].strip(), (splits[1].strip() if len(splits) == 2 else None)
