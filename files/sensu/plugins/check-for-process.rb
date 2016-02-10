#!/usr/bin/env ruby

# get the current list of processes
processes = `ps -A`

if not ARGV[0]
    p_name = "ps"
else
    p_name = ARGV[0]
end

# determine if the process is running
running = processes.lines.detect do |process|
  process.include?(p_name)
end

# return appropriate check output and exit status code
if running
  puts 'OK - ' + p_name + ' process is running'
  exit 0
else
  puts 'WARNING - ' + p_name + ' process is NOT running'
  exit 1
end

