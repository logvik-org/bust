library ieee;
use ieee.std_logic_1164.all;
use ieee.numeric_std.all;

-- User Libraries Start

-- User Libraries End

use work.example_ipbus_pif_pkg.all;

library ipbus;
use ipbus.ipbus.all;

entity example_ipbus is

  generic (
    -- User Generics Start

    -- User Generics End
    -- IPBUS Bus Interface Generics
    g_ipb_baseaddr        : std_logic_vector(31 downto 0) := (others => '0'));
  port (
    -- User Ports Start

    -- User Ports End
    -- IPBUS Bus Interface Ports
    ipb_clk      : in  std_logic;
    ipb_reset    : in  std_logic;
    ipb_in       : in  ipb_wbus;
    ipb_out      : out ipb_rbus
    );

end entity example_ipbus;

architecture behavior of example_ipbus is

  -- User Architecture Start

  -- User Architecture End

  -- IPBUS output signal for user readback
  signal ipb_out_i : ipb_rbus;
  -- Register Signals
  signal ipb_rw_regs    : t_example_ipbus_rw_regs    := c_example_ipbus_rw_regs;
  signal ipb_ro_regs    : t_example_ipbus_ro_regs    := c_example_ipbus_ro_regs;
  signal ipb_pulse_regs : t_example_ipbus_pulse_regs := c_example_ipbus_pulse_regs;

begin

  -- User Logic Start

  -- User Logic End

  ipb_out <= ipb_out_i;

  i_example_ipbus_ipb_pif : entity work.example_ipbus_ipb_pif
    generic map (
      g_ipb_baseaddr      => g_ipb_baseaddr)
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