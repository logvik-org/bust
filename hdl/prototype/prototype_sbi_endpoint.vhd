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
-- holds until the regfile answers with ack/err, then pulses ready (with rdata
-- valid) and holds it until the master ends the access by dropping cs. err and
-- ack both surface as a single ready beat: SBI has no error line, matching the
-- regfile's policy of reserving err for address-decode failures. SBI carries no
-- reset of its own, so a sync active-high reset is passed straight to the
-- regfile. The master drives a byte address (as the AXI endpoint does), so it
-- maps directly onto the local-bus address with no shift.
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
            -- SBI asserts exactly one of wena/rena with cs; forward as-is.
            if cs = '1' and (wena = '1' or rena = '1') then
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
              rdata_i <= s2m.rdata;
              ready_i <= '1';
              state   <= ST_RESP;
            end if;

          when ST_RESP =>
            -- Hold ready and rdata until the master ends the access (cs low).
            if cs = '0' then
              ready_i <= '0';
              state   <= ST_IDLE;
            end if;
        end case;
      end if;
    end if;
  end process p_sbi;

  ready <= ready_i;
  rdata <= rdata_i;

end architecture rtl;
