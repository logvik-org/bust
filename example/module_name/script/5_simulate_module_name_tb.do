if {[batch_mode]} {
  onerror {abort all; exit -f -code 1}
  onbreak {abort all; exit -f}
} else {
  onerror {abort all}
}

vsim  module_name.module_name_tb

if {[batch_mode] == 0} {
  add log -r /*
  source ../script/wave.do
}
run -all
