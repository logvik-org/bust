library ieee;
use ieee.std_logic_1164.all;
use ieee.numeric_std.all;

package example_module_empty_pif_pkg is

  constant C_EXAMPLE_MODULE_EMPTY_ADDR_WIDTH : natural := 32;
  constant C_EXAMPLE_MODULE_EMPTY_DATA_WIDTH : natural := 32;
  
  subtype t_example_module_empty_addr is std_logic_vector(C_EXAMPLE_MODULE_EMPTY_ADDR_WIDTH-1 downto 0);
  subtype t_example_module_empty_data is std_logic_vector(C_EXAMPLE_MODULE_EMPTY_DATA_WIDTH-1 downto 0);
  
  

end package example_module_empty_pif_pkg;