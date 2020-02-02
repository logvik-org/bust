# Set default error behaviour
if {[batch_mode]} {
  onerror {abort all; exit -f -code 1}
} else {
  onerror {abort all}
}

# Shut down running simulation
quit -sim

# Set project paths
quietly set example_module_path "../"
quietly set bus_path "../"
quietly set UVVM_path "../../../../../UVVM"

# Compile UVVM Dependencies
do $UVVM_path/script/compile_all.do $UVVM_path/script $example_module_path/sim $example_module_path/scripts/component_list.txt

# Set vcom args
quietly set vcom_args "-pedanticerrors -fsmverbose -quiet -check_synthesis +cover=sbt"

###########################################################################
# Compile bus source files into library
###########################################################################

# Set up library and sim path
quietly set lib_name "bust"
quietly set bus_sim_path "$bus_path/sim"

# (Re-)Generate library and Compile source files
echo "\nRe-gen lib and compile $lib_name source\n"
if {[file exists $bus_sim_path/$lib_name]} {
  file delete -force $bus_sim_path/$lib_name
}

vlib $bus_sim_path/$lib_name
vmap $lib_name $bus_sim_path/$lib_name

quietly set vhdldirectives "-2008 -work $lib_name"

eval vcom $vcom_args $vhdldirectives $bus_path/hdl/axi_pkg.vhd


###########################################################################
# Compile source files into library
###########################################################################

# Set up library and sim path
quietly set lib_name "example_axi"
quietly set example_axi_sim_path "$example_axi_path/sim"

# (Re-)Generate library and Compile source files
echo "\nRe-gen lib and compile $lib_name source\n"
if {[file exists $example_axi_sim_path/$lib_name]} {
  file delete -force $example_axi_sim_path/$lib_name
}

vlib $example_axi_sim_path/$lib_name
vmap $lib_name $example_axi_sim_path/$lib_name

quietly set vhdldirectives "-2008 -work $lib_name"

eval vcom $vcom_args $vhdldirectives $example_axi_path/hdl/example_axi_pif_pkg.vhd
eval vcom $vcom_args $vhdldirectives $example_axi_path/hdl/example_axi_axi_pif.vhd

###########################################################################
# Compile testbench files into library
###########################################################################
quietly set vcom_args "-quiet"
eval vcom $vcom_args $vhdldirectives $example_axi_path/tb/example_axi_axi_pif_tb.vhd

###########################################################################
# Simulate
###########################################################################
vsim -quiet -coverage -t 1ps example_axi.example_axi_axi_pif_tb
add wave -position insertpoint sim:/example_axi_axi_pif_tb/*

# Trick to avoid metastability warnings
quietly set NumericStdNoWarnings 1
run 1 ps;
quietly set NumericStdNoWarnings 0
run -all

coverage exclude -du example_axi_axi_pif -togglenode araddr
coverage exclude -du example_axi_axi_pif -togglenode araddr_i
coverage exclude -du example_axi_axi_pif -togglenode awaddr
coverage exclude -du example_axi_axi_pif -togglenode awaddr_i
coverage exclude -du example_axi_axi_pif -togglenode bresp
coverage exclude -du example_axi_axi_pif -togglenode bresp_i
coverage exclude -du example_axi_axi_pif -togglenode rresp
coverage exclude -du example_axi_axi_pif -togglenode rresp_i
coverage report
coverage report -html -htmldir covhtmlreport -code bcefst