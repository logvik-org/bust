library ieee;
use ieee.std_logic_1164.all;
use ieee.numeric_std.all;


package example_module_pif_pkg is

  constant C_EXAMPLE_MODULE_ADDR_WIDTH : natural := 32;
  constant C_EXAMPLE_MODULE_DATA_WIDTH : natural := 32;

  subtype t_example_module_addr is std_logic_vector(C_EXAMPLE_MODULE_ADDR_WIDTH-1 downto 0);
  subtype t_example_module_data is std_logic_vector(C_EXAMPLE_MODULE_DATA_WIDTH-1 downto 0);

  constant C_ADDR_REG0 : t_example_module_addr := 32X"0";
  constant C_ADDR_REG1 : t_example_module_addr := 32X"4";
  constant C_ADDR_REG2 : t_example_module_addr := 32X"8";
  constant C_ADDR_REG3 : t_example_module_addr := 32X"C";
  constant C_ADDR_REG4 : t_example_module_addr := 32X"10";
  constant C_ADDR_REG5 : t_example_module_addr := 32X"14";
  constant C_ADDR_REG6 : t_example_module_addr := 32X"18";
  constant C_ADDR_REG7 : t_example_module_addr := 32X"1C";
  constant C_ADDR_REG8 : t_example_module_addr := 32X"20";
  constant C_ADDR_REG9 : t_example_module_addr := 32X"24";
  constant C_ADDR_REG10 : t_example_module_addr := 32X"28";
  constant C_ADDR_REG11 : t_example_module_addr := 32X"2C";

  -- RW Register Record Definitions

  type t_example_module_rw_reg7 is record
    field0 : std_logic;
    field1 : std_logic_vector(3 downto 0);
    field2 : std_logic;
    field3 : std_logic_vector(14 downto 0);
  end record;

  type t_example_module_rw_regs is record
    reg0 : std_logic;
    reg1 : std_logic;
    reg3 : std_logic_vector(7 downto 0);
    reg5 : t_example_module_data;
    reg7 : t_example_module_rw_reg7;
  end record;

  -- RW Register Reset Value Constant

  constant c_example_module_rw_regs : t_example_module_rw_regs := (
    reg0 => '0',
    reg1 => '1',
    reg3 => 8X"3",
    reg5 => 32X"FFFFFFFF",
    reg7 => (
      field0 => '1',
      field1 => 4X"B",
      field2 => '0',
      field3 => 15X"2B"));

  -- RO Register Record Definitions

  type t_example_module_ro_reg8 is record
    field0 : std_logic;
    field1 : std_logic_vector(18 downto 0);
    field2 : std_logic;
    field3 : std_logic_vector(2 downto 0);
  end record;

  type t_example_module_ro_regs is record
    reg2 : std_logic;
    reg4 : std_logic_vector(13 downto 0);
    reg6 : t_example_module_data;
    reg8 : t_example_module_ro_reg8;
  end record;

  -- RO Register Reset Value Constant

  constant c_example_module_ro_regs : t_example_module_ro_regs := (
    reg2 => '0',
    reg4 => (others => '0'),
    reg6 => (others => '0'),
    reg8 => (
      field0 => '0',
      field1 => (others => '0'),
      field2 => '0',
      field3 => (others => '0')));
  -- PULSE Register Record Definitions

  type t_example_module_pulse_reg11 is record
    field0 : std_logic_vector(14 downto 0);
    field1 : std_logic;
  end record;

  type t_example_module_pulse_regs is record
    reg9 : std_logic;
    reg10 : std_logic_vector(3 downto 0);
    reg11 : t_example_module_pulse_reg11;
  end record;

  -- PULSE Register Reset Value Constant

  constant c_example_module_pulse_regs : t_example_module_pulse_regs := (
    reg9 => '1',
    reg10 => 4X"A",
    reg11 => (
      field0 => 15X"3",
      field1 => '0'));


end package example_module_pif_pkg;