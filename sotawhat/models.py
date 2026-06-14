from dataclasses import dataclass, field

@dataclass
class Result:
    id: str
    title: str
    authors: list
    date: str
    url: str
    abstract: str
    source: str
    extra: dict = field(default_factory=dict)
