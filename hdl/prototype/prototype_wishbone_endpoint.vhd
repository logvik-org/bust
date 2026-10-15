-- Wishbone (B4 classic) wrapper prototype for the local-bus register file.
-- One of the protocol wrappers in the target architecture:
--   <bus> wrapper -> local bus (t_lb_m2s / t_lb_s2m) -> regfile
-- Hand-written reference HDL (not generator output). UVVM ships no Wishbone VIP,
-- so it is verified with a small hand-written classic-cycle Wishbone master BFM
-- in the testbench, proving the Wishbone-to-local-bus bridge before the
-- generator emits it.
--
-- Classic Wishbone is a single-beat, hold-until-ack protocol, so the bridge is
-- pure combinational glue: a qualified cycle (cyc_i and stb_i) drives one
-- local-bus transaction (we_i selects write vs read) and the regfile's response
-- is forwarded straight back as a one-cycle ack_o/err_o beat. The wrapper adds no
-- register stage, so the regfile's single registered cycle is the whole latency:
-- ack_o/err_o assert one clock after the qualified cycle. The regfile's response
-- guard (it acks a held cycle only once) provides termination, so no FSM is
-- needed. Wishbone has a native err_o line, so a regfile decode error maps to
-- err_o; dat_o is still forced to 0 on err so reads of invalid addresses stay
-- deterministic. Wishbone's sync active-high reset passes straight to the
-- regfile, and the master drives a byte address mapped directly onto the local
-- bus.
library ieee;
use ieee.std_logic_1164.all;
use ieee.numeric_std.all;

use work.prototype_localbus_pkg.all;
use work.prototype_regfile_pkg.all;

entity prototype_wishbone_endpoint is
  generic (
    G_BASE_ADDRESS       : unsigned(31 downto 0) := x"00000000";
    G_CHECK_BASE_ADDRESS : boolean               := true
  );
  port (
    clk_i   : in  std_logic;
    rst_i   : in  std_logic;

    -- Wishbone B4 classic subordinate interface
    cyc_i   : in  std_logic;
    stb_i   : in  std_logic;
    we_i    : in  std_logic;
    adr_i   : in  std_logic_vector(31 downto 0);
    dat_i   : in  std_logic_vector(31 downto 0);
    dat_o   : out std_logic_vector(31 downto 0);
    ack_o   : out std_logic;
    err_o   : out std_logic;

    -- hardware side of the register file
    to_hw   : out t_prototype_to_hw;
    from_hw : in  t_prototype_from_hw
  );
end entity prototype_wishbone_endpoint;

architecture rtl of prototype_wishbone_endpoint is

  signal m2s : t_lb_m2s;
  signal s2m : t_lb_s2m;

  signal qualified : std_logic;

begin

  i_regfile : entity work.prototype_regfile
    generic map (
      G_BASE_ADDRESS       => G_BASE_ADDRESS,
      G_CHECK_BASE_ADDRESS => G_CHECK_BASE_ADDRESS,
      G_RESET_ACTIVE_LOW   => false)      -- Wishbone reset is sync active-high
    port map (
      clk     => clk_i,
      reset   => rst_i,
      lb_m2s  => m2s,
      lb_s2m  => s2m,
      to_hw   => to_hw,
      from_hw => from_hw);

  qualified <= cyc_i and stb_i;

  m2s.address <= adr_i;
  m2s.wdata   <= dat_i;
  m2s.wen     <= qualified and we_i;
  m2s.ren     <= qualified and not we_i;

  ack_o <= s2m.ack;
  err_o <= s2m.err;
  dat_o <= (others => '0') when s2m.err = '1' else s2m.rdata;

end architecture rtl;
