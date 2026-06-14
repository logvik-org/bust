-- Protocol-agnostic local bus interface for register-map access.
--
-- A minimal single-beat transaction: address, write data, read data, write
-- enable, read enable, plus an acknowledge / error response. All supported bus
-- protocols (AXI4-Lite, IPBus, ...) become thin wrappers around this.
--
-- Contract (single outstanding transaction, "hold until acknowledged"):
--   * The master asserts exactly one of wen / ren together with a valid
--     address (and wdata for writes) and holds the request stable until it
--     observes a response.
--   * The regfile completes the beat by pulsing exactly one of ack or err for
--     one clock cycle. ack and err are mutually exclusive.
--   * Variable-latency targets (e.g. a register backed by RAM) simply assert
--     the response later. There is no separate stall/wait signal: withholding
--     ack/err is the stall mechanism. This covers IPBus stall (delayed ack)
--     and AXI back-pressure (the wrapper delays its response channel) without
--     leaking protocol detail into the regfile. A dedicated stall wire would
--     only be needed for a pipelined / multi-outstanding bus, which is out of
--     scope for this single-beat abstraction.
--
-- Address/data widths are named constants rather than literals so the record
-- definitions read by intent. They are fixed at 32 bits in this prototype;
-- turning them into generics is a generator-time concern, deferred with the
-- rest of the generator work.
library ieee;
use ieee.std_logic_1164.all;

package localbus_pkg is

  constant C_LB_ADDR_WIDTH : natural := 32;
  constant C_LB_DATA_WIDTH : natural := 32;

  type t_lb_m2s is record
    address : std_logic_vector(C_LB_ADDR_WIDTH - 1 downto 0);
    wdata   : std_logic_vector(C_LB_DATA_WIDTH - 1 downto 0);
    wen     : std_logic;
    ren     : std_logic;
  end record;

  type t_lb_s2m is record
    rdata : std_logic_vector(C_LB_DATA_WIDTH - 1 downto 0);
    ack   : std_logic;
    err   : std_logic;
  end record;

  constant C_LB_M2S_IDLE : t_lb_m2s := (
    address => (others => '0'),
    wdata   => (others => '0'),
    wen     => '0',
    ren     => '0');

  constant C_LB_S2M_IDLE : t_lb_s2m := (
    rdata => (others => '0'),
    ack   => '0',
    err   => '0');

end package localbus_pkg;
