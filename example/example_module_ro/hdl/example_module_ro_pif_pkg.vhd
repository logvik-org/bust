library ieee;
use ieee.std_logic_1164.all;
use ieee.numeric_std.all;

package example_module_ro_pif_pkg is

  constant C_EXAMPLE_MODULE_RO_ADDR_WIDTH : natural := 32;
  constant C_EXAMPLE_MODULE_RO_DATA_WIDTH : natural := 32;
  
  subtype t_example_module_ro_addr is std_logic_vector(C_EXAMPLE_MODULE_RO_ADDR_WIDTH-1 downto 0);
  subtype t_example_module_ro_data is std_logic_vector(C_EXAMPLE_MODULE_RO_DATA_WIDTH-1 downto 0);
  
  constant C_ADDR_REG0 : t_example_module_ro_addr := 32X"0";
  constant C_ADDR_REG1 : t_example_module_ro_addr := 32X"4";
  constant C_ADDR_REG2 : t_example_module_ro_addr := 32X"8";
  constant C_ADDR_REG3 : t_example_module_ro_addr := 32X"C";
  
  -- RO Register Record Definitions
  
  type t_example_module_ro_ro_reg3 is record
    field0 : std_logic;
    field1 : std_logic_vector(18 downto 0);
    field2 : std_logic;
    field3 : std_logic_vector(2 downto 0);
  end record;
  
  type t_example_module_ro_ro_regs is record
    reg0 : std_logic;
    reg1 : std_logic_vector(13 downto 0);
    reg2 : t_example_module_ro_data;
    reg3 : t_example_module_ro_ro_reg3;
  end record;

  -- RO Register Reset Value Constant
  
  constant c_example_module_ro_ro_regs : t_example_module_ro_ro_regs := (
    reg0 => '0',
    reg1 => (others => '0'),
    reg2 => (others => '0'),
    reg3 => (
      field0 => '0',
      field1 => (others => '0'),
      field2 => '0',
      field3 => (others => '0')));

end package example_module_ro_pif_pkg;