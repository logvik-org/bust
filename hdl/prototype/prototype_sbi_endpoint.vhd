-- SBI (Simple Bus Interface) wrapper prototype for the local-bus register file.
-- One of the protocol wrappers in the target architecture:
--   <bus> wrapper -> local bus (t_lb_m2s / t_lb_s2m) -> regfile
-- Hand-written reference HDL (not generator output), verified with the stock
-- Bitvis SBI VIP, proving the SBI-to-local-bus bridge before the generator
-- emits it.
--
-- SBI is a single-beat protocol with an explicit ready handshake: the master
-- raises cs together with wena or rena and holds the request until the slave
-- asserts ready. The bridge starts one local-bus transaction on that strobe,
-- holds until the regfile answers with ack/err, then drives ready for a single
-- clock with rdata valid. Two details matter:
--   * ready is a one-cycle beat, not held until cs drops. The SBI master samples
--     rdata on the same edge it first sees ready, then ends the access; leaving
--     ready high would let the next access sample a stale ready/rdata, and the
--     inter-access cs gap is sub-cycle so it cannot be sampled reliably anyway.
--   * a one-cycle guard (ready still registered high the cycle after BUSY) blocks
--     re-triggering the just-completed access, the same scheme as the IPBus
--     endpoint. IDLE re-evaluates cs/wena/rena every cycle, so a back-to-back
--     access starts immediately with no cs-low handshake.
-- ack and err alike complete as one ready beat (SBI has no error line); on a
-- decode error rdata is forced to 0 so reads of invalid addresses are
-- deterministic, matching the AXI endpoint. SBI carries no reset of its own, so a
-- sync active-high reset is passed straight to the regfile. The master drives a
-- byte address (as the AXI endpoint does), mapped directly onto the local bus.
library ieee;
use ieee.std_logic_1164.all;
use ieee.numeric_std.all;

use work.localbus_pkg.all;
use work.prototype_regfile_pkg.all;

entity prototype_sbi_endpoint is
  generic (
    G_BASE_ADDRESS       : unsigned(31 downto 0) := x"00000000";
    G_CHECK_BASE_ADDRESS : boolean               := true
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

  type t_state is (ST_IDLE, ST_BUSY);
  signal state : t_state := ST_IDLE;

  signal m2s : t_lb_m2s := C_LB_M2S_IDLE;
  signal s2m : t_lb_s2m;

  signal ready_i : std_logic := '0';
  signal rdata_i : std_logic_vector(31 downto 0) := (others => '0');

begin

  i_regfile : entity work.prototype_regfile
    generic map (
      G_BASE_ADDRESS       => G_BASE_ADDRESS,
      G_CHECK_BASE_ADDRESS => G_CHECK_BASE_ADDRESS,
      G_RESET_ACTIVE_LOW   => false)      -- SBI carries no reset; use sync active-high
    port map (
      clk     => clk,
      reset   => reset,
      lb_m2s  => m2s,
      lb_s2m  => s2m,
      to_hw   => to_hw,
      from_hw => from_hw);

  p_sbi : process (clk) is
  begin
    if rising_edge(clk) then
      if reset = '1' then
        state   <= ST_IDLE;
        m2s     <= C_LB_M2S_IDLE;
        ready_i <= '0';
        rdata_i <= (others => '0');
      else
        ready_i <= '0';                   -- ready is a single-cycle beat

        case state is
          when ST_IDLE =>
            -- Start on an exclusive request (wena xor rena enforces the
            -- local-bus one-of-wen/ren invariant), but not while ready is still
            -- registered high: that gates re-triggering the just-completed
            -- access without needing to see cs go low.
            if cs = '1' and (wena xor rena) = '1' and ready_i = '0' then
              m2s.address <= addr;
              m2s.wdata   <= wdata;
              m2s.wen     <= wena;
              m2s.ren     <= rena;
              state       <= ST_BUSY;
            end if;

          when ST_BUSY =>
            if s2m.ack = '1' or s2m.err = '1' then
              m2s.wen <= '0';
              m2s.ren <= '0';
              -- err -> deterministic 0 (the regfile leaves rdata unchanged on a
              -- decode error, and SBI has no error line to flag it).
              if s2m.err = '1' then
                rdata_i <= (others => '0');
              else
                rdata_i <= s2m.rdata;
              end if;
              ready_i <= '1';
              state   <= ST_IDLE;
            end if;
        end case;
      end if;
    end if;
  end process p_sbi;

  ready <= ready_i;
  rdata <= rdata_i;

end architecture rtl;
