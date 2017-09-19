

if {[batch_mode]} {
  onerror {abort all; exit -f -code 1}
} else {
  onerror {abort all}
}
#Just in case...
quietly quit -sim   

# Detect simulator
if {[catch {eval "vsim -version"} message] == 0} { 
  quietly set simulator_version [eval "vsim -version"]
  # puts "Version is: $simulator_version"
  if {[regexp -nocase {modelsim} $simulator_version]} {
    quietly set simulator "modelsim"
  } elseif {[regexp -nocase {aldec} $simulator_version]} {
    quietly set simulator "rivierapro"
  } else {
    puts "Unknown simulator. Attempting use use Modelsim commands."
    quietly set simulator "modelsim"
  }  
} else { 
    puts "vsim -version failed with the following message:\n $message"
    abort all
}

# Set up module_name_part_path and lib_name
#------------------------------------------------------
quietly set lib_name "module_name"
quietly set part_name "module_name"
# path from mpf-file in sim
quietly set module_name_part_path "../..//$part_name"

if { [info exists 1] } {
  # path from this part to target part
  quietly set module_name_part_path "$1/..//$part_name"
  unset 1
}


# Testbenches reside in the design library. Hence no regeneration of lib.
#------------------------------------------------------------------------

if { [string equal -nocase $simulator "modelsim"] } {
  set compdirectives "-2008 -work $lib_name"
} elseif { [string equal -nocase $simulator "rivierapro"] } {
  set compdirectives "-2008 -dbg -work $lib_name"
}

eval vcom  $compdirectives  $module_name_part_path/tb/module_name_th.vhd
eval vcom  $compdirectives  $module_name_part_path/tb/module_name_tb.vhd
