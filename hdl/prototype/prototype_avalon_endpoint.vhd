-- Avalon-MM wrapper prototype for the local-bus register file.
-- One of the protocol wrappers in the target architecture:
--   <bus> wrapper -> local bus (t_lb_m2s / t_lb_s2m) -> regfile
-- Hand-written reference HDL (not generator output), verified with the stock
-- Bitvis Avalon-MM VIP, proving the Avalon-MM-to-local-bus bridge before the
-- generator emits it.
--
-- Avalon-MM stalls with waitrequest: the master holds the command (chipselect
-- with read or write) until the slave drops waitrequest, and for a
-- waitrequest-controlled read (no readdatavalid) readdata is valid on the cycle
-- waitrequest deasserts. The bridge is pure combinational glue: the command
-- drives one local-bus transaction and the regfile's response is forwarded
-- straight back, dropping waitrequest for the single cycle the regfile answers.
-- The wrapper adds no register stage, so the regfile's single registered cycle is
-- the whole latency: waitrequest drops one clock after the command. This is the
-- dual of the SBI endpoint: waitrequest=1 is "not ready", and the accept beat is
-- one cycle of waitrequest=0. With no command asserted, ack is low so waitrequest
-- defaults high. The regfile's response guard (it acks a held command only once)
-- provides transaction separation, so no FSM is needed. On a decode error
-- readdata is forced to 0 (the regfile leaves it unchanged), matching the AXI
-- endpoint. Avalon-MM's reset is sync active-high, passed straight to the
-- regfile, and the master drives a byte address mapped directly onto the local
-- bus.

library ieee;
use ieee.std_logic_1164.all;
use ieee.numeric_std.all;

use work.prototype_localbus_pkg.all;
use work.prototype_regfile_pkg.all;

entity prototype_avalon_endpoint is
  generic (
    G_BASE_ADDRESS       : unsigned(31 downto 0) := x"00000000";
    G_CHECK_BASE_ADDRESS : boolean               := true;
    G_MODULE_ADDR_WIDTH  : natural               := C_PROTOTYPE_MODULE_ADDR_WIDTH
  );
  port (
    clk   : in    std_logic;
    reset : in    std_logic;

    -- Avalon-MM subordinate interface
    chipselect  : in    std_logic;
    address     : in    std_logic_vector(31 downto 0);
    read        : in    std_logic;
    write       : in    std_logic;
    writedata   : in    std_logic_vector(31 downto 0);
    waitrequest : out   std_logic;
    readdata    : out   std_logic_vector(31 downto 0);

    -- hardware side of the register file
    to_hw   : out   t_prototype_to_hw;
    from_hw : in    t_prototype_from_hw
  );
end entity prototype_avalon_endpoint;

architecture rtl of prototype_avalon_endpoint is

  signal m2s : t_lb_m2s;
  signal s2m : t_lb_s2m;

begin

  -- The Avalon-MM reset is synchronous and active high.
  i_regfile : entity work.prototype_regfile(rtl)
    generic map (
      G_BASE_ADDRESS       => G_BASE_ADDRESS,
      G_CHECK_BASE_ADDRESS => G_CHECK_BASE_ADDRESS,
      G_MODULE_ADDR_WIDTH  => G_MODULE_ADDR_WIDTH,
      G_RESET_ACTIVE_LOW   => false
    )
    port map (
      clk     => clk,
      reset   => reset,
      lb_m2s  => m2s,
      lb_s2m  => s2m,
      to_hw   => to_hw,
      from_hw => from_hw
    );

  m2s.address <= address;
  m2s.wdata   <= writedata;
  m2s.wen     <= chipselect and write;
  m2s.ren     <= chipselect and read;

  -- waitrequest=1 stalls; the accept beat is one cycle of waitrequest=0 when the
  -- regfile answers. With no command, ack/err are low so waitrequest stays high.
  waitrequest <= not (s2m.ack or s2m.err);
  readdata    <= (others => '0') when s2m.err = '1' else
                 s2m.rdata;

end architecture rtl;
