-- Register definitions for the regs_demo prototype module.
-- Hardware-side records are split per register by direction:
--   *_to_hw   : regfile -> hardware (hw r / rw field values)
--   *_from_hw : hardware -> regfile (hw w / rw values plus we/wel/set/clr)
library ieee;
use ieee.std_logic_1164.all;

package regs_demo_regfile_pkg is

  constant C_ADDR_CTRL    : std_logic_vector(31 downto 0) := 32x"00";
  constant C_ADDR_STATUS  : std_logic_vector(31 downto 0) := 32x"04";
  constant C_ADDR_CMD     : std_logic_vector(31 downto 0) := 32x"08";
  constant C_ADDR_SCRATCH : std_logic_vector(31 downto 0) := 32x"0C";
  constant C_ADDR_HWCTRL  : std_logic_vector(31 downto 0) := 32x"10";

  -- Width of the local register-select field (covers offsets 0x00..0x10).
  constant C_MODULE_ADDR_WIDTH : natural := 5;

  type t_ctrl_to_hw is record
    enable : std_logic;
    mode   : std_logic_vector(1 downto 0);
  end record;

  type t_status_from_hw is record
    state     : std_logic_vector(3 downto 0);
    state_we  : std_logic;
    flag      : std_logic;
    alarm     : std_logic;
    alarm_wel : std_logic;
  end record;

  type t_cmd_to_hw is record
    trigger : std_logic;
  end record;

  type t_hwctrl_to_hw is record
    level : std_logic_vector(3 downto 0);
    gate  : std_logic;
  end record;

  type t_hwctrl_from_hw is record
    level    : std_logic_vector(3 downto 0);
    level_we : std_logic;
    gate_set : std_logic;
    gate_clr : std_logic;
  end record;

  type t_regs_demo_to_hw is record
    ctrl   : t_ctrl_to_hw;
    cmd    : t_cmd_to_hw;
    hwctrl : t_hwctrl_to_hw;
  end record;

  type t_regs_demo_from_hw is record
    status : t_status_from_hw;
    hwctrl : t_hwctrl_from_hw;
  end record;

end package regs_demo_regfile_pkg;
