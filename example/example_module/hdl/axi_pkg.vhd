library ieee;
use ieee.std_logic_1164.all;

package axi_pkg is


  constant C_AXI_DATA_WIDTH : natural := 32;
  constant C_AXI_ADDR_WIDTH : natural := 32;
  
  subtype t_axi_data is std_logic_vector(C_AXI_DATA_WIDTH-1 downto 0);
  subtype t_axi_addr is std_logic_vector(C_AXI_ADDR_WIDTH-1 downto 0);
  
  type t_axi_interconnect_to_slave is record
    araddr  : t_axi_addr;
    arvalid : std_logic;
    awaddr  : t_axi_addr;
    awvalid : std_logic;
    bready  : std_logic;
    rready  : std_logic;
    wdata   : t_axi_data;
    wvalid  : std_logic;
  end record;

  type t_axi_slave_to_interconnect is record
    arready : std_logic;
    awready : std_logic;
    bresp   : std_logic_vector(1 downto 0);
    bvalid  : std_logic;
    rdata   : t_axi_data;
    rresp   : std_logic_vector(1 downto 0);
    rvalid  : std_logic;
    wready  : std_logic;
  end record;

end axi_pkg;