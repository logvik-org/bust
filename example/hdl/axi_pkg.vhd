-------------------------------------------------------------------------------
--!@file        axi_pkg.vhd
--!@author      author_name
--!@brief       Package for AXI bus interface
--!
--!
-------------------------------------------------------------------------------
library ieee;
use ieee.std_logic_1164.all;

package axi_pkg is
  
  -- Slave data & addr widths
  constant C_axi_data_width : natural := 32;
  constant C_axi_addr_width : natural := 32;

  subtype t_axi_data is std_logic_vector(C_axi_data_width-1 downto 0);
  subtype t_axi_addr is std_logic_vector(C_axi_addr_width-1 downto 0);
  
 --! AXI bus record
  type t_axi_interconnect_to_slave is record
    araddr  : t_axi_addr;
    arprot  : std_logic_vector(2 downto 0);
    arvalid : std_logic;
    awaddr  : t_axi_addr;
    awprot  : std_logic_vector(2 downto 0);
    awvalid : std_logic;
    bready  : std_logic;
    rready  : std_logic;
    wdata   : t_axi_data;
    wstrb   : std_logic_vector((C_axi_data_width/8)-1 downto 0);
    wvalid  : std_logic;
  end record;

  --! AXI bus record
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
