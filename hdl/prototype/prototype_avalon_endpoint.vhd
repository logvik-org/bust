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
-- waitrequest deasserts. The bridge starts one local-bus transaction on the
-- command, holds (waitrequest high) until the regfile answers with ack/err, then
-- drops waitrequest for a single clock with readdata valid. This is the dual of
-- the SBI endpoint: waitrequest=1 is "not ready" (SBI ready=0), and the accept
-- beat is a one-cycle waitrequest=0 (SBI ready=1). The same one-cycle guard
-- (waitrequest still registered low the cycle after BUSY) blocks re-triggering
-- the just-completed access; IDLE re-evaluates the command every cycle, so a
-- back-to-back access starts immediately. On a decode error readdata is forced
-- to 0 (the regfile leaves it unchanged on err), matching the AXI endpoint.
-- Avalon-MM's reset is sync active-high, passed straight to the regfile, and the
-- master drives a byte address mapped directly onto the local bus.
library ieee;
use ieee.std_logic_1164.all;
use ieee.numeric_std.all;

use work.localbus_pkg.all;
use work.prototype_regfile_pkg.all;

entity prototype_avalon_endpoint is
  generic (
    G_BASE_ADDRESS       : unsigned(31 downto 0) := x"00000000";
    G_CHECK_BASE_ADDRESS : boolean               := true
  );
  port (
    clk         : in  std_logic;
    reset       : in  std_logic;

    -- Avalon-MM subordinate interface
    chipselect  : in  std_logic;
    address     : in  std_logic_vector(31 downto 0);
    read        : in  std_logic;
    write       : in  std_logic;
    writedata   : in  std_logic_vector(31 downto 0);
    waitrequest : out std_logic;
    readdata    : out std_logic_vector(31 downto 0);

    -- hardware side of the register file
    to_hw       : out t_prototype_to_hw;
    from_hw     : in  t_prototype_from_hw
  );
end entity prototype_avalon_endpoint;

architecture rtl of prototype_avalon_endpoint is

  type t_state is (ST_IDLE, ST_BUSY);
  signal state : t_state := ST_IDLE;

  signal m2s : t_lb_m2s := C_LB_M2S_IDLE;
  signal s2m : t_lb_s2m;

  signal waitrequest_i : std_logic := '1';
  signal readdata_i    : std_logic_vector(31 downto 0) := (others => '0');

begin

  i_regfile : entity work.prototype_regfile
    generic map (
      G_BASE_ADDRESS       => G_BASE_ADDRESS,
      G_CHECK_BASE_ADDRESS => G_CHECK_BASE_ADDRESS,
      G_RESET_ACTIVE_LOW   => false)      -- Avalon-MM reset is sync active-high
    port map (
      clk     => clk,
      reset   => reset,
      lb_m2s  => m2s,
      lb_s2m  => s2m,
      to_hw   => to_hw,
      from_hw => from_hw);

  p_avalon : process (clk) is
  begin
    if rising_edge(clk) then
      if reset = '1' then
        state         <= ST_IDLE;
        m2s           <= C_LB_M2S_IDLE;
        waitrequest_i <= '1';
        readdata_i    <= (others => '0');
      else
        waitrequest_i <= '1';             -- stall by default; accept is one cycle

        case state is
          when ST_IDLE =>
            -- Start on an exclusive command (read xor write enforces the
            -- local-bus one-of-wen/ren invariant), but not while waitrequest is
            -- still registered low: that gates re-triggering the just-completed
            -- access without needing to see the command drop.
            if chipselect = '1' and (read xor write) = '1'
               and waitrequest_i = '1' then
              m2s.address <= address;
              m2s.wdata   <= writedata;
              m2s.wen     <= write;
              m2s.ren     <= read;
              state       <= ST_BUSY;
            end if;

          when ST_BUSY =>
            if s2m.ack = '1' or s2m.err = '1' then
              m2s.wen <= '0';
              m2s.ren <= '0';
              if s2m.err = '1' then
                readdata_i <= (others => '0');
              else
                readdata_i <= s2m.rdata;
              end if;
              waitrequest_i <= '0';
              state         <= ST_IDLE;
            end if;
        end case;
      end if;
    end if;
  end process p_avalon;

  waitrequest <= waitrequest_i;
  readdata    <= readdata_i;

end architecture rtl;
