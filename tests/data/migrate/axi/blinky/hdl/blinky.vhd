library ieee;
use ieee.std_logic_1164.all;
use ieee.numeric_std.all;

-- User Libraries Start

-- User Libraries End

library bust;
use bust.axi_pkg.all;
use work.blinky_pif_pkg.all;

entity blinky is

  generic (
    -- User Generics Start
    g_blink_bits : natural := 4;
    -- User Generics End
    -- AXI Bus Interface Generics
    g_axi_baseaddr        : std_logic_vector(31 downto 0) := (others => '0');
    g_check_baseaddr      : boolean := true;
    g_module_addr_width   : integer := 0
    );
  port (
    -- User Ports Start
    led : out std_logic;
    -- User Ports End
    -- AXI Bus Interface Ports
    axi_clk      : in  std_logic;
    axi_areset_n : in  std_logic;
    axi_in       : in  t_axi_mosi;
    axi_out      : out t_axi_miso
    );

end entity blinky;

architecture behavior of blinky is

  -- User Architecture Start
  signal counter : unsigned(15 downto 0);
  -- User Architecture End

  -- AXI output signal for user readback
  signal axi_out_i : t_axi_miso;
  -- Register Signals
  signal axi_rw_regs    : t_blinky_rw_regs    := c_blinky_rw_regs;
  signal axi_ro_regs    : t_blinky_ro_regs    := c_blinky_ro_regs;
  signal axi_pulse_regs : t_blinky_pulse_regs := c_blinky_pulse_regs;

begin

  -- User Logic Start
  p_count : process (axi_clk)
  begin
    if rising_edge(axi_clk) then
      if axi_areset_n = '0' or axi_pulse_regs.clear = '1' then
        counter <= (others => '0');
      elsif axi_rw_regs.ctrl.enable = '1' then
        counter <= counter + unsigned(axi_rw_regs.ctrl.rate);
      end if;
    end if;
  end process p_count;

  axi_ro_regs.count <= std_logic_vector(counter);
  led <= counter(g_blink_bits - 1);
  -- User Logic End

  axi_out <= axi_out_i;

  i_blinky_axi_pif : entity work.blinky_axi_pif
    generic map (
      g_axi_baseaddr      => g_axi_baseaddr,
      g_check_baseaddr    => g_check_baseaddr,
      g_module_addr_width => g_module_addr_width)
    port map (
      axi_rw_regs         => axi_rw_regs,
      axi_ro_regs         => axi_ro_regs,
      axi_pulse_regs      => axi_pulse_regs,
      clk                 => axi_clk,
      areset_n            => axi_areset_n,
      awaddr              => axi_in.awaddr(C_BLINKY_ADDR_WIDTH-1 downto 0),
      awvalid             => axi_in.awvalid,
      awready             => axi_out_i.awready,
      wdata               => axi_in.wdata(C_BLINKY_DATA_WIDTH-1 downto 0),
      wvalid              => axi_in.wvalid,
      wready              => axi_out_i.wready,
      bresp               => axi_out_i.bresp,
      bvalid              => axi_out_i.bvalid,
      bready              => axi_in.bready,
      araddr              => axi_in.araddr(C_BLINKY_ADDR_WIDTH-1 downto 0),
      arvalid             => axi_in.arvalid,
      arready             => axi_out_i.arready,
      rdata               => axi_out_i.rdata(C_BLINKY_DATA_WIDTH-1 downto 0),
      rresp               => axi_out_i.rresp,
      rvalid              => axi_out_i.rvalid,
      rready              => axi_in.rready
      );

end architecture behavior;
