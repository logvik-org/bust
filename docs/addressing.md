# Base address and address range

A module answers for an address range: a block of `2**G_MODULE_ADDR_WIDTH`
addresses that starts at its base address. You set both with generics when
you instantiate the module. Inside the range, each register sits at its
register offset, its distance from the base address. The `address` keys in the
JSON file are register offsets, and so are the `C_<MODULE>_<REG>_OFFSET`
constants in the VHDL and the `<MODULE>_<REG>_OFFSET` constants in the headers. An address on
the bus is the base address plus a register offset.

Three generics of the bus endpoint control how the module decodes an address.
The register file and the starter top level have the same three:

| Generic | Default | What it sets |
|---|---|---|
| `G_BASE_ADDRESS` | 0 | Where the address range starts. An `unsigned` of `addr_width` bits. |
| `G_CHECK_BASE_ADDRESS` | `true` | Whether the module compares the high address bits of each access with `G_BASE_ADDRESS`. |
| `G_MODULE_ADDR_WIDTH` | `C_<MODULE>_MODULE_ADDR_WIDTH` | How many low address bits the module decodes. The address range is `2**G_MODULE_ADDR_WIDTH` addresses. |

`addr_width` in the JSON file is the width of the address on the bus. Of
those bits, the low `G_MODULE_ADDR_WIDTH` belong to the module's address range,
and the bits above them to the base address. `C_<MODULE>_MODULE_ADDR_WIDTH`,
in `<module>_regfile_pkg`, is the number of low bits that select a register. The
registers need all of them, so `G_MODULE_ADDR_WIDTH` cannot be smaller.

## How an address is decoded

The register file splits each address into three parts. The figure shows the
timer from [Getting started](getting-started.md), whose registers sit at
register offsets `0x0` to `0xC`, so `C_TIMER_MODULE_ADDR_WIDTH` is 4. The bit numbers
at the top are for `G_MODULE_ADDR_WIDTH => 12`, a 4 KiB address range.

```{raw} html
<svg class="addr-fig" viewBox="0 0 456 311" role="img" aria-label="How the register file splits an address into base address, the part of the address range above the registers and register select, for three settings of the generics"><text class="bits" x="10" y="14" text-anchor="start">31</text><text class="bits" x="217" y="14" text-anchor="end">12</text><text class="bits" x="223" y="14" text-anchor="start">11</text><text class="bits" x="369" y="14" text-anchor="end">4</text><text class="bits" x="375" y="14" text-anchor="start">3</text><text class="bits" x="446" y="14" text-anchor="end">0</text><rect class="f-base" x="8" y="22" width="212" height="30" rx="3"/><rect class="f-zero" x="220" y="22" width="152" height="30" rx="3"/><rect class="f-reg" x="372" y="22" width="76" height="30" rx="3"/><text class="t" x="114" y="42" text-anchor="middle">base address</text><text class="t" x="296" y="42" text-anchor="middle">above the registers</text><text class="t-reg" x="410" y="42" text-anchor="middle">register</text><line class="brace" x1="373" y1="60" x2="447" y2="60"/><line class="brace" x1="373" y1="55" x2="373" y2="60"/><line class="brace" x1="447" y1="55" x2="447" y2="60"/><text class="code" x="447" y="74" text-anchor="end">C_TIMER_MODULE_ADDR_WIDTH bits</text><line class="brace" x1="221" y1="88" x2="447" y2="88"/><line class="brace" x1="221" y1="83" x2="221" y2="88"/><line class="brace" x1="447" y1="83" x2="447" y2="88"/><text class="code" x="334" y="102" text-anchor="middle">range: G_MODULE_ADDR_WIDTH bits</text><line class="brace" x1="9" y1="88" x2="219" y2="88"/><line class="brace" x1="9" y1="83" x2="9" y2="88"/><line class="brace" x1="219" y1="83" x2="219" y2="88"/><text class="code" x="114" y="102" text-anchor="middle">the rest of addr_width</text><text class="row" x="8" y="136" text-anchor="start">A</text><text class="code" x="24" y="136" text-anchor="start">G_CHECK_BASE_ADDRESS =&gt; true, G_MODULE_ADDR_WIDTH =&gt; 4</text><rect class="f-base" x="8" y="143" width="364" height="30" rx="3"/><text class="t" x="190" y="163" text-anchor="middle">compared with G_BASE_ADDRESS</text><rect class="f-reg" x="372" y="143" width="76" height="30" rx="3"/><text class="t-reg" x="410" y="163" text-anchor="middle">register</text><text class="row" x="8" y="199" text-anchor="start">B</text><text class="code" x="24" y="199" text-anchor="start">G_CHECK_BASE_ADDRESS =&gt; false, G_MODULE_ADDR_WIDTH =&gt; 12</text><rect class="f-ignore" x="8" y="206" width="212" height="30" rx="3"/><text class="t" x="114" y="226" text-anchor="middle">not checked</text><rect class="f-zero" x="220" y="206" width="152" height="30" rx="3"/><text class="t" x="296" y="226" text-anchor="middle">must be 0</text><rect class="f-reg" x="372" y="206" width="76" height="30" rx="3"/><text class="t-reg" x="410" y="226" text-anchor="middle">register</text><text class="row" x="8" y="262" text-anchor="start">C</text><text class="code" x="24" y="262" text-anchor="start">G_CHECK_BASE_ADDRESS =&gt; false, G_MODULE_ADDR_WIDTH =&gt; 4</text><rect class="f-ignore" x="8" y="269" width="364" height="30" rx="3"/><text class="t" x="190" y="289" text-anchor="middle">not checked</text><rect class="f-reg" x="372" y="269" width="76" height="30" rx="3"/><text class="t-reg" x="410" y="289" text-anchor="middle">register</text></svg>
```

