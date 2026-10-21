-- SBI (Simple Bus Interface) wrapper prototype for the local-bus register file.
-- One of the protocol wrappers in the target architecture:
--   <bus> wrapper -> local bus (t_lb_m2s / t_lb_s2m) -> regfile
-- Hand-written reference HDL (not generator output), verified with the stock
-- Bitvis SBI VIP, proving the SBI-to-local-bus bridge before the generator
-- emits it.
--
-- SBI is a single-beat protocol with an explicit ready handshake: the master
-- raises cs together with wena or rena and holds the request until the slave
-- asserts ready. The bridge is pure combinational glue: the request drives one
-- local-bus transaction and the regfile's response is forwarded straight back as
-- a one-cycle ready beat. The wrapper adds no register stage, so the regfile's
-- single registered cycle is the whole latency: ready asserts one clock after the
-- request. The regfile's response guard (it acks a held request only once)
-- provides transaction separation, so no FSM is needed and the sub-cycle
-- inter-access cs gap never has to be sampled. ack and err alike complete as one
-- ready beat (SBI has no error line); on a decode error rdata is forced to 0 so
-- reads of invalid addresses stay deterministic, matching the AXI endpoint. SBI
-- carries no reset of its own, so a sync active-high reset passes straight to the
-- regfile. The master drives a byte address, mapped directly onto the local bus.
library ieee;
use ieee.std_logic_1164.all;
use ieee.numeric_std.all;

use work.prototype_localbus_pkg.all;
use work.prototype_regfile_pkg.all;

entity prototype_sbi_endpoint is
  generic (
    G_BASE_ADDRESS       : unsigned(31 downto 0) := x"00000000";
    G_CHECK_BASE_ADDRESS : boolean               := true;
    G_MODULE_ADDR_WIDTH  : natural               := C_MODULE_ADDR_WIDTH
  );
  port (
    clk     : in  std_logic;
    reset   : in  std_logic;

    -- SBI subordinate interface
    cs      : in  std_logic;
    addr    : in  std_logic_vector(31 downto 0);
    rena    : in  std_logic;
    wena    : in  std_logic;
    wdata   : in  std_logic_vector(31 downto 0);
    ready   : out std_logic;
    rdata   : out std_logic_vector(31 downto 0);

    -- hardware side of the register file
    to_hw   : out t_prototype_to_hw;
    from_hw : in  t_prototype_from_hw
  );
end entity prototype_sbi_endpoint;

architecture rtl of prototype_sbi_endpoint is

  signal m2s : t_lb_m2s;
  signal s2m : t_lb_s2m;

begin

  i_regfile : entity work.prototype_regfile
    generic map (
      G_BASE_ADDRESS       => G_BASE_ADDRESS,
      G_CHECK_BASE_ADDRESS => G_CHECK_BASE_ADDRESS,
      G_MODULE_ADDR_WIDTH  => G_MODULE_ADDR_WIDTH,
      G_RESET_ACTIVE_LOW   => false)      -- SBI carries no reset; use sync active-high
    port map (
      clk     => clk,
      reset   => reset,
      lb_m2s  => m2s,
      lb_s2m  => s2m,
      to_hw   => to_hw,
      from_hw => from_hw);

  m2s.address <= addr;
  m2s.wdata   <= wdata;
  m2s.wen     <= cs and wena;
  m2s.ren     <= cs and rena;

  -- SBI has no error line, so ack and err both complete as a single ready beat;
  -- on a decode error rdata is forced to 0 (the regfile leaves it unchanged).
  ready <= s2m.ack or s2m.err;
  rdata <= (others => '0') when s2m.err = '1' else s2m.rdata;

end architecture rtl;
