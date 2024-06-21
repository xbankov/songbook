def is_tag(text: str) -> bool:
    stripped = text.strip()
    return "\n" not in stripped and stripped.startswith("{") and stripped.endswith("}")


def is_ug_tag(text: str) -> bool:
    stripped = text.strip()
    return (
        "\n" not in stripped
        and stripped.startswith("[")
        and stripped.endswith("]")
        and "[tab]" not in stripped
        and "[ch]" not in stripped
    )


def get_tag_items(tag):
    splits = tag.strip()[1:-1].split(":", 1)
    return splits[0].strip(), (splits[1].strip() if len(splits) == 2 else None)
