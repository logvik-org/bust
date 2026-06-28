-- Register definitions for the prototype module.
--
-- The demo uses deliberately generic names (reg0..reg11, field0..) so the record
-- structure and naming scheme can be reviewed without semantic distraction.
-- The types here model what the generator will emit per module. Registers and
-- fields are expressed as nested records (regs.<reg>.<field>) so a module with
-- many registers stays one record signal instead of a flat list of signals,
-- and so the hardware sees each field by name with its modifiers attached.
--
-- Three record families, all nested register -> field:
--   t_prototype_regs      internal storage (one per field that holds state)
--   t_prototype_to_hw     regfile -> hardware (hw r / rw field values)
--   t_prototype_from_hw   hardware -> regfile (hw w / rw values + modifiers)
--
-- Field-level input records carry the value together with their modifier
-- strobes, so a field's write-enable or set/clear lives next to its value
-- (from_hw.reg4.field0.we, from_hw.reg4.field1.set, ...).
--
-- prototype register map (byte offsets; see local-bus-hdl.md for why the local
-- bus carries byte addresses):
--   reg0  0x00  field0 [0]     sw rw  hw r
--               field1 [2:1]   sw rw  hw r
--   reg1  0x04  field0 [3:0]   sw ro  hw w   we
--               field1 [4]     sw ro  hw w   (continuous)
--               field2 [5]     sw ro  hw w   wel
--   reg2  0x08  field0 [0]     sw wo  hw r
--   reg3  0x0C  field0 [7:0]   sw rw  hw na
--   reg4  0x10  field0 [3:0]   sw rw  hw rw  we
--               field1 [8]     sw rw  hw r   hwset, hwclr
--   reg5  0x14  field0 [3:0]   sw rw  hw r   onread rclr
--               field1 [7:4]   sw rw  hw r   onread rset
--   reg6  0x18  field0 [3:0]   sw rw  hw r   onwrite woset
--               field1 [7:4]   sw rw  hw r   onwrite woclr
--               field2 [11:8]  sw rw  hw r   onwrite wot
--   reg7  0x1C  field0 [3:0]   sw rw  hw r   onwrite wzs
--               field1 [7:4]   sw rw  hw r   onwrite wzc
--               field2 [11:8]  sw rw  hw r   onwrite wzt
--   reg8  0x20  field0 [3:0]   sw rw  hw r   onwrite wclr
--               field1 [7:4]   sw rw  hw r   onwrite wset
--   reg9  0x24  field0 [3:0]   sw rw  hw r   swmod
--               field1 [7:4]   sw rw  hw r   swacc
--   reg10 0x28  field0 [3:0]   sw rw  hw r   singlepulse
--   reg11 0x2C  field0 [1:0]   sw rw  hw r   enum {STATE0..STATE3}
library ieee;
use ieee.std_logic_1164.all;
use ieee.numeric_std.all;

use work.localbus_pkg.all;

