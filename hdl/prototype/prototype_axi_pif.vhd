-- AXI4-Lite wrapper prototype for the local-bus register file.
-- One of the protocol wrappers in the target architecture:
--   <bus> wrapper -> local bus (t_lb_m2s / t_lb_s2m) -> regfile
-- This is hand-written reference HDL (not generator output), verified with the
-- stock UVVM AXI-Lite VIP, to prove the AXI-to-local-bus bridge before the
-- generator emits it.
--
-- A simple AXI4-Lite slave FSM serializes one transaction at a time onto the
-- single-outstanding local bus: it accepts AW+W (or AR), drives wen/ren with the
-- full byte address and holds until the regfile answers with ack/err, then
-- returns the response. err maps to SLVERR; ack maps to OKAY. AXI's native
-- async active-low reset is handed to the regfile via G_RESET_ACTIVE_LOW.
library ieee;
use ieee.std_logic_1164.all;
use ieee.numeric_std.all;

use work.localbus_pkg.all;
use work.prototype_regfile_pkg.all;

entity prototype_axi_pif is
  generic (
    G_BASE_ADDRESS       : unsigned(31 downto 0) := x"00000000";
    G_CHECK_BASE_ADDRESS : boolean               := true
  );
  port (
    clk      : in  std_logic;
    areset_n : in  std_logic;

    -- AXI4-Lite subordinate interface
    awaddr   : in  std_logic_vector(31 downto 0);
    awvalid  : in  std_logic;
    awready  : out std_logic;
    wdata    : in  std_logic_vector(31 downto 0);
    wvalid   : in  std_logic;
    wready   : out std_logic;
    bresp    : out std_logic_vector(1 downto 0);
    bvalid   : out std_logic;
    bready   : in  std_logic;
    araddr   : in  std_logic_vector(31 downto 0);
    arvalid  : in  std_logic;
    arready  : out std_logic;
    rdata    : out std_logic_vector(31 downto 0);
    rresp    : out std_logic_vector(1 downto 0);
    rvalid   : out std_logic;
    rready   : in  std_logic;

    -- hardware side of the register file
    to_hw    : out t_prototype_to_hw;
    from_hw  : in  t_prototype_from_hw
  );
end entity prototype_axi_pif;

architecture rtl of prototype_axi_pif is

  -- AXI responses: OKAY / SLVERR.
  constant C_RESP_OKAY   : std_logic_vector(1 downto 0) := "00";
  constant C_RESP_SLVERR : std_logic_vector(1 downto 0) := "10";

  type t_state is (ST_IDLE, ST_WRITE, ST_BRESP, ST_READ, ST_RRESP);
  signal state : t_state := ST_IDLE;

  signal m2s : t_lb_m2s := C_LB_M2S_IDLE;
  signal s2m : t_lb_s2m;

  signal awready_i : std_logic := '0';
  signal wready_i  : std_logic := '0';
  signal bvalid_i  : std_logic := '0';
  signal bresp_i   : std_logic_vector(1 downto 0) := C_RESP_OKAY;
  signal arready_i : std_logic := '0';
  signal rvalid_i  : std_logic := '0';
  signal rresp_i   : std_logic_vector(1 downto 0) := C_RESP_OKAY;
  signal rdata_i   : std_logic_vector(31 downto 0) := (others => '0');

begin

  i_regfile : entity work.prototype_regfile
    generic map (
      G_BASE_ADDRESS       => G_BASE_ADDRESS,
      G_CHECK_BASE_ADDRESS => G_CHECK_BASE_ADDRESS,
      G_RESET_ACTIVE_LOW   => true)       -- AXI reset is active-low
    port map (
      clk     => clk,
      reset   => areset_n,
      lb_m2s  => m2s,
      lb_s2m  => s2m,
      to_hw   => to_hw,
      from_hw => from_hw);

  -- One transaction at a time, mapped onto the single-outstanding local bus.
  p_axi : process (clk, areset_n) is
  begin
    if areset_n = '0' then
      state     <= ST_IDLE;
      m2s       <= C_LB_M2S_IDLE;
      awready_i <= '0';
      wready_i  <= '0';
      bvalid_i  <= '0';
      bresp_i   <= C_RESP_OKAY;
      arready_i <= '0';
      rvalid_i  <= '0';
      rresp_i   <= C_RESP_OKAY;
      rdata_i   <= (others => '0');
    elsif rising_edge(clk) then
      -- Accept strobes are single-cycle.
      awready_i <= '0';
      wready_i  <= '0';
      arready_i <= '0';

      case state is
        when ST_IDLE =>
          -- Write has priority; only one of wen/ren is ever asserted.
          if awvalid = '1' and wvalid = '1' then
            m2s.address <= awaddr;
            m2s.wdata   <= wdata;
            m2s.wen     <= '1';
            awready_i   <= '1';
            wready_i    <= '1';
            state       <= ST_WRITE;
          elsif arvalid = '1' then
            m2s.address <= araddr;
            m2s.ren     <= '1';
            arready_i   <= '1';
            state       <= ST_READ;
          end if;

        when ST_WRITE =>
          if s2m.ack = '1' or s2m.err = '1' then
            m2s.wen  <= '0';
            bvalid_i <= '1';
            bresp_i  <= C_RESP_SLVERR when s2m.err = '1' else C_RESP_OKAY;
            state    <= ST_BRESP;
          end if;

        when ST_BRESP =>
          if bready = '1' then
            bvalid_i <= '0';
            state    <= ST_IDLE;
          end if;

        when ST_READ =>
          if s2m.ack = '1' or s2m.err = '1' then
            m2s.ren  <= '0';
            rvalid_i <= '1';
            if s2m.err = '1' then
              rresp_i <= C_RESP_SLVERR;
              rdata_i <= (others => '0');
            else
              rresp_i <= C_RESP_OKAY;
              rdata_i <= s2m.rdata;
            end if;
            state <= ST_RRESP;
          end if;

        when ST_RRESP =>
          if rready = '1' then
            rvalid_i <= '0';
            state    <= ST_IDLE;
          end if;
      end case;
    end if;
  end process p_axi;

  awready <= awready_i;
  wready  <= wready_i;
  bresp   <= bresp_i;
  bvalid  <= bvalid_i;
  arready <= arready_i;
  rdata   <= rdata_i;
  rresp   <= rresp_i;
  rvalid  <= rvalid_i;

end architecture rtl;
