-- Register definitions for the regs_demo prototype module.
--
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
-- (from_hw.hwctrl.level.we, from_hw.hwctrl.gate.set, ...).
--
-- regs_demo register map (byte offsets; see local-bus-hdl.md for why the local
-- bus carries byte addresses):
--   CTRL    0x00  ENABLE [0]    sw rw  hw r
--                 MODE   [2:1]  sw rw  hw r
--   STATUS  0x04  STATE  [3:0]  sw ro  hw w   we
--                 FLAG   [4]    sw ro  hw w   (continuous)
--                 ALARM  [5]    sw ro  hw w   wel
--   CMD     0x08  TRIGGER[0]    sw wo  hw r
--   SCRATCH 0x0C  VAL    [7:0]  sw rw  hw na
--   HWCTRL  0x10  LEVEL  [3:0]  sw rw  hw rw  we
--                 GATE   [8]    sw rw  hw r   hwset, hwclr
library ieee;
use ieee.std_logic_1164.all;
use ieee.numeric_std.all;

use work.localbus_pkg.all;

package regs_demo_regfile_pkg is

  constant C_ADDR_CTRL    : std_logic_vector(31 downto 0) := 32x"00";
  constant C_ADDR_STATUS  : std_logic_vector(31 downto 0) := 32x"04";
  constant C_ADDR_CMD     : std_logic_vector(31 downto 0) := 32x"08";
  constant C_ADDR_SCRATCH : std_logic_vector(31 downto 0) := 32x"0C";
  constant C_ADDR_HWCTRL  : std_logic_vector(31 downto 0) := 32x"10";

  -- Width of the local register-select field (covers offsets 0x00..0x10).
  constant C_MODULE_ADDR_WIDTH : natural := 5;

  -- Internal storage, grouped per register. One member per field that holds
  -- state (every software- or hardware-writable field). One record per
  -- register, each member a field.

  -- Stored fields of CTRL.
  type t_ctrl_regs is record
    enable : std_logic;                      -- CTRL.ENABLE
    mode   : std_logic_vector(1 downto 0);   -- CTRL.MODE
  end record;

  -- Stored fields of STATUS.
  type t_status_regs is record
    state : std_logic_vector(3 downto 0);    -- STATUS.STATE
    flag  : std_logic;                       -- STATUS.FLAG
    alarm : std_logic;                       -- STATUS.ALARM
  end record;

  -- Stored fields of CMD.
  type t_cmd_regs is record
    trigger : std_logic;                     -- CMD.TRIGGER
  end record;

  -- Stored fields of SCRATCH.
  type t_scratch_regs is record
    val : std_logic_vector(7 downto 0);      -- SCRATCH.VAL
  end record;

  -- Stored fields of HWCTRL.
  type t_hwctrl_regs is record
    level : std_logic_vector(3 downto 0);    -- HWCTRL.LEVEL
    gate  : std_logic;                       -- HWCTRL.GATE
  end record;

  -- Whole-module storage: the regfile keeps this as a single signal.
  type t_regs_demo_regs is record
    ctrl    : t_ctrl_regs;
    status  : t_status_regs;
    cmd     : t_cmd_regs;
    scratch : t_scratch_regs;
    hwctrl  : t_hwctrl_regs;
  end record;

  constant C_REGS_DEMO_REGS_RESET : t_regs_demo_regs := (
    ctrl    => (enable => '0', mode => (others => '0')),
    status  => (state => (others => '0'), flag => '0', alarm => '0'),
    cmd     => (trigger => '0'),
    scratch => (val => (others => '0')),
    hwctrl  => (level => (others => '0'), gate => '0'));

  -- regfile -> hardware: only fields the hardware can read (hw r / rw). One
  -- record per register that has at least one hardware-readable field.

  -- CTRL fields visible to hardware.
  type t_ctrl_to_hw is record
    enable : std_logic;
    mode   : std_logic_vector(1 downto 0);
  end record;

  -- CMD fields visible to hardware.
  type t_cmd_to_hw is record
    trigger : std_logic;
  end record;

  -- HWCTRL fields visible to hardware.
  type t_hwctrl_to_hw is record
    level : std_logic_vector(3 downto 0);
    gate  : std_logic;
  end record;

  -- Whole-module regfile -> hardware bundle: one member per register above.
  type t_regs_demo_to_hw is record
    ctrl   : t_ctrl_to_hw;
    cmd    : t_cmd_to_hw;
    hwctrl : t_hwctrl_to_hw;
  end record;

  -- hardware -> regfile: per-field input records pairing each value with the
  -- modifier strobes that gate it. A field gets its own record only when it
  -- carries a strobe (we/wel/set/clr); a plain continuous input is a bare
  -- member.

  -- STATUS.STATE input: hw value plus its write-enable.
  type t_status_state_in is record
    value : std_logic_vector(3 downto 0);
    we    : std_logic;
  end record;

  -- STATUS.ALARM input: hw value plus its active-low write-enable.
  type t_status_alarm_in is record
    value : std_logic;
    wel   : std_logic;
  end record;

  -- STATUS fields driven by hardware.
  type t_status_from_hw is record
    state : t_status_state_in;
    flag  : std_logic;                        -- continuous hw write, no enable
    alarm : t_status_alarm_in;
  end record;

  -- HWCTRL.LEVEL input: hw value plus its write-enable.
  type t_hwctrl_level_in is record
    value : std_logic_vector(3 downto 0);
    we    : std_logic;
  end record;

  -- HWCTRL.GATE input: set/clear strobes only (no value; the field is hw r).
  type t_hwctrl_gate_in is record
    set : std_logic;                          -- force to 1
    clr : std_logic;                          -- force to 0
  end record;

  -- HWCTRL fields driven by hardware.
  type t_hwctrl_from_hw is record
    level : t_hwctrl_level_in;
    gate  : t_hwctrl_gate_in;
  end record;

  -- Whole-module hardware -> regfile bundle: one member per register that has
  -- at least one hardware-writable field.
  type t_regs_demo_from_hw is record
    status : t_status_from_hw;
    hwctrl : t_hwctrl_from_hw;
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