package prototype_regfile_pkg is

  constant C_ADDR_REG0 : std_logic_vector(31 downto 0) := 32x"00";
  constant C_ADDR_REG1 : std_logic_vector(31 downto 0) := 32x"04";
  constant C_ADDR_REG2 : std_logic_vector(31 downto 0) := 32x"08";
  constant C_ADDR_REG3 : std_logic_vector(31 downto 0) := 32x"0C";
  constant C_ADDR_REG4 : std_logic_vector(31 downto 0) := 32x"10";
  constant C_ADDR_REG5 : std_logic_vector(31 downto 0) := 32x"14";
  constant C_ADDR_REG6 : std_logic_vector(31 downto 0) := 32x"18";
  constant C_ADDR_REG7 : std_logic_vector(31 downto 0) := 32x"1C";
  constant C_ADDR_REG8 : std_logic_vector(31 downto 0) := 32x"20";
  constant C_ADDR_REG9 : std_logic_vector(31 downto 0) := 32x"24";
  constant C_ADDR_REG10 : std_logic_vector(31 downto 0) := 32x"28";
  constant C_ADDR_REG11 : std_logic_vector(31 downto 0) := 32x"2C";

  -- Register-select width. 6 bits decode a 64-byte window (0x00..0x3F); the
  -- registers occupy 0x00..0x2C. base_match compares the bits above this width,
  -- so the base address must be aligned to this 64-byte window.
  constant C_MODULE_ADDR_WIDTH : natural := 6;

  -- Enumerated field type for reg11.field0: hardware and software see named
  -- states instead of raw bits, so assignments are compile-time type-checked.
  -- The literal positions are the field's encoded values (0..3).
  type t_reg11_field0 is (STATE0, STATE1, STATE2, STATE3);
  function to_slv(v : t_reg11_field0) return std_logic_vector;
  function to_reg11_field0(s : std_logic_vector(1 downto 0)) return t_reg11_field0;

  -- Internal storage, grouped per register. One member per field that holds
  -- state (every software- or hardware-writable field). One record per
  -- register, each member a field.

  -- Stored fields of reg0.
  type t_reg0_regs is record
    field0 : std_logic;                      -- reg0.field0
    field1 : std_logic_vector(1 downto 0);   -- reg0.field1
  end record;

  -- Stored fields of reg1.
  type t_reg1_regs is record
    field0 : std_logic_vector(3 downto 0);   -- reg1.field0
    field1 : std_logic;                      -- reg1.field1
    field2 : std_logic;                      -- reg1.field2
  end record;

  -- Stored fields of reg2.
  type t_reg2_regs is record
    field0 : std_logic;                      -- reg2.field0
  end record;

  -- Stored fields of reg3.
  type t_reg3_regs is record
    field0 : std_logic_vector(7 downto 0);   -- reg3.field0
  end record;

  -- Stored fields of reg4.
  type t_reg4_regs is record
    field0 : std_logic_vector(3 downto 0);   -- reg4.field0
    field1 : std_logic;                      -- reg4.field1
  end record;

  -- Stored fields of reg5 (onread effects on software read).
  type t_reg5_regs is record
    field0 : std_logic_vector(3 downto 0);   -- reg5.field0
    field1 : std_logic_vector(3 downto 0);   -- reg5.field1
  end record;

  -- Stored fields of reg6 (write-1 onwrite effects).
  type t_reg6_regs is record
    field0 : std_logic_vector(3 downto 0);   -- reg6.field0
    field1 : std_logic_vector(3 downto 0);   -- reg6.field1
    field2 : std_logic_vector(3 downto 0);   -- reg6.field2
  end record;

  -- Stored fields of reg7 (write-0 onwrite effects).
  type t_reg7_regs is record
    field0 : std_logic_vector(3 downto 0);   -- reg7.field0
    field1 : std_logic_vector(3 downto 0);   -- reg7.field1
    field2 : std_logic_vector(3 downto 0);   -- reg7.field2
  end record;

  -- Stored fields of reg8 (whole-field onwrite effects).
  type t_reg8_regs is record
    field0 : std_logic_vector(3 downto 0);   -- reg8.field0
    field1 : std_logic_vector(3 downto 0);   -- reg8.field1
  end record;

  -- Stored fields of reg9 (swmod/swacc pulse demo).
  type t_reg9_regs is record
    field0 : std_logic_vector(3 downto 0);   -- reg9.field0
    field1 : std_logic_vector(3 downto 0);   -- reg9.field1
  end record;

  -- Stored fields of reg10 (singlepulse: self-clears one cycle after a write).
  type t_reg10_regs is record
    field0 : std_logic_vector(3 downto 0);   -- reg10.field0
  end record;

  -- Stored fields of reg11 (enumerated field0, stored as the named type).
  type t_reg11_regs is record
    field0 : t_reg11_field0;                 -- reg11.field0
  end record;

  -- Whole-module storage: the regfile keeps this as a single signal.
  type t_prototype_regs is record
    reg0 : t_reg0_regs;
    reg1 : t_reg1_regs;
    reg2 : t_reg2_regs;
    reg3 : t_reg3_regs;
    reg4 : t_reg4_regs;
    reg5 : t_reg5_regs;
    reg6 : t_reg6_regs;
    reg7 : t_reg7_regs;
    reg8 : t_reg8_regs;
    reg9 : t_reg9_regs;
    reg10 : t_reg10_regs;
    reg11 : t_reg11_regs;
  end record;

  -- Clear-type onwrite fields (reg6.field1 woclr, reg7.field1 wzc, reg8.field0
  -- wclr) reset to all 1s: software cannot set them, so a nonzero reset is what
  -- makes their clearing observable in the demo.
  constant C_PROTOTYPE_REGS_RESET : t_prototype_regs := (
    reg0 => (field0 => '0', field1 => (others => '0')),
    reg1 => (field0 => (others => '0'), field1 => '0', field2 => '0'),
    reg2 => (field0 => '0'),
    reg3 => (field0 => (others => '0')),
    reg4 => (field0 => (others => '0'), field1 => '0'),
    reg5 => (field0 => (others => '0'), field1 => (others => '0')),
    reg6 => (field0 => (others => '0'), field1 => (others => '1'), field2 => (others => '0')),
    reg7 => (field0 => (others => '0'), field1 => (others => '1'), field2 => (others => '0')),
    reg8 => (field0 => (others => '1'), field1 => (others => '0')),
    reg9 => (field0 => (others => '0'), field1 => (others => '0')),
    reg10 => (field0 => (others => '0')),
    reg11 => (field0 => STATE0));

  -- regfile -> hardware: only fields the hardware can read (hw r / rw). One
  -- record per register that has at least one hardware-readable field.

  -- reg0 fields visible to hardware.
  type t_reg0_to_hw is record
    field0 : std_logic;
    field1 : std_logic_vector(1 downto 0);
  end record;

  -- reg2 fields visible to hardware.
  type t_reg2_to_hw is record
    field0 : std_logic;
  end record;

  -- reg4 fields visible to hardware.
  type t_reg4_to_hw is record
    field0 : std_logic_vector(3 downto 0);
    field1 : std_logic;
  end record;

  -- reg5 fields visible to hardware.
  type t_reg5_to_hw is record
    field0 : std_logic_vector(3 downto 0);
    field1 : std_logic_vector(3 downto 0);
  end record;

  -- reg6 fields visible to hardware.
  type t_reg6_to_hw is record
    field0 : std_logic_vector(3 downto 0);
    field1 : std_logic_vector(3 downto 0);
    field2 : std_logic_vector(3 downto 0);
  end record;

  -- reg7 fields visible to hardware.
  type t_reg7_to_hw is record
    field0 : std_logic_vector(3 downto 0);
    field1 : std_logic_vector(3 downto 0);
    field2 : std_logic_vector(3 downto 0);
  end record;

  -- reg8 fields visible to hardware.
  type t_reg8_to_hw is record
    field0 : std_logic_vector(3 downto 0);
    field1 : std_logic_vector(3 downto 0);
  end record;

  -- reg9 fields visible to hardware, each paired with its software-access pulse:
  -- swmod pulses one cycle when software modifies the field; swacc pulses one
  -- cycle when software reads or writes it.
  type t_reg9_field0_out is record
    value : std_logic_vector(3 downto 0);
    swmod : std_logic;
  end record;

  type t_reg9_field1_out is record
    value : std_logic_vector(3 downto 0);
    swacc : std_logic;
  end record;

  type t_reg9_to_hw is record
    field0 : t_reg9_field0_out;
    field1 : t_reg9_field1_out;
  end record;

  -- reg10.field0: singlepulse. The value is itself the pulse (high one cycle
  -- after a software write, then self-cleared), so there is no separate strobe.
  type t_reg10_to_hw is record
    field0 : std_logic_vector(3 downto 0);
  end record;

  -- reg11.field0: enumerated value exposed to hardware as the named type.
  type t_reg11_to_hw is record
    field0 : t_reg11_field0;
  end record;

  -- Whole-module regfile -> hardware bundle: one member per register above.
  type t_prototype_to_hw is record
    reg0 : t_reg0_to_hw;
    reg2 : t_reg2_to_hw;
    reg4 : t_reg4_to_hw;
    reg5 : t_reg5_to_hw;
    reg6 : t_reg6_to_hw;
    reg7 : t_reg7_to_hw;
    reg8 : t_reg8_to_hw;
    reg9 : t_reg9_to_hw;
    reg10 : t_reg10_to_hw;
    reg11 : t_reg11_to_hw;
  end record;

  -- hardware -> regfile: per-field input records pairing each value with the
  -- modifier strobes that gate it. A field gets its own record only when it
  -- carries a strobe (we/wel/set/clr); a plain continuous input is a bare
  -- member.

  -- reg1.field0 input: hw value plus its write-enable.
  type t_reg1_field0_in is record
    value : std_logic_vector(3 downto 0);
    we    : std_logic;
  end record;

  -- reg1.field2 input: hw value plus its active-low write-enable.
  type t_reg1_field2_in is record
    value : std_logic;
    wel   : std_logic;
  end record;

  -- reg1 fields driven by hardware.
  type t_reg1_from_hw is record
    field0 : t_reg1_field0_in;
    field1 : std_logic;                       -- continuous hw write, no enable
    field2 : t_reg1_field2_in;
  end record;

  -- reg4.field0 input: hw value plus its write-enable.
  type t_reg4_field0_in is record
    value : std_logic_vector(3 downto 0);
    we    : std_logic;
  end record;

  -- reg4.field1 input: set/clear strobes only (no value; the field is hw r).
  type t_reg4_field1_in is record
    set : std_logic;                          -- force to 1
    clr : std_logic;                          -- force to 0
  end record;

  -- reg4 fields driven by hardware.
  type t_reg4_from_hw is record
    field0 : t_reg4_field0_in;
    field1 : t_reg4_field1_in;
  end record;

  -- Whole-module hardware -> regfile bundle: one member per register that has
  -- at least one hardware-writable field.
  type t_prototype_from_hw is record
    reg1 : t_reg1_from_hw;
    reg4 : t_reg4_from_hw;
  end record;

  -- True when addr falls inside this module's window. With check disabled the
  -- instantiator owns decode and every address is accepted. The compared bits
  -- are above the module window, so base must be aligned to that window (the
  -- regfile asserts this).
  function base_match(addr  : std_logic_vector(31 downto 0);
                      base  : unsigned(31 downto 0);
                      check : boolean) return boolean;

  -- True when the register-select bits match a register's byte offset.
  function sel_is(sel      : std_logic_vector(C_MODULE_ADDR_WIDTH-1 downto 0);
                  reg_addr : std_logic_vector(31 downto 0)) return boolean;

  -- True when the select bits address any mapped register. Enumerates the
  -- register offsets in one place so the decode logic need not repeat them.
  function is_mapped(sel : std_logic_vector(C_MODULE_ADDR_WIDTH-1 downto 0)) return boolean;

