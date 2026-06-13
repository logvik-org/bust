-- Protocol-agnostic local bus interface for register-map access.
-- A minimal single-beat transaction: address, write data, read data, write
-- enable, read enable, acknowledge, error, and wait/stall. All supported bus
-- protocols (AXI4-Lite, IPBus, ...) become thin wrappers around this.
library ieee;
use ieee.std_logic_1164.all;

package localbus_pkg is

  type t_lb_m2s is record
    address : std_logic_vector(31 downto 0);
    wdata   : std_logic_vector(31 downto 0);
    wen     : std_logic;
    ren     : std_logic;
  end record;

  type t_lb_s2m is record
    rdata   : std_logic_vector(31 downto 0);
    ack     : std_logic;
    err     : std_logic;
    waitreq : std_logic;
  end record;

  constant C_LB_M2S_IDLE : t_lb_m2s := (
    address => (others => '0'),
    wdata   => (others => '0'),
    wen     => '0',
    ren     => '0');

  constant C_LB_S2M_IDLE : t_lb_s2m := (
    rdata   => (others => '0'),
    ack     => '0',
    err     => '0',
    waitreq => '0');

end package localbus_pkg;
