"""Validated operator relation catalog; stored relations are never rewritten."""

from collections.abc import Mapping
from dataclasses import asdict, dataclass
import re


@dataclass(frozen=True)
class RelationDefinition:
    """Stable directional meaning and configurable presentation of a relation."""

    key: str
    label: str
    description: str
    color: str = "gray"
    enabled: bool = True

    def as_dict(self) -> dict:
        """Return the JSON-compatible public definition."""
        return asdict(self)


_DEFINITIONS = (
    RelationDefinition("reference", "reference",
                       "Verweist auf eine verwandte Ressource, ohne Zustimmung, Reihenfolge oder Abhängigkeit zu behaupten."),
    RelationDefinition("part-of", "part-of", "Der Ausgang ist ein Bestandteil des Ziels.", "blue"),
    RelationDefinition("composed-of", "composed-of", "Der Ausgang besteht aus dem Ziel.", "green"),
    RelationDefinition("depends-on", "depends-on", "Der Ausgang benötigt das Ziel.", "red"),
    RelationDefinition("implements", "implements", "Der Ausgang setzt die Spezifikation des Ziels um.", "orange"),
    RelationDefinition("extends", "extends", "Der Ausgang erweitert das Ziel.", "purple"),
    RelationDefinition("references", "references", "Der Ausgang zitiert oder referenziert das Ziel.", "gray"),
    RelationDefinition("deprecates", "deprecates", "Der Ausgang erklärt das Ziel für veraltet.", "darkred"),
    RelationDefinition("parent", "parent", "Das Ziel ist dem Ausgang hierarchisch übergeordnet.", "blue"),
    RelationDefinition("child", "child", "Das Ziel ist dem Ausgang hierarchisch untergeordnet.", "green"),
    RelationDefinition("supports", "supports", "Der Ausgang stützt die Aussage des Ziels.", "green"),
    RelationDefinition("contradicts", "contradicts", "Der Ausgang widerspricht der Aussage des Ziels.", "red"),
    RelationDefinition("questions", "questions", "Der Ausgang stellt die Aussage des Ziels infrage.", "orange"),
)
_DOCUMENTATION = (_DEFINITIONS[3], *_DEFINITIONS[1:3], *_DEFINITIONS[4:8],
                  _DEFINITIONS[0], *_DEFINITIONS[8:10])
_PRESETS = {"basic": _DEFINITIONS[:4], "documentation": _DOCUMENTATION,
            "knowledge": (*_DOCUMENTATION, *_DEFINITIONS[10:])}
_KNOWN = {definition.key: definition for definition in _DEFINITIONS}
_FIELDS = {"key", "label", "description", "color", "enabled"}
_CSS_NAMES = frozenset("""
aliceblue antiquewhite aqua aquamarine azure beige bisque black blanchedalmond blue blueviolet brown burlywood
cadetblue chartreuse chocolate coral cornflowerblue cornsilk crimson cyan darkblue darkcyan darkgoldenrod
darkgray darkgreen darkgrey darkkhaki darkmagenta darkolivegreen darkorange darkorchid darkred darksalmon
darkseagreen darkslateblue darkslategray darkslategrey darkturquoise darkviolet deeppink deepskyblue dimgray
dimgrey dodgerblue firebrick floralwhite forestgreen fuchsia gainsboro ghostwhite gold goldenrod gray green
greenyellow grey honeydew hotpink indianred indigo ivory khaki lavender lavenderblush lawngreen lemonchiffon
lightblue lightcoral lightcyan lightgoldenrodyellow lightgray lightgreen lightgrey lightpink lightsalmon
lightseagreen lightskyblue lightslategray lightslategrey lightsteelblue lightyellow lime limegreen linen magenta
maroon mediumaquamarine mediumblue mediumorchid mediumpurple mediumseagreen mediumslateblue mediumspringgreen
mediumturquoise mediumvioletred midnightblue mintcream mistyrose moccasin navajowhite navy oldlace olive
olivedrab orange orangered orchid palegoldenrod palegreen paleturquoise palevioletred papayawhip peachpuff
peru pink plum powderblue purple rebeccapurple red rosybrown royalblue saddlebrown salmon sandybrown seagreen
seashell sienna silver skyblue slateblue slategray slategrey snow springgreen steelblue tan teal thistle
tomato transparent turquoise violet wheat white whitesmoke yellow yellowgreen
""".split())


def _valid_color(color: object) -> bool:
    return isinstance(color, str) and (
        color.lower() in _CSS_NAMES
        or re.fullmatch(r"#(?:[0-9a-fA-F]{3,4}|[0-9a-fA-F]{6}|[0-9a-fA-F]{8})", color) is not None)


def _custom_definition(entry: object) -> RelationDefinition:
    if not isinstance(entry, Mapping) or set(entry) - _FIELDS:
        raise ValueError("Beziehungstyp muss ein Objekt ohne unbekannte Felder sein.")
    key = entry.get("key")
    if not isinstance(key, str) or len(key) > 80 or not re.fullmatch(r"[a-z][a-z0-9]*(?:-[a-z0-9]+)*", key):
        raise ValueError("Beziehungsschlüssel muss ein Slug mit höchstens 80 Zeichen sein.")
    for field in ("label", "description"):
        if not isinstance(entry.get(field), str) or not entry[field].strip():
            raise ValueError(f"Beziehungstyp {key}: {field} muss nichtleerer Text sein.")
    color = entry.get("color", "gray")
    if not _valid_color(color):
        raise ValueError(f"Beziehungstyp {key}: ungültige CSS-Farbe.")
    enabled = entry.get("enabled", True)
    if type(enabled) is not bool:
        raise ValueError(f"Beziehungstyp {key}: enabled muss boolesch sein.")
    if key in _KNOWN and entry["description"] != _KNOWN[key].description:
        raise ValueError(f"Beziehungstyp {key}: Bedeutung eines Preset-Schlüssels darf nicht geändert werden.")
    return RelationDefinition(key, entry["label"], entry["description"], color, enabled)


def build_catalog(config: Mapping | None = None) -> tuple[RelationDefinition, ...]:
    """Build basic/documentation/knowledge plus custom types; reject invalid config."""
    if config is None:
        config = {}
    if not isinstance(config, Mapping) or set(config) - {"preset", "types"}:
        raise ValueError("RELATION_CATALOG muss ein Objekt mit preset und/oder types sein.")
    preset = config.get("preset", "documentation")
    if not isinstance(preset, str) or preset not in _PRESETS:
        raise ValueError(f"Unbekanntes Beziehungspreset: {preset!r}")
    entries = config.get("types", [])
    if not isinstance(entries, list):
        raise ValueError("RELATION_CATALOG.types muss eine Liste sein.")
    catalog = {definition.key: definition for definition in _PRESETS[preset]}
    seen = set()
    for entry in entries:
        definition = _custom_definition(entry)
        if definition.key in seen:
            raise ValueError(f"Doppelter Beziehungsschlüssel: {definition.key}")
        seen.add(definition.key)
        catalog[definition.key] = definition
    return tuple(catalog.values())


DEFAULT_CATALOG = build_catalog()
RELATION_TYPES = tuple((definition.key, definition.color) for definition in DEFAULT_CATALOG if definition.enabled)
