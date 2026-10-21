library ieee;
use ieee.std_logic_1164.all;
use ieee.numeric_std.all;

-- User Libraries Start

-- User Libraries End

library ipbus;
use ipbus.ipbus.all;
use work.blinky_pif_pkg.all;

entity blinky is

  generic (
    -- User Generics Start
    g_blink_bits : natural := 4;
    -- User Generics End
    -- IPBUS Bus Interface Generics
    g_ipb_baseaddr        : std_logic_vector(31 downto 0) := (others => '0');
    g_check_baseaddr      : boolean := true;
    g_module_addr_width   : integer := 0
    );
  port (
    -- User Ports Start
    led : out std_logic;
    -- User Ports End
    -- IPBUS Bus Interface Ports
    ipb_clk      : in  std_logic;
    ipb_reset    : in  std_logic;
    ipb_in       : in  ipb_wbus;
    ipb_out      : out ipb_rbus
    );

end entity blinky;

architecture behavior of blinky is

  -- User Architecture Start
  signal counter : unsigned(15 downto 0);
  -- User Architecture End

  -- IPBUS output signal for user readback
  signal ipb_out_i : ipb_rbus;
  -- Register Signals
  signal ipb_rw_regs    : t_blinky_rw_regs    := c_blinky_rw_regs;
  signal ipb_ro_regs    : t_blinky_ro_regs    := c_blinky_ro_regs;
  signal ipb_pulse_regs : t_blinky_pulse_regs := c_blinky_pulse_regs;

begin

  -- User Logic Start
  p_count : process (ipb_clk)
  begin
    if rising_edge(ipb_clk) then
      if ipb_reset = '1' or ipb_pulse_regs.clear = '1' then
        counter <= (others => '0');
      elsif ipb_rw_regs.ctrl.enable = '1' then
        counter <= counter + unsigned(ipb_rw_regs.ctrl.rate);
      end if;
    end if;
  end process p_count;

  ipb_ro_regs.count <= std_logic_vector(counter);
  led <= counter(g_blink_bits - 1);
  -- User Logic End

  ipb_out <= ipb_out_i;

  i_blinky_ipb_pif : entity work.blinky_ipb_pif
    generic map (
      g_ipb_baseaddr      => g_ipb_baseaddr,
      g_check_baseaddr    => g_check_baseaddr,
      g_module_addr_width => g_module_addr_width)
    port map (
      ipb_rw_regs         => ipb_rw_regs,
      ipb_ro_regs         => ipb_ro_regs,
      ipb_pulse_regs      => ipb_pulse_regs,
      clk                 => ipb_clk,
      reset               => ipb_reset,
      ipb_in              => ipb_in,
      ipb_out             => ipb_out_i
      );

end architecture behavior;
