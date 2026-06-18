-- IPBus wrapper prototype for the local-bus register file.
-- One of the protocol wrappers in the target architecture:
--   <bus> wrapper -> local bus (t_lb_m2s / t_lb_s2m) -> regfile
-- Hand-written reference HDL (not generator output), verified with the stock
-- vip_ipbus VIP, proving the IPBus-to-local-bus bridge before the generator
-- emits it.
--
-- IPBus is itself a single-beat, hold-until-ack protocol, so the bridge is pure
-- combinational glue: a strobe drives one local-bus transaction (wen for write,
-- ren for read) and the regfile's response (ack/err/rdata) is forwarded straight
-- back. The wrapper adds no register stage of its own, so the regfile's single
-- registered cycle is the whole latency: ipb_ack/ipb_err assert exactly one clock
-- after a strobe. The regfile's own response guard (it acks a held request only
-- once) provides transaction separation, so no FSM is needed here. The address is
-- forwarded unchanged; the regfile slices the module window from it. IPBus's sync
-- active-high reset passes straight to the regfile.
library ieee;
use ieee.std_logic_1164.all;
use ieee.numeric_std.all;

library ipbus;
use ipbus.ipbus.all;

use work.localbus_pkg.all;
use work.prototype_regfile_pkg.all;

entity prototype_ipb_endpoint is
  generic (
    G_BASE_ADDRESS       : unsigned(31 downto 0) := x"00000000";
    G_CHECK_BASE_ADDRESS : boolean               := true
  );
  port (
    clk     : in  std_logic;
    reset   : in  std_logic;
    ipb_in  : in  ipb_wbus;
    ipb_out : out ipb_rbus;
    to_hw   : out t_prototype_to_hw;
    from_hw : in  t_prototype_from_hw
  );
end entity prototype_ipb_endpoint;

architecture rtl of prototype_ipb_endpoint is

  signal m2s : t_lb_m2s;
  signal s2m : t_lb_s2m;

begin

  i_regfile : entity work.prototype_regfile
    generic map (
      G_BASE_ADDRESS       => G_BASE_ADDRESS,
      G_CHECK_BASE_ADDRESS => G_CHECK_BASE_ADDRESS,
      G_RESET_ACTIVE_LOW   => false)      -- IPBus reset is sync active-high
    port map (
      clk     => clk,
      reset   => reset,
      lb_m2s  => m2s,
      lb_s2m  => s2m,
      to_hw   => to_hw,
      from_hw => from_hw);

  m2s.address <= ipb_in.ipb_addr;
  m2s.wdata   <= ipb_in.ipb_wdata;
  m2s.wen     <= ipb_in.ipb_strobe and ipb_in.ipb_write;
  m2s.ren     <= ipb_in.ipb_strobe and not ipb_in.ipb_write;

  ipb_out.ipb_rdata <= s2m.rdata;
  ipb_out.ipb_ack   <= s2m.ack;
  ipb_out.ipb_err   <= s2m.err;

end architecture rtl;
