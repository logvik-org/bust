library ieee;
use ieee.std_logic_1164.all;
use ieee.numeric_std.all;

package example_module_rw_pif_pkg is

  constant C_EXAMPLE_MODULE_RW_ADDR_WIDTH : natural := 32;
  constant C_EXAMPLE_MODULE_RW_DATA_WIDTH : natural := 32;
  
  subtype t_example_module_rw_addr is std_logic_vector(C_EXAMPLE_MODULE_RW_ADDR_WIDTH-1 downto 0);
  subtype t_example_module_rw_data is std_logic_vector(C_EXAMPLE_MODULE_RW_DATA_WIDTH-1 downto 0);
  
  constant C_ADDR_REG0 : t_example_module_rw_addr := 32X"0";
  constant C_ADDR_REG1 : t_example_module_rw_addr := 32X"4";
  constant C_ADDR_REG2 : t_example_module_rw_addr := 32X"C";
  constant C_ADDR_REG3 : t_example_module_rw_addr := 32X"14";
  constant C_ADDR_REG4 : t_example_module_rw_addr := 32X"1C";
  
  -- RW Register Record Definitions
  
  type t_example_module_rw_rw_reg4 is record
    field0 : std_logic;
    field1 : std_logic_vector(3 downto 0);
    field2 : std_logic;
    field3 : std_logic_vector(14 downto 0);
  end record;
  
  type t_example_module_rw_rw_regs is record
    reg0 : std_logic;
    reg1 : std_logic;
    reg2 : std_logic_vector(7 downto 0);
    reg3 : t_example_module_rw_data;
    reg4 : t_example_module_rw_rw_reg4;
  end record;

  -- RW Register Reset Value Constant
  
  constant c_example_module_rw_rw_regs : t_example_module_rw_rw_regs := (
    reg0 => '0',
    reg1 => '1',
    reg2 => 8X"3",
    reg3 => 32X"FFFFFFFF",
    reg4 => (
      field0 => '1',
      field1 => 4X"B",
      field2 => '0',
      field3 => 15X"2B"));


end package example_module_rw_pif_pkg;