library ieee;
use ieee.std_logic_1164.all;
use ieee.numeric_std.all;

library uvvm_util;
context uvvm_util.uvvm_util_context;

library uvvm_vvc_framework;
use uvvm_vvc_framework.ti_vvc_framework_support_pkg.all;

library bitvis_vip_axilite;
use bitvis_vip_axilite.axilite_bfm_pkg.all;

use work.axi_pkg.all;

entity module_name_th is
end entity;

architecture struct of module_name_th is

  signal clk : std_logic := '0';
  signal rst : std_logic := '0';

  constant C_CLK_PERIOD : time := 10 ns;

  signal areset_n : std_logic := '1';
  signal axi_in   : t_axi_interconnect_to_slave;
  signal axi_out  : t_axi_slave_to_interconnect;

  signal araddr  : t_axi_addr;
  signal arprot  : std_logic_vector(2 downto 0);
  signal arvalid : std_logic;
  signal awaddr  : t_axi_addr;
  signal awprot  : std_logic_vector(2 downto 0);
  signal awvalid : std_logic;
  signal bready  : std_logic;
  signal rready  : std_logic;
  signal wdata   : t_axi_data;
  signal wstrb   : std_logic_vector((C_AXI_DATA_WIDTH/8)-1 downto 0);
  signal wvalid  : std_logic;

  signal arready : std_logic;
  signal awready : std_logic;
  signal bresp   : std_logic_vector(1 downto 0);
  signal bvalid  : std_logic;
  signal rdata   : t_axi_data;
  signal rresp   : std_logic_vector(1 downto 0);
  signal rvalid  : std_logic;
  signal wready  : std_logic;

begin

  clock_generator(clk, C_CLK_PERIOD);
  
  -- Toggle the reset after 10 clock periods
  p_rst : rst <= '1', '0' after 10 * C_CLK_PERIOD;

  areset_n <= not rst;

  -----------------------------------------------------------------------------
  -- Instantiate the concurrent procedure that initializes UVVM
  -----------------------------------------------------------------------------
  i_ti_uvvm_engine : entity uvvm_vvc_framework.ti_uvvm_engine;

  -----------------------------------------------------------------------------
  -- Instantiate DUT
  -----------------------------------------------------------------------------
  module_name_i : entity work.module_name
    port map (
      axi_clk      => clk,
      axi_areset_n => areset_n,
      axi_in       => axi_in,
      axi_out      => axi_out
      );

  axilite_vvc_i : entity bitvis_vip_axilite.axilite_vvc
    generic map (
      GC_ADDR_WIDTH   => C_AXI_ADDR_WIDTH,
      GC_DATA_WIDTH   => C_AXI_DATA_WIDTH,
      GC_INSTANCE_IDX => 0
      )
    port map (
      clk                                                 => clk,
      axilite_vvc_master_if.read_address_channel.araddr   => araddr,
      axilite_vvc_master_if.read_address_channel.arprot   => arprot,
      axilite_vvc_master_if.read_address_channel.arvalid  => arvalid,
      axilite_vvc_master_if.write_address_channel.awaddr  => awaddr,
      axilite_vvc_master_if.write_address_channel.awprot  => awprot,
      axilite_vvc_master_if.write_address_channel.awvalid => awvalid,
      axilite_vvc_master_if.write_response_channel.bready => bready,
      axilite_vvc_master_if.read_data_channel.rready      => rready,
      axilite_vvc_master_if.write_data_channel.wdata      => wdata,
      axilite_vvc_master_if.write_data_channel.wstrb      => wstrb,
      axilite_vvc_master_if.write_data_channel.wvalid     => wvalid,
      axilite_vvc_master_if.read_address_channel.arready  => arready,
      axilite_vvc_master_if.write_address_channel.awready => awready,
      axilite_vvc_master_if.write_response_channel.bresp  => bresp,
      axilite_vvc_master_if.write_response_channel.bvalid => bvalid,
      axilite_vvc_master_if.read_data_channel.rdata       => rdata,
      axilite_vvc_master_if.read_data_channel.rresp       => rresp,
      axilite_vvc_master_if.read_data_channel.rvalid      => rvalid,
      axilite_vvc_master_if.write_data_channel.wready     => wready
      );

  -- write address channel
  axi_in.awaddr  <= awaddr;
  axi_in.awvalid <= awvalid;
  axi_in.awprot  <= awprot;
  awready        <= axi_out.awready;

  -- write data channel
  axi_in.wdata  <= wdata;
  axi_in.wstrb  <= wstrb;
  axi_in.wvalid <= wvalid;
  wready        <= axi_out.wready;

  -- write response channel
  axi_in.bready <= bready;
  bresp         <= axi_out.bresp;
  bvalid        <= axi_out.bvalid;

  -- read address channel
  axi_in.araddr  <= araddr;
  axi_in.arvalid <= arvalid;
  axi_in.arprot  <= arprot;
  arready        <= axi_out.arready;

  -- read data channel
  axi_in.rready <= rready;
  rdata         <= axi_out.rdata;
  rresp         <= axi_out.rresp;
  rvalid        <= axi_out.rvalid;


end architecture;