- **Register select**, the low `C_<MODULE>_MODULE_ADDR_WIDTH` bits, picks the
  register.
- **Above the registers**, bits `C_<MODULE>_MODULE_ADDR_WIDTH` to
  `G_MODULE_ADDR_WIDTH - 1`, must be 0. An address where one of them is set is
  in the address range but above the registers. There are no such bits when
  `G_MODULE_ADDR_WIDTH` has its default.
- **Base address**, bit `G_MODULE_ADDR_WIDTH` and up, must equal the same
  bits of `G_BASE_ADDRESS` when `G_CHECK_BASE_ADDRESS` is `true`. When it is
  `false`, the module does not look at them.

An access that fails a check gets an [error response](buses.md#errors), and so
does an access to an unused register offset, such as `0x8` in a module with
registers at `0x0`, `0x4` and `0xC`. A failed write changes nothing,
and a failed read returns `G_UNMAPPED_READ_DATA`, 0 by default.

## Choosing the settings

Two questions decide the settings.

**Does the interconnect check the base address?** Many interconnects, such as
an AXI4-Lite crossbar or the IPBus fabric, forward an access to a module only
when its address falls in the module's address range. The base address is then
checked already, so set `G_CHECK_BASE_ADDRESS => false`. The module then does
not use `G_BASE_ADDRESS`, and you can leave it out. On a bus where every module
sees every access, nothing else checks the base address. Set
`G_CHECK_BASE_ADDRESS => true` and give the module its base address with
`G_BASE_ADDRESS`.

**How large is the module's address range?** Set `G_MODULE_ADDR_WIDTH` to
match the address range your system gives the module, for example 12 for
4 KiB. An access to an address in that range where no register sits then gets
an error, so a wrong address in software shows up as an error instead of
reaching a register. The default decodes only the bits the registers need. It
is safe only when no access can reach an address above the registers, which is
the case with `G_CHECK_BASE_ADDRESS => true`, or with an interconnect that
forwards exactly the `2**C_<MODULE>_MODULE_ADDR_WIDTH` addresses of the
registers. When in doubt, set `G_MODULE_ADDR_WIDTH`.

With the timer at base address `x"4000_1000"` in a 4 KiB address range, the
settings in the figure answer these accesses:

| | `G_CHECK_BASE_ADDRESS` | `G_MODULE_ADDR_WIDTH` | `0x4000_1004` | `0x4000_1014` | `0x5000_1004` |
|---|---|---|---|---|---|
| A | `true` | 4, the default | `load` | error | error |
| B | `false` | 12 | `load` | error | `load` |
| C | `false` | 4, the default | `load` | `load` | `load` |

- **A** is for a bus where every module sees every access. The module compares
  every address bit, so only its own 16 bytes answer. With
  `G_MODULE_ADDR_WIDTH => 12` as well, it answers the same, and the base
  address must then be a multiple of 4 KiB.
- **B** is for an interconnect that forwards the timer's 4 KiB to it. Every
  address in the range where no register sits gets an error. The module
  leaves the base address bits to the interconnect, so it would answer
  `0x5000_1004` too, but the interconnect never forwards that address.
- **C** is B with the default module address width. The module decodes only the
  low 4 bits, so `0x4000_1014` reaches `load` through those bits, `0x4`, with no
  error. A wrong address in software can then hit a pulse or clear-on-read
  register. Use B instead.

## Alignment

With `G_CHECK_BASE_ADDRESS` set to `true`, `G_BASE_ADDRESS` must be a multiple
of `2**G_MODULE_ADDR_WIDTH`, so the address range starts on a boundary of its
own size. Otherwise the register file stops the simulation with an assertion
failure. For the timer, `x"4000_1000"` works with any module address width up
to 12, and `x"4000_1010"` only with the default of 4. With
`G_CHECK_BASE_ADDRESS` set to `false`, the module does not use
`G_BASE_ADDRESS`.

`G_MODULE_ADDR_WIDTH` must be at least `C_<MODULE>_MODULE_ADDR_WIDTH` and at
most `addr_width`. Another value also stops the simulation with an assertion
failure.

## Byte and word addresses

The register file compares every low address bit with the register offsets.
With 32-bit data on a bus whose addresses count bytes, the timer's registers
sit at `0x0`, `0x4`, `0x8` and `0xC`. An access to an address between them,
such as `0x4000_1005`, matches no register and gets an error, as an unused
register offset does. On AXI4-Lite a read of `0x1` with a register at `0x0`
gets `SLVERR`, not the register.

`byte_addressable` in the module changes only how far apart bust places the
registers that have no address, which register offsets it accepts in the JSON
file, and which addresses the generated testbench tries. The generated HDL is
the same either way. See
[Byte and word addresses](register-map-format.md#byte-and-word-addresses).

On IPBus, addresses count 32-bit words. The IPBus endpoint passes the low
`addr_width` bits of `ipb_addr` to the register file, and the IPBus fabric
decodes the higher bits. [IPBus](buses.md#ipbus) has the details.

## Why the base address is a generic

The base address describes where you place the module, not the module itself,
so it is not a key in the JSON file. You can instantiate one register map
several times at different base addresses, and you can move a module without
generating it again. The headers give register offsets for the same reason, and
your software adds the base address.

## Field offsets in the headers

In the headers, `_OFFSET` also names the lowest bit of a field, as in
`<MODULE>_<REG>_<FIELD>_OFFSET`. That is a bit position inside the register,
not an address. [Software headers](headers.md#constant-names)
lists the constants.
