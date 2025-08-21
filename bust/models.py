# bust/models.py
from __future__ import annotations
from typing import List, Literal, Optional, Union
from pydantic import BaseModel, Field, field_validator, model_validator
import hashlib
import json

Bus = Literal["axi", "ipbus"]
Access = Literal["rw", "ro"]
Mode = Literal["rw", "ro", "pulse"]
Behavior = Literal["self_clear"]  # extend later if needed

def _parse_addr(v: Union[int, str]) -> int:
    if isinstance(v, int):
        return v
    v = v.strip().lower()
    if v.startswith("0x"):
        return int(v, 16)
    return int(v)

class FieldDef(BaseModel):
    name: str
    lsb: int = Field(ge=0)
    msb: int = Field(ge=0)
    access: Access
    behavior: Optional[Behavior] = None

    @model_validator(mode="after")
    def _width_ok(self):
        if self.msb < self.lsb:
            raise ValueError(f"Field '{self.name}': msb < lsb")
        return self

    @property
    def width(self) -> int:
        return self.msb - self.lsb + 1

class RegisterDef(BaseModel):
    name: str
    addr: Union[int, str]
    mode: Mode
    reset: int = 0
    fields: List[FieldDef] = Field(default_factory=list)

    @field_validator("addr", mode="before")
    @classmethod
    def _coerce_addr(cls, v):
        return _parse_addr(v)

class RegMap(BaseModel):
    name: str
    bus: Bus
    addr_width: int = 16
    data_width: int = 32
    endianness: Literal["little","big"] = "little"
    base_addr: Union[int, str] = "0x0000"
    registers: List[RegisterDef]

    @field_validator("base_addr", mode="before")
    @classmethod
    def _coerce_base(cls, v):
        return _parse_addr(v)

    @model_validator(mode="after")
    def _semantic_checks(self):
        # basic uniqueness & alignment checks
        seen = set()
        word_bytes = max(1, self.data_width // 8)
        for r in self.registers:
            if r.addr in seen:
                raise ValueError(f"Duplicate register address 0x{r.addr:X} ('{r.name}')")
            seen.add(r.addr)
            if r.addr % word_bytes != 0:
                raise ValueError(f"Register '{r.name}' not aligned to {word_bytes} bytes")
        return self

    # Canonical dump used for hashing / determinism
    def canonical(self) -> dict:
        def canon_reg(r: RegisterDef) -> dict:
            fs = sorted(r.fields, key=lambda f: (f.lsb, f.msb, f.name))
            return {
                "name": r.name,
                "addr": r.addr,
                "mode": r.mode,
                "reset": r.reset,
                "fields": [
                    {"name": f.name, "lsb": f.lsb, "msb": f.msb,
                     "access": f.access, "behavior": f.behavior}
                    for f in fs
                ],
            }
        regs = sorted(self.registers, key=lambda r: (r.addr, r.name))
        return {
            "name": self.name,
            "bus": self.bus,
            "addr_width": self.addr_width,
            "data_width": self.data_width,
            "endianness": self.endianness,
            "base_addr": self.base_addr,
            "registers": [canon_reg(r) for r in regs],
        }

    def canonical_hash(self) -> str:
        blob = json.dumps(self.canonical(), separators=(",", ":"), sort_keys=True)
        return "sha256:" + hashlib.sha256(blob.encode()).hexdigest()

class GenOptions(BaseModel):
    targets: List[str]
    template_pack: str = "default-v1"
    output_naming: Literal["bust","flat","custom"] = "bust"
    validate_only: bool = False

class ValidateResult(BaseModel):
    valid: bool
    warnings: List[str] = Field(default_factory=list)
    canonical_hash: Optional[str] = None
    normalized: Optional[dict] = None