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
-- clock (with rdata valid) before waiting for the master to end the access by
-- dropping cs. The single-cycle ready beat matters: the SBI master samples rdata
-- on the same edge it first sees ready high, so leaving ready asserted into the
-- next access would let the master sample stale data. ack and err alike complete
-- as one ready beat (SBI has no error line); on a decode error rdata is forced to
-- 0 so reads of invalid addresses are deterministic, matching the AXI endpoint.
-- SBI carries no reset of its own, so a sync active-high reset is passed straight
-- to the regfile. The master drives a byte address (as the AXI endpoint does), so
-- it maps directly onto the local-bus address with no shift.
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

  type t_state is (ST_IDLE, ST_BUSY, ST_RESP);
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
        case state is
          when ST_IDLE =>
            ready_i <= '0';
            -- Start only on an exclusive request (wena xor rena). SBI asserts
            -- exactly one, but enforcing it here keeps the local-bus invariant
            -- (exactly one of wen/ren) from leaking out to a mis-driven master.
            if cs = '1' and (wena xor rena) = '1' then
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
              state   <= ST_RESP;
            end if;

          when ST_RESP =>
            -- ready is a single-cycle beat (set in ST_BUSY); drop it after the
            -- master has had one clock to sample it, then wait for the access to
            -- end (cs low) so the next access starts clean and never samples a
            -- stale ready/rdata.
            ready_i <= '0';
            if cs = '0' then
              state <= ST_IDLE;
            end if;
        end case;
      end if;
    end if;
  end process p_sbi;

  ready <= ready_i;
  rdata <= rdata_i;

end architecture rtl;
