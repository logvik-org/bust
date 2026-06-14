-- Register definitions for the regs_demo prototype module.
--
-- The demo uses deliberately generic names (reg0..reg4, field0..) so the record
-- structure and naming scheme can be reviewed without semantic distraction.
-- The types here model what the generator will emit per module. Registers and
-- fields are expressed as nested records (regs.<reg>.<field>) so a module with
-- many registers stays one record signal instead of a flat list of signals,
-- and so the hardware sees each field by name with its modifiers attached.
--
-- Three record families, all nested register -> field:
--   t_regs_demo_regs      internal storage (one per field that holds state)
--   t_regs_demo_to_hw     regfile -> hardware (hw r / rw field values)
--   t_regs_demo_from_hw   hardware -> regfile (hw w / rw values + modifiers)
--
-- Field-level input records carry the value together with their modifier
-- strobes, so a field's write-enable or set/clear lives next to its value
-- (from_hw.reg4.field0.we, from_hw.reg4.field1.set, ...).
--
-- regs_demo register map (byte offsets; see local-bus-hdl.md for why the local
-- bus carries byte addresses):
--   reg0  0x00  field0 [0]    sw rw  hw r
--               field1 [2:1]  sw rw  hw r
--   reg1  0x04  field0 [3:0]  sw ro  hw w   we
--               field1 [4]    sw ro  hw w   (continuous)
--               field2 [5]    sw ro  hw w   wel
--   reg2  0x08  field0 [0]    sw wo  hw r
--   reg3  0x0C  field0 [7:0]  sw rw  hw na
--   reg4  0x10  field0 [3:0]  sw rw  hw rw  we
--               field1 [8]    sw rw  hw r   hwset, hwclr
library ieee;
use ieee.std_logic_1164.all;
use ieee.numeric_std.all;

use work.localbus_pkg.all;

package regs_demo_regfile_pkg is

  constant C_ADDR_REG0 : std_logic_vector(31 downto 0) := 32x"00";
  constant C_ADDR_REG1 : std_logic_vector(31 downto 0) := 32x"04";
  constant C_ADDR_REG2 : std_logic_vector(31 downto 0) := 32x"08";
  constant C_ADDR_REG3 : std_logic_vector(31 downto 0) := 32x"0C";
  constant C_ADDR_REG4 : std_logic_vector(31 downto 0) := 32x"10";

  -- Width of the local register-select field (covers offsets 0x00..0x10).
  constant C_MODULE_ADDR_WIDTH : natural := 5;

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

  -- Whole-module storage: the regfile keeps this as a single signal.
  type t_regs_demo_regs is record
    reg0 : t_reg0_regs;
    reg1 : t_reg1_regs;
    reg2 : t_reg2_regs;
    reg3 : t_reg3_regs;
    reg4 : t_reg4_regs;
  end record;

  constant C_REGS_DEMO_REGS_RESET : t_regs_demo_regs := (
    reg0 => (field0 => '0', field1 => (others => '0')),
    reg1 => (field0 => (others => '0'), field1 => '0', field2 => '0'),
    reg2 => (field0 => '0'),
    reg3 => (field0 => (others => '0')),
    reg4 => (field0 => (others => '0'), field1 => '0'));

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

  -- Whole-module regfile -> hardware bundle: one member per register above.
  type t_regs_demo_to_hw is record
    reg0 : t_reg0_to_hw;
    reg2 : t_reg2_to_hw;
    reg4 : t_reg4_to_hw;
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
  type t_regs_demo_from_hw is record
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

end package regs_demo_regfile_pkg;

package body regs_demo_regfile_pkg is

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

end package body regs_demo_regfile_pkg;