end package prototype_regfile_pkg;

package body prototype_regfile_pkg is

  function base_match(addr  : std_logic_vector(31 downto 0);
                      base  : unsigned(31 downto 0);
                      check : boolean) return boolean is
    constant base_slv : std_logic_vector(31 downto 0) := std_logic_vector(base);
  begin
    if not check then
      return true;
    end if;
    return addr(31 downto C_MODULE_ADDR_WIDTH)
         = base_slv(31 downto C_MODULE_ADDR_WIDTH);
  end function;

  function sel_is(sel      : std_logic_vector(C_MODULE_ADDR_WIDTH-1 downto 0);
                  reg_addr : std_logic_vector(31 downto 0)) return boolean is
  begin
    return sel = reg_addr(C_MODULE_ADDR_WIDTH-1 downto 0);
  end function;

  function is_mapped(sel : std_logic_vector(C_MODULE_ADDR_WIDTH-1 downto 0)) return boolean is
  begin
    return sel_is(sel, C_ADDR_REG0) or sel_is(sel, C_ADDR_REG1)
        or sel_is(sel, C_ADDR_REG2) or sel_is(sel, C_ADDR_REG3)
        or sel_is(sel, C_ADDR_REG4) or sel_is(sel, C_ADDR_REG5)
        or sel_is(sel, C_ADDR_REG6) or sel_is(sel, C_ADDR_REG7)
        or sel_is(sel, C_ADDR_REG8) or sel_is(sel, C_ADDR_REG9)
        or sel_is(sel, C_ADDR_REG10) or sel_is(sel, C_ADDR_REG11);
  end function;

  -- case over the literals so the encoding follows each enum's declared value,
  -- not its position; the two only coincide for in-order 0,1,2,.. enums.
  function to_slv(v : t_reg11_field0) return std_logic_vector is
    variable slv : std_logic_vector(1 downto 0);
  begin
    case v is
      when STATE0 => slv := "00";
      when STATE1 => slv := "01";
      when STATE2 => slv := "10";
      when STATE3 => slv := "11";
    end case;
    return slv;
  end function;

  -- case decode rather than to_integer(unsigned(s)) so meta-values (X/U/Z/-)
  -- give a defined result instead of a numeric_std assertion.
  function to_reg11_field0(s : std_logic_vector(1 downto 0)) return t_reg11_field0 is
  begin
    case s is
      when "00"   => return STATE0;
      when "01"   => return STATE1;
      when "10"   => return STATE2;
      when "11"   => return STATE3;
      when others => return STATE0;
    end case;
  end function;

end package body prototype_regfile_pkg;
