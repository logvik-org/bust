library ieee;
use ieee.std_logic_1164.all;
use ieee.numeric_std.all;

-- User Libraries Start

-- User Libraries End

library bust;
use bust.axi_pkg.all;
use work.example_axi_pif_pkg.all;

entity example_axi is

  generic (
    -- User Generics Start

    -- User Generics End
    -- AXI Bus Interface Generics
    g_axi_baseaddr        : std_logic_vector(31 downto 0) := (others => '0'));
  port (
    -- User Ports Start

    -- User Ports End
    -- AXI Bus Interface Ports
    axi_clk      : in  std_logic;
    axi_areset_n : in  std_logic;
    axi_in       : in  t_axi_mosi;
    axi_out      : out t_axi_miso
    );

end entity example_axi;

architecture behavior of example_axi is

  -- User Architecture Start

  -- User Architecture End

  -- AXI output signal for user readback
  signal axi_out_i : t_axi_miso;
  -- Register Signals
  signal axi_rw_regs    : t_example_axi_rw_regs    := c_example_axi_rw_regs;
  signal axi_ro_regs    : t_example_axi_ro_regs    := c_example_axi_ro_regs;
  signal axi_pulse_regs : t_example_axi_pulse_regs := c_example_axi_pulse_regs;

begin

  -- User Logic Start

  -- User Logic End

  axi_out <= axi_out_i;

  i_example_axi_axi_pif : entity work.example_axi_axi_pif
    generic map (
      g_axi_baseaddr      => g_axi_baseaddr)
    port map (
      axi_rw_regs         => axi_rw_regs,
      axi_ro_regs         => axi_ro_regs,
      axi_pulse_regs      => axi_pulse_regs,
      clk                 => axi_clk,
      areset_n            => axi_areset_n,
      awaddr              => axi_in.awaddr(C_EXAMPLE_AXI_ADDR_WIDTH-1 downto 0),
      awvalid             => axi_in.awvalid,
      awready             => axi_out_i.awready,
      wdata               => axi_in.wdata(C_EXAMPLE_AXI_DATA_WIDTH-1 downto 0),
      wvalid              => axi_in.wvalid,
      wready              => axi_out_i.wready,
      bresp               => axi_out_i.bresp,
      bvalid              => axi_out_i.bvalid,
      bready              => axi_in.bready,
      araddr              => axi_in.araddr(C_EXAMPLE_AXI_ADDR_WIDTH-1 downto 0),
      arvalid             => axi_in.arvalid,
      arready             => axi_out_i.arready,
      rdata               => axi_out_i.rdata(C_EXAMPLE_AXI_DATA_WIDTH-1 downto 0),
      rresp               => axi_out_i.rresp,
      rvalid              => axi_out_i.rvalid,
      rready              => axi_in.rready
      );

end architecture behavior;
