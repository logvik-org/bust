-- APB (AMBA APB) wrapper prototype for the local-bus register file.
-- One of the protocol wrappers in the target architecture:
--   <bus> wrapper -> local bus (t_lb_m2s / t_lb_s2m) -> regfile
-- Hand-written reference HDL (not generator output). UVVM ships no APB VIP, so it
-- is verified with a small hand-written APB master BFM in the testbench, proving
-- the APB-to-local-bus bridge before the generator emits it.
--
-- APB is a two-phase protocol: a SETUP cycle (psel asserted, penable low) is
-- followed by ACCESS cycles (psel and penable both high) until the slave raises
-- pready. The bridge drives the local-bus request from the SETUP cycle itself and
-- holds it (busy) until the regfile answers, so the regfile's single registered
-- cycle surfaces as pready in the first ACCESS cycle: a zero-wait-state transfer
-- (the APB two-cycle minimum). The response (pready/prdata/pslverr) is forwarded
-- combinationally from the local bus, adding no register stage of its own.
-- Holding the request until ack honours the local-bus hold-until-ack contract,
-- so a variable-latency register simply stretches the ACCESS phase with wait
-- states. The busy flag keeps the request asserted for exactly one transaction
-- (the regfile's own response guard blocks a re-service in the ack cycle), and it
-- clears on ack so a back-to-back transfer starts cleanly at its SETUP cycle. APB
-- has a native pslverr, so a regfile decode error maps to pslverr (prdata still
-- forced to 0). APB's reset (presetn) is active-low and async, handed to the
-- regfile via G_RESET_ACTIVE_LOW; the master drives a byte address mapped
-- directly onto the local bus.
library ieee;
use ieee.std_logic_1164.all;
use ieee.numeric_std.all;

use work.prototype_localbus_pkg.all;
use work.prototype_regfile_pkg.all;

entity prototype_apb_endpoint is
  generic (
    G_BASE_ADDRESS       : unsigned(31 downto 0) := x"00000000";
    G_CHECK_BASE_ADDRESS : boolean               := true;
    G_MODULE_ADDR_WIDTH  : natural               := C_MODULE_ADDR_WIDTH
  );
  port (
    pclk    : in  std_logic;
    presetn : in  std_logic;

    -- APB subordinate interface
    psel    : in  std_logic;
    penable : in  std_logic;
    pwrite  : in  std_logic;
    paddr   : in  std_logic_vector(31 downto 0);
    pwdata  : in  std_logic_vector(31 downto 0);
    prdata  : out std_logic_vector(31 downto 0);
    pready  : out std_logic;
    pslverr : out std_logic;

    -- hardware side of the register file
    to_hw   : out t_prototype_to_hw;
    from_hw : in  t_prototype_from_hw
  );
end entity prototype_apb_endpoint;

architecture rtl of prototype_apb_endpoint is

  signal m2s : t_lb_m2s;
  signal s2m : t_lb_s2m;

  -- Request held from the SETUP cycle until the regfile answers, so the local-bus
  -- hold-until-ack contract holds even for a variable-latency register.
  signal busy       : std_logic := '0';
  signal req_active : std_logic;

begin

  i_regfile : entity work.prototype_regfile
    generic map (
      G_BASE_ADDRESS       => G_BASE_ADDRESS,
      G_CHECK_BASE_ADDRESS => G_CHECK_BASE_ADDRESS,
      G_MODULE_ADDR_WIDTH  => G_MODULE_ADDR_WIDTH,
      G_RESET_ACTIVE_LOW   => true)       -- APB presetn is active-low
    port map (
      clk     => pclk,
      reset   => presetn,
      lb_m2s  => m2s,
      lb_s2m  => s2m,
      to_hw   => to_hw,
      from_hw => from_hw);

  -- Active from the SETUP cycle (psel high, penable low) and held while busy.
  req_active <= '1' when (psel = '1' and penable = '0') or busy = '1' else '0';

  m2s.address <= paddr;
  m2s.wdata   <= pwdata;
  m2s.wen     <= req_active and pwrite;
  m2s.ren     <= req_active and not pwrite;

  p_busy : process (pclk, presetn) is
  begin
    if presetn = '0' then
      busy <= '0';
    elsif rising_edge(pclk) then
      if psel = '1' and penable = '0' then
        busy <= '1';                      -- latch the in-flight transaction at SETUP
      elsif s2m.ack = '1' or s2m.err = '1' then
        busy <= '0';                      -- release once the regfile answers
      end if;
    end if;
  end process p_busy;

  pready  <= s2m.ack or s2m.err;
  pslverr <= s2m.err;
  prdata  <= (others => '0') when s2m.err = '1' else s2m.rdata;

end architecture rtl;
