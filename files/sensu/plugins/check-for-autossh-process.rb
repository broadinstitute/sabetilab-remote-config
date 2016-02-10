#!/usr/bin/env ruby

# get the current list of processes
processes = `ps -A`

# determine if the process is running
running = processes.lines.detect do |process|
  process.include?('autossh')
end

# return appropriate check output and exit status code
if running
  puts 'OK - autossh process is running'
  exit 0
else
  puts 'WARNING - autossh process is NOT running'
  exit 1
end

