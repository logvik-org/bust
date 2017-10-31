library ieee;
use ieee.std_logic_1164.all;
use ieee.numeric_std.all;

use work.axi_pkg.all;
use work.module_name_pkg.all;

entity module_name is

  port (

    -- AXI Bus Interface
    axi_clk      : in std_logic;
    axi_areset_n : std_logic;
    axi_in       : t_axi_interconnect_to_slave;
    axi_out      : t_axi_slave_to_interconnect
    );

end entity module_name;

architecture behavior of module_name is

  signal axi_rw_regs : t_module_name_rw_regs;
  signal axi_ro_regs : t_module_name_ro_regs := (
    reg3 => (others => '0'),
    reg4 => (
      test => (others => '0'),
      test2 => '0'
    ));

begin

  i_module_name_axi_pif : entity work.module_name_axi_pif
    port map (
      axi_ro_regs => axi_ro_regs,
      axi_rw_regs => axi_rw_regs,
      clk         => axi_clk,
      areset_n    => axi_areset_n,
      awaddr      => axi_awaddr(C_MODULE_NAME_ADDR_WIDTH-1 downto 0),
      awvalid     => axi_awvalid,
      awready     => axi_awready,
      wdata       => axi_wdata(C_MODULE_NAME_DATA_WIDTH-1 downto 0),
      wvalid      => axi_wvalid,
      wready      => axi_wready,
      bresp       => axi_bresp,
      bvalid      => axi_bvalid,
      bready      => axi_bready,
      araddr      => axi_araddr(C_MODULE_NAME_ADDR_WIDTH-1 downto 0),
      arvalid     => axi_arvalid,
      arready     => axi_arready,
      rdata       => axi_rdata(C_MODULE_NAME_DATA_WIDTH-1 downto 0),
      rresp       => axi_rresp,
      rvalid      => axi_rvalid,
      rready      => axi_rready
      );
  -- Set unused bus data bits to zero
  axi_out.rdata(C_AXI_DATA_WIDTH-1 downto C_MODULE_NAME_DATA_WIDTH) <= (others => '0');

end architecture behavior;