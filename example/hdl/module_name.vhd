-------------------------------------------------------------------------------
--!@file        module_name.vhd
--!@author      author_name
--!@brief       module_name
--!
--!
-------------------------------------------------------------------------------
library ieee;
use ieee.std_logic_1164.all;
use ieee.numeric_std.all;

entity module_name is

  port (
    clk                       : in  std_logic;
    reset                     : in  std_logic;
    axi_interconnect_to_slave : in  t_axi_interconnect_to_slave;
    axi_slave_to_interconnect : out t_axi_slave_to_interconnect
    );

end entity module_name;

architecture behavior of module_name is

begin  -- architecture behavior

  module_name_axi_handler_i: entity work.module_name_axi_handler
    port map (
      axi_ro_regs => axi_ro_regs,
      axi_rw_regs => axi_rw_regs,
      clk         => clk,
      areset_n    => areset_n,
      awaddr      => awaddr,
      awvalid     => awvalid,
      awready     => awready,
      wdata       => wdata,
      wvalid      => wvalid,
      wready      => wready,
      bresp       => bresp,
      bvalid      => bvalid,
      bready      => bready,
      araddr      => araddr,
      arvalid     => arvalid,
      arready     => arready,
      rdata       => rdata,
      rresp       => rresp,
      rvalid      => rvalid,
      rready      => rready);

end architecture behavior;
